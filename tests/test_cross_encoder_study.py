"""Synthetic gates for the prespecified Experiment 011 analysis."""

import copy
import os
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import spearmanr

from eegt import cross_encoder_study as study
from eegt import pretrained_study as previous


PACKET = Path(os.environ.get('EEGT_011_PACKET', Path(__file__).resolve().parents[2]))


def row(ci, person="001", session="001", recording="r1", array_row=None):
    return dict(candidate_index=ci, source_subject=person, session=session,
                recording_id=recording, status="ELIGIBLE", array_row=ci if array_row is None else array_row)


def synthetic_ledger():
    rng = np.random.default_rng(21)
    rows = [row(0), row(1, array_row=1)]
    patches = rng.normal(size=(2, 4, 30, 200)).astype(np.float32)
    prepared = dict(patches=patches, candidate_indices=np.array([0, 1], dtype=np.int64))
    for view, dim in (("morphology", 8), ("spectrum", 40), ("coordination", 5)):
        prepared["baseline_" + view] = rng.normal(size=(2, 28, dim))
    grid = np.empty((2, 5, 4, 30, 200), dtype=np.float32)
    measurements = []
    for i, r in enumerate(rows):
        for j, name in enumerate(study.VARIANTS):
            x = previous.waveform_variant(patches[i], name, 9009 + r["candidate_index"])
            grid[i, j] = x * np.float32(0.7)
            measurements.append(dict(candidate_index=r["candidate_index"], variant=name,
                                     input_sha256=previous.array_hash(x),
                                     output_sha256=previous.array_hash(grid[i, j]),
                                     maximum_absolute_prepared_uv=float(np.max(np.abs(x)) * 100)))
    archive = dict(embeddings=grid, candidate_indices=prepared["candidate_indices"].copy(),
                   variants=np.array(study.VARIANTS))
    return rows, prepared, archive, measurements


def test_full_frozen_input_preflight():
    if 'EEGT_011_PACKET' not in os.environ and not (PACKET / 'input/pretrained_weights.pth').is_file():
        pytest.skip('optional captured-packet preflight; set EEGT_011_PACKET for the actual checkpoint test')
    validated = study.validate_inputs(PACKET)
    assert len(validated["selected"]) == 122
    assert len(validated["old_run"]["measurements"]) == 610
    assert validated["protocol"]["selection"]["primary_expected_people"] == 5


def test_geometry_and_change_alignment_with_average_ties():
    rng = np.random.default_rng(17)
    a = rng.normal(size=(28, 200))
    same, reason = study.checked_vectors(a)
    assert reason is None and len(same["geometry"]) == 378 and len(same["change"]) == 27
    for metric in study.METRICS:
        rho, missing = study.spearman_result(same[metric], same[metric])
        assert missing is None and rho == pytest.approx(1.0, abs=1e-12)
    left = np.array([0, 1, 1, 3, 4], dtype=float)
    right = np.array([0, 2, 2, 1, 5], dtype=float)
    assert study.spearman_result(left, right)[0] == pytest.approx(spearmanr(left, right).statistic)


def test_zero_nonfinite_and_constant_abstain():
    assert study.checked_vectors(np.zeros((28, 200)))[1] == "ZERO_NORM_VECTOR"
    assert study.checked_vectors(np.full((28, 200), np.nan))[1] == "NONFINITE_VECTOR"
    identical = np.tile(np.ones(200), (28, 1))
    vectors, reason = study.checked_vectors(identical)
    assert reason is None
    assert study.spearman_result(vectors["geometry"], vectors["geometry"])[1] == "CONSTANT_DISTANCE_VECTOR"
    assert study.spearman_result(None, vectors["change"], "ZERO_NORM_VECTOR")[1] == "LEFT_ZERO_NORM_VECTOR"


