#!/usr/bin/env python3
"""Run the frozen direct-waveform implementation battery and bounded fixture smoke."""

import os

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_name] = "1"

import argparse
import hashlib
import json
import math
import resource
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import scipy
from scipy import signal

from eegt.waveform_events import PROTOCOL, crossings, discover, match_events


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_sha(array):
    array = np.asarray(array, dtype="<f8")
    return hashlib.sha256(array.tobytes()).hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def sine_case(case):
    fs = case["fs_hz"]
    t = np.arange(round(case["duration_seconds"]*fs), dtype=float)/fs
    return case["amplitude_uv"]*np.sin(2*np.pi*case["frequency_hz"]*t+case["phase_radians"])


def new_discovery(x, fs=250, valid=None, segments=None, **kwargs):
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[None, :]
    if valid is None:
        valid = np.ones(x.shape, dtype=bool)
    if segments is None:
        segments = [(0, x.shape[1], 0.)]
    return discover(x, fs, valid, segments, **kwargs)


def summary(result):
    families = {}
    for row in result["events"]:
        key = row["family"] + ":" + row["detector"]
        item = families.setdefault(key, {"candidate": 0, "accepted": 0, "rejected": 0})
        item["candidate"] += 1
        item["accepted" if row["accepted"] else "rejected"] += 1
    return {"families": families, "run_statuses": [run["status"] for run in result["runs"]],
            "valid_duration_seconds": sum(r["valid_duration_seconds"] for r in result["runs"]),
            "guarded_valid_duration_seconds": sum(r["guarded_valid_duration_seconds"] for r in result["runs"]),
            "rejected_duration_seconds": sum(r["rejected_duration_seconds"] for r in result["runs"]),
            "invalid_duration_seconds": result["invalid_duration_seconds"],
            "invalid_intervals": result["invalid_intervals"]}


def scientific_view(report):
    """Stable scientific values for exact comparison across fresh output roots."""
    synthetic = {key: value for key, value in report["synthetic"].items()
                 if key != "runtime_seconds"}
    return {"schema": "eegt-waveform-scientific-results/v1",
            "protocol_sha256": report["protocol_sha256"],
            "synthetic": synthetic, "fixture_status": report["fixture_status"],
            "fixture_events_sha256": report.get("fixture_events_sha256"),
            "fixture_summary": report.get("fixture_summary")}


def scored_landmarks(result, truth, fs, margin=2, tolerance_samples=2):
    """Pair with context, then censor crossing-edge pairs on both sides."""
    guard = result["runs"][0].get("guard_samples", 0)
    end = result["runs"][0]["end_sample"]
    interior_start = guard + tolerance_samples + margin
    interior_end = end - guard - tolerance_samples - margin
    output = {}
    for truth_name, family in (("extrema", "extremum"), ("inflections", "inflection")):
        groups = ("peak", "trough") if family == "extremum" else (
            "curvature_positive_to_negative", "curvature_negative_to_positive")
        errors = []
        core_truth = core_detected = missed = extra = 0
        edge_censored_truth = edge_censored_detected = 0
        context_truth = context_detected = 0
        for key in groups:
            expected = [r["nearest_sample"] for r in truth[truth_name]
                        if r.get("polarity" if family == "extremum" else "direction") == key
                        and guard-tolerance_samples <= r["nearest_sample"] < end-guard+tolerance_samples]
            detected = [r["index"] for r in result["events"]
                        if r["accepted"] and r["family"] == family
                        and r.get("polarity" if family == "extremum" else "direction") == key]
            i = j = 0
            core_truth += sum(interior_start <= q < interior_end for q in expected)
            core_detected += sum(interior_start <= q < interior_end for q in detected)
            context_truth += sum(not interior_start <= q < interior_end for q in expected)
            context_detected += sum(not interior_start <= q < interior_end for q in detected)
            while i < len(expected) and j < len(detected):
                difference = detected[j]-expected[i]
                if abs(difference) <= tolerance_samples:
                    true_core = interior_start <= expected[i] < interior_end
                    detected_core = interior_start <= detected[j] < interior_end
                    if true_core and detected_core:
                        errors.append(difference)
                    elif true_core:
                        edge_censored_truth += 1
                    elif detected_core:
                        edge_censored_detected += 1
                    i += 1
                    j += 1
                elif difference < 0:
                    extra += int(interior_start <= detected[j] < interior_end)
                    j += 1
                else:
                    missed += int(interior_start <= expected[i] < interior_end)
                    i += 1
            missed += sum(interior_start <= q < interior_end for q in expected[i:])
            extra += sum(interior_start <= q < interior_end for q in detected[j:])
        eligible_truth = core_truth-edge_censored_truth
        eligible_detected = core_detected-edge_censored_detected
        output[family] = {"truth_n": eligible_truth, "detected_n": eligible_detected,
                          "matched_n": len(errors), "missed_n": missed, "extra_n": extra,
                          "core_truth_n": core_truth, "core_detected_n": core_detected,
                          "edge_censored_truth_n": edge_censored_truth,
                          "edge_censored_detected_n": edge_censored_detected,
                          "out_of_core_context_truth_n": context_truth,
                          "out_of_core_context_detected_n": context_detected,
                          "evaluation_interval_samples": [interior_start, interior_end],
                          "max_abs_error_samples": max(map(abs, errors)) if errors else None,
                          "mean_signed_bias_samples": float(np.mean(errors)) if errors else None,
                          "mean_signed_bias_seconds": float(np.mean(errors))/fs if errors else None}
        if (len(errors)+missed != eligible_truth or len(errors)+extra != eligible_detected):
            raise AssertionError(f"scoring denominators do not reconcile for {family}")
    return output


