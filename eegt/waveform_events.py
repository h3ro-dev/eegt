"""Numeric, gap-safe direct waveform landmarks, cycles, bursts and event matching.

No recording identity, electrode semantics or curator metadata enters this module.
All sample indices are relative to the stated continuous timing segment.
"""

from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache

import numpy as np
from scipy import signal


PROTOCOL = "eegt-direct-waveform/v1"
BANDS = ((4., 8.), (8., 13.), (13., 30.))
THRESHOLDS = {"amp_fraction_threshold": .3, "amp_consistency_threshold": .4,
              "period_consistency_threshold": .5, "monotonicity_threshold": .8,
              "min_n_cycles": 3}


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _coefficient_hash(values):
    return hashlib.sha256(np.asarray(values, dtype="<f8").tobytes()).hexdigest()


def _runs(mask):
    padded = np.r_[False, np.asarray(mask, bool), False].astype(np.int8)
    edges = np.flatnonzero(np.diff(padded))
    return [(int(a), int(b)) for a, b in edges.reshape(-1, 2)]


def crossings(derivative, epsilon, *, include_rejected=False):
    """Return opposite-sign crossings with deterministic direct/zero-run indices.

    A qualifying crossing has two nonzero samples of each sign. With
    include_rejected, all bracketed crossings are returned with their reason.
    """
    d = np.asarray(derivative, dtype=np.float64)
    if d.ndim != 1 or not np.isfinite(d).all() or not np.isfinite(epsilon) or epsilon < 0:
        raise ValueError("derivative must be finite 1-D and epsilon nonnegative")
    s = np.where(d > epsilon, 1, np.where(d < -epsilon, -1, 0))
    rows = []
    previous = None
    for right in np.flatnonzero(s):
        right = int(right)
        if previous is not None and s[previous] != s[right]:
            left = previous
            direct = right == left + 1
            index = right if direct else (left + right) // 2
            fraction = (float(left + abs(d[left]) / (abs(d[left]) + abs(d[right])))
                        if direct else None)
            qualified = (left >= 1 and right + 1 < len(s) and
                         s[left-1] == s[left] and s[right+1] == s[right])
            row = {"index": index, "fractional_index": fraction,
                   "direction": "positive_to_negative" if s[left] > 0 else "negative_to_positive",
                   "accepted": bool(qualified),
                   "rejection_reasons": [] if qualified else ["INSUFFICIENT_SIGN_SUPPORT"],
                   "bracket": [left, right], "sign_flank": [left-1, right+2]}
            if qualified or include_rejected:
                rows.append(row)
        previous = right
    return rows


def _window(fs, smoothing_ms):
    target = fs * smoothing_ms / 1000.
    lower = max(5, 2 * math.floor((target - 1) / 2) + 1)
    upper = lower + 2
    return int(upper if abs(upper - target) <= abs(lower - target) else lower)


def _padlen_sos(sos):
    return int(3 * (2 * len(sos) + 1 - min(np.count_nonzero(sos[:, 2] == 0),
                                          np.count_nonzero(sos[:, 5] == 0))))


