import unittest
import numpy as np
from eegt.contract import NumericRecording, mw75_decoded


class ContractTests(unittest.TestCase):
    def test_no_context_fields(self):
        payload = dict(samples_uv=np.ones((2, 500)), sample_rate_hz=250,
                       valid_samples=np.ones((2, 500), bool))
        for field in ["subject", "source", "sleep_stage", "date", "diagnosis", "history", "meaning", "channel_names"]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                NumericRecording.from_payload(payload | {field: "sentinel"})
        accepted = NumericRecording.from_payload(payload)
        self.assertEqual(set(accepted.__dict__), set(payload))

    def test_copies_cannot_drift(self):
        x = np.ones((1, 500))
        r = NumericRecording(x, 250, np.ones(x.shape, bool))
        x[:] = 8
        self.assertTrue(np.all(r.samples_uv == 1))
        with self.assertRaises(ValueError):
            r.samples_uv[:] = 4

    def test_shape_integrity_and_nonfinite(self):
        with self.assertRaises(ValueError):
            NumericRecording(np.array([[np.nan]]), 250, np.ones((1, 1), bool))
        with self.assertRaises(ValueError):
            NumericRecording(np.ones((1, 500)), 250, np.ones((1, 499), bool))
        with self.assertRaises(ValueError):
            NumericRecording(np.ones((1, 500)), 80, np.ones((1, 500), bool))

    def test_mw75_requires_verified_shape_order_units_and_integrity(self):
        x = np.ones((12, 1000))
        order = tuple(f"contact-{n}" for n in range(12))
        kw = dict(sample_rate_hz=500, channel_order=order, expected_channel_order=order,
                  units="uV", sample_integrity=np.ones(1000, bool))
        r = mw75_decoded(x, **kw)
        self.assertEqual(r.samples_uv.shape, (12, 1000))
        for update in [dict(units="V"), dict(sample_rate_hz=250), dict(channel_order=order[::-1]),
                       dict(sample_integrity=np.ones(999, bool))]:
            with self.subTest(update=list(update)), self.assertRaises(ValueError):
                mw75_decoded(x, **(kw | update))
        with self.assertRaises(ValueError):
            mw75_decoded(x[:11], **kw)
        mask = np.ones(1000, bool); mask[10] = False
        r = mw75_decoded(x, **(kw | dict(sample_integrity=mask)))
        self.assertFalse(r.valid_samples[:, 10].any())


if __name__ == "__main__":
    unittest.main()
