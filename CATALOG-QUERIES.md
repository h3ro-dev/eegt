# Querying the consolidated curator index

Preparation document: the final database is not released yet. These queries work against the proposed SQLite schema; they neither decode EEG nor run a model.

Source hours describe qualified recordings, including portions not analyzed. They are not selected-window hours. Reanalysis in several experiments does not add source hours. People are scoped to dataset; the same source-local label in two datasets does not establish that it is the same person.

```sql
-- Source inventory with missing durations kept visible.
SELECT dataset_id, status, recordings, source_local_people,
       source_sessions, known_recording_hours, unknown_duration_recordings
FROM coverage ORDER BY dataset_id, status;

-- Original endpoint JSON, including its actual denominator, exclusions,
-- test family and null fields. Historical field names remain unchanged.
SELECT experiment_id, endpoint_id, model_id, cohort, receipt_json
FROM results ORDER BY experiment_id, endpoint_id;

-- Exact experiment-specific source support. This is not a count of people
-- independent of each experiment's inclusion and pairing rules.
SELECT e.experiment_id, r.dataset_id, r.source_subject, r.session_id,
       e.role, e.receipt_json
FROM experiment_recordings AS e
JOIN recordings AS r USING(recording_id)
ORDER BY e.experiment_id, r.dataset_id, r.source_subject, r.session_id;

-- Declared file evidence: nullable hashes or bytes stay explicitly unknown.
SELECT dataset_id, revision, path, bytes, sha256, status, receipt_path
FROM source_files ORDER BY dataset_id, revision, path;

-- Directed dependencies are imported only from matching recorded hashes.
SELECT parent_id, child_id, relation, receipt_path FROM lineage
ORDER BY parent_id, child_id;
```

The historically reported 11.4% is 393 of 3,458 external windows passing that earlier coverage criterion. It is not accuracy, percent of brains decoded, or a universal-token rate. Read the originating experiment for its exact window definition and reference set. Continuous encoder similarity, event timing agreement and discrete tokenizer agreement are separate quantities; this database must not relabel one as another.

Source provenance and grouping keys are curator metadata. Discovery receives only numeric arrays; identity, history and semantic labels are not input features. Technical qualification does not establish device equivalence, clinical meaning, pretraining independence or biological specificity of detected events.
