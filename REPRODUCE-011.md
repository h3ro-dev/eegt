# Reproduce Experiment 011

Extract the v0.7.0 data archive into a fresh directory. Its top level contains `input/`, `repo/` and `FILE-MANIFEST.json`. Preserve those paths. The selected numeric EEG arrays and both models' archived outputs are included; full original recordings and model weights remain upstream.

Use Python 3.12 and the pinned encoder environment:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r repo/requirements-encoder.lock
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python repo/scripts/reproduce_cross_encoder.py reproduce --packet-root . --output-dir reproduced
.venv/bin/python repo/scripts/reproduce_cross_encoder.py compare --packet-root . --output-dir reproduced
```

`reproduced` must be a new output location. This command checks source and archive hashes, validates all row identities and variant input/output pairs, and recomputes the comparison without loading a checkpoint or calling a model. Do not edit a receipt to admit different bytes. Original model weights are not needed for this offline route. Internet access is needed only if the pinned packages are not already available.

The comparison checks every nested scientific result within 1e-12. SQLite file headers can vary across SQLite versions; scientific values, table contents, integrity and foreign keys are the acceptance boundary. The original recorded database hash remains in its release manifest.

For the independent numerical check, use the archived review script with explicit paths after installing the same NumPy/SciPy versions:

```sh
.venv/bin/python repo/results/011/implementation-review/verify.py --packet-root . --output independent-check.json
```

The archive preserves the original test file required by the pre-inference source seal. Eight pure synthetic checks need no waveform checkpoint; its optional full preflight check requires the pinned CBraMod checkpoint at `input/pretrained_weights.pth`. The current Git repository's test harness supports `EEGT_011_PACKET=/absolute/captured/packet` and skips this one optional preflight when no packet is provided. Both test versions and the harness-only correction are retained. The actual checkpoint preflight and all nine analysis tests passed during development.

The run manifest was sealed before inference. `repo/results/011/analysis-amendment.json` describes the later integer-serialization and weightless-offline repairs; the original code and failed partial are retained. No scientific metric, input selection or model forward was changed by those repairs. An inference rerun is separate work with its own untouched output directory and pinned upstream checkpoints, not an overwrite of this published experiment.

Read `repo/notes/experiment-011.md` for denominators, negative/inconclusive findings, model/source attribution and limits. Numeric inputs have no identity/history/semantic labels; curator identifiers remain necessary for provenance and participant-level evaluation. These continuous encoders do not decode thoughts or establish universal tokens.
