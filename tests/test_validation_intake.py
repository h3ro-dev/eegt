"""Synthetic and explicitly exposed checks for Experiment013 intake."""

import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import weakref

import numpy as np
import pytest

from eegt import validation_intake as intake
from eegt import validation_study  # load the same scientific imports before sealing fixtures
from eegt.validation_provenance import loaded_sources


def _identity_source():
    cohorts = [dict(id="new_people", people=[f"{i:03}" for i in range(7, 11)],
                    sessions=["001", "002"]),
               dict(id="new_sessions", people=[f"{i:03}" for i in range(1, 7)],
                    sessions=["003", "004"])]
    protocol = dict(channels=list(intake.CHANNELS), rate_hz=250, cohorts=cohorts,
                    quality=dict(minimum_blocks_per_record=3,
                                 minimum_complete_participants=3))
    records = []
    for person, session in sorted((p, s) for c in cohorts for p in c["people"]
                                  for s in c["sessions"]):
        path = f"sub-{person}/ses-{session}/eeg/sub-{person}_ses-{session}_task-sleep_acq-earEEG_eeg.set"
        rid = hashlib.sha256(f"ds005178:commit:{path}".encode()).hexdigest()[:24]
        cohort = next(c["id"] for c in cohorts if person in c["people"])
        records.append(dict(recording_id=rid, source_subject=person, session=session,
                            cohort=cohort,
                            channels=[dict(name=n, type="EEG", units="uV") for n in intake.CHANNELS],
                            file=dict(path=path, algorithm="sha256", bytes=1,
                                      expected_digest="a" * 64)))
    return protocol, dict(source=dict(dataset="ds005178", commit="commit"), records=records)


def _json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n")


def _one_record(tmp_path, *, blocks=5):
    rate = 250
    t = np.arange(blocks * intake.BLOCK_SAMPLES) / rate
    x = np.vstack([20 * np.sin(2 * np.pi * (8 + c) * t) for c in range(4)]).astype(np.float64)
    valid = np.ones_like(x, dtype=bool)
    rid = "f" * 24
    rec = dict(recording_id=rid, source_subject="001", session="001",
               cohort="exposed_fixture", status="QUALIFIED",
               samples_per_channel=x.shape[1], path="source.set", sha256="a" * 64)
    source = dict(records=[dict(recording_id=rid, source_subject="001", session="001",
                                cohort="exposed_fixture")])
    protocol = dict(cohorts=[dict(id="exposed_fixture", people=["001"], sessions=["001"])],
                    quality=dict(minimum_blocks_per_record=3,
                                 minimum_complete_participants=3))
    return x, valid, rec, source, protocol


def _handoff(tmp_path, x, valid, rec, *, initial_pass=5):
    rel = "native.npz"
    np.savez_compressed(tmp_path / rel, samples_uv=x, valid=valid)
    times = np.concatenate([block * 30 + np.arange(1.5, 29, 1)
                            for block in range(initial_pass)])
    baseline_rel = "baseline.npz"
    np.savez_compressed(tmp_path / baseline_rel, times=times,
                        valid=np.ones(len(times), dtype=bool))
    return dict(records=intake._quality_rows_for_record(rec, 0, times,
                                                        np.ones(len(times), dtype=bool)),
                native_archives={rec["recording_id"]:
                                 dict(path=rel, sha256=intake.digest(tmp_path / rel))},
                baseline_archives={rec["recording_id"]:
                                   dict(path=baseline_rel,
                                        sha256=intake.digest(tmp_path / baseline_rel))})


def test_exact_twenty_record_source_contract_and_cohorts():
    protocol, source = _identity_source()
    assert len(intake.validate_sources(source, protocol)) == 20
    bad = json.loads(json.dumps(source))
    bad["records"][0]["cohort"] = "new_people"
    with pytest.raises(ValueError, match="identity|cohort"):
        intake.validate_sources(bad, protocol)
    bad = json.loads(json.dumps(source))
    bad["records"][0]["recording_id"] = "0" * 24
    with pytest.raises(ValueError, match="identity"):
        intake.validate_sources(bad, protocol)


