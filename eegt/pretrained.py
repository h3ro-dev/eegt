"""CPU inference adapter for the pinned CodeBrain EEGSSM stage-2 backbone.

Inputs are already filtered, resampled, segmented and scaled by the caller.
This module does no EEG preprocessing or scientific interpretation.
"""

import hashlib
import os
from pathlib import Path

# Set these before NumPy/Torch import when this module is the first importer.
# A launcher must set them before process start if other modules import BLAS first.
for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import numpy as np
import torch

from .vendor.codebrain.SSSM import SSSM


_CHECKPOINT_BYTES = 60_901_006
_CHECKPOINT_SHA256 = "d9714b8732c9883a04d022ee66254cd578ae1fa27f5458e6ab7f1aa96e9a7352"
_PATCH_SHAPE = (4, 30, 200)


class CodeBrainEncoder:
    """Official pretrained EEGSSM patch embeddings on a single CPU thread."""

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
                raise ValueError("CodeBrain checkpoint size mismatch")
            sha = hashlib.sha256()
            for chunk in iter(lambda: f.read(1 << 20), b""):
                sha.update(chunk)
            if sha.hexdigest() != _CHECKPOINT_SHA256:
                raise ValueError("CodeBrain checkpoint SHA-256 mismatch")
            f.seek(0)
            state = torch.load(f, weights_only=True, map_location="cpu")

        if not isinstance(state, dict) or not state:
            raise ValueError("CodeBrain checkpoint is not a state dictionary")
        if not all(isinstance(k, str) and k.startswith("module.")
                   and isinstance(v, torch.Tensor) for k, v in state.items()):
            raise ValueError("Unexpected CodeBrain checkpoint wrapper or tensor keys")
        # Official pretraining saved DataParallel's single `module.` prefix.
        weights = {k[len("module."):]: v for k, v in state.items()}
        if len(weights) != len(state):
            raise ValueError("Duplicate keys after CodeBrain module prefix removal")

        self._model = SSSM(
            in_channels=200, res_channels=200, skip_channels=200,
            out_channels=200, num_res_layers=8,
            diffusion_step_embed_dim_in=200,
            diffusion_step_embed_dim_mid=200,
            diffusion_step_embed_dim_out=200,
            s4_lmax=570, s4_d_state=64, s4_dropout=0.1,
            s4_bidirectional=True, s4_layernorm=True,
            codebook_size_t=4096, codebook_size_f=4096,
            if_codebook=False,
        )
        self._model.load_state_dict(weights, strict=True)
        self._model.eval().requires_grad_(False)

    def encode(self, patches):
        """Return float32 [B,4,30,200] embeddings for finite float32 patches."""
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
            output = self._model(tensor)
        # Upstream's feature branch calls squeeze(), removing only B when B=1
        # under this fixed interface. Restore B without pooling any features.
        if patches.shape[0] == 1 and output.shape == _PATCH_SHAPE:
            output = output.unsqueeze(0)
        if output.shape != patches.shape or output.dtype != torch.float32:
            raise RuntimeError(f"Unexpected CodeBrain output: {tuple(output.shape)}, {output.dtype}")
        result = output.cpu().numpy().copy()
        if not np.isfinite(result).all():
            raise RuntimeError("CodeBrain produced nonfinite embeddings")
        return result
