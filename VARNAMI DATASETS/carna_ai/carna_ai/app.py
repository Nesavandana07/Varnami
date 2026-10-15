#!/usr/bin/env python3
"""CARNA-AI web dashboard + JSON API.   python app.py  ->  http://127.0.0.1:5000"""
import os, tempfile, numpy as np
from flask import Flask, jsonify, request, send_from_directory
from carna import pipeline, composer, synth, audio
from carna.knowledge import load_ragas

app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024


def _enc(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, np.ndarray): return o.tolist()
    if isinstance(o, np.bool_): return bool(o)
    raise TypeError(type(o))
app.json.default = _enc


@app.get("/")
def index(): return send_from_directory("static", "index.html")


@app.get("/api/ragas")
def ragas():
    return jsonify([{"name": r.name, "arohanam": r.meta["arohanam"], "avarohanam": r.meta["avarohanam"], "type": r.meta["type"],
                     "vakra": r.meta["vakra"], "has_audio": r.meta["audio_match"] != "none", "expert_verified": r.meta["expert_verified"]}
                    for r in load_ragas().values()])


@app.post("/api/analyze")
def analyze():
    f = request.files.get("file")
    if not f: return jsonify(error="No audio file uploaded"), 400
    tonic = request.form.get("tonic_hz", type=float)
    secs = min(request.form.get("max_seconds", 90, type=int), 240)
    suffix = os.path.splitext(f.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        f.save(tmp.name)
    try:
        return jsonify(pipeline.analyse(tmp.name, tonic_hz=tonic, max_seconds=secs))
    except Exception as e:                      # unreadable audio, too little voiced material, ...
        return jsonify(error=f"{type(e).__name__}: {e}"), 422
    finally:
        os.unlink(tmp.name)


@app.get("/api/demo")
def demo():
    """Analyse a synthetic grammar-based clip (so the dashboard is usable without audio files)."""
    raga = request.args.get("raga", "Mohanam"); secs = request.args.get("seconds", 30, type=int); seed = request.args.get("seed", 1, type=int)
    mix = request.args.get("mix")                      # optional second raga -> film-style mixed clip
    if raga not in load_ragas(): return jsonify(error="unknown raga"), 400
    y, tonic = synth.synth_audio(raga, secs, seed=seed)
    if mix and mix in load_ragas():
        y2, _ = synth.synth_audio(mix, secs // 2, tonic=tonic, seed=seed + 7); y = np.concatenate([y[: len(y) * 2 // 3], y2])
    res = pipeline.analyse(y, max_seconds=None)
    res["demo"] = {"synthetic": True, "true_raga": raga, "mix": mix, "true_tonic_hz": tonic,
                   "note": "Synthetic audio generated from the sheet's scales - not real singing."}
    return jsonify(res)


@app.get("/api/compare")
def compare():
    a, b = request.args.get("a"), request.args.get("b"); R = load_ragas()
    if a not in R or b not in R: return jsonify(error="unknown raga"), 400
    return jsonify(composer.compare(a, b))


@app.post("/api/compose")
def compose():
    j = request.get_json(force=True); R = load_ragas()
    a, b = j.get("a"), j.get("b")
    if a not in R or b not in R: return jsonify(error="unknown raga"), 400
    out = composer.generate(a, b, int(j.get("length", 16)), float(j.get("blend", 0.5)), int(j.get("seed", 0)),
                            float(j.get("tonic_hz", 146.83)), float(j.get("bpm", 80)))
    out["compare"] = composer.compare(a, b)
    return jsonify(out)


if __name__ == "__main__":
    from carna import classify; classify.load_model()         # train bootstrap model on first run (~15 s)
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
