# Experiment 010 final correction review

**Verdict: ACCEPTED for the sealed v6 source and publication copy.** Root remains accountable for building and extracting the actual accepted archive and checking the public release and page bytes. This reviewer changed no canonical or snapshot file and made no public send.

The final input is `input-v6/repo`, bound by `input-v6/MANIFEST.json` SHA-256 **`e3386f15d1683e61267d20255a1b983d5f310a70f37ff76fa6f533de9a716de6`**. I verified the exact set and SHA-256 of all **93** listed files. The companion JSON has every input-v6-relative path under `input_hashes.snapshot_files_sha256`. Compared with v4, exactly seven publication paths changed and two prior review artifacts were added. All numeric code, protocol, derived arrays, results, plot data, package code, and tests are unchanged. The archived v4 review, science review, audit result, and historical audit source match this reviewer's retained artifacts byte for byte.

## Correction findings

1. **P1 resolved.** Both homepage copies now identify notebook 001—010 and current protocol 010. “Read current notes” opens `distributed.html`; only the 010 card carries the current marker. The data-release link targets v0.6.0.
2. **P2 resolved.** The current rendered study directly links EESM23 version 1.0.0, the primary dataset paper, pinned CodeBrain source and pinned weights. The homepage source list includes EESM23 and CodeBrain.
3. **P3 resolved for the requested branding.** James's exact phrase “An LLM’s interpretation of your brainwaves” remains labelled **Project subtitle** on the study, homepage, and README. Each immediately explains that this experiment uses continuous EEG embeddings, runs no LLM decoder, and makes no thought-interpretation claim. The measured claims remain numerical and bounded.
4. **P4 resolved for the affected current documents.** `CITATION.cff` refers to the included `notes/experiment-010.md`. README's older cards and unbundled documents use stable public v0.6.0 links; its 11 local links resolve inside the 93-file snapshot. Current reproduction files are included. The unchanged packager gate is inherited from the v4 check.

## Verification inherited and repeated

`scripts/report_distributed.py` was rerun in a scratch copy with one numerical thread. Its Research Note, both HTML copies, both JSON copies, and both PNG copies match the v6 snapshot **byte for byte**. Root and site HTML copies are identical. The current public JSON has 5,760 candidate blocks, 2,973 quality passes, 2,851 qualified unselected, 2,787 rejected, and 122 selected; five paired people contribute 110 selected blocks to each primary comparison. The original inference receipt reports 610 forwards.

The unchanged scientific inputs inherit the independent science audit: **22,354 assertions**, all 732 selected-block comparisons, 19,398 cyclic-shift values, 488 control comparisons, 11,994 null draws, and SQLite's 5,760/366/488 rows with integrity and foreign keys checked. The geometry mean correlations remain 0.0815, 0.0381, 0.0419 (six-test adjusted p = 0.003 each); change correlations remain 0.0342, 0.0141, 0.0270 (adjusted p = 0.387, 1.000, 0.639). These are weak, conditional results from five already exposed paired people. No universal, semantic, diagnostic, or physical Neurable result is established.

The package scripts and release-gate tests are byte-identical to v4. Four release-gate tests passed then, and a scratch-only **synthetic** accepted-review fixture verified 90 archive members and two checksum lines. The root general-suite receipt reports 66 passes plus one optional encoder skip. None of those proofs is an actual v6 production archive acceptance.

## Limits and root handoff

The original raw four-hour eligibility computation and waveform decoding were **NOT_RUN independently**; no encoder forward or weight-file read was performed here. Full model compatibility was reviewed previously in Experiment 009. The cyclic-shift p values assume within-block exchangeability, which nonstationary EEG may violate; five people and previously examined data limit generalization. The archived `reviewer-audit-source.txt` is a historical audit script tied to the original reviewer directory layout; the portable reproduction entrypoints are `eegt.distributed_study` and `scripts/report_distributed.py`.

Root must place this receipt at `results/010/independent-review`, then build and extract the actual accepted archive and read back the public release and page bytes. Those checks are **NOT_RUN_BY_REVIEWER**. The validation note's future local review-receipt link becomes available only after that root integration. Three historical relative references in unchanged `STRATEGY.md` target files outside the bounded bundle; they are unrelated to the 010 reproduction path and remain a minor archival-navigation limitation.
