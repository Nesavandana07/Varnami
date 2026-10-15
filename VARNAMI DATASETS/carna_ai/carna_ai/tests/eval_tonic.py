"""Tonic-estimation accuracy.  `--synthetic`: known-tonic synthetic audio.  `--audio-root DIR`: real varnam recordings,
ground truth = tonic_hz in data/audio_manifest.csv (skips qc_flag=tonic_unverified)."""
import sys, argparse, csv, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carna import audio, synth
from carna.knowledge import raga_names, DATA

def err_cents(est, true): return 1200 * np.log2(est / true)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--synthetic", action="store_true"); ap.add_argument("--audio-root"); ap.add_argument("--seconds", type=int, default=60)
    a = ap.parse_args(); rows = []
    if a.synthetic:
        for i, r in enumerate(raga_names()):
            y, tonic = synth.synth_audio(r, 25, seed=100 + i, noise_db=-30)
            rows.append((r, tonic, audio.analyse_audio(y, max_seconds=None)["tonic_hz"]))
    if a.audio_root:
        for m in csv.DictReader(open(DATA / "audio_manifest.csv")):
            if m["qc_flag"] != "ok": continue
            p = Path(a.audio_root) / m["path_in_zip"]
            if p.exists(): rows.append((m["raga_in_your_list"] + "/" + m["singer"], float(m["tonic_hz"]), audio.analyse_audio(str(p), max_seconds=a.seconds, offset=30)["tonic_hz"]))
    for n, t, e in rows: print(f"{n:34s} true {t:7.2f}  est {e:7.2f}  err {err_cents(e, t):8.1f}c")
    E = np.array([abs(err_cents(e, t)) for _, t, e in rows])
    fold = np.minimum(E % 1200, 1200 - E % 1200)
    print(f"n={len(E)}  exact (<50c): {np.mean(E < 50):.0%}   pitch-class right, octave maybe wrong (<50c folded): {np.mean(fold < 50):.0%}")

if __name__ == "__main__": main()
