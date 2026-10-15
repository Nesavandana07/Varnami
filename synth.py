"""Grammar-based synthetic material.  NOT real Carnatic singing: phrases are random walks over the raga's
arohanam/avarohanam from the pilot sheet, with GENERIC ornaments (slides, oscillations).  Used to (a) test
every pipeline stage with known ground truth and (b) bootstrap a grammar-only baseline until real audio is used.
Also renders note lists to audio for the composer's playback."""
import numpy as np
from .knowledge import load_ragas
from .audio import SR, HOP, FPS

_rng = lambda s: s if isinstance(s, np.random.Generator) else np.random.default_rng(s)


def ladders(raga):
    """Traversal ladders over octaves -1..+1 (drops the repeated S' so octaves chain)."""
    R = load_ragas()[raga]
    up = [x + 12 * o for o in (-1, 0, 1) for x in R.aro[:-1]]
    down = [x + 12 * o for o in (1, 0, -1) for x in R.avaro[1:]]
    return {"up": up, "down": down}


def random_phrase_notes(raga, n_notes, rng, lo=-12, hi=19):
    """List of (abs_semitone, duration_s, ornament): runs along aro when ascending, along avaro when descending."""
    L, cur, notes = ladders(raga), int(rng.choice([0, 7, 12])), []
    while len(notes) < n_notes:
        lad = L["up" if rng.random() < 0.5 else "down"]
        idx = int(np.argmin([abs(x - cur) for x in lad]))
        for _ in range(int(rng.integers(2, 7))):
            idx += 1
            if idx >= len(lad) or not lo <= lad[idx] <= hi: cur = int(rng.choice([0, 7, 12])); break
            cur = lad[idx]
            dur = float(np.clip(rng.lognormal(-1.4, 0.55), 0.12, 1.2))
            notes.append((cur, dur, str(rng.choice(["steady", "osc", "slide"], p=[.5, .3, .2]))))
    return notes[:n_notes]


def notes_to_contour(notes, tonic, fps=FPS, rng=None, jitter_cents=6):
    """Frame-level f0 (Hz) with generic ornaments + intonation jitter."""
    rng = _rng(rng if rng is not None else 0)
    segs, prev = [], None
    for st, dur, orn in notes:
        n = max(2, int(dur * fps)); t = np.arange(n) / fps
        c = np.full(n, st * 100.0)
        if orn == "osc":
            c += rng.uniform(25, 70) * np.sin(2 * np.pi * rng.uniform(4.5, 6.5) * t)
        if (orn == "slide" or rng.random() < 0.3) and prev is not None:
            m = max(1, int(n * rng.uniform(.15, .4)))
            c[:m] = np.linspace(prev * 100.0, st * 100.0, m)
        segs.append(c); prev = st
    c = np.concatenate(segs)
    c += gaussian_noise(len(c), jitter_cents, rng)
    return tonic * 2 ** (c / 1200)


def gaussian_noise(n, s, rng):
    from scipy.ndimage import gaussian_filter1d
    return gaussian_filter1d(rng.normal(0, s * 3, n), 2)


def synth_contour(raga, seconds=30, tonic=None, seed=0, fps=FPS):
    rng = np.random.default_rng(seed)
    tonic = tonic or float(rng.uniform(110, 240))
    notes, tot = [], 0.0
    while tot < seconds:
        chunk = random_phrase_notes(raga, 12, rng); notes += chunk; tot += sum(d for _, d, _ in chunk)
    f0 = notes_to_contour(notes, tonic, fps, rng)[: int(seconds * fps)]
    return f0, tonic, notes


def degrade_contour(f0, rng, dropout=0.04, octave_err=0.01):
    """Mimic pitch-tracker faults for training robustness: unvoiced dropouts and octave errors."""
    f0 = f0.copy(); n = len(f0)
    for _ in range(int(dropout * n / 8)): i = rng.integers(0, n); f0[i:i + rng.integers(2, 12)] = np.nan
    for _ in range(int(octave_err * n / 3)): i = rng.integers(0, n); f0[i:i + rng.integers(1, 4)] *= rng.choice([.5, 2.])
    return f0


# ---------------------------------------------------------------- audio rendering
def render_f0(f0, sr=SR, hop=HOP, harmonics=(1, .5, .3, .15, .08), drone_tonic=None, drone_db=-22, noise_db=None, seed=0):
    rng = np.random.default_rng(seed)
    f = np.nan_to_num(f0, nan=0.0)
    voiced = (f > 0).astype(float)
    n = len(f) * hop
    ft = np.interp(np.arange(n), np.arange(len(f)) * hop, f)
    env = np.interp(np.arange(n), np.arange(len(f)) * hop, gaussian_smooth(voiced, 3))
    ph = 2 * np.pi * np.cumsum(ft) / sr
    y = sum(a * np.sin(k * ph) for k, a in zip(range(1, len(harmonics) + 1), harmonics)) * env * 0.5
    if drone_tonic:
        t = np.arange(n) / sr; g = 10 ** (drone_db / 20)
        y += g * sum(w * np.sin(2 * np.pi * drone_tonic * r * t) for r, w in ((1, 1), (1.5, .8), (2, .6), (.5, .5)))
    if noise_db is not None: y += 10 ** (noise_db / 20) * rng.normal(0, 1, n)
    return (y / (np.max(np.abs(y)) + 1e-9) * 0.9).astype(np.float32)


def gaussian_smooth(x, s):
    from scipy.ndimage import gaussian_filter1d
    return gaussian_filter1d(x, s)


def synth_audio(raga, seconds=20, tonic=None, seed=0, noise_db=-35, drone_db=-22):
    f0, tonic, notes = synth_contour(raga, seconds, tonic, seed)
    return render_f0(f0, drone_tonic=tonic, drone_db=drone_db, noise_db=noise_db, seed=seed), tonic
