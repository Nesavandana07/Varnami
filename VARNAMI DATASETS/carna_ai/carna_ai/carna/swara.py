"""Stage 3: relative-cents contour -> swara segments (with pitch-movement + timing) -> readable notation."""
import numpy as np
from .knowledge import DEFAULT_NAMES, ALT_NAMES, load_ragas
from .audio import FPS


def _runs(q):
    """Run-length encode an int array with NaN-as-sentinel (use a large int)."""
    idx = np.r_[0, np.where(np.diff(q) != 0)[0] + 1, len(q)]
    return [[int(idx[i]), int(idx[i + 1]), int(q[idx[i]])] for i in range(len(idx) - 1)]


def segment_notes(cents, fps=FPS, min_note_s=0.08, min_voiced_s=0.06, gamaka_amp=20):
    """Quantise to nearest semitone, merge sub-`min_note_s` runs into neighbours (glides / gamaka excursions),
    then describe the movement inside each note from the raw contour.  Returns list of dicts (see `fields`)."""
    NAN = -10 ** 6
    ok = ~np.isnan(cents)
    q = np.where(ok, np.round(np.nan_to_num(cents) / 100.0), NAN).astype(int)
    runs = [r for r in _runs(q)]
    minf = max(1, int(min_note_s * fps))
    # merge short voiced runs
    changed = True
    while changed:
        changed = False
        for i, (s, e, v) in enumerate(runs):
            if v == NAN or e - s >= minf: continue
            prev = runs[i - 1] if i > 0 and runs[i - 1][2] != NAN and runs[i - 1][1] == s else None
            nxt = runs[i + 1] if i + 1 < len(runs) and runs[i + 1][2] != NAN and runs[i + 1][0] == e else None
            if prev is None and nxt is None:
                if e - s < int(min_voiced_s * fps): runs[i][2] = NAN; changed = True; break
                continue
            tgt = prev if (nxt is None or (prev is not None and prev[1] - prev[0] >= nxt[1] - nxt[0])) else nxt
            tgt[0], tgt[1] = min(tgt[0], s), max(tgt[1], e)
            runs.pop(i); changed = True; break
        if changed:                                    # coalesce equal neighbours
            out = []
            for r in runs:
                if out and out[-1][2] == r[2] and out[-1][1] == r[0]: out[-1][1] = r[1]
                else: out.append(r)
            runs = out
    notes = []
    for s, e, v in runs:
        if v == NAN: continue
        seg = cents[s:e]; seg = seg[~np.isnan(seg)]
        if len(seg) == 0: continue
        n3 = max(1, len(seg) // 4)
        start_c, end_c, mean_c = float(np.median(seg[:n3])), float(np.median(seg[-n3:])), float(np.median(seg))
        dev = seg - np.median(seg)
        thr = gamaka_amp
        st = np.where(dev > thr, 1, np.where(dev < -thr, -1, 0)); st = st[st != 0]
        cycles = int(np.sum(np.diff(st) != 0) // 2) if len(st) > 1 else 0
        rng_c = float(seg.max() - seg.min())
        if cycles >= 2 and rng_c > 2 * thr: mv = "oscillation"
        elif end_c - start_c > 45: mv = "glide_up"
        elif end_c - start_c < -45: mv = "glide_down"
        else: mv = "steady"
        notes.append({"semitone": int(v), "pc": int(v % 12), "octave": int(v // 12), "start": s / fps, "end": e / fps,
                      "dur": (e - s) / fps, "mean_cents": mean_c, "offset_cents": mean_c - 100.0 * v,
                      "start_cents": start_c, "end_cents": end_c, "range_cents": rng_c, "cycles": cycles, "movement": mv})
    # a following note starting right after a glide inherits the contour: record the approach from the previous note
    for a, b in zip(notes, notes[1:]):
        b["from_semitone"] = a["semitone"] if b["start"] - a["end"] < 0.15 else None
    if notes: notes[0]["from_semitone"] = None
    return notes


def swara_name(pc, raga=None):
    """Display name for a pitch class; raga context disambiguates R2/G1, R3/G2, D2/N1, D3/N2."""
    if raga: return load_ragas()[raga].names.get(pc, DEFAULT_NAMES[pc])
    return DEFAULT_NAMES[pc]


def swara_candidates(pc):
    return ALT_NAMES.get(pc, [DEFAULT_NAMES[pc]])


def label_notes(notes, raga=None):
    for n in notes:
        n["swara"] = swara_name(n["pc"], raga); n["candidates"] = swara_candidates(n["pc"])
        n["label"] = n["swara"] + ("'" if n["octave"] >= 1 else "") + ("." if n["octave"] < 0 else "")  # S' upper, .S lower
        n["label"] = ("." + n["swara"] if n["octave"] < 0 else n["swara"] + ("'" * n["octave"]))
    return notes


MV_MARK = {"oscillation": "~", "glide_up": "/", "glide_down": "\\", "steady": ""}


def to_notation(notes, unit_s=None, line_gap_s=0.6, max_line=16, raga=None):
    """Text notation. `,` extends the previous swara by one time unit (unit = median note length unless given);
    `~` oscillation (gamaka-like), `/` `\\` rising/falling glide within the note; `.S` lower octave, `S'` upper;
    a new line starts after a pause > `line_gap_s`."""
    notes = label_notes(notes, raga)
    if not notes: return ""
    unit = unit_s or max(0.12, float(np.median([n["dur"] for n in notes])))
    lines, cur, last_end = [], [], notes[0]["start"]
    for n in notes:
        if cur and (n["start"] - last_end > line_gap_s or len(cur) >= max_line):
            lines.append(" ".join(cur)); cur = []
        tok = n["label"] + MV_MARK[n["movement"]] + "," * max(0, int(round(n["dur"] / unit)) - 1)
        cur.append(tok); last_end = n["end"]
    if cur: lines.append(" ".join(cur))
    return "\n".join(lines)