def test_freeze_requires_acceptance_and_exact_source_hashes(tmp_path, monkeypatch):
    for name in intake.THREAD_ENV:
        monkeypatch.setenv(name, "1")
    protocol, source = _identity_source()
    protocol["state"] = "FROZEN"
    _json(tmp_path / intake.PROTOCOL_PATH, protocol)
    _json(tmp_path / intake.SOURCE_PATH, source)
    for name in intake.REQUIRED_FROZEN:
        path = tmp_path / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
    _json(tmp_path / "review.json", dict(status="ACCEPTED"))
    for name in ("codebrain.bin", "cbramod.bin", "vendor-codebrain.py", "vendor-cbramod.py"):
        (tmp_path / name).write_bytes(name.encode())
    seal = dict(schema="eegt-validation-run-source-manifest/v1", status="ACCEPTED",
                inputs={name: intake.digest(tmp_path / name) for name in intake.REQUIRED_FROZEN},
                accepted_reviews=[dict(status="ACCEPTED", path="review.json",
                                       sha256=intake.digest(tmp_path / "review.json"))],
                models={name:dict(checkpoint=dict(path=name + ".bin",
                                                  sha256=intake.digest(tmp_path / (name + ".bin"))),
                                  vendor_sources={"vendor-" + name + ".py":
                                                  intake.digest(tmp_path / ("vendor-" + name + ".py"))})
                        for name in ("codebrain", "cbramod")},
                resource_bounds=dict(max_download_bytes=4_000_000_000,
                                     numeric_processes=1, blas_threads=1,
                                     cpu_seconds=7200, rss_bytes=2147483648,
                                     artifact_bytes=10000000000, first_block_required=True),
                runtimes=dict(encoder=intake._runtime("encoder"),
                              corpus=intake._runtime("corpus")))
    for relative, actual_path in loaded_sources().items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(actual_path.read_bytes())
        seal.setdefault("inputs", {})[relative] = intake.digest(path)
    _json(tmp_path / intake.FREEZE_PATH, seal)
    assert intake.require_accepted_freeze(tmp_path, "encoder")[0]["status"] == "ACCEPTED"
    assert intake.require_accepted_freeze(tmp_path, "corpus")[0]["status"] == "ACCEPTED"
    monkeypatch.setenv("OMP_NUM_THREADS", "2")
    with pytest.raises(ValueError, match="numeric thread cap"):
        intake.require_accepted_freeze(tmp_path, "encoder")
    monkeypatch.setenv("OMP_NUM_THREADS", "1")
    protocol["state"] = "DRAFT"
    _json(tmp_path / intake.PROTOCOL_PATH, protocol)
    seal["inputs"][intake.PROTOCOL_PATH] = intake.digest(tmp_path / intake.PROTOCOL_PATH)
    _json(tmp_path / intake.FREEZE_PATH, seal)
    with pytest.raises(ValueError, match="protocol state"):
        intake.require_accepted_freeze(tmp_path, "encoder")
    protocol["state"] = "FROZEN"
    _json(tmp_path / intake.PROTOCOL_PATH, protocol)
    seal["inputs"][intake.PROTOCOL_PATH] = intake.digest(tmp_path / intake.PROTOCOL_PATH)
    _json(tmp_path / intake.FREEZE_PATH, seal)
    (tmp_path / "eegt/transitions.py").write_text("tampered")
    with pytest.raises(ValueError, match="input changed"):
        intake.require_accepted_freeze(tmp_path, "encoder")
    (tmp_path / "eegt/transitions.py").write_text("eegt/transitions.py")
    seal["status"] = "DRAFT"
    _json(tmp_path / intake.FREEZE_PATH, seal)
    with pytest.raises(ValueError, match="not accepted"):
        intake.require_accepted_freeze(tmp_path, "encoder")


def test_baseline_centers_and_native_gap_boundaries():
    times = np.arange(1.5, 29, 1)
    valid = np.ones(28, dtype=bool)
    valid[2] = False
    assert intake.baseline_counts(times, valid, blocks=1) == [27]
    assert intake._gap_reasons([[500, 500], [1000, 1200]], 0, 7500) == [
        "NATIVE_BOUNDARY", "NATIVE_GAP"]
    assert intake._gap_reasons([[7500, 7500]], 0, 7500) == []


@pytest.mark.skipif(importlib.util.find_spec("mne") is None,
                    reason="source qualification belongs to the corpus runtime")
