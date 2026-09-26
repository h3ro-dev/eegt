"""Package the complete captured Experiment 012, gated by independent review."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess

from package_event_assets import digest, inventory, write_assets

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def collect(root, packet):
    """Keep the exact execution layout; overlay only byte-identical sealed files."""
    root, packet = Path(root).resolve(), Path(packet).resolve()
    base = Path(os.path.commonpath([root, packet]))
    mapping = {}

    def add(archive, local):
        relative = local.relative_to(base).as_posix()
        if archive in mapping and digest(base / mapping[archive]) != digest(local):
            raise ValueError('conflicting captured release path: ' + archive)
        mapping[archive] = relative

    for name, expected in read(packet / 'SOURCE-MANIFEST.json')['files'].items():
        target = packet / name
        if digest(target) != expected['sha256']:
            raise ValueError('inherited input changed: ' + name)
        add(name, target)
    for name in ('SOURCE-MANIFEST.json', 'RESOURCE-EXPANSION-001.json', 'out/REPORT.json', 'out/TEST-RESULTS.json'):
        add(name, packet / name)
    seal = read(packet / 'repo/results/012/RUN-SOURCE-MANIFEST.json')
    for name, expected in seal['source_files'].items():
        target = packet / 'repo' / name
        if digest(target) != expected['sha256'] or digest(root / name) != expected['sha256']:
            raise ValueError('frozen or integrated source changed: ' + name)
        add('repo/' + name, target)
    for folder in ('results/012', 'data/derived/012/events'):
        for path in sorted((packet / 'repo' / folder).rglob('*')):
            if path.is_file():
                if path.name.endswith(('.partial', '-journal', '-wal', '-shm')) or '__pycache__' in path.parts:
                    raise ValueError('unfinished run artifact: ' + str(path))
                add('repo/' + path.relative_to(packet / 'repo').as_posix(), path)
    # Publication and independent evidence are added without replacing run bytes.
    for path in sorted((root / 'results/012').rglob('*')):
        if path.is_file() and path.name not in ('release-review.json', 'release-files.json'):
            add('repo/' + path.relative_to(root).as_posix(), path)
    publication = [
        'scripts/package_event_assets.py', 'scripts/package_events.py', 'scripts/report_events.py',
        'tests/test_package_event_assets.py', 'tests/test_package_events.py', 'tests/test_report_events.py',
        'REPRODUCE-012.md', 'README.md', 'STRATEGY.md', 'DATABASE.md', 'RUNBOOK.md', 'CITATION.cff',
        'notes/experiment-012.md', 'notes/validation-012.md',
        'site/events.html', 'site/index.html', 'site/styles.css', 'site/script.js', 'site/favicon.svg',
        'site/data/events.json', 'site/data/events-summary.png',
        'events.html', 'index.html', 'styles.css', 'script.js', 'favicon.svg',
        'data/events.json', 'data/events-summary.png']
    for name in publication:
        add('repo/' + name, root / name)
    add('README.md', root / 'REPRODUCE-012.md')
    return base, mapping


def verify_science(root, packet, require_replay=True):
    root, packet = Path(root), Path(packet)
    result = read(packet / 'out/REPORT.json')
    if result['status'] != 'COMPLETE':
        raise ValueError('numerical run not complete')
    expected_counts = dict(indexed_blocks=122, partitions=2806, native_matches=99552,
                           prepared_metrics=2440, candidate_rows=5760)
    if result['counts'] != expected_counts:
        raise ValueError('numerical run denominators changed')
    for name, expected in result['artifact_files'].items():
        target = packet / name
        if not target.is_file() or digest(target) != expected['sha256']:
            raise ValueError('run output changed: ' + name)
    summary = packet / 'repo/results/012/summary.json'
    database = packet / 'repo/results/012/analysis.sqlite'
    if (digest(summary) != digest(root / 'results/012/summary.json') or
            digest(database) != digest(root / 'results/012/analysis.sqlite')):
        raise ValueError('canonical science differs from run')
    if read(summary)['status'] != 'COMPLETE_NUMERICAL_RECORD':
        raise ValueError('scientific summary not complete')
    acceptance = read(root / 'results/012/implementation-review/ACCEPTANCE.json')
    if (acceptance.get('status') != 'ACCEPTED' or
            acceptance.get('summary_sha256') != digest(summary) or
            acceptance.get('index_sha256') != digest(database)):
        raise ValueError('independent numerical acceptance missing or stale')
    if require_replay:
        replay = read(root / 'results/012/extracted-reproduction.json')
        if (replay.get('status') != 'REPRODUCED' or not replay.get('full_scientific_summary') or
                replay.get('blocks') != 122 or replay.get('partitions') != 2806 or
                replay.get('run_manifest_sha256') != digest(packet / 'repo/results/012/RUN-SOURCE-MANIFEST.json')):
            raise ValueError('complete extracted reproduction required')
    db = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('invalid numerical index')
    finally:
        db.close()
    return result


def verify_review(files, review):
    if review.get('status') != 'ACCEPTED' or review.get('files') != files:
        raise ValueError('independent release review missing or changed release inputs')


def package(root, packet, stage=False):
    root, packet = Path(root).resolve(), Path(packet).resolve()
    science = verify_science(root, packet, require_replay=not stage)
    base, mapping = collect(root, packet)
    files = inventory(base, mapping)
    if not stage:
        review = read(root / 'results/012/release-review.json')
        verify_review(files, review)
        mapping['repo/results/012/release-review.json'] = (root / 'results/012/release-review.json').relative_to(base).as_posix()
        files = inventory(base, mapping)
    prefix = 'eegt-v0.8.0-' + ('review' if stage else 'data')
    out = root / 'dist'
    manifest_path = out / (prefix + '-manifest.json')
    sums_path = out / (prefix + '-SHA256SUMS.txt')
    if manifest_path.exists() or sums_path.exists():
        raise FileExistsError('preserve existing release metadata')
    assets = write_assets(base, mapping, out, prefix, expected_files=files)
    manifest = dict(assets, schema='eegt-012-release/v1', release='v0.8.0',
                    state='CANDIDATE_NOT_ACCEPTED' if stage else 'REVIEWED_UNPUBLISHED',
                    build_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
                    run_manifest_sha256=science['frozen_manifest_sha256'],
                    numerical_counts=science['counts'])
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    sums_path.write_text(''.join(f"{row['sha256']}  {name}\n" for name, row in sorted(assets['assets'].items())) +
                         f'{digest(manifest_path)}  {manifest_path.name}\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--packet-root', type=Path, required=True)
    parser.add_argument('--stage', action='store_true')
    args = parser.parse_args()
    result = package(args.root, args.packet_root, args.stage)
    print(json.dumps(dict(state=result['state'], files=len(result['files']),
                          assets={k: {a: r[a] for a in ('bytes', 'sha256')} for k, r in result['assets'].items()})))
