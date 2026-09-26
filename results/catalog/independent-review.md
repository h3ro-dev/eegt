# Independent final catalog content review

**Status: ACCEPTED_FOR_PUBLICATION.** This accepts the v0.10.0 catalog's numerical, provenance, source, package and candidate public-claim content. It does not assert catalog publication or live readback. Reviewer `session-88981af3c741f4ce3c045aff76ce659b` / thread `01a0de2e-79a9-7be0-a9e2-d9a38d94fb26`; root owns release integration.

## Exact packet and rebuild

- Outer `INPUT-MANIFEST.json`: `f374eb6b77b98151b1361eac307a638a2f1386d634dddd76eece696c63fcfb06`; all 7 declared files rehashed. Catalog member manifest: `ce0b389c129d0cc2579b1a655c6646d3c920a713189bb2b21fbd5c223ec1d8b5`; 57 members, 60,558,336 bytes, all hashes and lengths exact, no symlinks or unexpected files. Extractor receipt `799f8428d3b2ae5dc3c15ad29bbc887e355d6e3528a4984005a684628b78ebf1`; independent inventory `a4b47e254aa197ca278d99583fc4643b18312d85123739070fae3e7fa64f27b3`. Post-review inventory stayed exact: `474b3f9da8b420b94a0f534dab876e359f53fd911568415ae290af651a341ca9`.
- Offline rebuild exited 0 in 1.57 wall seconds (1.14 user, 0.18 system; peak RSS 185,008,128 bytes). Packaged and rebuilt SQLite SHA256 are both `cefcbd423b57cc8b9345f4731c542369a8c43b1cc2c09cd0473f2a16efe91790`. Every summary field matched, including logical-content SHA256 `64efd3d566264f18c30a15d71eeca13ac7ec9f4060024228c1fc509996b58f1f`; exact user schema and every table row matched. Both SQLite databases passed integrity and foreign-key checks. All 36 bound inputs rehashed.
- Rebuild summary SHA256 `54153bca791649437ecc7b7c93da8e6ae49549c7f5a637483580d775c90f0ebf`; independent audit SHA256 `025277d94cd1352c0a8c8c507eef54ffa98af9dd0e26d32693d1aca65fbd0f8f`. The complete 57-member and reviewed-source hash lists are in the JSON report.

## Provenance and claims

- The source catalog has **89 candidates, 88 qualified recordings and 476.05329555555556 qualified source hours**, independently summed from 67 historical, 2 EESM19 and 20 Experiment 013 original recording receipts. All 158 source-file receipts are retained, with 146 recording-file links; one ds005207 quarantine remains visible. Source-local people are not globally unique, and experiment joins add no people or hours.
- The 013 publication receipt is `PUBLISHED_AND_VERIFIED` and binds stage manifest `87caec95a2116cc3518c61e7888ae513d27fdc972c8edcb353f207e4f555177c`. The four imported source/protocol/qualification/summary members match that published inventory byte for byte. The catalog preserves two exact model IDs and checkpoint hashes, all nine experiment receipts, 29 result rows and three explicit hash-bound lineage links.
- Experiment 013 has 9,600 candidates, 4,117 quality passes, 174 selected blocks, 4,002 event partitions, 130 new-session and 44 new-person selected blocks. Six complete new-session people yield four inconclusive comparisons; two complete new-person people leave four tests not estimable. The eight original endpoint receipts and their null fields match exactly. Earlier 011 and 012 adjusted p values match their included summaries.
- Supplied `catalog.html` and `catalog.json` match a fresh render byte for byte: `ea565e4fe80f997d645edad1a83b463a6575c7c895bdd9db70e460d1219bd1dd` and `54153bca791649437ecc7b7c93da8e6ae49549c7f5a637483580d775c90f0ebf`. The page separates source hours, quality windows, selected blocks and independent people; calibration, reference/gain/clock, pretraining overlap and physical Neurable equivalence remain UNKNOWN. Cards and synthesis preserve numerical discovery boundaries and avoid semantic, diagnostic and universal-language claims. DOI is `PREPARED_NOT_DEPOSITED` / `NOT_ISSUED`.

## Preliminary findings and focused evidence

| Finding | Final disposition | Direct evidence |
|---|---|---|
| CAT-SR-01 manifest race | Resolved | Builder hashes parsed bytes and rechecks before commit/return; mutation canary rejected with no database. |
| CAT-SR-02 summary/renderer binding | Resolved | Full DB-derived summary comparison; six forged count/coverage render and stage cases rejected; eight endpoints compared to bound summary artifact. |
| CAT-SR-03 publication path escape | Resolved | Publication receipt and stage paths confined before binding; three absolute/traversal cases rejected. |
| CAT-SR-04 shared file identity | Resolved | Two links and both receipts retained; conflicting file ID, bytes, SHA, URL and status rejected. |

Reviewer suite: **21/21 passed** with warnings as errors, exit 0. Synthetic canaries: **PASS**, receipt SHA256 `c91c4968c5d67375a105c8ae27db5b29826e6f6400871b7762c5edfa67ee7717`. No EEG, detector or model computation occurred.

## Remaining release boundary

Root must perform catalog publication, asset download verification and live page readback. The immutable candidate has pending labels; its `CITATION.cff` date-released must match the eventual v0.10.0 publication date. Historical numerical releases and source terms govern upstream wave/model claims; the ds005185 license text is not bundled, though its public source links and hashes are. No DOI is issued. The present acceptance is content approval for publication, not evidence that the catalog is already public.

Machine-readable report SHA256: `6491f1aca26c610356064536b91f3e81916d4baa379a88f2abe9763ffcc1d527`.
