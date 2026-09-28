"""Metadata-only EESM19 capacity audit; never opens an EEG payload."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
META = ROOT / "outputs/research/eesm19-metadata-audit"
CATALOG = ROOT / "work/database-release/final/catalog.sqlite"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    inputs = {}

    def record(path: Path) -> Path:
        inputs[str(path.relative_to(ROOT))] = digest(path)
        return path

    source_receipt = json.loads(record(META / "out/REPORT.json").read_text())
    inventory = json.loads(record(META / "sources/graphql-inventory.json").read_text())
    source_seals = {
        x["path"]: x
        for x in json.loads(record(META / "sources/metadata-sources.json").read_text())
    }
    assert inventory["data"]["snapshot"]["id"] == "ds005185:1.0.2"
    assert source_receipt["source_revision"]["openneuro_git_commit"] == "0857858f7a2ba1582930f23eca3ec56f90a96da9"
    pattern = re.compile(
        r"(?P<person>sub-\d{3})/(?P<session>ses-\d{3})/eeg/"
        r"(?P=person)_(?P=session)_task-sleep_acq-(?P<acq>earEEG|PSG)_eeg\.(?P<ext>set|fdt)"
    )
    payloads = defaultdict(dict)
    for row in inventory["data"]["snapshot"]["files"]:
        match = pattern.fullmatch(row["filename"])
        if match:
            info = match.groupdict()
            key = (info["person"], info["session"], info["acq"])
            assert info["ext"] not in payloads[key], key
            payloads[key][info["ext"]] = row
    assert len(payloads) == 200
    assert all(set(pair) == {"set", "fdt"} for pair in payloads.values())
    people = sorted({key[0] for key in payloads})
    source_sessions = {}
    for person in people:
        relative = f"{person}/{person}_sessions.tsv"
        path = record(META / "sources/pinned" / relative)
        assert digest(path) == source_seals[relative]["sha256"], relative
        rows = list(csv.DictReader(path.read_text().splitlines(), delimiter="\t"))
        declared_sessions = {f"ses-{int(row['sessionNumber']):03d}" for row in rows}
        indexed_sessions = {key[1] for key in payloads if key[0] == person}
        assert declared_sessions == indexed_sessions, person
        assert len(rows) == len(declared_sessions), person
        source_sessions[person] = {
            acquisition: sorted(key[1] for key in payloads if key[0] == person and key[2] == acquisition)
            for acquisition in ("earEEG", "PSG")
        }
        accepted = source_receipt["effective_metadata"]["source_people_sessions"][person]
        assert source_sessions[person]["earEEG"] == accepted["ear_only_sessions"]
        assert source_sessions[person]["PSG"] == accepted["psg_sessions"]

    channel_metadata = {}
    for acquisition in ("earEEG", "PSG"):
        relative = f"acq-{acquisition}_channels.tsv"
        path = record(META / "sources/pinned" / relative)
        assert digest(path) == source_seals[relative]["sha256"]
        rows = list(csv.DictReader(path.read_text().splitlines(), delimiter="\t"))
        ear = [row for row in rows if re.fullmatch(r"E[LR][ABCTEI]", row["name"])]
        assert len(ear) == 12
        channel_metadata[acquisition] = {
            "total_channels_declared": len(rows),
            "ear_contact_names_declared": [row["name"] for row in ear],
            "ear_units_declared": sorted({row["units"] for row in ear}),
            "ear_reference_declared": sorted({row["reference"] for row in ear}),
            "reserved_record_header_verification": "NOT_RUN",
            "physical_calibration": "UNKNOWN",
            "exact_reference_set": "UNKNOWN",
        }
    record(CATALOG)
    con = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    recordings = [dict(row) for row in con.execute(
        "SELECT source_subject,session_id,status,duration_seconds FROM recordings "
        "WHERE dataset_id='ds005185' ORDER BY source_subject,session_id"
    )]
    con.close()
    exposed_people = sorted({f"sub-{int(row['source_subject']):03d}" for row in recordings})
    assert exposed_people == source_receipt["development_people"] == ["sub-001"]
    assert [(row["source_subject"], row["session_id"]) for row in recordings] == [("001", "005"), ("001", "006")]
    reserved = sorted(set(people) - set(exposed_people))
    assert reserved == source_receipt["reserved_people"]

    def capacity(acquisition: str) -> dict:
        candidate_people = [person for person in reserved if source_sessions[person][acquisition]]
        return {
            "candidate_people": candidate_people,
            "candidate_person_count": len(candidate_people),
            "candidate_session_count": sum(len(source_sessions[person][acquisition]) for person in candidate_people),
            "candidate_source_hours": None,
            "candidate_selected_windows": None,
            "candidate_event_count": None,
            "qualified_person_count_established_by_this_audit": 0,
            "qualification_status": "NOT_ASSESSED",
            "new_person_waveform_access": "NOT_RUN",
            "capacity_is_metadata_upper_bound": True,
        }

    output = {
        "schema": "eegt-replication-capacity/1",
        "status": "METADATA_AUDITED_PENDING_INDEPENDENT_REVIEW",
        "dataset": "ds005185:1.0.2",
        "source_commit": source_receipt["source_revision"]["openneuro_git_commit"],
        "source_url": "https://openneuro.org/datasets/ds005185/versions/1.0.2",
        "source_scope": "Previously acquired pinned inventory and metadata only; no EEG, media, task scoring or reserved waveform payload read.",
        "denominators": {
            "source_people": len(people),
            "source_sessions": len(payloads),
            "source_acquisition_sessions": dict(sorted(Counter(key[2] for key in payloads).items())),
            "source_payload_files": sum(len(pair) for pair in payloads.values()),
            "source_payload_bytes": sum(row["size"] for pair in payloads.values() for row in pair.values()),
            "recorded_exposed_people": len(exposed_people),
            "recorded_exposed_sessions": len(recordings),
            "recorded_exposed_source_hours": sum(row["duration_seconds"] for row in recordings) / 3600,
            "recorded_unexposed_candidate_people_all_acquisitions": len(reserved),
            "recorded_unexposed_candidate_sessions_all_acquisitions": sum(key[0] in reserved for key in payloads),
        },
        "exposure_evidence": {
            "catalog_recordings": recordings,
            "whole_person_exclusions": exposed_people,
            "meaning": "No prior waveform exposure recorded in the accepted project audit/catalog for the other EESM19 source IDs. Cross-dataset person overlap, external use and foundation-model pretraining overlap remain UNKNOWN.",
        },
        "ear_only_capacity": capacity("earEEG"),
        "psg_session_ear_contact_capacity": capacity("PSG"),
        "source_person_sessions": source_sessions,
        "channel_metadata": channel_metadata,
        "design_consequences": [
            "Ear-only acquisition offers at most 9 recorded-unexposed candidate people, so a target of 12 complete people is infeasible within that acquisition family.",
            "PSG sessions offer 19 candidate people and 76 candidate sessions, contingent on a separately frozen ear-contact measurement contract and quality qualification.",
            "PSG and ear-only session counts must not be treated as independent people or pooled without a prespecified acquisition-family design.",
            "Nine is only an attainable adjusted-p floor for the prior eight-test family, not adequate power. The minimum scientifically worthwhile effect and transferable variance remain unspecified.",
            "No additional reserved waveform access is authorized by this audit; protocol freeze and independent review remain required.",
        ],
        "inputs_sha256": inputs,
        "audit_script_sha256": digest(Path(__file__)),
    }
    (HERE / "CAPACITY.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": output["status"], "denominators": output["denominators"], "ear_only_candidates": output["ear_only_capacity"]["candidate_person_count"], "psg_candidates": output["psg_session_ear_contact_capacity"]["candidate_person_count"]}, indent=2))


if __name__ == "__main__":
    main()