def test_qualification_preserves_missing_and_rejects_source_sha_mismatch(tmp_path, monkeypatch):
    from eegt.repeated import qualify_record  # bind the phase-specific imports too
    protocol, source = _identity_source()
    first = source["records"][0]
    first["file"]["bytes"] = 5
    first["file"]["expected_digest"] = hashlib.sha256(b"right").hexdigest()
    _json(tmp_path / intake.SOURCE_PATH, source)
    _json(tmp_path / intake.PROTOCOL_PATH, protocol)
    seal = dict(resource_bounds=dict(cpu_seconds=7200, rss_bytes=2147483648,
        artifact_bytes=10000000000, first_block_required=True))
    for relative, actual_path in loaded_sources().items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(actual_path.read_bytes())
        seal.setdefault("inputs", {})[relative] = intake.digest(path)
    _json(tmp_path / intake.FREEZE_PATH, seal)
    monkeypatch.setattr(intake, "require_accepted_freeze",
                        lambda _root, _phase: (seal, protocol, source))
    path = intake._record_path(tmp_path, source, first)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"wrong")
    acquisition = dict(manifest_sha256=intake.digest(tmp_path / intake.SOURCE_PATH), completed=True,
                       records=[dict(recording_id=r["recording_id"], status="VERIFIED" if i == 0 else "FAILED",
                                     bytes=5 if i == 0 else None,
                                     sha256=r["file"]["expected_digest"] if i == 0 else None,
                                     reason=None if i == 0 else "SOURCE_MISSING")
                                for i, r in enumerate(source["records"])])
    incomplete = dict(acquisition, completed=False)
    _json(tmp_path / "results/013/acquisition.json", incomplete)
    with pytest.raises(ValueError, match="acquisition/source"):
        intake.qualify_sources(tmp_path)
    _json(tmp_path / "results/013/acquisition.json", acquisition)
    with pytest.raises(RuntimeError, match="first-record review required"):
        intake.qualify_sources(tmp_path)
    profile = tmp_path / "results/013/first-record-qualify.json"
    _json(tmp_path / "results/013/first-block-review-intake-qualify.json", dict(
        schema="eegt-validation-first-block-review/v1", status="ADMITTED",
        phase="intake-qualify", profile_sha256=intake.digest(profile),
        run_manifest_sha256=intake.digest(tmp_path / intake.FREEZE_PATH),
        resource_bounds=seal["resource_bounds"], admitted_by="synthetic-test"))
    result = intake.qualify_sources(tmp_path)
    assert len(result["records"]) == 20
    assert result["records"][0]["reason"] == "SOURCE_SHA256_MISMATCH"
    assert result["records"][0]["sha256"] == hashlib.sha256(b"wrong").hexdigest()
    assert all(r["reason"] == "SOURCE_MISSING" for r in result["records"][1:])


def test_qualification_releases_decoder_cycle_before_resource_check(tmp_path, monkeypatch):
    from eegt import repeated

    protocol, source = _identity_source()
    first = source["records"][0]
    first["file"].update(bytes=5, expected_digest=hashlib.sha256(b"right").hexdigest())
    _json(tmp_path / intake.SOURCE_PATH, source)
    _json(tmp_path / intake.PROTOCOL_PATH, protocol)
    _json(tmp_path / intake.FREEZE_PATH, {"resource_bounds": {"rss_bytes": 2147483648}})
    path = intake._record_path(tmp_path, source, first)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"right")
    _json(tmp_path / "results/013/acquisition.json", dict(
        manifest_sha256=intake.digest(tmp_path / intake.SOURCE_PATH), completed=True,
        records=[dict(recording_id=r["recording_id"], status="VERIFIED" if i == 0 else "FAILED",
                      bytes=5 if i == 0 else None,
                      sha256=first["file"]["expected_digest"] if i == 0 else None,
                      reason=None if i == 0 else "SOURCE_MISSING")
                 for i, r in enumerate(source["records"])]))
    monkeypatch.setattr(intake, "require_accepted_freeze",
                        lambda _root, _phase: ({}, protocol, source))

    refs = []

    class DecoderCycle:
        def __init__(self):
            self.cycle = self

    def fake_qualify(_path, _record, _protocol):
        cycle = DecoderCycle()
        refs.append(weakref.ref(cycle))
        return dict(gaps=[[2, 3]], decoder_warnings=["kept"],
                    native_nonfinite_samples_by_channel={"RB": 0},
                    digital_conversion={"checked_values": 12, "maximum_absolute_error_uv": 0.0},
                    duration_seconds=1.0)

    class Guard:
        def __init__(self, *_args):
            pass

        def check(self):
            return {}

        def after_record(self, index, _recording_id):
            if index == 0:
                assert refs[0]() is None

    monkeypatch.setattr(repeated, "qualify_record", fake_qualify)
    monkeypatch.setattr(intake, "IntakeResources", Guard)
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        receipt = intake.qualify_sources(tmp_path)
    finally:
        if was_enabled:
            gc.enable()
    row = receipt["records"][0]
    assert row["status"] == "QUALIFIED"
    assert row["decoder_warnings"] == ["kept"]
    assert row["digital_conversion"]["checked_values"] == 12
    assert row["gap_seconds"] == [dict(start_sample=2, stop_sample=3,
                                        start_seconds=2 / intake.RATE,
                                        stop_seconds=3 / intake.RATE)]


