"""Experiment 013 analysis over hash-bound numeric intake and separate identities.

This module contains no source downloader or EEG decoder. Normal empirical calls
require both the accepted pre-acquisition freeze and post-preparation acceptance.
The exposed-012 verifier reads archived outputs only; it never calls an encoder or
detector. Scientific numerical functions are imported from the released modules.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import scipy
import sqlite3
import sys
import time

import numpy as np

from . import distributed_study, event_study as old, pretrained_study, waveform_events as wave
from .validation_provenance import verify_loaded_sources


MODELS = old.MODELS
METRICS = old.METRICS
PREPARED_VARIANTS = old.PREPARED_VARIANTS
NATIVE_VARIANTS = old.NATIVE_VARIANTS
FREEZE_SCHEMA = "eegt-validation-run-source-manifest/v1"
INPUT_ACCEPTANCE_SCHEMA = "eegt-validation-input-acceptance/v1"
THREAD_ENV = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")
REQUIRED_FROZEN_INPUTS = (
    "protocol/experiment-013.json", "protocol/corpus-manifest-013.json",
    "eegt/validation_provenance.py", "eegt/validation_intake.py", "scripts/prepare_validation.py",
    "tests/test_validation_intake.py", "eegt/validation_study.py",
    "scripts/reproduce_validation.py", "tests/test_validation_study.py",
    "eegt/event_study.py", "eegt/waveform_events.py", "eegt/transitions.py",
    "eegt/pretrained_study.py", "eegt/distributed_study.py",
    "eegt/pretrained.py", "eegt/cbramod.py",
    "requirements-events.lock", "requirements-encoder.lock", "requirements.lock",
)


def digest(path: Path) -> str:
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def read_json(path: Path):
    return json.loads(Path(path).read_text())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError(f"unsafe relative path: {relative!r}")
    target = root / relative
    if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"path leaves root: {relative}")
    return target


def verify_hash_map(root: Path, entries: dict, *, label: str) -> None:
    if not isinstance(entries, dict) or not entries:
        raise ValueError(f"{label} hash map missing")
    for relative, expected in entries.items():
        target = _inside(root, relative)
        sha = expected.get("sha256") if isinstance(expected, dict) else expected
        if not isinstance(sha, str) or len(sha) != 64 or not target.is_file() or digest(target) != sha:
            raise ValueError(f"{label} SHA256 mismatch: {relative}")
        if isinstance(expected, dict) and "bytes" in expected and target.stat().st_size != expected["bytes"]:
            raise ValueError(f"{label} byte count mismatch: {relative}")


def runtime_identity() -> dict:
    python = Path(sys.executable).resolve()
    packages = {}
    for name in ("numpy", "scipy", "torch", "bycycle", "neurodsp"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return dict(python=str(python), python_sha256=digest(python),
                python_version=platform.python_version(), packages=packages,
                threads={name: os.environ.get(name) for name in THREAD_ENV})


def phase_runtime(stage: str) -> dict:
    """Fields shared with the corpus/encoder/events freeze verifier."""
    result = dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__)
    if stage == "events":
        result.update(bycycle=importlib.metadata.version("bycycle"),
                      neurodsp=importlib.metadata.version("neurodsp"))
    return result


def require_torch_runtime(freeze: dict) -> str:
    expected = freeze.get("runtimes", {}).get("encoder", {}).get("torch")
    try:
        actual = importlib.metadata.version("torch")
    except importlib.metadata.PackageNotFoundError:
        actual = None
    if not isinstance(expected, str) or not expected or actual != expected:
        raise ValueError(f"encoder Torch runtime mismatch: frozen={expected!r}, actual={actual!r}")
    return actual


def require_accepted_freeze(root: Path, *, stage: str | None = None) -> dict:
    """Fail closed on source/runtime drift, preferring the intake shared verifier.

    The intake module is absent in the isolated analysis packet. The local checks
    also run when the shared verifier is available so an omitted source cannot
    silently weaken this analysis boundary.
    """
    root = Path(root)
    shared_seal = None
    if importlib.util.find_spec("eegt.validation_intake") is not None:
        validation_intake = importlib.import_module("eegt.validation_intake")
        shared = getattr(validation_intake, "require_accepted_freeze", None)
        if shared is not None:
            shared_seal, _, _ = shared(root=root, phase=stage or "encoder")
    path = root / "results/013/RUN-SOURCE-MANIFEST.json"
    manifest = read_json(path)
    if manifest.get("schema") != FREEZE_SCHEMA or manifest.get("status") != "ACCEPTED":
        raise ValueError("accepted pre-acquisition freeze missing")
    if shared_seal is not None and canonical(shared_seal) != canonical(manifest):
        raise ValueError("shared/local freeze identity mismatch")
    if not set(REQUIRED_FROZEN_INPUTS).issubset(manifest.get("inputs", {})):
        raise ValueError("frozen source census incomplete")
    verify_hash_map(root, manifest["inputs"], label="frozen input")
    protocol = read_json(root / "protocol/experiment-013.json")
    if protocol.get("state") != "FROZEN":
        raise ValueError("protocol is not frozen")
    reviews = manifest.get("accepted_reviews")
    if not isinstance(reviews, list) or not reviews:
        raise ValueError("accepted review references missing")
    for review in reviews:
        if not isinstance(review, dict) or review.get("status") != "ACCEPTED":
            raise ValueError("accepted review status missing")
        verify_hash_map(root, {review["path"]: review["sha256"]}, label="accepted review")
    models = manifest.get("models", {})
    if set(models) != set(MODELS):
        raise ValueError("both model identities required")
    for name in MODELS:
        model = models[name]
        checkpoint = model.get("checkpoint", {})
        vendors = model.get("vendor_sources")
        if not isinstance(vendors, dict) or not vendors:
            raise ValueError(f"{name} vendor sources missing")
        verify_hash_map(root, {checkpoint["path"]: checkpoint["sha256"],
                               **vendors}, label=f"{name} model")
    bounds = manifest.get("resource_bounds", {})
    if any(not isinstance(bounds.get(key), (int, float)) or bounds[key] <= 0
           for key in ("cpu_seconds", "rss_bytes", "artifact_bytes")) or bounds.get("first_block_required") is not True:
        raise ValueError("fixed resource bounds and first-block gate required")
    verify_loaded_sources(manifest)
    verify_source(protocol, read_json(root / "protocol/corpus-manifest-013.json"))
    if stage is not None:
        actual = phase_runtime(stage)
        expected = manifest.get("runtimes", {}).get(stage)
        threads = runtime_identity()["threads"]
        if (not isinstance(expected, dict) or
                any(expected.get(key) != value for key, value in actual.items()) or
                ("python_sha256" in expected and expected["python_sha256"] != digest(Path(sys.executable).resolve())) or
                any(value != "1" for value in threads.values())):
            raise ValueError(f"{stage} runtime identity or one-thread limit mismatch")
    return manifest


def require_input_acceptance(root: Path, freeze: dict) -> dict:
    """Bind outputs produced after the source freeze, before inference/events."""
    root = Path(root)
    acceptance = read_json(root / "results/013/INPUT-ACCEPTANCE.json")
    if acceptance.get("schema") != INPUT_ACCEPTANCE_SCHEMA or acceptance.get("status") != "ACCEPTED":
        raise ValueError("post-preparation input acceptance missing")
    if acceptance.get("run_source_manifest_sha256") != digest(root / "results/013/RUN-SOURCE-MANIFEST.json"):
        raise ValueError("input acceptance/freeze join mismatch")
    required = {"results/013/prepared.json", "data/derived/013/native-selected.npz",
                "data/derived/013/prepared.npz"}
    if not required.issubset(acceptance.get("inputs", {})):
        raise ValueError("post-preparation numeric input census incomplete")
    verify_hash_map(root, acceptance["inputs"], label="accepted prepared input")
    return acceptance


def recording_id(source: dict, row: dict) -> str:
    file_path = row["file"]["path"]
    origin = f"{source['source']['dataset']}:{source['source']['commit']}:{file_path}"
    return hashlib.sha256(origin.encode()).hexdigest()[:24]


def verify_source(protocol: dict, source: dict) -> list[dict]:
    rows = source["records"]
    expected = {(person, night): cohort["id"] for cohort in protocol["cohorts"]
                for person in cohort["people"] for night in cohort["sessions"]}
    actual = [(r["source_subject"], r["session"]) for r in rows]
    if (len(rows) != len(expected) or len(set(actual)) != len(actual) or set(actual) != set(expected)
            or actual != sorted(actual)):
        raise ValueError("source record census, order, or identity mismatch")
    ids = []
    for row in rows:
        pair = row["source_subject"], row["session"]
        if row["cohort"] != expected[pair] or row["recording_id"] != recording_id(source, row):
            raise ValueError(f"source cohort or recording ID mismatch: {pair}")
        if row["file"].get("algorithm") != "sha256" or len(row["file"].get("expected_digest", "")) != 64:
            raise ValueError(f"source content hash missing: {pair}")
        ids.append(row["recording_id"])
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate recording ID")
    return rows


def cohort_gates(rows: list[dict], protocol: dict) -> dict:
    counts = Counter((r["cohort"], r["source_subject"], r["session"])
                     for r in rows if r["status"] == "ELIGIBLE")
    minimum_blocks = protocol["aggregation"]["minimum_paired_metric_blocks_per_recording"]
    minimum_people = protocol["aggregation"]["minimum_complete_people_per_cohort"]
    gates = {}
    for cohort in protocol["cohorts"]:
        key, nights = cohort["id"], tuple(cohort["sessions"])
        census = [dict(source_subject=p, session=n, selected_blocks=counts[key, p, n])
                  for p in cohort["people"] for n in nights]
        complete = [p for p in cohort["people"] if all(counts[key, p, n] >= minimum_blocks for n in nights)]
        gates[key] = dict(status="READY" if len(complete) >= minimum_people else "INSUFFICIENT_PARTICIPANTS",
                          complete_participants=complete, complete_participant_count=len(complete),
                          minimum_blocks_per_night=minimum_blocks,
                          minimum_complete_participants=minimum_people, records=census)
    return gates


@dataclass
class ValidatedInputs:
    protocol: dict
    source: dict
    receipt: dict
    native: dict
    prepared: dict
    selected: list[dict]
    gates: dict


def validate_inputs(protocol: dict, source: dict, receipt: dict,
                    native: dict, prepared: dict) -> ValidatedInputs:
    """Independently recompute the full census, selection, joins and row hashes."""
    records = verify_source(protocol, source)
    per_record = protocol["selection"]["candidate_blocks_per_recording"]
    block_seconds = protocol["selection"]["block_seconds"]
    stratum_seconds = protocol["selection"]["stratum_seconds"]
    rows = receipt["records"]
    if len(rows) != len(records) * per_record:
        raise ValueError("candidate census count mismatch")
    if [r["candidate_index"] for r in rows] != list(range(len(rows))):
        raise ValueError("candidate index census mismatch")
    for i, row in enumerate(rows):
        source_row = records[i // per_record]
        expected = (source_row["recording_id"], source_row["source_subject"],
                    source_row["session"], source_row["cohort"])
        if tuple(row[k] for k in ("recording_id", "source_subject", "session", "cohort")) != expected:
            raise ValueError(f"candidate/source identity mismatch: {i}")
        start = (i % per_record) * block_seconds
        if (row["start_seconds"] != start or row["duration_seconds"] != block_seconds or
                row["stratum_index"] != start // stratum_seconds):
            raise ValueError(f"candidate time mismatch: {i}")
        quality_ok = row["quality_status"] == "PASS"
        if row["quality_status"] not in ("PASS", "FAIL") or quality_ok != (not row["reasons"]):
            raise ValueError(f"candidate quality/reasons mismatch: {i}")
    expected_selected = set(distributed_study.selected_indices(rows))
    selected = []
    for row in rows:
        ci = row["candidate_index"]
        status = ("ELIGIBLE" if ci in expected_selected else
                  "QUALIFIED_UNSELECTED" if row["quality_status"] == "PASS" else "REJECTED")
        if row["status"] != status:
            raise ValueError(f"selection/status mismatch: {ci}")
        if status == "ELIGIBLE":
            if row["array_row"] != len(selected):
                raise ValueError(f"array-row/candidate join mismatch: {ci}")
            selected.append(row)
        elif row.get("array_row") is not None:
            raise ValueError(f"unselected array row: {ci}")
    ids = [r["candidate_index"] for r in selected]
    n = len(ids)
    if (set(native) - {"samples_uv", "valid", "candidate_indices", "sample_rate_hz"} or
            set(prepared) - {"patches", "candidate_indices"} or
            native["samples_uv"].shape != (n, 4, 7500) or native["samples_uv"].dtype != np.float64 or
            native["valid"].shape != (n, 4, 7500) or native["valid"].dtype != np.bool_ or
            prepared["patches"].shape != (n, 4, 30, 200) or prepared["patches"].dtype != np.float32 or
            not np.array_equal(native["candidate_indices"], ids) or
            not np.array_equal(prepared["candidate_indices"], ids) or
            not np.all(native["valid"]) or
            not np.isfinite(native["samples_uv"]).all() or not np.isfinite(prepared["patches"]).all()):
        raise ValueError("numeric array shape, dtype, mask, order or finite contract mismatch")
    if "sample_rate_hz" in native and float(native["sample_rate_hz"]) != 250:
        raise ValueError("native sample rate mismatch")
    for i, row in enumerate(selected):
        if (row.get("native_array_sha256") != pretrained_study.array_hash(native["samples_uv"][i]) or
                row.get("valid_mask_sha256") != pretrained_study.array_hash(native["valid"][i]) or
                row.get("prepared_array_sha256") != pretrained_study.array_hash(prepared["patches"][i])):
            raise ValueError(f"selected numeric row hash mismatch: {row['candidate_index']}")
    gates = cohort_gates(rows, protocol)
    if receipt.get("inference_gates") != gates:
        raise ValueError("cohort inference gates mismatch")
    return ValidatedInputs(protocol, source, receipt, native, prepared, selected, gates)


def load_inputs(root: Path) -> ValidatedInputs:
    root = Path(root)
    receipt_path = root / "results/013/prepared.json"
    receipt = read_json(receipt_path)
    verify_hash_map(root, receipt["inputs"], label="prepared receipt input")
    if (receipt["inputs"].get("protocol/experiment-013.json") != digest(root / "protocol/experiment-013.json")
            or receipt["inputs"].get("protocol/corpus-manifest-013.json") != digest(root / "protocol/corpus-manifest-013.json")):
        raise ValueError("prepared receipt/protocol/source join mismatch")
    native_path = _inside(root, receipt["native_array_path"])
    prepared_path = _inside(root, receipt["array_path"])
    if digest(native_path) != receipt["native_array_sha256"] or digest(prepared_path) != receipt["array_sha256"]:
        raise ValueError("numeric archive SHA256 mismatch")
    with np.load(native_path, allow_pickle=False) as archive:
        native = {name: archive[name] for name in archive.files}
    with np.load(prepared_path, allow_pickle=False) as archive:
        prepared = {name: archive[name] for name in archive.files}
    return validate_inputs(read_json(root / "protocol/experiment-013.json"),
                           read_json(root / "protocol/corpus-manifest-013.json"),
                           receipt, native, prepared)


def checked_model_archive(root: Path, name: str, inputs: ValidatedInputs,
                          freeze: dict, acceptance: dict,
                          *, allow_synthetic: bool = False) -> tuple[dict | None, dict]:
    """Return complete model output or an explicit absence; reject corrupt success."""
    if name not in MODELS:
        raise ValueError("unknown model")
    path = root / f"results/013/inference-{name}.json"
    if not path.exists():
        return None, dict(status="MISSING", reason="INFERENCE_RECEIPT_MISSING")
    receipt = read_json(path)
    if receipt.get("status") != "COMPLETE":
        return None, dict(status=receipt.get("status", "FAILED"),
                          reason=receipt.get("reason", "INCOMPLETE_MODEL_INFERENCE"))
    array_path = _inside(root, receipt["array_path"])
    bindings = {"prepared_receipt_sha256": digest(root / "results/013/prepared.json"),
                "prepared_archive_sha256": inputs.receipt["array_sha256"],
                "input_acceptance_sha256": digest(root / "results/013/INPUT-ACCEPTANCE.json"),
                "run_manifest_sha256": digest(root / "results/013/RUN-SOURCE-MANIFEST.json"),
                "protocol_sha256": digest(root / "protocol/experiment-013.json"),
                "source_manifest_sha256": digest(root / "protocol/corpus-manifest-013.json"),
                "checkpoint_sha256": freeze["models"][name]["checkpoint"]["sha256"],
                "array_sha256": digest(array_path)}
    if any(receipt.get(key) != value for key, value in bindings.items()):
        raise ValueError(f"{name} inference source or output hash mismatch")
    implementation = receipt.get("encoder_implementation")
    if implementation not in ("PINNED_CHECKPOINT", "SYNTHETIC_FACTORY"):
        raise ValueError(f"{name} encoder implementation missing")
    if implementation == "SYNTHETIC_FACTORY" and not allow_synthetic:
        raise ValueError(f"{name} synthetic encoder archive cannot enter empirical evaluation")
    expected_runtime = {key: freeze["runtimes"]["encoder"][key]
                        for key in phase_runtime("encoder")}
    if implementation == "PINNED_CHECKPOINT":
        expected_runtime["torch"] = freeze["runtimes"]["encoder"].get("torch")
        if not isinstance(expected_runtime["torch"], str) or not expected_runtime["torch"]:
            raise ValueError(f"{name} frozen Torch version missing")
    if (receipt.get("runtime_contract") != expected_runtime or
            receipt.get("runtime", {}).get("threads") != dict.fromkeys(THREAD_ENV, "1")):
        raise ValueError(f"{name} inference runtime contract mismatch")
    if (implementation == "PINNED_CHECKPOINT" and
            receipt["runtime"].get("packages", {}).get("torch") != expected_runtime["torch"]):
        raise ValueError(f"{name} inference Torch provenance mismatch")
    with np.load(array_path, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    ready_ids = [r["candidate_index"] for r in inputs.selected if inputs.gates[r["cohort"]]["status"] == "READY"]
    emb = data.get("embeddings")
    if (set(data) != {"embeddings", "candidate_indices", "variants"} or
            emb.shape != (len(ready_ids), 5, 4, 30, 200) or emb.dtype != np.float32 or
            not np.isfinite(emb).all() or
            not np.array_equal(data["candidate_indices"], ready_ids) or
            tuple(data["variants"]) != PREPARED_VARIANTS or
            len(receipt.get("measurements", [])) != 5 * len(ready_ids)):
        raise ValueError(f"{name} inference shape/order/count mismatch")
    selected_by_id = {r["candidate_index"]: r for r in inputs.selected}
    for i, ci in enumerate(ready_ids):
        source_row = selected_by_id[ci]
        block = inputs.prepared["patches"][source_row["array_row"]]
        for j, variant in enumerate(PREPARED_VARIANTS):
            x = pretrained_study.waveform_variant(block, variant, 9009 + ci)
            old.checked_measurement(receipt["measurements"][5*i+j], ci, variant,
                                    pretrained_study.array_hash(x),
                                    pretrained_study.array_hash(emb[i, j]))
    return data, dict(status="COMPLETE", reason=None, verified_forwards=5 * len(ready_ids))


def compare_prepared_results(results: dict, embeddings: dict[str, np.ndarray]) -> tuple[dict, list[dict], list[dict]]:
    """Use released support and numerical methods with whichever models exist."""
    if set(results) != set(PREPARED_VARIANTS):
        raise ValueError("five prepared event variants required")
    counts, eligible = {}, {}
    for name in PREPARED_VARIANTS:
        counts[name], eligible[name] = old.event_counts(results[name])
    base_k, base_pairs = old.support_indices(eligible["original"], eligible["independent_phase"])
    supports, comparisons, effects = {}, [], []
    for variant in PREPARED_VARIANTS:
        k, pairs = ((base_k, base_pairs) if variant in ("original", "independent_phase") else
                    old.support_indices(eligible["original"], eligible["independent_phase"], eligible[variant]))
        supports[variant] = dict(interval_indices=k, adjacent_pairs=pairs,
                                 all_channel_eligible_intervals=eligible[variant])
        j = PREPARED_VARIANTS.index(variant)
        for model, emb in embeddings.items():
            if model not in MODELS or emb.shape != (5, 4, 30, 200) or emb.dtype != np.float32 or not np.isfinite(emb).all():
                raise ValueError(f"invalid model block: {model}")
            latent = np.mean(emb[j], axis=0, dtype=np.float64)
            for metric in METRICS:
                result = old.metric_result(counts[variant], latent, k, pairs, metric)
                comparisons.append(dict(model=model, variant=variant, metric=metric,
                                        support=supports[variant], **result))
    by_key = {(r["model"], r["variant"], r["metric"]): r for r in comparisons}
    for model in embeddings:
        for metric in METRICS:
            original, phase = by_key[model, "original", metric], by_key[model, "independent_phase", metric]
            reasons = [f"{name}:{row['reason']}" for name, row in
                       (("original", original), ("independent_phase", phase)) if row["rho"] is None]
            effects.append(dict(model=model, metric=metric, original_rho=original["rho"],
                                independent_phase_rho=phase["rho"],
                                effect=None if reasons else original["rho"] - phase["rho"],
                                reason=";".join(reasons) if reasons else None))
    return supports, comparisons, effects


def fill_effect_rows(selected: list[dict], existing: list[dict], gates: dict) -> list[dict]:
    by_id = {r["candidate_index"]: r for r in selected}
    by_key = {}
    for effect in existing:
        key = effect["candidate_index"], effect["model"], effect["metric"]
        if (key in by_key or key[0] not in by_id or key[1] not in MODELS or key[2] not in METRICS or
                (effect["effect"] is None) != (effect["reason"] is not None)):
            raise ValueError("duplicate, misjoined, or malformed block effect")
        if effect["effect"] is not None and not np.isfinite(effect["effect"]):
            raise ValueError("nonfinite block effect")
        by_key[key] = effect
    rows = []
    for selected_row in selected:
        ci = selected_row["candidate_index"]
        for model in MODELS:
            for metric in METRICS:
                key = ci, model, metric
                if key in by_key:
                    rows.append(by_key[key])
                else:
                    reason = ("COHORT_INFERENCE_GATE" if gates[selected_row["cohort"]]["status"] != "READY"
                              else "MODEL_OR_EVENT_RESULT_MISSING")
                    rows.append(dict(candidate_index=ci, model=model, metric=metric,
                                     original_rho=None, independent_phase_rho=None,
                                     effect=None, reason=reason))
    return rows


def aggregate_endpoints(selected: list[dict], effect_rows: list[dict],
                        protocol: dict, gates: dict) -> list[dict]:
    """Eight fixed tests; separate actual nights and no positive inference below n=3."""
    filled = fill_effect_rows(selected, effect_rows, gates)
    by_key = {(r["candidate_index"], r["model"], r["metric"]): r for r in filled}
    minimum_blocks = protocol["aggregation"]["minimum_paired_metric_blocks_per_recording"]
    minimum_people = protocol["aggregation"]["minimum_complete_people_per_cohort"]
    family = protocol["multiplicity"]["family_size"]
    if family != 8 or len(protocol["cohorts"]) != 2:
        raise ValueError("fixed eight-endpoint family mismatch")
    output = []
    for cohort in protocol["cohorts"]:
        cid, nights = cohort["id"], tuple(cohort["sessions"])
        if len(nights) != 2:
            raise ValueError("exact paired nights required")
        for model in MODELS:
            for metric in METRICS:
                records, people = [], []
                for person in cohort["people"]:
                    night_rows = {}
                    for night in nights:
                        blocks = [r for r in selected if (r["cohort"], r["source_subject"], r["session"]) ==
                                  (cid, person, night)]
                        entries = [(r["candidate_index"], by_key[r["candidate_index"], model, metric]) for r in blocks]
                        good = [r["effect"] for _, r in entries if r["effect"] is not None]
                        status = "VALID" if len(good) >= minimum_blocks else "TOO_FEW_PAIRED_BLOCKS"
                        row = dict(person=person, night=night,
                                   recording_id=blocks[0]["recording_id"] if blocks else None,
                                   selected_blocks=len(blocks), paired_valid_blocks=len(good),
                                   excluded=[dict(candidate_index=ci, reason=r["reason"]) for ci, r in entries
                                             if r["effect"] is None], status=status,
                                   median_effect=float(np.median(good)) if status == "VALID" else None)
                        records.append(row)
                        night_rows[night] = row
                    complete = all(night_rows[n]["status"] == "VALID" for n in nights)
                    effect = (sum(night_rows[n]["median_effect"] for n in nights) / 2) if complete else None
                    people.append(dict(person=person, status="COMPLETE" if complete else "INCOMPLETE_NIGHTS",
                                       night_medians={n: night_rows[n]["median_effect"] for n in nights},
                                       reasons=[] if complete else [f"{n}:{night_rows[n]['status']}" for n in nights
                                                                    if night_rows[n]["status"] != "VALID"],
                                       effect=effect))
                valid = [p["effect"] for p in people if p["effect"] is not None]
                gate_ready = gates[cid]["status"] == "READY"
                if gate_ready and len(valid) >= max(3, minimum_people):
                    raw = old.exact_signflip(valid)
                    test = dict(status="COMPARED", reason=None, n=len(valid),
                                observed_mean=raw["observed_mean"], assignments=raw["assignments"],
                                extreme_count=raw["extreme_count"], p_two_sided=raw["p_two_sided"],
                                p_bonferroni_eight=min(1., family * raw["p_two_sided"]),
                                family_size=family, alpha=protocol["multiplicity"]["alpha"],
                                sign_symmetry_assumption="participant effects exchangeable under sign reversal",
                                two_sided_minimum_p=2 / (2 ** len(valid)))
                else:
                    reason = "COHORT_INFERENCE_GATE" if not gate_ready else "INSUFFICIENT_METRIC_PARTICIPANTS"
                    test = dict(status="NOT_ESTIMABLE", reason=reason, n=len(valid),
                                observed_mean=None, assignments=0, extreme_count=None,
                                p_two_sided=None, p_bonferroni_eight=None,
                                family_size=family, alpha=protocol["multiplicity"]["alpha"],
                                sign_symmetry_assumption="participant effects exchangeable under sign reversal",
                                two_sided_minimum_p=None)
                output.append(dict(cohort=cid, model=model, metric=metric,
                                   selected_blocks=sum(r["selected_blocks"] for r in records),
                                   paired_valid_blocks=sum(r["paired_valid_blocks"] for r in records),
                                   records=records, participants=people, test=test))
    return output


def write_json(path: Path, value: dict, *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with path.open("x") as handle:
            handle.write(canonical(value) + "\n")
    else:
        temporary = path.with_name(path.name + ".partial")
        temporary.write_text(canonical(value) + "\n")
        temporary.replace(path)


def save_npz(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"preserve incomplete archive: {temporary}")
    with temporary.open("xb") as handle:
        np.savez_compressed(handle, **arrays)
    temporary.rename(path)


def _artifact_bytes(root: Path) -> int:
    return sum(p.stat().st_size for folder in (root / "results/013", root / "data/derived/013")
               if folder.exists() for p in folder.rglob("*") if p.is_file())


def _resource_snapshot(root: Path, start_cpu: float, start_wall: float) -> dict:
    return dict(cpu_seconds=time.process_time() - start_cpu,
                wall_seconds=time.monotonic() - start_wall,
                process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                artifact_bytes=_artifact_bytes(root))


def _check_bounds(snapshot: dict, bounds: dict) -> None:
    if (snapshot["cpu_seconds"] > bounds["cpu_seconds"] or
            snapshot["process_peak_rss_bytes"] > bounds["rss_bytes"] or
            snapshot["artifact_bytes"] > bounds["artifact_bytes"]):
        raise RuntimeError("fixed CPU/RSS/artifact bound exceeded")


def require_first_block_review(root: Path, profile_path: Path, phase: str,
                               freeze: dict) -> dict:
    receipt_path = root / f"results/013/first-block-review-{phase}.json"
    review = read_json(receipt_path)
    if (review.get("schema") != "eegt-validation-first-block-review/v1" or
            review.get("status") != "ADMITTED" or review.get("phase") != phase or
            review.get("profile_sha256") != digest(profile_path) or
            review.get("run_manifest_sha256") != digest(root / "results/013/RUN-SOURCE-MANIFEST.json") or
            review.get("resource_bounds") != freeze["resource_bounds"] or
            not review.get("admitted_by")):
        raise ValueError(f"first-block review missing or stale: {phase}")
    return review


def _model_part(root: Path, name: str, ci: int) -> tuple[Path, Path]:
    directory = root / f"results/013/inference-{name}-parts"
    return directory / f"candidate-{ci:05d}.npz", directory / f"candidate-{ci:05d}.json"


def _read_model_part(root: Path, name: str, ci: int, block: np.ndarray,
                     freeze_sha: str, acceptance_sha: str,
                     implementation: str) -> tuple[np.ndarray, list[dict]] | None:
    array_path, receipt_path = _model_part(root, name, ci)
    if not array_path.exists() and not receipt_path.exists():
        return None
    if not array_path.exists() or not receipt_path.exists():
        raise ValueError(f"incomplete model part: {name}/{ci}")
    receipt = read_json(receipt_path)
    if (receipt.get("schema") != "eegt-validation-model-part/v1" or receipt.get("candidate_index") != ci or
            receipt.get("model") != name or receipt.get("run_manifest_sha256") != freeze_sha or
            receipt.get("input_acceptance_sha256") != acceptance_sha or
            receipt.get("encoder_implementation") != implementation or
            receipt.get("array_sha256") != digest(array_path)):
        raise ValueError(f"model part source/output mismatch: {name}/{ci}")
    with np.load(array_path, allow_pickle=False) as archive:
        output = archive["embeddings"]
    if output.shape != (5, 4, 30, 200) or output.dtype != np.float32 or not np.isfinite(output).all():
        raise ValueError(f"invalid model part array: {name}/{ci}")
    if len(receipt["measurements"]) != 5:
        raise ValueError(f"model part measurement count mismatch: {name}/{ci}")
    for j, variant in enumerate(PREPARED_VARIANTS):
        x = pretrained_study.waveform_variant(block, variant, 9009 + ci)
        old.checked_measurement(receipt["measurements"][j], ci, variant,
                                pretrained_study.array_hash(x), pretrained_study.array_hash(output[j]))
    return output, receipt["measurements"]


def run_inference(root: Path, name: str, *, resume: bool = False,
                  encoder_factory=None) -> dict:
    """One model at a time; first call stops after its first complete block."""
    root = Path(root)
    freeze = require_accepted_freeze(root, stage="encoder")
    acceptance = require_input_acceptance(root, freeze)
    inputs = load_inputs(root)
    if name not in MODELS:
        raise ValueError("unknown model")
    implementation = "PINNED_CHECKPOINT" if encoder_factory is None else "SYNTHETIC_FACTORY"
    torch_version = require_torch_runtime(freeze) if encoder_factory is None else None
    if resume and (root / f"results/013/inference-{name}.json").exists():
        archive, state = checked_model_archive(root, name, inputs, freeze, acceptance,
                                               allow_synthetic=encoder_factory is not None)
        if archive is not None and state["status"] == "COMPLETE":
            if read_json(root / f"results/013/inference-{name}.json")["encoder_implementation"] != implementation:
                raise ValueError("encoder implementation changed on resume")
            return read_json(root / f"results/013/inference-{name}.json")
    freeze_sha = digest(root / "results/013/RUN-SOURCE-MANIFEST.json")
    acceptance_sha = digest(root / "results/013/INPUT-ACCEPTANCE.json")
    candidates = [row for row in inputs.selected if inputs.gates[row["cohort"]]["status"] == "READY"]
    ids = [row["candidate_index"] for row in candidates]
    checkpoint = _inside(root, freeze["models"][name]["checkpoint"]["path"])
    if digest(checkpoint) != freeze["models"][name]["checkpoint"]["sha256"]:
        raise ValueError("checkpoint SHA256 changed")
    profile_path = root / f"results/013/first-block-inference-{name}.json"
    if bool(profile_path.exists()) != resume and candidates:
        raise ValueError("use first run, then explicit hash-checked --resume")
    if not resume and candidates and any(_model_part(root, name, row["candidate_index"])[0].exists()
                                         for row in candidates):
        raise ValueError("orphan model part before first-block profile")
    if resume and candidates:
        profile = read_json(profile_path)
        if (profile["run_manifest_sha256"] != freeze_sha or
                profile["input_acceptance_sha256"] != acceptance_sha):
            raise ValueError("first-block profile source changed")
        require_first_block_review(root, profile_path, f"inference-{name}", freeze)
    encoder = None
    if candidates:
        if encoder_factory is None:
            if name == "codebrain":
                from .pretrained import CodeBrainEncoder
                verify_loaded_sources(freeze)
                encoder = CodeBrainEncoder(checkpoint)
            else:
                from .cbramod import CBraModEncoder
                verify_loaded_sources(freeze)
                encoder = CBraModEncoder(checkpoint)
        else:
            encoder = encoder_factory(checkpoint)
    started_cpu, started_wall = time.process_time(), time.monotonic()
    by_id = {}
    rows_to_visit = candidates if resume else candidates[:1]
    for row in rows_to_visit:
        ci, block = row["candidate_index"], inputs.prepared["patches"][row["array_row"]]
        existing = _read_model_part(root, name, ci, block, freeze_sha, acceptance_sha, implementation)
        if existing is not None:
            by_id[ci] = existing
            continue
        embeddings, measurements = [], []
        for variant in PREPARED_VARIANTS:
            x = pretrained_study.waveform_variant(block, variant, 9009 + ci)
            start = time.monotonic()
            try:
                y = encoder.encode(x[None])
                if y.shape != (1, 4, 30, 200) or y.dtype != np.float32 or not np.isfinite(y).all():
                    raise ValueError("encoder output contract failed")
            except Exception as error:
                failure = dict(schema="eegt-validation-forward-failure/v1", observed_utc=utc_now(),
                               model=name, candidate_index=ci, variant=variant,
                               input_sha256=pretrained_study.array_hash(x),
                               error_type=type(error).__name__, reason=str(error),
                               run_manifest_sha256=freeze_sha, input_acceptance_sha256=acceptance_sha)
                write_json(root / f"results/013/failed-forward-{name}-{ci:05d}-{variant}.json", failure,
                           exclusive=True)
                raise
            embeddings.append(y[0])
            measurements.append(dict(candidate_index=ci, variant=variant,
                                     input_sha256=pretrained_study.array_hash(x),
                                     output_sha256=pretrained_study.array_hash(y[0]),
                                     maximum_absolute_prepared_uv=float(np.max(np.abs(x)) * 100),
                                     seconds=time.monotonic() - start))
        part = np.stack(embeddings).astype(np.float32, copy=False)
        array_path, receipt_path = _model_part(root, name, ci)
        save_npz(array_path, embeddings=part)
        write_json(receipt_path, dict(schema="eegt-validation-model-part/v1", model=name,
                                      encoder_implementation=implementation,
                                      candidate_index=ci, run_manifest_sha256=freeze_sha,
                                      input_acceptance_sha256=acceptance_sha,
                                      array_sha256=digest(array_path), measurements=measurements,
                                      runtime=runtime_identity(), resources=_resource_snapshot(root, started_cpu, started_wall)),
                   exclusive=True)
        by_id[ci] = part, measurements
        _check_bounds(_resource_snapshot(root, started_cpu, started_wall), freeze["resource_bounds"])
    if candidates and not resume:
        measured = _resource_snapshot(root, started_cpu, started_wall)
        projected = dict(cpu_seconds=measured["cpu_seconds"] * len(candidates),
                         artifact_bytes=measured["artifact_bytes"] * len(candidates),
                         rss_bytes=measured["process_peak_rss_bytes"])
        write_json(profile_path, dict(schema="eegt-validation-first-block/v1", phase=f"inference-{name}",
                                      candidate_index=ids[0], run_manifest_sha256=freeze_sha,
                                      input_acceptance_sha256=acceptance_sha,
                                      resources=measured, projected=projected,
                                      action="ROOT_REVIEW_BEFORE_RESUME"), exclusive=True)
        return dict(status="PAUSED_FOR_FIRST_BLOCK_PROFILE", model=name, completed_blocks=1,
                    total_blocks=len(candidates), resources=measured, projected=projected)
    outputs, measurements = [], []
    for row in candidates:
        ci, block = row["candidate_index"], inputs.prepared["patches"][row["array_row"]]
        part = _read_model_part(root, name, ci, block, freeze_sha, acceptance_sha, implementation)
        if part is None:
            raise ValueError(f"missing model part after run: {name}/{ci}")
        outputs.append(part[0])
        measurements.extend(part[1])
    emb = np.stack(outputs) if outputs else np.empty((0, 5, 4, 30, 200), dtype=np.float32)
    array_path = root / f"data/derived/013/{name}-embeddings.npz"
    if array_path.exists():
        raise FileExistsError("preserve existing complete inference archive")
    save_npz(array_path, embeddings=emb, candidate_indices=np.asarray(ids, dtype=np.int64),
             variants=np.asarray(PREPARED_VARIANTS))
    contract = phase_runtime("encoder")
    if torch_version is not None:
        contract["torch"] = torch_version
    result = dict(schema="eegt-validation-inference/v1", status="COMPLETE", model=name,
                  encoder_implementation=implementation,
                  run_manifest_sha256=freeze_sha, input_acceptance_sha256=acceptance_sha,
                  prepared_receipt_sha256=digest(root / "results/013/prepared.json"),
                  prepared_archive_sha256=inputs.receipt["array_sha256"],
                  protocol_sha256=digest(root / "protocol/experiment-013.json"),
                  source_manifest_sha256=digest(root / "protocol/corpus-manifest-013.json"),
                  checkpoint_sha256=freeze["models"][name]["checkpoint"]["sha256"],
                  array_path=str(array_path.relative_to(root)), array_sha256=digest(array_path),
                  shape=list(emb.shape), variants=list(PREPARED_VARIANTS),
                  block_variant_runs=len(measurements), measurements=measurements,
                  runtime=runtime_identity(), runtime_contract=contract,
                  resources=_resource_snapshot(root, started_cpu, started_wall),
                  observed_at_utc=utc_now())
    _check_bounds(result["resources"], freeze["resource_bounds"])
    write_json(root / f"results/013/inference-{name}.json", result, exclusive=True)
    return result


def partition_path(root: Path, ci: int, branch: str, variant: str) -> Path:
    if branch not in ("native", "prepared") or variant not in (NATIVE_VARIANTS if branch == "native" else PREPARED_VARIANTS):
        raise ValueError("undeclared event partition")
    return root / f"data/derived/013/events/candidate-{ci:05d}/{branch}-{variant}.jsonl.gz"


def read_partition(path: Path) -> tuple[dict, dict]:
    with gzip.open(path, "rt") as handle:
        first = json.loads(next(handle))
        if first.get("type") != "header":
            raise ValueError("event partition header missing")
        events = []
        for line in handle:
            row = json.loads(line)
            if row.get("type") != "event":
                raise ValueError("event partition row type mismatch")
            events.append(row["value"])
    header = first["value"]
    if len(events) != header["event_rows"] or hashlib.sha256(canonical(events).encode()).hexdigest() != header["events_sha256"]:
        raise ValueError("event partition count/content mismatch")
    return header, dict(header["result"], events=events)


def save_partition(path: Path, header: dict, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".partial")
    if temp.exists() or path.exists():
        raise FileExistsError(f"preserve existing event observation: {path}")
    with temp.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as handle:
            handle.write((canonical(dict(type="header", value=header)) + "\n").encode())
            for event in events:
                handle.write((canonical(dict(type="event", value=event)) + "\n").encode())
    temp.rename(path)


def observed_event(root: Path, ci: int, branch: str, variant: str,
                   samples: np.ndarray, valid: np.ndarray, rate: int,
                   config: dict, transform: dict, freeze_sha: str,
                   acceptance_sha: str, *, detector=wave.discover) -> tuple[Path, dict, dict]:
    path = partition_path(root, ci, branch, variant)
    array_sha = pretrained_study.array_hash(samples)
    mask_sha = pretrained_study.array_hash(valid)
    if path.exists():
        header, result = read_partition(path)
        if (header["candidate_index"] != ci or header["branch"] != branch or header["variant"] != variant or
                header["array_sha256"] != array_sha or header["mask_sha256"] != mask_sha or
                header["run_manifest_sha256"] != freeze_sha or
                header["input_acceptance_sha256"] != acceptance_sha):
            raise ValueError(f"existing event partition input mismatch: {ci}/{branch}/{variant}")
        return path, header, result
    result = detector(samples, rate, valid, [(0, samples.shape[1], 0.)],
                      include_cycles=(branch == "native" and variant == "primary"),
                      include_envelopes=(branch == "native" and variant == "primary"), **config)
    header = dict(schema="eegt-validation-event-partition/v1", candidate_index=ci,
                  branch=branch, variant=variant, sample_rate_hz=rate,
                  run_manifest_sha256=freeze_sha, input_acceptance_sha256=acceptance_sha,
                  array_sha256=array_sha, mask_sha256=mask_sha, transform=transform,
                  event_rows=len(result["events"]),
                  accepted_rows=sum(bool(r["accepted"]) for r in result["events"]),
                  rejected_rows=sum(not bool(r["accepted"]) for r in result["events"]),
                  events_sha256=hashlib.sha256(canonical(result["events"]).encode()).hexdigest(),
                  result={key: value for key, value in result.items() if key != "events"})
    save_partition(path, header, result["events"])
    return path, header, result


def open_index(root: Path, inputs: ValidatedInputs, freeze_sha: str,
               acceptance_sha: str) -> sqlite3.Connection:
    path = root / "results/013/analysis.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    first = not path.exists()
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=DELETE")
    if first:
        with db:
            db.executescript("""
            CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE candidates(candidate_index INTEGER PRIMARY KEY,array_row INTEGER,
                cohort TEXT,person TEXT,night TEXT,recording_id TEXT,status TEXT,reasons_json TEXT);
            CREATE TABLE partitions(candidate_index INTEGER,branch TEXT,variant TEXT,path TEXT,
                sha256 TEXT,bytes INTEGER,header_json TEXT,PRIMARY KEY(candidate_index,branch,variant));
            CREATE TABLE native_timeline(candidate_index INTEGER,variant TEXT,channel INTEGER,receipt_json TEXT,
                PRIMARY KEY(candidate_index,variant,channel));
            CREATE TABLE native_match(candidate_index INTEGER,variant TEXT,channel INTEGER,
                family TEXT,polarity TEXT,direction TEXT,tolerance_seconds REAL,receipt_json TEXT,
                PRIMARY KEY(candidate_index,variant,channel,family,polarity,direction,tolerance_seconds));
            CREATE TABLE prepared_metric(candidate_index INTEGER,variant TEXT,model TEXT,metric TEXT,receipt_json TEXT,
                PRIMARY KEY(candidate_index,variant,model,metric));
            CREATE TABLE block_effect(candidate_index INTEGER,model TEXT,metric TEXT,effect REAL,reason TEXT,
                receipt_json TEXT,PRIMARY KEY(candidate_index,model,metric));
            CREATE TABLE morphology_block(candidate_index INTEGER,channel INTEGER,family TEXT,band TEXT,
                definition TEXT,receipt_json TEXT,PRIMARY KEY(candidate_index,channel,family,band,definition));
            CREATE TABLE completed_blocks(candidate_index INTEGER PRIMARY KEY,completed_utc TEXT);
            """)
            db.executemany("INSERT INTO metadata VALUES(?,?)",
                           (("run_manifest_sha256", freeze_sha), ("input_acceptance_sha256", acceptance_sha)))
            for row in inputs.receipt["records"]:
                db.execute("INSERT INTO candidates VALUES(?,?,?,?,?,?,?,?)",
                           (row["candidate_index"], row["array_row"], row["cohort"],
                            row["source_subject"], row["session"], row["recording_id"],
                            row["status"], canonical(row["reasons"])))
    metadata = dict(db.execute("SELECT key,value FROM metadata"))
    expected_candidates = [(row["candidate_index"], row["array_row"], row["cohort"],
                            row["source_subject"], row["session"], row["recording_id"],
                            row["status"], canonical(row["reasons"]))
                           for row in inputs.receipt["records"]]
    actual_candidates = db.execute("SELECT candidate_index,array_row,cohort,person,night,"
                                   "recording_id,status,reasons_json FROM candidates "
                                   "ORDER BY candidate_index").fetchall()
    if (metadata != {"run_manifest_sha256": freeze_sha, "input_acceptance_sha256": acceptance_sha} or
            actual_candidates != expected_candidates):
        db.close()
        raise ValueError("existing event index identity/census mismatch")
    return db


def process_event_block(root: Path, row: dict, inputs: ValidatedInputs,
                        model_archives: dict[str, dict | None], db: sqlite3.Connection,
                        freeze_sha: str, acceptance_sha: str,
                        *, detector=wave.discover) -> dict:
    ci = row["candidate_index"]
    if db.execute("SELECT 1 FROM completed_blocks WHERE candidate_index=?", (ci,)).fetchone():
        raise ValueError("block already indexed")
    i = row["array_row"]
    native, valid, prepared = (inputs.native["samples_uv"][i],
                               inputs.native["valid"][i], inputs.prepared["patches"][i])
    partitions, native_results, prepared_results = [], {}, {}
    timelines, matches = [], []
    try:
        for variant in NATIVE_VARIANTS:
            x, mask, config, transform = old.native_variant(native, valid, variant, ci)
            item = observed_event(root, ci, "native", variant, x, mask, 250, config, transform,
                                  freeze_sha, acceptance_sha, detector=detector)
            partitions.append(item[:2])
            native_results[variant] = item[2]
            if variant != "primary":
                t, m = old.native_matches(native_results["primary"], item[2], variant)
                timelines.extend(dict(variant=variant, **entry) for entry in t)
                matches.extend(dict(variant=variant, **entry) for entry in m)
        for variant in PREPARED_VARIANTS:
            x32 = pretrained_study.waveform_variant(prepared, variant, 9009 + ci)
            x = x32.reshape(4, 6000).astype(np.float64) * 100
            mask = np.ones(x.shape, dtype=bool)
            transform = dict(name=variant, source_float32_sha256=pretrained_study.array_hash(x32),
                             source_units="microvolt/100", analyzed_units="microvolt",
                             source_rate_hz=200, seed=9009 + ci if variant == "independent_phase" else None)
            item = observed_event(root, ci, "prepared", variant, x, mask, 200, {}, transform,
                                  freeze_sha, acceptance_sha, detector=detector)
            partitions.append(item[:2])
            prepared_results[variant] = item[2]
        embeddings = {}
        for model, archive in model_archives.items():
            if archive is None:
                continue
            positions = np.flatnonzero(archive["candidate_indices"] == ci)
            if len(positions) > 1:
                raise ValueError(f"duplicate model candidate join: {model}/{ci}")
            if len(positions) == 1:
                embeddings[model] = archive["embeddings"][int(positions[0])]
        _, comparisons, effects = compare_prepared_results(prepared_results, embeddings)
        effects = [dict(candidate_index=ci, **entry) for entry in effects]
        effects = fill_effect_rows([row], effects, inputs.gates)
        morphology = old.morphology_summary(old.morphology_groups(native_results["primary"]))
    except Exception as error:
        write_json(root / f"results/013/failed-event-{ci:05d}.json",
                   dict(schema="eegt-validation-event-failure/v1", candidate_index=ci,
                        error_type=type(error).__name__, reason=str(error), observed_utc=utc_now(),
                        run_manifest_sha256=freeze_sha, input_acceptance_sha256=acceptance_sha),
                   exclusive=True)
        raise
    with db:
        for path, header in partitions:
            db.execute("INSERT INTO partitions VALUES(?,?,?,?,?,?,?)",
                       (ci, header["branch"], header["variant"], str(path.relative_to(root)),
                        digest(path), path.stat().st_size, canonical(header)))
        for entry in timelines:
            db.execute("INSERT INTO native_timeline VALUES(?,?,?,?)",
                       (ci, entry["variant"], entry["channel"], canonical(entry)))
        for entry in matches:
            db.execute("INSERT INTO native_match VALUES(?,?,?,?,?,?,?,?)",
                       (ci, entry["variant"], entry["channel"], entry["family"], entry["polarity"],
                        entry["direction"], entry["tolerance_seconds"], canonical(entry)))
        for entry in comparisons:
            db.execute("INSERT INTO prepared_metric VALUES(?,?,?,?,?)",
                       (ci, entry["variant"], entry["model"], entry["metric"], canonical(entry)))
        for entry in effects:
            db.execute("INSERT INTO block_effect VALUES(?,?,?,?,?,?)",
                       (ci, entry["model"], entry["metric"], entry["effect"], entry["reason"], canonical(entry)))
        for entry in morphology:
            db.execute("INSERT INTO morphology_block VALUES(?,?,?,?,?,?)",
                       (ci, entry["channel"], entry["family"], canonical(entry["band_hz"]),
                        entry["definition"], canonical(entry)))
        db.execute("INSERT INTO completed_blocks VALUES(?,?)", (ci, utc_now()))
    return dict(candidate_index=ci, partitions=len(partitions), native_matches=len(matches),
                prepared_metrics=len(comparisons), effects=effects,
                compressed_partition_bytes=sum(path.stat().st_size for path, _ in partitions))


def verify_indexed_partitions(root: Path, db: sqlite3.Connection) -> int:
    completed = {row[0] for row in db.execute("SELECT candidate_index FROM completed_blocks")}
    eligible = {row[0] for row in db.execute("SELECT candidate_index FROM candidates WHERE status='ELIGIBLE'")}
    if not completed.issubset(eligible):
        raise ValueError("completed block is not a selected candidate")
    expected = {(ci, branch, variant) for ci in completed
                for branch, variants in (("native", NATIVE_VARIANTS), ("prepared", PREPARED_VARIANTS))
                for variant in variants}
    actual = list(db.execute("SELECT candidate_index,branch,variant FROM partitions"))
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("indexed partition completed-block membership mismatch")
    checked = 0
    for ci, branch, variant, relative, sha, size, saved_header in db.execute(
            "SELECT candidate_index,branch,variant,path,sha256,bytes,header_json FROM partitions ORDER BY candidate_index,branch,variant"):
        path = _inside(root, relative)
        if not path.is_file() or path.stat().st_size != size or digest(path) != sha:
            raise ValueError(f"indexed partition bytes changed: {relative}")
        header, _ = read_partition(path)
        if (canonical(header) != saved_header or header["candidate_index"] != ci or
                header["branch"] != branch or header["variant"] != variant):
            raise ValueError(f"indexed partition header changed: {relative}")
        checked += 1
    if checked != len(expected):
        raise ValueError("indexed partition denominator mismatch")
    return checked


def evaluate_index(root: Path, inputs: ValidatedInputs, db: sqlite3.Connection,
                   freeze_sha: str, acceptance_sha: str) -> dict:
    checked = verify_indexed_partitions(root, db)
    saved = [json.loads(row[0]) for row in db.execute(
        "SELECT receipt_json FROM block_effect ORDER BY candidate_index,model,metric")]
    completed_ids = {row[0] for row in db.execute("SELECT candidate_index FROM completed_blocks")}
    expected_effects = {(ci, model, metric) for ci in completed_ids
                        for model in MODELS for metric in ("geometry", "change")}
    actual_effects = [(row["candidate_index"], row["model"], row["metric"]) for row in saved]
    if len(actual_effects) != len(expected_effects) or set(actual_effects) != expected_effects:
        raise ValueError("completed block effect census mismatch")
    complete = db.execute("SELECT count(*) FROM completed_blocks").fetchone()[0]
    missing_ready_model = sum(row["reason"] == "MODEL_OR_EVENT_RESULT_MISSING" for row in saved)
    endpoints = aggregate_endpoints(inputs.selected, saved, inputs.protocol, inputs.gates)
    return dict(schema="eegt-validation-scientific-summary/v1",
                status=("NO_ELIGIBLE_BLOCKS" if not inputs.selected else
                        "COMPLETE_NUMERICAL_RECORD" if complete == len(inputs.selected) and not missing_ready_model
                        else "PARTIAL_NUMERICAL_RECORD"),
                run_manifest_sha256=freeze_sha, input_acceptance_sha256=acceptance_sha,
                protocol_sha256=digest(root / "protocol/experiment-013.json"),
                source_manifest_sha256=digest(root / "protocol/corpus-manifest-013.json"),
                candidate_blocks=len(inputs.receipt["records"]), selected_blocks=len(inputs.selected),
                completed_event_blocks=complete, indexed_partitions=checked,
                native_variants=list(NATIVE_VARIANTS), prepared_variants=list(PREPARED_VARIANTS),
                cohort_inference_gates=inputs.gates, primary_endpoints=endpoints,
                support_failure_rows=db.execute("SELECT count(*) FROM block_effect WHERE reason IS NOT NULL").fetchone()[0],
                missing_ready_model_effect_rows=missing_ready_model,
                native_match_rows=db.execute("SELECT count(*) FROM native_match").fetchone()[0],
                morphology_rows=db.execute("SELECT count(*) FROM morphology_block").fetchone()[0],
                interpretation_limits="numeric events only; no semantic, clinical, or population-transfer inference")


def run_events(root: Path, *, resume: bool = False) -> dict:
    """Process all selected native blocks; only ready cohorts can have model effects."""
    root = Path(root)
    freeze = require_accepted_freeze(root, stage="events")
    require_input_acceptance(root, freeze)
    inputs = load_inputs(root)
    freeze_sha = digest(root / "results/013/RUN-SOURCE-MANIFEST.json")
    acceptance_sha = digest(root / "results/013/INPUT-ACCEPTANCE.json")
    model_data = {name: checked_model_archive(root, name, inputs, freeze, {})[0] for name in MODELS}
    profile_path = root / "results/013/first-block-events.json"
    if inputs.selected and bool(profile_path.exists()) != resume:
        raise ValueError("use first event block, then explicit hash-checked --resume")
    if resume and inputs.selected:
        profile = read_json(profile_path)
        if (profile["run_manifest_sha256"] != freeze_sha or
                profile["input_acceptance_sha256"] != acceptance_sha):
            raise ValueError("event first-block profile source changed")
        require_first_block_review(root, profile_path, "events", freeze)
    db = open_index(root, inputs, freeze_sha, acceptance_sha)
    try:
        verify_indexed_partitions(root, db)
        if not resume and db.execute("SELECT count(*) FROM completed_blocks").fetchone()[0]:
            raise ValueError("orphan event block before first-block profile")
        started_cpu, started_wall = time.process_time(), time.monotonic()
        todo = [row for row in inputs.selected if not db.execute(
            "SELECT 1 FROM completed_blocks WHERE candidate_index=?", (row["candidate_index"],)).fetchone()]
        if not resume:
            todo = todo[:1]
        for row in todo:
            process_event_block(root, row, inputs, model_data, db, freeze_sha, acceptance_sha)
            measured = _resource_snapshot(root, started_cpu, started_wall)
            _check_bounds(measured, freeze["resource_bounds"])
        if inputs.selected and not resume:
            measured = _resource_snapshot(root, started_cpu, started_wall)
            projected = dict(cpu_seconds=measured["cpu_seconds"] * len(inputs.selected),
                             artifact_bytes=measured["artifact_bytes"] * len(inputs.selected),
                             rss_bytes=measured["process_peak_rss_bytes"])
            write_json(profile_path, dict(schema="eegt-validation-first-block/v1", phase="events",
                                          candidate_index=inputs.selected[0]["candidate_index"],
                                          run_manifest_sha256=freeze_sha,
                                          input_acceptance_sha256=acceptance_sha,
                                          resources=measured, projected=projected,
                                          action="ROOT_REVIEW_BEFORE_RESUME"), exclusive=True)
            return dict(status="PAUSED_FOR_FIRST_BLOCK_PROFILE", completed_blocks=1,
                        total_blocks=len(inputs.selected), resources=measured, projected=projected)
        summary = evaluate_index(root, inputs, db, freeze_sha, acceptance_sha)
        write_json(root / "results/013/summary.json", summary)
        _check_bounds(_resource_snapshot(root, started_cpu, started_wall), freeze["resource_bounds"])
        return summary
    finally:
        db.close()


def replay_events(root: Path) -> dict:
    """Read recorded event/model results; this is not detector regeneration."""
    root = Path(root)
    freeze = require_accepted_freeze(root, stage="events")
    require_input_acceptance(root, freeze)
    inputs = load_inputs(root)
    freeze_sha = digest(root / "results/013/RUN-SOURCE-MANIFEST.json")
    acceptance_sha = digest(root / "results/013/INPUT-ACCEPTANCE.json")
    model_data = {name: checked_model_archive(root, name, inputs, freeze, {})[0] for name in MODELS}
    db = open_index(root, inputs, freeze_sha, acceptance_sha)
    try:
        partitions = verify_indexed_partitions(root, db)
        for (ci,) in db.execute("SELECT candidate_index FROM completed_blocks ORDER BY candidate_index"):
            prepared = {variant: read_partition(partition_path(root, ci, "prepared", variant))[1]
                        for variant in PREPARED_VARIANTS}
            embeddings = {}
            for name, archive in model_data.items():
                if archive is None:
                    continue
                pos = np.flatnonzero(archive["candidate_indices"] == ci)
                if len(pos) == 1:
                    embeddings[name] = archive["embeddings"][int(pos[0])]
            _, metrics, effects = compare_prepared_results(prepared, embeddings)
            saved_metrics = [json.loads(row[0]) for row in db.execute(
                "SELECT receipt_json FROM prepared_metric WHERE candidate_index=?", (ci,))]
            if sorted(map(canonical, metrics)) != sorted(map(canonical, saved_metrics)):
                raise ValueError(f"recorded prepared metrics changed: {ci}")
            selected = next(row for row in inputs.selected if row["candidate_index"] == ci)
            effects = fill_effect_rows([selected], [dict(candidate_index=ci, **r) for r in effects], inputs.gates)
            saved_effects = [json.loads(row[0]) for row in db.execute(
                "SELECT receipt_json FROM block_effect WHERE candidate_index=?", (ci,))]
            if sorted(map(canonical, effects)) != sorted(map(canonical, saved_effects)):
                raise ValueError(f"recorded block effects changed: {ci}")
            primary = read_partition(partition_path(root, ci, "native", "primary"))[1]
            for variant in NATIVE_VARIANTS[1:]:
                result = read_partition(partition_path(root, ci, "native", variant))[1]
                timeline, matches = old.native_matches(primary, result, variant)
                timeline = [dict(variant=variant, **r) for r in timeline]
                matches = [dict(variant=variant, **r) for r in matches]
                saved_t = [json.loads(row[0]) for row in db.execute(
                    "SELECT receipt_json FROM native_timeline WHERE candidate_index=? AND variant=?", (ci, variant))]
                saved_m = [json.loads(row[0]) for row in db.execute(
                    "SELECT receipt_json FROM native_match WHERE candidate_index=? AND variant=?", (ci, variant))]
                if (sorted(map(canonical, timeline)) != sorted(map(canonical, saved_t)) or
                        sorted(map(canonical, matches)) != sorted(map(canonical, saved_m))):
                    raise ValueError(f"recorded native comparison changed: {ci}/{variant}")
        summary = evaluate_index(root, inputs, db, freeze_sha, acceptance_sha)
        if (root / "results/013/summary.json").exists() and canonical(summary) != canonical(
                read_json(root / "results/013/summary.json")):
            raise ValueError("recorded summary changed")
        return dict(schema="eegt-validation-replay/v1", status="REPLAYED_RECORDED_EVENTS",
                    completed_blocks=summary["completed_event_blocks"], partitions=partitions,
                    full_scientific_summary=summary["status"] == "COMPLETE_NUMERICAL_RECORD",
                    detector_regenerated=False, run_manifest_sha256=freeze_sha,
                    input_acceptance_sha256=acceptance_sha)
    finally:
        db.close()


def _read_012_partition(path: Path) -> tuple[dict, dict]:
    """Released 012 partition format predates the 013 per-partition events hash."""
    with gzip.open(path, "rt") as handle:
        header_row = json.loads(next(handle))
        if header_row.get("type") != "header":
            raise ValueError("012 partition header missing")
        rows = []
        for line in handle:
            item = json.loads(line)
            if item.get("type") != "event":
                raise ValueError("012 partition event row mismatch")
            rows.append(item["value"])
    header = header_row["value"]
    if len(rows) != header["event_rows"]:
        raise ValueError("012 partition event denominator mismatch")
    return header, dict(header["result"], events=rows)


def verify_exposed_012(packet: Path, supplement: Path, sqlite_path: Path) -> dict:
    """Exact archived hashes and one full per-block 012 numeric parity proof.

    The supplement supplies row zero's 23 event partitions and the complete
    accepted SQL ledger. No forward or detector is invoked here.
    """
    packet, supplement, sqlite_path = Path(packet), Path(supplement), Path(sqlite_path)
    manifest = read_json(packet / "INPUT-MANIFEST.json")
    old_paths = ("repo/results/010/prepared.json", "repo/results/010/inference.json",
                 "repo/results/011/inference.json", "repo/data/derived/010/prepared.npz",
                 "repo/data/derived/010/embeddings.npz", "repo/data/derived/011/embeddings.npz",
                 "repo/data/derived/012/native-selected.npz", "repo/results/012/summary.json")
    verify_hash_map(packet, {name: manifest["files"][name] for name in old_paths}, label="exposed 012 packet")
    extra = read_json(supplement / "MANIFEST.json")
    verify_hash_map(supplement, extra["files"], label="exposed 012 supplement")
    if digest(sqlite_path) != extra["sqlite_uncompressed_sha256"]:
        raise ValueError("exposed 012 SQLite SHA256 mismatch")
    root = packet / "repo"
    prepared_receipt = read_json(root / "results/010/prepared.json")
    selected = [row for row in prepared_receipt["records"] if row["status"] == "ELIGIBLE"]
    curator = read_json(supplement / "native-selected-curator.json")
    with np.load(root / "data/derived/010/prepared.npz", allow_pickle=False) as a:
        prepared = {k: a[k] for k in a.files}
    with np.load(root / "data/derived/012/native-selected.npz", allow_pickle=False) as a:
        native = {k: a[k] for k in a.files}
    if (len(selected) != 122 or len(curator["records"]) != 122 or
            prepared["patches"].shape != (122, 4, 30, 200) or
            native["samples_uv"].shape != (122, 4, 7500) or
            not np.array_equal(prepared["candidate_indices"], [r["candidate_index"] for r in selected])):
        raise ValueError("exposed 012 selected numeric census mismatch")
    encoders, receipts = {}, {}
    for name, experiment in (("codebrain", "010"), ("cbramod", "011")):
        with np.load(root / f"data/derived/{experiment}/embeddings.npz", allow_pickle=False) as a:
            encoders[name] = {k: a[k] for k in a.files}
        receipts[name] = read_json(root / f"results/{experiment}/inference.json")
        if (encoders[name]["embeddings"].shape != (122, 5, 4, 30, 200) or
                not np.array_equal(encoders[name]["candidate_indices"], prepared["candidate_indices"]) or
                tuple(encoders[name]["variants"]) != PREPARED_VARIANTS or
                len(receipts[name]["measurements"]) != 610):
            raise ValueError(f"exposed 012 model archive mismatch: {name}")
    for i, row in enumerate(selected):
        cur = curator["records"][i]
        if (cur["array_row"] != i or cur["candidate_index"] != row["candidate_index"] or
                cur["native_array_sha256"] != old.array_digest(native["samples_uv"][i]) or
                cur["valid_mask_sha256"] != old.array_digest(native["valid"][i]) or
                cur["prepared_array_sha256"] != pretrained_study.array_hash(prepared["patches"][i])):
            raise ValueError(f"exposed 012 curator/numeric join mismatch: {i}")
        for j, variant in enumerate(PREPARED_VARIANTS):
            x = pretrained_study.waveform_variant(prepared["patches"][i], variant,
                                                  9009 + row["candidate_index"])
            for name in MODELS:
                old.checked_measurement(receipts[name]["measurements"][5*i+j],
                                        row["candidate_index"], variant,
                                        pretrained_study.array_hash(x),
                                        pretrained_study.array_hash(encoders[name]["embeddings"][i, j]))
    db = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    try:
        row0 = selected[0]
        if db.execute("SELECT candidate_index FROM completed_blocks WHERE array_row=0").fetchone()[0] != row0["candidate_index"]:
            raise ValueError("exposed 012 SQL first-block identity mismatch")
        prepared_results, native_results = {}, {}
        for branch, variants, target in (("native", NATIVE_VARIANTS, native_results),
                                         ("prepared", PREPARED_VARIANTS, prepared_results)):
            for variant in variants:
                relative = f"row-000/{branch}-{variant}.jsonl.gz"
                path = supplement / relative
                header, result = _read_012_partition(path)
                indexed = db.execute("SELECT path,sha256,bytes,header_json FROM partitions WHERE array_row=0 AND branch=? AND variant=?",
                                     (branch, variant)).fetchone()
                if (indexed is None or not indexed[0].endswith(relative) or indexed[1] != digest(path) or
                        indexed[2] != path.stat().st_size or indexed[3] != canonical(header)):
                    raise ValueError(f"exposed 012 partition/index mismatch: {relative}")
                target[variant] = result
        block_embeddings = {name: encoders[name]["embeddings"][0] for name in MODELS}
        _, old_supports, old_metrics, old_effects = old.prepared_comparisons(prepared_results, block_embeddings)
        supports, metrics, effects = compare_prepared_results(prepared_results, block_embeddings)
        if (canonical(supports) != canonical(old_supports) or
                sorted(map(canonical, metrics)) != sorted(map(canonical, old_metrics)) or
                sorted(map(canonical, effects)) != sorted(map(canonical, old_effects))):
            raise ValueError("013 comparison interface differs from released 012 numerics")
        indexed_metrics = [json.loads(r[0]) for r in db.execute(
            "SELECT receipt_json FROM prepared_metric WHERE array_row=0")]
        indexed_effects = [json.loads(r[0]) for r in db.execute(
            "SELECT receipt_json FROM block_effect WHERE array_row=0")]
        if (sorted(map(canonical, metrics)) != sorted(map(canonical, indexed_metrics)) or
                sorted(map(canonical, effects)) != sorted(map(canonical, indexed_effects))):
            raise ValueError("exposed 012 per-block prepared metric/effect parity mismatch")
        match_count = timeline_count = 0
        for variant in NATIVE_VARIANTS[1:]:
            timeline, matches = old.native_matches(native_results["primary"], native_results[variant], variant)
            timeline = [dict(variant=variant, **r) for r in timeline]
            matches = [dict(variant=variant, **r) for r in matches]
            saved_t = [json.loads(r[0]) for r in db.execute(
                "SELECT receipt_json FROM native_timeline WHERE array_row=0 AND variant=?", (variant,))]
            saved_m = [json.loads(r[0]) for r in db.execute(
                "SELECT receipt_json FROM native_match WHERE array_row=0 AND variant=?", (variant,))]
            if (sorted(map(canonical, timeline)) != sorted(map(canonical, saved_t)) or
                    sorted(map(canonical, matches)) != sorted(map(canonical, saved_m))):
                raise ValueError(f"exposed 012 native per-block parity mismatch: {variant}")
            timeline_count += len(timeline)
            match_count += len(matches)
    finally:
        db.close()
    return dict(schema="eegt-validation-exposed-parity/v1", status="EXACT_ROW_ZERO_PARITY",
                original_packet_manifest_sha256=digest(packet / "INPUT-MANIFEST.json"),
                supplement_manifest_sha256=digest(supplement / "MANIFEST.json"),
                sqlite_sha256=digest(sqlite_path), selected_numeric_rows_verified=122,
                prepared_variant_inputs_verified=610, model_outputs_verified=1220,
                full_event_blocks_verified=1, event_partitions_verified=23,
                prepared_metrics_verified=len(metrics), block_effects_verified=len(effects),
                native_timelines_verified=timeline_count, native_matches_verified=match_count,
                detector_regenerated=False, model_forward_called=False)


def load_engineering_input(root: Path, freeze_sha: str) -> tuple[dict, dict, dict]:
    """Isolated EESM19 12-contact input; never map it to four encoder contacts."""
    receipt_path = root / "results/013/engineering-prepared.json"
    acceptance_path = root / "results/013/engineering-input-acceptance.json"
    acceptance = read_json(acceptance_path)
    if (acceptance.get("schema") != "eegt-validation-engineering-input-acceptance/v1" or
            acceptance.get("status") != "ACCEPTED" or
            acceptance.get("run_manifest_sha256") != freeze_sha):
        raise ValueError("engineering input acceptance missing or stale")
    verify_hash_map(root, acceptance["inputs"], label="engineering input")
    if acceptance["inputs"].get("results/013/engineering-prepared.json") != digest(receipt_path):
        raise ValueError("engineering receipt not accepted")
    receipt = read_json(receipt_path)
    archive_path = _inside(root, receipt["array_path"])
    if (acceptance["inputs"].get(receipt["array_path"]) != digest(archive_path) or
            receipt.get("array_sha256") != digest(archive_path)):
        raise ValueError("engineering archive not accepted")
    with np.load(archive_path, allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    rows = receipt["records"]
    sessions = [row["session"] for row in rows]
    channels = receipt.get("channel_names", rows[0].get("channel_names") if rows else None)
    if (set(arrays) != {"samples_uv", "valid"} or
            arrays["samples_uv"].shape != (2, 12, 15000) or arrays["samples_uv"].dtype != np.float64 or
            arrays["valid"].shape != (2, 12, 15000) or arrays["valid"].dtype != np.bool_ or
            not np.isfinite(arrays["samples_uv"][arrays["valid"]]).all() or
            receipt["sample_rate_hz"] != 500 or sessions != ["005", "006"] or
            not isinstance(channels, list) or len(channels) != 12 or
            len(set(channels)) != 12 or "EOGr" in channels or
            any(row.get("source_subject") != "001" or row.get("channel_names", channels) != channels for row in rows)):
        raise ValueError("EESM19 shape, nights, channel or support mismatch")
    if len(rows) != 2:
        raise ValueError("EESM19 receipt row count mismatch")
    for i, night in enumerate(sessions):
        row = rows[i]
        if (row["session"] != night or row["native_array_sha256"] != pretrained_study.array_hash(arrays["samples_uv"][i]) or
                row["valid_mask_sha256"] != pretrained_study.array_hash(arrays["valid"][i])):
            raise ValueError(f"EESM19 source/mask row mismatch: {night}")
    receipt["sessions"] = sessions
    receipt["channels"] = channels
    return receipt, arrays, acceptance


def run_engineering(root: Path, *, resume: bool = False) -> dict:
    """Two prespecified native-only nights; separate from the eight primary tests."""
    root = Path(root)
    freeze = require_accepted_freeze(root, stage="events")
    freeze_sha = digest(root / "results/013/RUN-SOURCE-MANIFEST.json")
    receipt, arrays, acceptance = load_engineering_input(root, freeze_sha)
    acceptance_sha = digest(root / "results/013/engineering-input-acceptance.json")
    out = root / "results/013/engineering"
    profile_path = out / "first-block.json"
    if bool(profile_path.exists()) != resume:
        raise ValueError("use first engineering block, then explicit --resume")
    if resume:
        require_first_block_review(root, profile_path, "engineering", freeze)
    started_cpu, started_wall = time.process_time(), time.monotonic()
    indices = range(2) if resume else range(1)
    for i in indices:
        night = receipt["sessions"][i]
        path = root / f"data/derived/013/engineering/night-{night}-primary.jsonl.gz"
        x, mask = arrays["samples_uv"][i], arrays["valid"][i]
        array_sha, mask_sha = pretrained_study.array_hash(x), pretrained_study.array_hash(mask)
        if path.exists():
            header, _ = read_partition(path)
            if (header["array_sha256"] != array_sha or header["mask_sha256"] != mask_sha or
                    header["run_manifest_sha256"] != freeze_sha or
                    header["input_acceptance_sha256"] != acceptance_sha):
                raise ValueError(f"engineering restart/source mismatch: {night}")
            continue
        result = wave.discover(x, 500, mask, [(0, 15000, 0.)],
                               include_cycles=True, include_envelopes=True)
        header = dict(schema="eegt-validation-engineering-partition/v1", session=night,
                      source_subject="001", channels=receipt["channels"],
                      array_sha256=array_sha, mask_sha256=mask_sha,
                      run_manifest_sha256=freeze_sha,
                      input_acceptance_sha256=acceptance_sha,
                      event_rows=len(result["events"]),
                      accepted_rows=sum(bool(r["accepted"]) for r in result["events"]),
                      rejected_rows=sum(not bool(r["accepted"]) for r in result["events"]),
                      events_sha256=hashlib.sha256(canonical(result["events"]).encode()).hexdigest(),
                      result={key: value for key, value in result.items() if key != "events"})
        save_partition(path, header, result["events"])
        _check_bounds(_resource_snapshot(root, started_cpu, started_wall), freeze["resource_bounds"])
    if not resume:
        measured = _resource_snapshot(root, started_cpu, started_wall)
        write_json(profile_path, dict(schema="eegt-validation-first-block/v1", phase="engineering",
                                      session="005", resources=measured,
                                      projected=dict(cpu_seconds=2 * measured["cpu_seconds"],
                                                     artifact_bytes=2 * measured["artifact_bytes"],
                                                     rss_bytes=measured["process_peak_rss_bytes"]),
                                      run_manifest_sha256=freeze_sha,
                                      input_acceptance_sha256=acceptance_sha,
                                      action="ROOT_REVIEW_BEFORE_RESUME"), exclusive=True)
        return dict(status="PAUSED_FOR_FIRST_BLOCK_PROFILE", complete_nights=1, total_nights=2)
    partitions = []
    for night in receipt["sessions"]:
        path = root / f"data/derived/013/engineering/night-{night}-primary.jsonl.gz"
        header, _ = read_partition(path)
        partitions.append(dict(session=night, path=str(path.relative_to(root)),
                               sha256=digest(path), bytes=path.stat().st_size,
                               event_rows=header["event_rows"],
                               accepted_rows=header["accepted_rows"],
                               rejected_rows=header["rejected_rows"],
                               support_runs=header["result"].get("runs")))
    summary = dict(schema="eegt-validation-engineering-summary/v1", status="COMPLETE_TECHNICAL_RECORD",
                   source="EESM19", source_subject="001", sessions=["005", "006"],
                   channels=receipt["channels"], sample_rate_hz=500,
                   native_partitions=partitions, model_status={name: "NOT_EVALUATED_FOR_12_CONTACTS" for name in MODELS},
                   primary_family_membership=False, p_values=None,
                   run_manifest_sha256=freeze_sha,
                   input_acceptance_sha256=acceptance_sha,
                   interpretation="technical support and event counts only; no population or device-transfer claim")
    write_json(out / "summary.json", summary)
    return summary
