"""Small synthetic probes for the Experiment 012 code review; no run data."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "repo/scripts"))
spec = importlib.util.spec_from_file_location("package_events", HERE / "repo/scripts/package_events.py")
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)
spec = importlib.util.spec_from_file_location("report_events", HERE / "repo/scripts/report_events.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n")


with tempfile.TemporaryDirectory(dir=HERE / "scratch") as temp:
    base = Path(temp)
    root, packet = base / "root", base / "packet"
    sr = packet / "repo/results/012"
    rr = root / "results/012"
    sr.mkdir(parents=True)
    rr.mkdir(parents=True)
    put(sr / "summary.json", {"status": "COMPLETE_NUMERICAL_RECORD"})
    put(rr / "summary.json", {"status": "COMPLETE_NUMERICAL_RECORD"})
    for path in (sr / "analysis.sqlite", rr / "analysis.sqlite"):
        db = sqlite3.connect(path)
        db.execute("CREATE TABLE probe (id INTEGER)")
        db.commit()
        db.close()
    put(sr / "RUN-SOURCE-MANIFEST.json", {"schema": "synthetic-probe"})
    counts = dict(indexed_blocks=122, partitions=2806, native_matches=99552,
                  prepared_metrics=2440, candidate_rows=5760)
    put(packet / "out/REPORT.json", {"status": "COMPLETE", "counts": counts,
                                    "artifact_files": {}, "frozen_manifest_sha256": "0" * 64})
    put(rr / "implementation-review/ACCEPTANCE.json",
        {"status": "ACCEPTED", "summary_sha256": package.digest(sr / "summary.json"),
         "index_sha256": package.digest(sr / "analysis.sqlite")})
    put(rr / "extracted-reproduction.json",
        {"status": "REPRODUCED", "full_scientific_summary": True,
         "blocks": 122, "partitions": 2806,
         "run_manifest_sha256": package.digest(sr / "RUN-SOURCE-MANIFEST.json"),
         "index_sha256": "0" * 64})
    science = package.verify_science(root, packet, require_replay=True)
    assert science["counts"] == counts
    assert science["artifact_files"] == {}
    files = {"repo/note.md": {"source_path": "repo/note.md", "bytes": 1, "sha256": "a" * 64}}
    package.verify_review(files, {"status": "ACCEPTED", "files": files})
    endpoint = {"model": "x", "metric": "geometry", "paired_valid_blocks": 18,
                "participants": [{"person": str(i), "status": "COMPLETE"} for i in range(6)],
                "records": [{"person": str(i), "paired_valid_blocks": 3} for i in range(6)],
                "test": {"status": "COMPARED", "p_bonferroni_four": 0.125}}
    six, = report.primary_rows({"primary_endpoints": [endpoint]})
    assert six["people"] == 6 and six["primary_blocks"] == 18
    extracted = base / "extracted"
    extracted.mkdir()
    (extracted / "listed.bin").write_bytes(b"ok")
    (extracted / "unlisted.py").write_text("print('extra file')\n")
    listed = {"listed.bin": {"bytes": 2, "sha256": hashlib.sha256(b"ok").hexdigest()}}
    put(extracted / "FILE-MANIFEST.json", {"files": listed})
    # Same listed-file verification as REPRODUCE-012.md lines 21-35.
    for name, row in json.loads((extracted / "FILE-MANIFEST.json").read_text())["files"].items():
        path = extracted / name
        assert path.is_file() and path.stat().st_size == row["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    print(json.dumps({"probe": "synthetic_only", "science_gate": "ACCEPTED_EMPTY_INDEX_AND_ARTIFACT_LIST",
                      "replay_index_hash_checked": False,
                      "review_gate": "ACCEPTED_STATUS_AND_FILES_ONLY",
                      "docs_check_rejects_unlisted_file": False,
                      "report_supports_six_complete_people": True}, sort_keys=True))
