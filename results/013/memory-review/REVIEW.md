# Experiment013 memory correction source review

**Verdict: ACCEPTED for the exact v2 two-file overlay.** This accepts the qualification and quality allocation-lifetime source correction for root integration. It does not accept the still-DRAFT manifest as an executable seal, validate all 20 reserved records, complete Experiment013 validation, or authorize publication.

## Exact source and contract

The original packet's 583 files matched `INPUT-MANIFEST.json` without a missing or mismatched byte/hash. Its 63 accepted original source bindings and the candidate63 bindings matched the actual files. The v1 patch reproduced the v1 files byte for byte. The v1 review was **CHANGES_REQUIRED** because the quality decoder kept its embedded cache live through the resource gate; see [V1-REVIEW.md](V1-REVIEW.md).

The packet's `AGENTS.md` carries policy 2026-09-24.4; James's supplied replacement policy 2026-09-26.1 governed this continuing review.

The root's v2 overlay changed only `eegt/validation_intake.py` and `tests/test_validation_intake.py` relative to v1. The source hashes are `eb9cdbe5bc464d7ff4f3a56ab5c0bacd8189933e174d50b1c6f50ec05bd0b4cf` and `5431a2a821e80af6df62e068f4dc5a5bccfd6c73357c10600d770c79f5ac195b`. The v2 draft hash is `8487b401f816bf26eb65ab22a389c680ccffdfe5fe4c70bb98b1f7998fff9e19`. Every `FILES.json` hash and all 63 v2 source bindings matched actual bytes. The original accepted seal hash remains `3c62792612383e548cb358aa3ed7090cc0bd74ee39853b322c2dd71c1978c03e`.

The v2 source adds `del raw; gc.collect()` in quality's existing `finally` block after `raw.close()` and before feature extraction. Qualification's `gc.collect()` before `guard.after_record` remains unchanged from v1. All scientific protocol, source-list, qualification fields, cohort/mask/numeric code, runtime/model bindings, first-record gate, and the 2,147,483,648-byte RSS limit are unchanged. The draft still says `DRAFT_RESOURCE_AMENDMENT_NOT_EXECUTABLE` and names the original seal digest. [v2-packet-audit.json](raw/v2-packet-audit.json) and [v2-diff.patch](raw/v2-diff.patch) record the exact changed bytes; [packet-audit.json](raw/packet-audit.json) contains the full original packet inventory.

## Independent behavior checks

The original raw diagnostic logged 11 repeats and stopped at the first original process peak above 2 GiB, 2,265,186,304 bytes. Its 12 cleanup repeats stayed at or below 804,323,328 bytes. All old/new output hashes equal `beaaf226d72b9988b6893a9a8f95809a8e8dc95fdbc3e45d635023555355ede0`, and the ten returned fields equal the archived Experiment008 001/001 qualification row. My single-process twelve-read diagnostic through the v1 qualification loop used only scratch copies of this exposed waveform and reached 811,368,448 bytes, with all ten fields equal. V2 leaves that code unchanged, so this proof remains applicable; I did not rerun it.

The new quality regression failed against v1 at the live decoder reference assertion and passed against v2 with the pinned Python 3.12.14 / MNE 1.13.2 corpus runtime. The changed-path intake, resource and provenance suite passed: **16 passed, 1 optional skip, 9 subtests passed**. A bounded two-read MNE-only probe on the same exposed fixture showed the 121,645,440-byte embedded cache and `raw` both unreachable after each v2 close/delete/collect boundary; the two transformed array SHA-256 values matched. Its peak was 620,527,616 bytes by process resource accounting (620,560,384 bytes by `/usr/bin/time -l`), below the unchanged 2 GiB check. These are fixture and source-boundary checks, not an empirical quality or preparation run. Raw independent logs are under [out/raw](raw).

## Release boundary and remaining proof

The amendment contract retains the pre-access commit and seal, original first-record admission and failed-attempt logs, states that technical exposure before failure is an **unknown subset of the acquired 20 records**, and requires fresh profiles/admissions under an additive accepted seal before empirical execution. The packet directly verifies the sealed manifest bytes; the external failed-attempt report/resource files named by hash in `evidence/REPORT.json` were not shipped in this lane for independent byte recheck. Root must verify their retained native copies, add the exact final v2 bindings and exposure state to the accepted amendment, and perform the staged 20-record checks. No corrected-source pre-access timing is claimed.

Preparation still builds per-record temporary groups and intentionally retains selected arrays for its final archive. No preparation stage was run; its actual peak and whole-corpus fit remain unknown. The existing resource checks and root's staged admissions remain the execution gates. The native dispatch receipt for this review records Sol Max on Studio1 under a held launch lock for a 2 GiB RAM demand; fresh seven-host exporter coverage and direct local measurements were recorded before the numerical probes. Dollar cost is **UNKNOWN**.
