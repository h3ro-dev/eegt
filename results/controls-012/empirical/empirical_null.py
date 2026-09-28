"""Proposed sealed-event timing null. Never reads EEG waveform arrays.

The empirical entry point is intentionally gated by an independently accepted
protocol receipt. Current DRAFT protocol cannot execute either empirical stage.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import os
import platform
import resource
import signal
import sqlite3
import statistics
import sys
import time
from pathlib import Path

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    if os.environ.get(_name) != "1":
        raise SystemExit(f"{_name}=1 required before numerical imports")

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
REPO = PROJECT / "work" / "transition-extracted-final" / "repo"
CONTROLS = PROJECT / "work" / "next-study" / "controls"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(CONTROLS))

from eegt.waveform_events import match_events  # noqa: E402
from null_controls import timing_matched_control  # noqa: E402


STRATA = (("extremum", "peak", "positive_to_negative"),
          ("extremum", "trough", "negative_to_positive"),
          ("inflection", None, "curvature_positive_to_negative"),
          ("inflection", None, "curvature_negative_to_positive"))


class ResourceStop(Exception):
    """Graceful resource refusal with an intact stage receipt."""


def runtime_versions():
    return {"python": platform.python_version(),
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy")}


def rss_bytes():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value*1024)


def resource_guard(start_cpu, cpu_ceiling, rss_ceiling):
    """Stop between draws, reserving five CPU minutes for a durable receipt."""
    if time.process_time()-start_cpu >= cpu_ceiling-300:
        raise ResourceStop("CPU_PREEMPTIVE_STOP")
    if rss_bytes() >= rss_ceiling:
        raise ResourceStop("RSS_LIMIT_AT_DRAW_BOUNDARY")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for piece in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(piece)
    return h.hexdigest()


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def seed_for(base, array_row, channel, stratum_index, draw):
    if not (0 <= array_row < 1000 and 0 <= channel < 10 and
            0 <= stratum_index < 10 and 0 <= draw < 10000):
        raise ValueError("seed coordinates outside frozen domain")
    return base + array_row * 1_000_000 + channel * 100_000 + stratum_index * 10_000 + draw


def in_support(row, intervals):
    a, b = row["support_start_seconds"], row["support_end_seconds"]
    return any(left <= a <= b <= right for left, right in intervals)


def pooled_f1(rows):
    n_a = sum(row["n_a"] for row in rows)
    n_b = sum(row["n_b"] for row in rows)
    matched = sum(row["matched"] for row in rows)
    return None if not (n_a or n_b) else 2 * matched / (n_a + n_b)


def order_summary(values):
    """Fixed fifth, fiftieth, ninety-fifth sorted observations of 99 draws."""
    if len(values) != 99 or any(value is None for value in values):
        return {"status": "NOT_ESTIMABLE", "reason": "NOT_99_NONEMPTY_DRAWS"}
    ordered = sorted(values)
    return {"status": "OK", "draws": 99, "order_05": ordered[4],
            "median": statistics.median(ordered), "order_95": ordered[94]}


def _stratum(row):
    return row["family"], row.get("polarity"), row.get("direction")


def _partition(repo, entry):
    path = repo / entry["path"]
    if not path.is_file() or path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
        raise ValueError(f"PARTITION_HASH_MISMATCH: {entry['path']}")
    with gzip.open(path, "rt") as handle:
        first = json.loads(next(handle))
        if first.get("type") != "header" or first.get("value") != entry["header"]:
            raise ValueError("PARTITION_HEADER_MISMATCH")
        rows = []
        for line in handle:
            item = json.loads(line)
            if item.get("type") != "event":
                raise ValueError("PARTITION_RECORD_TYPE_MISMATCH")
            rows.append(item["value"])
    if (len(rows) != entry["event_rows"] or
            sum(bool(r["accepted"]) for r in rows) != entry["accepted_rows"]):
        raise ValueError("PARTITION_ROW_COUNT_MISMATCH")
    return rows


def _timeline(db, array_row, channel):
    row = db.execute("SELECT receipt_json FROM native_timeline WHERE array_row=? AND "
                     "variant='independent_phase' AND channel=?", (array_row, channel)).fetchone()
    if row is None:
        raise ValueError("MISSING_ACCEPTED_TIMELINE")
    receipt = json.loads(row[0])
    if receipt["clock_mapping"] != "identical block clock" or receipt["clock_error_bound_seconds"] != 0:
        raise ValueError("UNSUPPORTED_CLOCK_MAPPING")
    return receipt


def _accepted_match(db, array_row, channel, stratum, tolerance):
    row = db.execute("SELECT receipt_json FROM native_match WHERE array_row=? AND "
                     "variant='independent_phase' AND channel=? AND family=? AND "
                     "polarity IS ? AND direction=? AND ABS(tolerance_seconds-?)<1e-9",
                     (array_row, channel, stratum[0], stratum[1], stratum[2], tolerance)).fetchone()
    if row is None:
        raise ValueError("MISSING_ACCEPTED_MATCH")
    return json.loads(row[0])


def _checked_match(a, b, interval_a, interval_b, tolerance, expected=None):
    result = match_events(a, b, intervals_a_seconds=interval_a,
                          intervals_b_seconds=interval_b, shared_clock=True,
                          clock_error_bound_seconds=0., tolerance_seconds=tolerance,
                          max_eligible_pairs=4_000_000)
    if result["status"] != "OK":
        raise ValueError(f"MATCHER_{result['status']}")
    if expected is not None:
        for key in ("n_a_before", "n_b_before", "n_a", "n_b", "matched", "eligible_pairs"):
            if result[key] != expected[key]:
                raise ValueError(f"ACCEPTED_MATCH_DIVERGENCE:{key}")
        if ((result["agreement"] is None) != (expected["agreement"] is None) or
                result["agreement"] is not None and
                abs(result["agreement"]-expected["agreement"]) > 1e-12):
            raise ValueError("ACCEPTED_AGREEMENT_DIVERGENCE")
    return result


def evaluate_row(db, repo, row_spec, protocol, *, resource_check=None):
    """One fixed selected block; all 99 draws, four contacts and four strata."""
    array_row = row_spec["array_row"]
    events = {entry["variant"]: _partition(repo, entry) for entry in row_spec["partitions"]}
    tol = protocol["tolerances_seconds"]
    draw_count = protocol["draws"]
    if draw_count != 99 or tol != [0.01, 0.025, 0.05]:
        raise ValueError("PROTOCOL_PARAMETER_MISMATCH")
    raw = {str(t): [] for t in tol}
    null = {str(t): [[] for _ in range(draw_count)] for t in tol}
    cell_counts = []
    for channel in range(4):
        timeline = _timeline(db, array_row, channel)
        common = timeline["common_guarded_intervals"]
        if not common or timeline["common_duration_seconds"] <= 0:
            raise ValueError("EMPTY_COMMON_GUARDED_SUPPORT")
        interval_a = timeline["primary_guarded_intervals"]
        interval_b = timeline["variant_guarded_intervals_aligned"]
        for stratum_index, stratum in enumerate(STRATA):
            aa = [r for r in events["primary"] if r["accepted"] and
                  r["channel_key"] == f"channel_{channel}" and _stratum(r) == stratum]
            bb = [r for r in events["independent_phase"] if r["accepted"] and
                  r["channel_key"] == f"channel_{channel}" and _stratum(r) == stratum]
            bb_common = [r for r in bb if in_support(r, common)]
            if len(bb_common) == 0 and len(bb) != 0:
                # Empty after guard is valid; the accepted matcher records it.
                pass
            cell_counts.append({"channel": channel, "stratum": list(stratum),
                                "accepted_primary": len(aa), "accepted_phase": len(bb),
                                "phase_complete_support": len(bb_common),
                                "common_guarded_seconds": timeline["common_duration_seconds"]})
            for t in tol:
                recorded = _accepted_match(db, array_row, channel, stratum, t)
                checked = _checked_match(aa, bb, interval_a, interval_b, t, recorded)
                raw[str(t)].append(checked)
            for draw in range(draw_count):
                if resource_check is not None:
                    resource_check()
                seed = seed_for(protocol["seed_base"], array_row, channel, stratum_index, draw)
                if bb_common:
                    shuffled, _ = timing_matched_control(
                        bb_common, support_intervals=common,
                        bin_seconds=protocol["bin_seconds"], seed=seed)
                else:
                    shuffled = []
                for t in tol:
                    compared = _checked_match(aa, shuffled, interval_a, interval_b, t)
                    if compared["n_a"] != raw[str(t)][-1]["n_a"] or \
                            compared["n_b"] != raw[str(t)][-1]["n_b"]:
                        raise ValueError("NULL_ELIGIBLE_COUNT_DIVERGENCE")
                    null[str(t)][draw].append(compared)
    by_tolerance = {}
    for t in tol:
        key = str(t)
        observed = pooled_f1(raw[key])
        draws = [pooled_f1(rows) for rows in null[key]]
        distribution = order_summary(draws)
        by_tolerance[key] = {"status": "OK" if distribution["status"] == "OK" else "NOT_ESTIMABLE",
                             "raw_recomputed_f1": observed, "null_draw_f1": draws,
                             "null_summary": distribution,
                             "exploratory_excess_vs_null_median":
                                 observed-distribution["median"] if observed is not None and
                                 distribution["status"] == "OK" else None,
                             "raw_eligible_primary": sum(r["n_a"] for r in raw[key]),
                             "raw_eligible_phase": sum(r["n_b"] for r in raw[key]),
                             "raw_matched": sum(r["matched"] for r in raw[key])}
    return {"array_row": array_row, "candidate_index": row_spec["candidate_index"],
            "source_subject": row_spec["source_subject"], "session": row_spec["session"],
            "recording_id": row_spec["recording_id"], "cells": cell_counts,
            "by_tolerance": by_tolerance, "status": "OK"}


def _runtime_checks(protocol, review_path):
    if protocol["status"] != "DRAFT_PENDING_INDEPENDENT_REVIEW":
        raise ValueError("UNEXPECTED_PROTOCOL_STATE")
    review = json.loads(review_path.read_text())
    if review.get("status") != "ACCEPTED" or review.get("protocol_sha256") != digest(HERE / "PROTOCOL.json"):
        raise ValueError("INDEPENDENT_PROTOCOL_ACCEPTANCE_REQUIRED")
    if runtime_versions() != protocol["runtime_exact"]:
        raise ValueError("RUNTIME_VERSION_MISMATCH")
    for label, entry in protocol["source_sha256"].items():
        path = Path(entry["absolute_path"])
        if not path.is_file() or path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise ValueError(f"SOURCE_HASH_MISMATCH:{label}")


def _write_new(path, value):
    with path.open("x") as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")


def descriptive_summary(rows, *, planned_rows):
    """Person/session denominators and equal-person descriptive excess only."""
    sessions = {(row["source_subject"], row["session"]) for row in rows if row["status"] == "OK"}
    people = {person for person, _ in sessions}
    complete = sorted(person for person in people if
                      (person, "001") in sessions and (person, "002") in sessions)
    person_excess = {}
    for person in complete:
        values = [row["by_tolerance"]["0.025"]["exploratory_excess_vs_null_median"]
                  for row in rows if row["source_subject"] == person and
                  row["session"] in ("001", "002")]
        if len(values) == 2 and all(value is not None for value in values):
            person_excess[person] = statistics.mean(values)
    return {"planned_selected_blocks": planned_rows, "completed_selected_blocks": len(rows),
            "distinct_people": len(people), "distinct_person_sessions": len(sessions),
            "two_session_complete_people": len(complete),
            "estimable_two_session_people": len(person_excess),
            "descriptive_person_excess_25ms": person_excess,
            "equal_person_mean_excess_25ms": statistics.mean(person_excess.values())
            if person_excess else None,
            "inference": "NONE; people and nights are described, blocks are not independent people"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("first-unit", "remaining"))
    parser.add_argument("--review", type=Path, required=True,
                        help="Independent acceptance receipt bound to PROTOCOL.json hash")
    parser.add_argument("--admission", type=Path,
                        help="Root first-unit resource admission, required for remaining")
    args = parser.parse_args()
    start_cpu, start_wall = time.process_time(), time.perf_counter()
    protocol = json.loads((HERE / "PROTOCOL.json").read_text())
    soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
    ceiling = int(protocol["resource_bounds"]["cpu_seconds"])
    new_hard = ceiling if hard == resource.RLIM_INFINITY else min(hard, ceiling)
    new_soft = min(new_hard-10, soft if soft != resource.RLIM_INFINITY else ceiling)
    if new_soft <= 0:
        raise ResourceStop("CPU_LIMIT_TOO_SMALL_FOR_RECEIPT")
    resource.setrlimit(resource.RLIMIT_CPU, (new_soft, new_hard))
    def cpu_signal(_signum, _frame):
        raise ResourceStop("CPU_SOFT_LIMIT")
    signal.signal(signal.SIGXCPU, cpu_signal)
    _runtime_checks(protocol, args.review)
    first_path = HERE / "FIRST-UNIT.json"
    if args.stage == "first-unit":
        selection = protocol["selection"][:1]
        output = first_path
    else:
        if not first_path.is_file() or args.admission is None:
            raise ValueError("FIRST_UNIT_AND_ADMISSION_REQUIRED")
        first = json.loads(first_path.read_text())
        admission = json.loads(args.admission.read_text())
        if first.get("status") != "COMPLETE" or admission.get("status") != "ACCEPTED" or \
                admission.get("first_unit_sha256") != digest(first_path) or \
                admission.get("protocol_sha256") != digest(HERE / "PROTOCOL.json"):
            raise ValueError("FIRST_UNIT_RESOURCE_ADMISSION_MISMATCH")
        first_resources = first["resources"]
        if (first_resources["cpu_seconds"]*12*3 > 6000 or
                first_resources["peak_rss_bytes"] > 1024**3):
            raise ValueError("FIRST_UNIT_RESOURCE_PROJECTION_REFUSED")
        selection = protocol["selection"][1:]
        output = HERE / "REMAINING.json"
    if output.exists():
        raise FileExistsError(f"preserve existing stage receipt: {output}")
    db_path = Path(protocol["source_sha256"]["accepted_index"]["absolute_path"])
    db = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
    report = {"schema": "eegt-conditional-timing-null-stage/v1", "status": "IN_PROGRESS",
              "stage": args.stage, "protocol_sha256": digest(HERE / "PROTOCOL.json"),
              "review_sha256": digest(args.review), "runtime": runtime_versions(),
              "rows": [], "not_run": []}
    def check_resource():
        resource_guard(start_cpu, ceiling, protocol["resource_bounds"]["rss_bytes"])
    try:
        for row_spec in selection:
            check_resource()
            report["rows"].append(evaluate_row(db, REPO, row_spec, protocol,
                                               resource_check=check_resource))
            check_resource()
        if report["status"] == "IN_PROGRESS":
            report["status"] = "COMPLETE"
    except ResourceStop as error:
        report["status"] = "RESOURCE_STOP"
        report["failure"] = {"type": type(error).__name__, "message": str(error),
                             "array_row": selection[len(report["rows"])]["array_row"]
                             if len(report["rows"]) < len(selection) else None}
    except Exception as error:
        report["status"] = "FAILED"
        report["failure"] = {"type": type(error).__name__, "message": str(error),
                             "array_row": selection[len(report["rows"])]["array_row"]
                             if len(report["rows"]) < len(selection) else None}
    finally:
        signal.signal(signal.SIGXCPU, signal.SIG_IGN)
        db.close()
        report["resources"] = {"cpu_seconds": time.process_time()-start_cpu,
                               "wall_seconds": time.perf_counter()-start_wall,
                               "peak_rss_bytes": rss_bytes(),
                               "cpu_hard_limit_seconds": new_hard,
                               "cpu_soft_limit_seconds": new_soft}
        complete_rows = report["rows"]
        if args.stage == "remaining":
            complete_rows = json.loads(first_path.read_text())["rows"] + complete_rows
        report["descriptive_denominators"] = descriptive_summary(
            complete_rows, planned_rows=len(protocol["selection"]))
        report["original_012_release_unmodified"] = True
        completed = {r["array_row"] for r in complete_rows}
        report["not_run"] = [r["array_row"] for r in protocol["selection"]
                             if r["array_row"] not in completed]
        report["not_run_reason"] = ("PENDING_RESOURCE_ADMISSION" if args.stage == "first-unit"
                                    and report["status"] == "COMPLETE" else
                                    report["status"] if report["not_run"] else None)
        _write_new(output, report)
    if report["status"] != "COMPLETE":
        raise SystemExit(f"stage {args.stage} ended {report['status']}; see {output}")
    print(f"{args.stage} COMPLETE; receipt {output}")


if __name__ == "__main__":
    main()