def accepted(result, family=None, detector=None, band=None):
    return [r for r in result["events"] if r["accepted"] and
            (family is None or r["family"] == family) and
            (detector is None or r["detector"] == detector) and
            (band is None or r.get("band_hz") == band)]


def per_minute(count, seconds):
    return count*60/seconds if seconds > 0 else None


def no_oscillator(case):
    fs = case["fs_hz"]
    n = round(case["duration_seconds"]*fs)
    values = np.random.default_rng(case["seed"]).normal(size=n)
    if case["generator"] == "colored_ar1":
        values = signal.lfilter([1.], [1., -.9], values)
        values /= np.std(values)
    return case["scale_uv"]*values


def packet_case(case):
    fs = case["fs_hz"]
    t = np.arange(round(case["duration_seconds"]*fs))/fs
    envelope = np.where((t >= 10) & (t < 20), .5-.5*np.cos(2*np.pi*(t-10)/10), 0)
    rng = np.random.default_rng(case["seed"])
    return 20*envelope*np.sin(2*np.pi*8*t) + rng.normal(0, case["noise_sd_uv"], len(t))


def packet_metrics(result):
    known = (10., 20.)
    metrics = {}
    for detector in ("bycycle_contiguous", "neurodsp_dual_threshold"):
        rows = accepted(result, "burst", detector, [8., 13.])
        hits = [r for r in rows if max(r["seconds"], known[0]) < min(r["interval_end_seconds"], known[1])]
        boundary_errors = [[r["seconds"]-known[0], r["interval_end_seconds"]-known[1]] for r in hits]
        metrics[detector] = {"burst_count": len(rows), "hit": bool(hits),
                             "off_packet_bursts": len(rows)-len(hits),
                             "boundary_errors_seconds": boundary_errors}
    return metrics


def compare_same_family(a, b, family, polarity, fs=250, tolerance=.025):
    ra = [r for r in accepted(a, family) if r["polarity"] == polarity]
    rb = [r for r in accepted(b, family) if r["polarity"] == polarity]
    return match_events(ra, rb, intervals_a_seconds=[(0, a["runs"][0]["end_sample"]/a["sample_rate_hz"])],
                        intervals_b_seconds=[(0, b["runs"][0]["end_sample"]/b["sample_rate_hz"])],
                        shared_clock=True, clock_error_bound_seconds=0., tolerance_seconds=tolerance)


