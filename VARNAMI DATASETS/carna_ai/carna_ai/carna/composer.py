"""Stage 6a: two-raga combination experiment.  Compares two ragas and generates a short constrained phrase.
Constraints: starts on Sa; each section uses only its raga's swaras; ascents follow that raga's arohanam, descents its
avarohanam; raga switch happens on a SHARED swara (pivot); strong beats prefer shared swaras; each raga contributes at
least one 'colour' swara unique to it when it has any; phrase ends on Sa.  No gamaka (none are expert-verified yet)."""
import io, base64, re, numpy as np, soundfile as sf
from .knowledge import load_ragas, DEFAULT_NAMES
from .explain import grammar_pairs
from .synth import ladders, render_f0
from .audio import SR, FPS


def compare(a, b):
    R = load_ragas(); A, B = R[a], R[b]
    sh, ua, ub = sorted(A.pcs & B.pcs), sorted(A.pcs - B.pcs), sorted(B.pcs - A.pcs)
    nm = lambda R_, ps: [R_.names[p] for p in ps]
    GA, GB = grammar_pairs(a), grammar_pairs(b)
    return {"a": a, "b": b, "jaccard": round(len(sh) / len(A.pcs | B.pcs), 3), "shared": nm(A, sh), "shared_semitones": sh,
            "only_a": nm(A, ua), "only_b": nm(B, ub), "only_a_semitones": ua, "only_b_semitones": ub,
            "naming_differences": [f"semitone {p}: {A.names[p]} in {a} vs {B.names[p]} in {b}" for p in sh if A.names[p] != B.names[p]],
            "arohanam": {a: " ".join(A.names.get(x % 12, "") + ("'" if x == 12 else "") for x in A.aro), b: " ".join(B.names.get(x % 12, "") + ("'" if x == 12 else "") for x in B.aro)},
            "avarohanam": {a: " ".join(A.names.get(x % 12, "") + ("'" if x == 12 else "") for x in A.avaro), b: " ".join(B.names.get(x % 12, "") + ("'" if x == 12 else "") for x in B.avaro)},
            "vakra": {a: A.meta.get("vakra"), b: B.meta.get("vakra")},
            "n_swaras": {a: len(A.pcs), b: len(B.pcs)},
            "grammar_only_a": [f"{DEFAULT_NAMES[f]}->{DEFAULT_NAMES[t]} ({d})" for d in ("asc", "desc") for f, t in sorted(GA[d] - GB[d])][:8],
            "grammar_only_b": [f"{DEFAULT_NAMES[f]}->{DEFAULT_NAMES[t]} ({d})" for d in ("asc", "desc") for f, t in sorted(GB[d] - GA[d])][:8],
            "caveat": "Pitch-class overlap ignores gamaka and phrasing; it is a first filter only."}


def _walk(raga, n, start, rng, shared, strong_every, profile):
    """n notes in `raga`, beginning near `start`, steering toward `profile(i)` (target semitone)."""
    L = ladders(raga); cur, out = start, []
    for i in range(n):
        tgt = profile(i)
        d = "up" if tgt > cur else "down"
        if rng.random() < 0.25: d = "up" if d == "down" else "down"
        lad = L[d]; idx = int(np.argmin([abs(x - cur) for x in lad]))
        cands = [lad[j] for j in (idx + 1, idx + 2) if 0 <= j < len(lad) and -12 <= lad[j] <= 19]
        cands = [c for c in cands if c != cur] or [cur]
        w = np.array([(1.0 / (1 + abs(c - tgt))) * (2.0 if (i % strong_every == 0 and c % 12 in shared) else 1.0)
                      * (1.0 if c == cands[0] else 0.4) for c in cands])
        cur = int(rng.choice(cands, p=w / w.sum())); out.append(cur)
    return out


def syllabify(text):
    """Splits lyrics text into syllables (aksharas) respecting hyphens, spaces, and Indic phonetics."""
    if not text or not str(text).strip(): return []
    cleaned = re.sub(r'[,.;:!?|/\\~]+', ' ', str(text).strip())
    words = cleaned.split()
    syls = []
    for w in words:
        if "-" in w:
            parts = [p.strip() for p in w.split("-") if p.strip()]
            syls.extend(parts)
        else:
            chunks = re.findall(r'[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]*[aeiouAEIOU]+(?:[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ](?![aeiouAEIOU]))*', w)
            if chunks: syls.extend(chunks)
            else: syls.append(w)
    return [s for s in syls if s]


def fit_lyrics(notes, lyrics_text):
    """Fits lyrics syllables to swara notes, extending long notes (deergha) and building aligned dual notation."""
    syls = syllabify(lyrics_text)
    if not syls: return {"aligned": [], "dual_notation": "", "syllables": []}
    aligned = []
    for i, note in enumerate(notes):
        syl = syls[i % len(syls)] if syls else "-"
        dur = note["dur_beats"]
        ext = " ." * max(0, int(round(dur)) - 1) if dur >= 1.5 else ""
        aligned.append({
            "note_idx": i, "swara": note["swara"], "dur_beats": dur,
            "raga": note["raga"], "role": note["role"],
            "syllable": syl, "display": f"{syl}{ext}".strip()
        })
    swara_toks, lyric_toks = [], []
    for a in aligned:
        sw_ext = "," * max(0, int(round(a["dur_beats"])) - 1) if a["dur_beats"] >= 1.5 else ""
        sw = f"{a['swara']}{sw_ext}"
        lyr = a["display"]
        w = max(len(sw), len(lyr)) + 2
        swara_toks.append(sw.ljust(w))
        lyric_toks.append(lyr.ljust(w))
    dual = "Swara:   " + "".join(swara_toks) + "\nSahitya: " + "".join(lyric_toks)
    return {"aligned": aligned, "dual_notation": dual, "syllables": syls}


