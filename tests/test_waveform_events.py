"""Scientific interface checks for direct waveform measurements."""

import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from eegt.waveform_events import crossings, discover, filter_support, match_events


def sine(fs=250, f=8, seconds=30, phase=0):
    t = np.arange(round(fs * seconds)) / fs
    return (20 * np.sin(2 * np.pi * f * t + phase))[None, :]


def run(x, fs=250, valid=None, **kwargs):
    if valid is None:
        valid = np.ones_like(x, dtype=bool)
    return discover(x, fs, valid, [(0, x.shape[1], 0.0)], **kwargs)


class WaveformEventsTests(unittest.TestCase):
    def test_cycle_and_envelope_guard_includes_preceding_broadband(self):
        broadband = filter_support(250.)
        for band in ((4., 8.), (8., 13.), (13., 30.)):
            for envelope in (False, True):
                receipt = filter_support(250., narrowband=band, envelope=envelope)
                self.assertGreaterEqual(receipt["guard_samples"], broadband["guard_samples"])
                self.assertEqual(len(receipt["fir_kernel"]) % 2, 1)

    def test_battery_cli_refuses_occupied_output(self):
        script = Path(__file__).parents[1] / "scripts" / "validate_waveform_events.py"
        protocol = Path(__file__).parents[1] / "protocol" / "waveform-battery.json"
        with tempfile.TemporaryDirectory() as dirname:
            Path(dirname, "existing.txt").write_text("keep")
            result = subprocess.run([sys.executable, str(script), "--input-root", dirname,
                                     "--output-root", dirname, "--protocol", str(protocol)],
                                    env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1])},
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("output root is occupied", result.stderr)
            self.assertEqual(Path(dirname, "existing.txt").read_text(), "keep")

    def test_scientific_receipt_excludes_runtime_measurements(self):
        from scripts.validate_waveform_events import scientific_view
        left = {"protocol_sha256": "abc", "synthetic": {"hard_gates_passed": True,
                "stationary": [{"id": "case", "max_error_samples": 1}], "runtime_seconds": 12.},
                "fixture_status": "COMPATIBILITY_SMOKE_COMPLETE",
                "fixture_events_sha256": "events", "runtime_seconds": 13., "max_rss_bytes": 100}
        right = {**left, "runtime_seconds": 14., "max_rss_bytes": 200,
                 "synthetic": {**left["synthetic"], "runtime_seconds": 11.}}
        self.assertEqual(scientific_view(left), scientific_view(right))
        self.assertNotIn("runtime_seconds", scientific_view(left)["synthetic"])

    def test_sign_crossings_keep_direct_and_plateau_indices(self):
        values = np.array([1., 1., -1., -1., 2., 2., 0., 0., -2., -2.])
        rows = crossings(values, 0.0)
        self.assertEqual([(r["index"], r["fractional_index"], r["direction"]) for r in rows],
                         [(2, 1.5, "positive_to_negative"), (4, 3 + 1/3, "negative_to_positive"),
                          (6, None, "positive_to_negative")])
        self.assertEqual(crossings([1, -1, -1], 0), [])
        self.assertEqual(rows[0]["sign_flank"], [0, 4])
        self.assertEqual(rows[2]["sign_flank"], [4, 10])

    def test_chirp_truth_labels_follow_independent_analytic_derivatives(self):
        from scripts.freeze_waveform_protocol import chirp_truth
        fs, duration, f0, f1 = 250, 30, 3, 20
        slope = (f1-f0)/duration
        truth = chirp_truth(fs, duration, f0, f1, 0.)
        self.assertGreater(len(truth["extrema"]), 100)
        self.assertGreater(len(truth["inflections"]), 100)
        def derivatives(t):
            angle = 2*math.pi*(f0*t+.5*slope*t*t)
            angular_rate = 2*math.pi*(f0+slope*t)
            angular_acceleration = 2*math.pi*slope
            return (20*angular_rate*math.cos(angle),
                    20*(angular_acceleration*math.cos(angle)-angular_rate**2*math.sin(angle)))
        for family, component in (("extrema", 0), ("inflections", 1)):
            for row in truth[family]:
                t = row["seconds"]
                h = min(1e-5, t/2, (duration-t)/2)
                self.assertGreater(h, 0)
                before, after = derivatives(t-h)[component], derivatives(t+h)[component]
                self.assertLess(before*after, 0, (family, row))
                if family == "extrema":
                    self.assertEqual(row["polarity"], "peak" if before > 0 else "trough")
                else:
                    self.assertEqual(row["direction"], "curvature_positive_to_negative" if before > 0
                                     else "curvature_negative_to_positive")

    def test_chirp_and_asymmetric_scoring_have_reconciled_denominators(self):
        from scripts.freeze_waveform_protocol import asymmetric_truth, chirp_truth
        from scripts.validate_waveform_events import scored_landmarks
        fs, duration = 250, 30
        t = np.arange(fs*duration)/fs
        chirp = 20*np.sin(2*np.pi*(3*t+.5*(17/30)*t*t))
        asym_phase = 2*np.pi*8*t
        asym = 20*(np.sin(asym_phase)+.25*np.sin(2*asym_phase))
        cases = ((chirp, chirp_truth(fs, duration, 3, 20, 0.)),
                 (asym, asymmetric_truth(fs, duration, 8)))
        for x, truth in cases:
            scored = scored_landmarks(run(x[None, :]), truth, fs, tolerance_samples=10)
            for family in ("extremum", "inflection"):
                value = scored[family]
                self.assertGreater(value["truth_n"], 0)
                self.assertGreater(value["matched_n"], 0)
                self.assertEqual(value["matched_n"]+value["missed_n"], value["truth_n"])
                self.assertEqual(value["matched_n"]+value["extra_n"], value["detected_n"])
                self.assertEqual(value["core_truth_n"]-value["edge_censored_truth_n"], value["truth_n"])
                self.assertEqual(value["core_detected_n"]-value["edge_censored_detected_n"], value["detected_n"])
                self.assertIsNotNone(value["mean_signed_bias_samples"])
        asymmetric_extrema = scored_landmarks(run(asym[None, :]), cases[1][1], fs,
                                              tolerance_samples=10)["extremum"]
        self.assertGreater(asymmetric_extrema["edge_censored_truth_n"] +
                           asymmetric_extrema["edge_censored_detected_n"], 0)

    def test_guard_requires_both_sign_flanks_and_records_full_support(self):
        guard = filter_support(250.)["guard_samples"]
        rejected_at_guard = []
        for phase in (0., math.pi/2, math.pi/4, 3*math.pi/4):
            result = run(sine(phase=phase))
            for row in result["events"]:
                if row["family"] not in ("extremum", "inflection"):
                    continue
                self.assertEqual(row["support_start_sample"],
                                 row["sign_flank_start_sample"]-guard)
                self.assertEqual(row["support_end_sample"],
                                 row["sign_flank_end_sample"]+guard)
                if row["accepted"]:
                    self.assertGreaterEqual(row["sign_flank_start_sample"], guard)
                    self.assertLessEqual(row["sign_flank_end_sample"], 7500-guard)
                    self.assertGreaterEqual(row["support_start_sample"], 0)
                    self.assertLessEqual(row["support_end_sample"], 7500)
                elif ("SIGN_FLANK_FILTER_GUARD" in row["rejection_reasons"] and
                      guard <= row["index"] < 7500-guard):
                    rejected_at_guard.append(row)
        self.assertTrue(rejected_at_guard)

    def test_affine_abstains_and_short_runs_are_explicit(self):
        for x in (np.zeros((1, 7500)), np.ones((1, 7500)) * 5,
                  (5 + .2 * np.arange(7500) / 250)[None, :]):
            result = run(x)
            self.assertEqual(result["runs"][0]["status"], "DEGENERATE_AFFINE")
            self.assertFalse(any(row["accepted"] for row in result["events"]))
        self.assertEqual(run(np.sin(np.arange(20., dtype=float))[None, :])["runs"][0]["status"],
                         "UNSUPPORTED_SHORT_RUN")

    def test_sine_units_geometry_and_gap_support(self):
        x = sine(f=5, phase=math.pi / 7)
        valid = np.ones_like(x, bool)
        valid[:, 3000:3250] = False
        result = run(x, valid=valid, include_cycles=True, include_envelopes=True)
        self.assertEqual(result["invalid_intervals"],
                         [{"segment_key": "segment_0", "channel_key": "channel_0",
                           "start_sample": 3000, "end_sample": 3250,
                           "duration_seconds": 1.0, "reason": "INVALID_MASK"}])
        accepted = [r for r in result["events"] if r["accepted"] and r["family"] == "extremum"]
        self.assertGreater(len(accepted), 30)
        self.assertTrue(all(r["support_end_sample"] <= 3000 or r["support_start_sample"] >= 3250
                            for r in accepted))
        self.assertTrue(all(abs(r["seconds"] - r["index"] / 250) < 1e-12 for r in accepted))
        self.assertTrue(all(r["amplitude_uv"] is not None and r["slope_uv_per_second"] is not None
                            and r["curvature_uv_per_second2"] is not None for r in accepted))
        self.assertTrue(all(r["path_length"] is None and r["turning_angle_radians"] is None
                            and r["return_distance"] is None for r in accepted))

    def test_rate_rejection_and_clock_segments(self):
        x = sine(fs=100, seconds=30)
        self.assertEqual(run(x, fs=100)["runs"][0]["status"], "UNSUPPORTED_RATE")
        slower = run(x, fs=100, include_cycles=True)
        self.assertTrue(any(row["family"] == "cycle" for row in slower["events"]))
        x = sine(seconds=30)
        result = discover(x, 250, np.ones_like(x, bool), [(0, 3750, 0.0), (3750, 7500, 0.0)])
        self.assertEqual({r["segment_key"] for r in result["events"]}, {"segment_0", "segment_1"})

    def test_bycycle_and_envelope_keep_distinct_units(self):
        result = run(sine(), include_cycles=True, include_envelopes=True)
        cycles = [r for r in result["events"] if r["family"] == "cycle" and r["accepted"]]
        self.assertTrue(cycles)
        self.assertTrue(all(r["period_seconds"] > 0 and r["amplitude_uv"] > 0 for r in cycles))
        self.assertTrue(all(r["interval_end_sample"] > r["index"] for r in cycles))
        self.assertEqual({r["detector"] for r in result["events"] if r["family"] == "burst"},
                         {"bycycle_contiguous", "neurodsp_dual_threshold"} &
                         {r["detector"] for r in result["events"] if r["family"] == "burst"})
        for burst in (r for r in result["events"] if r["family"] == "burst" and
                      r["detector"] == "bycycle_contiguous" and r["accepted"]):
            adjacent_rejected = [cycle for cycle in result["events"] if cycle["family"] == "cycle"
                                 and cycle["band_hz"] == burst["band_hz"] and cycle["cycle_membership"]
                                 and not cycle["accepted"] and
                                 (cycle["interval_end_sample"] == burst["index"] or
                                  cycle["index"] == burst["interval_end_sample"])]
            self.assertFalse(adjacent_rejected, "accepted burst boundary is guard-censored")

    def test_matching_objective_pairs_nulls_and_abstentions(self):
        def ev(t, i):
            return {"seconds": t, "support_start_seconds": t, "support_end_seconds": t,
                    "accepted": True, "segment_key": "segment_0", "channel_key": "channel_0",
                    "family": "extremum", "polarity": "peak", "index": i}
        common = {"intervals_a_seconds": [(0, 2)], "intervals_b_seconds": [(0, 2)],
                  "shared_clock": True, "clock_error_bound_seconds": 0.001, "tolerance_seconds": .1}
        result = match_events([ev(0, 0), ev(.1, 1)], [ev(.08, 2), ev(.18, 3)], **common)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["matched_input_index_pairs"], [[0, 0], [1, 1]])
        self.assertEqual(result["signed_lags_seconds"], [.08, .07999999999999999])
        self.assertIsNone(match_events([], [], **common)["agreement"])
        self.assertEqual(match_events([ev(0, 0)], [], **common)["fraction_a_matched"], 0)
        self.assertIsNone(match_events([ev(0, 0)], [], **common)["fraction_b_matched"])
        self.assertEqual(match_events([ev(0, 0)], [], **{**common, "clock_error_bound_seconds": None})["status"],
                         "NOT_COMPARABLE")
        self.assertEqual(match_events([ev(0, 0)] * 3, [ev(0, 0)] * 3,
                                      **{**common, "max_eligible_pairs": 8})["status"], "MATCH_LIMIT")

    def test_matching_matches_small_exhaustive_optimum_and_shared_support(self):
        def ev(t, width=0):
            return {"seconds": t, "support_start_seconds": t-width,
                    "support_end_seconds": t+width, "accepted": True,
                    "segment_key": "segment_0", "channel_key": "channel_0",
                    "family": "extremum", "polarity": "peak", "direction": "positive_to_negative"}
        from functools import lru_cache
        @lru_cache(None)
        def optimum(a, b, i=0, j=0):
            if i == len(a) or j == len(b):
                return (0, 0.)
            choices = [optimum(a, b, i+1, j), optimum(a, b, i, j+1)]
            if a[i]-.03 <= b[j] <= a[i]+.03:
                count, cost = optimum(a, b, i+1, j+1)
                choices.append((count+1, cost+abs(a[i]-b[j])))
            return max(choices, key=lambda pair: (pair[0], -pair[1]))
        values = ((0., .04, .08), (.02, .06), (0., 0., .04), (.01, .03, .07))
        for a in values:
            for b in values:
                result = match_events([ev(t) for t in a], [ev(t) for t in b],
                                      intervals_a_seconds=[(0, 1)], intervals_b_seconds=[(0, 1)],
                                      shared_clock=True, clock_error_bound_seconds=0., tolerance_seconds=.03)
                count, cost = optimum(a, b)
                self.assertEqual(result["matched"], count)
                self.assertAlmostEqual(result["total_absolute_lag_seconds"], cost)
                self.assertEqual(len({i for i, _ in result["matched_input_index_pairs"]}), count)
                self.assertEqual(len({j for _, j in result["matched_input_index_pairs"]}), count)
        partial = match_events([ev(.5, .2)], [ev(.5)], intervals_a_seconds=[(0, 1)],
                               intervals_b_seconds=[(.4, 1)], shared_clock=True,
                               clock_error_bound_seconds=0., tolerance_seconds=.025)
        self.assertEqual((partial["n_a_before"], partial["n_a"], partial["n_b"],
                          partial["common_duration_seconds"]), (1, 0, 1, .6))
        a, b = ev(.2), ev(.3)
        for row, finish in ((a, .5), (b, .6)):
            row.update(family="burst", band_hz=[8., 13.], definition="cycle_contiguity",
                       interval_end_seconds=finish, support_end_seconds=finish)
        burst = match_events([a], [b], intervals_a_seconds=[(0, 1)],
                             intervals_b_seconds=[(0, 1)], shared_clock=True,
                             clock_error_bound_seconds=0., tolerance_seconds=.11)
        self.assertEqual(burst["matched_input_index_pairs"], [[0, 0]])
        self.assertAlmostEqual(burst["interval_iou"][0], .5)
        self.assertAlmostEqual(burst["duration_bias_seconds"][0], 0.)

    def test_matching_separate_polarities_can_cross_in_time(self):
        def ev(t, polarity):
            return {"seconds": t, "support_start_seconds": t,
                    "support_end_seconds": t, "accepted": True,
                    "segment_key": "segment_0", "channel_key": "channel_0",
                    "family": "extremum", "polarity": polarity, "direction": None}
        a = [ev(0, "peak"), ev(1, "trough")]
        b = [ev(0, "trough"), ev(1, "peak")]
        kwargs = {"intervals_a_seconds": [(0, 2)], "intervals_b_seconds": [(0, 2)],
                  "shared_clock": True, "clock_error_bound_seconds": 0.,
                  "tolerance_seconds": 1.1}
        result = match_events(a, b, **kwargs)
        self.assertEqual(result["matched_input_index_pairs"], [[0, 1], [1, 0]])
        self.assertEqual(result["matched"], 2)
        one_empty = match_events(a, [], **kwargs)
        self.assertEqual(one_empty["fraction_a_matched"], 0.)
        self.assertIsNone(one_empty["fraction_b_matched"])


if __name__ == "__main__":
    unittest.main()
