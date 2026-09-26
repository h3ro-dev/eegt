"""Exact v4 and final regression overlay audit against preserved v3."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
v3 = root / "scratch/v3-repo"
v4 = root / "scratch/v4-repo"
packet = root / "update-root-v4"
regression = root / "update-root-v4-regression"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(folder):
    return {str(p.relative_to(folder)): sha(p) for p in folder.rglob("*")
            if p.is_file() and not ({"__pycache__", ".pytest_cache"} & set(p.parts))}


declared = json.loads((packet / "INPUT-MANIFEST.json").read_text())
reg_declared = json.loads((regression / "INPUT-MANIFEST.json").read_text())
packet_actual = files(packet)
reg_actual = files(regression)
before, after = files(v3), files(v4)
changes = sorted(n for n in before.keys() | after.keys() if before.get(n) != after.get(n))
result = {
    "schema": "eegt-v4-review-packet-audit/v1",
    "v4_packet_manifest_sha256": sha(packet / "INPUT-MANIFEST.json"),
    "v4_packet_inventory": packet_actual,
    "v4_packet_declared_hashes_match": all(packet_actual.get(n) == h for n, h in declared.items()),
    "v4_packet_declared_names_match": set(packet_actual) == set(declared) | {"INPUT-MANIFEST.json"},
    "regression_manifest_sha256": sha(regression / "INPUT-MANIFEST.json"),
    "regression_inventory": reg_actual,
    "regression_declared_hashes_match": all(reg_actual.get(n) == h for n, h in reg_declared.items()),
    "regression_declared_names_match": set(reg_actual) == set(reg_declared) | {"INPUT-MANIFEST.json"},
    "v3_v4_changed_paths": changes,
    "exact_two_file_delta": changes == ["eegt/validation_intake.py", "tests/test_validation_intake.py"],
    "v4_source_matches_packet": after["eegt/validation_intake.py"] == packet_actual["eegt/validation_intake.py"],
    "v4_final_test_matches_regression": after["tests/test_validation_intake.py"] == reg_actual["test_validation_intake.py"],
    "v4_regression_changes_only_test": packet_actual["eegt/validation_intake.py"] == after["eegt/validation_intake.py"],
    "v3_review_json_sha256": sha(root / "out/V3-REVIEW.json"),
    "v2_review_json_sha256": sha(root / "out/REVIEW.json"),
    "unchanged_protocol_hashes": {n: after[n] for n in after if n.startswith("protocol/")
                                  and n in ("protocol/corpus-manifest-013.json",
                                            "protocol/engineering-input-013.json",
                                            "protocol/experiment-013.json")},
    "unchanged_decoder_sha256": after["eegt/repeated.py"],
    "unchanged_resource_gate_code_sha256": after["eegt/validation_study.py"],
}
out = root / "out/raw/v4-packet-audit.json"
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps({k: v for k, v in result.items() if not k.endswith("inventory")}, indent=2))
assert all(result[k] for k in ("v4_packet_declared_hashes_match",
                               "v4_packet_declared_names_match",
                               "regression_declared_hashes_match",
                               "regression_declared_names_match",
                               "exact_two_file_delta", "v4_source_matches_packet",
                               "v4_final_test_matches_regression"))
