# CARNA-AI pilot — raga analysis pipeline, classifier, film-mix and composer prototype

```
pip install -r requirements.txt
python app.py            # http://127.0.0.1:5000  (first run trains the bootstrap model, ~15 s)
python -m pytest tests   # 16 tests, ~10 s
```

## Where each deliverable lives
| Deliverable | Code | Notes |
|---|---|---|
| 2 · Noise handling, pitch contour, tonic (Sa), relative pitch | `carna/audio.py` | high-pass + spectral gate → `librosa.pyin` → spike/gap cleaning → drone-aware Sa estimate → cents above Sa (octave kept). Essentia hook: `extract_pitch(engine="essentia")`. |
| 3 · Swara extraction + notation | `carna/swara.py` | semitone quantisation, short-run merging, per-note movement (steady / glide / oscillation, cycle count, start/end cents), raga-aware naming (G2 vs R3, N2 vs D3), text notation with `,` holds, `/ \ ~` marks, `.S` lower / `S'` upper octave. |
| 4 · Classifier + explanation | `carna/features.py`, `classify.py`, `explain.py`, `train.py` | RandomForest on pitch-class histogram + **directional** transition matrices + gamaka/intonation stats. Rule-based explanation: scale conformance, off-scale/missing swaras, grammar hit-rate, moves that separate winner from runner-up, prayoga matching. |
| 5 · Film-song mixed influence | `carna/film.py` | primary / secondary / other %, per-20 s window timeline, verdict. Same columns as `film_song_template.csv`. |
| 6 · Composer + dashboard | `carna/composer.py`, `app.py`, `static/index.html` | compare two ragas, constrained phrase (see below), WAV playback; dashboard has upload, pitch curve, swara timeline, confidence/film charts, composer. |
| Test material | `carna/synth.py` | grammar-based synthetic contours/audio with ground truth; also renders composer playback. |

## What has and has not been validated  (read this)
The pilot zip contains **no audio** (the varnam recordings are in the separate CompMusic zip) and the `prayogas`, `gamakas`, `film_songs` tables are empty. So:

* **Everything was tested on synthetic audio generated from the sheet's own scales.** Results (99%+ classification, 16/16 end-to-end) show the plumbing works and that the features can separate same-scale ragas *when the music follows the sheet's grammar*. They say **nothing** about real singing; expect a large drop.
* Segmentation on synthetic: ~86% of notes recovered at ~97% precision (fast 0.12 s notes are the misses).
* Tonic: 100% within 50 cents with a clear drone (−22 dB), ~87% with a faint one (−30 dB); **~6% without any drone** (voice-only is close to a guess). The API returns `tonic_warning` when the winner's margin is <0.5; type the Sa in Hz when you know it. Not yet checked on real recordings.
* Film mix weights are a heuristic (classifier probability × scale fit). Uncalibrated until annotated film songs exist.
* **No prayogas are shipped.** `explain.py` reports that none are loaded; it lists recurring scale-legal patterns clearly labelled "NOT expert prayogas". Fill `data/prayoga_template.csv` (set `verified_by_expert=Y`) and matching switches on automatically.
* Composer phrases use no gamaka (none verified). Constraints (starts/ends on Sa, in-scale, pivot on a shared swara, one colour swara per raga) are satisfied for all 240 ordered pairs × variations tested, but "satisfies the constraints" ≠ "sounds like a good Carnatic phrase" — needs your Music Domain Expert.
* Ragas sharing a scale (Harikambhoji/Kambhoji/Sahana; Kharaharapriya/Sriragam; Dheerasankarabharanam/Begada) can only be separated by directional movement/phrasing; expect these to be the first confusions on real audio.

## Run on the real varnam audio
```
unzip carnatic_varnam_1.1.zip -d /data/varnam            # must contain carnatic_varnam_1.1/Audio/*.mp3
python tests/eval_tonic.py --audio-root /data/varnam      # Sa-estimate accuracy vs manifest tonic_hz
python train.py --audio-root /data/varnam --synthetic-fill   # singer-level split (test = vignesh, dharini)
```
`train.py` saves `models/real.joblib`, which `app.py` then prefers over the synthetic bootstrap. The mp3 → manifest → split path was smoke-tested with generated mp3s; it has not run on the actual recordings. With 3–5 clips per raga the real-audio model is a pipeline test, not a trustworthy classifier.

## Needs expert input (Team Rule 4)
Verify the scales in `ragas_knowledge_base`; supply prayogas and gamaka definitions; annotate film songs; judge composer output.
