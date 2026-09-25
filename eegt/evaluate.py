"""Descriptive numerical battery. Group metadata is used only in evaluation."""
import itertools
import json
import time
import platform
import resource
import numpy as np
from sklearn.metrics import adjusted_rand_score, adjusted_mutual_info_score
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from .acquire import ROOT, digest
from .artifacts import verify_prepared_inputs, RECEIPT
from .model import Tokenizer
from .signal import features, normalized_waves, surrogate


def agreement(a, b):
    if len(a) < 2:
        return dict(n=int(len(a)), ari=None, ami=None)
    return dict(n=int(len(a)), ari=float(adjusted_rand_score(a, b)),
                ami=float(adjusted_mutual_info_score(a, b)))


def occupancy(labels, k):
    counts = np.bincount(labels, minlength=k)
    if not counts.sum():
        return dict(occupied=0, effective_vocabulary=0, largest_token_fraction=None)
    p = counts[counts > 0] / counts.sum()
    return dict(occupied=int(np.count_nonzero(counts)), effective_vocabulary=float(np.exp(-(p * np.log(p)).sum())),
                largest_token_fraction=float(p.max()))


def ratio_mse(target, reconstructed, baseline):
    denominator = np.mean((target - baseline) ** 2)
    return float(np.mean((target - reconstructed) ** 2) / denominator) if denominator > 0 else None


