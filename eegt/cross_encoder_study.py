"""Frozen Experiment 011: paired geometry of two pretrained EEG encoders.

Inference sees numerical patches only. Source identities enter validation and
evaluation after both models' latents have been archived. No fitting occurs.
"""

from collections import defaultdict
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import platform
import resource
import sqlite3
import sys
import time
import traceback

for _thread_var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread_var] = "1"

import numpy as np

from .acquire import digest
from .corpus import atomic_json, canonical_json
from . import distributed_study, pretrained_study as previous


PROTOCOL_SHA256 = "792b56402d7d95eef8a7ed4b727d73b22819a521b6b99af34a37cacf2877ca2e"
VARIANTS = previous.VARIANTS
VIEWS = previous.VIEWS
METRICS = ("geometry", "change")
SOURCE_PATHS = (
    "eegt/cross_encoder_study.py", "scripts/reproduce_cross_encoder.py",
    "tests/test_cross_encoder_study.py", "eegt/cbramod.py",
    "eegt/pretrained_study.py", "eegt/distributed_study.py",
    "eegt/acquire.py", "eegt/corpus.py", "eegt/pretrained.py",
    "eegt/vendor/cbramod/cbramod.py",
    "eegt/vendor/cbramod/criss_cross_transformer.py",
    "eegt/vendor/codebrain/SGConv.py", "eegt/vendor/codebrain/SSSM.py",
    "requirements.lock", "requirements-encoder.lock", "pyproject.toml",
)


def read(path):
    return json.loads(Path(path).read_text())


def require_hash(path, expected, label=None):
    actual = digest(Path(path))
    if actual != expected:
        raise ValueError(f"{label or path} SHA-256 mismatch")
    return actual


def selected_identity(rows, indices, expected_count=122):
    """Refuse duplicate, reordered, or mismatched selected candidate rows."""
    selected = [row for row in rows if row["status"] == "ELIGIBLE"]
    ids = [row["candidate_index"] for row in selected]
    if len(selected) != expected_count or len(set(ids)) != len(ids):
        raise ValueError("selected row count or duplicate identity")
    if ids != sorted(ids) or not np.array_equal(np.asarray(indices), ids):
        raise ValueError("selected candidate order or identity mismatch")
    if [row["array_row"] for row in selected] != list(range(expected_count)):
        raise ValueError("selected archive row order mismatch")
    recordings = {}
    for row in selected:
        key = (row["source_subject"], row["session"])
        old = recordings.setdefault(key, row["recording_id"])
        if old != row["recording_id"]:
            raise ValueError("recording identity mismatch")
    if len(recordings) != 12 or len(set(recordings.values())) != 12:
        raise ValueError("recording set mismatch")
    return selected


def measurement_index(measurements, selected):
    expected = [(r["candidate_index"], v) for r in selected for v in VARIANTS]
    found = [(m["candidate_index"], m["variant"]) for m in measurements]
    if found != expected or len(set(found)) != len(found):
        raise ValueError("variant ledger duplicate, order, or identity mismatch")
    return {key: row for key, row in zip(found, measurements)}


def verify_ledger(prepared, codebrain, selected, old_measurements):
    """Bind every original/variant input and CodeBrain output to both archives."""
    if set(prepared) != {"patches", "candidate_indices", *(f"baseline_{v}" for v in VIEWS)}:
        raise ValueError("prepared archive member set mismatch")
    if set(codebrain) != {"embeddings", "candidate_indices", "variants"}:
        raise ValueError("CodeBrain archive member set mismatch")
    n = len(selected)
    if prepared["patches"].shape != (n, 4, 30, 200) or prepared["patches"].dtype != np.float32:
        raise ValueError("prepared patch shape or dtype mismatch")
    if codebrain["embeddings"].shape != (n, 5, 4, 30, 200) or codebrain["embeddings"].dtype != np.float32:
        raise ValueError("CodeBrain latent shape or dtype mismatch")
    if not np.array_equal(prepared["candidate_indices"], codebrain["candidate_indices"]):
        raise ValueError("archive candidate ordering mismatch")
    if tuple(codebrain["variants"]) != VARIANTS:
        raise ValueError("CodeBrain variant order mismatch")
    ledger = measurement_index(old_measurements, selected)
    for i, row in enumerate(selected):
        ci = row["candidate_index"]
        for j, variant in enumerate(VARIANTS):
            entry = ledger[ci, variant]
            x = previous.waveform_variant(prepared["patches"][i], variant, 9009 + ci)
            if previous.array_hash(x) != entry["input_sha256"]:
                raise ValueError(f"variant input hash mismatch: {ci}/{variant}")
            if previous.array_hash(codebrain["embeddings"][i, j]) != entry["output_sha256"]:
                raise ValueError(f"CodeBrain output hash mismatch: {ci}/{variant}")
            amplitude = float(np.max(np.abs(x)) * 100)
            if amplitude != entry["maximum_absolute_prepared_uv"]:
                raise ValueError(f"variant amplitude mismatch: {ci}/{variant}")
    return ledger


