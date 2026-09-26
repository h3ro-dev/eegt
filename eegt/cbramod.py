"""CPU adapter for the pinned, pretrained CBraMod backbone.

The caller supplies finite, preprocessed float32 patches in microvolts/100.
This module does no filtering, scaling, channel mapping, or pooling.
"""

import hashlib
import io
import os
from pathlib import Path

# A launcher must set these before process start if it imports BLAS first.
for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import numpy as np
import torch

from .vendor.cbramod.cbramod import CBraMod


_CHECKPOINT_BYTES = 19_775_842
_CHECKPOINT_SHA256 = "0792cb808c14e6b7a2bb2ce1dff379bc47bc54c49a779825bdfeb33bf8157178"
_PATCH_SHAPE = (4, 30, 200)


class CBraModEncoder:
    """Return the full contextual [B, 4, 30, 200] latent grid on CPU."""

    def __init__(self, checkpoint_path):
        torch.set_num_threads(1)
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            if torch.get_num_interop_threads() != 1:
                raise RuntimeError("Torch interop threads were initialized above 1") from None

        checkpoint = Path(checkpoint_path)
        with checkpoint.open("rb") as f:
            if os.fstat(f.fileno()).st_size != _CHECKPOINT_BYTES:
                raise ValueError("CBraMod checkpoint size mismatch")
            data = f.read()
        if len(data) != _CHECKPOINT_BYTES:
            raise ValueError("CBraMod checkpoint size mismatch")
        if hashlib.sha256(data).hexdigest() != _CHECKPOINT_SHA256:
            raise ValueError("CBraMod checkpoint SHA-256 mismatch")
        state = torch.load(io.BytesIO(data), map_location="cpu", weights_only=True)

        if not isinstance(state, dict) or not state:
            raise ValueError("CBraMod checkpoint is not a state dictionary")
        if not all(isinstance(k, str) and isinstance(v, torch.Tensor)
                   for k, v in state.items()):
            raise ValueError("Unexpected CBraMod state dictionary contents")

        model = CBraMod().cpu()
        model.load_state_dict(state, strict=True)
        self._model = model.eval().requires_grad_(False)

    def encode(self, patches):
        """Encode finite float32 NumPy [B,4,30,200] patches without mutation."""
        if not isinstance(patches, np.ndarray):
            raise TypeError("patches must be a NumPy ndarray")
        if patches.dtype != np.float32:
            raise TypeError("patches must have dtype float32")
        if patches.ndim != 4 or patches.shape[0] < 1 or patches.shape[1:] != _PATCH_SHAPE:
            raise ValueError("patches must have shape [B,4,30,200], B >= 1")
        if not np.isfinite(patches).all():
            raise ValueError("patches must contain only finite values")

        tensor = torch.from_numpy(np.array(patches, copy=True, order="C"))
        with torch.inference_mode():
            output = self._model.encoder(self._model.patch_embedding(tensor))
        if output.shape != patches.shape or output.dtype != torch.float32:
            raise RuntimeError(f"Unexpected CBraMod output: {tuple(output.shape)}, {output.dtype}")
        result = output.cpu().numpy().copy()
        if not np.isfinite(result).all():
            raise RuntimeError("CBraMod produced nonfinite embeddings")
        return result
