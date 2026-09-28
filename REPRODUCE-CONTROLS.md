# Offline reproduction of the conditional timing-control supplement

This packet reproduces the fixed exploratory twelve-block follow-up to Experiment 012 and the metadata-only EESM19 capacity audit. It needs no model call, detector run, waveform download or reserved/private recording. Replaying these exposed inputs is a reproducibility check, not an independent-person replication.

Download `eegt-v0.11.0-controls.tar.gz`, the file manifest, SHA256 checksums and independent release review from the [v0.11.0 release](https://github.com/h3ro-dev/eegt/releases/tag/v0.11.0). Verify the downloaded archive against its checksum before extraction. The public Git repository provides browsable receipts and notes; the archive supplies the complete relative path layout and required input files.

```sh
shasum -a 256 eegt-v0.11.0-controls.tar.gz
tar -xzf eegt-v0.11.0-controls.tar.gz
cd packet
```

Compare the printed checksum with the archive line in the downloaded checksum file. Extract each rerun into a fresh directory. Original stage receipts are immutable; the adapter refuses to overwrite its earlier replay outputs.

Use **Python 3.12.12, NumPy 2.5.3 and SciPy 1.18.1** on a POSIX runtime with `resource.RLIMIT_CPU` and `SIGXCPU`. The adapter checks exact Python/NumPy/SciPy versions. A compatible existing environment is sufficient; dependency pins are in `work/next-study/release/requirements-replay.txt`, including Matplotlib 3.11.2 for optional regeneration of the supplied figure. Source SQLite files are copied byte-for-byte and opened read-only.

Run from the extracted packet root, one process at a time:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
python work/next-study/release/replay_adapter.py verify
python work/next-study/release/replay_adapter.py metadata
python work/next-study/release/replay_adapter.py empirical
```

`verify` checks the explicit file allowlist and all frozen source/acceptance seals. `metadata` runs the unchanged capacity audit, redirecting only its output directory, and compares the resulting `CAPACITY.json` byte-for-byte with the accepted original. It reads metadata and the public catalog only.

`empirical` maps the original absolute provenance paths into the packet layout, imports the unchanged frozen runner and calls its unchanged `evaluate_row` for the twelve predetermined rows. It verifies all 99 timing draws at each of the three tolerances, all original accepted event-count/F1 receipts, and the person-level descriptive summary. The new receipts are written under `work/next-study/release/replay/`; the original `FIRST-UNIT.json`, `REMAINING.json`, protocol and source data are preserved. A successful numerical receipt has status `COMPLETE_MATCH`. Any mismatch, resource stop or incomplete row is a failure, not a partial replication success.

The empirical CPU hard limit is 7,200 seconds, with an earlier signal and between-draw guard. RSS is checked against 2 GiB between calls and after rows; an individual matcher call can temporarily cross a polling threshold before the guard runs. The original study used 201.260463 total CPU seconds across two sequential stages and peaked at 467,894,272 bytes RSS. These are observed measurements, not universal hardware requirements.

The archive includes only the 24 selected event partitions, while its unchanged full accepted 012 SQLite index and prior summary retain the broader historical receipts. The other 110 blocks receive no new timing-control analysis. Public source identifiers remain provenance/evaluation metadata; no identity, history, task or semantic labels enter numerical discovery. The packet excludes raw waveform arrays, model checkpoints, private EEG/media and vendor correspondence.

Historical draft/pending labels inside frozen artifacts are deliberate. Later [protocol acceptance](results/controls-012/empirical-review/PROTOCOL-ACCEPTANCE.json), [scientific output acceptance](results/controls-012/empirical-review/OUTPUT-REVIEW.json) and the release review establish their subsequent state. The separate relocation adapter changes file lookup/output placement only; it does not alter the original scientific choices or code.

See the [research note](notes/conditional-timing-012.md) for estimands, people/session/time/event denominators and limitations. A positive raw-minus-null difference does not establish neural origin: this timing null also removes fine spacing and waveform constraints. EESM19 candidate capacity remains unqualified metadata, and adequate power has not been established.
