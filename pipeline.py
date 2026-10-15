"""End-to-end analysis: audio -> pitch -> tonic -> swaras -> notation -> raga + explanation -> film-song mix."""
import numpy as np
from . import audio, swara, classify, explain, film


def analyse_notes_from_cents(cents, total_s, tonic, extra=None, fps=audio.FPS):
    notes = swara.segment_notes(cents, fps=fps)
    if len(notes) < 5: raise ValueError("Too few stable notes detected - is this a vocal/melodic recording?")
    probs, wprobs = classify.predict_proba(notes, total_s)
    ex = explain.explain(notes, probs)
    raga = ex["raga"]
    out = {"tonic_hz": tonic, "duration_s": total_s, "n_notes": len(notes),
           "notes": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in n.items() if k != "candidates"}
                     for n in swara.label_notes(notes, raga)],
           "notation": swara.to_notation(notes, raga=raga),
           "classification": {"top": [{"raga": r, "confidence": round(p, 4)} for r, p in sorted(probs.items(), key=lambda kv: -kv[1])[:6]],
                              "predicted": raga, "confidence": round(ex["confidence"], 4), "margin": round(ex["margin"], 4)},
           "explanation": ex, "film": film.influence(notes, probs, wprobs)}
    if extra: out.update(extra)
    return out


def downsample_pitch(times, cents, max_points=3000):
    step = max(1, len(times) // max_points)
    t, c = times[::step], cents[::step]
    return {"t": [round(float(x), 3) for x in t], "cents": [None if np.isnan(x) else round(float(x), 1) for x in c]}


def analyse(source, tonic_hz=None, max_seconds=90, engine="librosa"):
    a = audio.analyse_audio(source, tonic_hz=tonic_hz, max_seconds=max_seconds, engine=engine)
    m = a.get("tonic_margin")
    extra = {"tonic_source": a["tonic_source"], "tonic_margin": None if m is None else round(m, 2),
             "tonic_warning": (m is not None and m < 0.5) and
             "Sa estimate is low-confidence (no clear drone / ambiguous). Enter the known Sa in Hz and re-run: every swara label depends on it.",
             "voiced_frac": round(a["voiced_frac"], 3),
             "pitch": downsample_pitch(a["times"], a["cents"])}
    return analyse_notes_from_cents(a["cents"], a["duration_s"], a["tonic_hz"], extra)
