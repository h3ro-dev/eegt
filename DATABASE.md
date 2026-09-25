# EEGT continuous database

The database connects every derived observation to its original source file,
sample coordinates and frozen experiment. Raw samples remain immutable files;
SQLite stores the inventory and evidence needed to interpret the derived data.

```mermaid
flowchart LR
  A[Pinned public archive] --> B[Verified raw files]
  B --> C[Recordings and native gaps]
  C --> D[Numeric windows and quality masks]
  D --> E[Training-only reference]
  D --> F[Transition events and geometry]
  E --> F
  F --> G[Per-record evidence and research notes]
  H[Context labels in a separate evaluator] -. later .-> G
```

## Files and boundaries

| Artifact | Contents | Role |
|---|---|---|
| `protocol/corpus-manifest-v1.json` | Pinned commits, source paths, content hashes, units, technical metadata, selection and prior-exposure flags | Curator inventory; never a discovery-model input |
| `data/cache/` | Original checksum-verified SET/FDT files | Immutable source cache; fetched from public archives, excluded from Git |
| `results/corpus-v1/corpus.sqlite` | Datasets, recordings, source files, channels, discontinuities and coverage view | Queryable source catalog; distributed as a release asset |
| `data/derived/003/*.npz` | Numeric feature matrices, validity, timestamps and segment indices | Reproducible derivatives, using non-executable NumPy arrays |
| `results/003/features.json` | Feature hashes, exposure and source/processing identity | Connects derived files to the frozen input bundle |
| `results/003/analysis.sqlite` | Catalog plus feature receipts, model references, transition events and per-record metrics | Queryable numerical evidence; distributed as a release asset |
| `results/006/` and `results/007/` | Control and transfer results linked by recording keys and hashes | Evaluation layer; no semantic labels sent back into discovery |

Each recording key is scoped to its source snapshot. Public participant IDs are
grouping keys, not proof of globally unique people. Removing names and labels
from input arrays does not remove all possible identity-related information
from EEG. No such inference is part of this study.

## Denominators

Count source participant records, sessions, recordings, source hours,
discontinuities, qualified records, all feature windows, QC-passing windows and
eligible scored contexts separately. A window is multichannel in Experiment 003;
Experiment 002 used per-channel windows. At a half-second hop, multiplying
eligible window centers by 0.5 estimates center-grid exposure, not independent
sample size or the exact union of valid raw samples. Missing and quarantined
sources remain visible.

```sql
-- Counts and decoded sample duration, including quarantine rows.
SELECT * FROM coverage ORDER BY dataset_id, status;

-- Source problems that must not disappear from the denominator.
SELECT dataset_id, source_subject, status, reason
FROM recordings WHERE status <> 'QUALIFIED';

-- Native gaps and boundaries, in source sample coordinates.
SELECT recording_id, start_sample, stop_sample, kind
FROM discontinuities ORDER BY recording_id, start_sample;

-- Individual numerical events; these are not clinical diagnoses.
SELECT recording_id, view, scale_seconds, time_seconds, score, geometry_json
FROM transition_events WHERE scale_seconds = 2.0
ORDER BY recording_id, view, time_seconds;
```

## Growing the corpus

1. Inventory a new public source version. Include only the around-ear EEG
   scope or explicitly create a new comparison protocol. Verify terms, technical
   fields, provenance, source-local participants and repeated-session structure.
2. Pin source content hashes and deduplicate payloads before choosing splits.
   Preserve missing files and failures. Do not count re-downloading an unchanged
   file or slicing more overlapping windows as new evidence.
3. Reserve new participants or sessions before examining signals. Repeated
   evaluation consumes a holdout; record that exposure in the next manifest.
4. Freeze a numbered protocol, acquire and qualify sources, run the unchanged
   baseline plus the new question, independently review, and publish a release.
5. Prioritize gaps the current corpus cannot answer: repeated sessions, genuine
   Neurable acquisition, contact/reseating variation and independently aligned
   context. Add meaning only through later blinded evaluation after discovery.

The current database has no proven Neurable capture, globally unique participant
census, population-level repeat-session reliability estimate, clinical endpoint or universal
token geometry. Experiment008 adds a bounded descriptive repeat-night comparison, with separate acceptance evidence.

## Repeated-session extension · v0.4.0

`results/corpus-v2/corpus.sqlite` indexes all three sources with 67 candidates, 66 qualified records and retained quarantine. Its `coverage` view groups source and status; source-local participant counts are not a global identity census. Earlier catalog and analysis files remain unchanged.

`results/008/catalog.sqlite` holds the twelve new raw-record receipts. `results/008/analysis.sqlite` adds per-record metrics and primary-scale transition events; `data/derived/008/*.npz` retains feature rows, timestamps, validity and native segment keys. The JSON summary includes all cross-night distance cells and all exact pairing-permutation statistics. The frozen training reference is reused without refitting.

## Pretrained comparison extension · v0.5.0

`results/009/analysis.sqlite` retains 240 candidates, 27 segment/view comparisons and 36 waveform-control comparisons. Candidate rows include source grouping, native start seconds and rejection reasons. `data/derived/009/prepared.npz` contains nine `[4,30,200]` numerical wave blocks and aligned frozen descriptors; `embeddings.npz` contains the 45 model outputs. Source identity, array order, dtype, shape and numerical bytes are hash-bound. The checkpoint and source commits are pinned in `protocol/experiment-009.json`.

Only 9/240 segments qualify (3.75%). That denominator is candidate 30-second segments from the selected first ten minutes of each recording; it is neither corpus coverage nor diagnostic accuracy. There are zero complete eligible participant pairs and no primary p values. This reuses exposed recordings and does not increase the corpus's qualified recording or hour totals. Original source files, participants and recording-hours must not be counted again because another model processed them.

Downloaded hours (86.38), selected analysis hours (48), QC windows and scored-context exposure are distinct. The dataset's other four participants remain untouched. The other nights of analyzed participants are reserved for new-session evaluation, not new-person evaluation.

A **held-out person** is someone whose recordings were never used to choose or tune the method. A **held-out session** is another recording occasion, possibly from someone already represented. A **held-out device or dataset** tests another measurement setup or source. These tests answer different questions; success at one cannot stand in for the others. Grouping metadata stays in the evaluator, while discovery receives anonymous numeric arrays.

## Experiment 010: quality census and selected model support

`results/010/prepared.json` retains every one of 5,760 candidate blocks with source, night, native start, twenty-minute stratum, rejection reasons, missing-sample counts, and separate `quality_status` and selection `status`. `PASS` quality is not a neural diagnosis. Selection `ELIGIBLE` is the lower temporal median quality-pass block of a nonempty stratum. `QUALIFIED_UNSELECTED` remains in the ledger with its reason for omission defined by that rule.

`data/derived/010/prepared.npz` contains 122 selected numeric wave arrays and aligned descriptors, with row hashes. `embeddings.npz` contains 610 variant outputs; `inference.json` binds every output to its input and code/checkpoint. `analysis.sqlite` has 5,760 candidates, 366 block/view comparisons and 488 control comparisons. Per-metric complete-participant aggregation uses five people and 110 selected blocks; person 003's twelve blocks remain descriptive.

The census covers 48 already exposed hours, of which 24.775 hours pass the thirty-second quality gate. Selected model support is 61 minutes. These are analytical subsets, not extra recorded hours or new people. The corpus remains 67 candidates, 66 qualified source recordings and 309.85 qualified source hours. The v0.6.0 release provides the new derivatives and receipts; v0.4.0 retains original baseline features, and pinned public archives retain full source recordings.
