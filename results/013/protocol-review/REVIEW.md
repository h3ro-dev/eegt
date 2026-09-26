# Independent EEGT 013 review

**Disposition: ACCEPTED** for the exact reviewed r7 candidate only. Empirical access and release acceptance are separate.

Bead `eco-uzwh8s.37.3` · Reviewer `session-d90d706165cdf73b0fb4471fb4171e88` · Integration owner `session-13ffd342d925791b856652db872e4142` · Native dollar cost **UNKNOWN**.

## Findings

- **E013-REVIEW-001 — FIXED_IN_R3_RECHECKED** — `eegt/validation_study.py:evaluate_index`: Zero selected and completed blocks were labeled COMPLETE_NUMERICAL_RECORD. After r3: NO_ELIGIBLE_BLOCKS and all eight endpoints NOT_ESTIMABLE. [before](repro-zero.log); [after](repro-zero-r3.log).
- **E013-REVIEW-002 — FIXED_IN_R3_RECHECKED** — `eegt/validation_study.py:verify_indexed_partitions/evaluate_index`: A correct total of 23 partitions could belong to a different candidate; effect joins were not exact. Exact completed candidate x 18 native + 5 prepared partition set and 4 effect rows per completed block now required. [before](repro-index.log); [after](test-r3-events-corrected.log).
- **E013-REVIEW-003 — FIXED_IN_R3_RECHECKED_WITH_LIMIT** — `eegt/validation_intake.py:IntakeResources/qualify_sources/build_quality_census/prepare_validation`: Accepted CPU/RSS/artifact bounds and first-record profiling were absent from intake stages. R3 checks caps before/after each record, stops after first record for hash-bound root review, reuses only exact numeric archives. Record-boundary overshoot remains documented. [before](repro-intake-bounds.log); [after](test-r3-intake-pytest.log).
- **E013-REVIEW-004 — FIXED_IN_R5_RECHECKED** — `eegt/validation_study.py:open_index`: Existing event index accepted a changed participant identity with same candidate count and freeze hashes. R5 compares all eight candidate columns with validated prepared rows; 8-field regression and 21-test suite pass. [before](repro-candidate-index.log); [after](repro-candidate-index-r5.log).
- **E013-REVIEW-005 — FIXED_IN_R7_RECHECKED** — `eegt/validation_provenance.py:verify_loaded_sources; scripts/reproduce_validation.py:main; scripts/prepare_validation.py:main`: Earlier freezes accepted shadowed imported EEGT modules; r6 fixed those but accepted a changed normal CLI. R7 binds both normal __main__ script names and all loaded EEGT module bytes. A copied CLI with different bytes now refuses before source access; equal bytes pass. The original stale imported study also refuses in r6. Four provenance unit tests and the full 33-test suite pass. [before](repro-shadow-cli-r6.log); [after](repro-shadow-cli-r7.log).

## Checks

Commands are relative to the listed working directory. Raw output is linked here and embedded verbatim in [REVIEW.json](REVIEW.json). Every numerical check used one process and one thread.

| Check | State | Wall / user CPU / peak RSS | Raw output |
|---|---|---:|---|
| `inventory_initial` | PASS | UNKNOWN | [inventory-check.log](inventory-check.log) |
| `inventory_final` | PASS | UNKNOWN | [inventory-check-final.log](inventory-check-final.log) |
| `inventory_r6` | PASS | UNKNOWN | [inventory-check-r6.log](inventory-check-r6.log) |
| `inventory_r7` | PASS | UNKNOWN | [inventory-check-r7.log](inventory-check-r7.log) |
| `additive_hashes_initial` | PASS | UNKNOWN | [update-audit.log](update-audit.log) |
| `inventory_addenda_and_effective` | PASS | UNKNOWN | [final-inventory.log](final-inventory.log) |
| `inventory_addenda_r6` | PASS | UNKNOWN | [final-inventory-r6.log](final-inventory-r6.log) |
| `inventory_addenda_r7` | PASS | UNKNOWN | [final-inventory-r7.log](final-inventory-r7.log) |
| `source_exposure` | PASS | UNKNOWN | [source-audit.log](source-audit.log) |
| `protocol_initial` | PASS | UNKNOWN | [protocol-audit.log](protocol-audit.log) |
| `protocol_r3_r4` | PASS | 2.69 s / 0.9 s / UNKNOWN | [final-protocol-audit.log](final-protocol-audit.log) |
| `protocol_r5` | PASS | 5.11 s / 0.93 s / UNKNOWN | [final-protocol-audit-r5.log](final-protocol-audit-r5.log) |
| `protocol_r7` | PASS | 2.03 s / 0.95 s / UNKNOWN | [final-protocol-audit-r7.log](final-protocol-audit-r7.log) |
| `corpus_runtime` | PASS | UNKNOWN | [runtime-corpus.log](runtime-corpus.log) |
| `events_runtime` | PASS | UNKNOWN | [runtime-events.log](runtime-events.log) |
| `intake_initial` | PASS | 9.17 s / 2.7 s / UNKNOWN | [test-intake.log](test-intake.log) |
| `study_initial_bad_fixture_path` | HARNESS_ERROR | 25.11 s / 15.88 s / UNKNOWN | [test-study.log](test-study.log) |
| `study_initial_corrected_fixture_path` | PASS | 87.24 s / 44.75 s / UNKNOWN | [test-study-corrected.log](test-study-corrected.log) |
| `engineering_initial` | PASS | 8.41 s / 1.3 s / UNKNOWN | [test-engineering.log](test-engineering.log) |
| `r3_events_wrong_module_name` | HARNESS_ERROR | 72.19 s / 47.76 s / UNKNOWN | [test-r3-events.log](test-r3-events.log) |
| `r3_events_corrected` | PASS | 75.79 s / 45.29 s / UNKNOWN | [test-r3-events-corrected.log](test-r3-events-corrected.log) |
| `r3_intake_unittest_only` | INCOMPLETE_HARNESS | 8.73 s / 2.05 s / UNKNOWN | [test-r3-intake.log](test-r3-intake.log) |
| `r3_intake_pytest` | PASS | 5.36 s / 2.67 s / UNKNOWN | [test-r3-intake-pytest.log](test-r3-intake-pytest.log) |
| `r4_engineering` | PASS | 4.18 s / 1.3 s / UNKNOWN | [test-r4-engineering.log](test-r4-engineering.log) |
| `r5_ledger_study` | PASS | 69.77 s / 46.71 s / UNKNOWN | [test-r5-ledger-study.log](test-r5-ledger-study.log) |
| `r6_provenance_study_ledger_engineering` | PASS | 69.38 s / 49.78 s / UNKNOWN | [test-r6-events.log](test-r6-events.log) |
| `r6_intake` | PASS | 14.58 s / 3.09 s / UNKNOWN | [test-r6-intake.log](test-r6-intake.log) |
| `r7_provenance_study_ledger_engineering` | PASS | 58.39 s / 46.71 s / UNKNOWN | [test-r7-events.log](test-r7-events.log) |
| `r7_intake` | PASS | 11.18 s / 2.68 s / UNKNOWN | [test-r7-intake.log](test-r7-intake.log) |
| `corpus_freeze_initial` | PASS | 8.37 s / 2.01 s / UNKNOWN | [gates-corpus.log](gates-corpus.log) |
| `events_freeze_initial` | PASS | 2.03 s / 1.05 s / UNKNOWN | [gates-events.log](gates-events.log) |
| `corpus_freeze_r4` | PASS | 8.05 s / 1.73 s / UNKNOWN | [gates-corpus-r4.log](gates-corpus-r4.log) |
| `events_freeze_r4` | PASS | 5.76 s / 0.99 s / UNKNOWN | [gates-events-r4.log](gates-events-r4.log) |
| `corpus_freeze_r6` | PASS | 3.28 s / 1.67 s / UNKNOWN | [gates-corpus-r6.log](gates-corpus-r6.log) |
| `events_freeze_r6` | PASS | 1.71 s / 0.93 s / UNKNOWN | [gates-events-r6.log](gates-events-r6.log) |
| `preflight_source_only` | PASS | UNKNOWN | [preflight.log](preflight.log) |
| `combined_shared_gate_initial` | PASS | 4.96 s / 1.3 s / UNKNOWN | [combined-fixture.log](combined-fixture.log) |
| `combined_shared_gate_r5` | PASS | 3.12 s / 1.33 s / UNKNOWN | [combined-fixture-r5.log](combined-fixture-r5.log) |
| `combined_shared_gate_r6` | PASS | 2.28 s / 1.35 s / UNKNOWN | [combined-fixture-r6.log](combined-fixture-r6.log) |
| `exposed001_full_grid_and_bytes` | PASS | 1.43 s / 0.78 s / UNKNOWN | [exposed001-compare.log](exposed001-compare.log) |
| `exposed012_archive_parity` | PASS | 44.52 s / 29.5 s / UNKNOWN | [exposed012-parity.log](exposed012-parity.log) |
| `exposed012_archive_parity_r6` | PASS | 32.68 s / 26.69 s / UNKNOWN | [exposed012-parity-r6.log](exposed012-parity-r6.log) |
| `finding001_zero_before` | REPRODUCED_THEN_FIXED | 2.85 s / 1.15 s / UNKNOWN | [repro-zero.log](repro-zero.log) |
| `finding001_zero_after` | PASS | 10.08 s / 1.18 s / UNKNOWN | [repro-zero-r3.log](repro-zero-r3.log) |
| `finding002_partition_before` | REPRODUCED_THEN_FIXED | 1.81 s / 1.1 s / UNKNOWN | [repro-index.log](repro-index.log) |
| `finding003_bounds_before` | REPRODUCED_THEN_FIXED | 10.88 s / 2.16 s / UNKNOWN | [repro-intake-bounds.log](repro-intake-bounds.log) |
| `finding004_candidate_index_before` | REPRODUCED_THEN_FIXED | 5.7 s / 1.1 s / UNKNOWN | [repro-candidate-index.log](repro-candidate-index.log) |
| `finding004_candidate_index_after` | PASS | 9.3 s / 1.16 s / UNKNOWN | [repro-candidate-index-r5.log](repro-candidate-index-r5.log) |
| `finding005_shadowed_executable` | OPEN_FINDING | 3.09 s / 1.11 s / UNKNOWN | [repro-code-import.log](repro-code-import.log) |
| `finding005_imported_module_r6` | PASS | 7.2 s / 1.22 s / UNKNOWN | [repro-code-import-r6.log](repro-code-import-r6.log) |
| `finding005_shadowed_cli_r6` | OPEN_FINDING | 1.82 s / 0.9 s / UNKNOWN | [repro-shadow-cli-r6.log](repro-shadow-cli-r6.log) |
| `finding005_shadowed_cli_r7` | PASS_EXPECTED_REFUSAL | 2.15 s / 0.97 s / UNKNOWN | [repro-shadow-cli-r7.log](repro-shadow-cli-r7.log) |
| `finding005_equal_cli_r7` | PASS | 12.61 s / 1.08 s / UNKNOWN | [preflight-r7-equal-cli.log](preflight-r7-equal-cli.log) |

### Reproduction commands

