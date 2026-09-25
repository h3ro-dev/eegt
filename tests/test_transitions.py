"""Synthetic contract checks for label-blind transition primitives."""

import inspect
import json
import unittest

import numpy as np

from eegt import transitions as tr


def _wave(channels=4, seconds=10, rate=200, change_at=None):
    time = np.arange(int(seconds * rate)) / rate
    data = []
    for channel in range(channels):
        phase = 0.31 * channel
        low = 15 * np.sin(2 * np.pi * 8 * time + phase)
        high = 15 * np.sin(2 * np.pi * 24 * time + phase)
        data.append(low if change_at is None else np.where(time < change_at, low, high))
    return np.asarray(data)


def _matrix(result, view_names=("morphology", "spectrum", "coordination")):
    return np.concatenate([result["views"][name] for name in view_names], axis=1)


class FeatureTests(unittest.TestCase):
    def test_fixed_dimensions_spike_and_gap_exclusion(self):
        rate = 200
        samples = _wave(seconds=9, rate=rate)
        sample_valid = np.ones(samples.shape, dtype=bool)
        sample_valid[:2, int(2.5 * rate):int(3.0 * rate)] = False
        samples[:2, int(5.0 * rate)] = 900
        original = samples.copy()
        result = tr.extract_features(samples, rate, valid_samples=sample_valid)
        self.assertTrue(np.array_equal(samples, original))
        self.assertEqual(set(result), {"times", "valid", "views", "feature_names", "metadata"})
        self.assertEqual(result["times"].dtype, np.dtype("float64"))
        self.assertEqual(result["valid"].dtype, np.dtype("bool"))
        self.assertFalse(np.any(result["valid"][(result["times"] >= 2.0) & (result["times"] <= 3.5)]))
        self.assertFalse(np.any(result["valid"][(result["times"] >= 4.5) & (result["times"] <= 6.0)]))
        for name, values in result["views"].items():
            self.assertTrue(np.isnan(values[~result["valid"]]).all(), name)
            self.assertTrue(np.isfinite(values[result["valid"]]).all(), name)
            self.assertEqual(values.shape[1], len(result["feature_names"][name]))
        more = tr.extract_features(_wave(channels=6, seconds=9, rate=rate), rate)
        self.assertEqual({k: v.shape[1] for k, v in result["views"].items()},
                         {k: v.shape[1] for k, v in more["views"].items()})

    def test_native_line_check_and_unavailable_check(self):
        rate = 200
        t = np.arange(1000) / rate
        line = np.tile(20 * np.sin(2 * np.pi * 50 * t), (4, 1))
        checked = tr.extract_features(line, rate)
        self.assertTrue(checked["metadata"]["line_check_available"])
        self.assertFalse(checked["valid"].any())
        low_nyquist = tr.extract_features(_wave(seconds=5, rate=120), 120)
        self.assertFalse(low_nyquist["metadata"]["line_check_available"])

    def test_flat_and_nonfinite_channels_are_excluded(self):
        samples = _wave(seconds=5)
        samples[0] = 3.0
        samples[1, 350] = np.nan
        result = tr.extract_features(samples, 200)
        touching_nan = (result["times"] >= 1.0) & (result["times"] <= 2.5)
        self.assertFalse(result["valid"][touching_nan].any())
        self.assertTrue(result["valid"][~touching_nan].any())
        self.assertTrue(np.isnan(_matrix(result)[~result["valid"]]).all())

    def test_haloed_chunk_agrees_on_interior_windows(self):
        samples = _wave(seconds=28)
        whole = tr.extract_features(samples, 200)
        chunk = tr.extract_features(samples[:, 800:4800], 200)
        for index, local_time in enumerate(chunk["times"]):
            global_time = local_time + 4.0
            whole_index = np.flatnonzero(np.isclose(whole["times"], global_time))
            self.assertEqual(len(whole_index), 1)
            self.assertEqual(bool(chunk["valid"][index]), bool(whole["valid"][whole_index[0]]))
            np.testing.assert_allclose(_matrix(chunk)[index], _matrix(whole)[whole_index[0]],
                                       rtol=0, atol=1e-10)

    def test_piecewise_frequency_shift_has_nearby_score(self):
        result = tr.extract_features(_wave(seconds=20, change_at=10), 200)
        self.assertTrue(result["valid"].all())
        spectrum = result["views"]["spectrum"]
        reference = tr.fit_reference(spectrum)
        scores = tr.boundary_scores(spectrum, result["times"], result["valid"],
                                    reference, scales_seconds=(2.0,))["2.0"]
        best = int(np.nanargmax(scores))
        self.assertLess(abs(result["times"][best] - 10), 1.5)
        self.assertGreater(scores[best], np.nanmedian(scores))

    def test_public_api_is_label_blind_and_input_is_unmodified(self):
        expected = {
            "extract_features": ["samples_uv", "sample_rate_hz", "valid_samples", "window_seconds", "hop_seconds"],
            "fit_reference": ["feature_arrays"],
            "boundary_scores": ["features", "times", "valid", "reference", "scales_seconds"],
            "select_boundaries": ["scores", "times", "threshold", "min_separation_seconds"],
            "transition_geometry": ["features", "times", "valid", "reference", "indices", "context_seconds"],
            "match_boundaries": ["times_a", "times_b", "tolerance_seconds"],
            "phase_surrogate": ["samples_uv", "seed", "shared_phase"],
        }
        positional_count = {"extract_features": 2, "fit_reference": 1,
                            "boundary_scores": 4, "select_boundaries": 2,
                            "transition_geometry": 5, "match_boundaries": 2,
                            "phase_surrogate": 1}
        for name, names in expected.items():
            signature = inspect.signature(getattr(tr, name))
            self.assertEqual(list(signature.parameters), names)
            for parameter in list(signature.parameters.values())[positional_count[name]:]:
                self.assertEqual(parameter.kind, inspect.Parameter.KEYWORD_ONLY)
        samples = _wave(seconds=4)
        original = samples.copy()
        tr.extract_features(samples, 200)
        tr.phase_surrogate(samples)
        np.testing.assert_array_equal(samples, original)


