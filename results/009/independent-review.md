# Experiment 009 independent acceptance

**Status: ACCEPTED** for the reviewed source and assembled 100-file snapshot. The earlier F1 and F3 fixes remain accepted. The supplemental root `styles.css` closes F2 without a scientific source or result change.

The supplement's `styles.css` has SHA-256 `e5c9d68f01daadae9d58fc49237eacd7bf26e8d0772412a5e0539f58fd5a0fe1`, exactly matches its one-file manifest, and is byte-identical to the already-reviewed `site/styles.css`. All 99 original input-v2 files still match their manifest. [ACCEPTANCE.json](ACCEPTANCE.json) contains the combined **100-file** `input_hashes.snapshot_files_sha256` map; the acceptance receipt itself is excluded from that map.

With the CSS added only to `scratch/package-fixture`, an explicitly temporary accepted receipt and Git commit let `package_pretrained.run` complete. Its **test-only** tar was 5,323,495 bytes (SHA-256 `2b8cfa62054c86a2e3179645b8885b49fe9d90be747ee05b6fc484270f2fdc45`). All 91 extracted members matched the package manifest, including both CSS paths, both page paths, JSON and plot assets. All six primary statuses remain `INSUFFICIENT_PARTICIPANTS`.

The [initial review](../input-v2/repo/results/009/review-initial.md) remains the numerical evidence: 54 segment comparisons and 1,431 shift values independently matched to floating-point precision; a fresh real forward differed by at most `4.77e-6` and passed `atol=rtol=1e-5`, without byte identity. The 11 scientific files checked in the prior continuation remain byte-identical to the original snapshot. Those tests were not repeated.

This acceptance covers the reviewed code and combined snapshot. The fixture tar hash and fixture Git commit are **not** production release identifiers. Root retains the final real-repository tar build, exact extracted-bundle evaluate/report/full suite, bundle-verification receipt, release, and public readback. This reviewer made no source edit or publication.