```text
inventory_initial [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: python3 scratch/check_inventory.py
inventory_final [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: python3 scratch/check_inventory.py
inventory_r6 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: python3 scratch/check_inventory.py
inventory_r7 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: python3 scratch/check_inventory.py
additive_hashes_initial [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: python3 scratch/audit_update.py
inventory_addenda_and_effective [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: python3 scratch/final_inventory.py
inventory_addenda_r6 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: python3 scratch/final_inventory.py
inventory_addenda_r7 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: python3 scratch/final_inventory.py
source_exposure [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: python3 scratch/audit_sources.py
protocol_initial [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/audit_protocol.py
protocol_r3_r4 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/audit_final_protocol.py
protocol_r5 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/audit_final_protocol.py
protocol_r7 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/audit_final_protocol.py
corpus_runtime [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /Users/studio1/lanes.noindex/eco-uzwh8s.37.1/scratch/corpus-venv/bin/python -c "import platform,numpy,scipy,mne; print(platform.python_version(),numpy.__version__,scipy.__version__,mne.__version__)"
events_runtime [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python -c "import platform,numpy,scipy,bycycle,neurodsp; print(platform.python_version(),numpy.__version__,scipy.__version__,bycycle.__version__,neurodsp.__version__)"
intake_initial [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.1/scratch/corpus-venv/bin/python -m pytest -q tests/test_validation_intake.py
study_initial_bad_fixture_path [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python -m unittest -v tests.test_validation_study
study_initial_corrected_fixture_path [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python -m unittest -v tests.test_validation_study
engineering_initial [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python -m unittest -v tests.test_validation_engineering
r3_events_wrong_module_name [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python -m unittest -v tests.test_validation_ledger tests.test_validation_study tests.test_engineering_controls
r3_events_corrected [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python -m unittest -v tests.test_validation_ledger tests.test_validation_study tests.test_validation_engineering
r3_intake_unittest_only [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.1/scratch/corpus-venv/bin/python -m unittest -v tests.test_validation_intake tests.test_validation_intake_resources
r3_intake_pytest [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.1/scratch/corpus-venv/bin/python -m pytest -q tests/test_validation_intake.py tests/test_validation_intake_resources.py
r4_engineering [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python -m unittest -v tests.test_validation_engineering
r5_ledger_study [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python -m unittest -v tests.test_validation_ledger tests.test_validation_study
r6_provenance_study_ledger_engineering [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python -m unittest -v tests.test_validation_provenance tests.test_validation_intake_resources tests.test_validation_study tests.test_validation_ledger tests.test_validation_engineering
r6_intake [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.1/scratch/corpus-venv/bin/python -m pytest -q tests/test_validation_intake.py tests/test_validation_intake_resources.py
r7_provenance_study_ledger_engineering [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python -m unittest -v tests.test_validation_provenance tests.test_validation_intake_resources tests.test_validation_study tests.test_validation_ledger tests.test_validation_engineering
r7_intake [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.1/scratch/corpus-venv/bin/python -m pytest -q tests/test_validation_intake.py tests/test_validation_intake_resources.py
corpus_freeze_initial [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.1/scratch/corpus-venv/bin/python scratch/gates_corpus.py
events_freeze_initial [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/gates_events.py
corpus_freeze_r4 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.1/scratch/corpus-venv/bin/python scratch/gates_corpus.py
events_freeze_r4 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/gates_events.py
corpus_freeze_r6 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.1/scratch/corpus-venv/bin/python scratch/gates_corpus.py
events_freeze_r6 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/gates_events.py
preflight_source_only [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scripts/reproduce_validation.py preflight --root .
combined_shared_gate_initial [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/combined_fixture.py
combined_shared_gate_r5 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/combined_fixture.py
combined_shared_gate_r6 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/combined_fixture.py
exposed001_full_grid_and_bytes [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.1/scratch/corpus-venv/bin/python scratch/compare_exposed001.py
exposed012_archive_parity [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scripts/reproduce_validation.py exposed-parity --root . --supplement ../supplement-exposed012 --sqlite ../scratch/exposed012/analysis.sqlite
exposed012_archive_parity_r6 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scripts/reproduce_validation.py exposed-parity --root . --supplement ../supplement-exposed012 --sqlite ../scratch/exposed012/analysis.sqlite
finding001_zero_before [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/repro_zero.py
finding001_zero_after [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/repro_zero.py
finding002_partition_before [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/repro_index.py
finding003_bounds_before [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.1/scratch/corpus-venv/bin/python scratch/repro_intake_bounds.py
finding004_candidate_index_before [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/repro_candidate_index.py
finding004_candidate_index_after [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/repro_candidate_index.py
finding005_shadowed_executable [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python -c "from eegt import validation_study; validation_study.require_accepted_freeze(scratch_combined, stage=events)"
finding005_imported_module_r6 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/repro_code_import_r6.py
finding005_shadowed_cli_r6 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/shadow-cli/reproduce_validation.py preflight --root scratch/combined-r6
finding005_shadowed_cli_r7 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/shadow-cli/reproduce_validation.py preflight --root scratch/combined-r6
finding005_equal_cli_r7 [cwd=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3]: env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/Users/studio1/lanes.noindex/eco-uzwh8s.37.3/scratch/packet/repo /usr/bin/time -l /Users/studio1/lanes.noindex/eco-uzwh8s.37.2/scratch/events/bin/python scratch/packet/repo/scripts/reproduce_validation.py preflight --root scratch/combined-r6
```

## Source and science assessment

- The 521-file initial packet has no missing, extra or mismatched bytes. All additive packets through r7 match their manifest SHA256. The effective source inventory has 525 paths and zero overlay mismatches.
- Twenty pinned ds005178 nights form separate new-people (eight nights) and new-session (12 nights) cohorts, with 3,312,979,776 declared bytes. The scoped exposure audit found no pair overlap with 12 exposed EESM23 nights. Missing sources stay visible.
- The full two-second/half-second baseline produced 28,797 centers, 27,916 valid. All 480 exposed candidate row fields and 11 selected prepared arrays matched exact supplied evidence. The failed encoder-runtime comparison remains retained: seven patch hashes differed, so preparation remains in the pinned corpus runtime.
- Native finite/gap/flat and prepared peak predicates, 28 centers, temporal selection and deterministic seeds use inherited functions with 16 unchanged accepted scientific module hashes. Five prepared and 18 native variants match the released constants.
- The eight prespecified cohort/model/metric tests keep cohorts and actual nights separate, require metric-valid paired blocks, use an explicit participant sign-symmetry assumption, and retain all eight multiplicity slots. Undefined effects remain null.
- The engineering branch has two prespecified first-30-second EESM19 inputs, 12 real EEG contacts at 500 Hz and validity masks; no encoder mapping, semantic label, adaptive replacement or primary test. A synthetic accepted freeze exercised the actual shared intake verifier and per-row receipt hashes.
- Archive parity covered 122 selected numeric rows, 1,220 archived model outputs, 23 hashed row-zero partitions, 20 prepared metrics, four effects, 68 timelines and 816 matches. This was archive replay, not detector regeneration or model forward.
- Normal acquisition, qualification, quality, preparation, inference, event, replay and engineering paths refused before an accepted freeze. R7 binds loaded EEGT source bytes and the two normal CLI script entry points; a mismatched copied CLI and a stale imported study both refuse.

## Remaining limitations

- This disposition is for the exact reviewed source/protocol bytes. It does not accept an empirical run or a scientific release.
- The experiment and engineering contracts are FROZEN in the reviewed candidate. No ACCEPTED RUN-SOURCE-MANIFEST or post-preparation INPUT-ACCEPTANCE exists in the packet. The old prospective run manifest is DRAFT_NOT_ACCEPTED, has stale hashes and omits new validation_provenance.py; root must rebuild it from final bytes.
- No reserved waveform payload was present or opened. Pinned source digests were checked against attached metadata, not newly acquired bytes. Missing sources must remain missing.
- Scoped local/remote filename-stat and canonical receipt audits found no overlap with 12 exposed EESM23 pairs. They cannot prove every historical exposure or foundation-model pretraining overlap; the latter remains UNKNOWN.
- Checkpoint payloads were absent from this review packet. Their prospective references match accepted 011 receipts but this review did not independently hash the model bytes.
- Exposed 012 parity replayed archived model outputs and the row-zero event partitions. It did not regenerate detectors, invoke encoders, or prove all 122 event blocks from raw signals.
- The proposed 4 GB acquisition cap exceeds 3,312,979,776 pinned bytes but is not live admission. Root must obtain fresh physical fit and first-record stage reviews before empirical access. Intake CPU/RSS/artifact checks occur at record boundaries; one record can overshoot before refusal.
- Maximum complete participant counts are four and six, so the fixed eight-test Bonferroni family has minimum adjusted two-sided sign-flip p values 1.0 and 0.25. No positive alpha=0.05 result is possible with these cohort sizes; this is a protocol power limit, not a threshold change.
- Native provider dollar cost is UNKNOWN. Review used the pinned corpus/events Python environments sequentially, one numerical process and one BLAS thread; no source acquisition or new model forward occurred.

## Complete reviewed SHA256 inventory

Initial manifest `2897dd09d63c7e3f635e46bc88f4f50d345bb3ee59c47ffbae09df872a12dd10`. Full machine-readable inventory: [FINAL-INVENTORY.json](FINAL-INVENTORY.json) (SHA256 `fb213339a7055d85fc79c3faa494aa53f1e21360b75ad02cd0dd7683ec0ce07e`). Effective paths below use the last reviewed additive byte version.

