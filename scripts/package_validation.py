"""Stage, never publish, the captured Experiment013 using the existing archive writer."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(p):
    return json.loads(p.read_text())


def stage(root, output):
    root, output = root.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError('Preserve existing stage: ' + str(output))
    result = root / 'results/013'
    freeze = read(result / 'RUN-SOURCE-MANIFEST.json')
    summary = read(result / 'summary.json')
    prepared = read(result / 'prepared.json')
    engineering = read(result / 'engineering/summary.json')
    if freeze['status'] != 'ACCEPTED' or summary['status'] != 'COMPLETE_NUMERICAL_RECORD':
        raise ValueError('Completed, frozen numerical record required')
    if engineering['status'] != 'COMPLETE_TECHNICAL_RECORD':
        raise ValueError('Engineering record incomplete')
    if len(prepared['records']) != 9600 or len(summary['primary_endpoints']) != 8:
        raise ValueError('Candidate or endpoint family incomplete')
    freeze_sha = digest(result / 'RUN-SOURCE-MANIFEST.json')
    acceptance = read(result/'INPUT-ACCEPTANCE.json')
    if acceptance['status']!='ACCEPTED' or acceptance['run_source_manifest_sha256']!=freeze_sha:
        raise ValueError('Input acceptance is stale')
    for name,expected_sha in acceptance['inputs'].items():
        if digest(root/name)!=expected_sha: raise ValueError('Accepted numeric input changed: '+name)
    if summary['input_acceptance_sha256']!=digest(result/'INPUT-ACCEPTANCE.json'):
        raise ValueError('Summary input acceptance differs')
    protocol=read(root/'protocol/experiment-013.json')
    actual=[(e['cohort'],e['model'],e['metric']) for e in summary['primary_endpoints']]
    expected={(e['cohort'],e['model'],e['metric']) for e in protocol['primary_endpoints']}
    if len(actual)!=8 or len(expected)!=8 or set(actual)!=expected: raise ValueError('Eight endpoint identities differ')
    for model in ('codebrain','cbramod'):
        inference=read(result/f'inference-{model}.json')
        if (inference['status']!='COMPLETE' or inference['encoder_implementation']!='PINNED_CHECKPOINT'
            or inference['run_manifest_sha256']!=freeze_sha
            or inference['input_acceptance_sha256']!=digest(result/'INPUT-ACCEPTANCE.json')
            or inference['prepared_receipt_sha256']!=digest(result/'prepared.json')
            or inference['array_sha256']!=digest(root/inference['array_path'])):
            raise ValueError('Model output acceptance differs: '+model)

    if summary['run_manifest_sha256'] != freeze_sha:
        raise ValueError('Summary/freeze join differs')
    for name, sha in freeze['inputs'].items():
        if digest(root / name) != sha:
            raise ValueError('Frozen source differs: ' + name)
    for review in freeze['accepted_reviews']:
        if review['status'] != 'ACCEPTED' or digest(root / review['path']) != review['sha256']:
            raise ValueError('Independent source review differs')
    selected = {r['candidate_index'] for r in prepared['records'] if r['status'] == 'ELIGIBLE'}
    dbpath = result / 'analysis.sqlite'
    with sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity failed')
        completed = {r[0] for r in db.execute('SELECT candidate_index FROM completed_blocks')}
        if completed != selected or summary['completed_event_blocks'] != len(selected):
            raise ValueError('Selected/completed block identities differ')
        rows = list(db.execute('SELECT candidate_index,branch,variant,path,sha256,bytes FROM partitions'))
        expected = {(ci, branch, variant) for ci in selected for branch, variants in
                    [('native', summary['native_variants']), ('prepared', summary['prepared_variants'])]
                    for variant in variants}
        if {(ci, branch, variant) for ci, branch, variant, _, _, _ in rows} != expected or len(rows) != len(expected):
            raise ValueError('Event partition identity census differs')
        if summary['indexed_partitions'] != len(rows):
            raise ValueError('Summary partition total differs')
        indexed = set()
        for _, _, _, path, sha, size in rows:
            p = root / path
            if p.stat().st_size != size or digest(p) != sha:
                raise ValueError('Event partition bytes differ: ' + path)
            indexed.add(path)
        actual = {p.relative_to(root).as_posix() for p in (root/'data/derived/013/events').rglob('*') if p.is_file()}
        if actual != indexed:
            raise ValueError('Extra or missing event partition files')
    mapping = {}
    def add(p):
        name = p.relative_to(root).as_posix()
        if p.is_symlink() or '__pycache__' in p.parts or p.name.endswith(('.partial', '-wal', '-shm', '-journal')):
            raise ValueError('Unsafe or unfinished release file: ' + name)
        mapping['repo/' + name] = name
    for name in freeze['inputs']:
        add(root/name)
    for review in freeze['accepted_reviews']:
        add(root/review['path'])
    for folder in ['eegt', 'results/013', 'data/derived/013']:
        for p in sorted((root/folder).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                add(p)
    for name in ['scripts/reproduce_validation.py', 'scripts/prepare_validation.py',
                 'scripts/package_event_assets.py', 'scripts/extract_event_assets.py',
                 'scripts/package_validation.py', 'scripts/report_validation.py', 'scripts/verify_validation_release.py',
                 'requirements-events.lock', 'REPRODUCE-013.md', 'notes/experiment-013.md',
                 'validation.html', 'data/validation.json', 'styles.css',
                 'site/validation.html', 'site/data/validation.json', 'site/styles.css']:
        add(root/name)
    # The unchanged freeze verifier hashes these upstream weights even during ledger replay.
    # They remain separately supplied dependencies, never silently omitted from the contract.
    external = {}
    for model, info in freeze['models'].items():
        ref = info['checkpoint']; p = root/ref['path']
        if digest(p) != ref['sha256']:
            raise ValueError('Upstream checkpoint changed')
        external[model] = dict(path=ref['path'], sha256=ref['sha256'], bytes=p.stat().st_size,
                               purpose='Verifier dependency; replay performs no model forward')
        for name, sha in info['vendor_sources'].items():
            if digest(root/name) != sha:
                raise ValueError('Vendor source differs')
            add(root/name)
    sys.path.insert(0, str(root/'scripts'))
    from package_event_assets import inventory, write_assets
    files = inventory(root, mapping)
    manifest = write_assets(root, mapping, output, 'eegt-v0.9.0-data', expected_files=files)
    manifest.update(state='CANDIDATE_NOT_ACCEPTED', run_manifest_sha256=freeze_sha,
                    summary_sha256=digest(result/'summary.json'), morphology_rows=summary['morphology_rows'], external_dependencies=external,
                    acceptance='Independent output review and extracted replay required before publication')
    target = output/'eegt-v0.9.0-data-manifest.json'
    target.write_text(json.dumps(manifest, sort_keys=True, indent=2)+'\n')
    checks = {name: row['sha256'] for name,row in manifest['assets'].items()}
    checks[target.name] = digest(target)
    (output/'eegt-v0.9.0-data-SHA256SUMS.txt').write_text(''.join(f'{sha}  {name}\n' for name,sha in sorted(checks.items())))
    return dict(status='STAGED_NOT_ACCEPTED', files=len(files), assets=len(manifest['assets']),
                manifest_sha256=digest(target), external_dependencies=external)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True);p.add_argument('--output', type=Path, required=True)
    a=p.parse_args();print(json.dumps(stage(a.root,a.output),indent=2))
