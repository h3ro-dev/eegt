"""Label-blind, sensor-space transition measurements for continuous EEG.

Only NumPy and SciPy are required. The functions neither infer physiological
states nor accept identity or task metadata. See METHODS.md for estimands and
limits before comparing results across recordings or acquisition setups.
"""

from __future__ import annotations

import math
from bisect import bisect_left

import numpy as np
from scipy import signal


_MORPH_BASE = ("log_rms_uv", "log_hjorth_mobility_per_s",
               "hjorth_complexity", "autocorr_100ms")
_SPECTRUM_BASE = tuple(f"log_power_{low:02d}_{min(low + 2, 40):02d}_hz"
                       for low in range(1, 40, 2))
_COORD_NAMES = ("sensor_corr_median", "sensor_corr_iqr",
                "sensor_abs_corr_median", "sensor_lead_eigenvalue_fraction",
                "sensor_effective_rank_fraction")
_FEATURE_NAMES = {
    "morphology": [f"{name}_{summary}" for summary in ("median", "iqr")
                   for name in _MORPH_BASE],
    "spectrum": [f"{name}_{summary}" for summary in ("median", "iqr")
                 for name in _SPECTRUM_BASE],
    "coordination": list(_COORD_NAMES),
}


def _numeric_matrix(value, name, *, finite=False):
    array = np.asarray(value)
    if array.ndim != 2 or not np.issubdtype(array.dtype, np.number) or np.iscomplexobj(array):
        raise ValueError(f"{name} must be a real numeric 2-D array")
    result = np.asarray(array, dtype=np.float64)
    if finite and not np.isfinite(result).all():
        raise ValueError(f"{name} must be finite")
    return result


def _positive(value, name, *, allow_zero=False):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be finite and positive") from error
    if not np.isfinite(number) or number < 0 or (not allow_zero and number == 0):
        raise ValueError(f"{name} must be finite and positive")
    return number


def _aggregate(values):
    quartiles = np.percentile(values, (25, 50, 75), axis=0)
    return np.concatenate((quartiles[1], quartiles[2] - quartiles[0]))


def _morphology(filtered, rate):
    centered = filtered - filtered.mean(axis=1, keepdims=True)
    first = np.diff(centered, axis=1) * rate
    second = np.diff(first, axis=1) * rate
    variance = np.mean(centered * centered, axis=1)
    first_variance = np.mean(first * first, axis=1)
    second_variance = np.mean(second * second, axis=1)
    mobility = np.sqrt(first_variance / np.maximum(variance, 1e-18))
    complexity = np.sqrt(second_variance / np.maximum(first_variance, 1e-18)) / np.maximum(mobility, 1e-9)
    lag = max(1, int(round(0.1 * rate)))
    left, right = centered[:, :-lag], centered[:, lag:]
    denominator = np.sqrt(np.sum(left * left, axis=1) * np.sum(right * right, axis=1))
    autocorr = np.sum(left * right, axis=1) / np.maximum(denominator, 1e-18)
    metrics = np.column_stack((np.log10(np.sqrt(variance) + 1e-9),
                               np.log10(mobility + 1e-9), complexity,
                               np.clip(autocorr, -1.0, 1.0)))
    return _aggregate(metrics)


def _spectrum(filtered, rate):
    nfft = max(filtered.shape[1], int(math.ceil(4 * rate)))
    frequency, density = signal.periodogram(filtered, fs=rate, window="hann",
                                             detrend="constant", scaling="density",
                                             nfft=nfft, axis=1)
    step = frequency[1] - frequency[0]
    cells = []
    for low in range(1, 40, 2):
        high = min(low + 2, 40)
        inside = (frequency >= low) & (frequency < high if high < 40 else frequency <= high)
        power = np.sum(density[:, inside], axis=1) * step
        cells.append(np.log10(power + 1e-12))
    return _aggregate(np.column_stack(cells))