def test_ledger_hash_tampering_and_duplicate_or_reordered_identity():
    rows, prepared, archive, ledger = synthetic_ledger()
    study.verify_ledger(prepared, archive, rows, ledger)
    bad = copy.deepcopy(ledger)
    bad[3]["input_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="input hash"):
        study.verify_ledger(prepared, archive, rows, bad)
    bad = copy.deepcopy(ledger)
    bad[3]["output_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="output hash"):
        study.verify_ledger(prepared, archive, rows, bad)
    with pytest.raises(ValueError, match="ledger duplicate"):
        study.measurement_index(ledger[:-1] + [ledger[0]], rows)
    with pytest.raises(ValueError, match="ledger duplicate"):
        study.measurement_index(ledger[::-1], rows)
    with pytest.raises(ValueError, match="candidate order"):
        study.selected_identity(rows, [1, 0], 2)
    with pytest.raises(ValueError, match="duplicate identity"):
        study.selected_identity([rows[0], rows[0]], [0, 0], 2)


def test_phase_pairing_uses_only_common_rows():
    rows = [row(i, array_row=i) for i in range(3)]
    values = [(0.8, 0.2), (None, 0.1), (0.5, None)]
    cross = []
    for i, (a, b) in enumerate(values):
        for variant, value in (("original", a), ("independent_phase", b)):
            cross.append(dict(candidate_index=i, variant=variant, geometry_rho=value,
                              geometry_reason=None if value is not None else "CONSTANT_DISTANCE_VECTOR"))
    paired = study.paired_blocks(cross, rows, "geometry")
    assert [p["delta"] for p in paired] == pytest.approx([0.6, None, None], nan_ok=True)
    assert paired[1]["reason"] == "ORIGINAL:CONSTANT_DISTANCE_VECTOR"
    assert paired[2]["reason"] == "INDEPENDENT_PHASE:CONSTANT_DISTANCE_VECTOR"
    primary = study.primary_result(paired, rows, "geometry")
    assert primary["paired_valid_blocks"] == 1
    assert primary["aggregates"]["original_rho"]["valid_blocks"] == 1
    assert primary["aggregates"]["independent_phase_rho"]["valid_blocks"] == 1
    assert primary["status"] == "INSUFFICIENT_PARTICIPANTS" and primary["test"] is None


def test_record_minimum_and_incomplete_person():
    rows = []
    blocks = []
    ci = 0
    for person, session, count in (("001", "001", 3), ("001", "002", 3),
                                   ("002", "001", 3), ("002", "002", 2),
                                   ("003", "001", 1), ("003", "002", 3)):
        for _ in range(count):
            rows.append(row(ci, person, session, f"r{person}{session}", ci))
            blocks.append(dict(candidate_index=ci, value=float(ci), reason=None))
            ci += 1
    result = study.aggregate_metric(blocks, rows)
    assert result["complete_participants"] == 1
    assert result["participants"][1]["status"] == "INCOMPLETE_SESSIONS"
    assert result["participants"][2]["reasons"] == ["001:TOO_FEW_VALID_BLOCKS"]
    assert next(r for r in result["records"] if r["source_subject"] == "002" and r["session"] == "002")["status"] == "TOO_FEW_VALID_BLOCKS"


def test_exact_signflip_discrete_probabilities():
    assert study.exact_signflip([1, 1, 1])["p_two_sided"] == 0.25
    p5 = study.exact_signflip([1, 2, 3, 4, 5])
    assert p5["sign_combinations"] == 32 and p5["extreme_count"] == 2
    assert p5["p_two_sided"] == 0.0625 and p5["p_bonferroni_two"] == 0.125
    assert study.exact_signflip([1, -1, 0])["p_two_sided"] == 1.0


def test_immutable_output_refusal(tmp_path):
    output = tmp_path / "analysis.sqlite"
    output.write_bytes(b"prior")
    with pytest.raises(FileExistsError, match="preserve existing"):
        study.write_sqlite(output, None, None, None)
    manifest = tmp_path / "repo/results/011/run-manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("prior")
    with pytest.raises(FileExistsError, match="preserve existing"):
        study.freeze_manifest(dict(root=tmp_path / "repo", packet=tmp_path))


def test_reproduction_comparator_rejects_scientific_drift():
    a = dict(primary=[dict(effect=0.25)], database=dict(sha256="a"))
    b = dict(primary=[dict(effect=0.25 + 5e-13)], database=dict(sha256="b"))
    assert study.compare_science(a, b)
    b["primary"][0]["effect"] += 2e-12
    with pytest.raises(AssertionError, match="numeric mismatch"):
        study.compare_science(a, b)