def synthetic_battery(protocol):
    started = time.monotonic()
    record = {"schema": "eegt-waveform-synthetic-receipt/v1", "protocol_sha256": None,
              "stationary": [], "analytic": {}, "controls": [], "packets": [],
              "targeted": {}, "sensitivities": [], "transformations": [], "hard_gates": {},
              "failure_branches": [], "runtime_seconds": None}
    failures = []
    primary_reference = None
    for case in protocol["stationary_sine"]:
        x = sine_case(case)
        result = new_discovery(x, case["fs_hz"])
        metrics = scored_landmarks(result, case["truth"], case["fs_hz"])
        row = {"id": case["id"], "array_sha256": array_sha(x), "summary": summary(result),
               "landmarks": metrics}
        record["stationary"].append(row)
        for family, value in metrics.items():
            if value["missed_n"] or value["extra_n"] or value["max_abs_error_samples"] is None or value["max_abs_error_samples"] > 2:
                failures.append(f"stationary:{case['id']}:{family}")
        if case["id"] == "sine-fs250-f5-zero":
            primary_reference = (x, result)
    record["hard_gates"]["stationary_all_36_within_2_samples_and_no_missed_extra"] = not any(x.startswith("stationary:") for x in failures)

    n = 7500
    t = np.arange(n)/250
    flat_cases = {"flat_zero": np.zeros(n), "flat_five": np.full(n, 5.),
                  "affine": 5+.2*t, "near_flat": 5+1e-10*np.sin(2*np.pi*8*t)}
    for name, x in flat_cases.items():
        result = new_discovery(x)
        record["targeted"][name] = {"array_sha256": array_sha(x), "summary": summary(result)}
        if name != "near_flat" and (result["runs"][0]["status"] != "DEGENERATE_AFFINE" or accepted(result)):
            failures.append(f"affine:{name}")
    for nshort in (2, 20):
        x = np.sin(np.arange(nshort, dtype=float))
        result = new_discovery(x)
        record["targeted"][f"short_{nshort}"] = {"array_sha256": array_sha(x), "summary": summary(result)}
        if accepted(result):
            failures.append(f"short_{nshort}_accepted")
    record["hard_gates"]["affine_exact_abstention"] = not any(x.startswith("affine:") for x in failures)
    sign_values = np.array([1., 1., -1., -1., 2., 2., 0., 0., -2., -2.])
    sign_result = crossings(sign_values, 0.)
    record["targeted"]["direct_plateau_sign"] = sign_result
    if [(r["index"], r["fractional_index"]) for r in sign_result] != [(2, 1.5), (4, 3+1/3), (6, None)]:
        failures.append("sign_convention")

    chirp = protocol["analytic_chirp"]
    phase = 2*np.pi*(chirp["f0_hz"]*t + .5*(chirp["f1_hz"]-chirp["f0_hz"])/30*t*t)
    analytic_x = chirp["amplitude_uv"]*np.sin(phase)
    chirp_result = new_discovery(analytic_x)
    record["analytic"]["chirp"] = {"array_sha256": array_sha(analytic_x),
                                     "summary": summary(chirp_result),
                                     "landmarks": scored_landmarks(chirp_result, chirp["truth"], 250,
                                                                   tolerance_samples=10)}
    asym = protocol["asymmetric_cycles"]
    phase = 2*np.pi*asym["frequency_hz"]*t
    asym_x = 20*(np.sin(phase)+.25*np.sin(2*phase))
    asym_result = new_discovery(asym_x)
    record["analytic"]["asymmetric"] = {"array_sha256": array_sha(asym_x),
                                          "summary": summary(asym_result),
                                          "landmarks": scored_landmarks(asym_result, asym["truth"], 250,
                                                                        tolerance_samples=10)}

    packet_aggregate = {}
    for case in protocol["finite_packets"]:
        x = packet_case(case)
        result = new_discovery(x, include_cycles=True, include_envelopes=True)
        metrics = packet_metrics(result)
        record["packets"].append({"id": case["id"], "noise_sd_uv": case["noise_sd_uv"],
                                   "array_sha256": array_sha(x), "summary": summary(result),
                                   "metrics": metrics,
                                   "landmarks": scored_landmarks(result, protocol["packet_analytic_truth"], 250,
                                                                 tolerance_samples=10)})
        for detector, data in metrics.items():
            key = f"{detector}:noise{case['noise_sd_uv']}"
            agg = packet_aggregate.setdefault(key, {"trials": 0, "hits": 0, "off_packet_bursts": 0})
            agg["trials"] += 1
            agg["hits"] += int(data["hit"])
            agg["off_packet_bursts"] += data["off_packet_bursts"]
    record["packet_aggregate"] = {key: {**item, "hit_rate": item["hits"]/item["trials"]}
                                  for key, item in packet_aggregate.items()}

    bands = protocol["configurations"]["cycle_bands_hz"]
    definitions = [("cycle", "bycycle_1.2.0", band, "cycle") for band in bands] + [
        ("burst", detector, band, "cycle" if detector == "bycycle_contiguous" else "envelope")
        for detector in ("bycycle_contiguous", "neurodsp_dual_threshold") for band in bands]
    for case in protocol["no_oscillator_controls"]:
        x = no_oscillator(case)
        full = case["seed"] in protocol["control_cycle_burst_seed_subset"]
        result = new_discovery(x, include_cycles=full, include_envelopes=full)
        guarded_seconds = summary(result)["guarded_valid_duration_seconds"]
        landmarks = len(accepted(result, "extremum")) + len(accepted(result, "inflection"))
        by_definition_band = {}
        for family, detector, band, source in definitions:
            label = f"{band[0]:g}-{band[1]:g}"
            key = f"{detector}:{label}"
            receipt_key = f"{source}:{label}Hz"
            status = result["runs"][0].get("oscillation_status", {}).get(receipt_key) if full else "NOT_REQUESTED"
            receipt = result["filters"].get(receipt_key)
            count = len(accepted(result, family, detector, band)) if status == "OK" else None
            seconds = max(0., (len(x)-2*receipt["guard_samples"])/case["fs_hz"]) if status == "OK" else None
            by_definition_band[key] = {"status": status, "accepted_n": count,
                                       "false_detection_trial": bool(count) if count is not None else None,
                                       "guarded_valid_seconds": seconds}
        record["controls"].append({"id": case["id"], "generator": case["generator"],
                                   "seed": case["seed"], "array_sha256": array_sha(x),
                                   "guarded_valid_seconds": guarded_seconds,
                                   "derivative_landmarks_n": landmarks,
                                   "derivative_landmarks_per_valid_minute": per_minute(landmarks, guarded_seconds),
                                   "cycle_burst_requested": full,
                                   "by_definition_band": by_definition_band,
                                   "summary": summary(result) if full else None})
    control_agg = {}
    for kind in ("white", "colored_ar1"):
        rows = [r for r in record["controls"] if r["generator"] == kind]
        duration = sum(r["guarded_valid_seconds"] for r in rows)
        control_agg[kind] = {"derivative_trials": len(rows),
                             "derivative_landmarks_n": sum(r["derivative_landmarks_n"] for r in rows),
                             "guarded_valid_seconds": duration,
                             "derivative_landmarks_per_valid_minute": per_minute(sum(r["derivative_landmarks_n"] for r in rows), duration),
                             "oscillation_subsets": {}}
        for subset_name, subset_rows in (("first10", [r for r in rows if r["seed"] < 10]),
                                         ("all100", rows)):
            by_band = {}
            for _, detector, band, _ in definitions:
                key = f"{detector}:{band[0]:g}-{band[1]:g}"
                scored = [r["by_definition_band"][key] for r in subset_rows
                          if r["by_definition_band"][key]["status"] == "OK"]
                valid_seconds = sum(r["guarded_valid_seconds"] for r in scored)
                count = sum(r["accepted_n"] for r in scored)
                by_band[key] = {"requested_trials": len(subset_rows), "scored_trials": len(scored),
                                "abstained_trials": len(subset_rows)-len(scored),
                                "false_detection_rows_n": count,
                                "false_detection_trials_n": sum(r["false_detection_trial"] for r in scored),
                                "guarded_valid_seconds": valid_seconds,
                                "false_detection_rows_per_valid_minute": per_minute(count, valid_seconds)}
            control_agg[kind]["oscillation_subsets"][subset_name] = by_band
    record["control_aggregate"] = control_agg
    complete_controls = all(
        item["scored_trials"] == 100 and item["abstained_trials"] == 0
        for kind in control_agg.values()
        for item in kind["oscillation_subsets"]["all100"].values())
    record["hard_gates"]["all_100_fixed_control_seeds_scored_per_definition_band"] = complete_controls
    if not complete_controls:
        failures.append("control_cycle_burst_coverage")

    # Targeted artifact fixtures use the same 30-second native clock.
    artifact = {"spike": np.where(np.arange(n) == 3750, 100., 0.),
                "step": np.where(np.arange(n) >= 3750, 20., 0.),
                "clipped": np.clip(20*np.sin(2*np.pi*8*t), -8, 8)}
    for name, x in artifact.items():
        result = new_discovery(x)
        s = summary(result)
        duration = s["guarded_valid_duration_seconds"]
        landmarks = len(accepted(result, "extremum"))+len(accepted(result, "inflection"))
        record["targeted"][name] = {"array_sha256": array_sha(x), "summary": s,
                                      "derivative_landmarks_n": landmarks,
                                      "derivative_landmarks_per_valid_minute": per_minute(landmarks, duration)}
    gap = np.ones((1, n), dtype=bool)
    gap[:, 3000:3250] = False
    gap_result = new_discovery(20*np.sin(2*np.pi*8*t), valid=gap,
                               include_cycles=True, include_envelopes=True)
    gap_ok = all(row["support_end_sample"] <= 3000 or row["support_start_sample"] >= 3250
                 for row in accepted(gap_result))
    record["targeted"]["gap"] = {"mask_sha256": hashlib.sha256(gap.tobytes()).hexdigest(),
                                  "summary": summary(gap_result), "accepted_support_clear": gap_ok}
    if not gap_ok:
        failures.append("gap_support_crossing")
    record["hard_gates"]["no_accepted_support_crosses_gap"] = gap_ok
    reset_result = new_discovery(20*np.sin(2*np.pi*8*t), segments=[(0, 3750, 0.), (3750, 7500, 0.)])
    reset_ok = all(row["support_start_sample"] is None or
                   0 <= row["support_start_sample"] <= row["support_end_sample"] <= 3750
                   for row in accepted(reset_result))
    record["targeted"]["clock_reset"] = {"timing_segments": [[0, 3750, 0], [3750, 7500, 0]],
                                          "summary": summary(reset_result),
                                          "segment_keys": sorted({e["segment_key"] for e in reset_result["events"]}),
                                          "accepted_support_within_own_segment": reset_ok}
    record["hard_gates"]["no_accepted_support_crosses_clock_reset"] = reset_ok
    if not reset_ok:
        failures.append("clock_reset_support_crossing")

    base_x, base = primary_reference
    for ms in (21, 31, 51):
        for band in ((.5, 40.), (1., 40.), (1., 30.)):
            result = new_discovery(base_x, smoothing_ms=ms, passband_hz=band)
            comparison = compare_same_family(base, result, "extremum", "peak")
            record["sensitivities"].append({"smoothing_ms": ms, "passband_hz": list(band),
                                            "summary": summary(result), "comparison_to_primary": comparison,
                                            "filter_guard_samples": result["filters"].get("waveform", {}).get("guard_samples")})
    for name, x in (("gain_offset", 2*base_x+7), ("polarity_inverted", -base_x)):
        transformed = new_discovery(x)
        record["transformations"].append({"name": name, "array_sha256": array_sha(x),
                                           "native_fs_hz": 250, "output_fs_hz": 250,
                                           "clock_mapping": "unchanged native sample clock",
                                           "summary": summary(transformed)})
    native_contacts = np.vstack([20*np.sin(2*np.pi*8*t), 10*np.sin(2*np.pi*8*t+np.pi/5),
                                 5*np.sin(2*np.pi*5*t), 3*np.sin(2*np.pi*5*t+np.pi/3)])
    for name, x in (("native_contacts", native_contacts),
                    ("common_average", native_contacts-native_contacts.mean(axis=0)),
                    ("pair_x0_minus_x1", native_contacts[0:1]-native_contacts[1:2])):
        transformed = new_discovery(x)
        record["transformations"].append({"name": name, "array_sha256": array_sha(x),
                                           "native_fs_hz": 250, "output_fs_hz": 250,
                                           "clock_mapping": "unchanged synthetic native clock; voltage reference changed" if name != "native_contacts" else "synthetic native clock",
                                           "summary": summary(transformed)})
    for line in (50, 60):
        x = base_x+20*np.sin(2*np.pi*line*t)
        for notch in (None, 50, 60):
            result = new_discovery(x, notch_hz=notch)
            record["sensitivities"].append({"line_hz": line, "notch_hz": notch,
                                            "array_sha256": array_sha(x), "summary": summary(result),
                                            "filter_guard_samples": result["filters"].get("waveform", {}).get("guard_samples"),
                                            "comparison_to_clean": compare_same_family(base, result, "extremum", "peak")})
    for output_fs, up, down in ((200, 4, 5), (500, 2, 1)):
        x = signal.resample_poly(base_x, up, down)
        result = new_discovery(x, fs=output_fs)
        record["transformations"].append({"name": f"resample_{output_fs}", "array_sha256": array_sha(x),
                                           "native_fs_hz": 250, "output_fs_hz": output_fs,
                                           "polyphase_up_down": [up, down],
                                           "clock_mapping": "same continuous origin with exact rational sample-time mapping",
                                           "native_resolution_floor_seconds": 1/250,
                                           "output_sample_period_seconds": 1/output_fs,
                                           "summary": summary(result),
                                           "comparison_to_native": compare_same_family(base, result, "extremum", "peak")})
    all_invalid = new_discovery(np.zeros((1, 7500)), valid=np.zeros((1, 7500), dtype=bool))
    record["targeted"]["zero_valid_duration"] = {"summary": summary(all_invalid),
                                                   "derivative_landmarks_per_valid_minute": per_minute(0, 0)}
    if record["targeted"]["zero_valid_duration"]["derivative_landmarks_per_valid_minute"] is not None:
        failures.append("zero_valid_duration_denominator")

    # Matching edge contracts, including explicit eligible-pair overflow.
    def event(t):
        return {"seconds": t, "support_start_seconds": t, "support_end_seconds": t,
                "accepted": True, "segment_key": "segment_0", "channel_key": "channel_0",
                "family": "extremum", "polarity": "peak", "direction": "positive_to_negative"}
    common = {"intervals_a_seconds": [(0, 2)], "intervals_b_seconds": [(0, 2)],
              "shared_clock": True, "clock_error_bound_seconds": .001, "tolerance_seconds": .1}
    matching = {"duplicate_tie": match_events([event(0), event(0)], [event(0), event(0)], **common),
                "empty_empty": match_events([], [], **common),
                "unknown_clock": match_events([event(0)], [event(0)], **{**common, "clock_error_bound_seconds": None}),
                "overflow": match_events([event(0)]*3, [event(0)]*3, **{**common, "max_eligible_pairs": 8})}
    record["targeted"]["matching"] = matching
    match_ok = (matching["duplicate_tie"]["matched_input_index_pairs"] == [[0, 0], [1, 1]]
                and matching["empty_empty"]["agreement"] is None
                and matching["unknown_clock"]["status"] == "NOT_COMPARABLE"
                and matching["overflow"]["status"] == "MATCH_LIMIT")
    record["hard_gates"]["matching_invariants"] = match_ok
    if not match_ok:
        failures.append("matching_invariants")
    packet_case_result = new_discovery(packet_case(protocol["finite_packets"][0]), include_cycles=True)
    units_ok = all((row["period_seconds"] is None or row["period_seconds"] > 0)
                   for row in accepted(packet_case_result, "cycle"))
    record["hard_gates"]["cycle_units_positive_seconds"] = units_ok
    if not units_ok:
        failures.append("cycle_units")
    scored_cases = ([case["landmarks"] for case in record["stationary"]] +
                    [case["landmarks"] for case in record["analytic"].values()] +
                    [case["landmarks"] for case in record["packets"]])
    denominators_ok = all(value["matched_n"]+value["missed_n"] == value["truth_n"] and
                          value["matched_n"]+value["extra_n"] == value["detected_n"] and
                          value["core_truth_n"]-value["edge_censored_truth_n"] == value["truth_n"] and
                          value["core_detected_n"]-value["edge_censored_detected_n"] == value["detected_n"]
                          for case in scored_cases for value in case.values())
    record["hard_gates"]["all_scoring_denominators_reconcile"] = denominators_ok
    if not denominators_ok:
        failures.append("scoring_denominators")
    chirp_scored = all(value["truth_n"] > 0 and value["matched_n"] > 0
                       for value in record["analytic"]["chirp"]["landmarks"].values())
    record["hard_gates"]["chirp_truth_nonempty_and_matched"] = chirp_scored
    if not chirp_scored:
        failures.append("chirp_truth_scoring")
    record["failure_branches"] = failures
    record["hard_gates_passed"] = not failures
    record["runtime_seconds"] = time.monotonic()-started
    return record


