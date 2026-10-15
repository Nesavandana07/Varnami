"""Stage 5: multi-candidate raga influence for film songs.  No single label is forced: each pilot raga gets a weight
from (a) window-averaged classifier probability and (b) how well the song's overall swara usage fits that raga's scale
(coverage of sung time x recall of the raga's swaras).  Weights are normalised to 100%.  Heuristic: no film-song labels
exist yet (film_song_template.csv is empty), so weights are uncalibrated."""
import numpy as np
from collections import defaultdict
from .knowledge import load_ragas, DEFAULT_NAMES


def usage(notes):
    u, tot = defaultdict(float), sum(n["dur"] for n in notes) or 1.0
    for n in notes: u[n["pc"]] += n["dur"] / tot
    return u


def scale_fit(notes, present=0.03):
    u = usage(notes); out = {}
    for name, R in load_ragas().items():
        cov = sum(v for p, v in u.items() if p in R.pcs)
        rec = float(np.mean([min(1.0, u.get(p, 0) / present) for p in R.pcs]))
        out[name] = (cov ** 6) * (rec ** 2)
    return out


def influence(notes, probs, window_probs=None, alpha=0.5, temp=0.6, min_pct=5.0):
    fit = scale_fit(notes)
    raw = {r: (max(probs.get(r, 0), 1e-6) ** alpha) * (max(fit[r], 1e-6) ** (1 - alpha)) for r in fit}
    w = {r: v ** (1 / temp) for r, v in raw.items()}; z = sum(w.values())
    pct = sorted(((r, 100 * v / z) for r, v in w.items()), key=lambda kv: -kv[1])
    top = [(r, p) for r, p in pct if p >= min_pct][:3] or pct[:1]
    prim, sec = top[0], (top[1] if len(top) > 1 else (None, 0.0))
    other = 100 - prim[1] - sec[1]          # same definition as film_song_template.csv (primary/secondary/other)
    verdict = ("single raga dominant" if prim[1] >= 75 else "primary raga with secondary influence" if prim[1] >= 45 and sec[0]
               else "mixed / no dominant raga")
    timeline = []
    for w_ in window_probs or []:
        r, p = max(w_["probs"].items(), key=lambda kv: kv[1]); timeline.append({"t0": w_["t0"], "t1": w_["t1"], "raga": r, "p": p})
    u = usage(notes); allp = set().union(*[R.pcs for R in load_ragas().values()])
    return {"primary": {"raga": prim[0], "pct": round(prim[1], 1)}, "secondary": {"raga": sec[0], "pct": round(sec[1], 1)},
            "other_pct": round(other, 1), "weights": [{"raga": r, "pct": round(p, 1)} for r, p in pct[:6]],
            "verdict": verdict, "window_timeline": timeline,
            "swara_usage": {DEFAULT_NAMES[p]: round(v, 3) for p, v in sorted(u.items())},
            "note": "Heuristic weights from scale fit + classifier; uncalibrated until annotated film songs exist."}
