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
    return jsonify([{
        "name": r.name,
        "arohanam": r.meta.get("arohanam", ""),
        "avarohanam": r.meta.get("avarohanam", ""),
        "type": r.meta.get("type", "Janya"),
        "melakarta_no": r.meta.get("melakarta_no_or_parent"),
        "parent_melakarta": r.meta.get("parent_melakarta", ""),
        "arohanam_class": r.meta.get("arohanam_class", ""),
        "avarohanam_class": r.meta.get("avarohanam_class", ""),
        "arohanam_swaras": r.meta.get("arohanam_swaras", 7),
        "avarohanam_swaras": r.meta.get("avarohanam_swaras", 7),
        "vakra": r.meta.get("vakra", "No"),
        "usage_band": r.meta.get("usage_band", "Common"),
        "pitch_classes": list(sorted(r.pcs)),
        "swaras": [r.names.get(p, "") for p in sorted(r.pcs)],
        "has_audio": r.meta.get("audio_match") != "none",
        "expert_verified": r.meta.get("expert_verified", "NO")
    } for r in load_ragas().values()])


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


@app.get("/api/glossary")
def glossary():
    from carna.knowledge import load_glossary
    return jsonify(load_glossary())


@app.get("/api/swaras")
def swaras():
    from carna.knowledge import load_swara_reference
    return jsonify(load_swara_reference())


@app.get("/api/raga/<name>")
def raga_details(name):
    R = load_ragas()
    if name not in R: return jsonify(error="unknown raga"), 404
    r = R[name]
    return jsonify({
        "name": r.name,
        "arohanam": r.meta.get("arohanam"),
        "avarohanam": r.meta.get("avarohanam"),
        "type": r.meta.get("type"),
        "melakarta_no": r.meta.get("melakarta_no_or_parent"),
        "parent_melakarta": r.meta.get("parent_melakarta"),
        "vakra": r.meta.get("vakra"),
        "arohanam_class": r.meta.get("arohanam_class"),
        "avarohanam_class": r.meta.get("avarohanam_class"),
        "pitch_classes": list(sorted(r.pcs)),
        "swaras": [r.names.get(p, "") for p in sorted(r.pcs)],
        "expert_verified": r.meta.get("expert_verified"),
        "usage_band": r.meta.get("usage_band", "Common")
    })


@app.post("/api/compose")
def compose():
    j = request.get_json(force=True); R = load_ragas()
    a, b = j.get("a"), j.get("b")
    if a not in R or b not in R: return jsonify(error="unknown raga"), 400
    lyrics_input = j.get("lyrics")
    out = composer.generate(a, b, int(j.get("length", 16)), float(j.get("blend", 0.5)), int(j.get("seed", 0)),
                            float(j.get("tonic_hz", 146.83)), float(j.get("bpm", 80)),
                            lyrics=lyrics_input)
    out["compare"] = composer.compare(a, b)
    return jsonify(out)


@app.post("/api/humming")
def analyze_humming():
    f = request.files.get("file")
    if not f: return jsonify(error="No audio file uploaded"), 400
    tonic = request.form.get("tonic_hz", type=float)
    secs = min(request.form.get("max_seconds", 60, type=int), 120)
    suffix = os.path.splitext(f.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        f.save(tmp.name)
    try:
        res = pipeline.analyse(tmp.name, tonic_hz=tonic, max_seconds=secs)
        res["is_humming"] = True
        return jsonify(res)
    except Exception as e:
        return jsonify(error=f"{type(e).__name__}: {e}"), 422
    finally:
        os.unlink(tmp.name)


@app.get("/api/samples")
def list_samples():
    """Returns curated demo samples with classical & cine context."""
    samples_dir = os.path.join(app.static_folder, "samples")
    meta = {
        "mohanam_varnam.mp3": {"title": "Ninnukori Varnam", "raga": "Mohanam", "tala": "Adi", "composer": "Ramnad Srinivasa Iyengar", "singer": "Prasanna", "tonic_hz": 146.83, "category": "carnatic"},
        "abhogi_varnam.mp3": {"title": "Evari Bodha Varnam", "raga": "Abhogi", "tala": "Adi", "composer": "Patnam Subramanya Iyer", "singer": "Dharini", "tonic_hz": 200.58, "category": "carnatic"},
        "sahana_varnam.mp3": {"title": "Karunimpa Varnam", "raga": "Sahana", "tala": "Adi", "composer": "Tiruvottiyur Tyagayya", "singer": "Sreevidya", "tonic_hz": 210.07, "category": "carnatic"}
    }
    out = []
    if os.path.exists(samples_dir):
        for f in sorted(os.listdir(samples_dir)):
            if f.endswith((".mp3", ".wav")):
                m = meta.get(f, {"title": f, "raga": "Unknown", "singer": "Artist", "tonic_hz": 146.83, "category": "carnatic"})
                out.append({"filename": f, "url": f"/static/samples/{f}", **m})
    return jsonify(out)


@app.get("/api/analyze-sample")
def analyze_sample():
    """Runs pipeline analysis directly on a server-hosted sample file."""
    name = request.args.get("sample")
    if not name: return jsonify(error="No sample specified"), 400
    sample_path = os.path.join(app.static_folder, "samples", os.path.basename(name))
    if not os.path.exists(sample_path): return jsonify(error="Sample file not found"), 404
    tonic = request.args.get("tonic_hz", type=float)
    secs = min(request.args.get("max_seconds", 60, type=int), 240)
    try:
        res = pipeline.analyse(sample_path, tonic_hz=tonic, max_seconds=secs)
        res["sample_name"] = name
        return jsonify(res)
    except Exception as e:
        return jsonify(error=f"{type(e).__name__}: {e}"), 422


@app.get("/api/raga/<name>/scale")
def raga_scale_audio(name):
    """Generates synthetic scale playback (Arohanam & Avarohanam) with tanpura drone."""
    R = load_ragas()
    if name not in R: return jsonify(error="unknown raga"), 404
    tonic = request.args.get("tonic_hz", 146.83, type=float)
    r = R[name]
    import io, base64, soundfile as sf
    from carna.synth import render_f0
    from carna.audio import SR, FPS
    seq = list(r.aro) + list(r.avaro[1:])
    f0_segs = []
    for st in seq:
        cents = st * 100.0
        dur_frames = max(2, int(0.55 * FPS))
        f0_segs.append(np.full(dur_frames, tonic * (2 ** (cents / 1200.0))))
    f0 = np.concatenate(f0_segs)
    y = render_f0(f0, drone_tonic=tonic, drone_db=-22)
    buf = io.BytesIO()
    sf.write(buf, y, SR, format="WAV", subtype="PCM_16")
    return jsonify({"raga": name, "tonic_hz": tonic, "wav_base64": base64.b64encode(buf.getvalue()).decode()})


@app.post("/api/contact")
def submit_contact():
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    message = (data.get("message") or "").strip()
    role = (data.get("role") or "Carnatic Student").strip()
    if not name or not email or not message:
        return jsonify(error="Please provide your name, email, and message."), 400
    return jsonify(status="ok", message=f"Thank you, {name}! Your message as a {role} has been received by the Varnami research team.")


@app.post("/api/feedback")
def submit_feedback():
    data = request.get_json(silent=True) or request.form
    rating = data.get("rating", 5)
    feedback = (data.get("feedback") or "").strip()
    return jsonify(status="ok", message="Thank you for supporting CARNA-AI research and providing feedback!")


if __name__ == "__main__":
    from carna import classify; classify.load_model()         # train bootstrap model on first run (~15 s)
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
