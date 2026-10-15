"""Swara + pitch-contour features.  Pitch classes alone cannot separate ragas that share a scale
(Harikambhoji/Kambhoji/Sahana, Kharaharapriya/Sriragam, Dheerasankarabharanam/Begada), so the vector also holds
DIRECTIONAL transition matrices (ascending vs descending moves) plus gamaka/intonation statistics."""
import numpy as np

N_FEAT = 12 + 144 + 144 + 8


def feature_names():
    pc = [f"pc{i}" for i in range(12)]
    asc = [f"asc_{a}->{b}" for a in range(12) for b in range(12)]
    desc = [f"desc_{a}->{b}" for a in range(12) for b in range(12)]
    return pc + asc + desc + ["frac_oscillating", "mean_cycles", "frac_glide", "mean_dur", "std_dur", "notes_per_s",
                              "mean_abs_offset", "mean_range"]


def note_features(notes, window_s=None):
    f = np.zeros(N_FEAT)
    if len(notes) < 3: return f
    dur = np.array([n["dur"] for n in notes]); pc = np.array([n["pc"] for n in notes])
    for p, d in zip(pc, dur): f[p] += d
    f[:12] /= f[:12].sum() or 1
    A, D = np.zeros((12, 12)), np.zeros((12, 12))
    for a, b in zip(notes, notes[1:]):
        if b["start"] - a["end"] > 0.5 or a["semitone"] == b["semitone"]: continue    # phrase boundary / repeat
        (A if b["semitone"] > a["semitone"] else D)[a["pc"], b["pc"]] += 1
    tot = A.sum() + D.sum()
    if tot: f[12:156], f[156:300] = (A / tot).ravel(), (D / tot).ravel()
    mv = [n["movement"] for n in notes]
    span = window_s or (notes[-1]["end"] - notes[0]["start"] + 1e-6)
    f[300:] = [np.mean([m == "oscillation" for m in mv]), np.mean([n["cycles"] for n in notes]),
               np.mean([m.startswith("glide") for m in mv]), dur.mean(), dur.std(), len(notes) / span,
               np.mean([abs(n["offset_cents"]) for n in notes]), np.mean([n["range_cents"] for n in notes])]
    return f


def window_notes(notes, t0, t1):
    return [n for n in notes if t0 <= n["start"] < t1]


def windows(notes, total_s, win_s=20.0, hop_s=10.0, min_notes=12):
    out, t = [], 0.0
    while t + min(win_s, total_s) <= total_s + 1e-6:
        w = window_notes(notes, t, t + win_s)
        if len(w) >= min_notes: out.append((t, t + win_s, w))
        t += hop_s
        if total_s <= win_s: break
    return out
