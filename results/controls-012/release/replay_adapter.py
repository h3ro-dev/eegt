"""Offline relocation adapter for unchanged accepted 012 timing-null code.

This adapter replaces absolute-path verification with hash-checked paths under
the packet root. It does not change the frozen runner, matcher, null helper,
events, settings, or scientific calculation.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import platform
import resource
import signal
import sqlite3
import sys
import time
from pathlib import Path

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
              "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    if os.environ.get(_name) != "1":
        raise SystemExit(f"{_name}=1 required before any numerical import")

HERE = Path(__file__).resolve().parent
PACKET = HERE.parents[2]
REPLAY_DIR = HERE / "replay"
PROTOCOL_REL = Path("work/next-study/empirical/PROTOCOL.json")
CAPACITY_REL = Path("work/next-study/replication/CAPACITY.json")
RUNNER_REL = Path("work/next-study/empirical/empirical_null.py")
AUDIT_REL = Path("work/next-study/replication/audit_capacity.py")
PROTOCOL_SHA = "6631cec40013e0f9b84e6c538049e6492fa2d20563211689077d015fa02cdabe"
ACCEPTANCE_SHA = "c296b9af4612f73361fd48f2beebff5da33fef70c201354ad7b4f624ad2c6479"
OUTPUT_REVIEW_SHA = "c5278bec3b7365d313fbb15f9ed3c74b8242b66f661d903f64fa2f58cded44cd"
CAPACITY_SHA = "919a798d3915741575d61a788fb57a27433967683b7fd467460306208f663cc7"
REPLICATION_REVIEW_SHA = "95d94e68b650c1533c56edc1359f73e753366cd5c3f6854e96dd81f4bc57688f"
ADMISSION_SHA = "50f09eab8abe090827cebef324fbdc3c0ea3ab130c35382c8f931fb89518dbd1"
FIRST_SHA = "7b57252f38d13ceaf08efe0c143d1e42d79672dd5e49331a7e80e3f5d8f08ecd"
REMAINING_SHA = "9bf843ba2e41793c83826bd4fe699f2616169fb4c8d93f43e7546ff046720a39"
RUNNER_SHA = "0a812d0f3d4111a46ddc0a25d290a37965fd9a26f5a131c29d8cf0771fea2534"
AUDIT_SHA = "c6b78fcf97308bfc11f908b689d4df55cda17daba2c395787adbad010bebeae8"
BUILDER_SHA = "409a475a6a964edae12288d24ad8850a9ae66f3c1c3af0249e05dc2852981b32"
FIXED_ARRAY_ROWS = (0, 11, 23, 35, 47, 48, 59, 71, 81, 92, 104, 112)


class ReplayStop(Exception):
    """A caught resource limit or failed exact comparison."""


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def canonical_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def read_sealed(relative: Path, sha: str) -> dict:
    path = PACKET / relative
    if not path.is_file() or path.is_symlink() or digest(path) != sha:
        raise ValueError(f"frozen file missing or changed: {relative}")
    return json.loads(path.read_text())


def _load_module(name: str, relative: Path, sha: str):
    path = PACKET / relative
    if digest(path) != sha:
        raise ValueError(f"unchanged module hash mismatch: {relative}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_packet() -> dict:
    # Import the copied builder only after verifying its exact file against the
    # sealed manifest. Its checks cover every packet file, not a directory glob.
    manifest_path = HERE / "FILE-MANIFEST.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("packet file manifest missing or linked")
    manifest = json.loads(manifest_path.read_text())
    own = next((item for item in manifest["files"] if item["path"] ==
                "work/next-study/release/build_packet.py"), None)
    if own is None or own["sha256"] != BUILDER_SHA or digest(HERE / "build_packet.py") != BUILDER_SHA:
        raise ValueError("packet builder differs from manifest")
    builder = _load_module("packet_builder", Path("work/next-study/release/build_packet.py"), BUILDER_SHA)
    checked = builder.load_and_verify_manifest()
    protocol = read_sealed(PROTOCOL_REL, PROTOCOL_SHA)
    acceptance = read_sealed(
        Path("work/next-study/empirical-review/PROTOCOL-ACCEPTANCE.json"), ACCEPTANCE_SHA)
    output_review = read_sealed(
        Path("work/next-study/empirical-review/OUTPUT-REVIEW.json"), OUTPUT_REVIEW_SHA)
    capacity = read_sealed(CAPACITY_REL, CAPACITY_SHA)
    replication_review = read_sealed(
        Path("work/next-study/empirical-review/REPLICATION-REVIEW.json"), REPLICATION_REVIEW_SHA)
    admission = read_sealed(
        Path("work/next-study/intake-2026-09-28/RESOURCE-ADMISSION.json"), ADMISSION_SHA)
    first = read_sealed(Path("work/next-study/empirical/FIRST-UNIT.json"), FIRST_SHA)
    remaining = read_sealed(Path("work/next-study/empirical/REMAINING.json"), REMAINING_SHA)
    if (acceptance.get("status") != "ACCEPTED" or
            acceptance.get("protocol_sha256") != PROTOCOL_SHA or
            output_review.get("status") != "ACCEPTED" or
            output_review.get("protocol_sha256") != PROTOCOL_SHA or
            replication_review.get("status") != "ACCEPTED" or
            replication_review.get("capacity_sha256") != CAPACITY_SHA or
            admission.get("status") != "ACCEPTED" or
            admission.get("protocol_sha256") != PROTOCOL_SHA or
            admission.get("first_unit_sha256") != FIRST_SHA):
        raise ValueError("accepted review or admission identity mismatch")
    if (first.get("status") != "COMPLETE" or remaining.get("status") != "COMPLETE" or
            len(first["rows"]) != 1 or len(remaining["rows"]) != 11 or
            remaining["not_run"]):
        raise ValueError("original stage completion mismatch")

    # The only relocation: original absolute paths are mapped to the identical
    # project-relative paths. Protocol bytes remain untouched in the packet.
    source_root = Path(protocol["source_artifact_root"])
    if source_root.parts[-3:] != ("work", "transition-extracted-final", "repo"):
        raise ValueError("unexpected frozen source root")
    original_project = source_root.parents[2]
    if PACKET.resolve() == original_project.resolve():
        raise ValueError("replay requires a distinct offline packet, not the source project")
    relocated = {}
    for label, source in protocol["source_sha256"].items():
        relative = Path(source["absolute_path"]).relative_to(original_project)
        mapped = (PACKET / relative).resolve()
        if (not mapped.is_relative_to(PACKET.resolve()) or
                mapped.stat().st_size != source["bytes"] or
                digest(mapped) != source["sha256"]):
            raise ValueError(f"relocated source mismatch: {label}")
        relocated[label] = relative.as_posix()
    if len(relocated) != 12:
        raise ValueError("not twelve relocated protocol sources")
    for row in protocol["selection"]:
        for part in row["partitions"]:
            relative = Path("work/transition-extracted-final/repo") / part["path"]
            path = PACKET / relative
            if path.stat().st_size != part["bytes"] or digest(path) != part["sha256"]:
                raise ValueError(f"selected partition mismatch: {relative}")
    if len(capacity["inputs_sha256"]) != 26:
        raise ValueError("not twenty-six capacity inputs")
    for name, sha in capacity["inputs_sha256"].items():
        if digest(PACKET / name) != sha:
            raise ValueError(f"metadata input mismatch: {name}")
    for short, sha in output_review["reviewed_sha256"].items():
        if digest(PACKET / "work/next-study" / short) != sha:
            raise ValueError(f"output-review subject mismatch: {short}")
    expected_rows = [row["array_row"] for row in protocol["selection"]]
    if ([row["array_row"] for row in first["rows"] + remaining["rows"]] != expected_rows or
            expected_rows != list(FIXED_ARRAY_ROWS)):
        raise ValueError("fixed row order mismatch")
    return {"status": "FROZEN_PACKET_VERIFIED", "manifest_sha256": digest(manifest_path),
            "file_count": len(checked["files"]) + 1, "protocol": protocol,
            "original_rows": first["rows"] + remaining["rows"],
            "original_summary": remaining["descriptive_denominators"],
            "relocated_source_paths": relocated}


def empirical_replay() -> dict:
    output = REPLAY_DIR / "EMPIRICAL-REPLAY.json"
    if output.exists():
        raise FileExistsError(f"preserve existing replay: {output}")
    start_cpu, start_wall = time.process_time(), time.perf_counter()
    hard_limit = 7200
    current_soft, current_hard = resource.getrlimit(resource.RLIMIT_CPU)
    new_hard = hard_limit if current_hard == resource.RLIM_INFINITY else min(current_hard, hard_limit)
    new_soft = min(new_hard - 10, current_soft if current_soft != resource.RLIM_INFINITY else hard_limit)
    if new_soft <= 0:
        raise ReplayStop("CPU_LIMIT_TOO_SMALL_FOR_RECEIPT")
    resource.setrlimit(resource.RLIMIT_CPU, (new_soft, new_hard))

    def cpu_signal(_signum, _frame):
        raise ReplayStop("CPU_SOFT_LIMIT")

    signal.signal(signal.SIGXCPU, cpu_signal)
    report = {"schema": "eegt-offline-conditional-timing-replay/v1", "status": "IN_PROGRESS",
              "protocol_sha256": PROTOCOL_SHA, "output_review_sha256": OUTPUT_REVIEW_SHA,
              "original_first_sha256": FIRST_SHA, "original_remaining_sha256": REMAINING_SHA,
              "relocation_is_engineering_only": True, "rows": [],
              "not_run": list(FIXED_ARRAY_ROWS)}
    db = None
    verified = None
    try:
        verified = verify_packet()
        protocol = verified["protocol"]
        runner = _load_module("frozen_empirical_null", RUNNER_REL, RUNNER_SHA)
        if runner.PROJECT.resolve() != PACKET.resolve():
            raise ValueError("unchanged runner import did not resolve packet layout")
        if runner.runtime_versions() != protocol["runtime_exact"]:
            raise ValueError("exact Python/NumPy/SciPy runtime mismatch")
        if (protocol["resource_bounds"]["cpu_seconds"] != 7200 or
                protocol["resource_bounds"]["rss_bytes"] != 2147483648 or
                protocol["resource_bounds"]["blas_threads"] != 1):
            raise ValueError("resource contract mismatch")
        report["runtime"] = runner.runtime_versions()
        report["manifest_sha256"] = verified["manifest_sha256"]
        report["relocated_source_paths"] = verified["relocated_source_paths"]
        db_path = PACKET / "work/transition-extracted-final/repo/results/012/analysis.sqlite"
        db = sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True)

        def check_resource():
            runner.resource_guard(start_cpu, hard_limit, 2147483648)

        for row_spec, original in zip(protocol["selection"], verified["original_rows"], strict=True):
            check_resource()
            observed = runner.evaluate_row(db, runner.REPO, row_spec, protocol,
                                           resource_check=check_resource)
            check_resource()
            receipt = {"array_row": row_spec["array_row"], "original_sha256":
                       canonical_digest(original), "replayed_sha256": canonical_digest(observed),
                       "full_scientific_row_equal": observed == original, "replayed_row": observed}
            report["rows"].append(receipt)
            if observed != original:
                raise ReplayStop(f"ROW_SCIENTIFIC_OUTPUT_MISMATCH:{row_spec['array_row']}")
        summary = runner.descriptive_summary(
            [row["replayed_row"] for row in report["rows"]],
            planned_rows=len(protocol["selection"]))
        check_resource()
        report["replayed_descriptive_summary"] = summary
        report["original_descriptive_summary"] = verified["original_summary"]
        report["descriptive_summary_equal"] = summary == verified["original_summary"]
        if not report["descriptive_summary_equal"]:
            raise ReplayStop("DESCRIPTIVE_SUMMARY_MISMATCH")
        report["status"] = "COMPLETE_MATCH"
    except Exception as error:
        report["status"] = "STOPPED_OR_FAILED"
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        signal.signal(signal.SIGXCPU, signal.SIG_IGN)
        if db is not None:
            db.close()
        report["resources"] = {"cpu_seconds": time.process_time() - start_cpu,
                               "wall_seconds": time.perf_counter() - start_wall,
                               "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                               if sys.platform == "darwin" else
                               resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                               "cpu_soft_limit_seconds": new_soft,
                               "cpu_hard_limit_seconds": new_hard}
        completed = {item["array_row"] for item in report["rows"]}
        report["not_run"] = [row for row in FIXED_ARRAY_ROWS if row not in completed]
        REPLAY_DIR.mkdir(parents=True, exist_ok=True)
        with output.open("x") as handle:
            json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
    return {"status": report["status"], "output": str(output), "output_sha256": digest(output),
            "completed_rows": len(report["rows"]), "not_run": report["not_run"],
            "resources": report["resources"]}


def metadata_replay() -> dict:
    verified = verify_packet()
    if platform.python_version() != verified["protocol"]["runtime_exact"]["python"]:
        raise ValueError("exact Python runtime mismatch")
    audit = _load_module("frozen_capacity_audit", AUDIT_REL, AUDIT_SHA)
    if audit.ROOT.resolve() != PACKET.resolve():
        raise ValueError("unchanged metadata audit did not resolve packet layout")
    output_dir = REPLAY_DIR / "metadata"
    output = output_dir / "CAPACITY.json"
    receipt = REPLAY_DIR / "METADATA-REPLAY.json"
    if output.exists() or receipt.exists():
        raise FileExistsError("preserve existing metadata replay")
    output_dir.mkdir(parents=True, exist_ok=False)
    audit.HERE = output_dir  # Redirect only the audit output; __file__/ROOT/inputs remain frozen.
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        audit.main()
    matched = digest(output) == CAPACITY_SHA
    result = {"schema": "eegt-offline-metadata-capacity-replay/v1",
              "status": "COMPLETE_MATCH" if matched else "OUTPUT_MISMATCH",
              "accepted_capacity_sha256": CAPACITY_SHA,
              "replayed_capacity_sha256": digest(output), "byte_equal_to_accepted": matched,
              "audit_script_sha256": AUDIT_SHA, "inputs_verified": 26,
              "captured_audit_stdout": captured.getvalue(),
              "no_eeg_payload_opened": True}
    with receipt.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return {"status": result["status"], "receipt": str(receipt),
            "receipt_sha256": digest(receipt)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("verify", "metadata", "empirical"))
    args = parser.parse_args()
    if args.action == "verify":
        result = verify_packet()
        result = {key: result[key] for key in ("status", "manifest_sha256", "file_count",
                                               "relocated_source_paths")}
    elif args.action == "metadata":
        result = metadata_replay()
    else:
        result = empirical_replay()
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] not in ("FROZEN_PACKET_VERIFIED", "COMPLETE_MATCH"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
