"""Synthetic contract checks for the pinned CodeBrain EEGSSM adapter.

Run with CODEBRAIN_CHECKPOINT and PYTHONPATH pointing to an installed eegt
package. Set CODEBRAIN_UPSTREAM_ZIP for the original-source CPU comparison.
"""

import importlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
if not os.environ.get('CODEBRAIN_CHECKPOINT'):
    raise unittest.SkipTest('optional encoder suite requires CODEBRAIN_CHECKPOINT and encoder environment')
try:
    import torch
except ImportError:
    raise unittest.SkipTest('optional encoder suite requires requirements-encoder.lock') from None
from eegt.pretrained import CodeBrainEncoder
CHECKPOINT = Path(os.environ['CODEBRAIN_CHECKPOINT'])


class EncoderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.encoder = CodeBrainEncoder(CHECKPOINT)

    def test_strict_weights_and_frozen_eval(self):
        model = self.encoder._model
        self.assertEqual(len(model.state_dict()), 269)
        self.assertEqual(sum(p.numel() for p in model.parameters()), 15_167_600)
        self.assertFalse(model.training)
        self.assertTrue(all(not p.requires_grad for p in model.parameters()))
        self.assertEqual(torch.get_num_threads(), 1)
        self.assertEqual(torch.get_num_interop_threads(), 1)

    def test_shapes_finite_signals_and_inference_mode(self):
        t = np.arange(6000, dtype=np.float32) / 200
        sine = np.sin(2 * np.pi * 10 * t).astype(np.float32).reshape(1, 1, 30, 200)
        rng = np.random.default_rng(9)
        zero = np.zeros((1, 4, 30, 200), dtype=np.float32)
        signals = [zero, np.broadcast_to(sine, zero.shape).copy(),
                   rng.standard_normal((1, 4, 30, 200)).astype(np.float32)]
        mode = []
        hook = self.encoder._model.register_forward_pre_hook(
            lambda _model, _args: mode.append(torch.is_inference_mode_enabled()))
        try:
            for x in signals:
                y = self.encoder.encode(x)
                self.assertEqual(y.shape, x.shape)
                self.assertEqual(y.dtype, np.float32)
                self.assertTrue(np.isfinite(y).all())
        finally:
            hook.remove()
        self.assertEqual(mode, [True] * len(signals))

    def test_repeat_batch_and_single_equivalence(self):
        rng = np.random.default_rng(11)
        x = rng.standard_normal((2, 4, 30, 200)).astype(np.float32)
        batched = self.encoder.encode(x)
        repeat = self.encoder.encode(x)
        self.assertEqual(batched.shape, x.shape)
        np.testing.assert_array_equal(batched, repeat)
        for i in range(2):
            single = self.encoder.encode(x[i:i + 1])
            self.assertEqual(single.shape, (1, 4, 30, 200))
            np.testing.assert_allclose(single[0], batched[i], atol=2e-5, rtol=2e-5)

    def test_rejects_malformed_inputs(self):
        good = np.zeros((1, 4, 30, 200), dtype=np.float32)
        bad = [good[0], good.transpose(0, 2, 1, 3),
               good.astype(np.float64), np.zeros((0, 4, 30, 200), dtype=np.float32),
               good.tolist(), np.full_like(good, np.nan),
               np.full_like(good, np.inf)]
        for x in bad:
            with self.subTest(shape=getattr(x, "shape", None), type=type(x).__name__):
                with self.assertRaises((TypeError, ValueError)):
                    self.encoder.encode(x)

    def test_same_size_checkpoint_tamper_refused_before_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            altered = Path(tmp) / "CodeBrain.pth"
            shutil.copyfile(CHECKPOINT, altered)
            with altered.open("r+b") as f:
                f.seek(1_000_000)
                old = f.read(1)
                f.seek(1_000_000)
                f.write(bytes([old[0] ^ 1]))
            with patch("torch.load", side_effect=AssertionError("unsafe load attempted")):
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    CodeBrainEncoder(altered)

    def test_mask_values(self):
        block = self.encoder._model.residual_layer.residual_blocks[0]
        mask = block.generate_local_window_mask(7, 1)
        self.assertEqual(mask.device.type, "cpu")
        self.assertTrue(torch.equal(mask.diagonal(), torch.zeros(7)))
        off_diag = ~torch.eye(7, dtype=torch.bool)
        self.assertTrue(torch.isneginf(mask[off_diag]).all())

    def test_original_cpu_reference_forward(self):
        source_zip = os.environ.get("CODEBRAIN_UPSTREAM_ZIP")
        if not source_zip:
            self.skipTest("set CODEBRAIN_UPSTREAM_ZIP for pinned original-source comparison")
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(source_zip) as archive:
                prefix = "CodeBrain-22d350caf68246d2fda4f630ef837420db3fb130/Models/"
                models = Path(tmp) / "Models"
                models.mkdir()
                for name in ("SSSM.py", "SGConv.py"):
                    (models / name).write_bytes(archive.read(prefix + name))
            sys.path.insert(0, tmp)
            try:
                reference = importlib.import_module("Models.SSSM")
                model = reference.SSSM(
                    in_channels=200, res_channels=200, skip_channels=200,
                    out_channels=200, num_res_layers=8,
                    diffusion_step_embed_dim_in=200,
                    diffusion_step_embed_dim_mid=200,
                    diffusion_step_embed_dim_out=200, s4_lmax=570,
                    s4_d_state=64, s4_dropout=0.1,
                    s4_bidirectional=True, s4_layernorm=True,
                    codebook_size_t=4096, codebook_size_f=4096,
                    if_codebook=False)
                model.load_state_dict(self.encoder._model.state_dict(), strict=True)
                model.eval().requires_grad_(False)
                x = np.random.default_rng(5).standard_normal((1, 4, 30, 200)).astype(np.float32)
                # Only the original mask's CUDA transfer is replaced with a
                # no-op during its CPU reference forward. All math is original.
                with torch.inference_mode(), patch.object(torch.Tensor, "cuda", lambda t, *a, **k: t):
                    original = model(torch.from_numpy(x))
                adapted = self.encoder.encode(x)
                np.testing.assert_allclose(adapted[0], original.numpy(), atol=1e-6, rtol=1e-6)
            finally:
                sys.path.remove(tmp)
                for name in ("Models.SSSM", "Models.SGConv", "Models"):
                    sys.modules.pop(name, None)


if __name__ == "__main__":
    unittest.main()
