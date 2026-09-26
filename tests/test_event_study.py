"""Synthetic protocol invariants; no empirical detector call occurs in tests."""
import numpy as np
import pytest

from eegt import event_study as study


def result(events=(), guard=100, start=0, end=7500, channel=0):
    return dict(sample_rate_hz=250., events=list(events), runs=[dict(
        channel_key=f"channel_{channel}", segment_start_sample=0,
        clock_start_seconds=0., start_sample=start, end_sample=end,
        guard_samples=guard, status="OK")])


def event(seconds, support, *, index=None, family="extremum", polarity="peak",
          direction="positive_to_negative", channel=0):
    return dict(accepted=True, seconds=seconds, support_start_seconds=support[0],
                support_end_seconds=support[1], index=index if index is not None else int(seconds*250),
                channel_key=f"channel_{channel}", segment_key="segment_0", family=family,
                polarity=polarity, direction=direction)


def test_matching_uses_raw_overlap_then_two_guard_layers():
    edge = event(.5, (.35, .65))
    center = event(15., (14.5, 15.5))
    a = result([edge, center])
    b = result([edge.copy(), center.copy()])
    timeline, rows = study.native_matches(a, b, "gain_x2")
    assert timeline[0]["raw_valid_overlap_seconds"] == 30.
    assert timeline[0]["common_guarded_intervals"] == [(.4, 29.6)]
    stratum = next(r for r in rows if r["channel"] == 0 and r["family"] == "extremum"
                   and r["tolerance_seconds"] == .025)
    assert (stratum["accepted_a_before_guard"], stratum["n_a"], stratum["matched"]) == (2, 1, 1)
    assert stratum["common_duration_seconds"] == pytest.approx(29.2)
    assert len([r for r in rows if r["channel"] == 0]) == 12
    empty = next(r for r in rows if r["channel"] == 0 and r["polarity"] == "trough"
                 and r["tolerance_seconds"] == .025)
    assert empty["n_a"] == empty["n_b"] == 0
    assert empty["agreement"] is None and empty["common_duration_seconds"] == pytest.approx(29.2)


def test_shift_preserves_emitted_indices_masks_and_aligns_all_comparison_fields():
    x = np.arange(30000, dtype=np.float64).reshape(4, 7500)
    mask = np.ones_like(x, dtype=bool)
    mask[1, 100] = False
    y, valid, _, transform = study.native_variant(x, mask, "shift_plus_200ms", 62)
    assert not valid[:, :50].any()
    assert not valid[1, 150]
    assert np.array_equal(y[:, 50:], np.where(mask[:, :-50], x[:, :-50], 0))
    assert transform["dropped_source_samples"] == [7450, 7500]
    row = event(10.2, (9.9, 10.5), index=2550)
    row.update(fractional_index=2550.25, interval_end_seconds=11.2)
    aligned = study.aligned_rows([row], "shift_plus_200ms")[0]
    assert row["seconds"] == 10.2 and row["index"] == 2550
    assert aligned["index"] == 2550 and aligned["seconds"] == pytest.approx(10.)
    assert aligned["fractional_index"] == pytest.approx(2500.25)
    assert aligned["support_start_seconds"] == pytest.approx(9.7)
    assert aligned["support_end_seconds"] == pytest.approx(10.3)
    assert aligned["interval_end_seconds"] == pytest.approx(11.)
    assert study.raw_intervals(result(start=50, end=7500), 0) == [(.2, 30.)]


def test_common_reference_ands_masks_and_never_averages_partial_contacts():
    x = np.tile(np.array([[1.], [2.], [3.], [4.]]), (1, 7500))
    mask = np.ones(x.shape, bool)
    mask[2, 10] = False
    x[2, 10] = 999999
    y, valid, _, transform = study.native_variant(x, mask, "common_mean_reference", 62)
    assert not valid[:, 10].any() and np.all(y[:, 10] == 0)
    assert np.all(valid[:, 11]) and np.allclose(y[:, 11], [-1.5, -.5, .5, 1.5])
    assert transform["valid_runs"][0] == [(0, 10), (11, 7500)]