```text
23811120f0b33cb6e4c6b8652ea7df2adbdef6d896ba2448fbda9effc053bd57  AGENTS.md
426cb5a793559db4aa4a3fbae68bbcb471d1407de978d9989f5c3f728aefc0cc  BRIEF-DRAFT.md
93f6bb5199568ff8d1065ec61a31176eee7736eb1c722eb9d7cad720d9ed5e1f  BRIEF.md
ae0ed921bfa64301d2fe85e995970b1c649a1db10c6f88f28aa8dc6d940415d6  evidence/analysis/JEV-WORK.json
8d024d6e02ea24f019ee9bbd6e0f65b69d220acdf1056f0ae53dcf4d0bb42211  evidence/analysis/REPORT.json
0f332c4c83941c7b0478f2cead2126947711ea365e6f9d9805ff60656d21e87d  evidence/analysis/REPORT.md
9f13e12380b5306a8a38593a858cc0f8f790d60a222d21b352065c4a976ca8df  evidence/analysis/exposed-parity-final.log
0c53565d3e2c18a280072eb0a8f6fec66915acb5bd1bd7c7a8112c5a61de188d  evidence/analysis/owned-source-sha256.log
736e62a4e145e43626ff800954f73c4eefefc9cb40f3b867e59a1798f65458cd  evidence/analysis/preflight-final.log
9a8b2f44c391114e774733052fa6a7456988faef142bdeb6b79d7d548ac24e03  evidence/analysis/pycompile-final.log
a1b607fbfe0a6f9e5729b071a1a7e6a94ba2a36e548eb9c2a69aacdc0bf64301  evidence/analysis/resource-snapshot.log
f15bc332da4dac34b81dcd6283bc2326cf511c7d126572cf44143e9b0a255776  evidence/analysis/source-hash-audit.log
cb14d228660b74c4178621cdd27c4525ae436ee104769889a67a9f6690d2a385  evidence/analysis/test-validation-events.log
5ff15f29f948b01fb67b06a6a0232a6e6de71089571937aa80112883f1c15560  evidence/analysis/test-validation-focused.log
9ab7932751acf3058309c89305f6bdac8f4f0c80c2dddcfdb2638b67eef492ac  evidence/analysis/test-validation-study-final.log
65ef547d0fedac7c1c76ab879d289f3aedb6acb62e8bb1bf384c6be04e437fad  evidence/analysis/test-validation-study.log
3f6e7609c39f16dc41ac4475376f39bc779e451fc3fa96e3625fe969aa9b8da3  evidence/intake/JEV-OUTCOMES.log
562e5eadd3f117f64d43c66439e20ccd6474eb52763bde7f6a2ad142bb17d8fc  evidence/intake/JEV-WORK.json
2c7d8322b3679cf18c49a168a6577f33cfada4665f46a77ab70605ca3ae1b501  evidence/intake/REPORT.json
2916467a889ee53f14be2109ed9d907c3a4af5c5c39ee765a21ec2bad64a169c  evidence/intake/REPORT.md
df0ff110587e296454e63f15f5c725bc8995303769b652c155f6c59058541953  evidence/intake/compile.log
29ff549454010f967d6ee4141bdea8a2fedd4e5d3485cb9c038d213109d8dd6c  evidence/intake/encoder-runtime-difference.log
84d3fc9727a33137fccca7fc868686b67101d5dc967f586d7b4e179393ed5a39  evidence/intake/exposed-corpus-check.log
6d771c37d94a448edf433dab5b4d3eb6671f9de54a03c5a797a92dd4b640fe56  evidence/intake/exposed-prepare-corpus.log
af7b4fc5d6858bd907ea2c916a7ef02e204238f7beaaf303503fa8c6042108c0  evidence/intake/inherited-integrity.log
1c1635409a46aad667cf45369a56b29936136c9c9def73516d9e11888fa8cde0  evidence/intake/jev-outcome-200bb91ed307e7aa35456c943333b0d0e5870315d3eb47a079eaa1ce50d1242e.json
f0c5729f682debae23163a09604f71354e01071a1e1e5f13cbacc5f5e3f07b8a  evidence/intake/jev-outcome-2d10bc9a169349c958112201698f2c5792324e1f811bc49c813cfe41e9a3b4b6.json
264a82c4ece73cc533f600ce0cdc4acf065c1b1245432a248d3f7a56d97d6d5f  evidence/intake/jev-outcome-34a1d3e7d1ab24e52c68f7593fa57dd01a34f954b06f5694a134cbdb3fc19614.json
cd5cfc57e6852d64fb33c71b2f135624dd6d79e5a742e9b7468a0e4190e14fab  evidence/intake/jev-outcome-908236b249be165a083708faa229e6b06f8c625dfedbca8494ad96586181496e.json
801e8a68af23372a31e23be3b63732a44ae4aa781c03f09270fddf832c8ebc5d  evidence/intake/jev-outcome-a5b2c37262570e029d6fd15fb100e3e6350dbfb89b9c9f9a3b0f900d354e2d1d.json
26e6cd8dc44c6db0e947e0f35afec710fde5013ea98295c77d49d29517f3ed5e  evidence/intake/jev-outcome-aaa49c0b3392ee8e24974ca467bcbd000044bbc4b6a42791258ba0c9be12f007.json
59e5c606d0b14632ad59fae6c8a27fbc536516b218b1717c7ad83f9734dd44d3  evidence/intake/jev-outcome-f1084fed1fa8d9d0adffcb11499f3b31781226125814155f82216672cb16bdf5.json
1af61222c731662f96d6438221bf9c4aca734722ba8862fe2dc5f8cd15e9547f  evidence/intake/jev-trace-review.json
88bc3bb19eec43c321a5d0ad0cd091e846cf3a6a3c95d8928411cd81646c7d18  evidence/intake/parity-corpus.log
aa8f3edda346a07f62937c7fb1acfca62defa4277b39e1775e5d0e8162ab2ce2  evidence/intake/preflight-blocked.log
070d9ee26b2611841472084677a6c371d82f2911013d65f336bb04a3a8db4701  evidence/intake/resources.log
1d583952f1df270b60a9e574901ba6d0ca0e1bce73b42a227434e2a42fe5191d  evidence/intake/test-corpus.log
498eca8717b9524da5d7ae9c57d48ad8c92bf34ba268d9552c2948d52239f93a  evidence/intake/test-encoder.log
4183d18b25d55a59e61ec590e3c4480e31872e493902af755e10d51bb3d3623d  evidence/intake/test-validation-intake.log
8f3463d0c2cdfbc2c4309fe38846e8f02b81e7bce658bda61ab96f972bac3c85  input/ADAPTER-INTERFACE.json
2e9a5c5f303a2fd8eb8fc6d559ef2fc7f2a3122a2f6ac505b37de2b8c9b7d32f  input/BEAD-SNAPSHOT.json
fa3dd8e3dd2034585971f9ae782e63e42ded70e3fb52eed6766dec111d3850a4  input/BEAD37-CURRENT.json
a25b4e6bd9065251a9d141542be180335500f2e77e41f384c7858c0bbc0b0cce  input/BEAD39-CURRENT.json
e1a12cdb1801a394070e9d5319bfaa10cec47e8b3324d3a97b17ba7f956922c1  input/CANDIDATE-SOURCE-MANIFEST.json
23d89f01d85efd6fc969a1656e49654957eb6d9054be13e034c12491e5a0d901  input/CHILD-TASKS.json
65236b3fc094fe0440efbf7014bc09d0c1bff41ed67abdda75dc338fdc491e6e  input/DESIGN-NOTES.md
24620d8a89348fe13ddf867145c1be83d0dd400fe31b81a8f415bcd4585670da  input/EXECUTION-CONTRACT-DRAFT.md
5459a9cb8f9b75b3d6abd50bc973c8f99d4f32c5acdaaf42599b797b01e2b199  input/EXPOSURE-RECONCILIATION.json
68eda800dbbd16fb252e3c0ef5947998c2c7f6dc78edc1a79f963b663853a6a2  input/INDEPENDENT-REVIEW-CHECKLIST.md
37ec775cac0fcb3278f8919dc72b47b015b2029696c18a10505c52bc7fc1be23  input/INSTALLED-ENVIRONMENTS.json
dabb8cc34023210d88dc63540701d8366d5ae1c7ef36eca0c75e1b213f325452  input/INTERFACE-CORRECTION-001.json
b7d60cf01c56d894fed160def8521b709ab7c726bea2aa8fb3c1983939205624  input/INTERFACE-CORRECTION-002.json
b4741143257e4efb2dad7f149f97b5b19384c57f67dca14d85d18dd0c1bcaff1  input/INTERFACE-DRAFT.md
0f5164b4b53bc4d6a57db469ad33f7c828a3803c51162383b9ff68309cf17d30  input/KNOWN-NATIVE-DISPATCHES.json
b70a1122659221cf5d456d3c79f93c8101b6f6e69648387327ab55483d6b0fa3  input/LAUNCH-ADMISSION.json
bbd9f8ce5a8424c290b18522f0c607ebd22584f364b4d4496dbc6dbdf3f51e36  input/LOCAL-EXPOSURE-AUDIT.json
05ab5c984b70a58ce80105fa7bae78150e9e75c5220a2a899d46015ce901bf42  input/METADATA-ONLY.json
4aa33d7c826106a76db9a263c55cbfb851b90175d6018e73321819870406c1f3  input/REMOTE-EXPOSURE-AUDIT-jamess-macbook-pro-2.json
88f67aa5ab2ed2d011381e63b6d17790179e81b10b259a36d372f9de5dfea971  input/REMOTE-EXPOSURE-AUDIT-studio4.json
4bdb3796e3822cb26d853d9b400b141f4fdbbaee2481044b90137b8bea3b29e5  input/REMOTE-EXPOSURE-AUDIT-studio6.json
93f8f12646f0cd52866f1e3fefc0042bbe0a9865a83561a5cf31316069566ea6  input/REMOTE-EXPOSURE-AUDIT.json
c2016aad08152957d164a4a011e72565d1661c97a2fdca9432845364664498cd  input/RESOURCE-PROPOSAL.json
cb0013354aa0c76ed184146e38f21ed13a74fa3540d31e7781c941a3c37baac6  input/RUNTIME-COMPATIBILITY-EVIDENCE.json
779c8ba9f848ad199474d79f1f8a4c4a1d7fc6a5e41bf6a96b505e5ea544e440  input/SOURCE-HEAD-CHECK.json
5efa157e9847eb4378347fbb2ab6ae7e4deb3c72b23e0098946b1eba4f663f71  input/TECHNICAL-METADATA-SAMPLES.json
533ec22c1bae6d6a2e31c531d60ace463afd32513d7dc24129f17c489f2cb7d3  input/TECHNICAL-SOURCE-DRAFT.json
b8612183ddc78440558fffff9296d6216ecb3d90314ad3a9d48f6288ebeee64a  input/TWENTY-RECORD-METADATA-CHECK.json
af6b0a595948f03bf86e005ea9b98cd150f0f0fecda12b7b1cc0a83c8704a5ed  input/analysis-BEAD-DESCRIPTION.md
d658a72aa8d6ef26619d06a1be0809c0c40809c72b2b6117ed832881914a1059  input/intake-BEAD-DESCRIPTION.md
a7dc5eaf3c70eab776daef31bdacddeb00dd3922b124839371f4bc96d4c96fd8  input/protocol-013-design-draft.json
5da1ca41cbbcc4597617eff23b3afb701f281804abf4a5beba56cbb9b3aed178  input/review-BEAD-DESCRIPTION.md
336352046e250296fe662c4cb4119e48c0fefae38b7f8580bf2f42c159ee7db8  repo/.github/ISSUE_TEMPLATE/defect.md
b422c835d08150bf8eced71251b0018c5916a985ad14c1d5339c1dd65d905a7f  repo/.github/ISSUE_TEMPLATE/experiment.md
5b8760107211a2bbca000866c6927db4c367034a9f2bc14976c17392c7a27aa1  repo/.github/workflows/pages.yml
620444f90c67221e1414d3d72645493944579e63f846cea4d50d364efbdaa6b3  repo/.github/workflows/tests.yml
175da8777628c00706e9c49c3dcc2dc983931cad327d086ff028ecb8131d42df  repo/.gitignore
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  repo/.nojekyll
0ac8ffc971e7931d40572d1fac30ea7437ba1de9583d9f05909c3cfee5471008  repo/CHANGELOG.md
8610f7be1b10ef8f8f2120339fc77bf15d59865ea403eaa0c76fff58c4156823  repo/CITATION.cff
19646a50fcf48672dedffee5e173635eda56de93f3b5e7ab9c38beffe0856505  repo/CONTRIBUTING.md
b9d3498860f93373583b84cef00508f93bbba9e72093acc10e371fc65342a76c  repo/DATABASE.md
3060c43376584074620eb8e4c1fd148d016705d8dd8d5c61f6a08fe1710a7c39  repo/DATA_CARD.md
81d1fa0720e01c2b9e2c8b04e7d1713ee623c06db017b9583ea9a0b7e515abbd  repo/LICENSE
33d8f3bbe3b3217330c59af68b4aed6ac23890bddb3249fccca77f999794fe01  repo/MODEL_CARD.md
ff464e36eb927d052d0f024acbeb91125533b133948ceca97cbfab58aa90544e  repo/README.md
ba860434f5d1fdfcece9b1dbe15c7bfd9367150ca2de2d17e0d8032bcd04700a  repo/REPRODUCE-011.md
b1601a04efd471284f7e4ccca895131c29278ae957ceae421dad38f6e7a60fbb  repo/REPRODUCE-012.md
afcd8a0fe90ffc0af1d252a00b34236bd5a968f7927b4f7b96263ed0551e9bd7  repo/RUNBOOK.md
bf8b07dfadd80805e495cc1afe22ab79cbb3683a10581d703c9a716e7bada784  repo/STRATEGY.md
742f1e03835da99cd88415cf2599aa651f6455ef39dd2e13ebd6b15ab19010d2  repo/cross-encoder.html
4a48c81877a7ffffa1ccd090cfb2d9f3dfcfac478fff52640b16b9a7aef90efe  repo/data/cache/ds005178/sub-001/ses-001/eeg/sub-001_ses-001_task-sleep_acq-earEEG_eeg.set
785cda56a789ac37cbe020f787de7c1f1c8da77825eead0445e88abf95bc31a9  repo/data/congruence.png
d70a8e0ae7163e499a5d55d31561d7680e55c3c0e9089c55eb955c0e7db1dc13  repo/data/cross-encoder-summary.png
d41df51751f81f6f7592d5fe74c1923519b8a683f7ac07ac5b55c25cc904665f  repo/data/cross-encoder.json
829d8d380eeab0e12fb4f8bf7aa773625fd2c8d992e3c430a85cd5d0dc55cd3f  repo/data/derived/008/994b9095fb35625b16fd1e8f.npz
5c961360971ed18c88a0c2e474fece27ca7db08d359ffa8223a81f1c64b7de40  repo/data/derived/010/embeddings.npz
894cfc2f49371223ea488b6b662d909ba366ad1e84c215d18a37c9d64a138abc  repo/data/derived/010/prepared.npz
26e6deb6c7b93ef0f1df7103c71f2e785a3035982770295b61e9886ba0e54504  repo/data/derived/011/embeddings.npz
ca834711d7aada6f191b4b3eb05c1a3e1e4e40b7b4a1dde0af35f81843683533  repo/data/derived/012/native-selected.npz
093ac8c28d8d19fee6ab53bc119936e50aa373c3aedac723d4f37e2cac686dc9  repo/data/distributed-summary.png
73e712c1914071593480fc5a97b86b68ece8a159f1cdffe34d03fd3f30f13f28  repo/data/distributed.json
361108b9cbaae7415369a8344f425a187470babc21a291b43dae69be380f1c34  repo/data/events-summary.png
34696db66fbf5c6a2927e95b4d4023323d2ad2e0046c9ae41cd47b748d09da8d  repo/data/events.json
f61c6fc17b05930c0b732b2eed4994f039f8bd11e8587008edab86d42c3bfdca  repo/data/experiment-001.json
bb441885c272b23a1bbd505075db575af096f06829107df5f689b2957be31df7  repo/data/experiment-002.json
9794ccaae85f9944ca66c78160140352705a30dd08af9cc0730e37cc4a1631ec  repo/data/growth.json
c895d700770929e5d8a82be9f48399facbed04c2777e14d3c51a3d471b28f824  repo/data/pretrained-eligibility.png
bcc8d4e12f048adcad11505f15151b909c0c662f43ec838aac594dfd9587701e  repo/data/pretrained.json
6321b09899edb38c0a1ab740ba58dc21c33fe68d60774899c26c2c43a8a51f63  repo/data/repeated-sessions.json
f73b38209121e23f3c0c9de7c390d95dd9bf8ab3d807b401102e26a3363a6369  repo/data/session-distances.png
a4923b27a42dcf1b8f149b5c59e0278d74140cc5a3e26d92c6c14e10108b4152  repo/data/transition-agreement.png
30c95bff07c4e2dd8d4157adc2ab6348cc84c5072f9a5a1f3bcbf0d2b9b8f733  repo/distributed.html
fb8c515d9d1e529126c493cfb674a144c75d0f4ad12de4e8ec190f4aeccc0959  repo/eegt/__init__.py
120dfbfde3c717572035356db3fe9ba5cf8cddea1eeeeab91673313100d730a3  repo/eegt/acquire.py
4a84c228c972cab008dab508cd167b86ee60f88b0e551c1c4382385c8019352c  repo/eegt/artifacts.py
3dbb7835713c3a479b69adb600e7bd05907a7fcd4c259091f02df7b484da13f2  repo/eegt/calibrate.py
d09869e9c8644d620a896639269cf4ca7c4992a4dfd9ac15fd5a31a1cb8f7e0f  repo/eegt/cbramod.py
81e86845ec47fd41f32c451e3f4030588bd248c2729adc87848f0c955f3d9845  repo/eegt/contract.py
d58375540276c1571184c97270b503518a4ff59cdfdefaf32b547291fcc8c4c1  repo/eegt/controls.py
e8be0e5d853af6d0d57a55bbbb8c704cca5e1feea35e4944db3ee477e525a640  repo/eegt/corpus.py
cfc934775d663396713f3105dd121878186ff1d375c9531398f25a5a5c389eae  repo/eegt/cross_encoder_study.py
0f4f670b16494c6626a0edd36f53e94cbae2c1462c466209bede6108e5996266  repo/eegt/distributed_study.py
6e2c4ceeaa91f3b7109cba4f9459b35c9e35380a6f59a9c40d53e95c842f2df1  repo/eegt/evaluate.py
7bf41138c5525d11516c4a0609cd635c9e0093843efacb754fb4acd09bbcd566  repo/eegt/event_study.py
3b3689c9679856ec6ce7e43517868dc6db5d5869d951300fd0a5fe119be18350  repo/eegt/growth.py
a8f95e207ed3f67a686c97024e5ce93582891f406879330f6fb5e0cd084f3537  repo/eegt/model.py
188bfcdc5000fae25f05e8da832bebaf2d1325485fa5452823c785269db54619  repo/eegt/prepare.py
f64fa16898852048dcdd14da2f843d7b239c5e4e697e7be3a71643fb838841a0  repo/eegt/pretrained.py
80187b84274606d4d7d4c514d7eb05b892b4b8df96b8a92b6ea099293a232e3c  repo/eegt/pretrained_study.py
5f39bbd820147fb4d4d1df715cd5b818c8fd9f3be46797cf090098812105b6c3  repo/eegt/repeated.py
c9f15e16cb289ac22ecdfad16f17c834c2453e77d1503d1177574e19e5d745d1  repo/eegt/signal.py
f0c7c3dbf47f819aed52216369a7878cdf792b305999759704a86bcc3615bf0d  repo/eegt/transitions.py
311b4784045cc25c9cdc157c4087bc292cdaf6cea780e9d1bebf672eeb8a6299  repo/eegt/validation_engineering.py
c773b4159d907783df945e1e1e934efbddf8fd4e2bd851066e9172da65496761  repo/eegt/validation_intake.py
fa405fba4a1aea3ba21dc5ff520a7000a588f5d8998f66e06d0e5bc33ee23e97  repo/eegt/validation_provenance.py
31568d7d54fd363bc0030bf28af999f6757ba02d45cd0dd13bbb7060aa97cdec  repo/eegt/validation_study.py
eb839b706e4d7219842e96d7dc33285844abc794292602deb3498be7b699537c  repo/eegt/vendor/cbramod/LICENSE
0d7a6e86a934386c8019fbc54a2232c02455acdbf74cee1859bb60f61b797de1  repo/eegt/vendor/cbramod/NOTICE
e8193e557ee3ca3f422c17ae661fb8e4df671d9228c413ea092d879af1b8296b  repo/eegt/vendor/cbramod/cbramod.py
90e90b8c98ca7eb543c44e32afc29674d3f71cb090692ad9f82db3a43edf334c  repo/eegt/vendor/cbramod/criss_cross_transformer.py
c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4  repo/eegt/vendor/codebrain/LICENSE
26a18a2af6ee4936dad2a50000b842ba0dcf73ceeaf896309a43f18ba2e8533e  repo/eegt/vendor/codebrain/NOTICE
94f12f897ab4e8784a45d64fb65664184c872e6928159a6759fda2920c488be8  repo/eegt/vendor/codebrain/SGConv.py
9f7b892a3908ad838cb43a842c14c2a165e7f93d6243b31f0c9d32c90183253b  repo/eegt/vendor/codebrain/SSSM.py
80a9b8f62693e551c7f385a911fa15ca321325b7983f63da8fc7373ba451f572  repo/eegt/waveform_events.py
e55adc9ad1ac993c1ac5c66420f8052e1e79ad6b2390c93a720cbc8c99974c35  repo/events.html
8c230b2e0028d75ed23125d898c7a4a78fe43877d7740c017aa41ab01d7f5bde  repo/favicon.svg
cf9bc3d59e32dd1b88a014d0252be3c07cbde17a062fd4c5adee1fa2e569ec93  repo/growth.html
2dc552d264a1ccdd3135ead4eb14af86b95171db5d31e59b2866f6e5caec2b5e  repo/index.html
b1f54bfa5673aef32ee75c2214c7e83c7fd11cfd3efb2204397a2df3a648e6fd  repo/notes/correction-001.md
04ab301e616a86b588f25efd0832413b0c40c64b26e0410068f804497805aa5a  repo/notes/experiment-001.json
def1bbfffdbce91fa863375db2034b04f95ac74c2d7a74cb4976b42748e657af  repo/notes/experiment-001.md
4c078151e995fa8656747d86f329ce00ec16719e8e3aa1c0a630f3572d642981  repo/notes/experiment-002.md
bcfe169a6e709c5984219abad1a6fc88e678941cb025db40c1637a60cadd2e9b  repo/notes/experiment-003.md
ecc48b95476fd6fe7dc8b09a04ae6a5cf566ddee447c617bf91cc68beb4f0a92  repo/notes/experiment-004.md
a6d22a317835751a474f0175a975a4a11fbb6c9da82e9dd8c47725c37af94eaa  repo/notes/experiment-006.md
b95522f69b4d676458cc5e415bdde0049baf870de3d16fcc510509b86bcf1240  repo/notes/experiment-007.md
3e5ac9971cacc563b47464d36b2be2be1b11ebd2cd84506bc3a32c70b15c5781  repo/notes/experiment-008.md
da68e2d201177dcd24c05e6a2eb16597d202deb1254b411e4eac89acc22484b8  repo/notes/experiment-009.md
d01d8a05b425984c2ea44d006c5a2842ce11ee7713cba3982dc628b6c9ae342f  repo/notes/experiment-010.md
b86ef42044ddb31e1f1c628813734d855b44b1617c183eb1334d12ab3b2d628a  repo/notes/experiment-011.md
57ee803b6d6ef309e4b88f62a335b3d0ebb7d573745b9891a695afc047fa87b3  repo/notes/experiment-012.md
59ef72e764524cda196fb08a18a91503e30aa518c5a0cbea492a38b9b7bb61a6  repo/notes/model-compatibility-2026-09-25.md
3b3d19ed2d8b05f0e52a033b31bd34c287cad9d86c6a5a0d7c11c940a1f81c3d  repo/notes/release-0.2.0.md
c56f0cb47df9f82776de7859f5fb8a63907b6175c1c69fa8001d2ccb8e92674d  repo/notes/release-v0.3.0.md
e6495b7c05c2a73fb3c5191fbd3a3cada2ed30d6837721b7ea167ea985aa5193  repo/notes/research-intake-2026-09-25.md
b2de89eabb6470cc722c877c8c99442021a36d7149fdec513bf06cdb998062d5  repo/notes/validation-003.md
5bce222e15a3c41669031d30ff5d38f2c4bced9e7b26b4c9410cf0b1d0fcddd8  repo/notes/validation-008.md
14b13287ee0da7af3712397f82eec334db663afc14a6c04836ac282d7f5e76e1  repo/notes/validation-009.md
95541284dd539278e89dc2a493fbcedd8c1296ca87906691e1bae1fa0e748be1  repo/notes/validation-010.md
0cc644ad7a6037e9658bacc22b730fe93c0f816cd3caec8d12b1f3b4146efcce  repo/notes/validation-011.md
301505e42c3a50fbf9a30cb14e21fb36d6042949d1aa938f011364bb61d18ccb  repo/notes/validation-012.md
ff7b27c9d95895d6f446e8d8b52179b5371f5f24d11bfb7987a95f362b7ab66b  repo/pretrained.html
d62b4df2feab8e9774fb054008993aa2abdae22bed67ea39c901cbeb4d9a5534  repo/protocol/INPUT-CONTRACT.md
37863a26d78404f2013e5a16419dd33c84ede676a4aa4b815b38708c411a95b6  repo/protocol/amendment-001.md
6b24e9bfbc0e483868261172783f0576bad22835410ca4478a59046fe5c810df  repo/protocol/amendment-002.md
27374d34796b273d1b32dc85884507d7b33c6974155ae269e2a95afc71e1cfab  repo/protocol/amendment-003.md
2358ceb6673058989932ac70e83ae7fd52151b0dd5ab8dc53db5371b130807f5  repo/protocol/corpus-manifest-008.json
533ec22c1bae6d6a2e31c531d60ace463afd32513d7dc24129f17c489f2cb7d3  repo/protocol/corpus-manifest-013.json
a6dac5e85c6fe080f8665aa6223d45074b3880581c80701aff8bbfd32bc8d904  repo/protocol/corpus-manifest-v1.json
438a320618998cc70bc9c1d36f68f1f66590dced6cd07f51b69dfbc20bc36202  repo/protocol/corpus-v1.json
7aefc9cb2fee774bc24d1ec3a6a85c467311e4e8660e2388792cfa7dde2df10c  repo/protocol/direct-events-methods.md
93d4769d8d1653f26ed4c64bfaf312083f1e0511a47fb830c4319d2a5326fe17  repo/protocol/engineering-input-013.json
6d6449e057117221cfa9f01d5d9b30af518d223e60d81fa02ec0366ae27b0675  repo/protocol/experiment-002.json
1a0da132216c4da31dd78345950db95439ada3d543788664b42f6f5c0f0939a0  repo/protocol/experiment-003.json
bf19d4cfe6dd2b31f8d16f5e768ed00cbfff875b926f2af3fa75c27f3b0d7860  repo/protocol/experiment-008.json
5c45dc42d237b89653909bf536f3cf44927a28303f808ac1d0bc48b2c00562f1  repo/protocol/experiment-009.json
75f79f511d286254e544a50e470248153dc3b3fe38e1596936f748162cb3fa9b  repo/protocol/experiment-010.json
792b56402d7d95eef8a7ed4b727d73b22819a521b6b99af34a37cacf2877ca2e  repo/protocol/experiment-011.json
86f41254f1fc35a0d95e4e9aab45bec0e12d1964ec18d8a38a7d92c57daf92e9  repo/protocol/experiment-012-methods.md
60f02a8dce9a086be3a89fe612eb9437088054f007d14348c827292fae34e138  repo/protocol/experiment-012.json
680b442a3d3cb556748c541e3f50ab8711164b95ef6deff170e1d12c1c5bf9f9  repo/protocol/experiment-013.json
3061de6f1dbe4f0332f550133bf818df8922a5eb8e9c5c6616330758bf7415cd  repo/protocol/future-ear-source-intake-2026-09-25.json
46af5d4e597f54eaaaba1598b7afe4c169281c673c1b87ad7e52b0d4c7927fda  repo/protocol/neurable-availability-2026-09-25.json
c0d32749f5f736e3eb962f8dfa20787dffa5f487c2419dd5dc88666d0f767788  repo/protocol/neurable-availability-recheck-2026-09-25.json
1b0738a737f987f1b774f8206d287e7f5bf706c10bd6aae97bf952cd3cc22380  repo/protocol/neurable-pilot.md
afeb4181a98c7c030d36373f4dbbc40822fc463def3a8a27800a66764898d00c  repo/protocol/source-manifest.json
0d2c064c1ef0442bccc45e239f523539716cf3d61d38e4dd70dfb8c04d4b5bd6  repo/protocol/strategy-v2.md
1490c6adba3dccf06eb5ca3f85613d5ad1412a34125bbee5aa40b57136e6fcd3  repo/protocol/strategy-v3.md
360b98459b1a3c25dd2b4a793a2e6db3b15dc282089b01a38edc673505481e2c  repo/protocol/transition-methods.md
39049c9e6427cc1d6c45baa93d9e96b6aefb882c1237e103196fd2ac87119a3d  repo/protocol/waveform-battery.json
c79673d00faea95a564ab4348d67fbb424fdc3d891f126762263ad635e1299ec  repo/pyproject.toml
7e531543c4d2e45df38ac89f4398db48bd79354386f337601642b38f6bbe6bea  repo/repeated-sessions.html
c70edc4ff592cda5d77139b8b29912ebb0e2853c9c2b1139fab79022816b6182  repo/requirements-encoder.lock
9d6ace62d69501fa83a8c6a0c4d7fd388e61aa715c71af48c29c429c061791ec  repo/requirements-events.lock
350343d0cbfe4fd641d1ca252f451929a8347ceaba5201c4e25df1a4ead6ffb6  repo/requirements.lock
8c7f5529f140aa83a4d9be9bbc880718eebe309eb4c1957df7a54ffe69c4a394  repo/results/002/SHA256SUMS
6e63a36e06317a9ecee33e622e933f7d02780d9c08fb25ecaec86577a9290a99  repo/results/002/acquisition.json
409ff8fcdb98c91ef6c0ba963789ce859baeee5116d34a3a2927ac64eef764a5  repo/results/002/assignments.npz
785cda56a789ac37cbe020f787de7c1f1c8da77825eead0445e88abf95bc31a9  repo/results/002/congruence.png
008b644822da84e9282ce34207aeefab53d3030b5b7d4f1b83d4f21a184f8303  repo/results/002/evaluation-index.npz
3bb202389ddb1df8568f751316d2a195f861e32bbc2dd41ea600566a33aca84d  repo/results/002/export-audit.json
9b0b0d2f8eb70695834e2b85dd6ae3e145391ad963fa480a525a77afbbde15e8  repo/results/002/file-manifest.json
96def405cf26658f34c5ff6bbe65261b38151c78763534d0a0ea93fd99fa8a6f  repo/results/002/integration-acceptance.json
f1b948f10a9270bb3e8734d670eed246640cd8f6725c593212ddd54cfad9899e  repo/results/002/metrics.json
ceb5b4708757d0bb689abb8d38ddde427c04ad90b899bfab02d2d09c8803692c  repo/results/002/models.npz
abdafcc8a7a4a4131141d4c9b84f37fd67685d20575f88b8ee3b78f622fae4bd  repo/results/002/prepared-inputs.json
5c9b56f67ab35dd6a2dee3feb0e24631e8784992b21cefb674fac237a8b1393f  repo/results/002/provenance.json
02545b7591726a00827a85b11a5dd41a0e50c4c89dddc4e131d2c0e298289339  repo/results/002/qc.json
8046571e2d77ad35a89d0b62d1d57b7a71e723c83655cbf8efe7651554a7bbea  repo/results/002/release-assets.json
7bbcad850b4f28261e6940cb8c2f80c8ba43014844d1ea5ba71fb02ec7ce7839  repo/results/002/repair-equivalence.json
3d5fbf1b14373ab0ff641c51dc1bd37d123f5d624adb49a72cb2a12444b6cd79  repo/results/002/reproduction.json
19b681aa0034a259fcc5240727f0b6754f90a15d2a40fc202dba603a0abb1a0e  repo/results/002/resources.json
bb441885c272b23a1bbd505075db575af096f06829107df5f689b2957be31df7  repo/results/002/site-summary.json
e2f178208c5d7ccf57f3a0821d3d35e4171c0dbdc253db769b73d5e05b532275  repo/results/002/window-hashes.csv.gz
0adc6f38969f9cfee6aefa95e62874fbd156b78f225f86d0ea9e46ed47740ceb  repo/results/002/windows.csv.gz
2eef0589f75a7b65d57d1a8d595be29c03323b0046a7c23f8d05a81474fa5516  repo/results/003/author-receipt.json
8ead3548a9fb1911a5a58cb3ab4b91a667225affcbf6899df904c117f782706f  repo/results/003/coordinate-repair-equivalence.json
48635788222bbae0e67e2f8cd2b7801047feb1a9cad6fb849d0f966e1f560dd3  repo/results/003/features.json
c37fcb23e99e217ee0405504cab12723563a0717834643c949aa3116864f5879  repo/results/003/model.json
c66be6a8f4e7c35d14a84165a0069507d8f4ab254d2c234c8412e30407f1c2ee  repo/results/003/repair-equivalence.json
1a867fe7a431f1d114271bcc46efa339ed8a22461d4575f992e93a25c23fe87d  repo/results/003/summary.json
de7ca67dca4f23957414c228133198595f0956664a1b4de6c50d51989b117318  repo/results/006/01c0e5a982669a40ef39a2da.json
e6e4dcb364302c681decd024271a46721c02c7977255d84252c2ecd66207d8ed  repo/results/006/0d196f92f0b378394cd760e6.json
054b478909170fbbf1df399cc1610ed83b71f432f4dfe81aa20e13de5ce3cdff  repo/results/006/1b5acf2e3d881f8d845c5c3d.json
1d23dae184858226f44aa80b1043c0fce5a7c4cc47ebc6a9299a53e238d9ed3a  repo/results/006/1e75564b510efbab5250645f.json
3de451512244a6497458180d9845d8e6d9b4fb31844e97215283718cf6a57779  repo/results/006/218a3073e690fd445c9ff785.json
c07205a7664730eba7d3adc91ff0b6db11190bf9c2c216660cbc473b1d90d7a7  repo/results/006/2219351196d1be6920339bc0.json
e59a0a5e7966cb08a3a805eb137bbdff6630625c14381495172347460b21890b  repo/results/006/241f1a0efee9b97ef2e8312a.json
d8e7a0c5a519daaad2ed00fc7c6cd6cc4243f75f457d4620e91833d3dafe238f  repo/results/006/24ed84bce3c17a6934b8cf46.json
b96f202b58d46e80e20ebb789e858345b0e18b76188eab39b6b37f6597cdbf69  repo/results/006/28dcd586e1e3ea2aaf2e1e15.json
707b135fb57a873e65ca4afe7dd0657a8f7cebede16f36336a772fd544bd361e  repo/results/006/2e81fd22516c2019aad9def1.json
0c233ac9e744cfd99b7019c56474d49fcd62319c7981e4108ddd83cf1fda79ef  repo/results/006/2fd267fdbb112601cdfd31e9.json
ba64ba8629dca5be562d8f5ec90000b43e267391b835ee47744e2b1da865da0f  repo/results/006/306a881a6e49424da743316b.json
b9b849963bcbbe7853e48fa753a44839f1a5c417c9a40133c2a38409aa94737b  repo/results/006/32bda0c52065b7bf709b3039.json
cebff0317a0282b54e0aea69f6507a10f2b6bd411e896bb6a34b637a7def76c2  repo/results/006/3326ea898725be8674a28286.json
963f70fc92699247831bfa87b7d3a5143fa0fd314c1293d84360406d6831f7be  repo/results/006/361058659c8702ad20e20527.json
460e3906da3130b94205aa351b122b239bb3aa559a12636cf3dd62636f158abb  repo/results/006/3866b7eef005d3b1e4ca4919.json
bffb1ba2fb4422c5a2581dc3e2fe884cca04a5ccc87e7fbeb8df5674a543ce57  repo/results/006/38c82dce09dfa2382923466d.json
85c8aa6070c8e8fe15dbbc7c88d8f888bb723d9d598c2c382172e3559538a81b  repo/results/006/3d16f5d9d56d443bf0ee739c.json
ce5e00888d1219cf707c4411e6f875c7c791f9f63c9090907a9d1f8755277d31  repo/results/006/3f6d6bc992797e60bf3e7b29.json
cfc7313cf81d0d56319fc2a5cd713b36fe465ed7fe4a0fd9a848ae11220a07cb  repo/results/006/419fca2fb009345729cc774f.json
e574f7ae28954e05f8d5d3a2216454a3c82d696abc5162f4e519eabcb423f6ec  repo/results/006/47f6976731f4a41af0e298cf.json
4987e4adcd292a396adb2d3485acda411921fc697ebcc7b7cb7cb8435c969973  repo/results/006/4bd007ba65c9e5932ca3e165.json
1554c4d527747336b075cba9288cd4cf3bd3c24eb3cbb320fafd3195a031e5f4  repo/results/006/5587fd9f02629818e2d96390.json
34ca4441ceb7c9cf63bd09b76232eb65aff76cfcb4768fcd2d07b0f4a81a4ced  repo/results/006/6288c5df99166b6b5d676bbd.json
00509192a63543e18c326db3a924c4e91fd25b6ea7975a49a372394fac5fd400  repo/results/006/6b0fcc063642efabe9a42974.json
8e6b6639f8b2594ea20cca5216b551b3b86f090f23f5609730b51bbb8e52765c  repo/results/006/6cf1efff79eb1002775afb83.json
b432f5c8a7900f7e2038ae48623a0c9e7d7d572fdd93b83934e9a278d0f03d80  repo/results/006/71db1e918bf200fc43ed8f82.json
73f2fd7e9ef5cc2d64f090983368d0b1b5b108c8b684c6b2f9beea3b668b7452  repo/results/006/7a11c4433d6f9324bcc1083e.json
fd4b41d9decae83754d23c85874a8dc770f5c0c16204a8a15c8bea7468000913  repo/results/006/80ec5c9af848d14204affac8.json
d6fcfe74d7cc15f017e69d13bf7b1ede805dd8273db9bad2f766f022f2f392f1  repo/results/006/813fc44239acd4d32bea113f.json
08c1ccf8117f6c21d3eae86ffacb05058efa253b3b3b7b6bad1537bdf12ce264  repo/results/006/817b1ea63f7016a9620fd513.json
37e74eb6f1c02971a482fe77e6c41f38aeeee311f06828f1336aa03874f09990  repo/results/006/83094d85bd89374f421dfdca.json
d47f75709ec03719ecbb4b8bee6b33a0a2df2e914c4eebf20d288f5adda215e4  repo/results/006/8db5bebfca952d2824051b0e.json
5643e6cd06ed1901b2d705d6a9220ae6b0b5b09b04af001433cf78a8ff65c333  repo/results/006/96dd2209487bed2c3a4a2dd4.json
cd7fdf4ec0cbd06f89a2c7f62bbbe85e2feb2747be82e3ccdb702e45889d8cd6  repo/results/006/987a91bce590ac8566c7a209.json
8f9638beed1393754882f2df29d47f3497223c100f3f902ad2fa2d5994dcdd4c  repo/results/006/9bbf4329af49afd4b214695e.json
8ea9271e8f1a4afb35837e65d43e7c39d9d641fdf7e9d3abe41a72d2e94bf053  repo/results/006/a3063e75f57c58fd4887848f.json
b3590481cb161370c8d4dd88172e2f2a1b2fac48735b569ea8645e7de4dfe92f  repo/results/006/a4ee1f60731803275830d50f.json
b76024fdd8fafc828c7e0f674e47290a653792c90bdab1382d0415639a21f4a1  repo/results/006/ad5a3328b6c55efbb3221625.json
88d0a70a0937050242655408a92401f945e970ca49a35e3ac470e365d30b3bf1  repo/results/006/b14de6aa3005cda869a7dac2.json
811aea995e0a21c1730b975f53c18be698cc4f14a88122f4da4c4aea8648d41f  repo/results/006/b2d963340624e2c88af9a4e7.json
cc94122a8abdbc137f60b37b315cf48fcdf72974bfe491450f4f85ec777c5507  repo/results/006/b74b68bebcda493a4db8952a.json
651cdff3abde386f2f15330fc74ae25182fb65e361afeb10b5b8e62a2a0b297f  repo/results/006/bacddb4739a20ec7769d2c61.json
0ea30ecc6e778fd0a7a28adc4ba8b3a3fb1b56b00a3c6c5761aa5b7400e630c6  repo/results/006/be1e68e53464fe21c9ea8f6d.json
94bc8781aeb831ef48678ecd64838d98b3d9fbc2987e0dc9f7ecca58cbdebb7b  repo/results/006/c1781083d1b9641c0b2b894c.json
16cb92290ce02832074b5da1f901a4a903693d7d5c153ad6077750da8311ff0d  repo/results/006/cfe528de4fb205fdfafcf49f.json
8ff65f07dce00624ccc707b9f2fd6815106358b306beaad7458ec885d91cf0d9  repo/results/006/d370dbd08c9368b7aba96fd4.json
e7a3e31505ba0ec3aa6ca16d98c55158f71b80a4f52b0b252669d11a1a2f661d  repo/results/006/d38fd501d069612f1e3c216c.json
9d4e754b7884d09a8f5f5fb500a45c9958452f828a1e1f26aeec8f4f0745e33e  repo/results/006/d3f9379217af650b56498de9.json
e39f15f84f9b059fe88a4cf98a3563881610a29fa16746a69906fcbcf2700f77  repo/results/006/db100e5f83c5cf0ca5f68595.json
1474c1cd74cc6856d3651097503bfcd533791507e12d51f8a400b45189504833  repo/results/006/dbfa5c04a8c224a2658cb240.json
53f4e0a6294ebb9cf00560c5517410463872ad349b2413725cbb60495f4f9a7d  repo/results/006/dd7a7ce86ae2e4cc9f5c6695.json
d09a3a10f51a2fc53043dbe76756676f2b380c7a3631097e36c2b1db074dabd4  repo/results/006/e5f08ecd96f130639329ad9e.json
9505d68eb39d780748999c49c2f0353a61f62bb596db15d9dd37bfdb24c78bc8  repo/results/006/e9394f83b05ae9a5dcceb9cd.json
497d6898c6998490ca978dc543050c0448a18c0dab73cac7402dc64d7d2f55fe  repo/results/006/f8fa9847c1c8378bf40090e7.json
bdc4b29d274302fd8e7a3bff8333c8e9b10043f2de052becb096365e0e870c84  repo/results/006/row-receipt.json
37b95a3d488b18391f9e885b81bb1bad9a0947676c8a6b65b0eb6cc86437eab3  repo/results/006/summary.json
17e289452462fd71ab8cd65104b93fd130aabd7115673f8248349cadf4bd399f  repo/results/007/audit.json
93d767af17a259237f19117798aaaa3dede6a854b956e89fde81ceaea69f916e  repo/results/007/independent-review.json
bacdd108433b74552c126b5f4f20ea0e4167ca5a5afeda6f6065922718ac0270  repo/results/007/processing-receipt.json
69317f811a5a5018586e807046e713df354fd67803c108ec90aea426258fd154  repo/results/007/summary.json
cd59c7efb862f34f8699b4e31ca8579ff397f837800d86c008a40c3d9620a816  repo/results/008/acquisition.json
0d405a99bf4a0be5834cc6121469ef289d25e14a0d78bfe0f6cda858b24287ab  repo/results/008/features.json
eb5b8ec14e08a22026ae380ad257887c9528844e2559f6a8de213c7e1607e634  repo/results/008/independent-review.json
74ff51cf001dda7d5b191d5044c36b6a1dfbd4cf7a52fb78dc8e4c0d77dad24a  repo/results/008/model-audit-receipt.json
732b8c534f2d9a3eaef81fe7c827c2974167ee0a97143d460580858dc98bb55d  repo/results/008/model-compatibility.json
bff756e3a73d21fc24ee9a355d8ac1456720008a4f1f60c85120a6f8dbb340ce  repo/results/008/processing-receipt.json
33e0ac19e09888435be1c41c1baffb03d722ef73f0ae11c02f9b509efa905654  repo/results/008/qualification.json
d544d9e38ceaec15dbc5cf387901b43443edd5872b6e045dcc476baff6395d00  repo/results/008/report.json
6321b09899edb38c0a1ab740ba58dc21c33fe68d60774899c26c2c43a8a51f63  repo/results/008/summary.json
4644386064b217c9fc9a50f08329e5d2cb5657b897e5f6c183b9a7f08746ee59  repo/results/009/adapter/MODEL-RECEIPT.json
062cb9d5aa265c9c174b61e6608303e203c4ed54e3d20738d0bd1568d49a49e0  repo/results/009/adapter/REPORT.md
4b3ae7f22215564e796115575ad97378a47eb659228393142e0903ed410c81ca  repo/results/009/adapter/benchmark.json
9d8c8206d8b6900cd25f4ab84a153f0d52ef625bf9da3ef4dfb8c29b56048c95  repo/results/009/adapter/checkpoint-keys.tsv
1db32b395b1ca94bce6243882163a9f0b650827534a6dccdccaf4e2d2c802c68  repo/results/009/adapter/requirements-encoder.lock
24f6326fe2248d183601f1ca6743f22b36b4dd42939bf209f613eaa900e69edd  repo/results/009/adapter/test-output.txt
14fe2162eaddeff7a9cc510be9042a6be05afa3e903a08aa64c66b94e0066700  repo/results/009/adapter/vendor.patch
57cdb66c5ed7541bf24461e53bcb049fd4620089dd211c02ca41307f1e4618a9  repo/results/009/bundle-verification.json
3d6b2312f6e423cb24b446737b123a666e16b0e363ecaee913825cab4c734144  repo/results/009/execution-admission.json
7ec399c05da686f884c38af3e40ed72069a8758bcc3f84cd915a121ad1ffdd4e  repo/results/009/general-tests.txt
e8732aa57914871ffc0f8bbf7c3053ed1c0478868bbd3686baccd5c89eb3198a  repo/results/009/independent-review.json
a31326d877ffdf96749f48927865e78b06d5aae8d0d1b84d9c69b45299641fb4  repo/results/009/independent-review.md
e55295da6537b0762ec0ac96719b55aa3a704fd73211a7f9a8db77735ef4600d  repo/results/009/inference.json
f2f65ec7ae34ff6a1f8baa0d60d97e6ce4de0b168d61af6da72dd2e0f4b1e117  repo/results/009/inference.log
b4f8103b0d0beac251cc773dc5f411e44ad56ba79739e78830b790a9a2acdff7  repo/results/009/prepared.json
a1bf7d12eb43fda4a701138b1ed14ff56033e939e03abef11171671a22c6fe12  repo/results/009/report.json
33c6ebb4bbc8face67fdd54797504478542d9d7984483acc29ac093f4b155d41  repo/results/009/review-fixes.json
e49f19e7ada648ee8a8296138803ec8524a5c814c61918c2cebab274b64eb0bc  repo/results/009/review-fixes.md
5e3a9ed239abe80e4edb02ee7e8f9b71e15ba5ae2437f3403064279661a60bc9  repo/results/009/review-initial.json
b55bca03b8abeab81902d346d96f8f0c389537dff35c3549da80fe098f742734  repo/results/009/review-initial.md
bcc8d4e12f048adcad11505f15151b909c0c662f43ec838aac594dfd9587701e  repo/results/009/summary.json
b2bc20f72cc89aae9f29a88547d0714fb8aaf61942fd1d4f45a710810b98809a  repo/results/010/bundle-verification.json
f8d9a708ad0944c15053d4bb31c6659019668f476397168d00e31cda8f1371b7  repo/results/010/execution.json
f5f5a97686f47a39f2302257fc441ef48131e559932541a658e0e135fc2dfddd  repo/results/010/general-tests.txt
6aa62f30136908969cbccb127cceeff183a983b04235a1d6dcb551ec36051040  repo/results/010/independent-audit-result.json
c3cfd6a8784e0b84a9848d35d4dd10ef953cdc982ab194783decc7c02e43d712  repo/results/010/independent-review.json
fa8cac29627461118395a41801075989485fde55364016ecff9f63a4b2749917  repo/results/010/independent-review.md
be6ac5395f9c251df6e3e7e29540e642bcbe1da373391f47a6a28645df036201  repo/results/010/inference.json
3254c06181e19ab7b3f9fd759bd41681ac67a2659070df1f3a4468098c4bd9e2  repo/results/010/integration-checks.json
545186e75a2a1ca88b0e1da3dc08100fa6bf8d90c6c788358b523e224f3e367c  repo/results/010/prepared.json
e6a24f3b38a02e4af16081291e9fd589c3685404c81b741cf2c619006a03813e  repo/results/010/review-publication-initial.json
f60bc00609164ab18b883452f420858b7d8bd830c22cdc9e207dbcf13d47c241  repo/results/010/review-publication-initial.md
24acef48aae8003e3d1d83d96992afeef6f86468502c454037b012d0272ac455  repo/results/010/reviewer-audit-source.txt
66bb64777a832922bc90707f09d6b6bd9d179db00be2295e4ad415bec9fb2efd  repo/results/010/science-review.json
3f77f69b44ee04f86848954d2341586389e0a96f3ee283445923d91bef865a07  repo/results/010/science-review.md
5c077f25e6e81ee6464ab8b2b42fc8ffb63c663f2357b455448f7ec8b8724bbc  repo/results/010/summary.json
4de51eab3cc57527fb2cbcdbc3f0a241d99f79b5a477e9b204c6af240ac5ce7b  repo/results/011/analysis-amendment.json
41fa67f0d898a0af2000dc2548d992ad00cdea34095cf083de6dbd66411f2155  repo/results/011/evaluation-failed-1.log
968565341b66102e7cfc11e7b05e757b272e9a07ee426c97edc8f5209cd589a8  repo/results/011/frozen-tests/test_cross_encoder_study.py
50a5522b41de20bd34c544eb434288a5bb852f7752135db73a63d87d6149e0e3  repo/results/011/implementation-review/ACCEPTANCE.json
bcc9f6427612918ca05c29bc57eecf75b751532d68f61a3100930aefce49f7fe  repo/results/011/implementation-review/analysis-amendment.diff
976e09fa993021bb730cceedf75cc2287f1cf09347e1064f62a02a3bed30f28a  repo/results/011/implementation-review/test-harness-amendment.json
b7bd9f9834c700ab345a28e006eca0750ebfb7ab0afcf4698bfcf849264f65bb  repo/results/011/implementation-review/tests.log
4f60dd0c2336b7e46a83c54aa96fe14efbbaf077bcdd32406987b2f06bb6aa8b  repo/results/011/implementation-review/verification.json
1ef5d0c07889e65e7cdbc97bc8c7492199f9b5f260f07b6d9b7e20797b03bd40  repo/results/011/implementation-review/verify.py
3d4031b8440629c250d1cf20ea9e2c0ef71d011203f874816476fb32c73a0778  repo/results/011/implementation-review/worker-files.json
b82667fb61fd1b2e204994cdabb9d9baa41648905d2a9c061a1259db3e8614e6  repo/results/011/implementation-review/worker-report.md
28f66c7f97af94181810e6f5cf817b72ccc88b104e7a8d26f647ae666e6fb82a  repo/results/011/inference.json
d41df51751f81f6f7592d5fe74c1923519b8a683f7ac07ac5b55c25cc904665f  repo/results/011/offline-reproduction/summary.json
f5b54d32f7cf5e29160aa3b39be642c10e92e482d9808d89742459339a1a4c32  repo/results/011/pre-amendment-cross_encoder_study.py
292e56db962a5da0e1fd916331277542e9586a302ff561a90314a34d6cb5d2fe  repo/results/011/pre-offline-fix/analysis-amendment-1.diff
4e43b8c9a057f24a2c54f195cc045a678d13995180e9040fa7d8075ab8b1f4d3  repo/results/011/pre-offline-fix/analysis-amendment-1.json
264179c1623c8acae4113027ff08997244dfd01bd0ca9afd0ef682f259b66fbc  repo/results/011/pre-offline-fix/cross_encoder_study.py
9ef3f4890fce33f51fec85db14291417bf6856191c7e397c3842b1c0a408d3f5  repo/results/011/pre-offline-fix/offline-reproduction/summary.json
9ef3f4890fce33f51fec85db14291417bf6856191c7e397c3842b1c0a408d3f5  repo/results/011/pre-offline-fix/summary.json
b875296da9301df81ae255ed34a3e649c8571d646dbaf495156b8616eb67701a  repo/results/011/release-review.json
36929a2c4118f750ff74443456f3543006ad2ed866811bb3354bbb3a0f6d5082  repo/results/011/reproduction-inputs/FREEZE.json
e05a41b9fa725ad7fec6a49aa52b013d883cce46b3cd0d735b3d1f12bc8a1011  repo/results/011/reproduction-inputs/adapter-acceptance.json
792b56402d7d95eef8a7ed4b727d73b22819a521b6b99af34a37cacf2877ca2e  repo/results/011/reproduction-inputs/experiment-011.json
60ac1312851e60017dc7e21c89f5570ebb36c1288354a69822db74d1fc3c590a  repo/results/011/run-manifest.json
d41df51751f81f6f7592d5fe74c1923519b8a683f7ac07ac5b55c25cc904665f  repo/results/011/summary.json
3359e83c54cdd1bc58d74f9779610a42ebe0f6b626c0cd786ef7ba159cef7ce0  repo/results/012/RUN-SOURCE-MANIFEST.json
a09f60056c0e418b1e1f887a1a63c6c457e9d80bd5539162a6987dcf67c399d9  repo/results/012/code-review-r1/REVIEW.json
e0082d0d6a8e60144802f9a30632e367059f528b946f445f53492ca7f8c2e41d  repo/results/012/code-review-r1/REVIEW.md
8a9d7b0db9470ad04f891a3d94f1b789688e7fb8f276c9e13aa6f3a159b97b11  repo/results/012/code-review-r1/adversarial_review.py
2cd0dfef5ab70ca41f7cd69ee56d14838b7750c7636589198bb40b89bfa70eb8  repo/results/012/code-review-r2/CORRECTION-001.json
2600ef8194205ee7b582a8d2c174adf897bd638945aa103ea1c9fbd6dd6f32d3  repo/results/012/code-review-r2/NATIVE-CHECKPOINT.json
2b15bcb47015dfb2ef0d4603b58d03bf75215a64f7994a51846c4894ad974b06  repo/results/012/code-review-r2/RECHECK.json
ebf4f9fcfc8324e24ca6926c4b1ddbb99dfe7ba1ed516d9af9fc437043f860f2  repo/results/012/code-review-r2/RECHECK.md
5a33ac31d4794ee9eaad1be034e761b8c5340ca3b517e72598e544ea36550551  repo/results/012/code-review-r2/adversarial_r2.py
6e9326ddd320a3bbeeb4dd3354f5ad6284abdbab2b9515c843c8739da86ba754  repo/results/012/code-review-r2/recompute_primary.py
07b2c086e5da9362c53dfb95061d9303b5f477a1a100a03ef1965548440dba91  repo/results/012/code-review-r2/recomputed-primary.json
ad3c2061b329aa5e22e63e2e67407e02e3191ffbda2edbca5eed794eb2ba1ed3  repo/results/012/code-review-r2/root-windows-tests.log
33320cca43e031be80af0caa7ec4063c0328b45c6d3453561fb0c33592b463c0  repo/results/012/extracted-reproduction.json
ae38d8ba0533d29ddd61c6bf6c30c241ee67db750324bd3451c360b68a6a9171  repo/results/012/extraction-receipt.json
2d418fae82122413a18e322f1cdfc66e8a6ad787e91fcfbed3bff09556cde781  repo/results/012/first-block-checkpoint.json
8f316918c467ac5b24aa5ca8103f256d32362dcfda57355d036f9b0fa0e29ff5  repo/results/012/generated-reproduction.json
1e009e3866b6a52643ea3aa6c90812d7c09d2809f950bf88ab9d4dddb1a95379  repo/results/012/implementation-review/ACCEPTANCE.json
abeca19b0688591c6137eae4871779acd94487918f1475fe8a770c87be1a1d5c  repo/results/012/implementation-review/EMPIRICAL-AUDIT-PLAN.json
2f7b77a9e2a8fc3d5ca3a9da3824134b9f2236863d3203b1b25db66d50d3c147  repo/results/012/implementation-review/NUMERICAL-ADMISSION.json
052158ea6a1a411247d38bb5f7c11e99f3423e957d8113c26b5f0d39eb30f596  repo/results/012/implementation-review/REGENERATION-HARNESS-CORRECTION.json
3d31561c94032635d986ff16a98c0c1406376739c352c597e713e8f6bc6d5857  repo/results/012/implementation-review/REVIEW-DISPOSITIONS.json
09b501f064c46e6185bc5e81e5b944d37701829dda662053c6103935e43a60e6  repo/results/012/implementation-review/analytic-check.json
90624c9ab3a9be158be8c04376341d27ba0d15e1b0bb779f8212e4992454f61e  repo/results/012/implementation-review/analytic_check.py
afdb34c7858e3e3050333d6235232e28930280ca697f3cc3ed833c7e3b66c9c9  repo/results/012/implementation-review/canonical-tests.log
e7c4bdc1ec21d0cef85c5e10245b07674d9911dac2b20a07d107db51dcd4922a  repo/results/012/implementation-review/detector-regeneration-serialized.json
de58c65747326b60142807e0b953049625a736c76dedee0c925655e25cce12eb  repo/results/012/implementation-review/detector-regeneration.json
7bf41138c5525d11516c4a0609cd635c9e0093843efacb754fb4acd09bbcd566  repo/results/012/implementation-review/event_study.py
71ca314d914e0757bdc156a84706553d03e3bc13beea99eb6c7372c009c7f2c3  repo/results/012/implementation-review/history/extraction-r1.json
0efa5cdc0f9d1f91e36dd8e32348a94a3d72b4e57322a30f20d8040d88ca66af  repo/results/012/implementation-review/history/generated-reproduction-r1.json
8bebb5c085ede6aa7255d6fa43188a4beacc2f73391acf341a666f03a7d3fbce  repo/results/012/implementation-review/history/native-replay-r1.json
e22a4afdb5bd1f6f313a14ed34b2a07d8a3a4ef0ed5e48f4ee7e1d7bf7a684a0  repo/results/012/implementation-review/history/native-replay-r2.json
8f316918c467ac5b24aa5ca8103f256d32362dcfda57355d036f9b0fa0e29ff5  repo/results/012/implementation-review/history/native-replay-r2.log
0410b3a07f61f216126285a2690c5ecf0c1f51081d50370b0547ee2f61cd92fe  repo/results/012/implementation-review/history/run_transition_replay_r2.py
1ed73399dafc3a859860406bf6ea73298432435aa3311828c0754bfa455be6c8  repo/results/012/implementation-review/history/stage-review-r2-manifest.json
f3685d6733a53136883cd8830b063a2a48cddc15532cfa0311b0d1a6f35acfb1  repo/results/012/implementation-review/independent-numerical-check.json
1a6626abc537ddb77afd3af6ba21801defffd4ab637490596dae6d2069a4bdc9  repo/results/012/implementation-review/regenerate_samples-pre-serialization-check.py
ee6e93e52ed8ad3057a7900183226203735a2504bd4379d66f585805bd1aee8a  repo/results/012/implementation-review/regenerate_samples.py
05514153410467f52b11c2f2bfd42aa17ba1ff12ba7d2d711b9b3ce3a5eff923  repo/results/012/implementation-review/verify_empirical.py
3ad7c505309e2031a23d18daed73954c3fed9ddf3f543e9917c6d20914b1482f  repo/results/012/protocol-review/ACCEPTANCE.json
a09c6d7e5fa9087ad977e4cc2fb2f421cd1db4568c40500820e484ba2b113cdd  repo/results/012/protocol-review/recheck-r1/FILES.json
5050fb4f2138d69a2fa02b5a2df990f695be32a820e96ea2d501c567ff361384  repo/results/012/protocol-review/recheck-r1/RECHECK.json
1dbeb544d8b0f2e22586a1e42c0c4137385eadfdc5d0d7a84d6e68dd84c5bc79  repo/results/012/protocol-review/recheck-r1/RECHECK.md
4bb172616ac0f3d57f597e82e6d3e996ac131e6be0c3ab935b25b541c90d47d6  repo/results/012/protocol-review/review-r1/FILES.json
062a45fb629a342b53812330617dd101363c223a05261f6b5b841156c8f380ab  repo/results/012/protocol-review/review-r1/REVIEW.json
fbc2a4dbeefb5e106d9a3e87818ea5961c0a2dee6b05c1d7733a0f94386af699  repo/results/012/protocol-review/review-r1/REVIEW.md
eb5992c8448aa5dabca8f0821015a89f1da66aa36ebeea7aa9df148470891742  repo/results/012/release-files.json
ca7bf7bf54770daa794d5c05f24ff014330c8aea79c4b2f9433118aaeda0ca58  repo/results/012/release-independent-review/NATIVE-HANDOFF.json
2cda300b277121a27f281afed590b3ac549e570edaad0e494d46a1677337fd43  repo/results/012/release-independent-review/REVIEW.json
208b2f9dc37d8ffe252ce279bf56f49628772d553d4065e0e9ad36672e398496  repo/results/012/release-independent-review/REVIEW.md
b40c12852b3bb43f9e3332cd9f5e27fec28346416dbf28b81b17bcad3a475ba6  repo/results/012/release-review.json
e542a9baae15e4032c3f4c79b56959d1da84ff99275f452731db378c3f772829  repo/results/012/run-progress.json
88ff8692d94a67f849e8b3537e461ec329f5696ac1df93b5e8a16bf766cddb6f  repo/results/012/summary.json
99f42e7032d8b31b07a3332408c060d1ae33995b0a0279d084a6e2cd71e9a44c  repo/results/corpus-v1/acquisition.json
4e7b37c6315001a011b210d5eab0b6f5a5bf052495345bd3c707bfea66433cd1  repo/results/corpus-v1/calibration.json
980eb529d9d5cfbb28dc07581433b25c99def5346998162ff6a1c05e7bf01627  repo/results/corpus-v1/summary.json
f6e29f6b00c2901d0afbb304473d123327befde5f7b7540ef29e7e07cf2c6d15  repo/results/corpus-v2/summary.json
489ed74ab80c7e469faa0d00805c992af368a51142635ee7eaf849b91742723b  repo/script.js
64b7af17839abe40a6367ee38baab56affa8576afdca2c8fa791bf9a15ea2d3c  repo/scripts/audit_growth.py
f3295b4d8c57b943845a03961ba6b188fbf0f4c438576916dd9c4b5e1812b388  repo/scripts/audit_results.py
bd5037e0382738a1ef5129c0dee804ab645cb666a1c5773dba8644782e413a5a  repo/scripts/extract_event_assets.py
1c402056e03e2376180ed5a7a9c3d788bb3c0dcbfaee36dcd29ee97d01cfc8a6  repo/scripts/freeze_waveform_protocol.py
63c30ad5dbf4a3e042b9d9cf9b6c5a540beaabff23161681ce7f630d9e252aa0  repo/scripts/package_cross_encoder.py
baa130fcf528062afff8ed12147207216b09fb746ba9ec1153e187727e46058f  repo/scripts/package_distributed.py
02b77c2d87f4a8cd35b4b83cc99b7b0fcb78e37b300a815d7bafa2ddb07900c8  repo/scripts/package_event_assets.py
20e37581ea0e4e90f53225f8f6aac4eacab995bb1f27d8767f892d56523c4168  repo/scripts/package_events.py
9fbcfe75d8049f2c636bf9c541b7599600c51e216c7ba744f7b86cbc92ba1c8f  repo/scripts/package_growth.py
c8f1f0faed52ab061439d0fba02ec5fb19e0d2d4f271b7bb8c3c0dcb81337ccd  repo/scripts/package_pretrained.py
cd7c4a4d33a8cc737ac70751aa153cec78288d20b8db611d624012834d29b732  repo/scripts/package_repeated.py
d5e70b221343d85189f7b7043b299fec2a949f6008028baaff55e97bb095ba34  repo/scripts/prepare_validation.py
ff839f9ee20b4a0c2f91692a42d11f437aa339841c0dbc24fe5359b7c926be79  repo/scripts/prepare_waveform_inputs.py
f1d7dba040bbcff229f45f8c3dd95298e270be8de1b5eee608cd2e9ed378f547  repo/scripts/report.py
7a6b2591bd6c25627cda3deccc1aaf53cc608c35cab0bbf6c1955a7b825927de  repo/scripts/report_cross_encoder.py
af6d61d98318112e84c86b96622b8612287aa81e94e6f33d23a0763a95abffcb  repo/scripts/report_distributed.py
c864d59aafaa59cb4f27c674bb8eb87dafa761e7dc4c5a9252149b3a25739f92  repo/scripts/report_events.py
2402389cf7fac47f1f630ccfab023bd1fe39e83c356b833acb91b13300d9ef60  repo/scripts/report_growth.py
e4353ec199243c668ae6af86c8d1d04132ee94424740bd89e3eb5259b835984f  repo/scripts/report_pretrained.py
731dd3bde34beefd85349bbc6961d2712fc11b144003c319d21c10564b00c268  repo/scripts/report_repeated.py
34ef60cb572e1242040a46860de8b7daae60b6bc18d0e0ae37ae411129da022f  repo/scripts/reproduce_cross_encoder.py
7c819c8460537d7afe36746ad342f473d03bf187ddadc4a9d7ccb84b7772ad29  repo/scripts/reproduce_events.py
fd701af01a84ab1db14df7b63ce4c34c8ee7e264f908b737c21af17b63813cbb  repo/scripts/reproduce_validation.py
b59debfc531bcfd7e3fd6388335d9fe1d4e62d1c0d1d77eabac298e9ac208a31  repo/scripts/smoke_cbramod.py
16536a7a0b846ea39e91976efdd9b2b39360b4431f97b3369def9af6070b6201  repo/scripts/validate_waveform_events.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  repo/site/.nojekyll
6344100a8cd3e6e3939368ccce9863ee802ee98466862139fe0c1533b8bfe4a5  repo/site/README.md
742f1e03835da99cd88415cf2599aa651f6455ef39dd2e13ebd6b15ab19010d2  repo/site/cross-encoder.html
785cda56a789ac37cbe020f787de7c1f1c8da77825eead0445e88abf95bc31a9  repo/site/data/congruence.png
d70a8e0ae7163e499a5d55d31561d7680e55c3c0e9089c55eb955c0e7db1dc13  repo/site/data/cross-encoder-summary.png
d41df51751f81f6f7592d5fe74c1923519b8a683f7ac07ac5b55c25cc904665f  repo/site/data/cross-encoder.json
093ac8c28d8d19fee6ab53bc119936e50aa373c3aedac723d4f37e2cac686dc9  repo/site/data/distributed-summary.png
73e712c1914071593480fc5a97b86b68ece8a159f1cdffe34d03fd3f30f13f28  repo/site/data/distributed.json
361108b9cbaae7415369a8344f425a187470babc21a291b43dae69be380f1c34  repo/site/data/events-summary.png
34696db66fbf5c6a2927e95b4d4023323d2ad2e0046c9ae41cd47b748d09da8d  repo/site/data/events.json
f61c6fc17b05930c0b732b2eed4994f039f8bd11e8587008edab86d42c3bfdca  repo/site/data/experiment-001.json
bb441885c272b23a1bbd505075db575af096f06829107df5f689b2957be31df7  repo/site/data/experiment-002.json
9794ccaae85f9944ca66c78160140352705a30dd08af9cc0730e37cc4a1631ec  repo/site/data/growth.json
c895d700770929e5d8a82be9f48399facbed04c2777e14d3c51a3d471b28f824  repo/site/data/pretrained-eligibility.png
bcc8d4e12f048adcad11505f15151b909c0c662f43ec838aac594dfd9587701e  repo/site/data/pretrained.json
6321b09899edb38c0a1ab740ba58dc21c33fe68d60774899c26c2c43a8a51f63  repo/site/data/repeated-sessions.json
f73b38209121e23f3c0c9de7c390d95dd9bf8ab3d807b401102e26a3363a6369  repo/site/data/session-distances.png
a4923b27a42dcf1b8f149b5c59e0278d74140cc5a3e26d92c6c14e10108b4152  repo/site/data/transition-agreement.png
30c95bff07c4e2dd8d4157adc2ab6348cc84c5072f9a5a1f3bcbf0d2b9b8f733  repo/site/distributed.html
e55adc9ad1ac993c1ac5c66420f8052e1e79ad6b2390c93a720cbc8c99974c35  repo/site/events.html
8c230b2e0028d75ed23125d898c7a4a78fe43877d7740c017aa41ab01d7f5bde  repo/site/favicon.svg
cf9bc3d59e32dd1b88a014d0252be3c07cbde17a062fd4c5adee1fa2e569ec93  repo/site/growth.html
2dc552d264a1ccdd3135ead4eb14af86b95171db5d31e59b2866f6e5caec2b5e  repo/site/index.html
ff7b27c9d95895d6f446e8d8b52179b5371f5f24d11bfb7987a95f362b7ab66b  repo/site/pretrained.html
7e531543c4d2e45df38ac89f4398db48bd79354386f337601642b38f6bbe6bea  repo/site/repeated-sessions.html
489ed74ab80c7e469faa0d00805c992af368a51142635ee7eaf849b91742723b  repo/site/script.js
e5c9d68f01daadae9d58fc49237eacd7bf26e8d0772412a5e0539f58fd5a0fe1  repo/site/styles.css
e5c9d68f01daadae9d58fc49237eacd7bf26e8d0772412a5e0539f58fd5a0fe1  repo/styles.css
323c75faab14845dbb678941ebbbc71015c8028ad631a2f0f6f508292d46614b  repo/tests/test_artifacts.py
cd723b03e7e4a165a50ec635a9c2e119783e94b1bc6fac99c543b57824e58c28  repo/tests/test_cbramod.py
a2df5095fe785d33def6b36280dbf9ea052a2dfb79eb0cddd8dfecb095c451f0  repo/tests/test_contract.py
c321cc426ff8efb070d7c94bb874c3e8fcf3e236b5816f0230d0acd58e947c3e  repo/tests/test_corpus.py
cefab36ff92b01da3a7cef009badc56669fd4240daf35e8b8ae18edf6e26c4d7  repo/tests/test_cross_encoder_study.py
cf0c518761bd80d43377daf708c9dbea18c308aa3dbf93471b6e5bfd3acc9810  repo/tests/test_distributed_study.py
7c19abc134263f1ec1eea4561d9b30edff834e915329465389cff8d1c0acb709  repo/tests/test_event_study.py
1c1e9065cdb68e76dafab4865a5fb08d58243996091b5ec1bff607e6ec2e903f  repo/tests/test_extract_event_assets.py
e9643a671d39501b71f7b546e4e782b35fb0a427d845d1ac531bb955e112fe4d  repo/tests/test_growth.py
f4d102be697be8dfade1b645fc38909fa86c906f5c05510fb068ffd960acad08  repo/tests/test_package_cross_encoder.py
6ec8e4bc9b45edda2102bc40d4348741aee8d4b2ff7eb3626e7f7c76b30faa42  repo/tests/test_package_event_assets.py
308c531ccd527cbc208237625fe031e4e074e29299c96b23e6418069d0d9366d  repo/tests/test_package_events.py
9d0440ea5955d933f6e682b653d0b67b1022b56b505cbc74fb41d1a078a47034  repo/tests/test_package_pretrained.py
1582ad2c2ed19835bd02b3ed3270223e63a2d5bf1dcf5ccc722cb63bab86f405  repo/tests/test_pretrained.py
8f7aab1d57b11e5a177c4a748691426a77c7aceb884870968b8a8a7dfd716f18  repo/tests/test_pretrained_study.py
590e740eb6e0d5fdf1274e6822c4d5d285167d6e33106ed16d0cc40687d17d9d  repo/tests/test_repeated.py
941684aad73da7e5450102b4bd01f3b0754c680e3a467700127538905be07958  repo/tests/test_report_events.py
f0ce0f31fecb3b8500b24a5b44d6b1bd888476f6531f9661f7e99979bd701ae6  repo/tests/test_signal.py
118a9f3de5e3eb5cc38a5f52a07c3a9ff28f96f6483a184b386f994cf4b3ab82  repo/tests/test_transitions.py
f769617d9524306be2cc1e914b4bb466754cda3d17c1f1abf78474d813dbf395  repo/tests/test_validation_engineering.py
6280547db9c55a7b1614c24cd671e1ad90f0d9207e88690f45fbcb9a1b9fe902  repo/tests/test_validation_intake.py
6dce75554364e5dd149bd154508a649f624bcd8027d01cfbe0fb28f7bc82ba6c  repo/tests/test_validation_intake_resources.py
02b80dc0d0fe3bca004cddcef21b4036e581f7f18e792d3e74b65fa9507d7ab7  repo/tests/test_validation_ledger.py
b0dd38f2b16161339d5589a328426b48cca43816ee9539619620ceb8c50adbf9  repo/tests/test_validation_provenance.py
a61d95a0c35b7360f48fed2a238c975d7d4b484228fec34aef2ab8d2499954f5  repo/tests/test_validation_study.py
d0f73553906db2380203d5eaf21ee41751d90425b7613de69005a9c07dc96c2d  repo/tests/test_waveform_events.py
ef832eb6a22fba331909f25c1ef07a49cabeaa519c6582cd488ec1704109d9ce  supplement-exposed012/MANIFEST.json
75765b2aecc989d14a33bcb8c4ead8617eb1ac662eccfb4068412a7bac0cc480  supplement-exposed012/analysis.sqlite.gz
0423b46177767e36d52232dd74f9f035509b5d63900fb610d31e7f60887d871b  supplement-exposed012/native-selected-curator.json
0c93bb6f4b09c96cb2c491f56d9cfe4f3a691ae464bf6fb9e0fc102a19a0214e  supplement-exposed012/row-000/native-add_50hz.jsonl.gz
797139227832333ecd8b7722801daaa91f6a6155348bc1cf33266a7b618072a8  supplement-exposed012/row-000/native-add_60hz.jsonl.gz
ce07673be4c460965d038e5fa8313b1d3328bc88c29dc5c0125a900a7ee04a33  supplement-exposed012/row-000/native-additive_offset_50uv.jsonl.gz
c2bad28083e4ac4aa902387e3b1ed5a85f4a6a465f138b2c41295f75be74cded  supplement-exposed012/row-000/native-common_mean_reference.jsonl.gz
8b223fdce4de9a7b394855d31e7ab12c9fb39e8f7323e6d4e1ecb498968078f5  supplement-exposed012/row-000/native-gain_x2.jsonl.gz
33540b4fdb49a57e9e18db2e79b33b5b120908c557d1abc8b6ac17c830cd5cf6  supplement-exposed012/row-000/native-independent_phase.jsonl.gz
36b233dacad2b0041aa089405d27f6a244ea0af5fca1400dd8da17f80b1447a6  supplement-exposed012/row-000/native-notch_50hz.jsonl.gz
b8567562b79a40c3ca674d6f048da07ad1aa70135af7ddebdae3dfbdbf41d9ef  supplement-exposed012/row-000/native-notch_60hz.jsonl.gz
b115c8effef15060065a97afae647f666226cac6a38da18d228a9f5dddc91f76  supplement-exposed012/row-000/native-passband_0p5_40.jsonl.gz
51e65b22ef0c1f30e3b05276e44554314096e139fa80d7787a6dc667738961e8  supplement-exposed012/row-000/native-passband_1_30.jsonl.gz
2ce2ac77f63245c388f9ce13ffc925f149cda37609b0dc6bc56002a354d2820b  supplement-exposed012/row-000/native-polarity_xneg1.jsonl.gz
7fa8ca0a25640c95255055a5902e8343fd496c1041c076e10b36422111a7d65b  supplement-exposed012/row-000/native-primary.jsonl.gz
610634aa91030015769d8e718d868f2a3d61138017c21369a098539f36783fd9  supplement-exposed012/row-000/native-shared_phase.jsonl.gz
c9a63d75d6db050817eac32a35c051c84409df25d584bdfa1cdd9103a09b44ae  supplement-exposed012/row-000/native-shift_plus_200ms.jsonl.gz
c3059a9a7eecdc0a50d9e8c21490bfe3a4a96351ffc7d00cd441d3df3a905e8d  supplement-exposed012/row-000/native-smoothing_21ms.jsonl.gz
4e365ef90316b5ee7beda7495f8a42bc123bc8910943d4b037660c1a102c6541  supplement-exposed012/row-000/native-smoothing_51ms.jsonl.gz
567a90810249218e57a18d96c34ee472faa06c1e0b7d2961ca2ce2958feba323  supplement-exposed012/row-000/native-spike_100uv_8ms.jsonl.gz
714631a6647d88c4680e3768de524d0ac3bc794f8400f1d8525aeb914eda5865  supplement-exposed012/row-000/native-symmetric_clipping_50uv.jsonl.gz
34aa09184763f142ae3b107ed0168feb1ab5c940164d4640c6e74b2f2075d330  supplement-exposed012/row-000/prepared-channel_reverse.jsonl.gz
36d6d97d7a52f21fdcdefb079226f70becd0044f1eb06a13e1e1afdce1b459fb  supplement-exposed012/row-000/prepared-gain_half.jsonl.gz
84917ad8aca33b1ed363fa1b2cf5858c7089ce731cda8d7393d067f07ec483a6  supplement-exposed012/row-000/prepared-independent_phase.jsonl.gz
7c0b7f8062147bd72e7c5e7a4375ec842cf97de7aaa438f6430beb1b808bf433  supplement-exposed012/row-000/prepared-original.jsonl.gz
be7f99b4a7578f6b9f7d328a824a7e9ff138ad645287a2e2325f58242110d244  supplement-exposed012/row-000/prepared-polarity_flip.jsonl.gz
```

