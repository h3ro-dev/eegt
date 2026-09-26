"""Bounded CBraMod CPU compatibility smoke against captured official source.

Run with the captured compatibility packet and isolated encoder environment:
  python scripts/smoke_cbramod.py --packet-root /path/to/packet --output-dir /path/to/new-output
This script reads only the pinned source snapshot, checkpoint, and two exposed
development patches. It writes numerical receipts to out/.
"""

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import numpy as np
import torch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--packet-root", required=True, type=Path)
parser.add_argument("--output-dir", required=True, type=Path)
args = parser.parse_args()
ROOT = args.packet_root.resolve()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eegt.cbramod import CBraModEncoder

CHECKPOINT = ROOT / "scratch/pretrained_weights.pth"
DEVELOPMENT = ROOT / "input/development-patches.npy"
OUT = args.output_dir.resolve()
if OUT.exists():
    raise FileExistsError("Preserve existing smoke evidence; choose a new output directory")
SOURCE = ROOT / "input/audit/scratch/sources"
EXPECTED_WEIGHT_SHA = "0792cb808c14e6b7a2bb2ce1dff379bc47bc54c49a779825bdfeb33bf8157178"
TOLERANCE = {"atol": 1e-6, "rtol": 1e-5}


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def file_record(path):
    data = path.read_bytes()
    return {"path": os.path.relpath(path, ROOT), "bytes": len(data), "sha256": sha_bytes(data)}


def verify_inputs():
    audit = json.loads((ROOT / "input/audit/out/SOURCE_HASHES.json").read_text())
    for item in audit["source_records"]:
        path = ROOT / "input/audit" / item["path"]
        actual = file_record(path)
        if actual["bytes"] != item["bytes"] or actual["sha256"] != item["sha256"]:
            raise ValueError(f"Captured audit source mismatch: {item['key']}")
    snapshot = json.loads((ROOT / "input/source-snapshot.json").read_text())
    for name, expected in snapshot["files"].items():
        if file_record(ROOT / "repo" / name)["sha256"] != expected:
            raise ValueError(f"Pinned packet source mismatch: {name}")
    receipt = json.loads((ROOT / "input/development-receipt.json").read_text())
    development = file_record(DEVELOPMENT)
    if development["sha256"] != receipt["array_sha256"]:
        raise ValueError("Development patch receipt SHA-256 mismatch")
    weight = file_record(CHECKPOINT)
    if weight["bytes"] != 19_775_842 or weight["sha256"] != EXPECTED_WEIGHT_SHA:
        raise ValueError("Pinned CBraMod checkpoint size or SHA-256 mismatch")
    return {"captured_source_count": len(audit["source_records"]),
            "source_snapshot_count": len(snapshot["files"]),
            "source_manifest": file_record(ROOT / "input/audit/out/SOURCE_HASHES.json"),
            "source_snapshot": file_record(ROOT / "input/source-snapshot.json"),
            "development_receipt": file_record(ROOT / "input/development-receipt.json"),
            "development": development, "checkpoint": weight}


@contextmanager
def official_model():
    """Import unedited pinned author files through their original import path."""
    if "models" in sys.modules:
        raise RuntimeError("Original-source module name is already occupied")
    with tempfile.TemporaryDirectory(dir=ROOT / "scratch") as tmp:
        models = Path(tmp) / "models"
        models.mkdir()
        (models / "cbramod.py").write_bytes((SOURCE / "cb_model.txt").read_bytes())
        (models / "criss_cross_transformer.py").write_bytes(
            (SOURCE / "cb_transformer.txt").read_bytes())
        sys.path.insert(0, tmp)
        try:
            original = importlib.import_module("models.cbramod")
            model = original.CBraMod().cpu()
            state = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
            model.load_state_dict(state, strict=True)
            model.eval().requires_grad_(False)
            yield model, len(state)
        finally:
            sys.path.remove(tmp)
            sys.modules.pop("models.cbramod", None)
            sys.modules.pop("models.criss_cross_transformer", None)
            sys.modules.pop("models", None)


def save_array(name, array):
    path = OUT / f"{name}.npy"
    np.save(path, array, allow_pickle=False)
    return {**file_record(path), "array_sha256": sha_bytes(array.tobytes(order="C")),
            "shape": list(array.shape), "dtype": str(array.dtype)}


