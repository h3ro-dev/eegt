# Experiment 012 publication and packaging code review

**Verdict: CHANGES_REQUIRED (code scope only).** The five requested stdlib tests pass. Synthetic fixtures expose three release-gate failures and two reporting/extraction risks. This does not assess the healthy numerical run or accept a release.

## Reviewed source SHA256

| File | SHA256 |
| --- | --- |
| `INPUT-MANIFEST.json` | `5c8044c150698b3cb0b984bcba48c71d73d6fad3742647f74a02fc27d515088e` |
| `prior-review/analytic-check.json` | `09b501f064c46e6185bc5e81e5b944d37701829dda662053c6103935e43a60e6` |
| `prior-review/REVIEW-DISPOSITIONS.json` | `3d31561c94032635d986ff16a98c0c1406376739c352c597e713e8f6bc6d5857` |
| `repo/REPRODUCE-012.md` | `0fe2bd67c2516433ff65dec46fdaa7e388a54ff0a2aeceb1d146f830ed62088b` |
| `repo/eegt/event_study.py` | `7bf41138c5525d11516c4a0609cd635c9e0093843efacb754fb4acd09bbcd566` |
| `repo/protocol/experiment-012-methods.md` | `86f41254f1fc35a0d95e4e9aab45bec0e12d1964ec18d8a38a7d92c57daf92e9` |
| `repo/protocol/experiment-012.json` | `60f02a8dce9a086be3a89fe612eb9437088054f007d14348c827292fae34e138` |
| `repo/results/012/RUN-SOURCE-MANIFEST.json` | `3359e83c54cdd1bc58d74f9779610a42ebe0f6b626c0cd786ef7ba159cef7ce0` |
| `repo/scripts/package_event_assets.py` | `63aea692b276cfe51bdada07ca7113e46a34ee4cd3aba833fa04ac427e7732b7` |
| `repo/scripts/package_events.py` | `7ed3cdf6508ee5597c9b13c6859bed0e3c273ab85580e86b604b7cde8d9254e7` |
| `repo/scripts/report_events.py` | `e60f28bdad1c9177b32bc320f2a8576c9b9447d942e874a508449516502d7c87` |
| `repo/scripts/reproduce_events.py` | `7c819c8460537d7afe36746ad342f473d03bf187ddadc4a9d7ccb84b7772ad29` |
| `repo/tests/test_package_event_assets.py` | `8584260fd701acf98bdd41d06cf732ec65841ce63acd7588fc46a62d906eb467` |
| `repo/tests/test_package_events.py` | `0c9cc78bfeda7e4fb607bfa44c9d28fa93c0fa14cb64980bbb62a1345ee3654a` |
| `repo/tests/test_report_events.py` | `67f6bfdcbb7928c0d6c2fdc0285da2d514f16928c2dac13ce3a737c65c44f997` |

## Findings

### R012-01 · P1 · Completeness gate trusts self-reported counts and artifact list

Source: `repo/scripts/package_events.py:68`, `repo/scripts/package_events.py:73`, `repo/scripts/package_events.py:77`, `repo/scripts/package_events.py:99`.

Evidence: verify_science compares fixed counts only to out/REPORT.json and checks hashes only for entries REPORT lists. Its SQLite check is PRAGMA integrity_check, not row cardinality or partition-file coverage. The synthetic probe passed with an empty SQLite table, artifact_files={} and a REPORT frozen_manifest_sha256 of 64 zeroes.

Impact: A malformed or stale candidate could be packaged while the release claims all 2,806 partitions and 122 blocks. This does not imply the current numerical run is incomplete.

Required change: Independently query the SQLite table counts and expected identities, enumerate every indexed partition and require its path, size and SHA256, and compare that complete set with REPORT and the candidate archive inventory. Bind the run manifest digest to the report and accepted source.

Reproduce: `PYTHONDONTWRITEBYTECODE=1 python3 -B scratch/adversarial_review.py`.

### R012-02 · P1 · Extracted reproduction gate accepts an unbound assertion

Source: `repo/scripts/package_events.py:93`, `repo/scripts/package_events.py:97`, `repo/scripts/reproduce_events.py:590`.

Evidence: verify_science accepts extracted-reproduction.json when status, full_scientific_summary, 122, 2806 and run_manifest_sha256 match. It does not inspect the replay index_sha256, a hashed reproduction receipt, or the archive that was extracted. The synthetic probe passed with replay index_sha256 set to 64 zeroes.

