# Experiment 012 independent final candidate review

**Status: ACCEPTED · Scope: FINAL_RELEASE · Candidate is not yet published.**

Reviewer native thread: `01a0dc45-5aa8-7f21-9138-a2437735cd5c` · Bead: `eco-uzwh8s.34.3`. This verdict covers the exact supplied candidate and its pre-review 2,979-file inventory. The original lead performs final packaging, publication and public readback.

The exact `package_events.object_sha(FINAL-FILES.json)` is `eb5992c8448aa5dabca8f0821015a89f1da66aa36ebeea7aa9df148470891742`. The packet manifest SHA256 is `ae0d00cf875606b2051bdd7e5b063271f6d7134ac6e2fadb6ca5ce35019700d7`; all 183 listed input files matched size and SHA256.

## Findings

| Finding | Disposition | Evidence |
| --- | --- | --- |
| R012-01 | RESOLVED | The unchanged release gate checks SQLite integrity, eight cardinalities, selected block and 122 x 23 variant identities, and exact disk/index/report partition coverage. The current 2,970-file staged inventory and extraction receipt agree exactly; accepted numerical index hash 427627c7... is reproduced by streaming the supplied gzip. Prior independent readback checked 48 night medians and all four participant tests on these unchanged bytes. |
| R012-02 | RESOLVED | The raw generated receipt and native stdout log are identical JSON; they report REPRODUCED, full summary, 122 blocks, 2,806 partitions and the same frozen manifest/index hashes. The wrapper binds generated receipt, extraction receipt, corrected staged manifest and native execution receipt by exact SHA256. Native receipt records exit code 0, the extracted cwd/runner, one numeric process and a 1,530.6 s wall interval. |
| R012-03 | RESOLVED | The unchanged final gate requires exact pre-review inventory, this independent review artifact, nonempty resolved dispositions, expected reviewer thread and a separate native completion handoff; it adds those final artifacts only after review. The supplied FINAL-FILES.json object_sha is bound here; root must verify this turn at the native source and supply its handoff after completion. |
| R012-04 | RESOLVED | Unchanged actual summary/public JSON/Experiment 012 article retain five complete people and 110 primary blocks per endpoint, four estimable inconclusive tests and explicit undefined controls. The home page now says two fixed pretrained EEG backbones; its site/root copies hash equally. |
| R012-05 | RESOLVED | Extractor preflights exact shards, canonical paths, member sets, types and sizes before output, then hashes extracted files and complete tree. Four extractor unit tests pass; staged membership covers each of 2,970 captured files exactly once and the root extraction receipt matches all files/assets. |
| R012-06 | RESOLVED | Corrected safe_name rejects Windows drive/colon paths, trailing dot/space components and reserved devices. Eight direct forbidden-name cases plus four coherent manifest/tar cases fail before destination creation; corrected extractor regression passes. The staged corrected extractor hash is bd5037e0382738a1ef5129c0dee804ab645cb666a1c5773dba8644782e413a5a. |

## Complete replay and staged extraction

The corrected `review-r2` stage manifest binds 2,970 captured files and three shards. Every staged file occurs in exactly one shard member list. Its embedded file-manifest hash is `54ed88f13783ad63315b39cc7b1ba5bfc3e45bcf0849079bc5d01bc88c4b78c1`. The checked extraction receipt has exactly the staged file and asset size/SHA maps.

The generated numerical receipt is `REPRODUCED`, `full_scientific_summary=true`, with 122 blocks and 2,806 partitions. Its frozen run-manifest hash is `3359e83c54cdd1bc58d74f9779610a42ebe0f6b626c0cd786ef7ba159cef7ce0`; its index hash is `427627c73149bce542b77ca152d2e0a4c0c32eb0b6b983839d360e8967c949bb`, independently reproduced by streaming the supplied SQLite gzip. The wrapper matches the raw generated receipt and binds that receipt, the extraction receipt, staged manifest and native execution receipt by SHA256. The retained native stdout log parses to the exact generated receipt JSON. The root execution receipt records the extracted working directory and runner, one numerical process, exit code 0 and 1,530.6 seconds elapsed.

This is evidence of the **root-run** extracted replay. I did not run another replay. The shard files and 2,806 partition files were not supplied locally; their complete byte identities were checked by the retained extraction receipt and replay. I directly hashed all 183 supplied packet files and 157 locally present inventory files. I also streamed the supplied SQLite gzip to verify its decompressed SHA256.

The final pre-review inventory contains 2,979 files. Exactly eleven disclosed files changed or were added after staging. `package_events.verify_stage_deltas()` accepted that actual map; it refused an undisclosed map and a synthetic change to the scientific summary. The final review artifact and the later native completed-turn handoff are intentionally absent from this pre-review inventory, avoiding a self-hash cycle.

## Source and report checks