### Additive packet hashes

```text
6921d4850bfa1a0010f1442edfe8ef3ebd256bf5221dbf04c2218ff983920995  update-final-analysis/UPDATE-MANIFEST.json
ae0ed921bfa64301d2fe85e995970b1c649a1db10c6f88f28aa8dc6d940415d6  update-final-analysis/evidence/analysis/JEV-WORK.json
8d024d6e02ea24f019ee9bbd6e0f65b69d220acdf1056f0ae53dcf4d0bb42211  update-final-analysis/evidence/analysis/REPORT.json
0f332c4c83941c7b0478f2cead2126947711ea365e6f9d9805ff60656d21e87d  update-final-analysis/evidence/analysis/REPORT.md
9f13e12380b5306a8a38593a858cc0f8f790d60a222d21b352065c4a976ca8df  update-final-analysis/evidence/analysis/exposed-parity-final.log
0c53565d3e2c18a280072eb0a8f6fec66915acb5bd1bd7c7a8112c5a61de188d  update-final-analysis/evidence/analysis/owned-source-sha256.log
736e62a4e145e43626ff800954f73c4eefefc9cb40f3b867e59a1798f65458cd  update-final-analysis/evidence/analysis/preflight-final.log
9a8b2f44c391114e774733052fa6a7456988faef142bdeb6b79d7d548ac24e03  update-final-analysis/evidence/analysis/pycompile-final.log
a1b607fbfe0a6f9e5729b071a1a7e6a94ba2a36e548eb9c2a69aacdc0bf64301  update-final-analysis/evidence/analysis/resource-snapshot.log
f15bc332da4dac34b81dcd6283bc2326cf511c7d126572cf44143e9b0a255776  update-final-analysis/evidence/analysis/source-hash-audit.log
cb14d228660b74c4178621cdd27c4525ae436ee104769889a67a9f6690d2a385  update-final-analysis/evidence/analysis/test-validation-events.log
5ff15f29f948b01fb67b06a6a0232a6e6de71089571937aa80112883f1c15560  update-final-analysis/evidence/analysis/test-validation-focused.log
9ab7932751acf3058309c89305f6bdac8f4f0c80c2dddcfdb2638b67eef492ac  update-final-analysis/evidence/analysis/test-validation-study-final.log
65ef547d0fedac7c1c76ab879d289f3aedb6acb62e8bb1bf384c6be04e437fad  update-final-analysis/evidence/analysis/test-validation-study.log
3266ec0a8d933b03c6cb8aecc4ddee79bb2c5b35f0ae87984abe085e8beab340  update-final-analysis/repo/eegt/validation_study.py
fd701af01a84ab1db14df7b63ce4c34c8ee7e264f908b737c21af17b63813cbb  update-final-analysis/repo/scripts/reproduce_validation.py
122f031a2b4c0863df840efb7e7315fd8c281c586809425ab814af4141fc2c72  update-final-analysis/repo/tests/test_validation_study.py
956a0cac49e7a13b84e3ad74efbb9ae0861aa909c4033c9a3d87a232f992747f  update-root-r3/MANIFEST.json
76051cca7249eb91aa622347f17974452aaa176b516b170fadf51cca6239e126  update-root-r3/eegt/validation_intake.py
e3a16c6bebbba696eeab10aa3953536e9a5478476142066514aa233e2455b4b5  update-root-r3/eegt/validation_study.py
680b442a3d3cb556748c541e3f50ab8711164b95ef6deff170e1d12c1c5bf9f9  update-root-r3/protocol/experiment-013.json
22d666642b3c7539031f72421cb8a7afce0a5f94f06fa1261a7046f91555fa7e  update-root-r3/tests/test_validation_intake.py
c2ff8ab16a8ee929211e2eb647fd4ac10b9d731d063488590880d92226a0b62f  update-root-r3/tests/test_validation_intake_resources.py
9389e64a8597281542821e13659c3e30f2a75759da8e950a9e15f5bd77586e3e  update-root-r3/tests/test_validation_ledger.py
83c13be9dd3c6b1fa3917d283f5ed91c0b4fecea8120b9d082221b2319e1d1e2  update-root-r3/ROOT-INTAKE-r3.log  [unbound worker log]
c32789aa63bfb3d7dc1d8a1e936adc4827f28bc6d5921946461748126c171780  update-root-r3/ROOT-REGRESSION-r2.log  [unbound worker log]
1280907b0cb5b3ddfaa72397639575523b97b2423f67bb9f6a44d54773c94d04  update-root-r4/MANIFEST.json
93d4769d8d1653f26ed4c64bfaf312083f1e0511a47fb830c4319d2a5326fe17  update-root-r4/protocol/engineering-input-013.json
7b6bb33a3a64cc98bf69bdf96980f278be3a9c45c0439ec46c24998ee51bbfce  update-root-r5/MANIFEST.json
15a808eb7dd5ccf8dbccf9d0cdef9296e43755c52b17bbb84a4bf872e6fa6a1f  update-root-r5/eegt/validation_study.py
02b80dc0d0fe3bca004cddcef21b4036e581f7f18e792d3e74b65fa9507d7ab7  update-root-r5/tests/test_validation_ledger.py
a01c5353ef50d00e73fe49e34a488b82448c028599cdd422fdf2a71a62cda928  update-root-r5/ROOT-REGRESSION-r5.log  [unbound worker log]
eb0304ce4045d33bba6e3aa6d7a9fc1d2b77b24f47cb63c50aa9f4a5d67fda5d  update-root-r6/MANIFEST.json
c773b4159d907783df945e1e1e934efbddf8fd4e2bd851066e9172da65496761  update-root-r6/eegt/validation_intake.py
e6f7282134786a7f85b07226a7afa6e05faa4dfb0dc7e52a6345c8e131481a7d  update-root-r6/eegt/validation_provenance.py
31568d7d54fd363bc0030bf28af999f6757ba02d45cd0dd13bbb7060aa97cdec  update-root-r6/eegt/validation_study.py
6280547db9c55a7b1614c24cd671e1ad90f0d9207e88690f45fbcb9a1b9fe902  update-root-r6/tests/test_validation_intake.py
6dce75554364e5dd149bd154508a649f624bcd8027d01cfbe0fb28f7bc82ba6c  update-root-r6/tests/test_validation_intake_resources.py
a3efc2ef104530b1b88f82e551fc124f563f51cc4fbbef4706019b7d222ae3d3  update-root-r6/tests/test_validation_provenance.py
a61d95a0c35b7360f48fed2a238c975d7d4b484228fec34aef2ab8d2499954f5  update-root-r6/tests/test_validation_study.py
4125c1ac9030529abe1b158211f581b7d5a573529d23643c9070df9262742ca6  update-root-r6/ROOT-INTAKE-r6.log  [unbound worker log]
3760161569822a45595b3ab00a4dbaa10202771a0855a9c520a2cf8d4880448d  update-root-r6/ROOT-INTAKE-r6b.log  [unbound worker log]
fce1ad61ab7db6c8300670b99cdfe50499890bd4a9973398fba1d2109561d0c1  update-root-r6/ROOT-REGRESSION-r6.log  [unbound worker log]
4b18145adf9696b2ea3d13bda9b9c226131b2822b34b194a14a0f512bd5460df  update-root-r6/ROOT-SYNTHETIC-r6.log  [unbound worker log]
db7ac2799fe989e06e4ec83eb707658062acfe0123d554c33173287e15f6618d  update-root-r7/MANIFEST.json
fa405fba4a1aea3ba21dc5ff520a7000a588f5d8998f66e06d0e5bc33ee23e97  update-root-r7/eegt/validation_provenance.py
b0dd38f2b16161339d5589a328426b48cca43816ee9539619620ceb8c50adbf9  update-root-r7/tests/test_validation_provenance.py
c72e44c040f8a7fd1f389a4bb304b4db8855a6e2908a711c7641c0b17198ab9a  update-root-r7/ROOT-PROVENANCE-r7.log  [unbound worker log]
a2a0a988170c8697d85b602b038b970de01aa0b76745ef5528973fc3ab46d901  MODEL-CACHE-REUSE.json
4ee1308fe0481834dc3c11b15db6a274394099fbaeb4689b3a69ef41dac3e762  RUN-SOURCE-MANIFEST-DRAFT.json
```

Root owns the later execution seal, empirical admission and release verification. This review applies only to the hashes above.
