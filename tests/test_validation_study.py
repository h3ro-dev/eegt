"""Synthetic contract checks and archived exposed-012 readback; no model/detector call."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import numpy as np

from eegt import validation_study as study
from eegt.validation_provenance import loaded_sources


PACKET = Path(__file__).resolve().parents[2]


def synthetic_case(*, people=3, per_record=6, failed_pairs=()):
    cohorts = [dict(id="new_people", people=[f"p{i}" for i in range(people)], sessions=["night-A", "night-B"]),
               dict(id="new_sessions", people=[f"q{i}" for i in range(people)], sessions=["later-X", "later-Y"])]
    protocol = dict(state="FROZEN", cohorts=cohorts,
                    selection=dict(candidate_blocks_per_recording=per_record,
                                   block_seconds=30, stratum_seconds=60 if per_record == 6 else 30),
                    aggregation=dict(minimum_paired_metric_blocks_per_recording=3 if per_record == 6 else 1,
                                     minimum_complete_people_per_cohort=3 if people == 3 else 1),
                    multiplicity=dict(family_size=8, alpha=.05))
    source = dict(source=dict(dataset="synthetic", commit="fixed-commit"), records=[])
    for cohort in cohorts:
        for person in cohort["people"]:
            for night in cohort["sessions"]:
                row = dict(source_subject=person, session=night, cohort=cohort["id"],
                           file=dict(path=f"{person}/{night}.set", algorithm="sha256",
                                     expected_digest="a" * 64))
                row["recording_id"] = study.recording_id(source, row)
                source["records"].append(row)
    source["records"].sort(key=lambda r: (r["source_subject"], r["session"]))
    rows, native_rows, valid_rows, prepared_rows, ids = [], [], [], [], []
    selected_per_record = per_record // 2 if per_record == 6 else per_record
    for record_number, source_row in enumerate(source["records"]):
        for block in range(per_record):
            ci = record_number * per_record + block
            failed = (source_row["source_subject"], source_row["session"]) in failed_pairs
            eligible = not failed and (block % 2 == 0 if per_record == 6 else True)
            row = dict(candidate_index=ci, recording_id=source_row["recording_id"],
                       source_subject=source_row["source_subject"], session=source_row["session"],
                       cohort=source_row["cohort"], start_seconds=block * 30,
                       duration_seconds=30, stratum_index=(block * 30) // protocol["selection"]["stratum_seconds"],
                       quality_status="FAIL" if failed else "PASS",
                       reasons=["SYNTHETIC_QUALITY_FAIL"] if failed else [],
                       status="REJECTED" if failed else "ELIGIBLE" if eligible else "QUALIFIED_UNSELECTED",
                       array_row=len(ids) if eligible else None)
            if eligible:
                native = np.full((4, 7500), .1 + ci / 1000, dtype=np.float64)
                valid = np.ones((4, 7500), dtype=bool)
                prepared = np.full((4, 30, 200), .001 + ci / 100000, dtype=np.float32)
                row.update(native_array_sha256=study.pretrained_study.array_hash(native),
                           valid_mask_sha256=study.pretrained_study.array_hash(valid),
                           prepared_array_sha256=study.pretrained_study.array_hash(prepared))
                native_rows.append(native)
                valid_rows.append(valid)
                prepared_rows.append(prepared)
                ids.append(ci)
            rows.append(row)
    n = len(ids)
    native = dict(samples_uv=np.stack(native_rows) if n else np.empty((0, 4, 7500), dtype=np.float64),
                  valid=np.stack(valid_rows) if n else np.empty((0, 4, 7500), dtype=bool),
                  candidate_indices=np.array(ids, dtype=np.int64), sample_rate_hz=np.array(250))
    prepared = dict(patches=np.stack(prepared_rows) if n else np.empty((0, 4, 30, 200), dtype=np.float32),
                    candidate_indices=np.array(ids, dtype=np.int64))
    receipt = dict(records=rows, inference_gates=study.cohort_gates(rows, protocol))
    return protocol, source, receipt, native, prepared


def synthetic_frozen_root(base: Path, case):
    root = base / "repo"
    protocol, source, receipt, native, prepared = case
    for relative in study.REQUIRED_FROZEN_INPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative)
    (root / "protocol/experiment-013.json").write_text(study.canonical(protocol))
    (root / "protocol/corpus-manifest-013.json").write_text(study.canonical(source))
    for model in study.MODELS:
        path = root / f"weights/{model}.bin"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((model + " synthetic checkpoint").encode())
        vendor = root / f"eegt/vendor/{model}/source.py"
        vendor.parent.mkdir(parents=True, exist_ok=True)
        vendor.write_text("# synthetic vendor\n")
    review = root / "results/013/review/ACCEPTANCE.json"
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text('{"status":"ACCEPTED"}')
    models = {}
    for model in study.MODELS:
        checkpoint = f"weights/{model}.bin"
        vendor = f"eegt/vendor/{model}/source.py"
        models[model] = dict(checkpoint=dict(path=checkpoint, sha256=study.digest(root / checkpoint)),
                             vendor_sources={vendor: study.digest(root / vendor)})
    bounds = dict(max_download_bytes=4_000_000_000, numeric_processes=1, blas_threads=1,
                  cpu_seconds=7200, rss_bytes=10_000_000_000,
                  artifact_bytes=10_000_000_000, first_block_required=True)
    freeze = dict(schema=study.FREEZE_SCHEMA, status="ACCEPTED",
                  inputs={relative: study.digest(root / relative) for relative in study.REQUIRED_FROZEN_INPUTS},
                  accepted_reviews=[dict(status="ACCEPTED", path="results/013/review/ACCEPTANCE.json",
                                         sha256=study.digest(review))],
                  models=models, resource_bounds=bounds,
                  runtimes={"encoder": dict(study.phase_runtime("encoder"), torch="2.4.1"),
                            "events": study.phase_runtime("events")})
    for relative, actual_path in loaded_sources().items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(actual_path.read_bytes())
        freeze["inputs"][relative] = study.digest(path)
    study.write_json(root / "results/013/RUN-SOURCE-MANIFEST.json", freeze)
    native_path = root / "data/derived/013/native-selected.npz"
    prepared_path = root / "data/derived/013/prepared.npz"
    study.save_npz(native_path, **native)
    study.save_npz(prepared_path, **prepared)
    receipt.update(inputs={"protocol/experiment-013.json": study.digest(root / "protocol/experiment-013.json"),
                           "protocol/corpus-manifest-013.json": study.digest(root / "protocol/corpus-manifest-013.json")},
                   native_array_path="data/derived/013/native-selected.npz",
                   native_array_sha256=study.digest(native_path),
                   array_path="data/derived/013/prepared.npz", array_sha256=study.digest(prepared_path))
    study.write_json(root / "results/013/prepared.json", receipt)
    acceptance = dict(schema=study.INPUT_ACCEPTANCE_SCHEMA, status="ACCEPTED",
                      run_source_manifest_sha256=study.digest(root / "results/013/RUN-SOURCE-MANIFEST.json"),
                      inputs={name: study.digest(root / name) for name in
                              ("results/013/prepared.json", "data/derived/013/native-selected.npz",
                               "data/derived/013/prepared.npz")})
    study.write_json(root / "results/013/INPUT-ACCEPTANCE.json", acceptance)
    return root


class ValidationContractTests(unittest.TestCase):
    def setUp(self):
        # Synthetic roots are not the fixed 20-record corpus checked by the
        # installed intake verifier. Exercise this module's local gate in unit
        # tests; the shared-verifier test below explicitly injects that call.
        find_spec = study.importlib.util.find_spec
        patcher = mock.patch.object(study.importlib.util, "find_spec",
                                    side_effect=lambda name: None if name == "eegt.validation_intake"
                                    else find_spec(name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_generic_counts_and_distinct_actual_nights(self):
        inputs = study.validate_inputs(*synthetic_case())
        self.assertEqual(len(inputs.receipt["records"]), 72)
        self.assertEqual(len(inputs.selected), 36)
        self.assertEqual({k: v["complete_participant_count"] for k, v in inputs.gates.items()},
                         {"new_people": 3, "new_sessions": 3})
        self.assertEqual([r["session"] for r in inputs.gates["new_sessions"]["records"][:2]],
                         ["later-X", "later-Y"])

    def test_missing_night_and_no_cohort_borrowing(self):
        case = synthetic_case(failed_pairs={("p0", "night-B")})
        inputs = study.validate_inputs(*case)
        self.assertEqual(inputs.gates["new_people"]["status"], "INSUFFICIENT_PARTICIPANTS")
        self.assertEqual(inputs.gates["new_sessions"]["status"], "READY")
        endpoints = study.aggregate_endpoints(inputs.selected, [], inputs.protocol, inputs.gates)
        self.assertEqual(len(endpoints), 8)
        self.assertTrue(all(e["test"]["p_two_sided"] is None for e in endpoints))
        self.assertIn("night-B:TOO_FEW_PAIRED_BLOCKS", endpoints[0]["participants"][0]["reasons"])

    def test_zero_eligible_and_insufficient_people_are_explicit(self):
        base = synthetic_case()
        all_pairs = {(r["source_subject"], r["session"]) for r in base[1]["records"]}
        inputs = study.validate_inputs(*synthetic_case(failed_pairs=all_pairs))
        self.assertEqual(inputs.native["samples_uv"].shape, (0, 4, 7500))
        self.assertEqual(len(inputs.selected), 0)
        endpoints = study.aggregate_endpoints(inputs.selected, [], inputs.protocol, inputs.gates)
        self.assertEqual(len(endpoints), 8)
        self.assertTrue(all(e["test"]["status"] == "NOT_ESTIMABLE" for e in endpoints))
        self.assertTrue(all(e["test"]["n"] == 0 for e in endpoints))

    def test_missing_model_and_support_failures_never_create_positive_p(self):
        inputs = study.validate_inputs(*synthetic_case())
        missing = study.aggregate_endpoints(inputs.selected, [], inputs.protocol, inputs.gates)
        self.assertTrue(all(e["test"]["p_bonferroni_eight"] is None for e in missing))
        rows = [dict(candidate_index=r["candidate_index"], model="codebrain", metric="geometry",
                     effect=None, reason="INSUFFICIENT_GEOMETRY_INTERVALS") for r in inputs.selected]
        unsupported = study.aggregate_endpoints(inputs.selected, rows, inputs.protocol, inputs.gates)
        self.assertEqual(unsupported[0]["paired_valid_blocks"], 0)
        self.assertEqual(unsupported[0]["records"][0]["excluded"][0]["reason"],
                         "INSUFFICIENT_GEOMETRY_INTERVALS")
        self.assertIsNone(unsupported[0]["test"]["p_two_sided"])

    def test_exact_signflip_fixed_eight_test_resolution(self):
        inputs = study.validate_inputs(*synthetic_case())
        rows = [dict(candidate_index=r["candidate_index"], model="codebrain", metric="geometry",
                     effect=1.0, reason=None) for r in inputs.selected if r["cohort"] == "new_people"]
        endpoints = study.aggregate_endpoints(inputs.selected, rows, inputs.protocol, inputs.gates)
        test = endpoints[0]["test"]
        self.assertEqual(test["n"], 3)
        self.assertEqual(test["assignments"], 8)
        self.assertEqual(test["p_two_sided"], .25)
        self.assertEqual(test["p_bonferroni_eight"], 1.)
        self.assertEqual(test["two_sided_minimum_p"], .25)
        self.assertEqual(endpoints[4]["cohort"], "new_sessions")
        self.assertEqual(endpoints[4]["records"][0]["night"], "later-X")

    def test_under_three_people_cannot_generate_positive_inference(self):
        inputs = study.validate_inputs(*synthetic_case(people=1, per_record=2))
        rows = [dict(candidate_index=r["candidate_index"], model="codebrain", metric="geometry",
                     effect=1.0, reason=None) for r in inputs.selected]
        result = study.aggregate_endpoints(inputs.selected, rows, inputs.protocol, inputs.gates)[0]["test"]
        self.assertEqual(result["n"], 1)
        self.assertEqual(result["status"], "NOT_ESTIMABLE")
        self.assertIsNone(result["p_two_sided"])

    def test_duplicate_and_misjoined_identities_rejected(self):
        case = synthetic_case()
        mutated = copy.deepcopy(case[2])
        mutated["records"][0]["recording_id"] = case[1]["records"][1]["recording_id"]
        with self.assertRaisesRegex(ValueError, "candidate/source identity"):
            study.validate_inputs(case[0], case[1], mutated, case[3], case[4])
        duplicate = copy.deepcopy(case[1])
        duplicate["records"][1]["source_subject"] = duplicate["records"][0]["source_subject"]
        duplicate["records"][1]["session"] = duplicate["records"][0]["session"]
        with self.assertRaisesRegex(ValueError, "census, order, or identity"):
            study.verify_source(case[0], duplicate)
        inputs = study.validate_inputs(*case)
        bad = [dict(candidate_index=inputs.selected[0]["candidate_index"], model="codebrain",
                    metric="geometry", effect=1., reason=None)] * 2
        with self.assertRaisesRegex(ValueError, "duplicate"):
            study.aggregate_endpoints(inputs.selected, bad, inputs.protocol, inputs.gates)

    def test_source_changes_and_missing_freeze_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = synthetic_frozen_root(Path(td), synthetic_case(people=1, per_record=2))
            self.assertEqual(study.require_accepted_freeze(root)["status"], "ACCEPTED")
            study.require_input_acceptance(root, study.require_accepted_freeze(root))
            path = root / "eegt/event_study.py"
            path.write_text("changed")
            with self.assertRaisesRegex(ValueError, "frozen input SHA256 mismatch"):
                study.require_accepted_freeze(root)
            path.write_text("eegt/event_study.py")
            (root / "results/013/RUN-SOURCE-MANIFEST.json").unlink()
            with self.assertRaises(FileNotFoundError):
                study.require_accepted_freeze(root)

    def test_shared_verifier_cannot_bypass_analysis_freeze_checks(self):
        with tempfile.TemporaryDirectory() as td:
            root = synthetic_frozen_root(Path(td), synthetic_case(people=1, per_record=2))
            def shared_verifier(*, root, phase):
                return (study.read_json(root / "results/013/RUN-SOURCE-MANIFEST.json"), None, None)
            shared_module = types.SimpleNamespace(require_accepted_freeze=shared_verifier)
            with (mock.patch.object(study.importlib.util, "find_spec", return_value=object()),
                  mock.patch.object(study.importlib, "import_module", return_value=shared_module)):
                self.assertEqual(study.require_accepted_freeze(root, stage="events")["status"], "ACCEPTED")
                manifest_path = root / "results/013/RUN-SOURCE-MANIFEST.json"
                seal = study.read_json(manifest_path)
                seal["inputs"].pop("eegt/waveform_events.py")
                study.write_json(manifest_path, seal)
                with self.assertRaisesRegex(ValueError, "frozen source census incomplete"):
                    study.require_accepted_freeze(root, stage="events")
                seal["inputs"]["eegt/waveform_events.py"] = study.digest(root / "eegt/waveform_events.py")
                seal["resource_bounds"].pop("cpu_seconds")
                study.write_json(manifest_path, seal)
                with self.assertRaisesRegex(ValueError, "fixed resource bounds"):
                    study.require_accepted_freeze(root, stage="events")

    def test_engineering_numeric_mask_and_night_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root = synthetic_frozen_root(Path(td), synthetic_case(people=1, per_record=2))
            freeze_sha = study.digest(root / "results/013/RUN-SOURCE-MANIFEST.json")
            channels = [f"ear-{i:02d}" for i in range(12)]
            samples = np.zeros((2, 12, 15000), dtype=np.float64)
            valid = np.ones_like(samples, dtype=bool)
            valid[0, 0, 10:20] = False
            samples[0, 0, 10:20] = np.nan
            archive_path = root / "data/derived/013/engineering-native.npz"
            study.save_npz(archive_path, samples_uv=samples, valid=valid)
            rows = [dict(source_subject="001", session=night, channel_names=channels,
                         native_array_sha256=study.pretrained_study.array_hash(samples[i]),
                         valid_mask_sha256=study.pretrained_study.array_hash(valid[i]))
                    for i, night in enumerate(("005", "006"))]
            receipt_path = root / "results/013/engineering-prepared.json"
            receipt = dict(array_path="data/derived/013/engineering-native.npz",
                           array_sha256=study.digest(archive_path), sample_rate_hz=500,
                           channel_names=channels, records=rows)
            study.write_json(receipt_path, receipt)
            accepted = dict(schema="eegt-validation-engineering-input-acceptance/v1",
                            status="ACCEPTED", run_manifest_sha256=freeze_sha,
                            inputs={"results/013/engineering-prepared.json": study.digest(receipt_path),
                                    receipt["array_path"]: study.digest(archive_path)})
            acceptance_path = root / "results/013/engineering-input-acceptance.json"
            study.write_json(acceptance_path, accepted)
            loaded, arrays, _ = study.load_engineering_input(root, freeze_sha)
            self.assertEqual(loaded["sessions"], ["005", "006"])
            self.assertFalse(arrays["valid"][0, 0, 10:20].any())
            receipt["records"][1]["session"] = "007"
            study.write_json(receipt_path, receipt)
            accepted["inputs"]["results/013/engineering-prepared.json"] = study.digest(receipt_path)
            study.write_json(acceptance_path, accepted)
            with self.assertRaisesRegex(ValueError, "EESM19 shape, nights"):
                study.load_engineering_input(root, freeze_sha)

    def test_hash_checked_first_block_and_deterministic_resume(self):
        class FakeEncoder:
            calls = 0
            def __init__(self, checkpoint):
                self.checkpoint = checkpoint
            def encode(self, x):
                FakeEncoder.calls += 1
                return x.copy()

        with tempfile.TemporaryDirectory() as td:
            root = synthetic_frozen_root(Path(td), synthetic_case(people=1, per_record=2))
            first = study.run_inference(root, "codebrain", encoder_factory=FakeEncoder)
            self.assertEqual(first["status"], "PAUSED_FOR_FIRST_BLOCK_PROFILE")
            self.assertEqual(FakeEncoder.calls, 5)
            with self.assertRaises(FileNotFoundError):
                study.run_inference(root, "codebrain", resume=True, encoder_factory=FakeEncoder)
            self.assertEqual(FakeEncoder.calls, 5)
            profile = root / "results/013/first-block-inference-codebrain.json"
            freeze = study.read_json(root / "results/013/RUN-SOURCE-MANIFEST.json")
            study.write_json(root / "results/013/first-block-review-inference-codebrain.json",
                             dict(schema="eegt-validation-first-block-review/v1", status="ADMITTED",
                                  phase="inference-codebrain", profile_sha256=study.digest(profile),
                                  run_manifest_sha256=study.digest(root / "results/013/RUN-SOURCE-MANIFEST.json"),
                                  resource_bounds=freeze["resource_bounds"], admitted_by="synthetic-test"))
            result = study.run_inference(root, "codebrain", resume=True, encoder_factory=FakeEncoder)
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(result["block_variant_runs"], 40)
            self.assertEqual(FakeEncoder.calls, 40)
            again = study.run_inference(root, "codebrain", resume=True, encoder_factory=FakeEncoder)
            self.assertEqual(again["array_sha256"], result["array_sha256"])
            self.assertEqual(FakeEncoder.calls, 40)
            inputs = study.load_inputs(root)
            freeze = study.read_json(root / "results/013/RUN-SOURCE-MANIFEST.json")
            accepted = study.read_json(root / "results/013/INPUT-ACCEPTANCE.json")
            self.assertEqual(study.checked_model_archive(root, "codebrain", inputs, freeze, accepted,
                                                         allow_synthetic=True)[1]["status"],
                             "COMPLETE")
            with self.assertRaisesRegex(ValueError, "synthetic encoder archive"):
                study.checked_model_archive(root, "codebrain", inputs, freeze, accepted)
            self.assertEqual(study.checked_model_archive(root, "cbramod", inputs, freeze, accepted)[1]["reason"],
                             "INFERENCE_RECEIPT_MISSING")

    def test_real_encoder_torch_version_mismatch_refused_before_forward(self):
        with tempfile.TemporaryDirectory() as td:
            root = synthetic_frozen_root(Path(td), synthetic_case(people=1, per_record=2))
            with mock.patch.object(study.importlib.metadata, "version", return_value="9.9.9"):
                with self.assertRaisesRegex(ValueError, "encoder Torch runtime mismatch"):
                    study.run_inference(root, "codebrain")
            self.assertFalse((root / "results/013/inference-codebrain.json").exists())
            self.assertFalse(list((root / "results/013").glob("inference-codebrain-parts/*")))

    def test_failed_forward_preserves_explicit_failure(self):
        class FailingEncoder:
            def __init__(self, checkpoint):
                pass
            def encode(self, x):
                raise RuntimeError("synthetic forward failure")

        with tempfile.TemporaryDirectory() as td:
            root = synthetic_frozen_root(Path(td), synthetic_case(people=1, per_record=2))
            with self.assertRaisesRegex(RuntimeError, "synthetic forward failure"):
                study.run_inference(root, "codebrain", encoder_factory=FailingEncoder)
            rows = list((root / "results/013").glob("failed-forward-codebrain-*.json"))
            self.assertEqual(len(rows), 1)
            failure = study.read_json(rows[0])
            self.assertEqual(failure["variant"], "original")
            self.assertEqual(failure["error_type"], "RuntimeError")
            self.assertFalse((root / "results/013/inference-codebrain.json").exists())

    def test_no_ready_cohort_writes_empty_model_archive_without_forward(self):
        base = synthetic_case(people=1, per_record=2)
        pairs = {(r["source_subject"], r["session"]) for r in base[1]["records"]}
        with tempfile.TemporaryDirectory() as td:
            root = synthetic_frozen_root(Path(td), synthetic_case(people=1, per_record=2, failed_pairs=pairs))
            result = study.run_inference(root, "codebrain", encoder_factory=lambda _: self.fail("encoder was called"))
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(result["shape"], [0, 5, 4, 30, 200])
            self.assertEqual(result["measurements"], [])

    def test_synthetic_first_event_block_and_recorded_replay(self):
        with tempfile.TemporaryDirectory() as td:
            root = synthetic_frozen_root(Path(td), synthetic_case(people=1, per_record=2))
            first = study.run_events(root)
            self.assertEqual(first["status"], "PAUSED_FOR_FIRST_BLOCK_PROFILE")
            self.assertEqual(first["completed_blocks"], 1)
            self.assertEqual(len(list((root / "data/derived/013/events").rglob("*.jsonl.gz"))), 23)
            replay = study.replay_events(root)
            self.assertEqual(replay["status"], "REPLAYED_RECORDED_EVENTS")
            self.assertEqual(replay["completed_blocks"], 1)
            self.assertEqual(replay["partitions"], 23)
            self.assertFalse(replay["detector_regenerated"])

    def test_failed_synthetic_event_preserves_failure_row(self):
        with tempfile.TemporaryDirectory() as td:
            root = synthetic_frozen_root(Path(td), synthetic_case(people=1, per_record=2))
            inputs = study.load_inputs(root)
            freeze_sha = study.digest(root / "results/013/RUN-SOURCE-MANIFEST.json")
            acceptance_sha = study.digest(root / "results/013/INPUT-ACCEPTANCE.json")
            db = study.open_index(root, inputs, freeze_sha, acceptance_sha)
            try:
                def failed_detector(*args, **kwargs):
                    raise RuntimeError("synthetic detector failure")
                with self.assertRaisesRegex(RuntimeError, "synthetic detector failure"):
                    study.process_event_block(root, inputs.selected[0], inputs,
                                              {name: None for name in study.MODELS}, db,
                                              freeze_sha, acceptance_sha, detector=failed_detector)
                failure = study.read_json(root / f"results/013/failed-event-{inputs.selected[0]['candidate_index']:05d}.json")
                self.assertEqual(failure["error_type"], "RuntimeError")
                self.assertEqual(db.execute("SELECT count(*) FROM completed_blocks").fetchone()[0], 0)
            finally:
                db.close()

    def test_exposed_012_full_first_block_numeric_parity(self):
        result = study.verify_exposed_012(PACKET, PACKET / "supplement-exposed012",
                                          PACKET / "scratch/exposed012/analysis.sqlite")
        self.assertEqual(result["status"], "EXACT_ROW_ZERO_PARITY")
        self.assertEqual(result["selected_numeric_rows_verified"], 122)
        self.assertEqual(result["model_outputs_verified"], 1220)
        self.assertEqual(result["event_partitions_verified"], 23)
        self.assertEqual(result["prepared_metrics_verified"], 20)
        self.assertEqual(result["block_effects_verified"], 4)
        self.assertEqual(result["native_matches_verified"], 816)
        self.assertFalse(result["detector_regenerated"])


if __name__ == "__main__":
    unittest.main()
