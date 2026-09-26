# Experiment 012 independent recheck, checkpoint 2

**Verdict: CHANGES_REQUIRED for the exact code packet reviewed here.** The actual report and corrected release gates pass this bounded review except for one public extractor path escape on Windows. This is not final release acceptance. Root reports a canonical correction, but its changed bytes are outside this immutable packet and need a fresh review.

Native reviewer thread: `01a0dc45-5aa8-7f21-9138-a2437735cd5c` · Bead: `eco-uzwh8s.34.3` · review scope: code and available actual report only.

## Prior finding dispositions

| Finding | Disposition | Evidence |
| --- | --- | --- |
| R012-01 | Resolved in reviewed code | Direct read-only SQLite integrity, eight cardinalities, selected block identities, 122 × 23 variant keys, every partition hash and exact disk/index/report coverage. A synthetic fake COMPLETE report with an empty index is refused. Actual index counts pass. |
| R012-02 | Implemented; native replay pending | Final mode requires `ACCEPTED`, 122 blocks, 2,806 partitions, frozen manifest and index identity, a generated receipt, verified staged extraction receipt and manifest, and every staged asset hash. Forged wrapper alone is refused. The full extracted replay was not supplied here. |
| R012-03 | Implemented; native final review pending | Review gate binds the exact pre-review inventory, artifact digest, dispositions, expected reviewer thread and native handoff fields. Review artifacts are added afterward to avoid a self-hash cycle. The local native JSON checks structure and hashes; its authenticity must be checked at the actual native channel in the next checkpoint. |
| R012-04 | Resolved and checked against actual results | The inference and noise prose follows current values. The primary table includes five complete people and 110 blocks per endpoint; person 003 remains visible as incomplete. Four tests are estimable; none has adjusted p below 0.05. |
| R012-05 | Partly resolved | Preflight rejects missing, extra, duplicate, link and POSIX traversal members before writing; synthetic malformed archives were refused. Windows drive-qualified names remain accepted in this packet, as R012-06 details. |

## New finding

**R012-06 · P1 for the public extractor · Windows path escape.** `safe_name()` in `repo/scripts/extract_event_assets.py` uses `PurePosixPath`. Both the release writer and extractor accept an archive member named `C:/escape.txt`. On Windows, `Path("extracted") / "C:/escape.txt"` resolves to `C:\escape.txt`, outside the requested destination. A trusted current release inventory appears free of these names, but the public extractor claims path safety and accepts a constructed manifest plus shard containing one. Reject drive-qualified and colon-bearing names before extraction, and cover the case in tests. The lead reported a canonical fix and new regressions; that version has not been received or reviewed in this packet.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B - <<'PYCODE'
import sys
from pathlib import PureWindowsPath
sys.path.insert(0, "repo/scripts")
from extract_event_assets import safe_name
safe_name("C:/escape.txt")  # wrongly accepted in reviewed source
print(PureWindowsPath("extracted") / "C:/escape.txt")  # C:\escape.txt
PYCODE
```

## Actual results and public report

The 468,275,200-byte SQLite index decompressed from the sealed archive has SHA256 `427627c73149bce542b77ca152d2e0a4c0c32eb0b6b983839d360e8967c949bb` and passes `PRAGMA integrity_check`. It contains 5,760 candidates, 2,806 partitions, 8,296 native timelines, 99,552 native matches, 2,440 prepared metrics, 488 block effects, 5,368 morphology rows and 122 completed blocks. The native primary branch has 1,991,157 event candidates, 1,213,086 accepted and 778,071 rejected.

Using only `block_effect` and the published recording boundaries, I independently recomputed all 48 night medians and the four five-person exact sign-flip tests. Each endpoint uses 110 blocks from complete people, while all 122 paired valid blocks remain recorded. The raw/adjusted p values are:

| Encoder | Metric | Raw p | Adjusted p |
| --- | --- | ---: | ---: |
| codebrain | geometry | 0.125 | 0.5 |
| codebrain | change | 0.0625 | 0.25 |
| cbramod | geometry | 1 | 1 |
| cbramod | change | 0.875 | 1 |

The prepared public JSON exactly matches `report_events.collect()` on the available summary, progress and index. Exact-row assertions passed for all four primary tables in the prepared public note and HTML. They accurately state the 122/110 block distinction, four inconclusive adjusted tests, noise controls, undefined direct geometry and separate native/prepared support. The plot visibly has four panels with five complete-person dots and matching adjusted p labels. At 25 ms, the independent-phase control has 1,952 defined strata and pooled agreement from 308,603 matches; `passband_0p5_40` has 1,952 undefined strata, which the prose does not score as zero or perfect.

## Checks and reproduction

All ten focused stdlib unit tests passed: five package tests, two reporter tests and three extractor tests. Nine extra adversarial cases in `scratch/adversarial_r2.py` passed, including fake run counts, missing replay proof, undisclosed stage changes and malformed tar members. The independent readback script passed for all four primary tests.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s repo/tests -p 'test_package*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s repo/tests -p 'test_report_events.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s repo/tests -p 'test_extract_event_assets.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -B scratch/adversarial_r2.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scratch/recompute_primary.py
```

To recreate the scratch index from the sealed review packet:

```sh
python3 - <<'PYCODE'
import gzip, shutil
from pathlib import Path
with gzip.open('analysis.sqlite.gz', 'rb') as src, Path('scratch/analysis.sqlite').open('wb') as dst:
    shutil.copyfileobj(src, dst, 1024 * 1024)
PYCODE
```