class ReferenceAndBoundaryTests(unittest.TestCase):
    def test_reference_is_frozen_and_training_only(self):
        train = np.array([[1., 10.], [2., 20.], [3., 30.], [4., 40.]])
        reference = tr.fit_reference([train[:2], train[2:]])
        center = reference["center"].copy()
        scale = reference["scale"].copy()
        train[:] = 1000
        np.testing.assert_array_equal(reference["center"], center)
        np.testing.assert_array_equal(reference["scale"], scale)
        self.assertTrue((scale > 0).all())
        with self.assertRaises(ValueError):
            tr.fit_reference(np.array([[np.nan, 1.]]))

    def test_scores_do_not_cross_invalid_rows(self):
        features = np.tile(np.arange(18, dtype=float)[:, None], (1, 2))
        times = np.arange(18) * 0.5
        valid = np.ones(18, dtype=bool)
        valid[8] = False
        features[8] = np.nan
        ref = tr.fit_reference(features[valid])
        score = tr.boundary_scores(features, times, valid, ref,
                                   scales_seconds=(1.0,))["1.0"]
        self.assertTrue(np.isnan(score[7:11]).all())
        self.assertTrue(np.isfinite(score[2:7]).all())
        self.assertTrue(np.isfinite(score[11:17]).all())

    def test_unrepresentable_score_is_missing(self):
        features = np.array([[-1e308], [1e308], [-1e308], [1e308]])
        ref = {"center": np.zeros(1), "scale": np.ones(1)}
        scores = tr.boundary_scores(features, np.arange(4, dtype=float),
                                    np.ones(4, bool), ref,
                                    scales_seconds=(1.0,))["1.0"]
        self.assertTrue(np.isnan(scores).all())

    def test_invalid_time_grids_raise_and_explicit_gap_is_allowed(self):
        features = np.arange(12, dtype=float)[:, None]
        times = np.arange(12, dtype=float) * 0.5
        valid = np.ones(12, dtype=bool)
        ref = tr.fit_reference(features)
        for broken in (times[::-1], np.array([0, 0] + list(times[2:])),
                       np.array(list(times[:6]) + list(times[6:] + 1))):
            with self.assertRaises(ValueError):
                tr.boundary_scores(features, broken, valid, ref)
        gapped = times.copy()
        gapped[6:] += 1
        valid[5:7] = False
        scores = tr.boundary_scores(features, gapped, valid, ref,
                                    scales_seconds=(0.5,))["0.5"]
        self.assertTrue(np.isnan(scores[5:8]).all())
        with self.assertRaises(ValueError):
            tr.select_boundaries(np.ones(12), times[::-1], threshold=0.5)
        with self.assertRaises(ValueError):
            tr.transition_geometry(features, times[::-1], np.ones(12, bool), ref, [4])

    def test_peak_selection_respects_nan_plateau_and_separation(self):
        scores = np.array([np.nan, 1., 3., 3., 1., np.nan, 4., 1., 3., 1.])
        chosen = tr.select_boundaries(scores, np.arange(len(scores), dtype=float),
                                      threshold=2., min_separation_seconds=3.)
        np.testing.assert_array_equal(chosen, np.array([2, 6]))
        self.assertEqual(chosen.dtype, np.dtype("int64"))

    def test_geometry_has_finite_json_rows_and_null_without_context(self):
        features = np.array([[0., 0.], [1., 0.], [2., 0.], [2., 1.],
                             [2., 2.], [1., 2.], [0., 2.]])
        times = np.arange(len(features), dtype=float)
        valid = np.ones(len(features), bool)
        ref = {"center": np.zeros(2), "scale": np.ones(2)}
        self.assertEqual(tr.transition_geometry(features, times, valid, ref, []), [])
        rows = tr.transition_geometry(features, times, valid, ref, [3, 0], context_seconds=2)
        self.assertEqual(rows[0]["index"], 3)
        self.assertGreater(rows[0]["pre_post_distance"], 0)
        self.assertGreater(rows[0]["path_length"], 0)
        self.assertTrue(0 <= rows[0]["turning_angle_radians"] <= np.pi)
        self.assertIsNone(rows[1]["pre_post_distance"])
        self.assertIsNone(rows[1]["return_distance"])
        json.dumps(rows, allow_nan=False)
        valid[2] = False
        self.assertIsNone(tr.transition_geometry(features, times, valid, ref, [3],
                                                  context_seconds=2)[0]["path_length"])

    def test_geometry_nulls_unrepresentable_finite_input_metrics(self):
        huge = np.array([[-1e200, 0.], [-1e200, 0.], [1e200, 0.],
                         [1e200, 1e200], [1e200, 1e200]])
        row = tr.transition_geometry(huge, np.arange(5, dtype=float),
                                     np.ones(5, bool),
                                     {"center": np.zeros(2), "scale": np.ones(2)},
                                     [2], context_seconds=2)[0]
        json.dumps(row, allow_nan=False)
        self.assertTrue(np.isfinite(row["path_length"]))
        enormous = huge.copy()
        enormous[0, 0] = -1e308
        enormous[1, 0] = -1e308
        enormous[2, 0] = 1e308
        row = tr.transition_geometry(enormous, np.arange(5, dtype=float),
                                     np.ones(5, bool),
                                     {"center": np.zeros(2), "scale": np.ones(2)},
                                     [2], context_seconds=2)[0]
        json.dumps(row, allow_nan=False)
        self.assertIsNone(row["path_length"])