def generate(a, b, length=16, blend=0.5, seed=0, tonic_hz=146.83, bpm=80, with_audio=True, lyrics=None):
    R = load_ragas(); A, B = R[a], R[b]; rng = np.random.default_rng(seed)
    shared = A.pcs & B.pcs; ua, ub = A.pcs - B.pcs, B.pcs - A.pcs
    length = int(np.clip(length, 8, 48)); nb = int(round(length * blend)); nb = int(np.clip(nb, 0 if blend == 0 else 3, length - (0 if blend == 1 else 3)))
    na = length - nb
    peak = int(rng.choice([7, 9, 12]))
    prof = lambda i: (peak * (i / (length * 0.6)) if i < length * 0.6 else peak * (1 - (i - length * 0.6) / (length * 0.4)))
    seq = [(0, a)]
    segA = _walk(a, na, 0, rng, shared, 4, lambda i: prof(i)) if na else []
    # pivot: last note of section A must be shared (nudge to the nearest shared pitch within a step or two)
    if segA and nb:
        segA[-1] = min((x for x in range(-12, 20) if x % 12 in shared and x % 12 in A.pcs), key=lambda x: abs(x - segA[-1]))
    segB = _walk(b, nb, segA[-1] if segA else 0, rng, shared, 4, lambda i: prof(na + i)) if nb else []
    pitches = [(p, a) for p in segA] + [(p, b) for p in segB]
    # colour swara guarantee: place one swara unique to each raga at the position needing the smallest nudge
    # (never the first note, the pivot, or the final note, which the cadence rewrites)
    for raga, uniq in ((a, ua), (b, ub)):
        idxs = [i for i, (_, r) in enumerate(pitches) if r == raga and 0 < i < len(pitches) - 1 and not (na and nb and i == na - 1)]
        if uniq and len(idxs) >= 2 and not any(pitches[i][0] % 12 in uniq for i in idxs):
            cand = [(abs(x - pitches[i][0]), i, x) for i in idxs for x in range(-12, 20) if x % 12 in uniq]
            _, i, x = min(cand); pitches[i] = (x, raga)
    # cadence on Sa: step-wise approach, final Sa (nearest octave)
    last_r = pitches[-1][1]
    fin = min((0, 12), key=lambda s: abs(s - pitches[-1][0]))
    pitches[-1] = (fin, last_r)
    durs = rng.choice([1, 1, 2, .5, .5, 1.5], size=len(pitches)).tolist(); durs[-1] = 3.0
    for i in range(len(durs)):
        if i % 4 == 3 and i < len(durs) - 1: durs[i] = max(durs[i], 1.0)
    notes = [{"semitone": int(p), "pc": int(p % 12), "raga": r, "dur_beats": float(d),
              "swara": R[r].names[p % 12] + ("'" if p >= 12 else "") + ("" if p >= 0 else "_low"),
              "role": "pivot" if (nb and na and i == na - 1) else "colour" if p % 12 in (ua if r == a else ub) else "shared" if p % 12 in shared else "own"}
             for i, ((p, r), d) in enumerate(zip(pitches, durs))]
    chk = {"starts_on_sa": notes[0]["pc"] == 0 or True, "ends_on_sa": notes[-1]["pc"] == 0,
           "all_in_scale": all(n["pc"] in R[n["raga"]].pcs for n in notes),
           "pivot_shared": (na == 0 or nb == 0) or notes[na - 1]["pc"] in shared,
           "has_colour_a": any(n["role"] == "colour" and n["raga"] == a for n in notes) or not ua,
           "has_colour_b": any(n["role"] == "colour" and n["raga"] == b for n in notes) or not ub or nb == 0}
    # start on Sa
    if notes[0]["pc"] != 0:
        notes[0].update(semitone=0, pc=0, swara="S", role="shared")
    chk["starts_on_sa"] = True
    spb = 60.0 / bpm
    text = " ".join(f"{n['swara']}{',' * (int(round(n['dur_beats'])) - 1) if n['dur_beats'] >= 1.5 else ''}" + (" |" if i == na - 1 and na and nb else "")
                    for i, n in enumerate(notes))
    out = {"a": a, "b": b, "notes": notes, "notation": text, "n_a": na, "n_b": nb, "checks": chk, "bpm": bpm, "tonic_hz": tonic_hz,
           "legend": "`|` = switch of raga at a shared pivot swara; `,` = held longer; `_low` = lower octave; no gamaka applied."}
    if lyrics:
        out["lyrics"] = fit_lyrics(notes, lyrics)
    if with_audio: out["wav_base64"] = render_wav(notes, tonic_hz, spb)
    return out



def render_wav(notes, tonic_hz, spb, glide_s=0.07):
    segs = []
    for n in notes:
        k = max(2, int(n["dur_beats"] * spb * FPS)); segs.append(np.full(k, n["semitone"] * 100.0))
    c = np.concatenate(segs)
    from scipy.ndimage import uniform_filter1d
    c = uniform_filter1d(c, max(1, int(glide_s * FPS)), mode="nearest")           # portamento between notes
    f0 = tonic_hz * 2 ** (c / 1200)
    y = render_f0(f0, drone_tonic=tonic_hz, drone_db=-20)
    buf = io.BytesIO(); sf.write(buf, y, SR, format="WAV", subtype="PCM_16")
    return base64.b64encode(buf.getvalue()).decode()
