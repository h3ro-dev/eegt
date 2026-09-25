"""Generate the public note and graphic directly from immutable numeric results."""
import itertools
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
x = json.loads((ROOT / "results/002/metrics.json").read_text())
primary = [m for m in x["models"] if m["k"] == 16 and m["seed"] == 17]
names = {"spectrum": "Spectrum", "waveform": "Waveform", "time_frequency": "Time-frequency"}
q = x["qc"]
rows = []
for m in primary:
    for g in m["groups"]:
        if g["group"] in ("test", "external"):
            rows.append(f"| {names[m['method']]} | {g['group']} | {g['accepted']:,}/{g['total_windows']:,} | "
                        f"{100*g['coverage_total']:.2f}% | {g['assignment_occupancy']['effective_vocabulary']:.2f}/16 | "
                        f"{g['normalized_wave_mse_ratio_k1']:.3f} | {g['standardized_spectrum_mse_ratio_k1']:.3f} |")
comparisons = [a for a in x["agreements"] if a["kind"] == "cross_method" and "-k16-s17" in a["a"]
               and a["group"] in ["test", "external"]]
agree_rows = [f"| {a['a'].split('-k')[0]} / {a['b'].split('-k')[0]} | {a['group']} | "
              f"{a['all_qc_pass']['n']:,} | {a['all_qc_pass']['ari']:.4f} | {a['all_qc_pass']['ami']:.4f} | "
              f"{a['accepted_intersection']['n']:,} | {a['accepted_intersection']['ari']:.4f} |" for a in comparisons]
stability = []
for method in names:
    for group in ["test", "external"]:
        vals = [a["all_qc_pass"]["ari"] for a in x["agreements"] if a["kind"] == "seed_stability" and
                a["a"].startswith(method + "-k16-") and a["group"] == group]
        stability.append(f"| {names[method]} | {group} | {min(vals):.4f}–{max(vals):.4f} |")