Impact: A stale or hand-authored replay assertion can satisfy the final package gate without proving the staged archive was extracted and replayed.

Required change: Bind the gate to the exact generated reproduction receipt and index hash, the staged asset-manifest hash and the isolated extraction path; have the independent reviewer verify the extraction and receipt. Permit only the documented review/replay additions between staged and final payloads.

Reproduce: `PYTHONDONTWRITEBYTECODE=1 python3 -B scratch/adversarial_review.py`.

### R012-03 · P1 · Independent-review gate has no reviewer provenance

Source: `repo/scripts/package_events.py:108`, `repo/scripts/package_events.py:118`, `repo/tests/test_package_events.py:16`.

Evidence: verify_review accepts only status==ACCEPTED and an equal files mapping. The existing unit test and synthetic probe both pass an object containing only those two fields. No reviewer identity, reviewed source digest, native handoff receipt or finding disposition is required.

Impact: The package command can label a release reviewed from a locally written assertion, so the gate itself does not establish independent acceptance.

Required change: Require a source-bound independent review artifact with reviewer/session identity, scope, exact inventory digest, review artifact SHA256 and dispositions; verify that against the native handoff before final packaging. Treat a status field alone as insufficient.

Reproduce: `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s repo/tests -p test_package_events.py -v`.

### R012-04 · P2 · Two public inference sentences are fixed instead of checked against results

Source: `repo/scripts/report_events.py:69`, `repo/scripts/report_events.py:117`, `repo/scripts/report_events.py:119`.

Evidence: The report always says at most five complete people and all 100 noise trials have cycle detections in every band/type. primary_rows supports six complete people, and collect reads actual scored and detection counts, but run does not use these values to validate the prose. The synthetic primary-row probe yields six complete people.

Impact: If the complete result differs, the HTML and note can state a false sample size or control result while the machine-readable table is correct. Actual results were not supplied in this checkpoint.

Required change: Derive the sample-size p-value-resolution sentence and noise-control sentence from collected values, or fail rendering when a deliberately fixed claim is not met. Confirm against the actual complete output at the later checkpoint.

Reproduce: `PYTHONDONTWRITEBYTECODE=1 python3 -B scratch/adversarial_review.py`.

### R012-05 · P2 · Public extraction instructions do not reject unexpected archive members

Source: `repo/REPRODUCE-012.md:8`, `repo/REPRODUCE-012.md:24`, `repo/scripts/package_event_assets.py:121`.

Evidence: The writer itself rejects unsafe names and verifies emitted members. The published steps extract downloaded tar files before checking each member path/type, then hash only names listed in FILE-MANIFEST.json. A synthetic extracted directory with one correct listed file and an extra unlisted Python file passes that exact listed-file loop.

Impact: The public verification command cannot prove an extracted tree has only approved files or that each shard has the advertised member set. This concerns downloaded-asset verification; it is not evidence that the writer emits unsafe members.

Required change: Before extraction, verify each shard hash against a trusted release manifest, reject absolute/traversal/link/duplicate/unlisted members, require shard names and member sets to equal the release manifest, and after extraction require the complete tree to equal FILE-MANIFEST.json.

Reproduce: `PYTHONDONTWRITEBYTECODE=1 python3 -B scratch/adversarial_review.py`.

## Checks

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s repo/tests -p 'test_package*.py' -v` — 4 passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s repo/tests -p 'test_report_events.py' -v` — 1 passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B scratch/adversarial_review.py` — synthetic findings reproduced; no empirical runner or data.

## Verified boundaries

- primary_rows counts paired-valid blocks only for COMPLETE people and retains the all-person count separately.
- null native agreement stays undefined when the pooled denominator is zero.
- the tar writer checks canonical paths, symlinks, source hash/size, written member inventory, per-member hash, deterministic gzip metadata, size bounds and existing outputs.
- the published reproduction command preserves the packet/repo layout expected by reproduce_events.py.
- source-curator identity joins occur after numerical block effects in the frozen event_study.py.

## Required later checkpoint

- Root correction and independent recheck of affected source/tests.
- Actual 122-block numerical acceptance and complete archive inventory review.
- Fresh source-bound staged/final archive extraction and exact offline replay.
- Final public page and download readback.

No reserved data, empirical output, actual archive, public page, model run, publication or canonical repository modification was inspected here.