def validate_inputs(packet_root, require_checkpoint=True):
    """Validate frozen protocol, full receipts, archives and all 610 hash pairs."""
    packet = Path(packet_root)
    root = packet / "repo"
    require_hash(root / "protocol/experiment-011.json", PROTOCOL_SHA256, "frozen protocol")
    require_hash(packet / "input/experiment-011.json", PROTOCOL_SHA256, "supplied protocol")
    protocol = read(root / "protocol/experiment-011.json")
    freeze = read(packet / "input/FREEZE.json")
    if freeze["sha256"] != PROTOCOL_SHA256 or freeze["status"] != "FROZEN_BEFORE_SECOND_MODEL_SCIENTIFIC_INFERENCE":
        raise ValueError("protocol freeze mismatch")
    adapter = read(packet / "input/adapter-acceptance.json")
    if adapter["status"] != "ACCEPTED" or adapter["bead"] != "eco-uzwh8s.30":
        raise ValueError("adapter review not accepted")
    for relative, sha in adapter["files"].items():
        require_hash(root / relative, sha, f"accepted adapter {relative}")
    if require_checkpoint:
        checkpoint = packet / "input/pretrained_weights.pth"
        if checkpoint.stat().st_size != protocol["cbramod"]["checkpoint_bytes"]:
            raise ValueError("CBraMod checkpoint byte count mismatch")
        require_hash(checkpoint, protocol["cbramod"]["checkpoint_sha256"], "CBraMod checkpoint")
    for relative, sha in protocol["inputs"].items():
        require_hash(root / relative, sha, f"frozen input {relative}")
    prepared_receipt = read(root / protocol["selection"]["prepared_receipt"])
    old_run = read(root / protocol["codebrain"]["receipt"])
    if prepared_receipt["array_path"] != protocol["selection"]["prepared_archive"]:
        raise ValueError("prepared archive path mismatch")
    if old_run["array_path"] != protocol["codebrain"]["archive"] or old_run["status"] != "COMPLETE":
        raise ValueError("CodeBrain archive path or status mismatch")
    if old_run["checkpoint_sha256"] != protocol["codebrain"]["checkpoint_sha256"]:
        raise ValueError("CodeBrain checkpoint identity mismatch")
    if old_run["protocol_sha256"] != protocol["inputs"]["protocol/experiment-010.json"]:
        raise ValueError("CodeBrain protocol identity mismatch")
    if old_run["prepared_receipt_sha256"] != protocol["inputs"]["results/010/prepared.json"]:
        raise ValueError("CodeBrain prepared receipt identity mismatch")
    if old_run["prepared_archive_sha256"] != protocol["inputs"]["data/derived/010/prepared.npz"]:
        raise ValueError("CodeBrain prepared archive identity mismatch")
    for relative, sha in old_run["code_sha256"].items():
        require_hash(root / relative, sha, f"CodeBrain executable {relative}")
    p010 = read(root / "protocol/experiment-010.json")
    if distributed_study.validate_selection(root, prepared_receipt, p010)["status"] != "READY":
        raise ValueError("010 selection gate not ready")
    prepared, rows = previous.validate_prepared(root, prepared_receipt)
    if prepared_receipt["totals"]["eligible_blocks"] != protocol["selection"]["blocks"]:
        raise ValueError("selected block total mismatch")
    selected = selected_identity(prepared_receipt["records"], prepared["candidate_indices"], protocol["selection"]["blocks"])
    if rows != selected:
        raise ValueError("selected metadata identity mismatch")
    require_hash(root / old_run["array_path"], old_run["array_sha256"], "CodeBrain archive receipt")
    with np.load(root / old_run["array_path"], allow_pickle=False) as archive:
        codebrain = {k: archive[k] for k in archive.files}
    verify_ledger(prepared, codebrain, selected, old_run["measurements"])
    return dict(packet=packet, root=root, protocol=protocol, prepared=prepared,
                codebrain=codebrain, selected=selected, prepared_receipt=prepared_receipt,
                old_run=old_run)


def file_record(path, base):
    path = Path(path)
    return dict(path=str(path.relative_to(base)), bytes=path.stat().st_size, sha256=digest(path))


def runtime_record():
    import scipy
    import torch
    distributions = {}
    for name in ("numpy", "scipy", "torch"):
        dist = importlib.metadata.distribution(name)
        record = dist.read_text("RECORD")
        distributions[name] = dict(version=dist.version,
                                   record_sha256=None if record is None else hashlib.sha256(record.encode()).hexdigest())
    python_binary = Path(sys.executable).resolve()
    return dict(python=sys.version, executable=sys.executable,
                executable_resolved=str(python_binary), executable_sha256=digest(python_binary),
                platform=platform.platform(), distributions=distributions,
                numpy=np.__version__, scipy=scipy.__version__, torch=torch.__version__)