def test_phase_requires_full_finite_input_and_records_seed_hash():
    x = np.zeros((4, 7500), np.float64)
    mask = np.ones_like(x, bool)
    mask[0, 1] = False
    with pytest.raises(ValueError, match="INVALID_PHASE_INPUT"):
        study.native_variant(x, mask, "independent_phase", 62)
    mask[0, 1] = True
    x[0, 1] = np.nan
    with pytest.raises(ValueError, match="native variant input"):
        study.native_variant(x, mask, "shared_phase", 62)


def test_polarity_mapping_is_comparison_only_and_inverts_curvature_direction():
    rows = [event(1., (.5, 1.5)),
            event(2., (1.5, 2.5), family="inflection", polarity=None,
                  direction="curvature_negative_to_positive")]
    mapped = study.aligned_rows(rows, "polarity_xneg1")
    assert mapped[0]["polarity"] == "trough"
    assert mapped[0]["direction"] == "negative_to_positive"
    assert mapped[1]["direction"] == "curvature_positive_to_negative"
    assert rows[0]["polarity"] == "peak" and rows[1]["direction"] == "curvature_negative_to_positive"


def test_integer_event_bins_ignore_fractional_landmark_time():
    rows = [dict(accepted=True, family="extremum", index=199, fractional_index=200.5,
                 polarity="peak", channel_key="channel_0"),
            dict(accepted=True, family="inflection", index=200, fractional_index=199.1,
                 direction="curvature_negative_to_positive", channel_key="channel_3"),
            dict(accepted=False, family="extremum", index=201, polarity="peak", channel_key="channel_0")]
    r = dict(sample_rate_hz=200., events=rows,
             runs=[dict(channel_key=f"channel_{c}", segment_start_sample=0, clock_start_seconds=0.,
                        start_sample=0, end_sample=6000, guard_samples=200, status="OK") for c in range(4)])
    counts, eligible = study.event_counts(r)
    assert counts.shape == (30, 16)
    assert counts[0, 0] == 1 and counts[1, 15] == 1 and counts.sum() == 2
    assert eligible == list(range(1, 29))


def test_support_never_bridges_missing_intervals():
    k, pairs = study.support_indices([1, 2, 3, 5, 6, 7, 8, 9],
                                      [1, 2, 3, 5, 6, 7, 8, 9])
    assert k == [1, 2, 3, 5, 6, 7, 8, 9]
    assert pairs == [(1, 2), (2, 3), (5, 6), (6, 7), (7, 8), (8, 9)]
    assert study.metric_result(np.ones((30, 16)), np.ones((30, 200)), k, pairs,
                               "change")["reason"] == "INSUFFICIENT_ADJACENT_PAIRS"


def test_zero_nonfinite_and_constant_vectors_abstain_whole_metric():
    k = list(range(1, 9))
    pairs = [(a, b) for a, b in zip(k, k[1:])]
    counts = np.zeros((30, 16), dtype=np.int64)
    latent = np.zeros((30, 200), dtype=np.float64)
    for i in k:
        counts[i, i] = 1
        counts[i, 0] = i
        latent[i, i] = 1
        latent[i, 0] = i
    assert study.metric_result(counts, latent, k, pairs, "geometry")["rho"] == pytest.approx(1.)
    counts[4] = 0
    assert study.metric_result(counts, latent, k, pairs, "geometry")["reason"] == "EVENT_ZERO_NORM_VECTOR"
    counts[4, 4] = 1
    counts[4, 0] = 4
    latent[4, 4] = np.nan
    assert study.metric_result(counts, latent, k, pairs, "geometry")["reason"] == "MODEL_NONFINITE_VECTOR"
    latent[4, 4] = 1
    counts[:] = 0
    counts[k, 0] = 1
    assert study.metric_result(counts, latent, k, pairs, "geometry")["reason"] == "EVENT_CONSTANT_DISTANCE_VECTOR"


def test_analytic_proportional_vectors_do_not_gain_rank_from_roundoff():
    base = np.array([42, 32, 26, 14, 16, 3, 4, 1, 9, 40, 32, 45, 25, 30, 48, 36])
    vectors = np.arange(1, 9)[:, None] * base
    pairs = [(i, j) for i in range(8) for j in range(i+1, 8)]
    distances, reason = study._cosine_pairs(vectors, pairs)
    assert distances is None and reason == "CONSTANT_DISTANCE_VECTOR"
    assert study.COSINE_CONSTANT_ULPS == 32