class MatchingAndSurrogateTests(unittest.TestCase):
    def test_empty_and_duplicate_match_semantics(self):
        both_empty = tr.match_boundaries([], [])
        self.assertEqual((both_empty["precision"], both_empty["recall"], both_empty["f1"]),
                         (1., 1., 1.))
        self.assertIsNone(both_empty["median_abs_error_seconds"])
        one_empty = tr.match_boundaries([1.], [])
        self.assertEqual(one_empty["f1"], 0.)
        duplicate = tr.match_boundaries([1., 1.], [1.], tolerance_seconds=0.1)
        self.assertEqual(duplicate["matched"], 1)
        self.assertEqual(duplicate["precision"], 1.)
        self.assertEqual(duplicate["recall"], 0.5)
        nearest = tr.match_boundaries([0., 1.], [0.9], tolerance_seconds=1.)
        self.assertAlmostEqual(nearest["median_abs_error_seconds"], 0.1)

    def test_phase_surrogates_preserve_fft_amplitude_even_and_odd(self):
        rng = np.random.default_rng(8)
        for length in (128, 129):
            data = rng.normal(size=(3, length)) + 2.0
            original = data.copy()
            for shared in (False, True):
                surrogate = tr.phase_surrogate(data, seed=42, shared_phase=shared)
                np.testing.assert_allclose(np.abs(np.fft.rfft(surrogate, axis=1)),
                                           np.abs(np.fft.rfft(data, axis=1)), rtol=1e-12, atol=1e-10)
                np.testing.assert_allclose(np.fft.rfft(surrogate, axis=1)[:, 0],
                                           np.fft.rfft(data, axis=1)[:, 0], atol=1e-10)
                if length % 2 == 0:
                    np.testing.assert_allclose(np.fft.rfft(surrogate, axis=1)[:, -1],
                                               np.fft.rfft(data, axis=1)[:, -1], atol=1e-10)
                np.testing.assert_array_equal(surrogate, tr.phase_surrogate(data, seed=42,
                                                                              shared_phase=shared))
            np.testing.assert_array_equal(data, original)

    def test_shared_phase_preserves_cross_spectra(self):
        rng = np.random.default_rng(14)
        data = rng.normal(size=(2, 129))
        original = np.fft.rfft(data, axis=1)
        shared = np.fft.rfft(tr.phase_surrogate(data, shared_phase=True), axis=1)
        independent = np.fft.rfft(tr.phase_surrogate(data, shared_phase=False), axis=1)
        np.testing.assert_allclose(shared[0] * np.conj(shared[1]),
                                   original[0] * np.conj(original[1]), atol=1e-10)
        self.assertGreater(np.max(np.abs(independent[0] * np.conj(independent[1]) -
                                           original[0] * np.conj(original[1]))), 1.)
        with self.assertRaises(ValueError):
            tr.phase_surrogate(np.array([[1., np.nan]]))


if __name__ == "__main__":
    unittest.main()