def freeze_manifest(inputs):
    packet, root = inputs["packet"], inputs["root"]
    path = root / "results/011/run-manifest.json"
    if path.exists():
        raise FileExistsError("preserve existing 011 run manifest")
    input_paths = ("input/experiment-011.json", "input/FREEZE.json",
                   "input/adapter-acceptance.json", "input/pretrained_weights.pth")
    inputs_files = {p: file_record(packet / p, packet) for p in input_paths}
    inputs_files.update({f"repo/{p}": file_record(root / p, packet)
                         for p in ("protocol/experiment-011.json", *inputs["protocol"]["inputs"].keys())})
    code_files = {p: file_record(root / p, root) for p in SOURCE_PATHS}
    manifest = dict(schema="eegt-cross-encoder-run-manifest/v1", status="FROZEN_BEFORE_INFERENCE",
                    frozen_at_utc=datetime.now(timezone.utc).isoformat(), protocol_sha256=PROTOCOL_SHA256,
                    expected_blocks=122, expected_forwards=610, input_files=inputs_files,
                    executable_and_dependency_files=code_files, runtime=runtime_record(),
                    input_identity_rule="Full receipts and archives plus every selected row and all variant input/output hashes validated before freeze")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        handle.write(canonical_json(manifest))
    return manifest


def verify_manifest(inputs, allow_analysis_amendment=False, require_checkpoint=True):
    packet, root = inputs["packet"], inputs["root"]
    path = root / "results/011/run-manifest.json"
    manifest = read(path)
    if manifest["protocol_sha256"] != PROTOCOL_SHA256 or manifest["status"] != "FROZEN_BEFORE_INFERENCE":
        raise ValueError("run manifest mismatch")
    for relative, record in manifest["input_files"].items():
        if relative == "input/pretrained_weights.pth" and not require_checkpoint:
            continue  # The pinned inference receipt binds weights; offline evaluation never loads them.
        target = packet / relative
        if target.stat().st_size != record["bytes"]:
            raise ValueError(f"manifest input byte count mismatch: {relative}")
        require_hash(target, record["sha256"], f"manifest input {relative}")
    for relative, record in manifest["executable_and_dependency_files"].items():
        target = root / relative
        if target.stat().st_size != record["bytes"]:
            changed = True
        else:
            changed = digest(target) != record["sha256"]
        if changed:
            if not allow_analysis_amendment or relative != "eegt/cross_encoder_study.py":
                raise ValueError(f"manifest source mismatch: {relative}")
            amendment_path = root / "results/011/analysis-amendment.json"
            amendment = read(amendment_path)
            if (amendment["schema"] != "eegt-cross-encoder-analysis-amendment/v1"
                    or amendment["scope"] != "COUNT_SERIALIZATION_AND_WEIGHTLESS_REPRODUCTION"
                    or amendment["base_manifest_sha256"] != digest(path)
                    or amendment["source_before_sha256"] != record["sha256"]
                    or amendment["source_after_sha256"] != digest(target)
                    or amendment["source_before_sha256"] != digest(root / "results/011/pre-amendment-cross_encoder_study.py")):
                raise ValueError("analysis amendment binding mismatch")
    return manifest


def infer(inputs):
    """Run precisely one CBraMod forward for each frozen block and variant."""
    from .cbramod import CBraModEncoder
    import torch

    root = inputs["root"]
    out = root / "results/011"
    array_path = root / "data/derived/011/embeddings.npz"
    if (out / "inference.json").exists() or array_path.exists() or (out / "failed.json").exists():
        raise FileExistsError("preserve existing or failed 011 inference")
    manifest = verify_manifest(inputs)
    if torch.get_num_threads() != 1:
        torch.set_num_threads(1)
    encoder = CBraModEncoder(inputs["packet"] / "input/pretrained_weights.pth")
    if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
        raise RuntimeError("numerical thread contract failed")
    outputs, measurements = [], []
    start = time.perf_counter()
    try:
        for i, row in enumerate(inputs["selected"]):
            ci = row["candidate_index"]
            block_outputs = []
            for variant in VARIANTS:
                x = previous.waveform_variant(inputs["prepared"]["patches"][i], variant, 9009 + ci)
                old = inputs["old_run"]["measurements"][i * 5 + len(block_outputs)]
                if previous.array_hash(x) != old["input_sha256"]:
                    raise ValueError(f"pre-forward input identity mismatch: {ci}/{variant}")
                began = time.perf_counter()
                y = encoder.encode(x[None])[0]
                seconds = time.perf_counter() - began
                if y.shape != (4, 30, 200) or y.dtype != np.float32 or not np.isfinite(y).all():
                    raise RuntimeError(f"CBraMod latent contract failed: {ci}/{variant}")
                block_outputs.append(y)
                measurements.append(dict(candidate_index=ci, variant=variant,
                                         input_sha256=previous.array_hash(x),
                                         output_sha256=previous.array_hash(y),
                                         maximum_absolute_prepared_uv=float(np.max(np.abs(x)) * 100),
                                         seconds=seconds))
            outputs.append(np.stack(block_outputs))
            if (i + 1) % 10 == 0 or i + 1 == len(inputs["selected"]):
                print(f"CBraMod {i + 1}/{len(inputs['selected'])} blocks; {len(measurements)} forwards", flush=True)
        if len(measurements) != 610 or len(outputs) != 122:
            raise RuntimeError("scientific forward count mismatch")
        grid = np.stack(outputs)
        previous.save_arrays(array_path, embeddings=grid,
                             candidate_indices=inputs["prepared"]["candidate_indices"],
                             variants=np.array(VARIANTS))
        receipt = dict(schema="eegt-cross-encoder-inference/v1", status="COMPLETE",
                       run_manifest_sha256=digest(out / "run-manifest.json"),
                       protocol_sha256=PROTOCOL_SHA256,
                       checkpoint_sha256=inputs["protocol"]["cbramod"]["checkpoint_sha256"],
                       prepared_archive_sha256=inputs["prepared_receipt"]["array_sha256"],
                       codebrain_archive_sha256=inputs["old_run"]["array_sha256"],
                       array_path=str(array_path.relative_to(root)), array_sha256=digest(array_path),
                       shape=list(grid.shape), variants=list(VARIANTS), block_variant_runs=len(measurements),
                       elapsed_seconds=time.perf_counter() - start,
                       maximum_rss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                       torch_version=torch.__version__, numpy_version=np.__version__,
                       torch_threads=torch.get_num_threads(), torch_interop_threads=torch.get_num_interop_threads(),
                       blas_threads={name: os.environ[name] for name in
                                     ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                                      "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")},
                       observed_at_utc=datetime.now(timezone.utc).isoformat(), measurements=measurements)
        atomic_json(out / "inference.json", receipt)
        return receipt
    except Exception:
        if outputs:
            previous.save_arrays(root / "data/derived/011/partial-embeddings.npz",
                                 embeddings=np.stack(outputs),
                                 candidate_indices=inputs["prepared"]["candidate_indices"][:len(outputs)],
                                 variants=np.array(VARIANTS))
        atomic_json(out / "failed.json", dict(schema="eegt-cross-encoder-failure/v1",
                                              run_manifest_sha256=digest(out / "run-manifest.json"),
                                              completed_blocks=len(outputs), completed_forwards=len(measurements),
                                              measurements=measurements, error=traceback.format_exc(),
                                              elapsed_seconds=time.perf_counter() - start))
        raise


