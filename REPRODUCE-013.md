# Reproduce Experiment 013

Release candidate: extraction and morphology checks passed; complete replay, final independent output acceptance and public readback are pending. Do not treat this document as a published release receipt.

The v0.9.0 captured dataset is designed for exact replay of the recorded event ledger. It contains the frozen scientific source and protocol, all 9,600 candidate receipts, selected numeric inputs, both encoders' archived outputs, complete event partitions, the SQLite index, resource admissions and preserved failed attempts. Replay recomputes comparisons and the eight-endpoint scientific summary; it does not regenerate detector outputs or run neural inference.

Download every `eegt-v0.9.0-data-part-*.tar.gz` asset, the manifest and SHA256SUMS. Check the asset hashes, then run the separately verified `scripts/extract_event_assets.py` from the versioned source:

```sh
shasum -a 256 -c eegt-v0.9.0-data-SHA256SUMS.txt
python3 extract_event_assets.py --manifest eegt-v0.9.0-data-manifest.json --destination extracted --receipt extraction.json eegt-v0.9.0-data-part-*.tar.gz
```

Before executing the extractor, verify its SHA256 against the manifest entry `repo/scripts/extract_event_assets.py`. The extractor requires a new destination and checks the exact asset/member inventories, sizes, SHA256 values and paths. Preserve a failed partial extraction and investigate it before trying a new directory.

Two pinned upstream checkpoint files are external dependencies of the unchanged freeze verifier, even for ledger replay. Their precise paths, bytes and SHA256 values appear under `external_dependencies` in the release manifest and in `repo/results/013/RUN-SOURCE-MANIFEST.json`. Obtain the exact checkpoint revisions from the CodeBrain and CBraMod upstream sources documented in the model/protocol records, verify their hashes, and place them at the declared paths beneath `extracted/repo`. The pinned files are [CodeBrain](https://huggingface.co/YjMajy/CodeBrain/blob/bef08d2fdb1759685371cc635aad21ce59163689/CodeBrain.pth) and [CBraMod](https://huggingface.co/weighting666/CBraMod/blob/500543c7e30bda1b22bfd51a49301b238dee21fd/pretrained_weights.pth). They are checked but no model forward is invoked by replay. The archive does not redistribute the full raw recordings or those checkpoint files.

From `extracted`, fetch those exact revisions and verify them before replay:

```sh
mkdir -p repo/data/cache/models
curl -fL https://huggingface.co/YjMajy/CodeBrain/resolve/bef08d2fdb1759685371cc635aad21ce59163689/CodeBrain.pth -o repo/data/cache/models/codebrain.pth
curl -fL https://huggingface.co/weighting666/CBraMod/resolve/500543c7e30bda1b22bfd51a49301b238dee21fd/pretrained_weights.pth -o repo/data/cache/models/cbramod.pth
shasum -a 256 repo/data/cache/models/codebrain.pth repo/data/cache/models/cbramod.pth
```

The expected SHA256 values, respectively, are `d9714b8732c9883a04d022ee66254cd578ae1fa27f5458e6ab7f1aa96e9a7352` and `0792cb808c14e6b7a2bb2ce1dff379bc47bc54c49a779825bdfeb33bf8157178`. Stop if either differs; the replay verifier also enforces these hashes.


Use the frozen events runtime: Python 3.12.14, NumPy 1.26.4, SciPy 1.14.1, bycycle 1.2.0 and NeuroDSP 2.3.0. The requirements file records the event packages; the freeze records the actual runtime contract. The original frozen runner reached its CPU ceiling during independent replay without producing a complete receipt. Its failure and resource log are retained under `results/013/replay-original-failure.*`. The additive verification adapter passed independent source review and 14 focused tests; its first full corrected replay is in progress. It calls the unchanged frozen replay and numerical functions, decodes each payload once, and requires a complete final inventory and compressed-byte rehash. The original limits remain unchanged. This engineering correction does not establish successful reproduction until its full receipt is accepted.

The immutable data archive retains the earlier candidate instructions. Use the adapter and these instructions from the versioned source checkout as a separate companion to that captured data. Its exact reviewed SHA256 is `e12c6e64d0a5d670f24c5d7c37e8a71ccfbc1abf8bacce9dfd4fe01a7b286591`. From the source checkout, in an environment with those exact versions, substitute the actual absolute extraction path:

```sh
PYTHONDONTWRITEBYTECODE=1 python scripts/replay_validation_bounded.py --root /absolute/path/extracted/repo > replay.json
python scripts/verify_validation_release.py check-replay --root /absolute/path/extracted/repo --replay replay.json
python scripts/verify_validation_release.py morphology --root /absolute/path/extracted/repo > morphology-replay.json
```

Keep output receipts outside the captured input inventory. The runner sets all five numerical thread controls to one and rejects changed source, runtime, checkpoint, numeric archive and event-partition bindings. A complete successful receipt must have `status=REPLAYED_RECORDED_EVENTS`, `full_scientific_summary=true`, `completed_blocks=174` and `partitions=4002`, plus the exact run-manifest and input-acceptance hashes. Status or exit code alone is insufficient: the unchanged replay routine can return its replay status for a partial ledger. The release additionally checks all morphology rows against the archived native-primary partitions, because that comparison is outside the frozen replay routine. Retain this stdout receipt outside the captured input inventory. Do not edit the manifest or lower checks to make a mismatch pass.

Fresh raw-data preparation, encoder inference and detector regeneration are separate operations. Preserve the original artifacts, use the exact frozen sources and scientific rules, and follow the first-record/block admission gates and resource ceilings. They are not needed for recorded-ledger replay. Upstream model-pretraining overlap, physiological calibration and equivalence to physical Neurable hardware remain unknown.

The new-session and new-person cohorts remain separate. The new-person cohort fails the frozen complete-participant minimum; its missing primary results must remain missing. A numeric agreement between encoders, or a recurring waveform event, does not establish semantic meaning, a universal EEG vocabulary or a clinical diagnostic.
