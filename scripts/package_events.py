"""Package the complete captured Experiment 012, gated by independent review."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess

from package_event_assets import digest, inventory, write_assets

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def object_sha(value):
    return hashlib.sha256((json.dumps(value, sort_keys=True, indent=2) + '\n').encode()).hexdigest()


def checked_artifact(root, relative, expected):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != relative:
        raise ValueError('unsafe evidence path')
    path = root / path
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or digest(path) != expected:
        raise ValueError('evidence missing or changed: ' + relative)
    return read(path)


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
        if (path.is_file() and path.name not in ('release-review.json', 'release-files.json')
                and 'release-independent-review' not in path.parts):
            add('repo/' + path.relative_to(root).as_posix(), path)
    publication = [
        'scripts/package_event_assets.py', 'scripts/package_events.py', 'scripts/report_events.py', 'scripts/extract_event_assets.py',
        'tests/test_package_event_assets.py', 'tests/test_package_events.py', 'tests/test_report_events.py', 'tests/test_extract_event_assets.py',
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
    manifest_path = packet / 'repo/results/012/RUN-SOURCE-MANIFEST.json'
    manifest_sha = digest(manifest_path)
    if result['frozen_manifest_sha256'] != manifest_sha:
        raise ValueError('report does not bind the actual run manifest')
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
    permitted_status = ('ACCEPTED',) if require_replay else ('ACCEPTED_FOR_STAGING', 'ACCEPTED')
    if (acceptance.get('status') not in permitted_status or
            acceptance.get('summary_sha256') != digest(summary) or
            acceptance.get('index_sha256') != digest(database) or
            acceptance.get('run_manifest_sha256') != manifest_sha):
        raise ValueError('independent numerical acceptance missing or stale')
    if require_replay:
        replay = read(root / 'results/012/extracted-reproduction.json')
        if (replay.get('status') != 'REPRODUCED' or not replay.get('full_scientific_summary') or
                replay.get('blocks') != 122 or replay.get('partitions') != 2806 or
                replay.get('run_manifest_sha256') != manifest_sha or replay.get('index_sha256') != digest(database)):
            raise ValueError('complete extracted reproduction required')
        generated = checked_artifact(root, replay['generated_receipt_path'], replay['generated_receipt_sha256'])
        for key in ('status', 'full_scientific_summary', 'blocks', 'partitions', 'run_manifest_sha256', 'index_sha256'):
            if generated.get(key) != replay.get(key):
                raise ValueError('replay wrapper differs from the generated native receipt')
        extraction = checked_artifact(root, replay['extraction_receipt_path'], replay['extraction_receipt_sha256'])
        stage = checked_artifact(root, replay['stage_manifest_path'], replay['stage_manifest_sha256'])
        if (extraction.get('status') != 'EXTRACTED_AND_VERIFIED' or
                extraction.get('extraction_path') != replay.get('extraction_path') or
                extraction.get('release_manifest_sha256') != replay['stage_manifest_sha256'] or
                extraction.get('embedded_manifest_sha256') != stage['manifest_sha256'] or
                stage.get('state') != 'CANDIDATE_NOT_ACCEPTED' or
                stage.get('run_manifest_sha256') != manifest_sha or
                extraction['files'] != {n: {k: r[k] for k in ('bytes', 'sha256')} for n, r in stage['files'].items()}):
            raise ValueError('extraction does not bind the staged payload')
        if extraction['assets'] != {n: {k: r[k] for k in ('bytes', 'sha256')} for n, r in stage['assets'].items()}:
            raise ValueError('extraction asset binding differs')
        for name, row in stage['assets'].items():
            asset = root / Path(replay['stage_manifest_path']).parent / name
            if asset.stat().st_size != row['bytes'] or digest(asset) != row['sha256']:
                raise ValueError('staged asset missing or changed')
    db = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('invalid numerical index')
        tables = dict(candidates=5760, partitions=2806, native_timeline=8296, native_match=99552,
                      prepared_metric=2440, block_effect=488, morphology_block=5368, completed_blocks=122)
        for table, count in tables.items():
            if db.execute('SELECT count(*) FROM ' + table).fetchone()[0] != count:
                raise ValueError('actual table cardinality differs: ' + table)
        selected = [r for r in read(packet / 'repo/results/010/prepared.json')['records'] if r['status'] == 'ELIGIBLE']
        if list(db.execute('SELECT array_row,candidate_index FROM completed_blocks ORDER BY array_row')) != [(r['array_row'], r['candidate_index']) for r in selected]:
            raise ValueError('completed block identities differ')
        protocol = read(packet / 'repo/protocol/experiment-012.json')
        expected_keys = {(i, branch, v) for i in range(122) for branch, variants in
                         [('native', protocol['native_variants']), ('prepared', protocol['prepared_variants'])] for v in variants}
        rows = list(db.execute('SELECT array_row,branch,variant,path,sha256,bytes FROM partitions'))
        if {(i, branch, v) for i, branch, v, path, sha, size in rows} != expected_keys:
            raise ValueError('indexed partition identities differ')
        indexed = {}
        for i, branch, variant, path, expected, size in rows:
            name = f'data/derived/012/events/row-{i:03d}/{branch}-{variant}.jsonl.gz'
            if path != name:
                raise ValueError('noncanonical partition path')
            actual = packet / 'repo' / path
            if not actual.is_file() or actual.stat().st_size != size or digest(actual) != expected:
                raise ValueError('indexed partition missing or changed')
            indexed['repo/' + path] = dict(bytes=size, sha256=expected)
        reported = {n: {k: r[k] for k in ('bytes', 'sha256')} for n, r in result['artifact_files'].items() if n.startswith('repo/data/derived/012/events/')}
        actual_paths = {'repo/' + p.relative_to(packet / 'repo').as_posix() for p in (packet / 'repo/data/derived/012/events').rglob('*') if p.is_file()}
        if indexed != reported or set(indexed) != actual_paths:
            raise ValueError('index, report and complete partition-file inventories differ')
    finally:
        db.close()
    return result


def verify_review(root, files, review):
    if review.get('status') != 'ACCEPTED' or review.get('files') != files:
        raise ValueError('independent release review missing or changed release inputs')
    required = {'review_artifact_path', 'review_artifact_sha256', 'native_handoff_path', 'native_handoff_sha256', 'reviewer_thread_id'}
    if not required <= set(review):
        raise ValueError('independent review provenance fields are required')
    evidence = checked_artifact(root, review['review_artifact_path'], review['review_artifact_sha256'])
    native = checked_artifact(root, review['native_handoff_path'], review['native_handoff_sha256'])
    reviewer = review['reviewer_thread_id']
    if (reviewer != '01a0dc45-5aa8-7f21-9138-a2437735cd5c' or
            evidence.get('status') != 'ACCEPTED' or evidence.get('scope') != 'FINAL_RELEASE' or
            evidence.get('reviewer_thread_id') != reviewer or evidence.get('files_inventory_sha256') != object_sha(files) or
            not evidence.get('dispositions') or any(r.get('status') != 'RESOLVED' for r in evidence['dispositions']) or
            native.get('thread_id') != reviewer or native.get('turn_status') != 'completed' or
            native.get('review_artifact_sha256') != review['review_artifact_sha256'] or
            not native.get('observed_utc') or not native.get('turn_id') or not native.get('native_source')):
        raise ValueError('independent final review provenance is incomplete')


def verify_stage_deltas(root, files, review):
    replay = read(root / 'results/012/extracted-reproduction.json')
    stage = checked_artifact(root, replay['stage_manifest_path'], replay['stage_manifest_sha256'])
    before = stage['files']
    if set(before) - set(files):
        raise ValueError('staged payload files were removed')
    changed = {n for n, row in before.items() if row != files[n]}
    added = set(files) - set(before)
    permitted_prefixes = ('repo/results/012/implementation-review/', 'repo/results/012/release-independent-review/')
    permitted_files = {'repo/results/012/extracted-reproduction.json', 'repo/results/012/extraction-receipt.json',
                       'repo/results/012/generated-reproduction.json', 'repo/notes/validation-012.md'}
    if any(n not in permitted_files and not n.startswith(permitted_prefixes) for n in changed | added):
        raise ValueError('unexpected payload change after extracted replay')
    actual = {n: dict(before_sha256=before[n]['sha256'] if n in before else None, after_sha256=files[n]['sha256']) for n in sorted(changed | added)}
    if review.get('stage_deltas') != actual:
        raise ValueError('post-extraction changes were not independently reviewed')


def package(root, packet, stage=False, stage_revision=1):
    root, packet = Path(root).resolve(), Path(packet).resolve()
    science = verify_science(root, packet, require_replay=not stage)
    base, mapping = collect(root, packet)
    files = inventory(base, mapping)
    if not stage:
        review = read(root / 'results/012/release-review.json')
        verify_review(root, files, review)
        verify_stage_deltas(root, files, review)
        mapping['repo/results/012/release-review.json'] = (root / 'results/012/release-review.json').relative_to(base).as_posix()
        for key in ('review_artifact_path', 'native_handoff_path'):
            mapping['repo/' + review[key]] = (root / review[key]).relative_to(base).as_posix()
        files = inventory(base, mapping)
    if not isinstance(stage_revision, int) or stage_revision < 1:
        raise ValueError('positive staging revision required')
    prefix = 'eegt-v0.8.0-' + (f'review-r{stage_revision}' if stage else 'data')
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
    parser.add_argument('--stage-revision', type=int, default=1)
    args = parser.parse_args()
    result = package(args.root, args.packet_root, args.stage, args.stage_revision)
    print(json.dumps(dict(state=result['state'], files=len(result['files']),
                          assets={k: {a: r[a] for a in ('bytes', 'sha256')} for k, r in result['assets'].items()})))
