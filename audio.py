"""Stage 2: noise handling, pitch contour extraction, tonic (Sa) estimation, normalisation to relative cents.

Uses librosa (pyin). Essentia's PredominantPitchMelodia is a drop-in alternative for polyphonic film audio
(see `extract_pitch(engine="essentia")`); it is optional and only used if essentia is installed.
"""
import numpy as np, librosa, scipy.signal as sps
from scipy.ndimage import gaussian_filter1d, median_filter

SR, HOP, FRAME = 22050, 256, 2048
FPS = SR / HOP


def load_audio(path, max_seconds=None, offset=0.0):
    y, _ = librosa.load(path, sr=SR, mono=True, offset=offset, duration=max_seconds)
    return y


def denoise(y, sr=SR, hp_hz=60, noise_pct=10, over=1.5, floor=0.05):
    """High-pass (rumble/hum) + spectral gating. Noise profile = mean spectrum of the quietest `noise_pct`% frames."""
    if len(y) < 2 * FRAME: return y
    sos = sps.butter(4, hp_hz, "hp", fs=sr, output="sos")
    y = sps.sosfiltfilt(sos, y)
    S = librosa.stft(y, n_fft=FRAME, hop_length=HOP)
    mag, ph = np.abs(S), np.angle(S)
    e = mag.sum(0)
    quiet = e <= np.percentile(e, noise_pct)
    noise = mag[:, quiet].mean(1, keepdims=True)
    clean = np.maximum(mag - over * noise, floor * mag)          # soft floor limits musical-noise artefacts
    out = librosa.istft(clean * np.exp(1j * ph), hop_length=HOP, length=len(y))
    peak = np.max(np.abs(out)) or 1.0
    return (out / peak).astype(np.float32)


def extract_pitch(y, sr=SR, fmin=80.0, fmax=900.0, engine="librosa", voicing=0.5):
    """Returns (times, f0_hz with NaN for unvoiced, voiced_prob)."""
    if engine == "essentia":
        import essentia.standard as es
        f0, conf = es.PredominantPitchMelodia(sampleRate=sr, hopSize=HOP, frameSize=FRAME,
                                              minFrequency=fmin, maxFrequency=fmax)(y.astype(np.float32))
        f0 = np.where(f0 > 0, f0, np.nan)
        return np.arange(len(f0)) * HOP / sr, f0, np.asarray(conf)
    f0, _, vp = librosa.pyin(y, fmin=fmin, fmax=fmax, sr=sr, frame_length=FRAME, hop_length=HOP, fill_na=np.nan)
    f0 = np.where(vp >= voicing, f0, np.nan)
    return librosa.times_like(f0, sr=sr, hop_length=HOP), f0, vp


def clean_contour(f0, fps=FPS, max_gap_s=0.08, median_frames=5, max_jump_cents=900):
    """Remove octave-error spikes, light median smoothing, interpolate short gaps (gamaka is continuous)."""
    f0 = f0.astype(float).copy()
    c = 1200 * np.log2(f0)
    # single-frame octave-error spikes: far from both neighbours while the neighbours agree with each other
    a_, m_, b_ = c[:-2], c[1:-1], c[2:]
    spike = (np.abs(m_ - a_) > max_jump_cents) & (np.abs(m_ - b_) > max_jump_cents) & (np.abs(a_ - b_) < max_jump_cents / 2)
    c[1:-1][spike] = np.nan
    ok = ~np.isnan(c)
    if ok.sum() > median_frames:
        fill = np.where(ok, c, np.interp(np.arange(len(c)), np.where(ok)[0], c[ok]))
        sm = median_filter(fill, size=median_frames, mode="nearest")
        c = np.where(ok, sm, np.nan)
    # interpolate gaps shorter than max_gap_s
    n, i, mg = len(c), 0, int(max_gap_s * fps)
    while i < n:
        if np.isnan(c[i]):
            j = i
            while j < n and np.isnan(c[j]): j += 1
            if 0 < i and j < n and (j - i) <= mg: c[i:j] = np.linspace(c[i - 1], c[j], j - i + 2)[1:-1]
            i = j
        else: i += 1
    return 2 ** (c / 1200)


REF_HZ = 65.406  # C2: reference for folded cent histograms