## Exact reviewed hashes

All 58 entries in `RECHECK-MANIFEST.json` matched their declared size and SHA256. The manifest itself is `ad58eb6ea1907ece1e701a94e95c5ddb838e7023b90d066a43b76f36338fcb82`. The exact files used for this verdict are:

| File | SHA256 |
| --- | --- |
| `RECHECK-BRIEF.md` | `33364694c7a771833abae1bee465e9781092e0ec9cbbc70b5bc9e11eaab08709` |
| `RECHECK-MANIFEST.json` | `ad58eb6ea1907ece1e701a94e95c5ddb838e7023b90d066a43b76f36338fcb82` |
| `analysis.sqlite.gz` | `75765b2aecc989d14a33bcb8c4ead8617eb1ac662eccfb4068412a7bac0cc480` |
| `repo/REPRODUCE-012.md` | `b1601a04efd471284f7e4ccca895131c29278ae957ceae421dad38f6e7a60fbb` |
| `repo/notes/experiment-012.md` | `57ee803b6d6ef309e4b88f62a335b3d0ebb7d573745b9891a695afc047fa87b3` |
| `repo/notes/validation-012.md` | `2013f0aea5535509a1af7e17241c9a5a9b5380cfb42031cb6e43b4fa8b01de86` |
| `repo/protocol/experiment-012-methods.md` | `86f41254f1fc35a0d95e4e9aab45bec0e12d1964ec18d8a38a7d92c57daf92e9` |
| `repo/protocol/experiment-012.json` | `60f02a8dce9a086be3a89fe612eb9437088054f007d14348c827292fae34e138` |
| `repo/results/012/RUN-SOURCE-MANIFEST.json` | `3359e83c54cdd1bc58d74f9779610a42ebe0f6b626c0cd786ef7ba159cef7ce0` |
| `repo/results/012/implementation-review/ACCEPTANCE.json` | `d3e7c255e82e703a2e0630d2ba04c708e239befab2e23e1f56a14e2dc3d9401b` |
| `repo/results/012/implementation-review/independent-numerical-check.json` | `f3685d6733a53136883cd8830b063a2a48cddc15532cfa0311b0d1a6f35acfb1` |
| `repo/results/012/run-progress.json` | `e542a9baae15e4032c3f4c79b56959d1da84ff99275f452731db378c3f772829` |
| `repo/results/012/summary.json` | `88ff8692d94a67f849e8b3537e461ec329f5696ac1df93b5e8a16bf766cddb6f` |
| `repo/scripts/extract_event_assets.py` | `0a009dd4ba25d94cb95395ab1b338ff83b6e0750031cc89a26264ab61082dc1a` |
| `repo/scripts/package_event_assets.py` | `02b77c2d87f4a8cd35b4b83cc99b7b0fcb78e37b300a815d7bafa2ddb07900c8` |
| `repo/scripts/package_events.py` | `20e37581ea0e4e90f53225f8f6aac4eacab995bb1f27d8767f892d56523c4168` |
| `repo/scripts/report_events.py` | `c864d59aafaa59cb4f27c674bb8eb87dafa761e7dc4c5a9252149b3a25739f92` |
| `repo/scripts/reproduce_events.py` | `7c819c8460537d7afe36746ad342f473d03bf187ddadc4a9d7ccb84b7772ad29` |
| `repo/site/data/events-summary.png` | `361108b9cbaae7415369a8344f425a187470babc21a291b43dae69be380f1c34` |
| `repo/site/data/events.json` | `34696db66fbf5c6a2927e95b4d4023323d2ad2e0046c9ae41cd47b748d09da8d` |
| `repo/site/events.html` | `e55adc9ad1ac993c1ac5c66420f8052e1e79ad6b2390c93a720cbc8c99974c35` |
| `repo/tests/test_extract_event_assets.py` | `5a6b63ef3dcb1483f2ff0c4dc6b90348f9f412578a21ec6d2618d7b576a052ac` |
| `repo/tests/test_package_event_assets.py` | `6ec8e4bc9b45edda2102bc40d4348741aee8d4b2ff7eb3626e7f7c76b30faa42` |
| `repo/tests/test_package_events.py` | `308c531ccd527cbc208237625fe031e4e074e29299c96b23e6418069d0d9366d` |
| `repo/tests/test_report_events.py` | `941684aad73da7e5450102b4bd01f3b0754c680e3a467700127538905be07958` |
| `review-r1/REVIEW.md` | `e0082d0d6a8e60144802f9a30632e367059f528b946f445f53492ca7f8c2e41d` |

## Limits and next checkpoint

I did not open reserved people or sessions, run the empirical study, make model forwards, rerun detectors or perform the full numerical replay. I inspected the release gates and ran small fixtures; I did not package or extract the actual several-gigabyte staged release. The staged extraction, generated replay receipt, final inventory, independent final-review provenance and public page readback remain for a later fresh-admitted checkpoint. The local native handoff JSON is not authenticated proof by itself. No present artifact is a claim of final release acceptance. Scientific source was not changed by this reviewer. No API spending occurred here; native monetary cost is UNKNOWN.

Root should supply the corrected extractor and test hashes, stage revision 2, actual extraction and replay evidence, and final inventory for that checkpoint. This reviewed packet remains unchanged.
