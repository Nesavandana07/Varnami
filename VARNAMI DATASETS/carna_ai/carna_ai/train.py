#!/usr/bin/env python3
"""Train the baseline raga classifier.

  python train.py --synthetic                       # grammar-only bootstrap (no audio needed)  -> models/baseline.joblib
  python train.py --audio-root /path/to/unzipped    # real varnam audio (folder that contains carnatic_varnam_1.1/)
                  [--synthetic-fill] [--estimate-tonic] [--max-seconds 240]

Real mode: singer-level split from data/audio_manifest.csv (suggested_split), pitch contours cached in cache/.
Evaluation is on held-out SINGERS (test = vignesh + dharini).  --synthetic-fill adds grammar-synthetic windows for the 9
pilot ragas that have no audio, so the model still knows all 16 labels (they are never evaluated on real audio)."""
import argparse, csv, json, joblib, numpy as np
from pathlib import Path
from sklearn.metrics import accuracy_score, classification_report
from carna import audio, classify
from carna.features import note_features, windows
from carna.knowledge import DATA, raga_names
from carna.swara import segment_notes

def real_windows(root, estimate_tonic, max_s, win_s=20.0):
    cache = Path("cache"); cache.mkdir(exist_ok=True); X, y, split, singer = [], [], [], []
    for m in csv.DictReader(open(DATA / "audio_manifest.csv")):
        p = Path(root) / m["path_in_zip"]
        if not p.exists(): print("missing", p); continue
        cp = cache / (Path(m["file"]).stem + f"_{max_s}.npz")
        if cp.exists(): d = np.load(cp); times, f0, dur, y_raw = d["t"], d["f0"], float(d["dur"]), None
        else:
            y_raw = audio.load_audio(str(p), max_s, 20.0)
            t, f0, _ = audio.extract_pitch(audio.denoise(y_raw)); f0 = audio.clean_contour(f0); dur = len(y_raw) / audio.SR
            np.savez(cp, t=t, f0=f0, dur=dur)
        tonic = audio.estimate_tonic(f0, y=y_raw) if (estimate_tonic and y_raw is not None) else float(m["tonic_hz"])
        notes = segment_notes(audio.to_relative_cents(f0, tonic))
        for _, _, w in windows(notes, dur, win_s, win_s / 2):
            X.append(note_features(w, win_s)); y.append(m["raga_in_your_list"]); split.append(m["suggested_split"]); singer.append(m["singer"])
        print(f"{m['raga_in_your_list']:14s} {m['singer']:18s} tonic {tonic:6.1f} notes {len(notes)}")
    return np.array(X), np.array(y), np.array(split), np.array(singer)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true"); ap.add_argument("--audio-root")
    ap.add_argument("--synthetic-fill", action="store_true"); ap.add_argument("--estimate-tonic", action="store_true")
    ap.add_argument("--max-seconds", type=int, default=240); ap.add_argument("--clips", type=int, default=40)
    a = ap.parse_args()
    if a.synthetic or not a.audio_root:
        _, rep = classify.train_and_save(a.clips); print(json.dumps(rep, indent=1)); return
    X, y, split, _ = real_windows(a.audio_root, a.estimate_tonic, a.max_seconds)
    tr, te = split == "train", split == "test"
    Xtr, ytr = X[tr], y[tr]
    if a.synthetic_fill:
        Xs, ys, _ = classify.synthetic_dataset(a.clips, seed=0); keep = ~np.isin(ys, np.unique(y))
        Xtr, ytr = np.vstack([Xtr, Xs[keep]]), np.concatenate([ytr, ys[keep]])
    clf = classify.train(Xtr, ytr); pred = clf.predict(X[te])
    rep = {"data": "REAL varnam audio" + (" + synthetic fill for ragas without audio" if a.synthetic_fill else ""),
           "n_train_windows": int(len(ytr)), "n_test_windows": int(te.sum()), "test_accuracy": float(accuracy_score(y[te], pred)),
           "report": classification_report(y[te], pred, output_dict=True, zero_division=0)}
    print(classification_report(y[te], pred, zero_division=0))
    joblib.dump({"clf": clf, "report": rep}, classify.REAL_MODEL_PATH)
    Path(classify.REAL_MODEL_PATH).with_suffix(".report.json").write_text(json.dumps(rep, indent=1))
    print("saved", classify.REAL_MODEL_PATH)

if __name__ == "__main__": main()
