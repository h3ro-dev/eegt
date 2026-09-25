import json
from pathlib import Path
import unittest
import numpy as np
from sklearn.metrics import adjusted_rand_score
from eegt.contract import NumericRecording
from eegt.signal import window_quality, iter_windows, features, surrogate
from eegt.model import Tokenizer

PROTOCOL = json.loads((Path(__file__).resolve().parents[1] / "protocol/experiment-002.json").read_text())


class SignalTests(unittest.TestCase):
    def test_qc_and_complete_denominator(self):
        rate = 250
        good = 10 * np.sin(2 * np.pi * 10 * np.arange(500) / rate)
        channels = np.stack([np.r_[good, good[:100]], np.zeros(600)])
        windows = list(iter_windows(NumericRecording(channels, rate, np.ones(channels.shape, bool)), PROTOCOL))
        self.assertEqual(len(windows), 4)
        self.assertEqual(sum(w[-1] is not None for w in windows), 1)
        self.assertEqual(sum("INCOMPLETE" in w[2] for w in windows), 2)
        self.assertIn("FLAT", windows[2][2])
        line = 10 * np.sin(2 * np.pi * 50 * np.arange(500) / rate)
        self.assertIn("LINE_DOMINATED", window_quality(line, np.ones(500, bool), rate, PROTOCOL["qc"])[0])
        self.assertIn("HIGH_AMPLITUDE", window_quality(good * 100, np.ones(500, bool), rate, PROTOCOL["qc"])[0])

    def test_resampling_same_acquired_sinusoid(self):
        transformed = []
        for rate in (250, 500):
            x = 10 * np.sin(2 * np.pi * 10 * np.arange(2 * rate) / rate)
            r = NumericRecording(x[None, :], rate, np.ones((1, 2 * rate), bool))
            transformed.append(list(iter_windows(r, PROTOCOL))[0][-1])
        self.assertGreater(np.corrcoef(transformed[0][20:-20], transformed[1][20:-20])[0, 1], .999)

    def test_surrogates_preserve_specified_properties(self):
        w = np.random.default_rng(33).normal(size=(10, 200))
        s = surrogate(w, "sample_shuffle")
        np.testing.assert_allclose(np.sort(w, axis=1), np.sort(s, axis=1))
        p = surrogate(w, "phase_randomized")
        np.testing.assert_allclose(np.abs(np.fft.rfft(w)), np.abs(np.fft.rfft(p)), atol=1e-10)
        for method, width in [("spectrum", 40), ("waveform", 200), ("time_frequency", 80)]:
            self.assertEqual(features(w, method).shape, (10, width))

    def test_predict_does_not_refit_or_accept_metadata(self):
        w = np.random.default_rng(22).normal(size=(80, 200))
        m = Tokenizer("spectrum", 8, 17).fit(w[:60])
        before = {k: v.copy() for k, v in m.export_arrays().items()}
        m.predict(w[60:] * 1000)
        for k, v in before.items():
            np.testing.assert_array_equal(v, m.export_arrays()[k])
        with self.assertRaises(TypeError):
            m.fit(w, subject="sentinel")
        self.assertEqual(adjusted_rand_score([0, 0, 1, 1], [7, 7, 2, 2]), 1)


if __name__ == "__main__":
    unittest.main()