def run():
    started = time.monotonic()
    out = ROOT / "results/002"
    if (out / "metrics.json").exists():
        raise ValueError("metrics already exist; use a fresh version/directory for a different experiment")
    prepared_hashes = verify_prepared_inputs(ROOT)
    p = json.loads((ROOT / "protocol/experiment-002.json").read_text())
    qc = json.loads((out / "qc.json").read_text())
    if qc["protocol_sha256"] != digest(ROOT / "protocol/experiment-002.json"):
        raise ValueError("QC/protocol identity mismatch")
    with np.load(ROOT / "data/derived/analysis-waves.npz", allow_pickle=False) as d:
        waves = d["samples_uv"].astype(float)
        window_index = d["window_index"]
    with np.load(out / "evaluation-index.npz", allow_pickle=False) as d:
        evaluation_window_index = d["window_index"]
        group = d["recording_index"]
        split = d["split"]
    if (window_index.ndim != 1 or evaluation_window_index.ndim != 1 or
            not np.array_equal(window_index, evaluation_window_index) or
            len(np.unique(window_index)) != len(window_index)):
        raise ValueError("waveform/evaluation window identity mismatch")
    if len(waves) != len(group) or len(split) != len(waves) or len(waves) != qc["qc_pass"]:
        raise ValueError("common observation alignment mismatch")
    train = split == "train"
    if train.sum() < 100 or not np.any(split == "test") or not np.any(split == "external"):
        raise ValueError("insufficient frozen fit/test groups")
    group_splits = {int(g): set(split[group == g]) for g in np.unique(group)}
    if any(len(s) != 1 for s in group_splits.values()):
        raise ValueError("recording leaks across fit/evaluation split")
    target_wave = normalized_waves(waves)
    spectrum_scaler = StandardScaler().fit(features(waves[train], "spectrum"))
    target_spectrum = spectrum_scaler.transform(features(waves, "spectrum"))
    mean_wave = target_wave[train].mean(axis=0)
    mean_spectrum = target_spectrum[train].mean(axis=0)
    masks = {name: split == name for name in ["train", "validation", "test", "external"]}
    masks.update({f"r{g+1:03}": group == g for g in np.unique(group)})
    total_by_mask = {name: sum(r["total_windows"] for r in qc["records"] if
                    (r["split"] == name if name in ["train", "validation", "test", "external"] else r["recording"] == name))
                    for name in masks}
    models, predictions, accepted, model_arrays, comparisons, controls = {}, {}, {}, {}, [], []
    metrics = []
    for method, k, seed in itertools.product(p["methods"], p["vocabulary_sizes"], p["seeds"]):
        key = f"{method}-k{k}-s{seed}"
        tick = time.monotonic()
        # No provenance table or metadata is passed to fitting or prediction.
        model = Tokenizer(method, k, seed).fit(waves[train])
        labels, accept, distances = model.predict(waves)
        predictions[key], accepted[key], models[key] = labels, accept, model
        for name, a in model.export_arrays().items():
            model_arrays[key + "__" + name] = a
        train_labels = labels[train]
        centers_wave = np.stack([target_wave[train][train_labels == t].mean(axis=0)
                                if np.any(train_labels == t) else mean_wave for t in range(k)])
        centers_spectrum = np.stack([target_spectrum[train][train_labels == t].mean(axis=0)
                                    if np.any(train_labels == t) else mean_spectrum for t in range(k)])
        model_arrays[key + "__wave_reconstruction"] = centers_wave
        model_arrays[key + "__spectrum_reconstruction"] = centers_spectrum
        rows = []
        for name, mask in masks.items():
            n = int(mask.sum())
            if not n:
                rows.append(dict(group=name, total_windows=total_by_mask[name], qc_pass=0, accepted=0))
                continue
            rows.append(dict(group=name, total_windows=total_by_mask[name], qc_pass=n,
                             accepted=int(accept[mask].sum()), ood=int((~accept[mask]).sum()),
                             coverage_total=float(accept[mask].sum() / total_by_mask[name]),
                             coverage_qc_pass=float(accept[mask].mean()),
                             assignment_occupancy=occupancy(labels[mask], k),
                             accepted_occupancy=occupancy(labels[mask & accept], k),
                             normalized_wave_mse_ratio_k1=ratio_mse(target_wave[mask], centers_wave[labels[mask]], mean_wave),
                             standardized_spectrum_mse_ratio_k1=ratio_mse(target_spectrum[mask], centers_spectrum[labels[mask]], mean_spectrum)))
        metrics.append(dict(model=key, method=method, k=k, seed=seed, ood_threshold=model.ood_threshold,
                            fit_iterations=int(model.clusterer.n_iter_), groups=rows))
        print(json.dumps(dict(model=key, state="fitted", seconds=round(time.monotonic()-tick, 3))), flush=True)
    # Matched family/seed and within-family seed comparisons. Raw integer IDs
    # never need a mapping for ARI/AMI; masks are the exact common observations.
    pairs = []
    for k, seed in itertools.product(p["vocabulary_sizes"], p["seeds"]):
        pairs.extend((f"{a}-k{k}-s{seed}", f"{b}-k{k}-s{seed}", "cross_method")
                     for a, b in itertools.combinations(p["methods"], 2))
    for method, k in itertools.product(p["methods"], p["vocabulary_sizes"]):
        pairs.extend((f"{method}-k{k}-s{a}", f"{method}-k{k}-s{b}", "seed_stability")
                     for a, b in itertools.combinations(p["seeds"], 2))
    for a, b, kind in pairs:
        for name, mask in masks.items():
            if name in ["train", "validation"]:
                continue
            intersection = mask & accepted[a] & accepted[b]
            comparisons.append(dict(kind=kind, a=a, b=b, group=name,
                all_qc_pass=agreement(predictions[a][mask], predictions[b][mask]),
                accepted_intersection=agreement(predictions[a][intersection], predictions[b][intersection]),
                intersection_over_qc_pass=float(intersection.sum()/mask.sum()) if mask.sum() else None))
    # Prespecified primary setting controls, transformations after preprocessing.
    evaluate_mask = (split == "test") | (split == "external")
    panel = waves[evaluate_mask]
    control_group = group[evaluate_mask]
    for kind in ["sample_shuffle", "phase_randomized"]:
        transformed = surrogate(panel, kind)
        for method in p["methods"]:
            key = f"{method}-k16-s17"
            labels, accept, _ = models[key].predict(transformed)
            original = predictions[key][evaluate_mask]
            for g in np.unique(control_group):
                mask = control_group == g
                controls.append(dict(control=kind, model=key, group=f"r{g+1:03}",
                    comparison=agreement(original[mask], labels[mask]),
                    same_id_fraction=float((original[mask] == labels[mask]).mean()),
                    surrogate_accepted=int(accept[mask].sum()), denominator=int(mask.sum())))
    rng = np.random.default_rng(9001)
    nulls = []
    for a, b in itertools.combinations(p["methods"], 2):
        for name in ["test", "external"]:
            mask = masks[name]
            aa, bb = predictions[f"{a}-k16-s17"][mask], predictions[f"{b}-k16-s17"][mask]
            values = [adjusted_rand_score(aa, rng.permutation(bb)) for _ in range(100)]
            nulls.append(dict(a=a, b=b, group=name, n=int(mask.sum()), repeats=100,
                              observed_ari=float(adjusted_rand_score(aa, bb)),
                              null_ari_median=float(np.median(values)),
                              null_ari_95_interval=[float(v) for v in np.quantile(values, [.025, .975])],
                              note="label-permutation scale check, not a participant-level significance test"))
    np.savez_compressed(out / "assignments.npz", window_index=window_index,
                        **{k: v.astype("int16") for k, v in predictions.items()},
                        **{k + "__accepted": v for k, v in accepted.items()})
    model_arrays.update(common_spectrum_mean=spectrum_scaler.mean_, common_spectrum_std=spectrum_scaler.scale_)
    np.savez_compressed(out / "models.npz", **model_arrays)
    source_hashes = {str(f.relative_to(ROOT)): digest(f) for folder in ["eegt", "protocol"]
                     for f in sorted((ROOT / folder).glob("*")) if f.is_file()}
    receipt = dict(schema="eegt-results/v2", experiment="002", status="computed_pending_review",
                   protocol_sha256=digest(ROOT / "protocol/experiment-002.json"),
                   analysis_waves_sha256=digest(ROOT / "data/derived/analysis-waves.npz"),
                   prepared_inputs_sha256=digest(ROOT / RECEIPT), prepared_input_hashes=prepared_hashes,
                   source_hashes=source_hashes, qc=qc, models=metrics, agreements=comparisons,
                   controls=controls, permutation_nulls=nulls,
                   timing_seconds=float(time.monotonic()-started), python=platform.python_version(),
                   platform=platform.platform(), peak_rss_native=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
                   interpretation="Descriptive LLM-authored numeric model comparison; no universal or semantic meaning established.")
    (out / "metrics.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(state="computed_pending_review", models=len(metrics), windows=len(waves),
                          seconds=receipt["timing_seconds"])), flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        run()
