# Experiment 010 independent scientific review

**Verdict: ACCEPTED for the sealed scientific snapshot.** This verdict covers the frozen protocol, candidate and selection receipts, stored numerical arrays, inference identities, comparison statistics, and SQLite analysis. It does **not** approve publication text, package contents, source-link reachability, or a website. Those files were not in this review snapshot and require a separate readback.

Review work: `eco-uzwh8s.27` · reviewer scope: `out/` and `scratch/` only · accountable project owner: `session-13ffd342d925791b856652db872e4142`. No canonical code or data were changed. No model forward, new acquisition, public send, or release was made.

## Bound inputs and methods

The SHA-256 of `input/MANIFEST.json` is `c01b308c9118b92c151b3e822a8271b832febc46d9a69e54fafa2bea3eaf3c74`. All 65 listed snapshot files matched their manifest hashes both before and after review. The machine-readable companion contains the exact hash of every reviewed file. Key identities are:

| Input | SHA-256 |
| --- | --- |
| `protocol/experiment-009.json` | `5c45dc42d237b89653909bf536f3cf44927a28303f808ac1d0bc48b2c00562f1` |
| `protocol/experiment-010.json` | `75f79f511d286254e544a50e470248153dc3b3fe38e1596936f748162cb3fa9b` |
| `eegt/distributed_study.py` | `0f4f670b16494c6626a0edd36f53e94cbae2c1462c466209bede6108e5996266` |
| `eegt/pretrained_study.py` | `80187b84274606d4d7d4c514d7eb05b892b4b8df96b8a92b6ea099293a232e3c` |
| `data/derived/010/prepared.npz` | `894cfc2f49371223ea488b6b662d909ba366ad1e84c215d18a37c9d64a138abc` |
| `data/derived/010/embeddings.npz` | `5c961360971ed18c88a0c2e474fece27ca7db08d359ffa8223a81f1c64b7de40` |
| `results/010/summary.json` | `5c077f25e6e81ee6464ab8b2b42fc8ffb63c663f2357b455448f7ec8b8724bbc` |
| `results/010/analysis.sqlite` | `df67f4ea8228a0a69a79d6c98305c76af6c402b0979562d29d33e2aba584a4a4` |

The 010 protocol retains 009's source set, encoder, preprocessing, baseline references, quality thresholds, representation, waveform controls, six-test family, null method, seed, and multiplicity rule. Its specified change is a 48-hour census of the already examined first four hours of 12 recordings and one quality-pass lower temporal median per fixed 20-minute stratum. The protocol declares a freeze at 2026-09-25 21:50:49 UTC; the prepared receipt is dated 21:56:15 UTC and the inference receipt 21:58:12 UTC. The prepared receipt binds the implementation hash. Git commit objects and an independent clock attestation were absent from this snapshot, so commit timing was not separately proved.

## Recomputed evidence

I independently checked the 5,760 contiguous candidate IDs, all 480 exact 30-second starts in each of the 12 people/night recordings, the fixed stratum index, the quality/status distinction, and the lower median among quality-pass blocks in every nonempty stratum. The records have 2,973 quality passes, 2,851 qualified blocks left unselected, 2,787 rejections, and **122 selected blocks**. Selection is determined from stored eligibility and time; encoder scores are not used. The 12 recording counts and recomputed paired gate give five complete people (`001`, `002`, `004`, `005`, `006`) and 110 blocks in those complete pairs. Person `003` has one selected block in night `001` and 11 in night `002`; all 12 of that person's selected blocks remain descriptive and do not contribute to the six primary person means.

The 12 qualification rows, 12 corpus-manifest entries, 12 prior feature receipts, and 24 prepared source-hash references agree on recording IDs and hashes. Each feature receipt states 14,400 seconds previously analyzed. The source waveform and feature archive bytes themselves are outside this packet.

Using the pinned NumPy 1.26.4 and SciPy 1.14.1 environment and a single numerical thread, my independent script verified every selected prepared patch and baseline-array hash; every listed input variant hash and all 610 embedding output hashes; all **732** geometry/change block values and **19,398** nonzero cyclic-shift values; all **488** waveform-control comparisons; all six sets of 1,999 sampled null values and their upper-tail counts, quantiles, and Bonferroni calculations. SQLite contained exactly 5,760 candidate, 366 comparison, and 488 control rows matching the JSON receipts; integrity and foreign-key checks passed. The audit made 22,354 assertions. Reproduction code and its compact result are in `scratch/audit_science.py` and `scratch/audit-result.json`.

| Primary metric | Baseline view | Mean paired-person rho | Raw greater-tail p | Six-test adjusted p |
| --- | --- | ---: | ---: | ---: |
| Geometry | Morphology | 0.081494 | 0.0005 | 0.003 |
| Geometry | Spectrum | 0.038146 | 0.0005 | 0.003 |
| Geometry | Coordination | 0.041861 | 0.0005 | 0.003 |
| Adjacent change | Morphology | 0.034249 | 0.0645 | 0.387 |
| Adjacent change | Spectrum | 0.014072 | 0.2800 | 1.000 |
| Adjacent change | Coordination | 0.027045 | 0.1065 | 0.639 |

All five paired-person geometry means are positive for each baseline view, but the observed mean correlations are small. None of the three change-profile tests meets the six-test adjusted threshold. The independent-phase control has person-balanced mean geometry rho 0.03334 and change rho −0.02781 against the original representation; phase invariance is not established. The gain, polarity, and channel-reversal controls are descriptive sensitivity probes, not formal invariance tests.

The repository suite, run in one numerical thread with the locked baseline dependencies, passed **65 tests; one optional checkpoint-dependent encoder test was skipped**. The focused distributed and pretrained study subset passed 12 tests. Static inspection confirms `infer` and `evaluate` still default to Experiment 009 and `prepare` retains the 009 path. The already published 009 output was not in this snapshot, so its bytes were not compared here.

## Scientific interpretation and limits

The reported p values are **conditional on the frozen cyclic-shift null**, with minimum Monte Carlo p of 0.0005. Shifts within a nonstationary 30-second EEG block may not be exchangeable; independent block draws also do not create five independent person-level replications. The small correlations and only five complete people limit the evidence to exploratory alignment of numerical shapes on already exposed recordings. The 48 candidate hours are the same first-four-hour source intervals studied in Experiment 008, and Experiment 009's initial ten-minute result was known before 010. This is no new-person or untouched-data validation.

The full raw four-hour eligibility computation, original waveform decoding, baseline feature recomputation, and the frozen model's 610 forward computations were **not** rerun. The checkpoint file was not supplied here; its official expected SHA-256 (`d9714b8732c9883a04d022ee66254cd578ae1fa27f5458e6ab7f1aa96e9a7352`) matches the inference receipt and protocol but not a locally inspected weight file. I did not use reserved participants `007`–`010` or later sessions. The frozen code's original encoder inputs are numeric; the phase-control seed is prescribed as `9009 + candidate_index`, so any public shorthand about complete metadata independence should describe that deterministic control detail accurately.

No universal token language, semantic state, diagnostic accuracy, pretrained generalization, or physical Neurable transfer follows from these results. Publication claims and package/source download integrity must be reviewed against their own sealed final snapshot before they can inherit this scientific verdict.