@lru_cache(maxsize=64)
def filter_support(fs, passband=(1., 40.), smoothing_ms=31, notch_hz=None,
                   narrowband=None, envelope=False):
    """Measure complete 60-second impulse/step support for a pinned filter chain.

    If the probe cannot resolve both tails, callers must abstain. Returned
    coefficients are the actual SciPy/NeuroDSP coefficients used in filtering.
    """
    fs = float(fs)
    lo, hi = map(float, passband)
    if not (np.isfinite(fs) and fs > 0 and 0 < lo < hi < fs / 2):
        raise ValueError("unsupported rate or passband")
    if notch_hz is not None and not (0 < float(notch_hz) < fs / 2):
        raise ValueError("unsupported notch frequency")
    window = _window(fs, smoothing_ms)
    sos = signal.butter(4, (lo, hi), btype="bandpass", fs=fs, output="sos")
    padlen = _padlen_sos(sos)
    notch = None
    if notch_hz is not None:
        b, a = signal.iirnotch(float(notch_hz), 30., fs)
        notch = {"hz": float(notch_hz), "quality_factor": 30., "b": b.tolist(), "a": a.tolist(),
                 "padlen": int(3 * max(len(a), len(b)))}
    kernel = None
    if narrowband is not None:
        from neurodsp.filt.fir import design_fir_filter
        band = tuple(map(float, narrowband))
        kernel = np.asarray(design_fir_filter(fs, "bandpass", band, n_cycles=3), dtype=np.float64)
    n = int(round(60 * fs))
    mid = n // 2
    impulse = np.zeros(n, dtype=np.float64)
    impulse[mid] = 1.
    step = np.zeros(n, dtype=np.float64)
    step[mid:] = 1.

    def chain(x):
        if notch is not None:
            x = signal.filtfilt(notch["b"], notch["a"], x, padtype="odd", padlen=notch["padlen"])
        x = signal.sosfiltfilt(sos, x, padtype="odd", padlen=padlen)
        if kernel is not None:
            from neurodsp.filt import filter_signal
            x = filter_signal(x, fs, "bandpass", tuple(narrowband), n_cycles=3, remove_edges=False)
            if envelope:
                x = np.abs(signal.hilbert(x))
        return np.asarray(x, dtype=np.float64)

    yi, ys = chain(impulse), chain(step)
    if not np.isfinite(yi).all() or not np.isfinite(ys).all():
        raise ValueError("UNSUPPORTED_FILTER_SUPPORT: nonfinite probe")
    energy = float(np.dot(yi, yi))
    peak = float(np.max(np.abs(ys)))
    if energy <= 0 or peak <= 0:
        raise ValueError("UNSUPPORTED_FILTER_SUPPORT: zero probe")
    impulse_bad = np.abs(np.arange(n) - mid)
    # Sum both tail energies for every radius, then take the first resolved radius.
    energy_by_radius = np.bincount(impulse_bad, weights=yi * yi, minlength=mid + 1)
    remaining = np.cumsum(energy_by_radius[::-1])[::-1] - energy_by_radius
    resolved = np.flatnonzero(remaining / energy < 1e-6)
    if len(resolved) == 0:
        raise ValueError("UNSUPPORTED_FILTER_SUPPORT: impulse tail unresolved")
    impulse_guard = int(resolved[0])
    step_bad = np.flatnonzero(np.abs(ys) >= peak * 1e-6)
    step_guard = int(np.max(np.abs(step_bad - mid)))
    # Bycycle measures morphology on the preceding broadband trace, so its
    # narrowband output cannot justify a shorter guard than that trace.
    broadband_guard = (filter_support(fs, (lo, hi), smoothing_ms, notch_hz)["guard_samples"]
                       if kernel is not None else 0)
    guard = max(impulse_guard, step_guard, broadband_guard, (window - 1) // 2,
                (len(kernel) - 1) // 2 if kernel is not None else 0)
    if guard >= mid - 1:
        raise ValueError("UNSUPPORTED_FILTER_SUPPORT: 60-second tail unresolved")
    return {"sample_rate_hz": fs, "passband_hz": [lo, hi], "notch": notch,
            "sos": sos.tolist(), "sos_sha256": _coefficient_hash(sos), "sos_padlen": padlen,
            "fir_kernel": kernel.tolist() if kernel is not None else None,
            "fir_sha256": _coefficient_hash(kernel) if kernel is not None else None,
            "narrowband_hz": list(narrowband) if narrowband is not None else None,
            "envelope": bool(envelope), "window_samples": window,
            "window_seconds": window / fs, "half_smoothing_support_seconds": (window-1)/(2*fs),
            "impulse_guard_samples": impulse_guard, "step_guard_samples": step_guard,
            "preceding_broadband_guard_samples": broadband_guard if kernel is not None else None,
            "guard_samples": guard, "guard_seconds": guard / fs,
            "probe_seconds": 60, "impulse_tail_energy_fraction_at_guard": float(remaining[guard] / energy),
            "step_tail_max_fraction_at_guard": float(np.max(np.abs(ys[impulse_bad > guard])) / peak)}


def _filtered(x, fs, receipt):
    notch = receipt["notch"]
    if notch is not None:
        x = signal.filtfilt(notch["b"], notch["a"], x, padtype="odd", padlen=notch["padlen"])
    return signal.sosfiltfilt(np.asarray(receipt["sos"]), x, padtype="odd",
                              padlen=receipt["sos_padlen"])


def _base_row(segment_key, channel_key, family, detector, parameter_hash, index, fs, run,
              guard, *, end=None, accepted=False, reasons=()):
    relative = index - run["segment_start_sample"] if index is not None else None
    end_relative = end - run["segment_start_sample"] if end is not None else None
    support_start = relative - guard if relative is not None else None
    support_end = (end_relative + guard if end is not None else
                   relative + guard + 1 if relative is not None else None)
    return {"schema": PROTOCOL, "segment_key": segment_key, "channel_key": channel_key,
            "family": family, "detector": detector, "parameter_hash": parameter_hash,
            "index": relative, "fractional_index": None, "seconds": relative / fs if relative is not None else None,
            "interval_end_sample": end_relative, "interval_end_seconds": end_relative / fs if end_relative is not None else None,
            "polarity": None, "direction": None, "amplitude_uv": None, "slope_uv_per_second": None,
            "curvature_uv_per_second2": None, "period_seconds": None,
            "rise_fraction": None, "peak_fraction": None, "cycle_membership": None,
            "burst_membership": None, "accepted": bool(accepted), "rejection_reasons": list(reasons),
            "support_start_sample": support_start, "support_end_sample": support_end,
            "support_start_seconds": support_start / fs if support_start is not None else None,
            "support_end_seconds": support_end / fs if support_end is not None else None,
            "guard_samples": guard, "guard_seconds": guard / fs,
            "gap_distance_samples": min(index - run["start_sample"], run["end_sample"] - 1 - (end - 1 if end is not None else index)) if index is not None else None,
            "native_period_seconds": 1 / fs, "setting_disagreement_seconds": None,
            "synthetic_localization_error_samples": None,
            "preceding_interval_seconds": None, "following_interval_seconds": None,
            "path_length": None, "turning_angle_radians": None, "return_distance": None}


def _add_geometry(events):
    groups = {}
    for row in events:
        if row["accepted"] and row["family"] in ("extremum", "inflection"):
            key = (row["segment_key"], row["channel_key"], row["run_key"],
                   row["family"], row["polarity"], row["direction"])
            groups.setdefault(key, []).append(row)
    for group in groups.values():
        group.sort(key=lambda r: r["index"])
        for i, row in enumerate(group):
            if i:
                row["preceding_interval_seconds"] = row["seconds"] - group[i-1]["seconds"]
            if i + 1 < len(group):
                row["following_interval_seconds"] = group[i+1]["seconds"] - row["seconds"]


def discover(samples_uv, sample_rate_hz, valid_mask, timing_segments, *,
             passband_hz=(1., 40.), smoothing_ms=31, notch_hz=None,
             include_cycles=False, include_envelopes=False):
    """Discover candidate and accepted events on numeric native-clock channels.

    timing_segments is a nonoverlapping sequence of (start, end, clock_start_s).
    It partitions the sample axis; each reset is an independent segment.
    """
    x = np.asarray(samples_uv, dtype=np.float64)
    mask = np.asarray(valid_mask)
    fs = float(sample_rate_hz)
    if x.ndim != 2 or x.shape != mask.shape or mask.dtype != bool or not np.isfinite(fs) or fs <= 0:
        raise ValueError("samples, Boolean validity mask, and positive rate required")
    if not np.isfinite(x[mask]).all():
        raise ValueError("valid samples must be finite")
    segs = np.asarray(timing_segments, dtype=float)
    if segs.ndim != 2 or segs.shape[1] != 3 or not np.isfinite(segs).all() or len(segs) == 0:
        raise ValueError("timing_segments must be finite (start,end,clock_start_s) rows")
    if np.any(segs[:, :2] != np.floor(segs[:, :2])) or int(segs[0, 0]) != 0 or int(segs[-1, 1]) != x.shape[1] or np.any(segs[:, 1] <= segs[:, 0]) or np.any(segs[1:, 0] != segs[:-1, 1]):
        raise ValueError("timing segments must partition the sample axis")
    if len(passband_hz) != 2:
        raise ValueError("passband_hz needs two frequencies")
    config = {"fs": fs, "passband_hz": list(map(float, passband_hz)), "smoothing_ms": smoothing_ms,
              "notch_hz": notch_hz, "cycle_bands_hz": BANDS, "thresholds": THRESHOLDS}
    param_hash = _hash(config)
    events, runs, filters, invalid_intervals = [], [], {}, []
    if fs < 200:
        waveform_receipt = None
        waveform_error = "UNSUPPORTED_RATE"
        slower_receipt = None
        if include_cycles or include_envelopes:
            try:
                slower_receipt = filter_support(fs, tuple(passband_hz), smoothing_ms, notch_hz)
                filters["slower_method_broadband"] = slower_receipt
            except ValueError:
                pass
    else:
        slower_receipt = None
        try:
            waveform_receipt = filter_support(fs, tuple(passband_hz), smoothing_ms, notch_hz)
            waveform_error = None
            filters["waveform"] = waveform_receipt
        except ValueError as error:
            waveform_receipt = None
            waveform_error = str(error).split(":")[0]
    for seg_no, (start_float, end_float, clock_start) in enumerate(segs):
        seg_start, seg_end = int(start_float), int(end_float)
        segment_key = f"segment_{seg_no}"
        for channel in range(x.shape[0]):
            channel_key = f"channel_{channel}"
            for bad_start, bad_end in _runs(~mask[channel, seg_start:seg_end]):
                invalid_intervals.append({"segment_key": segment_key, "channel_key": channel_key,
                                          "start_sample": bad_start, "end_sample": bad_end,
                                          "duration_seconds": (bad_end-bad_start)/fs,
                                          "reason": "INVALID_MASK"})
            for run_no, (a, b) in enumerate(_runs(mask[channel, seg_start:seg_end])):
                a += seg_start
                b += seg_start
                run = {"segment_key": segment_key, "channel_key": channel_key, "run_key": f"run_{run_no}",
                       "segment_start_sample": seg_start, "segment_end_sample": seg_end,
                       "clock_start_seconds": float(clock_start), "start_sample": a, "end_sample": b,
                       "valid_duration_seconds": (b-a)/fs, "guarded_valid_duration_seconds": 0.,
                       "rejected_duration_seconds": (b-a)/fs, "status": None}
                runs.append(run)
                if waveform_error is not None:
                    run["status"] = waveform_error
                    if slower_receipt is not None:
                        data = x[channel, a:b]
                        guard = slower_receipt["guard_samples"]
                        need = max(slower_receipt["sos_padlen"],
                                   slower_receipt["notch"]["padlen"] if slower_receipt["notch"] else 0)
                        if len(data) >= 3 and np.max(np.abs(np.diff(data, n=2))) > 64*np.finfo(float).eps*max(1., float(np.max(np.abs(data)))) and len(data) > max(need, 2*guard):
                            filtered = _filtered(data, fs, slower_receipt)
                            _oscillation_events(data, filtered, fs, run, config, param_hash, filters, events,
                                                slower_receipt, include_cycles, include_envelopes)
                        else:
                            run["oscillation_status"] = {"all": "UNSUPPORTED_SHORT_RUN_OR_AFFINE"}
                    continue
                data = x[channel, a:b]
                if len(data) < 3:
                    run["status"] = "DEGENERATE_AFFINE"
                    continue
                if np.max(np.abs(np.diff(data, n=2))) <= 64*np.finfo(float).eps*max(1., float(np.max(np.abs(data)))):
                    run["status"] = "DEGENERATE_AFFINE"
                    continue
                guard = waveform_receipt["guard_samples"]
                need = max(waveform_receipt["sos_padlen"], waveform_receipt["notch"]["padlen"] if waveform_receipt["notch"] else 0,
                           waveform_receipt["window_samples"])
                if len(data) <= need or len(data) <= 2*guard:
                    run["status"] = "UNSUPPORTED_SHORT_RUN"
                    continue
                filtered = _filtered(data, fs, waveform_receipt)
                window = waveform_receipt["window_samples"]
                d1 = signal.savgol_filter(filtered, window, 3, deriv=1, delta=1/fs, mode="interp")
                d2 = signal.savgol_filter(filtered, window, 3, deriv=2, delta=1/fs, mode="interp")
                eps1 = 64*np.finfo(float).eps*max(1., float(np.median(np.abs(d1[guard:-guard]))))
                eps2 = 64*np.finfo(float).eps*max(1., float(np.median(np.abs(d2[guard:-guard]))))
                slope_min = 1e-6*max(1., float(np.median(np.abs(d1[guard:-guard]))))
                run.update(status="OK", guard_samples=guard, guard_seconds=guard/fs,
                           guarded_valid_duration_seconds=(len(data)-2*guard)/fs,
                           rejected_duration_seconds=2*guard/fs,
                           derivative_epsilon_uv_per_second=eps1,
                           curvature_epsilon_uv_per_second2=eps2, slope_gate_uv_per_second=slope_min)
                for family, derivative, epsilon in (("extremum", d1, eps1), ("inflection", d2, eps2)):
                    for item in crossings(derivative, epsilon, include_rejected=True):
                        i = item["index"]
                        flank_start, flank_end = item["sign_flank"]
                        flank_guarded = guard <= flank_start and flank_end <= len(data)-guard
                        accepted = item["accepted"] and flank_guarded
                        reasons = item["rejection_reasons"].copy()
                        if not flank_guarded:
                            reasons.append("SIGN_FLANK_FILTER_GUARD")
                        if family == "inflection" and abs(d1[i]) <= slope_min:
                            accepted = False
                            reasons.append("LOW_SLOPE")
                        row = _base_row(segment_key, channel_key, family, "savgol_sign_change", param_hash,
                                        a+i, fs, run, guard, accepted=accepted, reasons=reasons)
                        support_start = a-seg_start+flank_start-guard
                        support_end = a-seg_start+flank_end+guard
                        row.update(run_key=run["run_key"], fractional_index=(a-seg_start + item["fractional_index"] if item["fractional_index"] is not None else None),
                                   polarity=("peak" if item["direction"] == "positive_to_negative" else "trough") if family == "extremum" else None,
                                   direction=item["direction"] if family == "extremum" else "curvature_" + item["direction"],
                                   amplitude_uv=float(filtered[i]), slope_uv_per_second=float(d1[i]),
                                   curvature_uv_per_second2=float(d2[i]), bracket_samples=[a-seg_start+j for j in item["bracket"]],
                                   sign_flank_start_sample=a-seg_start+flank_start,
                                   sign_flank_end_sample=a-seg_start+flank_end,
                                   support_start_sample=support_start, support_end_sample=support_end,
                                   support_start_seconds=support_start/fs, support_end_seconds=support_end/fs)
                        events.append(row)
                if include_cycles or include_envelopes:
                    _oscillation_events(data, filtered, fs, run, config, param_hash, filters, events,
                                        waveform_receipt, include_cycles, include_envelopes)
    _add_geometry(events)
    return {"schema": PROTOCOL, "parameter_hash": param_hash, "sample_rate_hz": fs,
            "events": events, "runs": runs, "filters": filters,
            "invalid_intervals": invalid_intervals,
            "invalid_duration_seconds": float(np.size(mask) - np.count_nonzero(mask))/fs}


def _oscillation_events(raw, filtered, fs, run, config, param_hash, filters, events,
                        waveform_receipt, include_cycles, include_envelopes):
    a, b = run["start_sample"], run["end_sample"]
    seg, ch = run["segment_key"], run["channel_key"]
    for band in BANDS:
        label = f"{int(band[0])}-{int(band[1])}Hz"
        for definition, enabled in (("cycle", include_cycles), ("envelope", include_envelopes)):
            if not enabled:
                continue
            try:
                receipt = filter_support(fs, tuple(config["passband_hz"]), config["smoothing_ms"],
                                         config["notch_hz"], band, definition == "envelope")
                filters[f"{definition}:{label}"] = receipt
            except ValueError as error:
                run.setdefault("oscillation_status", {})[f"{definition}:{label}"] = str(error).split(":")[0]
                continue
            guard = receipt["guard_samples"]
            if len(raw) <= max(len(receipt["fir_kernel"]), 2*guard):
                run.setdefault("oscillation_status", {})[f"{definition}:{label}"] = "UNSUPPORTED_SHORT_RUN"
                continue
            if definition == "cycle":
                from bycycle.features import compute_features
                try:
                    frame = compute_features(filtered, fs, band, center_extrema="peak", burst_method="cycles",
                                             return_samples=True, threshold_kwargs=THRESHOLDS.copy(),
                                             find_extrema_kwargs={"pad": False, "boundary": 0,
                                                                  "filter_kwargs": {"n_cycles": 3}})
                except (ValueError, IndexError) as error:
                    run.setdefault("oscillation_status", {})[f"{definition}:{label}"] = f"LIBRARY_ERROR:{type(error).__name__}:{error}"
                    continue
                group = []
                def flush():
                    if not group:
                        return
                    first, last = group[0], group[-1]
                    complete_group = (first["index"] is not None and last["interval_end_sample"] is not None)
                    inside_group = complete_group and all(cycle["accepted"] for cycle in group)
                    reason = [] if inside_group else ["CENSORED_GUARD_BOUNDARY" if complete_group else "UNSCORABLE_CYCLE"]
                    row = _base_row(seg, ch, "burst", "bycycle_contiguous", param_hash,
                                    run["segment_start_sample"]+first["index"] if first["index"] is not None else None,
                                    fs, run, guard,
                                    end=run["segment_start_sample"]+last["interval_end_sample"] if last["interval_end_sample"] is not None else None,
                                    accepted=inside_group, reasons=reason)
                    row.update(run_key=run["run_key"], band_hz=list(band), definition="cycle_contiguity",
                               cycle_count=len(group), burst_membership=True)
                    events.append(row)
                    group.clear()
                for _, item in frame.iterrows():
                    values = {}
                    for name in ("sample_last_trough", "sample_peak", "sample_next_trough", "sample_zerox_rise", "sample_zerox_decay"):
                        value = item.get(name)
                        values[name] = int(value) if value is not None and np.isfinite(value) else None
                    left, peak, right = values["sample_last_trough"], values["sample_peak"], values["sample_next_trough"]
                    complete = (left is not None and peak is not None and right is not None and
                                0 <= left < peak < right <= len(raw))
                    inside = complete and guard <= left and right <= len(raw)-guard
                    reasons = [] if inside else ["UNSCORABLE_CYCLE" if not complete else "FILTER_GUARD"]
                    row = _base_row(seg, ch, "cycle", "bycycle_1.2.0", param_hash,
                                    a+left if left is not None else None, fs, run, guard,
                                    end=a+right if right is not None else None,
                                    accepted=inside, reasons=reasons)
                    burst_flag = bool(item.get("is_burst", False)) if not np.isnan(item.get("is_burst", False)) else False
                    period = item.get("period", np.nan)
                    amplitude = item.get("volt_amp", np.nan)
                    rise = item.get("time_rdsym", np.nan)
                    peak_fraction = item.get("time_ptsym", np.nan)
                    row.update(run_key=run["run_key"], band_hz=list(band), definition="trough_to_trough",
                               sample_peak=peak + a-run["segment_start_sample"] if peak is not None else None,
                               sample_zerox_rise=values["sample_zerox_rise"] + a-run["segment_start_sample"] if values["sample_zerox_rise"] is not None else None,
                               sample_zerox_decay=values["sample_zerox_decay"] + a-run["segment_start_sample"] if values["sample_zerox_decay"] is not None else None,
                               period_seconds=float(period/fs) if np.isfinite(period) else None,
                               amplitude_uv=float(amplitude) if np.isfinite(amplitude) else None,
                               rise_fraction=float(rise) if np.isfinite(rise) else None,
                               peak_fraction=float(peak_fraction) if np.isfinite(peak_fraction) else None,
                               cycle_membership=burst_flag, library_is_burst=burst_flag)
                    events.append(row)
                    if burst_flag:
                        if group and group[-1]["interval_end_sample"] != row["index"]:
                            flush()
                        group.append(row)
                    else:
                        flush()
                flush()
                run.setdefault("oscillation_status", {})[f"{definition}:{label}"] = "OK"
            else:
                from neurodsp.burst import detect_bursts_dual_threshold
                from neurodsp.timefrequency import amp_by_time
                try:
                    magnitude = amp_by_time(filtered, fs, band, remove_edges=False, n_cycles=3)
                    median = float(np.median(magnitude))
                    if not np.isfinite(median) or median <= 0:
                        raise ValueError("DEGENERATE_NORMALIZATION")
                    mask = detect_bursts_dual_threshold(filtered, fs, dual_thresh=(1, 2),
                                                        f_range=band, avg_type="median",
                                                        magnitude_type="amplitude", min_n_cycles=3,
                                                        n_cycles=3)
                except (ValueError, IndexError) as error:
                    run.setdefault("oscillation_status", {})[f"{definition}:{label}"] = f"LIBRARY_ERROR:{type(error).__name__}:{error}"
                    continue
                run.setdefault("envelope_median_uv", {})[label] = median
                for left, right in _runs(mask):
                    inside = guard <= left and right <= len(raw)-guard
                    row = _base_row(seg, ch, "burst", "neurodsp_dual_threshold", param_hash,
                                    a+left, fs, run, guard, end=a+right, accepted=inside,
                                    reasons=[] if inside else ["CENSORED_GUARD_BOUNDARY"])
                    row.update(run_key=run["run_key"], band_hz=list(band), definition="envelope_dual_threshold",
                               cycle_count=None, envelope_median_uv=median, duration_floor_seconds=3/band[0])
                    events.append(row)
                run.setdefault("oscillation_status", {})[f"{definition}:{label}"] = "OK"


def _normal_intervals(intervals):
    result = []
    for a, b in intervals:
        a, b = float(a), float(b)
        if not (np.isfinite(a) and np.isfinite(b) and 0 <= a <= b):
            raise ValueError("support intervals must be finite ordered seconds")
        if a < b:
            result.append((a, b))
    result.sort()
    merged = []
    for a, b in result:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    return merged


def match_events(events_a, events_b, *, intervals_a_seconds, intervals_b_seconds,
                 shared_clock, clock_error_bound_seconds, tolerance_seconds=.025,
                 max_eligible_pairs=4_000_000):
    """Sparse optimal one-to-one match with input-index pairs and signed lags.

    Matches only accepted same-family/polarity/band/definition events whose
    complete support lies in the verified shared timeline. Ties follow the
    historical match_boundaries node-construction order.
    """
    result = {"status": None, "n_a_before": len(events_a), "n_b_before": len(events_b),
              "n_a": None, "n_b": None, "common_duration_seconds": None,
              "eligible_pairs": None,
              "matched": None, "matched_input_index_pairs": [], "signed_lags_seconds": [],
              "fraction_a_matched": None, "fraction_b_matched": None,
              "agreement": None, "median_signed_lag_seconds": None,
              "median_absolute_lag_seconds": None, "total_absolute_lag_seconds": None,
              "interval_iou": None, "duration_bias_seconds": None}
    if not (shared_clock and clock_error_bound_seconds is not None and
            np.isfinite(clock_error_bound_seconds) and 0 <= clock_error_bound_seconds < tolerance_seconds):
        result["status"] = "NOT_COMPARABLE"
        return result
    if not np.isfinite(tolerance_seconds) or tolerance_seconds < 0 or max_eligible_pairs < 0:
        raise ValueError("invalid tolerance or pair limit")
    ia, ib = _normal_intervals(intervals_a_seconds), _normal_intervals(intervals_b_seconds)
    common = []
    for a0, a1 in ia:
        for b0, b1 in ib:
            left, right = max(a0, b0), min(a1, b1)
            if left < right:
                common.append((left, right))
    common = _normal_intervals(common)
    result["common_duration_seconds"] = float(sum(b-a for a, b in common))
    def selected(events):
        rows = []
        for i, row in enumerate(events):
            if not row.get("accepted", True):
                continue
            start, end = row.get("support_start_seconds"), row.get("support_end_seconds")
            if start is None or end is None or not np.isfinite([start, end, row["seconds"]]).all():
                continue
            if any(a <= start <= end <= b for a, b in common):
                rows.append((i, row))
        return rows
    a, b = selected(events_a), selected(events_b)
    result["n_a"], result["n_b"] = len(a), len(b)
    aligned = {(row.get("segment_key"), row.get("channel_key")) for _, row in a+b}
    if len(aligned) > 1:
        result["status"] = "NOT_COMPARABLE"
        return result
    fields = ("family", "polarity", "direction", "band_hz", "definition")
    def signature(row):
        return tuple(json.dumps(row.get(field), sort_keys=True) for field in fields)
    signatures = {signature(row) for _, row in a+b}
    if len(signatures) > 1:
        combined, remaining, eligible = [], max_eligible_pairs, 0
        for kind in sorted(signatures):
            subset_a = [(i, row) for i, row in a if signature(row) == kind]
            subset_b = [(i, row) for i, row in b if signature(row) == kind]
            sub = match_events([row for _, row in subset_a], [row for _, row in subset_b],
                               intervals_a_seconds=common, intervals_b_seconds=common,
                               shared_clock=True, clock_error_bound_seconds=clock_error_bound_seconds,
                               tolerance_seconds=tolerance_seconds, max_eligible_pairs=remaining)
            if sub["status"] != "OK":
                result["status"] = sub["status"]
                return result
            remaining -= sub["eligible_pairs"]
            eligible += sub["eligible_pairs"]
            for position, (i, j) in enumerate(sub["matched_input_index_pairs"]):
                iou = sub["interval_iou"][position] if sub["interval_iou"] is not None else None
                bias = sub["duration_bias_seconds"][position] if sub["duration_bias_seconds"] is not None else None
                combined.append((subset_a[i][0], subset_b[j][0], sub["signed_lags_seconds"][position], iou, bias))
        combined.sort(key=lambda item: (item[0], item[1]))
        signed = [item[2] for item in combined]
        matched = len(combined)
        result.update(status="OK", eligible_pairs=eligible, matched=matched,
                      matched_input_index_pairs=[[item[0], item[1]] for item in combined],
                      signed_lags_seconds=signed,
                      fraction_a_matched=matched/len(a) if a else None,
                      fraction_b_matched=matched/len(b) if b else None,
                      agreement=2*matched/(len(a)+len(b)) if a or b else None,
                      median_signed_lag_seconds=float(np.median(signed)) if signed else None,
                      median_absolute_lag_seconds=float(np.median(np.abs(signed))) if signed else None,
                      total_absolute_lag_seconds=float(sum(abs(value) for value in signed)),
                      interval_iou=[item[3] for item in combined] if any(item[3] is not None for item in combined) else None,
                      duration_bias_seconds=[item[4] for item in combined] if any(item[4] is not None for item in combined) else None)
        return result
    a.sort(key=lambda x: x[1]["seconds"])
    b.sort(key=lambda x: x[1]["seconds"])
    ta = np.array([row["seconds"] for _, row in a])
    tb = np.array([row["seconds"] for _, row in b])
    lower = np.searchsorted(tb, ta-tolerance_seconds, side="left")
    upper = np.searchsorted(tb, ta+tolerance_seconds, side="right")
    eligible_pairs = int(np.sum(upper-lower))
    if eligible_pairs > max_eligible_pairs:
        result["status"] = "MATCH_LIMIT"
        return result
    nodes = [(0, 0., -1, -1, -1)]
    tree = np.zeros(len(b)+1, dtype=np.int64)
    def better(x, y):
        nx, ny = nodes[x], nodes[y]
        if nx[0] != ny[0]:
            return x if nx[0] > ny[0] else y
        if nx[1] != ny[1]:
            return x if nx[1] < ny[1] else y
        return min(x, y)
    def query(end):
        best = 0
        while end:
            best = better(best, int(tree[end]))
            end -= end & -end
        return best
    for i in range(len(a)):
        pending = []
        for j in range(int(lower[i]), int(upper[i])):
            previous = query(j)
            error = abs(float(ta[i]-tb[j]))
            nodes.append((nodes[previous][0]+1, nodes[previous][1]+error, previous, i, j))
            pending.append((j+1, len(nodes)-1))
        for position, node in pending:
            while position <= len(b):
                tree[position] = better(int(tree[position]), node)
                position += position & -position
    pairs = []
    node = query(len(b))
    while node:
        _, _, prev, i, j = nodes[node]
        pairs.append((i, j))
        node = prev
    pairs.reverse()
    signed = [float(tb[j]-ta[i]) for i, j in pairs]
    m = len(pairs)
    result.update(status="OK", eligible_pairs=eligible_pairs, matched=m,
                  matched_input_index_pairs=[[a[i][0], b[j][0]] for i, j in pairs],
                  signed_lags_seconds=signed,
                  fraction_a_matched=m/len(a) if a else None,
                  fraction_b_matched=m/len(b) if b else None,
                  agreement=2*m/(len(a)+len(b)) if a or b else None,
                  median_signed_lag_seconds=float(np.median(signed)) if signed else None,
                  median_absolute_lag_seconds=float(np.median(np.abs(signed))) if signed else None,
                  total_absolute_lag_seconds=float(sum(abs(x) for x in signed)))
    if pairs and a[pairs[0][0]][1].get("family") == "burst":
        iou, bias = [], []
        for i, j in pairs:
            ra, rb = a[i][1], b[j][1]
            la, ua = ra["seconds"], ra["interval_end_seconds"]
            lb, ub = rb["seconds"], rb["interval_end_seconds"]
            intersection = max(0., min(ua, ub)-max(la, lb))
            union = max(ua, ub)-min(la, lb)
            iou.append(intersection/union if union else None)
            bias.append((ub-lb)-(ua-la))
        result["interval_iou"] = iou
        result["duration_bias_seconds"] = bias
    return result