def checked_vectors(array, kind="cosine"):
    """Return 378 geometry and 27 adjacent distances, or an exact abstention."""
    x = np.asarray(array)
    if x.ndim != 2 or x.shape[0] != 28 or x.shape[1] < 1:
        return None, "SHAPE_MISMATCH"
    if not np.isfinite(x).all():
        return None, "NONFINITE_VECTOR"
    if kind == "cosine":
        norms = np.linalg.norm(x.astype(np.float64), axis=1)
        if np.any(norms <= 1e-12):
            return None, "ZERO_NORM_VECTOR"
        d = previous.cosine_distances(x)
    elif kind == "rms":
        d = previous.rms_distances(x)
    else:
        raise ValueError("unknown distance type")
    upper = d[np.triu_indices(28, 1)]
    adjacent = np.diag(d, 1)
    if len(upper) != 378 or len(adjacent) != 27:
        raise RuntimeError("distance vector length mismatch")
    return {"geometry": upper, "change": adjacent}, None


def spearman_result(a, b, left_reason=None, right_reason=None):
    if left_reason:
        return None, "LEFT_" + left_reason
    if right_reason:
        return None, "RIGHT_" + right_reason
    if a is None or b is None or len(a) != len(b):
        return None, "DISTANCE_VECTOR_MISMATCH"
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        return None, "NONFINITE_DISTANCE_VECTOR"
    if np.all(a == a[0]) or np.all(b == b[0]):
        return None, "CONSTANT_DISTANCE_VECTOR"
    rho = previous.correlation(a, b)
    if rho is None or not np.isfinite(rho):
        return None, "UNDEFINED_CORRELATION"
    return rho, None


def aggregate_metric(blocks, selected, minimum_blocks=3):
    """All 12 record medians, all six two-session person means and exclusions."""
    by_id = {b["candidate_index"]: b for b in blocks}
    expected = [r["candidate_index"] for r in selected]
    if len(by_id) != len(blocks) or set(by_id) != set(expected):
        raise ValueError("aggregation block identity mismatch")
    by_record = defaultdict(list)
    for row in selected:
        by_record[(row["source_subject"], row["session"], row["recording_id"])].append(row)
    records = []
    for (person, session, recording_id), rows in sorted(by_record.items()):
        vals = [by_id[r["candidate_index"]]["value"] for r in rows]
        valid = [float(v) for v in vals if v is not None and np.isfinite(v)]
        excluded = [dict(candidate_index=r["candidate_index"],
                         reason=by_id[r["candidate_index"]]["reason"] or "NONFINITE_VALUE")
                    for r, value in zip(rows, vals) if value is None or not np.isfinite(value)]
        status = "VALID" if len(valid) >= minimum_blocks else "TOO_FEW_VALID_BLOCKS"
        records.append(dict(source_subject=person, session=session, recording_id=recording_id,
                            selected_blocks=len(rows), valid_blocks=len(valid), excluded=excluded,
                            status=status, median=None if status != "VALID" else float(np.median(valid))))
    by_person = defaultdict(dict)
    for record in records:
        by_person[record["source_subject"]][record["session"]] = record
    people = []
    for person in sorted(by_person):
        sessions = by_person[person]
        valid = all(s in sessions and sessions[s]["status"] == "VALID" for s in ("001", "002"))
        reasons = [] if valid else [f"{s}:" + (sessions[s]["status"] if s in sessions else "MISSING_SESSION")
                                    for s in ("001", "002") if s not in sessions or sessions[s]["status"] != "VALID"]
        people.append(dict(source_subject=person, status="COMPLETE" if valid else "INCOMPLETE_SESSIONS",
                           reasons=reasons, session_medians={s: sessions[s]["median"] for s in sorted(sessions)},
                           mean_two_sessions=(float((sessions["001"]["median"] + sessions["002"]["median"]) / 2)
                                              if valid else None)))
    scores = [p["mean_two_sessions"] for p in people if p["status"] == "COMPLETE"]
    return dict(selected_blocks=len(selected), valid_blocks=int(sum(b["value"] is not None and np.isfinite(b["value"]) for b in blocks)),
                records=records, participants=people, complete_participants=len(scores),
                mean_participant_value=None if not scores else float(np.mean(scores)))


