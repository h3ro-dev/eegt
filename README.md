# EEGT — EEG tokenization

**Project subtitle: An LLM’s interpretation of your brainwaves**

The current experiment runs a continuous EEG encoder, not an LLM decoder or thought interpretation.

An open research notebook asking which recurring voltage patterns different tokenizers agree on. The current release compares two fixed pretrained EEG encoders on the same time-distributed public around-ear EEG. This does not establish independent discovery by pretrained LLMs, semantic brain meaning, or a universal token vocabulary.

- [Research Notes website](https://h3ro-dev.github.io/eegt/)
- [Continuous corpus and transitions](https://h3ro-dev.github.io/eegt/growth.html)
- [Database contract](DATABASE.md), [Experiment 003 protocol](protocol/experiment-003.json), and [input contract](https://github.com/h3ro-dev/eegt/blob/v0.6.0/protocol/INPUT-CONTRACT.md)
- [Experiment 002 data card](https://github.com/h3ro-dev/eegt/blob/v0.6.0/DATA_CARD.md), [results](https://github.com/h3ro-dev/eegt/blob/v0.6.0/results/002/metrics.json), and [model card](https://github.com/h3ro-dev/eegt/blob/v0.6.0/MODEL_CARD.md)
- [Release data and checksums](https://github.com/h3ro-dev/eegt/releases)

## Two-encoder comparison · v0.7.0

[Experiment 011](https://h3ro-dev.github.io/eegt/cross-encoder.html) compares **CodeBrain and CBraMod** on the same **122 selected blocks**. CBraMod ran **610 new forward passes**; CodeBrain outputs were reused with exact hash checks. **Five paired people / 110 blocks** support both primary tests. Mean paired original-minus-phase effects are **0.0713 for geometry** and **0.0947 for change**. Both adjusted p values are **0.125**: positive observed contrasts, still inconclusive. No new source people or recorded hours enter this analysis.

[Research Note](notes/experiment-011.md) · [Frozen protocol](protocol/experiment-011.json) · [Validation](notes/validation-011.md) · [Release](https://github.com/h3ro-dev/eegt/releases/tag/v0.7.0) · [Reproduction instructions](REPRODUCE-011.md).

The data archive contains a complete `repo/` and `input/` reproduction packet, both latent archives and the selected numeric waves. Offline evaluation requires no checkpoint or model call. Preserve its original path layout and reproduce into a new output directory. The release keeps the original source seal, failed evaluation partial and explicit post-inference serialization/offline-dependency correction. Pretraining overlap, ear/scalp transfer, semantic meaning and universal tokenization remain unestablished.

## Time-distributed comparison · v0.6.0

[Experiment 010](https://h3ro-dev.github.io/eegt/distributed.html) checks **5,760 thirty-second blocks** within the same twelve previously exposed recordings: **2,973 quality-qualified (51.61%)**, **122 selected by a frozen time rule**, and **610 model forward passes**. Five people qualify for paired-night comparisons, contributing 110 selected blocks; person 003's twelve selected blocks remain descriptive. This adds no new source people or recorded hours. The corpus remains 67 candidates, 66 qualified recordings and 309.85 qualified source hours.

Geometry correlations with waveform shape, spectrum and sensor coordination are weak: **0.0815, 0.0381 and 0.0419**, each adjusted p = 0.003 under the prescribed cyclic-shift test. Change-profile correlations do not clear correction (adjusted p = 0.387, 1.000 and 0.639). These conditional tests on five already exposed people do not establish shared inflection points, universal tokens, semantic meaning or physical Neurable transfer. A continuous pretrained backbone was tested; a second learned encoder and a full discrete tokenizer remain future work.

[Note](notes/experiment-010.md) · [Frozen protocol](protocol/experiment-010.json) · [Independent validation](notes/validation-010.md) · [Release and data](https://github.com/h3ro-dev/eegt/releases/tag/v0.6.0). Numeric discovery receives no identity, history or semantic labels. All candidate outcomes remain in the provenance ledger; quality and selection are distinct.

To reproduce the comparisons from the extracted v0.6.0 bundle in a separate directory, install `requirements.lock` with Python 3.12, preserve the existing summary, then run:

```sh
mv results/010/summary.json results/010/summary-published.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python -m eegt.distributed_study evaluate
python scripts/report_distributed.py
python -W error -m unittest discover -s tests -q
```

To rerun actual inference, use a separate environment with `requirements-encoder.lock`, obtain the pinned official checkpoint described below, preserve `results/010/inference.json` and `data/derived/010/embeddings.npz`, then run `python -m eegt.distributed_study infer --checkpoint /path/to/CodeBrain.pth`. Loading rejects an incorrect checkpoint hash. Raw-to-prepared reproduction additionally needs the pinned twelve source recordings and v0.4.0 baseline feature files; preserve `results/010/prepared.json` and run `python -m eegt.distributed_study prepare`. Original full recordings and weights are not redistributed here. Published results are immutable; keep reruns in a separate directory.

The inherited 60 Hz notch does not specifically remove the source's 50 Hz mains; no preprocessing or eligibility threshold was relaxed for this run. Pretraining overlap and validity of 19-scalp-to-four-ear spatial transfer remain unknown. Untouched participants 007–010 and unexamined later sessions are reserved.

## Pretrained encoder feasibility · v0.5.0

[Experiment009](https://h3ro-dev.github.io/eegt/pretrained.html) runs the fixed CodeBrain EEGSSM backbone on four ear channels. Nine of 240 prespecified 30-second segments pass the common quality gate: 4.5 minutes from a two-hour candidate sample. The encoder completes 45 passes including waveform controls. No participant has three valid segments in each of two nights, so all six planned participant-level comparisons are **INSUFFICIENT_PARTICIPANTS**. No p values or universal-agreement claim are produced. All candidates, exclusions, segment correlations and outputs are retained.

The model runs continuous embeddings, not the full discrete tokenizer or an LLM decoder. Its 19-scalp-channel pretraining does not validate four-ear-channel geometry; pretraining overlap is unknown. This experiment adds no new source recordings or participants. The corpus inventory remains 66 qualified recordings / 309.85 recorded hours. See [the note](https://github.com/h3ro-dev/eegt/blob/v0.6.0/notes/experiment-009.md), [protocol](protocol/experiment-009.json) and [release bundle](https://github.com/h3ro-dev/eegt/releases/tag/v0.5.0).

The source metadata reports 50 Hz mains, while the fixed model recipe applies a 60 Hz notch; that notch does not specifically remove the source's 50 Hz component. This mismatch is retained and reported, rather than changing preprocessing after seeing results.

Recompute the comparisons from the v0.5.0 bundle in a separate directory, with Python 3.12 and the original numerical `requirements.lock`. Preserve the published summary before rerunning:

```sh
mv results/009/summary.json results/009/summary-published.json
python -m eegt.pretrained_study evaluate
python scripts/report_pretrained.py
```

For encoder inference, use a **separate** Python 3.12 environment with `requirements-encoder.lock`; Torch 2.4.1 uses NumPy 1.26.4, while the original numerical environment remains unchanged. Download the [pinned official weights](https://huggingface.co/YjMajy/CodeBrain/resolve/bef08d2fdb1759685371cc635aad21ce59163689/CodeBrain.pth); the adapter verifies its size and SHA before safe loading. In a rerun copy, move the published `results/009/inference.json` aside and run:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python -m eegt.pretrained_study infer --checkpoint /absolute/path/CodeBrain.pth
CODEBRAIN_CHECKPOINT=/absolute/path/CodeBrain.pth python -m unittest discover -s tests -p test_pretrained.py -v
```

The full original-source equivalence test additionally needs `CODEBRAIN_UPSTREAM_ZIP`, the archive for [commit22d350c](https://github.com/jingyingma01/CodeBrain/archive/22d350caf68246d2fda4f630ef837420db3fb130.zip). Tests report unavailable optional dependencies or source-reference evidence as skips, not passes. For raw-to-prepared reproduction, also obtain the v0.4.0 feature bundle and its pinned twelve raw recordings, preserve `results/009/prepared.json`, then run `python -m eegt.pretrained_study prepare` in the numerical environment. The v0.5.0 archive already includes the nine derived wave blocks and aligned descriptors needed for inference and evaluation. Original full recordings and model weights are not bundled.

EEGT-owned code is MIT; vendored CodeBrain files are Apache-2.0 with [attribution and modification notice](eegt/vendor/codebrain/NOTICE). Source-wave derivatives retain their CC0 source provenance.

## Repeated-session milestone · v0.4.0

[Experiment008](https://h3ro-dev.github.io/eegt/repeated-sessions.html) adds 12 recordings from six participants, each measured on two nights: 86.38 qualified recorded hours. Its frozen analysis uses the first four hours of each recording (48 hours total). The expanded index contains 67 candidates, 66 qualified recordings and 309.85 qualified hours across three datasets. These are source records, not a verified global count of unique people.

The comparison uses the existing frozen numerical baseline; no pretrained EEG/LLM checkpoint was run. The separate [model compatibility audit](https://github.com/h3ro-dev/eegt/blob/v0.6.0/notes/model-compatibility-2026-09-25.md) records actual input and checkpoint constraints. Four participants and later sessions remain reserved. Greater same-person similarity can also reflect stable anatomy, sensors or artifacts; it is not proof of universal tokens.

Recompute Experiment008 in a separate checkout with the existing locked environment. Preserve the checked-in published receipts by moving them aside before creating a fresh run (all commands from that checkout directory):

```sh
mv results/008 results/008-published
python -m eegt.repeated freeze
python -m eegt.repeated acquire
python -m eegt.repeated qualify
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python -m eegt.repeated extract
python -m eegt.repeated evaluate
python scripts/report_repeated.py
```

The published manifest freezes the selection. Existing immutable analyses refuse overwrite; use a clean copy with the release's locked dependencies when rerunning. The baseline `results/003/model.json` is already in source. The v0.4.0 data bundle includes the small v0.3.0 source catalog needed to rebuild the cross-release index; Experiment008's numerical analysis needs only its newly acquired sources. [Release assets](https://github.com/h3ro-dev/eegt/releases/tag/v0.4.0) contain the new databases and feature arrays; original waves remain at OpenNeuro.

## Continuous database milestone · v0.3.0

The full pinned around-ear source inventory contains 55 recordings and 21,535,181,808 verified bytes. Fifty-four qualify, totaling 223.47 decoded sample-hours. One recording remains quarantined for a duration discrepancy. Source participants, sessions, hours, multichannel windows and eligible scoring time have separate denominators. These are two public cEEGrid archives, with one recording per source participant; cross-archive identity overlap is unknown.

Experiment 003 measures changes in waveform shape, spectrum and sensor coordination, preserving native gaps. Experiment 004 records the expanded corpus; 006 tests phase and nuisance controls; 007 reports frozen participant/dataset transfer. Experiment 005 is a prepared Neurable capture protocol and **has not run**. See the [Research Notes](https://github.com/h3ro-dev/eegt/tree/v0.6.0/notes/) and [current priorities](STRATEGY.md).

The methods see numerical samples and technical timing/validity only. They receive no identity, task or clinical labels. These are three LLM-authored numerical views, not three pretrained LLMs independently discovering the same language. This historical milestone had no repeated sessions. Experiment008 adds a first repeat-night comparison; Experiment009 adds pretrained EEG encoder execution with insufficient participant support. Actual headset transfer remains open.

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

The default command uses one numerical process. Increase workers only after measuring CPU, memory and I/O capacity; the completed extraction used eight single-threaded processes. See [prepublication corrections](https://github.com/h3ro-dev/eegt/blob/v0.6.0/protocol/amendment-003.md). Never edit a hash receipt to admit changed inputs.

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

Preparation seals the related input files in `results/002/prepared-inputs.json`. Evaluation verifies their hashes and matching window IDs before fitting. If the files are mixed, altered or missing, regenerate from the pinned sources; do not hand-edit a receipt to bypass the check. The [prepublication repair record](https://github.com/h3ro-dev/eegt/blob/v0.6.0/protocol/amendment-002.md) explains the defect that motivated this boundary.

## How to read the numbers

For the transition study, timing F1 is `2 × matched boundaries / (boundaries from view A + boundaries from view B)`. Matching is one-to-one within one second. One means all detected boundaries match; zero means none match. The headline is the median of these per-record scores, not a percentage of people or brain meaning. Empty/empty records contribute no aggregate agreement evidence.

Coverage = accepted tokens divided by all selected windows (also separately reported against QC-passing windows). It is not accuracy. ARI/AMI compare assignments while allowing arbitrary token-number changes; 1 means identical partitions, near 0 means chance-level agreement under those metrics. High coverage does not mean stable, useful or universal tokens. Reconstruction ratios compare each model to a one-code baseline on the same observations; lower is better for that numerical target. The two sources and their unequal channel counts must not be treated as a population estimate.

The older scalp seed, Experiment 001, assigned 393 of 3,458 external windows (11.36%). Experiment 002 changes datasets, representation and QC; its coverage is not a controlled improvement over that seed.

## Contribute and publish

Start with a proposed numbered protocol or a reproducible defect. Keep acquisition metadata outside model inputs; record source versions, checksums, units and channel geometry; retain all selected seeds/settings and failures. See [CONTRIBUTING.md](https://github.com/h3ro-dev/eegt/blob/v0.6.0/CONTRIBUTING.md) and [the repeatable workflow](RUNBOOK.md). Every completed batch gets an immutable release and Research Note; corrections are appended and linked. No semantic or clinical claim is a default interpretation of a token.

Code: MIT. Derived numeric data/codebooks: CC0-1.0, with upstream source terms and attribution retained. See [LICENSE](LICENSE), [DATA_CARD.md](https://github.com/h3ro-dev/eegt/blob/v0.6.0/DATA_CARD.md), and [CITATION.cff](CITATION.cff).

Experiment 011 scales calibrated microvolts as µV/100, following both encoders’ documented pretraining convention. This does not validate amplitude distributions, reference/calibration equivalence or four-ear-channel positional mapping against their scalp inputs; the public note links the audited sources.
