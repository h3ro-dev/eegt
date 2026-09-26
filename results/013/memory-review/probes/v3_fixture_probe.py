"""Diagnostic-only exposed 008/001/001 v3 process-boundary probe."""
from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
from pathlib import Path
import resource
import time

from eegt import validation_intake as intake

HERE = Path(__file__).resolve().parents[1]
OLD = Path("/Users/studio1/lanes.noindex/eco-uzwh8s.37.1/repo")
FIXTURE = OLD / "data/cache/ds005178/sub-001/ses-001/eeg/sub-001_ses-001_task-sleep_acq-earEEG_eeg.set"
EXPECTED_SHA = "4a48c81877a7ffffa1ccd090cfb2d9f3dfcfac478fff52640b16b9a7aef90efe"
BOUND = 2_147_483_648
ITERATIONS = 2


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(obj):
    print(json.dumps(obj, sort_keys=True, separators=(",", ":")), flush=True)


def main():
    if sha(FIXTURE) != EXPECTED_SHA:
        raise AssertionError("exposed fixture hash differs")
    old = json.loads((OLD / "protocol/corpus-manifest-008.json").read_text())
    rec = next(r for r in old["records"]
               if (r["source_subject"], r["session"]) == ("001", "001"))
    expected = json.loads((HERE / "evidence/qualification-output.json").read_text())
    fields = sorted(expected)
    assert len(fields) == 10
    seal = json.loads((HERE / "update-root-v3/results/013/RUN-SOURCE-MANIFEST.json").read_text())
    seal["inputs"]["eegt/validation_intake.py"] = sha(HERE / "scratch/v3-repo/eegt/validation_intake.py")
    seal["inputs"]["tests/test_validation_intake.py"] = sha(HERE / "scratch/v3-repo/tests/test_validation_intake.py")
    seal["status"] = "DIAGNOSTIC_ONLY_UNACCEPTED"
    seal["diagnostic_scope"] = "previously exposed Experiment008 001/001 fixture only"
    diagnostic = HERE / "scratch/v3-diagnostic-binding.json"
    diagnostic.write_text(json.dumps(seal, sort_keys=True, indent=2) + "\n")
    guard = intake.IntakeResources(HERE / "scratch/v3-probe-root", seal, "qualify")
    technical = dict(expected_channels=list(intake.CHANNELS),
                     expected_sample_rate_hz=intake.RATE, analysis_seconds=0)
    emit(dict(event="start", fixture_sha256=EXPECTED_SHA,
              diagnostic_binding_sha256=sha(diagnostic),
              original_seal_sha256=sha(HERE / "update-root-v3/results/013/RUN-SOURCE-MANIFEST.json"),
              iterations=ITERATIONS, bound_bytes=BOUND,
              binding_status=seal["status"], numerical_workers_max=1,
              blas_threads=1, parent_pid=__import__("os").getpid()))
    results = []
    children_cpu_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    prior_children_cpu = children_cpu_before.ru_utime + children_cpu_before.ru_stime
    prior_worker_cpu = 0.0
    begin = time.monotonic()
    for index in range(ITERATIONS):
        value = intake._qualify_record_isolated(FIXTURE, rec, technical, guard)
        got = {name: value[name] for name in fields}
        assert got == expected
        measured = guard.check()
        child_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        child_cpu = child_usage.ru_utime + child_usage.ru_stime
        child_delta = child_cpu - prior_children_cpu
        worker_delta = measured["worker_cpu_seconds"] - prior_worker_cpu
        prior_children_cpu = child_cpu
        prior_worker_cpu = measured["worker_cpu_seconds"]
        assert measured["process_peak_rss_bytes"] < BOUND
        assert len(multiprocessing.active_children()) == 0
        results.append(dict(index=index, fields_equal=True, fields=fields,
                            aggregate_peak_rss_bytes=measured["process_peak_rss_bytes"],
                            aggregate_cpu_seconds=measured["cpu_seconds"],
                            worker_cpu_seconds=measured["worker_cpu_seconds"],
                            os_child_cpu_seconds=child_delta,
                            accounted_child_cpu_seconds=worker_delta,
                            post_snapshot_cpu_gap_seconds=child_delta - worker_delta,
                            worker_peak_rss_bytes=measured["max_worker_peak_rss_bytes"],
                            parent_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        emit(dict(event="record", **results[-1]))

    bad = copy.deepcopy(rec)
    bad["channels"][0]["units"] = "V"
    try:
        intake._qualify_record_isolated(FIXTURE, bad, technical, guard)
        raise AssertionError("known decoder rejection was accepted")
    except intake._QualificationRejected as exc:
        assert str(exc) == "ValueError: declared EEG microvolt units required"
        emit(dict(event="known_decoder_rejection", reason=str(exc)))

    try:
        intake._qualify_record_isolated(FIXTURE, rec, None, guard)
        raise AssertionError("unexpected worker error was quarantined")
    except RuntimeError as exc:
        assert "qualification worker: TypeError:" in str(exc)
        emit(dict(event="unexpected_worker_error", fatal=str(exc)))

    drift_guard = intake.IntakeResources(HERE / "scratch/v3-probe-root", seal, "qualify")
    drift_guard.seal = copy.deepcopy(seal)
    drift_guard.seal["inputs"]["eegt/repeated.py"] = "0" * 64
    try:
        intake._qualify_record_isolated(FIXTURE, rec, technical, drift_guard)
        raise AssertionError("fatal source drift was accepted")
    except RuntimeError as exc:
        assert "returned no result" in str(exc)
        assert len(multiprocessing.active_children()) == 0
        emit(dict(event="source_drift", fatal=str(exc), active_children=0))

    children_cpu_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    child_cpu_os = (children_cpu_after.ru_utime + children_cpu_after.ru_stime
                    - children_cpu_before.ru_utime - children_cpu_before.ru_stime)
    measured = guard.check()
    emit(dict(event="result", iterations=ITERATIONS,
              all_ten_fields_equal=True,
              max_aggregate_peak_rss_bytes=max(r["aggregate_peak_rss_bytes"] for r in results),
              rss_bound_bytes=BOUND,
              aggregate_cpu_seconds=measured["cpu_seconds"],
              measured_worker_cpu_seconds=measured["worker_cpu_seconds"],
              os_children_cpu_seconds_including_startup_and_failure_probes=child_cpu_os,
              parent_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              max_worker_peak_rss_bytes=measured["max_worker_peak_rss_bytes"],
              wall_seconds=time.monotonic() - begin,
              no_active_children=len(multiprocessing.active_children()) == 0,
              diagnostic_only=True))


if __name__ == "__main__":
    main()
