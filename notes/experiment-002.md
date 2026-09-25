# Research Notes · Experiment 002

Date: 2026-09-24. State: computed and reproduced; independent review/publication receipts are separate artifacts. Protocol frozen before wave inspection/fitting; one prefit filter-padding clarification is recorded. Scope: anonymous numerical around-ear EEG pattern comparison.

## Finding

The three representations find different partitions of the waves. Spectrum and time-frequency agree more than either agrees with phase-sensitive waveform shape. High assignment coverage alone does not establish universal or useful tokens. These are LLM-authored numerical models, not an experiment claiming independent discovery by different pretrained LLMs.

The primary setting was K=16/seed17 before fitting. On the external source, spectrum/time-frequency ARI is **0.2894**, spectrum/waveform **0.0387**, and waveform/time-frequency **0.0189** across the same **7,938 QC-passing windows**. ARI=1 is an identical partition after token renaming; near zero is chance-level partition agreement under this statistic. These numbers are descriptive, not a population test.

## Inputs and denominators

Eight fixed-selected CC0 around-ear recordings from two OpenNeuro sources; 2,769,602,360 downloaded source bytes; 80 recording-minutes analyzed. The native acquisition is 500 Hz ×18 channels in six recordings, and 250 Hz ×15/12 EEG channels in two recordings. These are cEEGrid sources, not Neurable headset captures. Neurable compatibility currently means the tested 12-channel/500 Hz decoded-array interface, not validated physical transfer.

There are **40,500 two-second channel windows**, of which **40,288 pass** engineering QC and **212 abstain**. Simultaneous channels and repeated windows are not independent people. ADC clipping rails are unknown. No sleep/task/clinical annotations, personal history or source identity enters model fitting.

Three participants teach the models; one supplies validation reporting; two different participants test same-source behavior; two from the other source test external behavior. There is no model selection from the validation/test outputs. Source public IDs define grouping; real-person overlap across source collections is not known.

## Coverage, occupancy and distortion

Coverage denominator includes withheld QC windows. Effective vocabulary is exp(entropy) over all QC-passing assignments, so a concentrated 16-code model can behave like far fewer equally used codes. Distortion ratios compare to a training-mean K=1 baseline on the same observations; lower is better for that numerical target. All raw assignments, including OOD assignments, enter these distortion and occupancy measurements.

| Method | Group | Accepted/all windows | Coverage | Effective vocabulary | Wave distortion/K1 | Spectrum distortion/K1 |
|---|---|---:|---:|---:|---:|---:|
| Spectrum | test | 10,640/10,800 | 98.52% | 12.02/16 | 1.002 | 0.491 |
| Spectrum | external | 7,544/8,100 | 93.14% | 10.92/16 | 1.004 | 0.381 |
| Waveform | test | 10,642/10,800 | 98.54% | 15.68/16 | 0.835 | 0.997 |
| Waveform | external | 7,885/8,100 | 97.35% | 4.72/16 | 0.591 | 1.009 |
| Time-frequency | test | 10,650/10,800 | 98.61% | 12.24/16 | 1.002 | 0.545 |
| Time-frequency | external | 7,377/8,100 | 91.07% | 9.49/16 | 0.999 | 0.443 |

The external waveform model's effective vocabulary is only **4.72/16** despite 97.35% overall coverage. Spectrum models compress spectral structure better; the waveform model compresses normalized waveform shape better. That is consistent with their different objectives, not evidence of one common natural alphabet.

## Agreement on common observations

| Pair | Group | All QC-pass N | ARI | AMI | Both accepted N | ARI on intersection |
|---|---|---:|---:|---:|---:|---:|
| spectrum / waveform | test | 10,792 | 0.0052 | 0.0136 | 10,502 | 0.0048 |
| spectrum / waveform | external | 7,938 | 0.0387 | 0.0964 | 7,508 | 0.0401 |
| spectrum / time_frequency | test | 10,792 | 0.2317 | 0.4204 | 10,536 | 0.2292 |
| spectrum / time_frequency | external | 7,938 | 0.2894 | 0.4495 | 7,180 | 0.2750 |
| waveform / time_frequency | test | 10,792 | 0.0025 | 0.0084 | 10,504 | 0.0023 |
| waveform / time_frequency | external | 7,938 | 0.0189 | 0.0776 | 7,333 | 0.0201 |

## Variation across seeds

All three seed pairings at K=16 are included below. Complete K=8/16/32 results and per-recording comparisons are in metrics.json; no best seed was selected.

| Method | Group | Seed-pair ARI range |
|---|---|---:|
| Spectrum | test | 0.5760–0.6837 |
| Spectrum | external | 0.7698–0.7923 |
| Waveform | test | 0.4296–0.6520 |
| Waveform | external | 0.2980–0.8201 |
| Time-frequency | test | 0.3883–0.5293 |
| Time-frequency | external | 0.5588–0.8105 |

## Controls and reproducibility

Within-window sample permutation and Fourier phase randomization were run at the primary setting, with per-recording outcomes in metrics.json. Phase randomization preserves the unwindowed FFT magnitude; subsequent Hann-window estimates may differ. One hundred random label permutations per primary pair provide a numerical null scale, not a participant-level significance test. Common-target K=1 distortion is reported above.

A separate copied package repeated all 27 fits. Assignment and model NPZ archives were byte-identical, and all numerical metrics, QC, controls and nulls matched. Runtime and peak RSS are not equality targets. The released full fit/evaluation took 14.01 seconds on the recorded one-thread environment. See reproduction.json and the resource receipt for its scope; this is a repeat on the same platform, not an outside replication.

Independent review found that the original evaluator could accept a same-length, reordered evaluation index. The saved run itself was aligned. Before publication, we added digest binding and matching window IDs before any fit, regenerated the run and verified that every numerical result was unchanged. The original finding and repair are retained in the [prepublication amendment](../protocol/amendment-002.md) and [numerical equivalence receipt](../results/002/repair-equivalence.json).

## Limits and next decision

Eight people and two source collections cannot establish universal congruence. Models share data and a K-means objective, preprocessing is hand-specified, codebook sizes are imposed, nuisance and contact artifacts can survive QC, and there is no semantic endpoint. A frozen blank input contract does not erase an LLM's training history or indirect identity in waveforms.

Experiment001's 393/3,458 (11.36%) external coverage belongs to a different scalp seed and pipeline. The coverage here is not a controlled improvement over that result. The next numerical expansion should test whether stable motifs survive additional around-ear subjects, reference/gain/time-window perturbations and a compatible learned codec. Keep those as new numbered protocols and retain this result, including disagreement. Semantic and independent scientific replication studies remain deferred by James.

## Sources and artifacts

- [ds004015 v1.0.2](https://openneuro.org/datasets/ds004015/versions/1.0.2), [source paper](https://doi.org/10.3389/fnins.2022.869426).
- [ds005207 v1.0.0](https://openneuro.org/datasets/ds005207/versions/1.0.0), [source paper](https://doi.org/10.1111/jsr.12786).
- [Neurable Research Kit](https://www.neurable.com/products/research-kit).
- [Frozen protocol](../protocol/experiment-002.json), [source manifest](../protocol/source-manifest.json), [all metrics](../results/002/metrics.json), [reproduction receipt](../results/002/reproduction.json), [release assets](https://github.com/h3ro-dev/eegt/releases).