The frozen run source files match the run manifest and staged release hashes. The summary, index gzip, reporter, experiment article, public JSON, Experiment 012 page and plot retain the hashes checked in the prior independent recheck. That recheck computed all 48 recording medians and four exact participant tests from `block_effect`: five complete people, 110 primary blocks per endpoint, adjusted p values 0.5, 0.25, 1 and 1. The home page now correctly describes two fixed pretrained EEG backbones; its root and site copies match byte for byte.

The corrected extractor rejects Windows drive and colon paths, trailing dot/space components, Windows reserved device names and POSIX traversal. Four corrected extractor unit tests passed, as did five focused package tests and two reporter tests. Eight direct unsafe-name cases and four coherent malicious manifest/tar cases were refused before any extraction directory was created. A broader `test_package*.py` discovery imported unrelated tests that require unavailable `pytest` and `eegt` imports in this review environment; the exact relevant modules passed separately. Python 3.14 emits a deprecation warning for `PureWindowsPath.is_reserved()`; the release reproduction environment pins Python 3.12.

## Exact reviewed input hashes

| File | SHA256 |
| --- | --- |
| `FINAL-FILES.json` | `eb5992c8448aa5dabca8f0821015a89f1da66aa36ebeea7aa9df148470891742` |
| `FINAL-PACKET-MANIFEST.json` | `ae0d00cf875606b2051bdd7e5b063271f6d7134ac6e2fadb6ca5ce35019700d7` |
| `FINAL-REVIEW-BRIEF.md` | `e16b89b0ed84da7bf003fcb953c0b49372bffa9f3472845c4f412aa583c95bb7` |
| `POST-STAGE-DELTAS.json` | `f2fa3988f01945c145b20d270aadbfcec394ccba3ea2e04d38c8f0444a1c1c59` |
| `analysis.sqlite.gz` | `75765b2aecc989d14a33bcb8c4ead8617eb1ac662eccfb4068412a7bac0cc480` |
| `dist/eegt-v0.8.0-review-r2-manifest.json` | `1ed73399dafc3a859860406bf6ea73298432435aa3311828c0754bfa455be6c8` |
| `repo/REPRODUCE-012.md` | `b1601a04efd471284f7e4ccca895131c29278ae957ceae421dad38f6e7a60fbb` |
| `repo/eegt/event_study.py` | `7bf41138c5525d11516c4a0609cd635c9e0093843efacb754fb4acd09bbcd566` |
| `repo/eegt/waveform_events.py` | `80a9b8f62693e551c7f385a911fa15ca321325b7983f63da8fc7373ba451f572` |
| `repo/index.html` | `2dc552d264a1ccdd3135ead4eb14af86b95171db5d31e59b2866f6e5caec2b5e` |
| `repo/notes/experiment-012.md` | `57ee803b6d6ef309e4b88f62a335b3d0ebb7d573745b9891a695afc047fa87b3` |
| `repo/notes/validation-012.md` | `301505e42c3a50fbf9a30cb14e21fb36d6042949d1aa938f011364bb61d18ccb` |
| `repo/protocol/experiment-012-methods.md` | `86f41254f1fc35a0d95e4e9aab45bec0e12d1964ec18d8a38a7d92c57daf92e9` |
| `repo/protocol/experiment-012.json` | `60f02a8dce9a086be3a89fe612eb9437088054f007d14348c827292fae34e138` |
| `repo/results/012/RUN-SOURCE-MANIFEST.json` | `3359e83c54cdd1bc58d74f9779610a42ebe0f6b626c0cd786ef7ba159cef7ce0` |
| `repo/results/012/code-review-r2/CORRECTION-001.json` | `2cd0dfef5ab70ca41f7cd69ee56d14838b7750c7636589198bb40b89bfa70eb8` |
| `repo/results/012/code-review-r2/NATIVE-CHECKPOINT.json` | `2600ef8194205ee7b582a8d2c174adf897bd638945aa103ea1c9fbd6dd6f32d3` |
| `repo/results/012/extracted-reproduction.json` | `33320cca43e031be80af0caa7ec4063c0328b45c6d3453561fb0c33592b463c0` |
| `repo/results/012/extraction-receipt.json` | `ae38d8ba0533d29ddd61c6bf6c30c241ee67db750324bd3451c360b68a6a9171` |
| `repo/results/012/generated-reproduction.json` | `8f316918c467ac5b24aa5ca8103f256d32362dcfda57355d036f9b0fa0e29ff5` |
| `repo/results/012/implementation-review/ACCEPTANCE.json` | `1e009e3866b6a52643ea3aa6c90812d7c09d2809f950bf88ab9d4dddb1a95379` |
| `repo/results/012/implementation-review/history/native-replay-r2.json` | `e22a4afdb5bd1f6f313a14ed34b2a07d8a3a4ef0ed5e48f4ee7e1d7bf7a684a0` |
| `repo/results/012/implementation-review/history/native-replay-r2.log` | `8f316918c467ac5b24aa5ca8103f256d32362dcfda57355d036f9b0fa0e29ff5` |
| `repo/results/012/implementation-review/history/run_transition_replay_r2.py` | `0410b3a07f61f216126285a2690c5ecf0c1f51081d50370b0547ee2f61cd92fe` |
| `repo/results/012/implementation-review/history/stage-review-r2-manifest.json` | `1ed73399dafc3a859860406bf6ea73298432435aa3311828c0754bfa455be6c8` |
| `repo/results/012/implementation-review/independent-numerical-check.json` | `f3685d6733a53136883cd8830b063a2a48cddc15532cfa0311b0d1a6f35acfb1` |
| `repo/results/012/run-progress.json` | `e542a9baae15e4032c3f4c79b56959d1da84ff99275f452731db378c3f772829` |
| `repo/results/012/summary.json` | `88ff8692d94a67f849e8b3537e461ec329f5696ac1df93b5e8a16bf766cddb6f` |
| `repo/scripts/extract_event_assets.py` | `bd5037e0382738a1ef5129c0dee804ab645cb666a1c5773dba8644782e413a5a` |
| `repo/scripts/package_event_assets.py` | `02b77c2d87f4a8cd35b4b83cc99b7b0fcb78e37b300a815d7bafa2ddb07900c8` |
| `repo/scripts/package_events.py` | `20e37581ea0e4e90f53225f8f6aac4eacab995bb1f27d8767f892d56523c4168` |
| `repo/scripts/report_events.py` | `c864d59aafaa59cb4f27c674bb8eb87dafa761e7dc4c5a9252149b3a25739f92` |
| `repo/scripts/reproduce_events.py` | `7c819c8460537d7afe36746ad342f473d03bf187ddadc4a9d7ccb84b7772ad29` |
| `repo/site/data/events-summary.png` | `361108b9cbaae7415369a8344f425a187470babc21a291b43dae69be380f1c34` |
| `repo/site/data/events.json` | `34696db66fbf5c6a2927e95b4d4023323d2ad2e0046c9ae41cd47b748d09da8d` |
| `repo/site/events.html` | `e55adc9ad1ac993c1ac5c66420f8052e1e79ad6b2390c93a720cbc8c99974c35` |
| `repo/site/index.html` | `2dc552d264a1ccdd3135ead4eb14af86b95171db5d31e59b2866f6e5caec2b5e` |
| `repo/tests/test_extract_event_assets.py` | `1c1e9065cdb68e76dafab4865a5fb08d58243996091b5ec1bff607e6ec2e903f` |
| `repo/tests/test_package_event_assets.py` | `6ec8e4bc9b45edda2102bc40d4348741aee8d4b2ff7eb3626e7f7c76b30faa42` |
| `repo/tests/test_package_events.py` | `308c531ccd527cbc208237625fe031e4e074e29299c96b23e6418069d0d9366d` |
| `repo/tests/test_report_events.py` | `941684aad73da7e5450102b4bd01f3b0754c680e3a467700127538905be07958` |
| `review-r1/REVIEW.json` | `a09f60056c0e418b1e1f887a1a63c6c457e9d80bd5539162a6987dcf67c399d9` |
| `review-r2/RECHECK.json` | `2b15bcb47015dfb2ef0d4603b58d03bf75215a64f7994a51846c4894ad974b06` |
| `review-r2/recomputed-primary.json` | `07b2c086e5da9362c53dfb95061d9303b5f477a1a100a03ef1965548440dba91` |