note = f"""# Research Notes · Experiment 002

Date: 2026-09-24. State: computed and reproduced; independent review/publication receipts are separate artifacts. Protocol frozen before wave inspection/fitting; one prefit filter-padding clarification is recorded. Scope: anonymous numerical around-ear EEG pattern comparison.

## Finding

The three representations find different partitions of the waves. Spectrum and time-frequency agree more than either agrees with phase-sensitive waveform shape. High assignment coverage alone does not establish universal or useful tokens. These are LLM-authored numerical models, not an experiment claiming independent discovery by different pretrained LLMs.

The primary setting was K=16/seed17 before fitting. On the external source, spectrum/time-frequency ARI is **0.2894**, spectrum/waveform **0.0387**, and waveform/time-frequency **0.0189** across the same **7,938 QC-passing windows**. ARI=1 is an identical partition after token renaming; near zero is chance-level partition agreement under this statistic. These numbers are descriptive, not a population test.

## Inputs and denominators

Eight fixed-selected CC0 around-ear recordings from two OpenNeuro sources; 2,769,602,360 downloaded source bytes; 80 recording-minutes analyzed. The native acquisition is 500 Hz ×18 channels in six recordings, and 250 Hz ×15/12 EEG channels in two recordings. These are cEEGrid sources, not Neurable headset captures. Neurable compatibility currently means the tested 12-channel/500 Hz decoded-array interface, not validated physical transfer.

There are **{q['total_windows']:,} two-second channel windows**, of which **{q['qc_pass']:,} pass** engineering QC and **{q['qc_abstain']:,} abstain**. Simultaneous channels and repeated windows are not independent people. ADC clipping rails are unknown. No sleep/task/clinical annotations, personal history or source identity enters model fitting.

Three participants teach the models; one supplies validation reporting; two different participants test same-source behavior; two from the other source test external behavior. There is no model selection from the validation/test outputs. Source public IDs define grouping; real-person overlap across source collections is not known.

## Coverage, occupancy and distortion

Coverage denominator includes withheld QC windows. Effective vocabulary is exp(entropy) over all QC-passing assignments, so a concentrated 16-code model can behave like far fewer equally used codes. Distortion ratios compare to a training-mean K=1 baseline on the same observations; lower is better for that numerical target. All raw assignments, including OOD assignments, enter these distortion and occupancy measurements.

| Method | Group | Accepted/all windows | Coverage | Effective vocabulary | Wave distortion/K1 | Spectrum distortion/K1 |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

The external waveform model's effective vocabulary is only **4.72/16** despite 97.35% overall coverage. Spectrum models compress spectral structure better; the waveform model compresses normalized waveform shape better. That is consistent with their different objectives, not evidence of one common natural alphabet.

## Agreement on common observations

| Pair | Group | All QC-pass N | ARI | AMI | Both accepted N | ARI on intersection |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(agree_rows)}

## Variation across seeds

All three seed pairings at K=16 are included below. Complete K=8/16/32 results and per-recording comparisons are in metrics.json; no best seed was selected.

| Method | Group | Seed-pair ARI range |
|---|---|---:|
{chr(10).join(stability)}

## Controls and reproducibility

Within-window sample permutation and Fourier phase randomization were run at the primary setting, with per-recording outcomes in metrics.json. Phase randomization preserves the unwindowed FFT magnitude; subsequent Hann-window estimates may differ. One hundred random label permutations per primary pair provide a numerical null scale, not a participant-level significance test. Common-target K=1 distortion is reported above.

A separate copied package repeated all 27 fits. Assignment and model NPZ archives were byte-identical, and all numerical metrics, QC, controls and nulls matched. Runtime and peak RSS are not equality targets. The released full fit/evaluation took {x['timing_seconds']:.2f} seconds on the recorded one-thread environment. See reproduction.json and the resource receipt for its scope; this is a repeat on the same platform, not an outside replication.

Independent review found that the original evaluator could accept a same-length, reordered evaluation index. The saved run itself was aligned. Before publication, we added digest binding and matching window IDs before any fit, regenerated the run and verified that every numerical result was unchanged. The original finding and repair are retained in the [prepublication amendment](../protocol/amendment-002.md) and [numerical equivalence receipt](../results/002/repair-equivalence.json).

## Limits and next decision

Eight people and two source collections cannot establish universal congruence. Models share data and a K-means objective, preprocessing is hand-specified, codebook sizes are imposed, nuisance and contact artifacts can survive QC, and there is no semantic endpoint. A frozen blank input contract does not erase an LLM's training history or indirect identity in waveforms.

Experiment001's 393/3,458 (11.36%) external coverage belongs to a different scalp seed and pipeline. The coverage here is not a controlled improvement over that result. The next numerical expansion should test whether stable motifs survive additional around-ear subjects, reference/gain/time-window perturbations and a compatible learned codec. Keep those as new numbered protocols and retain this result, including disagreement. Semantic and independent scientific replication studies remain deferred by James.

## Sources and artifacts

- [ds004015 v1.0.2](https://openneuro.org/datasets/ds004015/versions/1.0.2), [source paper](https://doi.org/10.3389/fnins.2022.869426).
- [ds005207 v1.0.0](https://openneuro.org/datasets/ds005207/versions/1.0.0), [source paper](https://doi.org/10.1111/jsr.12786).
- [Neurable Research Kit](https://www.neurable.com/products/research-kit).
- [Frozen protocol](../protocol/experiment-002.json), [source manifest](../protocol/source-manifest.json), [all metrics](../results/002/metrics.json), [reproduction receipt](../results/002/reproduction.json), [release assets](https://github.com/h3ro-dev/eegt/releases).
"""
(ROOT / "notes/experiment-002.md").write_text(note)
summary = dict(status="reproduced", headline="Different methods find different pattern vocabularies.",
               summary="Eight around-ear recordings; 27 fitted configurations. The run is numerically reproducible. High coverage did not produce a universal partition.",
               metrics=[dict(label="Source recordings", value="8", detail="Two CC0 cEEGrid collections; 80 recording-minutes analyzed."),
                        dict(label="QC-passing windows", value=f"{q['qc_pass']:,} / {q['total_windows']:,}", detail="Two-second channel windows; not independent people."),
                        dict(label="Spectrum / time-frequency ARI", value="0.2894", detail="External set: the same 7,938 QC-passing windows. Identical partitions would score 1."),
                        dict(label="Spectrum / waveform ARI", value="0.0387", detail="External set: low agreement despite high token coverage.")],
               downloads=[dict(label="Experiment 002 research note", url="https://github.com/h3ro-dev/eegt/blob/main/notes/experiment-002.md"),
                          dict(label="All numerical results", url="https://github.com/h3ro-dev/eegt/blob/main/results/002/metrics.json"),
                          dict(label="Waveforms, tokens and codebooks", url="https://github.com/h3ro-dev/eegt/releases/tag/v0.2.0")],
               limitations=["LLM-authored numerical algorithms; independent pretrained-LLM discovery is not established.",
                            "cEEGrid recordings are not Neurable recordings. The decoded input adapter is tested; physical headset transfer is not.",
                            "Eight people; no semantic, clinical or universal claim. Coverage is not accuracy."])
(ROOT / "results/002/site-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
fig, axs = plt.subplots(1, 2, figsize=(10, 4.8), layout="constrained")
for ax, group in zip(axs, ["test", "external"]):
    matrix = np.eye(3)
    methods = list(names)
    for a in comparisons:
        if a["group"] == group:
            i = methods.index(a["a"].split("-k")[0]); j = methods.index(a["b"].split("-k")[0])
            matrix[i, j] = matrix[j, i] = a["all_qc_pass"]["ari"]
    ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues")
    for i, j in itertools.product(range(3), repeat=2):
        ax.text(j, i, f"{matrix[i,j]:.3f}", ha="center", va="center", color="white" if matrix[i,j]>.6 else "#182a36")
    ax.set_xticks(range(3), names.values(), rotation=20, ha="right"); ax.set_yticks(range(3), names.values())
    ax.set_title("Same-source held-out people" if group == "test" else "Other-source held-out people")
fig.suptitle("EEGT Experiment 002 · Adjusted Rand agreement\nK=16, seed17 · same QC-passing windows · 1 = identical partitions", fontsize=12)
fig.savefig(ROOT / "results/002/congruence.png", dpi=180)
plt.close(fig)
