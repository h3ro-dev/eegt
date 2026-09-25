# Experiment 009 final independent review

**Verdict: CHANGES_REQUIRED.** F1 and F3 are resolved in the 99-file input-v2 snapshot. F2 has one concrete package failure: `scripts/package_pretrained.py` now requires a root `styles.css` file that the snapshot does not contain. This review did not edit source or publish.

## Input and retained evidence

All **99/99** input-v2 manifest entries match. The original 94-file input also still matches. The 11 scientific source, protocol, prepared-array, inference-array, summary and SQLite hashes checked for this continuation are byte-identical to the initial reviewed snapshot. The [initial review](../input-v2/repo/results/009/review-initial.md) retains the independent recomputation of 54 segment metrics and 1,431 shift values (maximum differences `1.11e-16` and `2.22e-16`) and the real-block cross-host forward result (maximum `4.77e-6`, within `atol=rtol=1e-5`, not byte-identical). [FINAL-REVIEW.json](FINAL-REVIEW.json) contains the exact 99-file hash map.

## Findings

- **F1 resolved:** The new release gate checks every recorded inference code hash, requires all four model-source entries and 14 core reviewed paths, checks each hash in the accepted snapshot map, and refuses a packaged Python file absent from that map. The three fresh focused tests passed. An in-memory, clearly temporary accepted fixture also validated all 99 actual snapshot hashes; it was only a test fixture.
- **F2 remains open:** The package path list includes `styles.css` at repository root. That file is absent from input-v2/repo and its manifest. A package run in `scratch/package-fixture` with a temporary accepted fixture failed before tar creation: `FileNotFoundError: scratch/package-fixture/styles.css`. The root `pretrained.html` links to that CSS path. Add the intended root copy and bind it in a new manifest, or use a valid existing path in both package and page. Then run the package and exact extracted-bundle checks.
- **F3 resolved:** README now explains that EESM23 metadata reports 50 Hz mains while the fixed model recipe uses a 60 Hz notch, which does not specifically remove 50 Hz. It also uses unittest discovery for the standalone adapter command. STRATEGY only changed spacing.

The supplied general-suite log records 61 tests run, one skipped, after the three new tests. I ran only the three focused package-binding tests in this continuation; the full numerical and model-backed suites were not repeated. The final tar, extracted rerun, release and public readback remain **NOT_RUN** here and belong to root after F2 is corrected.