def run():
    OUT.mkdir(exist_ok=True)
    verified = verify_inputs()
    patches = np.load(DEVELOPMENT, allow_pickle=False)
    if patches.shape != (2, 4, 30, 200) or patches.dtype != np.float32 or not np.isfinite(patches).all():
        raise ValueError("Development patch array shape, dtype, or finiteness mismatch")

    rng = np.random.default_rng(30)
    synthetic = (rng.standard_normal((1, 4, 30, 200)).astype(np.float32) * 0.05)
    synthetic_record = save_array("synthetic_input", synthetic)
    encoder = CBraModEncoder(CHECKPOINT)
    forwards = 0
    cases = []
    with official_model() as (reference, state_keys):
        for name, x in (("synthetic", synthetic),
                        ("development_0", patches[0:1]),
                        ("development_1", patches[1:2])):
            before = x.copy()
            started = time.perf_counter()
            actual = encoder.encode(x)
            adapter_seconds = time.perf_counter() - started
            forwards += 1
            with torch.inference_mode():
                started = time.perf_counter()
                tensor = torch.from_numpy(np.array(x, copy=True, order="C"))
                expected = reference.encoder(reference.patch_embedding(tensor)).cpu().numpy().copy()
                reference_seconds = time.perf_counter() - started
            forwards += 1
            if forwards > 20:
                raise RuntimeError("20-forward compatibility cap exceeded")
            if not np.array_equal(x, before):
                raise AssertionError(f"{name} input mutated")
            if actual.shape != x.shape or expected.shape != x.shape or actual.dtype != np.float32:
                raise AssertionError(f"{name} latent shape/dtype mismatch")
            if not actual.flags.owndata or np.shares_memory(actual, x):
                raise AssertionError(f"{name} output ownership mismatch")
            if not np.isfinite(actual).all() or not np.isfinite(expected).all():
                raise AssertionError(f"{name} nonfinite latent")
            difference = np.abs(actual - expected)
            close = bool(np.allclose(actual, expected, **TOLERANCE))
            case = {"name": name, "input_array_sha256": sha_bytes(x.tobytes(order="C")),
                    "adapter": save_array(f"latent_{name}", actual),
                    "official": save_array(f"official_{name}", expected),
                    "adapter_seconds": adapter_seconds,
                    "official_seconds": reference_seconds,
                    "max_absolute_error": float(difference.max()),
                    "max_relative_error_floor_1e_minus_6":
                        float((difference / np.maximum(np.abs(expected), 1e-6)).max()),
                    "allclose": close, "exact_equal": bool(np.array_equal(actual, expected))}
            cases.append(case)
            if not close:
                raise AssertionError(f"{name} official-source latent mismatch")

        started = time.perf_counter()
        repeated = encoder.encode(synthetic)
        repeat_seconds = time.perf_counter() - started
        forwards += 1
        if forwards > 20 or not np.array_equal(
                repeated, np.load(OUT / "latent_synthetic.npy", allow_pickle=False)):
            raise AssertionError("Repeated synthetic inference mismatch or forward cap exceeded")

    lock = (ROOT / "repo/requirements-encoder.lock").read_text().splitlines()
    packages = {line.split("==")[0]: importlib.metadata.version(line.split("==")[0])
                for line in lock if "==" in line}
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report = {"schema": "eegt-cbramod-smoke/v1", "status": "PASS",
              "observed_at": datetime.now(timezone.utc).isoformat(),
              "author_commit": "b9e961003214326972c567eff390e75b0287e32a",
              "weight_revision": "500543c7e30bda1b22bfd51a49301b238dee21fd",
              "verified_inputs": verified, "synthetic_input": synthetic_record,
              "state_keys": state_keys, "forward_count": forwards, "forward_cap": 20,
              "tolerance": TOLERANCE, "cases": cases,
              "repeatability": {"exact_equal": True, "seconds": repeat_seconds,
                                "array_sha256": sha_bytes(repeated.tobytes(order="C"))},
              "environment": {"python": sys.version, "executable": sys.executable,
                              "platform": platform.platform(), "machine": platform.machine(),
                              "packages": packages,
                              "threads": {"torch_intraop": torch.get_num_threads(),
                                          "torch_interop": torch.get_num_interop_threads(),
                                          "python_active": threading.active_count(),
                                          "blas_environment": {name: os.environ[name] for name in
                                             ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                                              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")}},
                              "peak_rss": rss,
                              "peak_rss_unit": "bytes (Darwin ru_maxrss)" if sys.platform == "darwin"
                                               else "KiB (Linux ru_maxrss)"}}
    (OUT / "SMOKE.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "forwards": forwards,
                      "state_keys": state_keys, "max_abs": max(c["max_absolute_error"] for c in cases),
                      "max_rel": max(c["max_relative_error_floor_1e_minus_6"] for c in cases),
                      "peak_rss": rss, "rss_unit": report["environment"]["peak_rss_unit"]}))


if __name__ == "__main__":
    run()