The exact eleven-row post-stage map is embedded in `REVIEW.json`; `POST-STAGE-DELTAS.json` has SHA256 `f2fa3988f01945c145b20d270aadbfcec394ccba3ea2e04d38c8f0444a1c1c59`.

## Reproduction commands

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Users/studio1/lanes.noindex/eco-uzwh8s.34.3/scratch/final-r3 python3 -B -m unittest discover -s repo/tests -p 'test_package_event_assets.py' -v
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Users/studio1/lanes.noindex/eco-uzwh8s.34.3/scratch/final-r3 python3 -B -m unittest discover -s repo/tests -p 'test_package_events.py' -v
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Users/studio1/lanes.noindex/eco-uzwh8s.34.3/scratch/final-r3 python3 -B -m unittest discover -s repo/tests -p 'test_report_events.py' -v
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Users/studio1/lanes.noindex/eco-uzwh8s.34.3/scratch/final-r3 python3 -B -m unittest discover -s repo/tests -p 'test_extract_event_assets.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -B scratch/final-r3/adversarial_paths.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scratch/final-r3/verify_evidence.py
```

## Verification limits and handoff

I did not open reserved people or sessions, acquire raw data, call models, rerun detectors or run the full empirical or extracted numerical replay. The original lead owns publication, final package execution and public download/page readback. This review accepts the release candidate and supplies the evidence artifact for that gate; it is not proof that a public release exists.

After this reviewer turn completes, the lead must verify its native completed status, store this review under `results/012/release-independent-review/`, bind the real native handoff in `release-review.json`, and run the final gate. I have not created that future native receipt. Native monetary cost is UNKNOWN; no paid API or per-window model work occurred in this review.