@pytest.mark.parametrize("field,value", [("candidate_index", 99), ("variant", "wrong"),
                                          ("input_sha256", "corrupt"), ("output_sha256", "corrupt")])
def test_receipt_identity_order_and_hash_corruption(field, value):
    measurement = dict(candidate_index=62, variant="original", input_sha256="a", output_sha256="b")
    measurement[field] = value
    with pytest.raises(ValueError, match="input/order/output hash mismatch"):
        study.checked_measurement(measurement, 62, "original", "a", "b")


def test_exact_person_sign_flips_and_four_endpoint_multiplicity():
    assert study.exact_signflip([1., 1.]) == dict(
        status="COMPARED", reason=None, n=2, observed_mean=1., assignments=4,
        extreme_count=2, p_two_sided=.5, p_bonferroni_four=1.)
    assert study.exact_signflip([1.])["status"] == "NOT_ESTIMABLE"
    assert study.exact_signflip([0., 0.])["p_two_sided"] == 1.
    # Inclusive 1e-12 tie rule treats a nearly equal absolute assignment as extreme.
    assert study.exact_signflip([1., 1., 1., 1., 1.])["p_two_sided"] == .0625


def test_recording_medians_then_equal_night_person_means():
    selected = []
    for i in range(122):
        person = "001" if i < 61 else "002"
        night = "001" if i % 61 < 31 else "002"
        selected.append(dict(candidate_index=i, source_subject=person, session=night,
                             recording_id=person+night))
    rows = []
    for r in selected:
        for model in study.MODELS:
            for metric in study.METRICS:
                rows.append(dict(candidate_index=r["candidate_index"], model=model, metric=metric,
                                 effect=1. if r["source_subject"] == "001" else 2., reason=None))
    endpoints = study.aggregate_effects(rows, selected)
    assert len(endpoints) == 4
    assert all(len(e["participants"]) == 2 and e["paired_valid_blocks"] == 122 for e in endpoints)
    assert all(e["test"]["observed_mean"] == 1.5 and e["test"]["p_two_sided"] == .5 for e in endpoints)


def test_quantiles_and_unique_exposure_for_morphology():
    r = result([dict(accepted=True, family="extremum", channel_key="channel_0", amplitude_uv=1.,
                     slope_uv_per_second=-2., curvature_uv_per_second2=3.)])
    groups = study.morphology_groups(r)
    rows = study.morphology_summary(groups)
    peak = next(row for row in rows if row["channel"] == 0 and row["family"] == "extremum")
    assert peak["guarded_seconds"] == pytest.approx(29.2)
    assert peak["accepted_count"] == 1
    assert peak["distributions"]["slope_magnitude_uv_per_second"]["q50"] == 2.


def test_streaming_morphology_pools_scalar_quantiles_by_recording():
    selected = [dict(array_row=0, candidate_index=10, source_subject="001", session="001",
                     recording_id="a"),
                dict(array_row=1, candidate_index=11, source_subject="001", session="001",
                     recording_id="a"),
                dict(array_row=2, candidate_index=12, source_subject="001", session="002",
                     recording_id="b")]
    seen = []
    def loader(i):
        seen.append(i)
        row = dict(accepted=True, family="extremum", channel_key="channel_0",
                   amplitude_uv=float(i+1))
        return result([row])
    nights, differences = study.combine_morphology(selected, loader)
    assert seen == [0, 1, 2]
    first = next(r for r in nights if r["night"] == "001" and r["channel"] == 0
                 and r["family"] == "extremum")
    assert first["accepted_count"] == 2
    assert first["guarded_seconds"] == pytest.approx(58.4)
    assert first["distributions"]["amplitude_uv"]["q50"] == 1.5
    difference = next(r for r in differences if r["channel"] == 0 and r["family"] == "extremum")
    assert difference["distribution_differences"]["amplitude_uv"]["q50"] == 1.5