def _coordination(filtered):
    centered = filtered - np.median(filtered, axis=1, keepdims=True)
    mad = 1.4826 * np.median(np.abs(centered), axis=1)
    clipped = np.clip(centered / np.maximum(mad[:, None], 1e-9), -5, 5)
    clipped -= clipped.mean(axis=1, keepdims=True)
    norm = np.linalg.norm(clipped, axis=1)
    standardized = clipped / np.maximum(norm[:, None], 1e-12)
    correlation = standardized @ standardized.T
    correlation = np.clip((correlation + correlation.T) / 2, -1, 1)
    np.fill_diagonal(correlation, 1.0)
    pairs = correlation[np.triu_indices(correlation.shape[0], k=1)]
    q25, q75 = np.percentile(pairs, (25, 75))
    eigenvalues = np.maximum(np.linalg.eigvalsh(correlation), 0)
    fractions = eigenvalues / np.maximum(eigenvalues.sum(), 1e-12)
    positive = fractions[fractions > 0]
    effective_rank = math.exp(-float(np.sum(positive * np.log(positive)))) / len(fractions)
    return np.array((np.median(pairs), q75 - q25, np.median(np.abs(pairs)),
                     eigenvalues[-1] / len(fractions), effective_rank), dtype=np.float64)


def extract_features(samples_uv, sample_rate_hz, *, valid_samples=None,
                     window_seconds=2.0, hop_seconds=0.5):
    """Measure overlapping, quality-gated windows in three fixed-width views.

    A window uses only its own samples. Each usable channel is reflected and
    zero-phase bandpassed at 1-40 Hz; the first and last up to 0.5 seconds are
    discarded from feature estimation. Thus filtering never crosses a gap.
    """
    samples = _numeric_matrix(samples_uv, "samples_uv")
    channels, count = samples.shape
    if channels < 1:
        raise ValueError("samples_uv needs at least one channel")
    rate = _positive(sample_rate_hz, "sample_rate_hz")
    if rate < 100:
        raise ValueError("sample_rate_hz must be at least 100 Hz")
    window_seconds = _positive(window_seconds, "window_seconds")
    hop_seconds = _positive(hop_seconds, "hop_seconds")
    if window_seconds < 1:
        raise ValueError("window_seconds must be at least 1 second")
    window = int(round(window_seconds * rate))
    hop = int(round(hop_seconds * rate))
    if hop < 1:
        raise ValueError("hop_seconds must span at least one sample")
    if valid_samples is None:
        sample_valid = np.ones(samples.shape, dtype=bool)
    else:
        sample_valid = np.asarray(valid_samples)
        if sample_valid.shape != samples.shape or sample_valid.dtype != np.dtype("bool"):
            raise ValueError("valid_samples must be a bool array shaped like samples_uv")
    starts = np.arange(0, max(count - window + 1, 0), hop, dtype=np.int64)
    times = (starts.astype(np.float64) + window / 2) / rate
    valid = np.zeros(len(starts), dtype=bool)
    views = {name: np.full((len(starts), len(names)), np.nan, dtype=np.float64)
             for name, names in _FEATURE_NAMES.items()}
    required = max(2, int(math.ceil(0.75 * channels)))
    line_check_available = rate / 2 > 65
    trim = min(int(round(0.5 * rate)), max(1, window // 4))
    sos = signal.butter(4, (1, 40), btype="bandpass", fs=rate, output="sos")
    for row, start in enumerate(starts):
        raw = samples[:, start:start + window]
        eligible = sample_valid[:, start:start + window].all(axis=1) & np.isfinite(raw).all(axis=1)
        if not np.any(eligible):
            continue
        candidates = np.flatnonzero(eligible)
        window_data = raw[candidates]
        ptp = np.ptp(window_data, axis=1)
        std = np.std(window_data, axis=1)
        keep = (ptp <= 500) & (std >= 0.05) & np.isfinite(ptp) & np.isfinite(std)
        if line_check_available:
            frequencies, native_power = signal.periodogram(window_data, fs=rate,
                                                             window="hann", detrend="constant",
                                                             scaling="spectrum", axis=1)
            total = native_power[:, frequencies >= 1].sum(axis=1)
            line_bins = ((np.abs(frequencies - 50) <= 1) |
                         (np.abs(frequencies - 60) <= 1))
            dominance = native_power[:, line_bins].sum(axis=1) / np.maximum(total, 1e-18)
            keep &= dominance <= 0.3
        if np.count_nonzero(keep) < required:
            continue
        filtered = signal.sosfiltfilt(sos, window_data[keep], axis=1)
        filtered = filtered[:, trim:-trim]
        usable = np.isfinite(filtered).all(axis=1) & (np.std(filtered, axis=1) >= 0.05)
        if np.count_nonzero(usable) < required:
            continue
        filtered = filtered[usable]
        morphology = _morphology(filtered, rate)
        spectrum = _spectrum(filtered, rate)
        coordination = _coordination(filtered)
        if not (np.isfinite(morphology).all() and np.isfinite(spectrum).all() and
                np.isfinite(coordination).all()):
            continue
        views["morphology"][row] = morphology
        views["spectrum"][row] = spectrum
        views["coordination"][row] = coordination
        valid[row] = True
    metadata = {
        "sample_rate_hz": rate,
        "window_samples": window,
        "hop_samples": hop,
        "edge_trim_samples_each_side": trim,
        "filter": "window-local zero-phase Butterworth 1-40 Hz, scipy butter order parameter 4",
        "line_check_available": line_check_available,
        "line_dominance_threshold": 0.3 if line_check_available else None,
        "min_usable_channels": required,
        "valid_window_count": int(valid.sum()),
        "invalid_window_count": int((~valid).sum()),
    }
    return {"times": times.astype(np.float64), "valid": valid, "views": views,
            "feature_names": {name: list(names) for name, names in _FEATURE_NAMES.items()},
            "metadata": metadata}


def fit_reference(feature_arrays):
    """Fit per-feature median and IQR from finite training rows only.

    Accepts one 2-D matrix or a nonempty sequence of 2-D matrices. Constant
    dimensions receive scale 1; returned arrays are independent of the input.
    """
    if isinstance(feature_arrays, np.ndarray):
        arrays = [_numeric_matrix(feature_arrays, "feature_arrays", finite=True)]
    else:
        try:
            arrays = [_numeric_matrix(part, "feature_arrays", finite=True)
                      for part in feature_arrays]
        except TypeError as error:
            raise ValueError("feature_arrays must be a matrix or sequence of matrices") from error
    if not arrays or any(array.shape[1] == 0 for array in arrays):
        raise ValueError("feature_arrays must contain at least one feature")
    width = arrays[0].shape[1]
    if any(array.shape[1] != width for array in arrays):
        raise ValueError("all training arrays must have the same feature width")
    data = np.concatenate(arrays, axis=0)
    if data.shape[0] == 0:
        raise ValueError("feature_arrays must contain at least one training row")
    lower, center, upper = np.percentile(data, (25, 50, 75), axis=0)
    spread = upper - lower
    spread[spread <= 1e-12] = 1.0
    return {"center": np.array(center, dtype=np.float64, copy=True),
            "scale": np.array(spread, dtype=np.float64, copy=True)}


def _validated_grid(times, valid):
    grid = np.asarray(times, dtype=np.float64)
    mask = np.asarray(valid)
    if grid.ndim != 1 or not np.isfinite(grid).all():
        raise ValueError("times must be a finite 1-D array")
    if mask.shape != grid.shape or mask.dtype != np.dtype("bool"):
        raise ValueError("valid must be a bool array shaped like times")
    differences = np.diff(grid)
    if not np.isfinite(differences).all() or np.any(differences <= 0):
        raise ValueError("times must be strictly increasing")
    if not len(differences):
        return grid, mask, None, np.empty(0, dtype=bool)
    linked_valid = mask[:-1] & mask[1:]
    nominal = float(np.median(differences[linked_valid])) if linked_valid.any() else float(np.min(differences))
    regular = np.isclose(differences, nominal, rtol=1e-6, atol=1e-9)
    if np.any(~regular & linked_valid):
        raise ValueError("time gaps between valid rows must be represented by invalid rows")
    return grid, mask, nominal, regular


def _standardized(features, reference, rows):
    data = _numeric_matrix(features, "features")
    if data.shape[0] != rows:
        raise ValueError("features rows must match times")
    try:
        center = np.asarray(reference["center"], dtype=np.float64)
        scale = np.asarray(reference["scale"], dtype=np.float64)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("reference needs center and scale arrays") from error
    if (center.shape != (data.shape[1],) or scale.shape != center.shape or
            not np.isfinite(center).all() or not np.isfinite(scale).all() or
            np.any(scale <= 0)):
        raise ValueError("reference dimension or scale is invalid")
    return (data - center) / scale


def boundary_scores(features, times, valid, reference, *, scales_seconds=(0.5, 2.0, 8.0)):
    """RMS train-scaled difference of pre/post mean feature vectors.

    Candidate index i denotes the boundary between rows i-1 and i. A score
    needs equal-duration, wholly finite and contiguous context on both sides.
    """
    grid, mask, spacing, regular = _validated_grid(times, valid)
    standardized = _standardized(features, reference, len(grid))
    good = mask & np.isfinite(standardized).all(axis=1)
    zeroed = np.where(good[:, None], standardized, 0)
    with np.errstate(over="ignore", invalid="ignore"):
        sums = np.vstack((np.zeros((1, standardized.shape[1])), np.cumsum(zeroed, axis=0)))
    bad_rows = np.r_[0, np.cumsum(~good)]
    bad_edges = np.r_[0, np.cumsum(~regular)]
    result = {}
    for scale in scales_seconds:
        duration = _positive(scale, "scale")
        key = str(scale)
        if key in result:
            raise ValueError("scales_seconds must be unique")
        scores = np.full(len(grid), np.nan, dtype=np.float64)
        if spacing is not None and standardized.shape[1] > 0:
            width = max(1, int(math.ceil(duration / spacing - 1e-12)))
            candidates = np.arange(width, len(grid) - width + 1)
            if len(candidates):
                start = candidates - width
                stop = candidates + width
                supported = ((bad_rows[stop] - bad_rows[start] == 0) &
                             (bad_edges[stop - 1] - bad_edges[start] == 0))
                with np.errstate(over="ignore", invalid="ignore"):
                    before = (sums[candidates] - sums[start]) / width
                    after = (sums[stop] - sums[candidates]) / width
                    difference = after - before
                    largest = np.max(np.abs(difference), axis=1)
                    distance = np.full(len(candidates), np.nan)
                    finite = np.isfinite(largest)
                    nonzero = finite & (largest > 0)
                    distance[finite & ~nonzero] = 0.0
                    distance[nonzero] = (largest[nonzero] *
                                         np.sqrt(np.mean((difference[nonzero] /
                                                          largest[nonzero, None]) ** 2, axis=1)))
                supported &= np.isfinite(distance)
                scores[candidates[supported]] = distance[supported]
        result[key] = scores
    return result


def select_boundaries(scores, times, *, threshold, min_separation_seconds=2.0):
    """Choose plateau-first local maxima, then greedily retain stronger peaks."""
    values = np.asarray(scores, dtype=np.float64)
    grid = np.asarray(times, dtype=np.float64)
    if (values.ndim != 1 or grid.ndim != 1 or len(values) != len(grid) or
            not np.isfinite(grid).all() or not np.isfinite(np.diff(grid)).all() or
            np.any(np.diff(grid) <= 0)):
        raise ValueError("scores and strictly increasing finite times must align")
    floor = _positive(threshold, "threshold", allow_zero=True)
    separation = _positive(min_separation_seconds, "min_separation_seconds", allow_zero=True)
    if np.isinf(values).any():
        raise ValueError("scores may contain NaN but not infinity")
    peaks = []
    index = 0
    while index < len(values):
        if np.isnan(values[index]):
            index += 1
            continue
        end = index
        while end + 1 < len(values) and values[end + 1] == values[index]:
            end += 1
        left = values[index - 1] if index and np.isfinite(values[index - 1]) else -np.inf
        right = values[end + 1] if end + 1 < len(values) and np.isfinite(values[end + 1]) else -np.inf
        if values[index] >= floor and values[index] > left and values[index] > right:
            peaks.append(index)
        index = end + 1
    selected = []
    selected_times = []
    for peak in sorted(peaks, key=lambda item: (-values[item], item)):
        position = bisect_left(selected_times, grid[peak])
        left_ok = position == 0 or grid[peak] - selected_times[position - 1] >= separation
        right_ok = position == len(selected_times) or selected_times[position] - grid[peak] >= separation
        if left_ok and right_ok:
            selected_times.insert(position, float(grid[peak]))
            selected.append(peak)
    return np.asarray(sorted(selected), dtype=np.int64)


def _distance(a, b):
    with np.errstate(over="ignore", invalid="ignore"):
        difference = np.asarray(a) - np.asarray(b)
        largest = float(np.max(np.abs(difference)))
        if not np.isfinite(largest):
            return None
        if largest == 0:
            return 0.0
        distance = largest * float(np.sqrt(np.mean((difference / largest) ** 2)))
    return distance if np.isfinite(distance) else None


def _unit_direction(vector):
    with np.errstate(over="ignore", invalid="ignore"):
        largest = float(np.max(np.abs(vector)))
        if not np.isfinite(largest) or largest == 0:
            return None
        scaled = vector / largest
        length = float(np.sqrt(np.sum(scaled * scaled)))
    return scaled / length if np.isfinite(length) and length > 0 else None


def transition_geometry(features, times, valid, reference, indices, *, context_seconds=2.0):
    """Describe local trajectories; unsupported context yields explicit nulls."""
    grid, mask, spacing, regular = _validated_grid(times, valid)
    standardized = _standardized(features, reference, len(grid))
    duration = _positive(context_seconds, "context_seconds")
    requested = np.asarray(indices)
    if requested.ndim != 1 or (requested.size and not np.issubdtype(requested.dtype, np.integer)):
        raise ValueError("indices must be a 1-D integer array")
    if np.any(requested < 0) or np.any(requested >= len(grid)):
        raise ValueError("indices must fall inside features")
    width = max(1, int(math.ceil(duration / spacing - 1e-12))) if spacing else 1
    metric_names = ("pre_post_distance", "path_length", "mean_speed",
                    "turning_angle_radians", "return_distance")
    rows = []
    for item in requested:
        index = int(item)
        row = {"index": index, "time_seconds": float(grid[index]),
               **{name: None for name in metric_names}}
        start, stop = index - width, index + width
        if (start < 0 or stop > len(grid) or not mask[start:stop].all() or
                not np.isfinite(standardized[start:stop]).all() or
                not regular[start:stop - 1].all()):
            rows.append(row)
            continue
        trajectory = standardized[start:stop]
        before = trajectory[:width]
        after = trajectory[width:]
        with np.errstate(over="ignore", invalid="ignore"):
            pre_center = before.mean(axis=0)
            post_center = after.mean(axis=0)
        steps = [_distance(trajectory[j + 1], trajectory[j])
                 for j in range(len(trajectory) - 1)]
        path = float(sum(steps)) if all(step is not None for step in steps) else None
        if path is not None and not np.isfinite(path):
            path = None
        elapsed = float(grid[stop - 1] - grid[start])
        if np.isfinite(pre_center).all() and np.isfinite(post_center).all():
            row["pre_post_distance"] = _distance(pre_center, post_center)
            row["return_distance"] = _distance(trajectory[-1], pre_center)
        row["path_length"] = path
        if path is not None and elapsed > 0:
            speed = path / elapsed
            row["mean_speed"] = speed if np.isfinite(speed) else None
        with np.errstate(over="ignore", invalid="ignore"):
            incoming = before[-1] - before[0]
            outgoing = after[-1] - after[0]
        pre_direction = _unit_direction(incoming)
        post_direction = _unit_direction(outgoing)
        if pre_direction is not None and post_direction is not None:
            cosine = float(np.clip(np.dot(pre_direction, post_direction), -1, 1))
            row["turning_angle_radians"] = float(math.acos(cosine))
        rows.append(row)
    return rows


def match_boundaries(times_a, times_b, *, tolerance_seconds=1.0):
    """Maximum-cardinality one-to-one match, then minimum absolute time error.

    Inputs are sorted internally. A is the reference for recall and B the
    detections for precision. A sparse dynamic program considers only eligible
    pairs, using O(E log(n_b)) time and O(E+n_b) storage, up to four million
    eligible pairs. Tied optimal chains use the earlier constructed state.
    """
    a = np.asarray(times_a, dtype=np.float64)
    b = np.asarray(times_b, dtype=np.float64)
    tolerance = _positive(tolerance_seconds, "tolerance_seconds", allow_zero=True)
    if a.ndim != 1 or b.ndim != 1 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("boundary times must be finite 1-D arrays")
    a, b = np.sort(a), np.sort(b)
    n, m = len(a), len(b)
    # Optimal monotone matching is a maximum-weight increasing chain of
    # eligible pairs. A Fenwick tree queries the best earlier b-index; batch
    # updates after each a-index prevent a boundary from matching twice.
    lower = np.searchsorted(b, a - tolerance, side="left")
    upper = np.searchsorted(b, a + tolerance, side="right")
    if int(np.sum(upper - lower)) > 4_000_000:
        raise ValueError("too many eligible boundary pairs for bounded optimal matching")
    # Each node is (count, cost, predecessor, absolute_error).
    nodes = [(0, 0.0, -1, 0.0)]
    tree = np.zeros(m + 1, dtype=np.int64)
    def better(x, y):
        nx, ny = nodes[x], nodes[y]
        if nx[0] != ny[0]: return x if nx[0] > ny[0] else y
        if nx[1] != ny[1]: return x if nx[1] < ny[1] else y
        return min(x, y)
    def query(end):
        best = 0
        while end:
            best = better(best, int(tree[end])); end -= end & -end
        return best
    for i in range(n):
        pending = []
        for j in range(int(lower[i]), int(upper[i])):
            previous = query(j)
            error = float(abs(a[i] - b[j]))
            nodes.append((nodes[previous][0] + 1, nodes[previous][1] + error, previous, error))
            pending.append((j + 1, len(nodes) - 1))
        for index, node in pending:
            while index <= m:
                tree[index] = better(int(tree[index]), node); index += index & -index
    errors = []
    node = query(m)
    while node:
        errors.append(nodes[node][3]); node = nodes[node][2]
    matched = len(errors)
    if not n and not m:
        precision = recall = f1 = 1.0
    else:
        precision = matched / m if m else 0.0
        recall = matched / n if n else 0.0
        f1 = 2 * precision * recall / (precision + recall) if matched else 0.0
    return {"n_a": n, "n_b": m, "matched": matched,
            "precision": float(precision), "recall": float(recall), "f1": float(f1),
            "median_abs_error_seconds": float(np.median(errors)) if errors else None,
            "total_abs_error_seconds": float(sum(errors))}


def phase_surrogate(samples_uv, *, seed=17, shared_phase=False):
    """Rotate positive-frequency rFFT bins without changing their amplitudes.

    Shared phase preserves every cross-spectrum; independent phases generally
    disturb cross-channel phase. DC and even-length Nyquist bins stay real and
    unchanged. The odd-length final bin is an ordinary complex frequency bin.
    """
    samples = _numeric_matrix(samples_uv, "samples_uv", finite=True)
    if samples.shape[0] < 1 or samples.shape[1] < 2:
        raise ValueError("samples_uv needs at least one channel and two samples")
    spectrum = np.fft.rfft(samples, axis=1)
    end = -1 if samples.shape[1] % 2 == 0 else spectrum.shape[1]
    frequencies = spectrum[:, 1:end]
    rng = np.random.default_rng(seed)
    phase_shape = (1 if shared_phase else samples.shape[0], frequencies.shape[1])
    rotation = np.exp(1j * rng.uniform(0, 2 * np.pi, size=phase_shape))
    spectrum[:, 1:end] = frequencies * rotation
    return np.fft.irfft(spectrum, n=samples.shape[1], axis=1)
