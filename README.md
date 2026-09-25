# EEGT — EEG tokenization

**An LLM’s interpretation of your brainwaves**

An open research notebook asking which recurring voltage patterns different tokenizers agree on. The current release is a numerical experiment on public around-ear EEG. Its models are LLM-authored unsupervised algorithms; this does not establish independent discovery by pretrained LLMs, semantic brain meaning, or a universal token vocabulary.

- [Research Notes website](https://h3ro-dev.github.io/eegt/)
- [Experiment 002 protocol](protocol/experiment-002.json) and [input contract](protocol/INPUT-CONTRACT.md)
- [Data card](DATA_CARD.md), [machine-readable results](results/002/metrics.json), [model card](MODEL_CARD.md)
- [Release data and checksums](https://github.com/h3ro-dev/eegt/releases)

## What ran

Eight fixed-selected recordings from two public CC0 cEEGrid collections; 80 recording-minutes analyzed; three people for fitting, one for validation reporting, two other people for same-source testing and two people from the other source. Forty thousand two-second channel windows are observations, not independent people. Three representations × three vocabulary sizes × three seeds = 27 fitted models. All prespecified settings, withheld windows and controls are retained.

Neurable's Research Kit publicly specifies 12 EEG channels at 500 Hz. This package has a strict decoded-array import adapter at that boundary. The open cEEGrid data come from different electrodes/references and are not Neurable recordings. No physical headset validation is claimed. [Official Research Kit](https://www.neurable.com/products/research-kit).

## Reproduce from the checkout

Use Python 3.12 and the exact locked environment. The commands operate relative to this source checkout; it contains the versioned experiment assets.

```sh
uv venv .venv --python 3.12
uv pip sync --python .venv/bin/python requirements.lock
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/audit_results.py
.venv/bin/python -m eegt.acquire download
.venv/bin/python -m eegt.prepare
```

The source manifest is already frozen; acquisition verifies 16 SET/FDT files, totaling 2,769,602,360 bytes. It needs about 3 GB of source storage plus space for derived files. Model fitting peaked below 2 GB RSS on the recorded run. Downloads use the public OpenNeuro S3 source without authentication; no model API key is required.

`python -m eegt.evaluate` refuses to overwrite existing metrics. For an exact rerun, first copy this checkout to a new run directory and move that copy's `results/002/metrics.json`, `models.npz` and `assignments.npz` to a separate baseline directory. Run the evaluator in the copy, compare assignments/model arrays and numerical metrics to the baseline, and retain the new timing receipt separately. This protects the published run. Input `.npz` files use `allow_pickle=False`; there are no executable model pickle files.

All processing is explicit: a fixed slice, engineering QC, 1–40 Hz filtering and 100 Hz resampling, then spectrum, normalized waveform/PCA and time-frequency features with train-fitted clustering. The frozen protocol and prefit padding clarification specify those choices. Raw source samples and native slices remain separate. Source identity and task labels never enter the discovery API.

Preparation seals the related input files in `results/002/prepared-inputs.json`. Evaluation verifies their hashes and matching window IDs before fitting. If the files are mixed, altered or missing, regenerate from the pinned sources; do not hand-edit a receipt to bypass the check. The [prepublication repair record](protocol/amendment-002.md) explains the defect that motivated this boundary.

## How to read the numbers

Coverage = accepted tokens divided by all selected windows (also separately reported against QC-passing windows). It is not accuracy. ARI/AMI compare assignments while allowing arbitrary token-number changes; 1 means identical partitions, near 0 means chance-level agreement under those metrics. High coverage does not mean stable, useful or universal tokens. Reconstruction ratios compare each model to a one-code baseline on the same observations; lower is better for that numerical target. The two sources and their unequal channel counts must not be treated as a population estimate.

The older scalp seed, Experiment 001, assigned 393 of 3,458 external windows (11.36%). Experiment 002 changes datasets, representation and QC; its coverage is not a controlled improvement over that seed.

## Contribute and publish

Start with a proposed numbered protocol or a reproducible defect. Keep acquisition metadata outside model inputs; record source versions, checksums, units and channel geometry; retain all selected seeds/settings and failures. See [CONTRIBUTING.md](CONTRIBUTING.md) and [the repeatable workflow](RUNBOOK.md). Every completed batch gets an immutable release and Research Note; corrections are appended and linked. No semantic or clinical claim is a default interpretation of a token.

Code: MIT. Derived numeric data/codebooks: CC0-1.0, with upstream source terms and attribution retained. See [LICENSE](LICENSE), [DATA_CARD.md](DATA_CARD.md), and [CITATION.cff](CITATION.cff).
