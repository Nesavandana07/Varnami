import sys, itertools, difflib
from pathlib import Path
import numpy as np, pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carna import synth, audio, swara, classify, explain, film, composer, knowledge
from carna.audio import to_relative_cents

RAGAS = knowledge.raga_names()


def notes_for(raga, seconds=40, seed=0, tonic=150.0):
    f0, t, _ = synth.synth_contour(raga, seconds, tonic=tonic, seed=seed)
    return swara.segment_notes(to_relative_cents(f0, t)), seconds


def test_knowledge_base():
    assert len(RAGAS) == 16 and knowledge.load_prayogas() == {}          # prayogas intentionally empty until expert-verified
    assert knowledge.load_ragas()["Kharaharapriya"].names[3] == "G2"     # raga context resolves G2 vs R3


@pytest.mark.parametrize("raga", ["Mohanam", "Sahana", "Begada", "Kharaharapriya"])
def test_segmentation_recovers_ground_truth(raga):
    f0, t, truth = synth.synth_contour(raga, 20, seed=3)
    got = swara.segment_notes(to_relative_cents(f0, t))
    a, b = [n[0] for n in truth], [g["semitone"] for g in got]
    matched = sum(m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    assert matched / len(a) > 0.75 and matched / len(b) > 0.9


def test_notation_has_movement_marks_and_octaves():
    n, _ = notes_for("Mohanam", 15)
    text = swara.to_notation(n, raga="Mohanam")
    assert any(c in text for c in "/\\~") and ("'" in text or "." in text)


@pytest.mark.parametrize("raga", ["Mohanam", "Hanumatodi", "Bhairavi"])
def test_audio_pipeline_tonic_and_class(raga):
    y, tonic = synth.synth_audio(raga, 30, seed=11, noise_db=-30)
    a = audio.analyse_audio(y, max_seconds=None)
    assert abs(1200 * np.log2(a["tonic_hz"] / tonic)) < 30
    from carna import pipeline
    assert pipeline.analyse_notes_from_cents(a["cents"], a["duration_s"], a["tonic_hz"])["classification"]["predicted"] == raga


def test_tonic_override_is_respected():
    y, tonic = synth.synth_audio("Mohanam", 12, seed=1)
    assert audio.analyse_audio(y, tonic_hz=123.0, max_seconds=None)["tonic_source"] == "user"


def test_classifier_heldout_synthetic():
    ok = 0
    for i, r in enumerate(RAGAS):
        n, tot = notes_for(r, seed=900 + i)
        probs, _ = classify.predict_proba(n, tot)
        ok += max(probs, key=probs.get) == r
    assert ok >= 14                      # synthetic only: proves plumbing, NOT real-world accuracy


def test_explanation_flags_unloaded_prayogas_and_shared_scales():
    n, tot = notes_for("Sahana", seed=5)
    probs, _ = classify.predict_proba(n, tot)
    ex = explain.explain(n, probs)
    text = " ".join(e["text"] for e in ex["evidence"])
    assert "No expert-verified prayogas" in text and ex["prayogas"]["n_loaded"] == 0


def test_prayoga_matching_with_fixture(monkeypatch):
    n, _ = notes_for("Mohanam", seed=2)
    seq = [x["pc"] for x in n[:12]]
    # build a fixture phrase from three consecutive DISTINCT notes actually present in the contour
    i = next(k for k in range(len(seq) - 2) if seq[k] != seq[k + 1] != seq[k + 2])
    pcs = seq[i:i + 3]
    fake = {"Mohanam": [{"id": "fixture", "swaras": "x", "pcs": pcs, "characteristic": "Y"}]}
    monkeypatch.setattr(explain, "load_prayogas", lambda: fake)
    assert explain.match_prayogas(n, "Mohanam")["hits"][0]["count"] >= 1


def test_film_single_vs_mixed():
    n, tot = notes_for("Kharaharapriya", seed=4)
    probs, wp = classify.predict_proba(n, tot)
    single = film.influence(n, probs, wp)
    assert single["primary"]["raga"] == "Kharaharapriya" and single["primary"]["pct"] >= 60
    parts, off = [], 0.0
    for i, r in enumerate(["Mohanam", "Hanumatodi", "Kharaharapriya"]):
        nn, s = notes_for(r, 20, seed=40 + i)
        for x in nn: x["start"] += off; x["end"] += off
        parts += nn; off += s
    probs, wp = classify.predict_proba(parts, off)
    mixed = film.influence(parts, probs, wp)
    assert mixed["primary"]["pct"] < single["primary"]["pct"] and mixed["secondary"]["raga"]
    assert abs(mixed["primary"]["pct"] + mixed["secondary"]["pct"] + mixed["other_pct"] - 100) < 0.5


def test_composer_constraints_all_pairs():
    for a, b in itertools.permutations(RAGAS, 2):
        for seed in (0, 1):
            g = composer.generate(a, b, 16, 0.5, seed, with_audio=False)
            assert all(g["checks"].values()), (a, b, seed, g["checks"])


def test_composer_audio_is_wav():
    import base64
    g = composer.generate("Hamsadhwani", "Ahiri", 12, 0.5, 1)
    assert base64.b64decode(g["wav_base64"])[:4] == b"RIFF"
    c = composer.compare("Hamsadhwani", "Ahiri")
    assert c["jaccard"] == 0.333 and c["shared_semitones"] == [0, 4, 7]    # matches the dataset README example