def fixture_smoke(input_root, output_root):
    started = time.monotonic()
    fixture_path = input_root / "exposed-fixture.npz"
    with np.load(fixture_path, allow_pickle=False) as source:
        x = source["samples_uv"]
        mask = source["valid"]
        fs = float(source["sample_rate_hz"])
        original_segments = source["segments"]
    segments = [(int(a), int(b), 0.) for a, b in original_segments]
    result = new_discovery(x, fs=fs, valid=mask, segments=segments,
                           include_cycles=True, include_envelopes=True)
    events_path = output_root / "FIXTURE-EVENTS.jsonl"
    with events_path.open("w") as handle:
        for row in result["events"]:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)+"\n")
    np.savez_compressed(output_root / "FIXTURE-MASKS.npz", valid=mask, segments=original_segments)
    curator = json.loads((input_root / "exposed-fixture-curator.json").read_text())
    receipt = {"schema": "eegt-bounded-fixture-smoke/v1", "scope": "compatibility only; no analytical inference",
               "fixture_sha256": sha(fixture_path), "curator_receipt_sha256": sha(input_root / "exposed-fixture-curator.json"),
               "source_binding": curator, "sample_rate_hz": fs, "shape": list(x.shape),
               "numeric_array_sha256": array_sha(x), "mask_sha256": hashlib.sha256(mask.tobytes()).hexdigest(),
               "timing_segments": segments, "summary": summary(result), "runs": result["runs"],
               "filters_path": "FIXTURE-FILTERS.json", "events_path": events_path.name,
               "events_sha256": sha(events_path), "runtime_seconds": time.monotonic()-started}
    save_json(output_root / "FIXTURE-FILTERS.json", result["filters"])
    save_json(output_root / "FIXTURE.json", receipt)
    return receipt


