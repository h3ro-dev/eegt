"""Synthetic contract and rejection checks for the optional CBraMod adapter.

Run with CBRAMOD_CHECKPOINT set to the pinned file. The separate smoke script
provides the required real official-source forward and development receipts.
"""

import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import numpy as np

if not os.environ.get("CBRAMOD_CHECKPOINT") or not Path(os.environ["CBRAMOD_CHECKPOINT"]).is_file():
    raise unittest.SkipTest("optional CBraMod tests require an available CBRAMOD_CHECKPOINT")

import torch

import eegt.cbramod as adapter


CHECKPOINT = Path(os.environ["CBRAMOD_CHECKPOINT"])


class CBraModTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.encoder = adapter.CBraModEncoder(CHECKPOINT)

    def test_strict_full_load_and_frozen_cpu(self):
        model = self.encoder._model
        self.assertGreater(len(model.state_dict()), 100)
        self.assertIsInstance(model.proj_out, torch.nn.Sequential)
        self.assertEqual(next(model.parameters()).device.type, "cpu")
        self.assertFalse(model.training)
        self.assertTrue(all(not p.requires_grad for p in model.parameters()))
        self.assertEqual(torch.get_num_threads(), 1)
        self.assertEqual(torch.get_num_interop_threads(), 1)

    def test_input_contract_and_output_ownership(self):
        good = np.zeros((1, 4, 30, 200), dtype=np.float32)
        original = good.copy()
        output = self.encoder.encode(good)
        np.testing.assert_array_equal(good, original)
        self.assertEqual(output.shape, good.shape)
        self.assertEqual(output.dtype, np.float32)
        self.assertTrue(np.isfinite(output).all())
        self.assertTrue(output.flags.owndata)
        self.assertFalse(np.shares_memory(output, good))

        bad = [(good[0], "shape"), (good.transpose(0, 2, 1, 3), "shape"),
               (np.zeros((0, 4, 30, 200), np.float32), "shape"),
               (good.astype(np.float64), "dtype"), (good.tolist(), "NumPy"),
               (np.full_like(good, np.nan), "finite"),
               (np.full_like(good, np.inf), "finite")]
        for value, message in bad:
            with self.subTest(shape=getattr(value, "shape", None), type=type(value).__name__):
                with self.assertRaisesRegex((TypeError, ValueError), message):
                    self.encoder.encode(value)

    def test_bad_size_and_same_size_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.pth"
            path.write_bytes(b"wrong size")
            with self.assertRaisesRegex(ValueError, "size mismatch"):
                adapter.CBraModEncoder(path)

            path.write_bytes(CHECKPOINT.read_bytes())
            with path.open("r+b") as f:
                f.seek(1_000_000)
                byte = f.read(1)
                f.seek(1_000_000)
                f.write(bytes([byte[0] ^ 1]))
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                adapter.CBraModEncoder(path)

    def test_strict_key_and_shape_mismatches_rejected(self):
        state = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
        for kind in ("missing key", "wrong shape"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                altered = state.copy()
                if kind == "missing key":
                    altered.pop(next(iter(altered)))
                    expected = "Missing key"
                else:
                    key = next(k for k, v in altered.items() if v.ndim and v.shape[0] > 1)
                    altered[key] = altered[key][:-1].clone()
                    expected = "size mismatch"
                path = Path(tmp) / "altered.pth"
                torch.save(altered, path)
                data = path.read_bytes()
                # Fixture-specific pins reach the real strict-load branch.
                with patch.object(adapter, "_CHECKPOINT_BYTES", len(data)), \
                     patch.object(adapter, "_CHECKPOINT_SHA256", hashlib.sha256(data).hexdigest()):
                    with self.assertRaisesRegex(RuntimeError, expected):
                        adapter.CBraModEncoder(path)


if __name__ == "__main__":
    unittest.main()