def drone_profile(y, sr=SR, bin_cents=10, n_oct=4):
    """Folded long-term spectrum using the MEDIAN over time of a fine CQT: a steady tanpura drone (Sa, Pa) survives,
    the moving voice does not.  Must be computed BEFORE denoise(), whose gate would treat the drone as noise."""
    bpo = 1200 // bin_cents
    C = np.abs(librosa.cqt(y, sr=sr, hop_length=1024, fmin=REF_HZ, n_bins=bpo * n_oct, bins_per_octave=bpo))
    prof = np.median(C, axis=1)
    F = prof.reshape(n_oct, bpo).sum(0)
    F = gaussian_filter1d(F, 15 / bin_cents, mode="wrap")
    return F / (F.max() or 1.0)


def voice_profile(f0, bin_cents=10):
    v = f0[~np.isnan(f0)]
    nb = 1200 // bin_cents
    H = np.bincount(((1200 * np.log2(v / REF_HZ) % 1200) // bin_cents).astype(int) % nb, minlength=nb).astype(float)
    H = gaussian_filter1d(H, 25 / bin_cents, mode="wrap")
    return H / (H.max() or 1.0)


def estimate_tonic(f0, y=None, lo=100.0, hi=300.0, bin_cents=10, w_drone=1.0, w_voice=0.1, return_debug=False):
    """Estimate Sa (Hz).  Each candidate Sa is scored by its own salience plus small bonuses for a Pa (+702c), Ma (+498c) or Ni (+1100c)
    partner above it, using the drone profile (if audio is given) and, with low weight, the voice histogram.
    Partner weights are deliberately small: a large Pa bonus lets the Ma class "borrow" Sa's energy (Ma's Pa is Sa).
    Tuned on synthetic drones only (91% at drone -22/-30 dB; 100% at -22 dB) - validate on real audio with tests/eval_tonic.py.
    Candidates are limited to a plausible Sa range; the octave is the one that puts the singer's median ~1.35x above Sa.
    Heuristic: always allow a user override when the shruti is known."""
    v = f0[~np.isnan(f0)]
    if len(v) < 50: raise ValueError("No pitched (voiced) material found - please upload a vocal or melodic recording")
    nb = 1200 // bin_cents
    pa, ma, ni = (int(round(x / bin_cents)) for x in (702, 498, 1100))
    def tonic_score(P): return P + 0.2 * np.roll(P, -pa) + 0.1 * np.roll(P, -ma) + 0.1 * np.roll(P, -ni)
    S = w_voice * tonic_score(voice_profile(f0, bin_cents))
    if y is not None: S = S + w_drone * tonic_score(drone_profile(y, bin_cents=bin_cents) ** 2)   # squaring sharpens dominant drone peaks
    cand = []
    for b in range(nb):
        f = REF_HZ * 2 ** (b * bin_cents / 1200); f *= 2 ** np.ceil(np.log2(lo / f))
        if f <= hi: cand.append(b)
    best = max(cand, key=lambda b: S[b])
    f_fold = REF_HZ * 2 ** (best * bin_cents / 1200)
    k = round(np.log2(float(np.median(v)) / f_fold / 1.35))
    tonic = float(f_fold * 2 ** k)
    # confidence: how far the winner stands above the best candidate in a *different* pitch class (>60c away)
    rival = max((S[b] for b in cand if min(abs(b - best), nb - abs(b - best)) * bin_cents > 60), default=0.0)
    margin = float((S[best] - rival) / (S[best] or 1.0))
    return (tonic, {"score": S, "best_bin": best, "margin": margin}) if return_debug else tonic


def to_relative_cents(f0, tonic):
    """Absolute Hz -> cents above Sa (octave information retained: 0 = Sa, 1200 = upper Sa, -500 = lower Pa)."""
    return 1200 * np.log2(f0 / tonic)


def analyse_audio(path_or_y, tonic_hz=None, max_seconds=90, engine="librosa", offset=0.0, do_denoise=True):
    y_raw = load_audio(path_or_y, max_seconds, offset) if isinstance(path_or_y, str) else path_or_y
    y = denoise(y_raw) if do_denoise else y_raw
    t, f0, vp = extract_pitch(y, engine=engine)
    f0 = clean_contour(f0)
    tmargin = None
    if tonic_hz: tonic = float(tonic_hz)
    else: tonic, dbg = estimate_tonic(f0, y=y_raw, return_debug=True); tmargin = dbg["margin"]
    return {"times": t, "f0": f0, "cents": to_relative_cents(f0, tonic), "tonic_hz": tonic,
            "tonic_source": "user" if tonic_hz else "estimated", "tonic_margin": tmargin, "duration_s": len(y) / SR,
            "voiced_frac": float(np.mean(~np.isnan(f0)))}