def write_report(output_root, report):
    save_json(output_root / "REPORT.json", report)
    synthetic = report.get("synthetic", {})
    max_error = max((v["max_abs_error_samples"] for case in synthetic.get("stationary", [])
                     for v in case["landmarks"].values() if v["max_abs_error_samples"] is not None), default=None)
    lines = ["# Direct waveform event validation", "", f"Synthetic hard gates: **{'PASS' if synthetic.get('hard_gates_passed') else 'FAIL'}**.",
             "", f"Stationary cases: {len(synthetic.get('stationary', []))}/36; maximum interior localization error: {max_error} native sample(s). Noise trials: {len(synthetic.get('controls', []))}/200; packet trials: {len(synthetic.get('packets', []))}/30.",
             "", "## Hard gates", ""]
    for name, value in synthetic.get("hard_gates", {}).items():
        lines.append(f"- {name}: {'PASS' if value else 'FAIL'}")
    if synthetic.get("failure_branches"):
        lines += ["", "## Excluded branches", ""] + [f"- {item}" for item in synthetic["failure_branches"]]
    lines += ["", "## Stochastic controls", ""]
    for name, item in synthetic.get("control_aggregate", {}).items():
        lines.append(f"- {name}: {item['derivative_landmarks_per_valid_minute']:.1f} derivative landmarks per guarded valid minute across {item['derivative_trials']} trials.")
        for key, value in item["oscillation_subsets"]["all100"].items():
            lines.append(f"  - {key}: {value['false_detection_rows_n']} rows in {value['false_detection_trials_n']}/{value['scored_trials']} scored negative trials; {value['abstained_trials']} abstentions among {value['requested_trials']} fixed seeds.")
        lines.append("  - Earlier first10 subset counts are retained separately in SYNTHETIC.json; the original first10 receipt is preserved under scratch/review-r1-before/out/SYNTHETIC.json.")
    lines += ["", "## Finite packets", ""]
    for name, item in synthetic.get("packet_aggregate", {}).items():
        lines.append(f"- {name}: {item['hits']}/{item['trials']} packet trials hit; {item['off_packet_bursts']} off-packet burst rows.")
    if report.get("fixture_summary"):
        families = report["fixture_summary"]["families"]
        lines += ["", "## Bounded compatibility smoke", "",
                  f"Four numeric channels × 30 native seconds; {sum(v['accepted'] for v in families.values())} accepted event rows and {sum(v['rejected'] for v in families.values())} rejected candidate rows. No additional data were acquired."]
    lines += ["", "## Scope", "", "Derivative rates describe voltage landmarks per guarded valid minute. Noise has no planted oscillator; its scored cycle and burst rows are false detections under that generator. No brain-state or clinical specificity is inferred.", "",
              "Cycle and burst definitions remain exploratory because these controls do not establish empirical specificity. Failed hard-gate branches, if any, are excluded from confirmatory use.", "",
              f"Bounded real fixture: **{report.get('fixture_status')}**. It runs only after every synthetic hard gate passes.",
              "", "`SCIENTIFIC.json` excludes runtime measurements so its SHA256 can be compared with a fresh rerun on the pinned environment.",
              "", "The frozen method recheck and implementation review were accepted; see the separate acceptance receipts. This battery does not establish empirical event specificity or clinical meaning.", ""]
    (output_root / "REPORT.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    input_root, output_root, protocol_path = args.input_root.resolve(), args.output_root.resolve(), args.protocol.resolve()
    if not input_root.is_dir() or not protocol_path.is_file():
        parser.error("input root and frozen protocol must exist")
    existing = list(output_root.iterdir()) if output_root.exists() else []
    if any(p.name != "BATTERY-PROTOCOL.json" or p.resolve() != protocol_path for p in existing):
        parser.error("output root is occupied; choose a fresh path")
    protocol = json.loads(protocol_path.read_text())
    if protocol.get("method_sha256") != sha(input_root / "METHODS.md") or len(protocol.get("stationary_sine", [])) != 36:
        parser.error("frozen protocol does not match method or required stationary cases")
    output_root.mkdir(parents=True, exist_ok=True)
    if output_root / "BATTERY-PROTOCOL.json" != protocol_path:
        shutil.copy2(protocol_path, output_root / "BATTERY-PROTOCOL.json")
    started = time.monotonic()
    save_json(output_root / "COMMAND.json", {"argv": sys.argv, "python": sys.version,
                                              "blas_threads": 1, "method_sha256": sha(input_root / "METHODS.md"),
                                              "protocol_sha256": sha(protocol_path)})
    import bycycle
    import neurodsp
    import pandas
    versions = {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__,
                "bycycle": bycycle.__version__, "neurodsp": neurodsp.__version__, "pandas": pandas.__version__}
    save_json(output_root / "VERSIONS.json", versions)
    report = {"schema": "eegt-waveform-validation-report/v1", "protocol_sha256": sha(protocol_path),
              "method_sha256": sha(input_root / "METHODS.md"), "versions": versions,
              "fixture_status": "NOT_RUN_SYNTHETIC_PENDING", "agent_monetary_cost_usd": "UNKNOWN"}
    try:
        synthetic = synthetic_battery(protocol)
        synthetic["protocol_sha256"] = sha(protocol_path)
        report["synthetic"] = synthetic
        save_json(output_root / "SYNTHETIC.json", synthetic)
        if synthetic["hard_gates_passed"]:
            receipt = fixture_smoke(input_root, output_root)
            report["fixture_status"] = "COMPATIBILITY_SMOKE_COMPLETE"
            report["fixture_summary"] = receipt["summary"]
            report["fixture_events_sha256"] = receipt["events_sha256"]
        else:
            report["fixture_status"] = "NOT_RUN_SYNTHETIC_HARD_GATE_FAILURE"
    except Exception as error:
        report["fixture_status"] = "NOT_RUN_BATTERY_ERROR"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        report["runtime_seconds"] = time.monotonic()-started
        report["max_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if "synthetic" in report:
            save_json(output_root / "SCIENTIFIC.json", scientific_view(report))
        write_report(output_root, report)
        manifest = {}
        for path in sorted(output_root.iterdir()):
            if path.is_file() and path.name != "MANIFEST.json":
                manifest[f"out/{path.name}"] = {"bytes": path.stat().st_size, "sha256": sha(path)}
        repo_root = Path(__file__).resolve().parents[1]
        for name in ("eegt/waveform_events.py", "tests/test_waveform_events.py",
                     "scripts/validate_waveform_events.py", "requirements-events.lock",
                     "scripts/freeze_waveform_protocol.py"):
            path = repo_root / name
            manifest["repo/" + name] = {"bytes": path.stat().st_size, "sha256": sha(path)}
        save_json(output_root / "MANIFEST.json", {"schema": "eegt-artifact-manifest/v1", "files": manifest})
    print(json.dumps({"hard_gates_passed": report["synthetic"]["hard_gates_passed"],
                      "fixture_status": report["fixture_status"], "runtime_seconds": report["runtime_seconds"]}))


if __name__ == "__main__":
    main()
