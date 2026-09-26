"""Frozen Experiment 012 numerical helpers. Identity enters only aggregation.

The detector and matcher live in waveform_events and are never modified here.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import product
from pathlib import Path
import hashlib
import json

import numpy as np
from scipy.stats import rankdata

from . import pretrained_study, transitions, waveform_events as wave


NATIVE_VARIANTS = (
    "primary", "gain_x2", "polarity_xneg1", "additive_offset_50uv",
    "smoothing_21ms", "smoothing_51ms", "passband_0p5_40", "passband_1_30",
    "notch_50hz", "notch_60hz", "add_50hz", "add_60hz",
    "common_mean_reference", "spike_100uv_8ms", "symmetric_clipping_50uv",
    "independent_phase", "shared_phase", "shift_plus_200ms",
)
PREPARED_VARIANTS = pretrained_study.VARIANTS
MODELS = ("codebrain", "cbramod")
METRICS = ("geometry", "change")
# The largest observed distinction between mathematically identical cosine
# distances can be a few ulps from 1-dot(unit_a,unit_b). 32 float64 eps is a
# conservative arithmetic-equivalence bound, fixed from analytic proportional
# vectors before any empirical event call. It never changes the rank statistic.
COSINE_CONSTANT_ULPS = 32
MATCH_STRATA = (("extremum", "peak", "positive_to_negative"),
                ("extremum", "trough", "negative_to_positive"),
                ("inflection", None, "curvature_positive_to_negative"),
                ("inflection", None, "curvature_negative_to_positive"))
ROOT_INPUTS = (
    "protocol/experiment-012.json", "protocol/experiment-012-methods.md",
    "results/010/prepared.json", "results/010/inference.json",
    "results/011/inference.json", "data/derived/010/prepared.npz",
    "data/derived/010/embeddings.npz", "data/derived/011/embeddings.npz",
    "data/derived/012/native-selected.npz",
    "data/derived/012/native-selected-curator.json",
)


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def array_digest(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def read_json(path):
    return json.loads(Path(path).read_text())


def verify_files(packet):
    """Verify every inherited byte before analysis, including review evidence."""
    packet = Path(packet)
    source = read_json(packet / "SOURCE-MANIFEST.json")
    if source["schema"] != "eegt-input-packet/v1" or source["work_id"] != "eco-uzwh8s.34.2":
        raise ValueError("source packet identity mismatch")
    for relative, entry in source["files"].items():
        path = packet / relative
        if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise ValueError(f"inherited file mismatch: {relative}")
    protocol = read_json(packet / "repo/protocol/experiment-012.json")
    if (protocol["status"] != "FROZEN" or
        source["files"]["repo/protocol/experiment-012.json"]["sha256"] !=
            "60f02a8dce9a086be3a89fe612eb9437088054f007d14348c827292fae34e138" or
        source["files"]["repo/protocol/experiment-012-methods.md"]["sha256"] !=
            "86f41254f1fc35a0d95e4e9aab45bec0e12d1964ec18d8a38a7d92c57daf92e9"):
        raise ValueError("frozen protocol mismatch")
    if tuple(protocol["native_variants"]) != NATIVE_VARIANTS or tuple(protocol["prepared_variants"]) != PREPARED_VARIANTS:
        raise ValueError("frozen variant order mismatch")
    for relative, expected in protocol["inputs"].items():
        if digest(packet / "repo" / relative) != expected:
            raise ValueError(f"protocol input mismatch: {relative}")
    return source, protocol


def _npz(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def checked_measurement(measurement, candidate_index, variant, input_sha256, output_sha256):
    if ((measurement["candidate_index"], measurement["variant"]) != (candidate_index, variant) or
        measurement["input_sha256"] != input_sha256 or measurement["output_sha256"] != output_sha256):
        raise ValueError(f"input/order/output hash mismatch: {candidate_index}/{variant}")


def verify_arrays(packet):
    """Verify 122 native rows and both 610-pair inference ledgers in order."""
    packet = Path(packet)
    root = packet / "repo"
    source, protocol = verify_files(packet)
    prep_receipt = read_json(root / "results/010/prepared.json")
    curator = read_json(root / "data/derived/012/native-selected-curator.json")
    prepared = _npz(root / "data/derived/010/prepared.npz")
    native = _npz(root / "data/derived/012/native-selected.npz")
    encoders = {name: _npz(root / protocol["models"][name]["archive"]) for name in MODELS}
    receipts = {name: read_json(root / protocol["models"][name]["receipt"]) for name in MODELS}
    selected = [r for r in prep_receipt["records"] if r["status"] == "ELIGIBLE"]
    ids = [r["candidate_index"] for r in selected]
    if (len(prep_receipt["records"]) != 5760 or len(selected) != 122 or
        [r["array_row"] for r in selected] != list(range(122)) or
        ids != sorted(set(ids)) or ids[0] != 62 or
        not np.array_equal(prepared["candidate_indices"], ids)):
        raise ValueError("selected identity or order mismatch")
    if (set(native) != {"samples_uv", "valid", "sample_rate_hz"} or
        native["samples_uv"].shape != (122, 4, 7500) or native["samples_uv"].dtype != np.float64 or
        native["valid"].shape != (122, 4, 7500) or native["valid"].dtype != bool or
        float(native["sample_rate_hz"]) != 250 or
        not np.all(native["valid"]) or not np.isfinite(native["samples_uv"]).all()):
        raise ValueError("native data/rate/continuous mask mismatch")
    if prepared["patches"].shape != (122, 4, 30, 200) or prepared["patches"].dtype != np.float32:
        raise ValueError("prepared shape or dtype mismatch")
    if not np.isfinite(prepared["patches"]).all():
        raise ValueError("prepared data nonfinite")
    if len(curator["records"]) != 122:
        raise ValueError("native curator row count mismatch")
    for name in MODELS:
        archive, receipt = encoders[name], receipts[name]
        if (set(archive) != {"embeddings", "candidate_indices", "variants"} or
            archive["embeddings"].shape != (122, 5, 4, 30, 200) or
            archive["embeddings"].dtype != np.float32 or
            not np.array_equal(archive["candidate_indices"], ids) or
            tuple(archive["variants"]) != PREPARED_VARIANTS or
            receipt["status"] != "COMPLETE" or len(receipt["measurements"]) != 610 or
            receipt["block_variant_runs"] != 610):
            raise ValueError(f"{name} archive or ledger mismatch")
        if not np.isfinite(archive["embeddings"]).all():
            raise ValueError(f"{name} latent nonfinite")
    checked = 0
    for i, ci in enumerate(ids):
        row = curator["records"][i]
        if (row["array_row"] != i or row["candidate_index"] != ci or
            row["native_sample_rate_hz"] != 250 or
            row["native_end_sample_exclusive"] - row["native_start_sample"] != 7500 or
            row["source_gaps"] or row["native_array_sha256"] != array_digest(native["samples_uv"][i]) or
            row["valid_mask_sha256"] != array_digest(native["valid"][i]) or
            row["prepared_array_sha256"] != pretrained_study.array_hash(prepared["patches"][i])):
            raise ValueError(f"native/prepared row identity mismatch: {i}/{ci}")
        for j, variant in enumerate(PREPARED_VARIANTS):
            x = pretrained_study.waveform_variant(prepared["patches"][i], variant, 9009 + ci)
            input_hash = pretrained_study.array_hash(x)
            for name in MODELS:
                measurement = receipts[name]["measurements"][5*i+j]
                checked_measurement(measurement, ci, variant, input_hash,
                                    pretrained_study.array_hash(encoders[name]["embeddings"][i, j]))
            checked += 1
    return dict(source=source, protocol=protocol, native=native, prepared=prepared,
                encoders=encoders, receipts=receipts, curator=curator, selected=selected,
                verified_prepared_pairs=checked, verified_inference_outputs=2*checked)


def native_variant(samples, valid, name, candidate_index):
    """Return one fixed numeric control, mask, detector kwargs and provenance."""
    x = np.asarray(samples, dtype=np.float64)
    mask = np.asarray(valid, dtype=bool)
    if x.shape != (4, 7500) or mask.shape != x.shape or not np.isfinite(x[mask]).all():
        raise ValueError("native variant input contract")
    y, m = x.copy(), mask.copy()
    config, transform = {}, {"name": name, "source_rate_hz": 250, "clock_origin_seconds": 0.0}
    if name == "primary":
        pass
    elif name == "gain_x2": y *= 2
    elif name == "polarity_xneg1": y *= -1
    elif name == "additive_offset_50uv": y[mask] += 50
    elif name == "smoothing_21ms": config["smoothing_ms"] = 21
    elif name == "smoothing_51ms": config["smoothing_ms"] = 51
    elif name == "passband_0p5_40": config["passband_hz"] = (.5, 40.)
    elif name == "passband_1_30": config["passband_hz"] = (1., 30.)
    elif name == "notch_50hz": config["notch_hz"] = 50.
    elif name == "notch_60hz": config["notch_hz"] = 60.
    elif name in ("add_50hz", "add_60hz"):
        hz = 50 if name == "add_50hz" else 60
        y += 10 * np.sin(2*np.pi*hz*np.arange(7500, dtype=np.float64)/250)[None, :]
        transform.update(sinusoid_hz=hz, amplitude_uv=10., phase_at_block_start=0.)
    elif name == "common_mean_reference":
        common = np.all(mask, axis=0)
        m = np.broadcast_to(common, x.shape).copy()
        y = np.zeros_like(x)
        y[:, common] = x[:, common] - np.mean(x[:, common], axis=0)
        transform["mask_rule"] = "AND of four original contact masks"
    elif name == "spike_100uv_8ms":
        t = np.arange(7500, dtype=np.float64)/250
        y += (100*np.exp(-.5*((t-15)/.008)**2))[None, :]
        transform.update(center_seconds=15., sigma_seconds=.008, amplitude_uv=100.)
    elif name == "symmetric_clipping_50uv":
        transform["clipped_sample_count"] = int(np.count_nonzero(mask & (np.abs(x) > 50)))
        y = np.clip(x, -50, 50)
    elif name in ("independent_phase", "shared_phase"):
        if not m.all():
            raise ValueError("INVALID_PHASE_INPUT")
        transform.update(seed=12012+candidate_index, phase_source_sha256=
                         "f0c7c3dbf47f819aed52216369a7878cdf792b305999759704a86bcc3615bf0d")
        y = transitions.phase_surrogate(x, seed=12012+candidate_index,
                                        shared_phase=name == "shared_phase")
    elif name == "shift_plus_200ms":
        y = np.zeros_like(x)
        m = np.zeros_like(mask)
        y[:, 50:] = x[:, :-50]
        m[:, 50:] = mask[:, :-50]
        transform.update(shift_samples=50, shift_seconds=.2, dropped_source_samples=[7450, 7500],
                         invalid_destination_samples=[0, 50], mapping="destination_sample=source_sample+50; no wrap")
    else:
        raise ValueError("undeclared native variant")
    y[~m] = 0
    transform.update(array_sha256=pretrained_study.array_hash(y), array_bytes_sha256=array_digest(y),
                     dtype=str(y.dtype), shape=list(y.shape), mask_sha256=array_digest(m),
                     valid_runs=[wave._runs(channel) for channel in m])
    return y, m, config, transform


def raw_intervals(result, channel):
    return [(r["start_sample"]/result["sample_rate_hz"], r["end_sample"]/result["sample_rate_hz"])
            for r in result["runs"] if r["channel_key"] == f"channel_{channel}"]


def guarded_intervals(result, channel, method="waveform"):
    fs = result["sample_rate_hz"]
    intervals = []
    for run in result["runs"]:
        if run["channel_key"] != f"channel_{channel}" or run["status"] != "OK":
            continue
        if method == "waveform":
            guard = run["guard_samples"]
        else:
            if run.get("oscillation_status", {}).get(method) != "OK" or method not in result["filters"]:
                continue
            guard = result["filters"][method]["guard_samples"]
        a = run["clock_start_seconds"] + (run["start_sample"]-run["segment_start_sample"]+guard)/fs
        b = run["clock_start_seconds"] + (run["end_sample"]-run["segment_start_sample"]-guard)/fs
        if a < b:
            intervals.append((a, b))
    return intervals


def intersections(a, b):
    return [(max(x, u), min(y, v)) for x, y in a for u, v in b if max(x, u) < min(y, v)]


def duration(intervals):
    return float(sum(b-a for a, b in intervals))


def aligned_rows(events, variant):
    """Comparison-only copies; emitted rows and integer indices remain intact."""
    rows = []
    for source in events:
        row = source.copy()
        if variant == "shift_plus_200ms":
            for key in ("seconds", "fractional_index", "support_start_seconds", "support_end_seconds",
                        "interval_end_seconds"):
                if row.get(key) is not None:
                    row[key] -= 50 if key == "fractional_index" else .2
        if variant == "polarity_xneg1":
            row["polarity"] = {"peak": "trough", "trough": "peak"}.get(row.get("polarity"), row.get("polarity"))
            direction = row.get("direction")
            if direction:
                row["direction"] = (direction.replace("positive_to_negative", "TEMP")
                                    .replace("negative_to_positive", "positive_to_negative")
                                    .replace("TEMP", "negative_to_positive"))
        rows.append(row)
    return rows


def native_matches(primary, variant_result, variant_name):
    shift = .2 if variant_name == "shift_plus_200ms" else 0.
    matches, timelines = [], []
    for channel in range(4):
        raw_a = raw_intervals(primary, channel)
        raw_b = [(a-shift, b-shift) for a, b in raw_intervals(variant_result, channel)]
        guard_a = guarded_intervals(primary, channel)
        guard_b = [(a-shift, b-shift) for a, b in guarded_intervals(variant_result, channel)]
        common = intersections(guard_a, guard_b)
        timelines.append(dict(channel=channel, raw_valid_overlap_seconds=duration(intersections(raw_a, raw_b)),
                              primary_raw_intervals=raw_a, variant_raw_intervals_aligned=raw_b,
                              primary_guarded_intervals=guard_a, variant_guarded_intervals_aligned=guard_b,
                              common_guarded_intervals=common, common_duration_seconds=duration(common),
                              clock_error_bound_seconds=0.0,
                              clock_mapping="subtract 0.2 s from shifted comparison fields" if shift else "identical block clock"))
        a = [r for r in primary["events"] if r["channel_key"] == f"channel_{channel}" and
             r["accepted"] and r["family"] in ("extremum", "inflection")]
        b = aligned_rows([r for r in variant_result["events"] if
                          r["channel_key"] == f"channel_{channel}" and r["accepted"] and
                          r["family"] in ("extremum", "inflection")], variant_name)
        def key(row):
            return row["family"], row.get("polarity"), row.get("direction")
        unexpected = (set(map(key, a)) | set(map(key, b))) - set(MATCH_STRATA)
        if unexpected:
            raise ValueError(f"unregistered landmark stratum: {unexpected}")
        for family, polarity, direction in MATCH_STRATA:
            aa = [r for r in a if key(r) == (family, polarity, direction)]
            bb = [r for r in b if key(r) == (family, polarity, direction)]
            for tolerance in (.010, .025, .050):
                result = wave.match_events(aa, bb, intervals_a_seconds=guard_a,
                                           intervals_b_seconds=guard_b, shared_clock=True,
                                           clock_error_bound_seconds=0., tolerance_seconds=tolerance)
                matches.append(dict(channel=channel, family=family, polarity=polarity,
                                    direction=direction, tolerance_seconds=tolerance,
                                    accepted_a_before_guard=len(aa), accepted_b_before_guard=len(bb),
                                    **result))
    return timelines, matches


COMPONENTS = (("extremum", "peak"), ("extremum", "trough"),
              ("inflection", "curvature_positive_to_negative"),
              ("inflection", "curvature_negative_to_positive"))


def event_counts(result):
    """Return all 30 integer bins, with eligibility fixed by guarded timelines."""
    if result["sample_rate_hz"] != 200:
        raise ValueError("prepared event rate mismatch")
    counts = np.zeros((30, 16), dtype=np.int64)
    for row in result["events"]:
        if not row["accepted"] or row["family"] not in ("extremum", "inflection"):
            continue
        index = row["index"]
        if not isinstance(index, int) or not 0 <= index < 6000:
            raise ValueError("accepted event index outside prepared block")
        label = row["polarity"] if row["family"] == "extremum" else row["direction"]
        component = COMPONENTS.index((row["family"], label))
        channel = int(row["channel_key"].removeprefix("channel_"))
        counts[index//200, 4*channel+component] += 1
    intervals = [guarded_intervals(result, ch) for ch in range(4)]
    eligible = [k for k in range(30) if all(any(a <= k and k+1 <= b for a, b in channel)
                                            for channel in intervals)]
    return counts, eligible


def support_indices(original, phase, other=None):
    base = set(original) & set(phase) & set(range(1, 29))
    if other is not None:
        base &= set(other)
    indices = sorted(base)
    pairs = [(a, b) for a, b in zip(indices, indices[1:]) if b == a+1]
    return indices, pairs


def _cosine_pairs(vectors, pairs):
    x = np.asarray(vectors, dtype=np.float64)
    if not np.isfinite(x).all():
        return None, "NONFINITE_VECTOR"
    norms = np.linalg.norm(x, axis=1)
    if np.any(norms == 0) or not np.isfinite(norms).all():
        return None, "ZERO_NORM_VECTOR"
    unit = x / norms[:, None]
    values = np.array([1-float(np.dot(unit[i], unit[j])) for i, j in pairs], dtype=np.float64)
    if not np.isfinite(values).all():
        return None, "NONFINITE_DISTANCE_VECTOR"
    scale = max(1., float(np.max(np.abs(values)))) if len(values) else 1.
    if len(values) == 0 or float(np.ptp(values)) <= COSINE_CONSTANT_ULPS*np.finfo(np.float64).eps*scale:
        return None, "CONSTANT_DISTANCE_VECTOR"
    return values, None


def metric_result(counts, embedding, indices, adjacent, metric):
    if metric not in METRICS:
        raise ValueError("unregistered metric")
    if len(indices) < 8 and metric == "geometry":
        return dict(status="NOT_ESTIMABLE", rho=None, reason="INSUFFICIENT_GEOMETRY_INTERVALS")
    if len(adjacent) < 7 and metric == "change":
        return dict(status="NOT_ESTIMABLE", rho=None, reason="INSUFFICIENT_ADJACENT_PAIRS")
    required = indices if metric == "geometry" else sorted(set(k for pair in adjacent for k in pair))
    if counts.shape != (30, 16) or embedding.shape != (30, 200):
        return dict(status="NOT_ESTIMABLE", rho=None, reason="VECTOR_SHAPE_MISMATCH")
    positions = {index: i for i, index in enumerate(required)}
    pairs = ([(i, j) for i in range(len(required)) for j in range(i+1, len(required))]
             if metric == "geometry" else [(positions[a], positions[b]) for a, b in adjacent])
    left, lr = _cosine_pairs(counts[required], pairs)
    right, rr = _cosine_pairs(embedding[required], pairs)
    if lr or rr:
        return dict(status="NOT_ESTIMABLE", rho=None, reason=("EVENT_"+lr if lr else "MODEL_"+rr))
    a, b = rankdata(left, method="average"), rankdata(right, method="average")
    rho = float(np.corrcoef(a, b)[0, 1])
    if not np.isfinite(rho):
        return dict(status="NOT_ESTIMABLE", rho=None, reason="UNDEFINED_CORRELATION")
    return dict(status="ESTIMABLE", rho=rho, reason=None)


def exact_signflip(effects):
    values = np.asarray(effects, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("finite person effects required")
    if len(values) < 2:
        return dict(status="NOT_ESTIMABLE", reason="FEWER_THAN_TWO_COMPLETE_PEOPLE",
                    n=int(len(values)), observed_mean=None, assignments=0, extreme_count=None,
                    p_two_sided=None, p_bonferroni_four=None)
    observed = float(np.mean(values))
    signed = [float(np.mean(values*np.array(signs, dtype=np.float64)))
              for signs in product((-1., 1.), repeat=len(values))]
    extreme = sum(abs(value) >= abs(observed)-1e-12 for value in signed)
    p = extreme/len(signed)
    return dict(status="COMPARED", reason=None, n=len(values), observed_mean=observed,
                assignments=len(signed), extreme_count=extreme,
                p_two_sided=p, p_bonferroni_four=min(1., 4*p))


def prepared_comparisons(results, embeddings):
    """Fixed support precedes metric values and is common to both encoders."""
    counts, eligible = {}, {}
    for name in PREPARED_VARIANTS:
        counts[name], eligible[name] = event_counts(results[name])
    primary_k, primary_pairs = support_indices(eligible["original"], eligible["independent_phase"])
    supports, rows, effects = {}, [], []
    for name in PREPARED_VARIANTS:
        k, pairs = (primary_k, primary_pairs) if name in ("original", "independent_phase") else \
            support_indices(eligible["original"], eligible["independent_phase"], eligible[name])
        supports[name] = dict(interval_indices=k, adjacent_pairs=pairs,
                              all_channel_eligible_intervals=eligible[name])
        j = PREPARED_VARIANTS.index(name)
        for model in MODELS:
            latent = np.mean(embeddings[model][j], axis=0, dtype=np.float64)
            for metric in METRICS:
                value = metric_result(counts[name], latent, k, pairs, metric)
                rows.append(dict(model=model, variant=name, metric=metric, support=supports[name], **value))
    by_key = {(r["model"], r["variant"], r["metric"]): r for r in rows}
    for model in MODELS:
        for metric in METRICS:
            original = by_key[model, "original", metric]
            phase = by_key[model, "independent_phase", metric]
            reason = None
            if original["rho"] is None or phase["rho"] is None:
                reason = ";".join(f"{v}:{row['reason']}" for v, row in
                                  (("original", original), ("independent_phase", phase)) if row["rho"] is None)
            effects.append(dict(model=model, metric=metric, original_rho=original["rho"],
                                independent_phase_rho=phase["rho"],
                                effect=None if reason else original["rho"]-phase["rho"], reason=reason))
    return counts, supports, rows, effects


def aggregate_effects(block_rows, selected):
    """Join curator identities only after every numerical block effect exists."""
    if len(selected) != 122 or len(block_rows) != 122*4:
        raise ValueError("all 122 numerical blocks and four endpoints required")
    ids = [r["candidate_index"] for r in selected]
    by_key = {(r["candidate_index"], r["model"], r["metric"]): r for r in block_rows}
    if len(by_key) != len(block_rows) or set(k[0] for k in by_key) != set(ids):
        raise ValueError("block effect identity mismatch")
    output = []
    for model in MODELS:
        for metric in METRICS:
            recording_groups = defaultdict(list)
            for selected_row in selected:
                key = (selected_row["source_subject"], selected_row["session"], selected_row["recording_id"])
                recording_groups[key].append((selected_row["candidate_index"],
                                             by_key[selected_row["candidate_index"], model, metric]))
            records = []
            for (person, night, rec), entries in sorted(recording_groups.items()):
                valid = [r["effect"] for _, r in entries if r["effect"] is not None]
                status = "VALID" if len(valid) >= 3 else "TOO_FEW_PAIRED_BLOCKS"
                records.append(dict(person=person, night=night, recording_id=rec,
                                    selected_blocks=len(entries), paired_valid_blocks=len(valid),
                                    excluded=[dict(candidate_index=ci, reason=r["reason"]) for ci, r in entries
                                              if r["effect"] is None], status=status,
                                    median_effect=float(np.median(valid)) if status == "VALID" else None))
            by_person = defaultdict(dict)
            for row in records:
                by_person[row["person"]][row["night"]] = row
            people = []
            for person, nights in sorted(by_person.items()):
                complete = all(n in nights and nights[n]["status"] == "VALID" for n in ("001", "002"))
                people.append(dict(person=person, status="COMPLETE" if complete else "INCOMPLETE_NIGHTS",
                                   night_medians={n: nights[n]["median_effect"] if n in nights else None
                                                  for n in ("001", "002")},
                                   reasons=[] if complete else [f"{n}:{nights[n]['status'] if n in nights else 'MISSING'}"
                                                                    for n in ("001", "002")
                                                                    if n not in nights or nights[n]["status"] != "VALID"],
                                   effect=(nights["001"]["median_effect"]+nights["002"]["median_effect"])/2
                                   if complete else None))
            test = exact_signflip([p["effect"] for p in people if p["status"] == "COMPLETE"])
            output.append(dict(model=model, metric=metric, selected_blocks=122,
                               paired_valid_blocks=sum(r["paired_valid_blocks"] for r in records),
                               records=records, participants=people, test=test))
    return output


def morphology_groups(result):
    """Block-level accepted rows and unique-run exposure by method/group."""
    groups = defaultdict(lambda: {"events": [], "exposure_seconds": 0.})
    methods = [("extremum", None, None, "waveform"), ("inflection", None, None, "waveform")]
    for band in wave.BANDS:
        label = f"{int(band[0])}-{int(band[1])}Hz"
        methods += [("cycle", list(band), "trough_to_trough", f"cycle:{label}"),
                    ("burst", list(band), "cycle_contiguity", f"cycle:{label}"),
                    ("burst", list(band), "envelope_dual_threshold", f"envelope:{label}")]
    for channel in range(4):
        for family, band, definition, method in methods:
            key = (channel, family, tuple(band) if band else None, definition)
            groups[key]["exposure_seconds"] = duration(guarded_intervals(result, channel, method))
    for row in result["events"]:
        if row["accepted"]:
            key = (int(row["channel_key"].removeprefix("channel_")), row["family"],
                   tuple(row["band_hz"]) if row.get("band_hz") else None, row.get("definition"))
            if key not in groups:
                raise ValueError("accepted morphology row has no declared exposure group")
            groups[key]["events"].append(row)
    return groups


def morphology_summary(groups):
    rows = []
    fields = ("amplitude_uv", "slope_magnitude_uv_per_second",
              "curvature_magnitude_uv_per_second2", "period_seconds",
              "rise_fraction", "peak_fraction", "burst_duration_seconds")
    for (channel, family, band, definition), group in sorted(groups.items(), key=lambda x: str(x[0])):
        events = group.get("events", [])
        seconds = float(group["exposure_seconds"])
        distributions = {}
        for field in fields:
            values = group["values"][field] if "values" in group else [
                value for row in events if (value := morphology_value(row, field)) is not None]
            distributions[field] = dict(n=len(values), q10=None, q50=None, q90=None)
            if values:
                q = np.quantile(values, [.1, .5, .9], method="linear")
                distributions[field].update(q10=float(q[0]), q50=float(q[1]), q90=float(q[2]))
        rows.append(dict(channel=channel, family=family, band_hz=list(band) if band else None,
                         definition=definition, accepted_count=group.get("accepted_count", len(events)),
                         guarded_seconds=seconds,
                         rate_per_guarded_minute=group.get("accepted_count", len(events))*60/seconds if seconds > 0 else None,
                         distributions=distributions))
    return rows


def morphology_value(row, field):
    if field == "slope_magnitude_uv_per_second":
        value = row.get("slope_uv_per_second")
        value = abs(value) if value is not None else None
    elif field == "curvature_magnitude_uv_per_second2":
        value = row.get("curvature_uv_per_second2")
        value = abs(value) if value is not None else None
    elif field == "burst_duration_seconds":
        value = (row["interval_end_seconds"]-row["seconds"]
                 if row["family"] == "burst" and row.get("interval_end_seconds") is not None else None)
    else:
        value = row.get(field)
    return float(value) if value is not None and np.isfinite(value) else None


def combine_morphology(selected, primary_loader):
    """Stream one recording at a time; retain scalar values, never event dictionaries."""
    fields = ("amplitude_uv", "slope_magnitude_uv_per_second",
              "curvature_magnitude_uv_per_second2", "period_seconds",
              "rise_fraction", "peak_fraction", "burst_duration_seconds")
    by_record = defaultdict(list)
    for row in selected:
        rec = (row["source_subject"], row["session"], row["recording_id"])
        by_record[rec].append(row)
    night_rows = []
    for (person, night, rec), selected_rows in sorted(by_record.items()):
        groups = defaultdict(lambda: {"accepted_count": 0, "exposure_seconds": 0.,
                                      "values": {field: [] for field in fields}})
        for selected_row in selected_rows:
            result = primary_loader(selected_row["array_row"])
            for key, group in morphology_groups(result).items():
                target = groups[key]
                target["accepted_count"] += len(group["events"])
                target["exposure_seconds"] += group["exposure_seconds"]
                for event in group["events"]:
                    for field in fields:
                        value = morphology_value(event, field)
                        if value is not None:
                            target["values"][field].append(value)
            del result
        for row in morphology_summary(groups):
            night_rows.append(dict(person=person, night=night, recording_id=rec, **row))
        del groups
    by_key = defaultdict(dict)
    for row in night_rows:
        key = (row["person"], row["channel"], row["family"],
               tuple(row["band_hz"]) if row["band_hz"] else None, row["definition"])
        by_key[key][row["night"]] = row
    differences = []
    for (person, channel, family, band, definition), nights in sorted(by_key.items(), key=lambda x: str(x[0])):
        if set(nights) != {"001", "002"}:
            raise ValueError("missing night morphology summary")
        a, b = nights["001"], nights["002"]
        def diff(x, y):
            return None if x is None or y is None else y-x
        differences.append(dict(person=person, channel=channel, family=family,
                                band_hz=list(band) if band else None, definition=definition,
                                nights={"001": a, "002": b},
                                accepted_count_difference=b["accepted_count"]-a["accepted_count"],
                                guarded_seconds_difference=b["guarded_seconds"]-a["guarded_seconds"],
                                rate_difference=diff(a["rate_per_guarded_minute"], b["rate_per_guarded_minute"]),
                                distribution_differences={field: {q: diff(a["distributions"][field][q],
                                                                        b["distributions"][field][q])
                                                             for q in ("q10", "q50", "q90")}
                                                          for field in a["distributions"]}))
    return night_rows, differences
