# Prepublication integrity repair

Independent review of the first computed Experiment 002 found that an altered, same-length evaluation index could pass the evaluator's row-count checks. The recorded run's rows were aligned; the defect concerned accepting a corrupted or mixed bundle on a later run.

Before publication, preparation was changed to include explicit window IDs in the evaluation index and seal the analysis waves, evaluation index, QC ledger, provenance and frozen protocol/source manifest in `prepared-inputs.json`. Evaluation verifies every bound digest and identical unique window IDs before any fit. Missing, altered or reordered inputs fail. This protects against accidental file mixing or modification, not an adversary who deliberately rewrites both files and their receipts.

No source selection, numeric samples, preprocessing, fit/evaluation splits, methods, settings or outcome definitions changed. The initial code/results are preserved in the project audit record. The release regenerates preparation and all fits after the repair; `results/002/repair-equivalence.json` records the numerical comparison with the original, and the independent repair review records its checked boundary.