def test_quality_releases_decoder_before_feature_extraction(tmp_path, monkeypatch):
    import mne

    protocol, source = _identity_source()
    source["records"] = source["records"][:1]
    src = source["records"][0]
    for name, value in ((intake.SOURCE_PATH, source), (intake.PROTOCOL_PATH, protocol),
                        (intake.FREEZE_PATH, {})):
        _json(tmp_path / name, value)
    path = intake._record_path(tmp_path, source, src)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"right")
    rec = dict(src, status="QUALIFIED", samples_per_channel=8, gaps=[],
               sha256=intake.digest(path))
    _json(tmp_path / "results/013/qualification.json", dict(
        inputs={intake.SOURCE_PATH: intake.digest(tmp_path / intake.SOURCE_PATH)}))
    monkeypatch.setattr(intake, "require_accepted_freeze", lambda *_: ({}, protocol, source))
    monkeypatch.setattr(intake, "_verify_qualification", lambda *_: [rec])
    refs, closed = [], []
    samples = np.arange(32, dtype=np.float64).reshape(4, 8)

    class Raw:
        info, ch_names, n_times = {"sfreq": 250}, list(intake.CHANNELS), 8

        def __init__(self):
            self.cycle = self
            refs.append(weakref.ref(self))

        def get_data(self, **_kwargs):
            return samples.copy()

        def close(self):
            closed.append(True)

    class Guard:
        def __init__(self, *_args):
            pass

        def check(self):
            return {}

        def after_record(self, *_args):
            assert refs[0]() is None

    def extract(x, gaps):
        assert closed == [True] and refs[0]() is None
        np.testing.assert_array_equal(x, samples * 1e6)
        assert gaps == []
        return np.empty(0), np.empty(0, dtype=bool)

    monkeypatch.setattr(mne.io, "read_raw_eeglab", lambda *_a, **_k: Raw())
    monkeypatch.setattr(intake, "extract_baseline_valid", extract)
    monkeypatch.setattr(intake, "IntakeResources", Guard)
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        receipt = intake.build_quality_census(tmp_path)
    finally:
        if was_enabled:
            gc.enable()
    archive = receipt["native_archives"][rec["recording_id"]]
    with np.load(tmp_path / archive["path"], allow_pickle=False) as saved:
        np.testing.assert_array_equal(saved["samples_uv"], samples * 1e6)
        assert saved["valid"].all()


def test_all_missing_sources_keep_9600_candidates_and_zero_shaped_arrays(tmp_path):
    protocol, source = _identity_source()
    qualification = dict(records=[])
    quality = dict(records=[], native_archives={})
    for i, src in enumerate(source["records"]):
        rec = dict(**{k: src[k] for k in ("recording_id", "source_subject", "session", "cohort")},
                   status="QUARANTINED", reason="SOURCE_MISSING", path=src["file"]["path"],
                   sha256=None)
        qualification["records"].append(rec)
        quality["records"].extend(intake._quality_rows_for_record(rec, i))
    result = intake.prepare_from_handoff(tmp_path, source, protocol, qualification, quality)
    assert len(result["records"]) == 9600
    assert result["records"][0]["candidate_index"] == 0
    assert result["records"][-1]["candidate_index"] == 9599
    assert result["totals"]["eligible_blocks"] == 0
    assert set(result["inference_gates"]) == {"new_people", "new_sessions"}
    assert all(g["status"] == "INSUFFICIENT_PARTICIPANTS" for g in result["inference_gates"].values())
    with np.load(tmp_path / result["native_array_path"]) as a:
        assert a["samples_uv"].shape == (0, 4, 7500)
        assert a["valid"].shape == (0, 4, 7500)
        assert a["candidate_indices"].shape == (0,)
    with np.load(tmp_path / result["array_path"]) as a:
        assert a["patches"].shape == (0, 4, 30, 200)
    assert intake.validate_prepared(tmp_path, result, protocol, source)