def exact_signflip(effects):
    values = np.asarray(effects, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("signflip requires finite participant effects")
    observed = float(np.mean(values))
    means = [float(np.mean(values * np.array(signs, dtype=np.float64)))
             for signs in product((-1, 1), repeat=len(values))]
    count = sum(abs(v) >= abs(observed) - 1e-12 for v in means)
    return dict(n=len(values), observed_mean=observed, sign_combinations=len(means),
                extreme_count=count, p_two_sided=count / len(means),
                p_bonferroni_two=min(1.0, 2 * count / len(means)))


def paired_blocks(cross, selected, metric):
    by_key = {(entry["candidate_index"], entry["variant"]): entry for entry in cross}
    result = []
    for row in selected:
        ci = row["candidate_index"]
        original = by_key[ci, "original"]
        phase = by_key[ci, "independent_phase"]
        a, b = original[f"{metric}_rho"], phase[f"{metric}_rho"]
        reasons = []
        if a is None:
            reasons.append("ORIGINAL:" + original[f"{metric}_reason"])
        if b is None:
            reasons.append("INDEPENDENT_PHASE:" + phase[f"{metric}_reason"])
        result.append(dict(candidate_index=ci, metric=metric,
                           original_rho=a, independent_phase_rho=b,
                           delta=None if reasons else float(a - b),
                           reason=None if not reasons else ";".join(reasons)))
    return result


def primary_result(blocks, selected, metric, minimum_blocks=3, minimum_people=3):
    """Original, phase and delta each use precisely the paired-valid rows."""
    values = {}
    for field in ("delta", "original_rho", "independent_phase_rho"):
        entries = [dict(candidate_index=b["candidate_index"],
                        value=b[field] if b["delta"] is not None else None,
                        reason=b["reason"])
                   for b in blocks]
        values[field] = aggregate_metric(entries, selected, minimum_blocks)
    complete = [p for p in values["delta"]["participants"] if p["status"] == "COMPLETE"]
    result = dict(metric=metric, status="INSUFFICIENT_PARTICIPANTS", paired_valid_blocks=values["delta"]["valid_blocks"],
                  paired_support_candidate_indices=[b["candidate_index"] for b in blocks if b["delta"] is not None],
                  aggregates=values, test=None)
    if len(complete) >= minimum_people:
        result["status"] = "COMPARED"
        result["test"] = exact_signflip([p["mean_two_sessions"] for p in complete])
    return result


def metric_entries(rows, metric):
    reason_key = metric.removesuffix("_rho") + "_reason" if metric.endswith("_rho") else metric + "_reason"
    return [dict(candidate_index=r["candidate_index"],
                 value=r.get(metric), reason=r.get(reason_key)) for r in rows]


def evaluate_science(inputs, cbramod, inference):
    selected, prepared, codebrain = inputs["selected"], inputs["prepared"], inputs["codebrain"]
    if tuple(cbramod["variants"]) != VARIANTS or not np.array_equal(cbramod["candidate_indices"], prepared["candidate_indices"]):
        raise ValueError("CBraMod variant/candidate order mismatch")
    if cbramod["embeddings"].shape != (122, 5, 4, 30, 200) or cbramod["embeddings"].dtype != np.float32:
        raise ValueError("CBraMod latent shape or dtype mismatch")
    ledger = measurement_index(inference["measurements"], selected)
    for i, row in enumerate(selected):
        for j, variant in enumerate(VARIANTS):
            if previous.array_hash(cbramod["embeddings"][i, j]) != ledger[row["candidate_index"], variant]["output_sha256"]:
                raise ValueError(f"CBraMod output hash mismatch: {row['candidate_index']}/{variant}")
            if ledger[row["candidate_index"], variant]["input_sha256"] != inputs["old_run"]["measurements"][i * 5 + j]["input_sha256"]:
                raise ValueError("cross-model input mismatch")
    pooled = {
        "codebrain": codebrain["embeddings"].astype(np.float64).mean(axis=2)[:, :, 1:29],
        "cbramod": cbramod["embeddings"].astype(np.float64).mean(axis=2)[:, :, 1:29],
    }
    vectors = {}
    for model in ("codebrain", "cbramod"):
        for i in range(122):
            for j in range(5):
                vectors[model, i, j] = checked_vectors(pooled[model][i, j])
    cross = []
    controls = []
    descriptors = []
    for i, row in enumerate(selected):
        ci = row["candidate_index"]
        for j, variant in enumerate(VARIANTS):
            left, left_reason = vectors["codebrain", i, j]
            right, right_reason = vectors["cbramod", i, j]
            entry = dict(candidate_index=ci, variant=variant)
            for metric in METRICS:
                value, reason = spearman_result(None if left is None else left[metric],
                                                None if right is None else right[metric],
                                                left_reason, right_reason)
                entry[f"{metric}_rho"] = value
                entry[f"{metric}_reason"] = reason
            cross.append(entry)
        for model in ("codebrain", "cbramod"):
            original, original_reason = vectors[model, i, 0]
            for j, variant in enumerate(VARIANTS[1:], 1):
                changed, changed_reason = vectors[model, i, j]
                entry = dict(candidate_index=ci, model=model, variant=variant)
                for metric in METRICS:
                    value, reason = spearman_result(None if original is None else original[metric],
                                                    None if changed is None else changed[metric],
                                                    original_reason, changed_reason)
                    entry[f"{metric}_rho"] = value
                    entry[f"{metric}_reason"] = reason
                difference = pooled[model][i, j] - pooled[model][i, 0]
                entry["rms_embedding_displacement"] = (float(np.sqrt(np.mean(difference ** 2)))
                                                       if np.isfinite(difference).all() else None)
                entry["rms_embedding_displacement_reason"] = (None if entry["rms_embedding_displacement"] is not None
                                                                else "NONFINITE_EMBEDDING")
                receipt = (inputs["old_run"] if model == "codebrain" else inference)
                old = receipt["measurements"][i * 5 + j]
                entry["maximum_absolute_prepared_uv"] = old["maximum_absolute_prepared_uv"]
                entry["maximum_absolute_prepared_uv_reason"] = None
                controls.append(entry)
            for view in VIEWS:
                baseline, baseline_reason = checked_vectors(prepared["baseline_" + view][i], "rms")
                entry = dict(candidate_index=ci, model=model, view=view)
                for metric in METRICS:
                    value, reason = spearman_result(None if original is None else original[metric],
                                                    None if baseline is None else baseline[metric],
                                                    original_reason, baseline_reason)
                    entry[f"{metric}_rho"] = value
                    entry[f"{metric}_reason"] = reason
                descriptors.append(entry)
    paired = [b for metric in METRICS for b in paired_blocks(cross, selected, metric)]
    primary = [primary_result([b for b in paired if b["metric"] == metric], selected, metric,
                              inputs["protocol"]["selection"]["minimum_blocks_per_record"],
                              inputs["protocol"]["primary"]["minimum_people"]) for metric in METRICS]
    secondary = []
    for variant in VARIANTS:
        subset = [r for r in cross if r["variant"] == variant]
        for metric in METRICS:
            secondary.append(dict(family="cross_model", variant=variant, metric=metric,
                                  aggregate=aggregate_metric(metric_entries(subset, metric + "_rho"), selected)))
    for model in ("codebrain", "cbramod"):
        for variant in VARIANTS[1:]:
            subset = [r for r in controls if r["model"] == model and r["variant"] == variant]
            for metric in ("geometry_rho", "change_rho", "rms_embedding_displacement",
                           "maximum_absolute_prepared_uv"):
                secondary.append(dict(family="within_model", model=model, variant=variant, metric=metric,
                                      aggregate=aggregate_metric(metric_entries(subset, metric), selected)))
        for view in VIEWS:
            subset = [r for r in descriptors if r["model"] == model and r["view"] == view]
            for metric in METRICS:
                secondary.append(dict(family="descriptor", model=model, view=view, metric=metric,
                                      aggregate=aggregate_metric(metric_entries(subset, metric + "_rho"), selected)))
    if (len(cross), len(controls), len(descriptors), len(paired), len(secondary)) != (610, 976, 732, 244, 54):
        raise RuntimeError("planned output count mismatch")
    return dict(schema="eegt-cross-encoder-summary/v1", status="EVALUATED",
                question=inputs["protocol"]["question"], protocol_sha256=PROTOCOL_SHA256,
                selected_blocks=len(selected), selected_seconds=len(selected) * 30,
                source_selection_gate=inputs["prepared_receipt"]["inference_gate"],
                primary=primary, secondary=secondary, block_cross_model=cross,
                block_within_model=controls, block_descriptors=descriptors, block_paired=paired,
                source_rejection_counts=inputs["prepared_receipt"]["rejection_counts"],
                discrete_test_limit_n5=dict(minimum_two_sided_p=0.0625, minimum_bonferroni_two_p=0.125),
                inference_limit="Exploratory exposed development data. A sign-flip test assumes independent people and sign symmetry of their paired effects. Shared architecture, training material, filtering, montage, and artifacts may explain alignment. No semantic, diagnostic, universal-token, or physical transfer claim.")


def write_sqlite(path, inputs, summary, inference):
    path = Path(path)
    if path.exists():
        raise FileExistsError("preserve existing analysis database")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".partial")
    if partial.exists():
        raise FileExistsError("preserve partial analysis database")
    db = sqlite3.connect(partial)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("""
        CREATE TABLE candidates(candidate_index INTEGER PRIMARY KEY, recording_id TEXT NOT NULL,
          source_subject TEXT NOT NULL, session TEXT NOT NULL, start_seconds INTEGER NOT NULL,
          status TEXT NOT NULL, receipt_json TEXT NOT NULL);
        CREATE TABLE model_outputs(candidate_index INTEGER NOT NULL REFERENCES candidates(candidate_index),
          model TEXT NOT NULL, variant TEXT NOT NULL, input_sha256 TEXT NOT NULL,
          output_sha256 TEXT NOT NULL, receipt_json TEXT NOT NULL,
          PRIMARY KEY(candidate_index,model,variant));
        CREATE TABLE cross_model(candidate_index INTEGER NOT NULL REFERENCES candidates(candidate_index),
          variant TEXT NOT NULL, geometry_rho REAL, change_rho REAL, receipt_json TEXT NOT NULL,
          PRIMARY KEY(candidate_index,variant));
        CREATE TABLE within_model(candidate_index INTEGER NOT NULL REFERENCES candidates(candidate_index),
          model TEXT NOT NULL, variant TEXT NOT NULL, receipt_json TEXT NOT NULL,
          PRIMARY KEY(candidate_index,model,variant));
        CREATE TABLE descriptors(candidate_index INTEGER NOT NULL REFERENCES candidates(candidate_index),
          model TEXT NOT NULL, view TEXT NOT NULL, receipt_json TEXT NOT NULL,
          PRIMARY KEY(candidate_index,model,view));
        CREATE TABLE paired(candidate_index INTEGER NOT NULL REFERENCES candidates(candidate_index),
          metric TEXT NOT NULL, original_rho REAL, independent_phase_rho REAL, delta REAL,
          reason TEXT, receipt_json TEXT NOT NULL, PRIMARY KEY(candidate_index,metric),
          CHECK((delta IS NULL AND reason IS NOT NULL) OR (delta IS NOT NULL AND reason IS NULL)));
        CREATE TABLE primary_tests(metric TEXT PRIMARY KEY, status TEXT NOT NULL,
          complete_participants INTEGER NOT NULL, p_two_sided REAL, p_bonferroni_two REAL,
          receipt_json TEXT NOT NULL);
        CREATE TABLE statistics(statistic_id TEXT PRIMARY KEY, family TEXT NOT NULL,
          metric TEXT NOT NULL, receipt_json TEXT NOT NULL);
        CREATE TABLE aggregate_records(statistic_id TEXT NOT NULL REFERENCES statistics(statistic_id),
          source_subject TEXT NOT NULL, session TEXT NOT NULL, receipt_json TEXT NOT NULL,
          PRIMARY KEY(statistic_id,source_subject,session));
        CREATE TABLE aggregate_people(statistic_id TEXT NOT NULL REFERENCES statistics(statistic_id),
          source_subject TEXT NOT NULL, receipt_json TEXT NOT NULL,
          PRIMARY KEY(statistic_id,source_subject));
        """)
        for r in inputs["prepared_receipt"]["records"]:
            db.execute("INSERT INTO candidates VALUES(?,?,?,?,?,?,?)", (r["candidate_index"], r["recording_id"],
                       r["source_subject"], r["session"], r["start_seconds"], r["status"], canonical_json(r)))
        for model, receipt in (("codebrain", inputs["old_run"]), ("cbramod", inference)):
            for r in receipt["measurements"]:
                db.execute("INSERT INTO model_outputs VALUES(?,?,?,?,?,?)", (r["candidate_index"], model,
                           r["variant"], r["input_sha256"], r["output_sha256"], canonical_json(r)))
        for r in summary["block_cross_model"]:
            db.execute("INSERT INTO cross_model VALUES(?,?,?,?,?)", (r["candidate_index"], r["variant"],
                       r["geometry_rho"], r["change_rho"], canonical_json(r)))
        for r in summary["block_within_model"]:
            db.execute("INSERT INTO within_model VALUES(?,?,?,?)", (r["candidate_index"], r["model"],
                       r["variant"], canonical_json(r)))
        for r in summary["block_descriptors"]:
            db.execute("INSERT INTO descriptors VALUES(?,?,?,?)", (r["candidate_index"], r["model"],
                       r["view"], canonical_json(r)))
        for r in summary["block_paired"]:
            db.execute("INSERT INTO paired VALUES(?,?,?,?,?,?,?)", (r["candidate_index"], r["metric"],
                       r["original_rho"], r["independent_phase_rho"], r["delta"], r["reason"], canonical_json(r)))
        for r in summary["primary"]:
            test = r["test"]
            db.execute("INSERT INTO primary_tests VALUES(?,?,?,?,?,?)",
                       (r["metric"], r["status"], r["aggregates"]["delta"]["complete_participants"],
                        None if test is None else test["p_two_sided"],
                        None if test is None else test["p_bonferroni_two"], canonical_json(r)))
        stats = []
        for p in summary["primary"]:
            for field, aggregate in p["aggregates"].items():
                stats.append((f"primary:{p['metric']}:{field}", "primary", p["metric"], aggregate))
        for s in summary["secondary"]:
            identifier = ":".join(str(s[k]) for k in ("family", "model", "variant", "view", "metric") if k in s)
            stats.append((identifier, s["family"], s["metric"], s["aggregate"]))
        for stat_id, family, metric, agg in stats:
            db.execute("INSERT INTO statistics VALUES(?,?,?,?)", (stat_id, family, metric, canonical_json(agg)))
            for record in agg["records"]:
                db.execute("INSERT INTO aggregate_records VALUES(?,?,?,?)", (stat_id, record["source_subject"],
                           record["session"], canonical_json(record)))
            for person in agg["participants"]:
                db.execute("INSERT INTO aggregate_people VALUES(?,?,?)", (stat_id, person["source_subject"],
                           canonical_json(person)))
        db.commit()
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite integrity or foreign-key check failed")
        counts = {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                  for table in ("candidates", "model_outputs", "cross_model", "within_model", "descriptors",
                                "paired", "primary_tests", "statistics", "aggregate_records", "aggregate_people")}
        if any(counts[k] != v for k, v in {"candidates": 5760, "model_outputs": 1220,
                                            "cross_model": 610, "within_model": 976,
                                            "descriptors": 732, "paired": 244, "primary_tests": 2,
                                            "statistics": 60, "aggregate_records": 720,
                                            "aggregate_people": 360}.items()):
            raise ValueError(f"SQLite row counts mismatch: {counts}")
    finally:
        db.close()
    partial.replace(path)
    return counts


