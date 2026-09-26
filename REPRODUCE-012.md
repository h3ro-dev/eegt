# Reproduce Experiment 012

Download **all** `eegt-v0.8.0-data-part-*.tar.gz` assets, the release manifest and its SHA256SUMS file from the v0.8.0 release. Each shard is below GitHub's individual asset limit. The shards are parts of one complete dataset, not alternative samples.

Verify the downloaded assets, then extract every shard into the same new directory:

```sh
shasum -a 256 -c eegt-v0.8.0-data-SHA256SUMS.txt
mkdir extracted
for asset in eegt-v0.8.0-data-part-*.tar.gz; do
  tar -xzf "$asset" -C extracted
done
cd extracted
```

The captured layout contains `repo/`, `input/`, `out/`, `SOURCE-MANIFEST.json`, the storage authorization, and a complete `FILE-MANIFEST.json`. Each shard carries the same complete file manifest; extraction repeats that identical file. Preserve the layout. The package includes the selected numerical EEG windows, masks, both models' archived vectors, all event candidates and rejections, the SQLite index, frozen methods, exact source and review evidence. Full original recordings and model weights remain upstream.

Check every extracted file before installing or executing anything:

```sh
python3 - <<'PY'
import hashlib, json
from pathlib import Path
files = json.loads(Path('FILE-MANIFEST.json').read_text())['files']
for name, row in files.items():
    path = Path(name)
    assert path.is_file() and path.stat().st_size == row['bytes'], name
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1048576), b''):
            h.update(block)
    assert h.hexdigest() == row['sha256'], name
print('Verified', len(files), 'extracted files')
PY
```

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

