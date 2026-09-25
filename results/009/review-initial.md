# Experiment 009 independent review

**Verdict: CHANGES_REQUIRED.** The archived computation and abstention are supported by the bounded checks below. Three concrete release and documentation gaps need correction before the v0.5.0 package is accepted. This review made no source edit or publication.

## Input binding

The snapshot manifest SHA-256 is `b0a9d0c2d429b094ccf84a3c9386fc18375c6745972d95f7bf53f549276e7e4c`; all **94/94** listed repo files matched. The official source ZIP is `4ebe7c8324a7a03e6cd54b7aa417bc65881d0c34bfc1089194f19c7ea8739805`. The copied 60,901,006-byte checkpoint matched the pinned SHA-256 `d9714b8732c9883a04d022ee66254cd578ae1fa27f5458e6ab7f1aa96e9a7352` before use. Exact hashes for every snapshot file, plus the brief, plan and fleet context, are in [REVIEW.json](REVIEW.json).

The protocol SHA-256 is `5c45dc42d237b89653909bf536f3cf44927a28303f808ac1d0bc48b2c00562f1`. Its recorded freeze at 17:21:25 UTC preceded preparation at 17:32:43 and inference at 17:44:52. This proves the internal recorded order; an external timestamp attestation was not supplied. The protocol fixes 12 exposed recordings, first 600 seconds, 20 nonoverlapping 30-second blocks per recording, no replacement, three eligible blocks per night and at least three complete two-night participants.

## Verified computation

- All 240 candidates remain; 9 are eligible and 231 rejected. Rejection reasons overlap: baseline QC 171, nonfinite native samples 70, amplitude over 100 µV 160. Each eligible prepared array, all three descriptors, every variant input and all 45 archived outputs matched its row hash.
- The 28 retained patch centers align with the 28 frozen descriptor centers; the change comparison uses 27 within-block adjacent steps. Independent SciPy distance and rank-correlation code recomputed all **54** archived segment metrics and **1,431** cyclic-shift values. Maximum absolute differences were `1.11e-16` and `2.22e-16` (acceptance tolerance `1e-9`).
- SQLite passed `integrity_check` and `foreign_key_check`: 240 candidates, 27 comparison rows, 36 control rows. Only two individual recordings have three blocks, in different people/nights. **Zero** people have three blocks on both nights. All six planned primary comparisons correctly abstain, with no p values or participant effect. The code's nested record → two-night person → person-mean aggregation, blockwise shifts, seed 9009 and Bonferroni six-way rule match the protocol; inferential null draws were correctly not run.
- The pinned ZIP diff contains only the relative import and CPU mask-device change; SGConv and Apache LICENSE are byte-identical. The wrapper verifies checkpoint size/hash before `weights_only=True`, strict-loads 269 tensor keys, freezes/evaluates the model and preserves the full `[B,4,30,200]` output. Fresh focused suites passed **14/14** (7 study, 7 adapter), including one original-source CPU forward. The first test collection lacked `opt-einsum`; its pinned version was installed and the full focused run then passed.
- A fresh actual forward for archived candidate 26 used the recorded input. The archived output's hash matched its receipt. The new host's output was within `atol=rtol=1e-5` of all 24,000 archived values (maximum absolute difference `4.77e-6`, mean `8.00e-7`), but was not byte-identical and did not satisfy `1e-6`. The original-source comparison passed on this same host.

## Required changes

1. **Bind release source to the recorded run.** [package_pretrained.py](../input/repo/scripts/package_pretrained.py) checks receipt `inputs` maps and review status, but it does not check `inference.code_sha256`. The wrapper, vendored SSSM and SGConv could change before packaging without this gate rejecting them. Verify those three recorded digests and the accepted review's input hashes against the exact packaged files, then rerun the release check after changes.
2. **Make the documented bundle rerun work.** [README.md](../input/repo/README.md) tells a reader to run `scripts/report_pretrained.py` from the data bundle. The packager omits `site/`, while that script writes `site/data/pretrained-eligibility.png` without creating its parent. Include/create the needed directory or direct readers to a complete checkout, then test the instruction from the final extracted tar.
3. **Add the 50/60-Hz caveat to README.** All twelve source metadata rows say 50-Hz mains. The fixed recipe applies a 60-Hz notch, which does not specifically remove 50 Hz. The Research Note and site say this; README's Experiment009 section should say it too.

The Research Note and site otherwise describe a fixed-weight backbone only, 19-scalp-to-four-ear spatial limits, unknown pretraining overlap, descriptive nine-row observations, possible calibration in the first ten minutes, and no clinical, semantic, universal or physical Neurable result. The public result does not pool segment p values.

## Not run and handoff

Raw EEG and reserved waves were not opened, so raw-to-prepared source decoding was inspected in code rather than independently replayed. Root's reported 57-pass general suite and one optional skip were not rerun; its log was absent from the snapshot. The final tar, release, and live site readback remain **NOT_RUN** in this lane. Root owns correction, integration, final package verification and publication.