def evaluate(packet_root, output_dir):
    """Offline analysis; only the frozen arrays, receipts and sources are read."""
    inputs = validate_inputs(packet_root, require_checkpoint=False)
    verify_manifest(inputs, allow_analysis_amendment=True, require_checkpoint=False)
    root = inputs["root"]
    inference = read(root / "results/011/inference.json")
    if inference["status"] != "COMPLETE" or inference["run_manifest_sha256"] != digest(root / "results/011/run-manifest.json"):
        raise ValueError("011 inference/manifest binding mismatch")
    if inference["protocol_sha256"] != PROTOCOL_SHA256 or inference["block_variant_runs"] != 610:
        raise ValueError("011 protocol/forward count mismatch")
    if inference["checkpoint_sha256"] != inputs["protocol"]["cbramod"]["checkpoint_sha256"]:
        raise ValueError("011 checkpoint receipt identity mismatch")
    require_hash(root / inference["array_path"], inference["array_sha256"], "CBraMod archive")
    with np.load(root / inference["array_path"], allow_pickle=False) as archive:
        if set(archive.files) != {"embeddings", "candidate_indices", "variants"}:
            raise ValueError("CBraMod archive member set mismatch")
        cbramod = {k: archive[k] for k in archive.files}
    summary = evaluate_science(inputs, cbramod, inference)
    out = Path(output_dir)
    if (out / "summary.json").exists() or (out / "analysis.sqlite").exists():
        raise FileExistsError("preserve existing evaluation")
    counts = write_sqlite(out / "analysis.sqlite", inputs, summary, inference)
    summary["input_hashes"] = dict(run_manifest=digest(root / "results/011/run-manifest.json"),
                                   analysis_amendment=digest(root / "results/011/analysis-amendment.json"),
                                   cbramod_archive=inference["array_sha256"],
                                   codebrain_archive=inputs["old_run"]["array_sha256"],
                                   prepared_archive=inputs["prepared_receipt"]["array_sha256"])
    summary["database"] = dict(sha256=digest(out / "analysis.sqlite"), row_counts=counts,
                               integrity_check="ok", foreign_key_check="ok")
    atomic_json(out / "summary.json", summary)
    return summary


def compare_science(reference, reproduced, tolerance=1e-12):
    """Compare every scalar and nested scientific value, excluding DB byte hashes."""
    def check(a, b, path="root"):
        if isinstance(a, dict) and isinstance(b, dict):
            if set(a) != set(b):
                raise AssertionError(f"reproduction keys differ at {path}")
            for key in a:
                if key == "database":
                    check({k: v for k, v in a[key].items() if k != "sha256"},
                          {k: v for k, v in b[key].items() if k != "sha256"}, path + ".database")
                else:
                    check(a[key], b[key], path + "." + key)
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                raise AssertionError(f"reproduction length differs at {path}")
            for i, (x, y) in enumerate(zip(a, b)):
                check(x, y, f"{path}[{i}]")
        elif isinstance(a, (int, float)) and not isinstance(a, bool):
            if not isinstance(b, (int, float)) or not np.isclose(a, b, rtol=0, atol=tolerance):
                raise AssertionError(f"reproduction numeric mismatch at {path}: {a} vs {b}")
        elif a != b:
            raise AssertionError(f"reproduction mismatch at {path}: {a} vs {b}")
    check(reference, reproduced)
    return True
