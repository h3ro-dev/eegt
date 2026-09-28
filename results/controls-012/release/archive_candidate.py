"""Create and stream-verify the exact-manifest archive candidate.

This tool intentionally does not walk the packet tree. Replay outputs in that
tree are not archive members. It does not publish or alter packet inputs.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKET = HERE / "stage" / "packet"
MANIFEST = PACKET / "work/next-study/release/FILE-MANIFEST.json"
ARCHIVE = HERE / "eegt-v0.11.0-controls.tar.gz"
RECEIPT = HERE / "run" / "ARCHIVE-CANDIDATE.json"
MANIFEST_SHA = "43c60d842d3a8d3a9105749f965622a7106bc269d45065a06066bd272232f6e3"
REPLAY_SHA = "6bb36490c96b5e53ae84112b8a0780047dd2fc6e7a19d89cf14b24b215c82cd9"
METADATA_SHA = "e0a2b6b58a9cd152460c50fbdf981aeeaadb9383ddc8a09ce89451cbda7028d0"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    if ARCHIVE.exists() or RECEIPT.exists():
        raise FileExistsError("preserve previous archive candidate and receipt")
    if digest(MANIFEST) != MANIFEST_SHA:
        raise ValueError("packet manifest seal changed")
    manifest = json.loads(MANIFEST.read_text())
    rows = manifest["files"]
    if len(rows) != 97 or [row["path"] for row in rows] != sorted(row["path"] for row in rows):
        raise ValueError("unexpected fixed allowlist")
    replay_path = PACKET / "work/next-study/release/replay/EMPIRICAL-REPLAY.json"
    metadata_path = PACKET / "work/next-study/release/replay/METADATA-REPLAY.json"
    if digest(replay_path) != REPLAY_SHA or digest(metadata_path) != METADATA_SHA:
        raise ValueError("clean replay seals changed")
    replay = json.loads(replay_path.read_text())
    metadata = json.loads(metadata_path.read_text())
    if (replay.get("status") != "COMPLETE_MATCH" or len(replay["rows"]) != 12 or
            replay["not_run"] or not replay["descriptive_summary_equal"] or
            not all(row["full_scientific_row_equal"] for row in replay["rows"]) or
            metadata.get("status") != "COMPLETE_MATCH" or
            not metadata["byte_equal_to_accepted"]):
        raise ValueError("clean complete replay required before candidate archive")
    names = []
    expected = {}
    for row in rows + [{"path": "work/next-study/release/FILE-MANIFEST.json",
                        "bytes": MANIFEST.stat().st_size, "sha256": MANIFEST_SHA}]:
        relative = Path(row["path"])
        if relative.is_absolute() or ".." in relative.parts or "replay" in relative.parts:
            raise ValueError(f"unsafe archive entry: {relative}")
        path = PACKET / relative
        if path.is_symlink() or not path.is_file() or path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise ValueError(f"packet input differs from manifest: {relative}")
        name = "packet/" + relative.as_posix()
        if name in expected:
            raise ValueError(f"duplicate archive member: {name}")
        names.append((name, path, row["bytes"]))
        expected[name] = row["sha256"]

    with ARCHIVE.open("xb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0, compresslevel=6) as zipped:
            with tarfile.open(fileobj=zipped, mode="w|", format=tarfile.PAX_FORMAT) as archive:
                for name, path, size in names:
                    info = tarfile.TarInfo(name)
                    info.size = size
                    info.mode = 0o444
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    with path.open("rb") as handle:
                        archive.addfile(info, handle)

    verified = []
    with tarfile.open(ARCHIVE, mode="r|gz") as archive:
        for member in archive:
            if not member.isfile() or member.name not in expected or member.name in verified:
                raise ValueError(f"unexpected archive member: {member.name}")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"unreadable archive member: {member.name}")
            value = hashlib.sha256()
            while chunk := source.read(1024 * 1024):
                value.update(chunk)
            if value.hexdigest() != expected[member.name]:
                raise ValueError(f"archive member hash mismatch: {member.name}")
            verified.append(member.name)
    if len(verified) != 98 or set(verified) != set(expected):
        raise ValueError("archive member count or exact allowlist mismatch")
    output = {"schema": "eegt-controls-archive-candidate/v1",
              "status": "EXACT_INPUT_PACKET_CANDIDATE_PENDING_INDEPENDENT_REVIEW",
              "archive_name": ARCHIVE.name, "archive_sha256": digest(ARCHIVE),
              "archive_bytes": ARCHIVE.stat().st_size,
              "manifest_sha256": MANIFEST_SHA, "member_count": len(verified),
              "regular_file_members_only": True, "top_level_prefix": "packet/",
              "all_member_hashes_match_manifest": True,
              "replay_outputs_excluded": True,
              "separate_empirical_replay_sha256": REPLAY_SHA,
              "separate_metadata_replay_receipt_sha256": METADATA_SHA,
              "published": False}
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    with RECEIPT.open("x") as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
