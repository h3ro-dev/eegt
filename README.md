# EEGT — EEG tokenization

**An LLM’s interpretation of your brainwaves**

An open research notebook asking which recurring voltage patterns different tokenizers agree on. The current release is a numerical experiment on public around-ear EEG. Its models are LLM-authored unsupervised algorithms; this does not establish independent discovery by pretrained LLMs, semantic brain meaning, or a universal token vocabulary.

- [Research Notes website](https://h3ro-dev.github.io/eegt/)
- [Continuous corpus and transitions](https://h3ro-dev.github.io/eegt/growth.html)
- [Database contract](DATABASE.md), [Experiment 003 protocol](protocol/experiment-003.json), and [input contract](protocol/INPUT-CONTRACT.md)
- [Experiment 002 data card](DATA_CARD.md), [results](results/002/metrics.json), and [model card](MODEL_CARD.md)
- [Release data and checksums](https://github.com/h3ro-dev/eegt/releases)

## Repeated-session milestone · v0.4.0

[Experiment008](https://h3ro-dev.github.io/eegt/repeated-sessions.html) adds 12 recordings from six participants, each measured on two nights: 86.38 qualified recorded hours. Its frozen analysis uses the first four hours of each recording (48 hours total). The expanded index contains 67 candidates, 66 qualified recordings and 309.85 qualified hours across three datasets. These are source records, not a verified global count of unique people.

The comparison uses the existing frozen numerical baseline; no pretrained EEG/LLM checkpoint was run. The separate [model compatibility audit](notes/model-compatibility-2026-09-25.md) records actual input and checkpoint constraints. Four participants and later sessions remain reserved. Greater same-person similarity can also reflect stable anatomy, sensors or artifacts; it is not proof of universal tokens.

Reproduce Experiment008 with the existing locked environment (all commands from this directory):

```sh
python -m eegt.repeated freeze
python -m eegt.repeated acquire
python -m eegt.repeated qualify
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python -m eegt.repeated extract
python -m eegt.repeated evaluate
python scripts/report_repeated.py
```

The published manifest freezes the selection. Existing immutable analyses refuse overwrite; use a clean copy with the release's locked dependencies when rerunning. The baseline `results/003/model.json` is already in source. To rebuild the cross-release index, extract the v0.3.0 database asset too; Experiment008's numerical analysis needs only its newly acquired sources. [Release assets](https://github.com/h3ro-dev/eegt/releases/tag/v0.4.0) contain the new databases and feature arrays; original waves remain at OpenNeuro.

## Continuous database milestone · v0.3.0

The full pinned around-ear source inventory contains 55 recordings and 21,535,181,808 verified bytes. Fifty-four qualify, totaling 223.47 decoded sample-hours. One recording remains quarantined for a duration discrepancy. Source participants, sessions, hours, multichannel windows and eligible scoring time have separate denominators. These are two public cEEGrid archives, with one recording per source participant; cross-archive identity overlap is unknown.

Experiment 003 measures changes in waveform shape, spectrum and sensor coordination, preserving native gaps. Experiment 004 records the expanded corpus; 006 tests phase and nuisance controls; 007 reports frozen participant/dataset transfer. Experiment 005 is a prepared Neurable capture protocol and **has not run**. See the [Research Notes](notes/) and [current priorities](STRATEGY.md).

The methods see numerical samples and technical timing/validity only. They receive no identity, task or clinical labels. These are three LLM-authored numerical views, not three pretrained LLMs independently discovering the same language. This historical milestone had no repeated sessions. Experiment008 below the current release adds a first repeat-night comparison; pretrained-model inference and actual headset transfer remain open.

## Earlier tokenization baseline · v0.2.0

Eight fixed-selected recordings from two public CC0 cEEGrid collections; 80 recording-minutes analyzed; three people for fitting, one for validation reporting, two other people for same-source testing and two people from the other source. Forty thousand two-second channel windows are observations, not independent people. Three representations × three vocabulary sizes × three seeds = 27 fitted models. All prespecified settings, withheld windows and controls are retained.

Neurable's Research Kit publicly specifies 12 EEG channels at 500 Hz. This package has a strict decoded-array import adapter at that boundary. The open cEEGrid data come from different electrodes/references and are not Neurable recordings. No physical headset validation is claimed. [Official Research Kit](https://www.neurable.com/products/research-kit).

## Reproduce the continuous corpus

Use Python 3.12 with `requirements.lock`. Reserve about 25 GB for raw and derived data, plus separate space for any copied rerun. Original files remain in the public archives; release downloads provide the SQLite databases and numeric derivatives. No model API key is required.

```sh
uv venv .venv --python 3.12
uv pip sync --python .venv/bin/python requirements.lock
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
.venv/bin/python -W error -m unittest discover -s tests -q
.venv/bin/python -m eegt.corpus download --max-bytes 22000000000
.venv/bin/python -m eegt.corpus qualify
.venv/bin/python -m eegt.calibrate
.venv/bin/python -m eegt.growth extract --workers 1
.venv/bin/python -m eegt.growth evaluate
.venv/bin/python -m eegt.controls
.venv/bin/python scripts/report_growth.py
.venv/bin/python scripts/audit_growth.py
```

The manifest is already frozen; do not reselect sources. Published outputs refuse replacement. For a rerun, copy the checkout to a new directory and move that copy's `results/corpus-v1`, `results/003`, `results/006`, `results/007`, and `data/derived/003` into a separate baseline directory before running. Preserve source files and the frozen protocol. Compare numerical arrays and metrics; SQLite binary hashes can differ with environment or serialization. Digital calibration checks the decoding conversion, not the original amplifier's accuracy.

The default command uses one numerical process. Increase workers only after measuring CPU, memory and I/O capacity; the completed extraction used eight single-threaded processes. See [prepublication corrections](protocol/amendment-003.md). Never edit a hash receipt to admit changed inputs.

## Reproduce the earlier Experiment 002

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

For the transition study, timing F1 is `2 × matched boundaries / (boundaries from view A + boundaries from view B)`. Matching is one-to-one within one second. One means all detected boundaries match; zero means none match. The headline is the median of these per-record scores, not a percentage of people or brain meaning. Empty/empty records contribute no aggregate agreement evidence.

Coverage = accepted tokens divided by all selected windows (also separately reported against QC-passing windows). It is not accuracy. ARI/AMI compare assignments while allowing arbitrary token-number changes; 1 means identical partitions, near 0 means chance-level agreement under those metrics. High coverage does not mean stable, useful or universal tokens. Reconstruction ratios compare each model to a one-code baseline on the same observations; lower is better for that numerical target. The two sources and their unequal channel counts must not be treated as a population estimate.

The older scalp seed, Experiment 001, assigned 393 of 3,458 external windows (11.36%). Experiment 002 changes datasets, representation and QC; its coverage is not a controlled improvement over that seed.

## Contribute and publish

Start with a proposed numbered protocol or a reproducible defect. Keep acquisition metadata outside model inputs; record source versions, checksums, units and channel geometry; retain all selected seeds/settings and failures. See [CONTRIBUTING.md](CONTRIBUTING.md) and [the repeatable workflow](RUNBOOK.md). Every completed batch gets an immutable release and Research Note; corrections are appended and linked. No semantic or clinical claim is a default interpretation of a token.

Code: MIT. Derived numeric data/codebooks: CC0-1.0, with upstream source terms and attribution retained. See [LICENSE](LICENSE), [DATA_CARD.md](DATA_CARD.md), and [CITATION.cff](CITATION.cff).