def test_finite_flat_amplitude_gap_short_and_archive_hash_failures(tmp_path):
    x, valid, rec, source, protocol = _one_record(tmp_path)
    x[2, 2 * 7500 + 50] = np.nan
    valid[2, 2 * 7500 + 50] = False
    x[:, 3 * 7500:4 * 7500] = 0
    x[:, 4 * 7500:5 * 7500] *= 15
    valid[:, 7500 + 100:7500 + 110] = False
    rec["gaps"] = [[7500 + 100, 7500 + 110]]
    quality = _handoff(tmp_path, x, valid, rec)
    result = intake.prepare_from_handoff(tmp_path, source, protocol,
                                         dict(records=[rec]), quality,
                                         output_prefix="synthetic")
    rows = result["records"]
    assert rows[0]["status"] == "ELIGIBLE"
    assert rows[1]["quality_status"] == "FAIL" and "NATIVE_GAP" in rows[1]["reasons"]
    assert "nonfinite native samples" in rows[2]["reasons"]
    assert "flat native channel" in rows[3]["reasons"]
    assert "preprocessed absolute amplitude exceeds 100 uV" in rows[4]["reasons"]
    assert "SHORT_SUPPORT" in rows[5]["reasons"]
    assert len([r for r in rows if r["status"] == "ELIGIBLE"]) == 1
    assert result["inference_gates"]["exposed_fixture"]["status"] == "INSUFFICIENT_PARTICIPANTS"
    with (tmp_path / "native.npz").open("ab") as f:
        f.write(b"tamper")
    with pytest.raises(ValueError, match="handoff archive hash"):
        intake.prepare_from_handoff(tmp_path, source, protocol,
                                    dict(records=[rec]), quality,
                                    output_prefix="other")
    with (tmp_path / result["array_path"]).open("ab") as f:
        f.write(b"tamper")
    with pytest.raises(ValueError, match="numeric archive changed"):
        intake.validate_prepared(tmp_path, result, protocol, source, expected_records=1)


def test_cohort_gate_never_borrows_other_people_or_nights():
    protocol = dict(cohorts=[dict(id="new_people", people=["007", "008", "009"],
                                  sessions=["001", "002"]),
                             dict(id="new_sessions", people=["001", "002", "003"],
                                  sessions=["003", "004"])],
                    quality=dict(minimum_blocks_per_record=3,
                                 minimum_complete_participants=3))
    rows = []
    for cohort in protocol["cohorts"]:
        for person in cohort["people"]:
            for night in cohort["sessions"]:
                count = 3 if cohort["id"] == "new_people" else (3 if night == "003" else 0)
                rows.extend(dict(cohort=cohort["id"], source_subject=person,
                                 session=night, status="ELIGIBLE") for _ in range(count))
    gates = intake.inference_gates(rows, protocol)
    assert gates["new_people"]["status"] == "READY"
    assert gates["new_sessions"]["status"] == "INSUFFICIENT_PARTICIPANTS"
    assert [r["session"] for r in gates["new_sessions"]["records"]] == [
        "003", "004", "003", "004", "003", "004"]


def test_exposed_fixture_reuse_when_supplied():
    path = os.environ.get("EEGT_EXPOSED_FIXTURE")
    if not path:
        pytest.skip("set EEGT_EXPOSED_FIXTURE after explicit exposed-corpus and exposed-prepare")
    fixture = Path(path)
    parity = intake.read(fixture / "parity.json")
    assert parity["candidate_rows"] == 480
    assert parity["baseline_masks_equal"]
    assert parity["selected_prepared_bytes_equal"]
    assert intake.digest(fixture / "results/exposed/prepared.json") == parity["new_prepared_sha256"]
