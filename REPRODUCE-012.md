# Reproduce Experiment 012

Download **all** `eegt-v0.8.0-data-part-*.tar.gz` assets, the release manifest and its SHA256SUMS file from the v0.8.0 release. Each shard is below GitHub's individual asset limit. The shards are parts of one complete dataset, not alternative samples.

Verify the downloaded assets against the checksum file from the trusted release page. Fetch the versioned extractor, then verify its bytes against the release manifest before running it:

```sh
shasum -a 256 -c eegt-v0.8.0-data-SHA256SUMS.txt
curl -fL https://raw.githubusercontent.com/h3ro-dev/eegt/v0.8.0/scripts/extract_event_assets.py -o extract_event_assets.py
python3 - <<'PYCODE'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('eegt-v0.8.0-data-manifest.json').read_text())
expected = manifest['files']['repo/scripts/extract_event_assets.py']['sha256']
if hashlib.sha256(Path('extract_event_assets.py').read_bytes()).hexdigest() != expected:
    raise SystemExit('Extractor checksum mismatch')
PYCODE
python3 extract_event_assets.py --manifest eegt-v0.8.0-data-manifest.json --destination extracted --receipt extraction.json eegt-v0.8.0-data-part-*.tar.gz
cd extracted
```

The destination must be new. Before writing files, the extractor checks the exact shard set, each asset's size and hash, every member's canonical path and type, and the advertised member sets. It rejects links, traversal, duplicate and unlisted members. It then verifies each extracted size/hash and the complete output tree. Failed partial extractions are preserved; use a new directory after investigating the cause. The extraction receipt is saved outside the extracted tree.

The captured layout contains `repo/`, `input/`, `out/`, `SOURCE-MANIFEST.json`, the storage authorization and a complete `FILE-MANIFEST.json`. Each shard carries the same complete file manifest; the extractor verifies those copies are identical. Preserve the layout. Selected EEG windows, masks, both models' archived vectors, all event candidates and rejections, the SQLite index, frozen methods, exact source and review evidence are included. Full original recordings and model weights remain upstream.

Use Python 3.12 and the pinned event environment:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r repo/requirements-events.lock
.venv/bin/python repo/scripts/reproduce_events.py preflight
.venv/bin/python repo/scripts/reproduce_events.py reproduce
```

The runner fixes numerical thread counts to one. The offline route does not load model weights, invoke a model or acquire any raw recordings. Internet access is needed only for packages not already available. Source and input hashes, exact NumPy/SciPy/bycycle/NeuroDSP/pandas versions and Python major/minor are checked. Host paths, operating-system labels and Python patch versions are recorded separately; they are not scientific input identities.

`reproduce` verifies all 2,806 event partitions, recomputes every native matching table, prepared-input comparison and the complete participant-level scientific summary, and writes a new timestamped reproduction receipt. It leaves the frozen source, partitions and original summary intact; it adds a readback entry to the copied `out/REPORT.json`. This is a **replay from the archived event ledger**, not regeneration of all detector events from the numerical waves. Expect several minutes of CPU work and temporary process memory; the archive contains several gigabytes of retained evidence.

For a detector rerun, use a separate copy, preserve the existing results and make a new run with the same sealed inputs and source. Do not overwrite published partitions or edit a manifest to admit new bytes. Resource ceilings must be assessed before expanding beyond the mandatory first-block checkpoint. The original first block and storage-only expansion are retained. No new scientific threshold or input selection was introduced by that expansion.

The release's independent checks and their exact scope are recorded in `repo/notes/validation-012.md`. Runtime receipts refer to the measured macOS hosts; resource accounting on an untested platform is not asserted to be identical. A mismatched exact scientific replay is a failure to investigate, not permission to relax its checks.

Read `repo/notes/experiment-012.md` for people, nights, windows, source-hour and event denominators. The full summary and public JSON retain undefined metrics and exclusions. These are numerical wave measurements and two continuous EEG backbones, not a thought decoder, diagnostic test or established universal token language.

