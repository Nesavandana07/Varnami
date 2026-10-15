"""Stage 4a: baseline raga classifier (scikit-learn RandomForest on swara + contour features).
Trained either on grammar-synthetic contours (default bootstrap) and/or real varnam audio (train.py --audio-root)."""
import json, joblib, numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from .features import note_features, windows, N_FEAT
from .knowledge import raga_names
from .swara import segment_notes
from .audio import to_relative_cents, FPS
from . import synth

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODEL_DIR / "baseline.joblib"           # synthetic-grammar bootstrap
REAL_MODEL_PATH = MODEL_DIR / "real.joblib"          # trained by train.py --audio-root (preferred when present)


def synthetic_dataset(clips_per_raga=40, clip_s=40, seed=0, win_s=20.0):
    X, y, g = [], [], []
    names = raga_names()
    for ri, r in enumerate(names):
        for c in range(clips_per_raga):
            rng = np.random.default_rng(seed * 100003 + ri * 1009 + c)
            f0, tonic, _ = synth.synth_contour(r, clip_s, seed=int(rng.integers(1 << 30)))
            f0 = synth.degrade_contour(f0, rng)
            notes = segment_notes(to_relative_cents(f0, tonic))
            for t0, t1, w in windows(notes, clip_s, win_s, win_s / 2):
                X.append(note_features(w, win_s)); y.append(r); g.append(f"{r}-{c}")
    return np.array(X), np.array(y), np.array(g)


def train(X, y, seed=0):
    clf = RandomForestClassifier(n_estimators=300, min_samples_leaf=2, class_weight="balanced", n_jobs=-1, random_state=seed)
    return clf.fit(X, y)


def train_and_save(clips_per_raga=40, path=MODEL_PATH):
    Xtr, ytr, _ = synthetic_dataset(clips_per_raga, seed=0)
    Xte, yte, _ = synthetic_dataset(max(8, clips_per_raga // 4), seed=1)       # different seeds => unseen clips
    clf = train(Xtr, ytr)
    pred = clf.predict(Xte); labels = clf.classes_
    report = {"data": "SYNTHETIC grammar-generated contours (not real singing)", "n_train_windows": len(ytr),
              "n_test_windows": len(yte), "test_accuracy": float(accuracy_score(yte, pred)),
              "per_raga_recall": {l: float(np.mean(pred[yte == l] == l)) for l in labels},
              "confusions": {}}
    cm = confusion_matrix(yte, pred, labels=labels)
    for i in range(len(labels)):
        for j in range(len(labels)):
            if i != j and cm[i, j]: report["confusions"][f"{labels[i]} -> {labels[j]}"] = int(cm[i, j])
    path.parent.mkdir(exist_ok=True)
    joblib.dump({"clf": clf, "report": report}, path)
    (path.with_suffix(".report.json")).write_text(json.dumps(report, indent=1))
    return clf, report


_cache = {}
def load_model(path=None, auto_train=True):
    path = path or (REAL_MODEL_PATH if REAL_MODEL_PATH.exists() else MODEL_PATH)
    if "m" not in _cache:
        if not Path(path).exists():
            if not auto_train: raise FileNotFoundError(path)
            train_and_save()
        _cache["m"] = joblib.load(path)
    return _cache["m"]


def predict_proba(notes, total_s, win_s=20.0):
    """Window-averaged class probabilities. Returns (dict raga->prob, per-window list)."""
    m = load_model(); clf = m["clf"]
    ws = windows(notes, total_s, win_s, win_s / 2) or [(0, total_s, notes)]
    P = clf.predict_proba(np.array([note_features(w, min(win_s, total_s)) for _, _, w in ws]))
    mean = P.mean(0)
    return dict(zip(clf.classes_, map(float, mean))), [{"t0": a, "t1": b, "probs": dict(zip(clf.classes_, map(float, p)))} for (a, b, _), p in zip(ws, P)]
