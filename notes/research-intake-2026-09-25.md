# Research intake · 2026-09-25

This is a bounded literature update for the database-growth milestone, not a
systematic review or a claim that EEGT discovered an unexplored field.

| Primary source | Relevant result or method | Decision for EEGT |
|---|---|---|
| [CodeBrain, ICLR 2026; revision 4, May 2026](https://arxiv.org/abs/2506.09110v4) | Separates temporal and frequency tokenizers and evaluates a multiscale model on downstream EEG tasks. | Maintain separate waveform and spectrum views. A useful trained tokenizer does not establish that all models discover the same natural alphabet. Audit electrode/input compatibility and training-set overlap before adding its checkpoint to the around-ear battery. |
| [EEG-FM-Compass, revision 3, August 2026](https://arxiv.org/abs/2601.17883v3) | Benchmarks 12 open models on 13 datasets and reports that scratch-trained specialists can remain competitive; larger models do not consistently generalize better. | Preserve transparent numeric baselines and participant-separated evaluation before spending compute on large pretrained models. Model size alone is not a reason for inclusion. |
| [REVE, October 2025](https://arxiv.org/abs/2510.21585) | Uses electrode-position-aware representations across heterogeneous EEG sources. | Candidate for a later compatible learned-representation comparison. Missing around-ear contact coordinates must remain unknown, rather than being assigned scalp locations to make a model run. |
| [Cole and Voytek, cycle-by-cycle analysis, 2019](https://doi.org/10.1152/jn.00273.2019) | Separates cycle duration, amplitude, symmetry and burst structure; simulations show how conventional transforms can conflate changes in different oscillatory properties. | Add cycle-level morphology only after testing cycle detection against synthetic nonoscillatory and artifact signals. Current transition analysis is a slower multivariate feature-change assay, not a millisecond microstate or cycle detector. |
| [Neurable Research Kit](https://www.neurable.com/products/research-kit) | Advertises raw EEG and motion access, 12 EEG channels and 500-Hz sampling. | Match the import contract to documented exports; use motion as a separate nuisance measurement when available. Public cEEGrid data cannot validate physical headset transfer. |

## Feature expansion priorities

1. First measure transition magnitude, path length, speed, turning angle and
   return distance using the current anonymous numeric views. Publish missing
   context and invalid windows. These are candidate signal descriptors.
2. Add burst duration, cycle asymmetry, dominant-frequency drift and aperiodic
   spectral slope with synthetic validation and explicit estimation uncertainty.
   Test whether they add reproducible information beyond the current views.
3. Add permutation entropy and recurrence estimates with matched record lengths,
   sampling rates and phase controls. These depend strongly on scale and tuning;
   a higher number is not inherently healthier or more meaningful.
4. Add lag-aware sensor coupling only after reference and volume-conduction
   sensitivity tests. Correlation between nearby contacts is not direct evidence
   of communication between brain regions. Sparse around-ear sensors do not
   reconstruct a full scalp microstate map.
5. Consider event recurrence, dwell times and recovery only after demonstrating
   stable state definitions and recording continuity. A gap between detections
   is not automatically time spent in a biological state.

Freeze each new feature family in its own numbered experiment, compare it with
existing baselines, and retain negative results. Context labels may later test
meaning in a separate evaluator after discovery is fixed. No feature here is
validated for clinical diagnosis by this project.

## Open-source and publication sequence

Keep the MIT analysis code, pinned source manifest, CC0 source attribution,
frozen protocols, SQLite catalogs, model parameters, tests and per-record results
together in versioned GitHub releases. Large original files remain at their
public archives with verified hashes and a reproducible downloader. Research
Notes link each claim to its denominator and run artifacts, including failures.

Publish a concise reproducibility package before inviting outside replication.
A later DOI archive or manuscript should cite the exact release, rather than a
moving branch. Community submissions need a source/permission record, technical
qualification and a separate untouched evaluation set. Announcements and claims
should follow the measured result; agreement among code written by LLMs must not
be described as independent discovery by pretrained LLMs.
