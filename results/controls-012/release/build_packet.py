"""Make a project-relative, explicit-allowlist offline packet from frozen inputs.

No tree walk or archive creation occurs here. ``plan`` seals the exact paths;
``build`` verifies that seal and copies only those paths into a new directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
MANIFEST = HERE / "FILE-MANIFEST.json"
STAGE = HERE / "stage" / "packet"

PROTOCOL_REL = "work/next-study/empirical/PROTOCOL.json"
CAPACITY_REL = "work/next-study/replication/CAPACITY.json"
PROTOCOL_SHA = "6631cec40013e0f9b84e6c538049e6492fa2d20563211689077d015fa02cdabe"
CAPACITY_SHA = "919a798d3915741575d61a788fb57a27433967683b7fd467460306208f663cc7"
OUTPUT_REVIEW_SHA = "c5278bec3b7365d313fbb15f9ed3c74b8242b66f661d903f64fa2f58cded44cd"

# These paths are hand-approved packet additions. Protocol-sourced and
# capacity-sourced paths are additionally constrained by fixed seals below.
EXTRA_PATHS = (
    "work/transition-extracted-final/repo/eegt/__init__.py",
    "work/transition-extracted-final/repo/results/012/protocol-review/ACCEPTANCE.json",
    "work/transition-extracted-final/repo/results/012/release-review.json",
    PROTOCOL_REL,
    "work/next-study/empirical/SYNTHETIC-TESTS.json",
    "work/next-study/empirical/FIRST-UNIT-COMMAND.json",
    "work/next-study/empirical/FIRST-UNIT-EXECUTION.json",
    "work/next-study/empirical/FIRST-UNIT.json",
    "work/next-study/empirical/FIRST-UNIT.stdout",
    "work/next-study/empirical/FIRST-UNIT.stderr",
    "work/next-study/empirical/REMAINING-COMMAND.json",
    "work/next-study/empirical/REMAINING-EXECUTION.json",
    "work/next-study/empirical/REMAINING.json",
    "work/next-study/empirical/REMAINING.stdout",
    "work/next-study/empirical/REMAINING.stderr",
    "work/next-study/empirical/REPORT.md",
    "work/next-study/empirical-review/PROTOCOL-ACCEPTANCE.json",
    "work/next-study/empirical-review/PROTOCOL-REVIEW.md",
    "work/next-study/empirical-review/OUTPUT-REVIEW.json",
    "work/next-study/empirical-review/OUTPUT-REVIEW.md",
    "work/next-study/empirical-review/REPLICATION-REVIEW.json",
    "work/next-study/empirical-review/REPLICATION-REVIEW.md",
    "work/next-study/intake-2026-09-28/RESOURCE-ADMISSION.json",
    "work/next-study/intake-2026-09-28/FIGURE-MANIFEST.json",
    "work/next-study/intake-2026-09-28/plot_controls.py",
    "work/next-study/intake-2026-09-28/density-control.png",
    "work/next-study/intake-2026-09-28/density-control.svg",
    "work/next-study/replication/audit_capacity.py",
    CAPACITY_REL,
    "work/next-study/replication/DESIGN.md",
    "work/next-study/release/build_packet.py",
    "work/next-study/release/replay_adapter.py",
    "work/next-study/release/test_release.py",
    "work/next-study/release/README.md",
    "work/next-study/release/requirements-replay.txt",
)

FORBIDDEN_PARTS = {"private", "vendor", "mailbox", "raw", "weights", "credentials", "secrets"}
SOURCE_KEYS = {
    "accepted_012_methods", "accepted_curator", "accepted_event_study",
    "accepted_index", "accepted_matcher", "accepted_summary",
    "draft_protocol_text", "extracted_report", "prior_control_receipt",
    "prior_timing_helper", "proposed_runner", "synthetic_tests",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def safe_relative(name: str) -> Path:
    parsed = PurePosixPath(name)
    if (not name or parsed.is_absolute() or parsed.as_posix() != name or
            any(part in ("", ".", "..") for part in parsed.parts) or
            any(part.lower() in FORBIDDEN_PARTS for part in parsed.parts)):
        raise ValueError(f"unsafe packet path: {name}")
    return Path(*parsed.parts)


def source_file(relative: str) -> Path:
    path = PROJECT / safe_relative(relative)
    cursor = path
    while cursor != PROJECT:
        if cursor.is_symlink():
            raise ValueError(f"symlink in source path: {relative}")
        cursor = cursor.parent
    if not path.is_file() or not path.resolve().is_relative_to(PROJECT.resolve()):
        raise FileNotFoundError(relative)
    return path


def _pinned_json(relative: str, expected_hash: str) -> dict:
    path = source_file(relative)
    if digest(path) != expected_hash:
        raise ValueError(f"frozen receipt hash changed: {relative}")
    return json.loads(path.read_text())


def expected_sources() -> dict[str, tuple[str, str, int]]:
    protocol = _pinned_json(PROTOCOL_REL, PROTOCOL_SHA)
    capacity = _pinned_json(CAPACITY_REL, CAPACITY_SHA)
    _pinned_json("work/next-study/empirical-review/OUTPUT-REVIEW.json", OUTPUT_REVIEW_SHA)
    source_root = Path(protocol["source_artifact_root"])
    if source_root.parts[-3:] != ("work", "transition-extracted-final", "repo"):
        raise ValueError("unexpected original source-root shape")
    original_project = source_root.parents[2]
    sources: dict[str, tuple[str, str, int]] = {}

    if set(protocol["source_sha256"]) != SOURCE_KEYS:
        raise ValueError("not exactly twelve frozen protocol source keys")
    for entry in protocol["source_sha256"].values():
        relative = Path(entry["absolute_path"]).relative_to(original_project).as_posix()
        sources[relative] = ("protocol_source", entry["sha256"], entry["bytes"])
    if len(sources) != 12:
        raise ValueError("duplicate protocol source path")

    if len(protocol["selection"]) != 12:
        raise ValueError("not twelve frozen selected blocks")
    event_paths = set()
    for row in protocol["selection"]:
        if {part["variant"] for part in row["partitions"]} != {"primary", "independent_phase"}:
            raise ValueError("unexpected partition variants")
        for part in row["partitions"]:
            relative = "work/transition-extracted-final/repo/" + part["path"]
            if relative in event_paths:
                raise ValueError("duplicate event partition")
            event_paths.add(relative)
            sources[relative] = ("selected_event_partition", part["sha256"], part["bytes"])
    if len(event_paths) != 24:
        raise ValueError("not exactly twenty-four event partitions")

    metadata_paths = {
        "outputs/research/eesm19-metadata-audit/out/REPORT.json",
        "outputs/research/eesm19-metadata-audit/sources/graphql-inventory.json",
        "outputs/research/eesm19-metadata-audit/sources/metadata-sources.json",
        "outputs/research/eesm19-metadata-audit/sources/pinned/acq-earEEG_channels.tsv",
        "outputs/research/eesm19-metadata-audit/sources/pinned/acq-PSG_channels.tsv",
        "work/database-release/final/catalog.sqlite",
    } | {
        f"outputs/research/eesm19-metadata-audit/sources/pinned/sub-{person:03d}/sub-{person:03d}_sessions.tsv"
        for person in range(1, 21)
    }
    if set(capacity["inputs_sha256"]) != metadata_paths or len(metadata_paths) != 26:
        raise ValueError("not exactly twenty-six pinned metadata inputs")
    for relative, sha in capacity["inputs_sha256"].items():
        sources[relative] = ("replication_metadata_input", sha, source_file(relative).stat().st_size)

    for relative in EXTRA_PATHS:
        path = source_file(relative)
        if relative in sources:
            raise ValueError(f"duplicate explicit addition: {relative}")
        sources[relative] = ("explicit_support", digest(path), path.stat().st_size)
    if len(sources) != 62 + len(EXTRA_PATHS):
        raise ValueError("unexpected source count")
    return sources


def planned_manifest() -> dict:
    sources = expected_sources()
    records = []
    for relative, (kind, sha, size) in sorted(sources.items()):
        path = source_file(relative)
        if path.stat().st_size != size or digest(path) != sha:
            raise ValueError(f"source size/hash mismatch: {relative}")
        records.append({"path": relative, "kind": kind, "bytes": size, "sha256": sha})
    kinds = Counter(item["kind"] for item in records)
    return {"schema": "eegt-offline-packet-file-manifest/v1",
            "status": "ALLOWLIST_ONLY_PENDING_INDEPENDENT_RELEASE_REVIEW",
            "protocol_sha256": PROTOCOL_SHA, "capacity_sha256": CAPACITY_SHA,
            "output_review_sha256": OUTPUT_REVIEW_SHA,
            "files": records, "counts_by_kind": dict(sorted(kinds.items())),
            "payload_bytes": sum(item["bytes"] for item in records)}


def load_and_verify_manifest() -> dict:
    if not MANIFEST.is_file():
        raise FileNotFoundError("run plan first")
    frozen = json.loads(MANIFEST.read_text())
    if frozen != planned_manifest():
        raise ValueError("manifest or source drift; do not build")
    return frozen


def build() -> dict:
    frozen = load_and_verify_manifest()
    if STAGE.exists():
        raise FileExistsError(f"preserve prior packet stage: {STAGE}")
    STAGE.mkdir(parents=True, exist_ok=False)
    for item in frozen["files"]:
        source = source_file(item["path"])
        destination = STAGE / safe_relative(item["path"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as reader, destination.open("xb") as writer:
            shutil.copyfileobj(reader, writer, 1024 * 1024)
        destination.chmod(0o444)
        if destination.stat().st_size != item["bytes"] or digest(destination) != item["sha256"]:
            raise ValueError(f"copied file mismatch: {item['path']}")
    destination = STAGE / "work/next-study/release/FILE-MANIFEST.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("rb") as reader, destination.open("xb") as writer:
        shutil.copyfileobj(reader, writer)
    destination.chmod(0o444)
    if digest(destination) != digest(MANIFEST):
        raise ValueError("copied manifest mismatch")
    return {"status": "COPIED_AND_VERIFIED_NOT_RELEASED", "packet_root": str(STAGE),
            "file_count": len(frozen["files"]) + 1,
            "payload_bytes": frozen["payload_bytes"] + MANIFEST.stat().st_size,
            "manifest_sha256": digest(MANIFEST)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("plan", "verify", "build"))
    args = parser.parse_args()
    if args.action == "plan":
        planned = planned_manifest()
        if MANIFEST.exists():
            if json.loads(MANIFEST.read_text()) != planned:
                raise FileExistsError("existing manifest differs; preserve it for review")
        else:
            with MANIFEST.open("x") as handle:
                json.dump(planned, handle, indent=2, sort_keys=True)
                handle.write("\n")
        output = {"status": "PLAN_SEALED_NOT_COPIED", "file_count": len(planned["files"]),
                  "payload_bytes": planned["payload_bytes"], "manifest_sha256": digest(MANIFEST)}
    elif args.action == "verify":
        planned = load_and_verify_manifest()
        output = {"status": "SOURCES_VERIFIED_NOT_COPIED", "file_count": len(planned["files"]),
                  "payload_bytes": planned["payload_bytes"], "manifest_sha256": digest(MANIFEST)}
    else:
        output = build()
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
