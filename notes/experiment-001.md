# EEGT Research Note — Experiment 001

**Title:** Seed-v1 spectral tokenization baseline
**Status:** Published to the local research ledger; public website publication is a separate release step.
**Date:** 2026-09-24
**Experiment ID:** EEGT-EXP-001

## Question

Can a deterministic, fixed spectral codebook assign repeatable symbols to short EEG windows, and how much of an untouched external split receives an in-vocabulary assignment? This is a measurement and transfer baseline. It does not test semantic meaning, clinical utility, or universal brain encoding.

## Blank-slate input contract

The tokenizer sees numeric signal windows plus the permitted acquisition geometry needed to interpret them. It does not receive participant history, identity, clinical labels, task labels, stimulus text, report text, or semantic annotations. Source provenance and split membership remain in audit records outside the model input.

## Data and method

- 14 licensed public EDF recordings from two source datasets; 27,266 two-second channel windows. Cross-dataset participant identity is unknown.
- The codebook was fit only on 8,239 numerically eligible windows from three EEGMMIDB participants.
- Six spectral bands plus RMS were normalized and clustered into 16 codes. The scaler, centroids, and OOD threshold were fit on training data only.
- Quality and OOD abstentions are retained explicitly; they are not silently converted to tokens.
- The exact source manifest, codebook, metrics, database, JSONL export, and environment are hash-bound in `EXPERIMENT-001.json`.

## Results

| Split | Channel windows | Assigned tokens | Coverage | OOD abstentions | Other QC abstentions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 11,904 | 8,197 | 68.86% | 42 | see metrics reason counts |
| Validation | 3,968 | 2,737 | 68.98% | 1,027 | see metrics reason counts |
| Same-dataset test | 7,936 | 7,047 | 88.80% | 442 | see metrics reason counts |
| External test | 3,458 | 393 | **11.36%** | 3,011 | 54 clipped |
| All outputs | 27,266 | 18,374 | 67.39% | 4,522 | 4,405 named QC reason entries |

QC reason counts are retained exactly in `metrics.json`; reason entries can be non-additive when a window has more than one recorded reason.

“11.4% external dataset coverage” means that 393 of the 3,458 external channel windows were close enough to the training codebook to receive one of its 16 symbols after quality checks. The other 3,065 windows were deliberately withheld from the token stream: 3,011 were outside the fitted distance threshold and 54 were clipped. It is not 11.4% of people, recordings, brain activity, or meaning.

On accepted same-dataset test windows, retained-feature RMSE was 0.262 versus 0.397 for a one-code training-mean baseline. The external next-token cross-entropy was 2.502 bits, compared with 2.492 bits for the within-record channel-shuffle control. These are descriptive baseline measurements, not evidence of semantic structure.

A synthetic channel-scale perturbation changed 16.14% of assignments when both original and perturbed windows remained tokenized. A synthetic common-average-reference perturbation changed 75.61% under the same conditional comparison and reduced coverage to 52.49%. These nuisance results make reference and scale controls mandatory for later work. Reverse channel-order recomputation changed zero features, QC outcomes, or tokens when source channel identities were retained.

## Interpretation

This experiment establishes a reproducible, auditable signal-token baseline and exposes a strong domain-shift boundary. It does not establish a natural language of the brain, semantic meaning, universal tokenization, session/device/site transfer, waveform reconstruction, or clinical/cognitive accuracy. The low external coverage is a reason to run the qualified battery and independent tokenizer comparisons in the strategy plan.

## Reproduction

Use the frozen seed manifest and the repository's deterministic CLI to rebuild `outputs/eeg-token-language/runs/seed-v1`. The accepted package includes two byte-identical offline runs, 21 tests, and an independent 53-check artifact audit. See [`outputs/START_HERE.md`](../START_HERE.md), [`outputs/review/ACCEPTANCE.json`](../review/ACCEPTANCE.json), and [`outputs/review/reproduction.json`](../review/reproduction.json).

## Next decision

Do not tune this seed against the external split. Freeze the blank-slate protocol, qualify CHB-MIT and a corrected 100 Hz Sleep-EDF path, then compare independent time, spectral, time-frequency, neural-codec, sensor-aware, and continuous representation baselines on held-out participants and devices. Experiment 002 should report agreement, abstention, nuisance sensitivity, and null controls before any meaning test.
