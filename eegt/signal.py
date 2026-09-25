"""Engineering QC and label-free transformations of numeric windows."""
from fractions import Fraction
import numpy as np
from scipy import signal
from .contract import NumericRecording


def window_quality(x, valid, rate, cfg):
    reasons = []
    if len(x) != round(2 * rate):
        reasons.append("INCOMPLETE")
    if not np.all(valid):
        reasons.append("INTEGRITY_OR_NONFINITE")
    if not np.all(np.isfinite(x)):
        if "INTEGRITY_OR_NONFINITE" not in reasons:
            reasons.append("INTEGRITY_OR_NONFINITE")
    if reasons:
        return reasons, None
    centered = x - x.mean()
    if x.std() < cfg["minimum_std_uv"]:
        reasons.append("FLAT")
    if np.ptp(x) > cfg["maximum_ptp_uv"]:
        reasons.append("HIGH_AMPLITUDE")
    line_ratio = None
    if rate / 2 > cfg["line_analysis_requires_native_nyquist_above_hz"]:
        f, p = signal.periodogram(centered, fs=rate, window="hann", detrend=False)
        total = p[(f >= 1) & (f <= min(70, rate / 2))].sum()
        if total > 0:
            line_ratio = float(max(p[(f >= a - 1) & (f <= a + 1)].sum() for a in (50, 60)) / total)
            if line_ratio > cfg["maximum_50_or_60hz_ratio"]:
                reasons.append("LINE_DOMINATED")
    return reasons, line_ratio


def iter_windows(recording: NumericRecording, protocol):
    rate = recording.sample_rate_hz
    n = round(protocol["window_seconds"] * rate)
    if not np.isclose(n / rate, 2.0):
        raise ValueError("protocol requires exact native two-second windows")
    sos = signal.butter(4, protocol["analysis_band_hz"], btype="bandpass", fs=rate, output="sos")
    ratio = Fraction(protocol["analysis_sample_rate_hz"] / rate).limit_denominator(10000)
    if not np.isclose(rate * ratio.numerator / ratio.denominator, protocol["analysis_sample_rate_hz"]):
        raise ValueError("analysis rate cannot be represented accurately")
    for channel in range(recording.samples_uv.shape[0]):
        for start in range(0, recording.samples_uv.shape[1], n):
            x = recording.samples_uv[channel, start:start + n]
            mask = recording.valid_samples[channel, start:start + n]
            reasons, line_ratio = window_quality(x, mask, rate, protocol["qc"])
            wave = None
            if not reasons:
                # Fixed physical padding avoids a different transient duration
                # at 250 and 500 Hz (SciPy's default is a fixed sample count).
                filtered = signal.sosfiltfilt(sos, x - x.mean(), padlen=round(.5 * rate))
                wave = signal.resample_poly(filtered, ratio.numerator, ratio.denominator)
                if wave.shape != (200,) or not np.all(np.isfinite(wave)):
                    raise ValueError("unexpected numerical transformation result")
            yield channel, start, reasons, line_ratio, wave


def normalized_waves(waves):
    x = waves - waves.mean(axis=1, keepdims=True)
    return x / np.maximum(np.sqrt(np.mean(x * x, axis=1, keepdims=True)), 1e-12)


def features(waves, method):
    """No labels, record names, participant fields or task context accepted."""
    x = np.asarray(waves, dtype=float)
    if x.ndim != 2 or x.shape[1] != 200 or not np.all(np.isfinite(x)):
        raise ValueError("features require finite 200-sample numerical windows")
    if method == "waveform":
        return normalized_waves(x)
    if method == "spectrum":
        f, p = signal.periodogram(x, fs=100, window="hann", axis=1)
        cells = [p[:, (f >= max(1, c - .5)) & (f < min(40.5, c + .5))].sum(axis=1) * .5
                 for c in range(1, 41)]
        return np.log10(np.maximum(np.stack(cells, axis=1), 1e-12))
    if method == "time_frequency":
        # Four fixed subwindows; 2-Hz bins reflect duration, not human EEG labels.
        parts = x.reshape(-1, 4, 50)
        f, p = signal.periodogram(parts, fs=100, window="hann", axis=2)
        return np.log10(np.maximum(p[:, :, (f >= 2) & (f <= 40)], 1e-12)).reshape(len(x), -1)
    raise ValueError("unknown feature method")


def surrogate(waves, kind, seed=610):
    rng = np.random.default_rng(seed)
    if kind == "sample_shuffle":
        return np.take_along_axis(waves, np.argsort(rng.random(waves.shape), axis=1), axis=1)
    if kind == "phase_randomized":
        fft = np.fft.rfft(waves, axis=1)
        phases = rng.uniform(-np.pi, np.pi, fft.shape)
        phases[:, 0] = 0
        phases[:, -1] = 0  # DC and real Nyquist must remain real and unchanged.
        return np.fft.irfft(fft * np.exp(1j * phases), n=waves.shape[1], axis=1)
    raise ValueError("unknown control")
