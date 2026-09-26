"""Read-only review fixtures for the corrected Experiment 012 release gates."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile


SCRIPTS = Path(__file__).resolve().parents[1] / 'repo/scripts'
sys.path.insert(0, str(SCRIPTS))
from extract_event_assets import extract
from package_event_assets import digest, inventory, write_assets

spec = importlib.util.spec_from_file_location('package_events', SCRIPTS / 'package_events.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def expect_refusal(label, func, marker, *, destination=None):
    try:
        func()
    except (ValueError, FileNotFoundError) as error:
        if marker not in str(error):
            raise AssertionError(f'{label}: wrong refusal: {error}') from error
        if destination is not None and destination.exists():
            raise AssertionError(f'{label}: destination created before refusal')
        print(f'PASS {label}: {error}')
    else:
        raise AssertionError(f'{label}: malformed fixture was accepted')


with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
    packet = Path(temp)
    root = packet / 'repo'
    out = packet / 'out'
    out.mkdir()
    summary = root / 'results/012/summary.json'
    database = root / 'results/012/analysis.sqlite'
    manifest = root / 'results/012/RUN-SOURCE-MANIFEST.json'
    acceptance = root / 'results/012/implementation-review/ACCEPTANCE.json'
    write_json(summary, {'status': 'COMPLETE_NUMERICAL_RECORD'})
    write_json(manifest, {'status': 'FROZEN_BEFORE_EMPIRICAL_EVENT_CALL'})
    import sqlite3
    db = sqlite3.connect(database)
    for table in ('candidates', 'partitions', 'native_timeline', 'native_match',
                  'prepared_metric', 'block_effect', 'morphology_block', 'completed_blocks'):
        db.execute(f'CREATE TABLE {table}(dummy INTEGER)')
    db.commit()
    db.close()
    accepted = dict(status='ACCEPTED_FOR_STAGING', summary_sha256=digest(summary),
                    index_sha256=digest(database), run_manifest_sha256=digest(manifest))
    write_json(acceptance, accepted)
    report = dict(status='COMPLETE', counts=dict(indexed_blocks=122, partitions=2806,
                  native_matches=99552, prepared_metrics=2440, candidate_rows=5760),
                  frozen_manifest_sha256=digest(manifest), artifact_files={})
    write_json(out / 'REPORT.json', report)
    expect_refusal('self-reported counts versus empty SQLite',
                   lambda: package.verify_science(root, packet, require_replay=False),
                   'actual table cardinality differs: candidates')
    accepted['status'] = 'ACCEPTED'
    write_json(acceptance, accepted)
    expect_refusal('missing extracted replay receipt',
                   lambda: package.verify_science(root, packet, require_replay=True),
                   'extracted-reproduction.json')
    write_json(root / 'results/012/extracted-reproduction.json',
               dict(status='REPRODUCED', full_scientific_summary=True, blocks=122,
                    partitions=2806, run_manifest_sha256=digest(manifest),
                    index_sha256=digest(database), generated_receipt_path='results/012/missing.json',
                    generated_receipt_sha256='0' * 64))
    expect_refusal('unbound generated replay receipt',
                   lambda: package.verify_science(root, packet, require_replay=True),
                   'evidence missing or changed')

    prior = {'repo/science.json': dict(source_path='old/science.json', bytes=1, sha256='a' * 64)}
    stage = root / 'dist/stage-manifest.json'
    write_json(stage, {'files': prior})
    write_json(root / 'results/012/extracted-reproduction.json',
               dict(stage_manifest_path='dist/stage-manifest.json', stage_manifest_sha256=digest(stage)))
    added = dict(source_path='new/validation.md', bytes=2, sha256='b' * 64)
    final = {**prior, 'repo/notes/validation-012.md': added}
    delta = {'repo/notes/validation-012.md': dict(before_sha256=None, after_sha256='b' * 64)}
    expect_refusal('undisclosed post-stage note',
                   lambda: package.verify_stage_deltas(root, final, {'stage_deltas': {}}),
                   'post-extraction changes were not independently reviewed')
    package.verify_stage_deltas(root, final, {'stage_deltas': delta})
    print('PASS disclosed allowed post-stage note')
    forbidden = {**prior, 'repo/protocol/experiment-012.json': added}
    expect_refusal('post-stage science addition',
                   lambda: package.verify_stage_deltas(root, forbidden, {}),
                   'unexpected payload change after extracted replay')

    source = packet / 'source'
    source.mkdir()
    (source / 'one.txt').write_text('one\n')
    mapping = {'repo/one.txt': 'source/one.txt'}
    assets = write_assets(packet, mapping, packet / 'assets', 'fixture',
                          expected_files=inventory(packet, mapping), shard_bytes=20480)
    asset = next((packet / 'assets').glob('*.tar.gz'))
    for kind in ('duplicate', 'traversal', 'missing'):
        with tarfile.open(asset, 'r:gz') as archive:
            original = [(member, archive.extractfile(member).read()) for member in archive.getmembers()]
        with tarfile.open(asset, 'w:gz') as archive:
            for member, body in original:
                if kind == 'missing' and member.name == 'repo/one.txt':
                    continue
                archive.addfile(member, io.BytesIO(body))
            if kind in ('duplicate', 'traversal'):
                member = tarfile.TarInfo('repo/one.txt' if kind == 'duplicate' else '../escape.txt')
                member.size = 1
                archive.addfile(member, io.BytesIO(b'x'))
        assets['assets'][asset.name].update(bytes=asset.stat().st_size, sha256=digest(asset))
        release_manifest = packet / 'release-manifest.json'
        write_json(release_manifest, assets)
        dest = packet / f'extract-{kind}'
        expect_refusal(f'{kind} tar member',
                       lambda: extract(release_manifest, [asset], dest, packet / f'{kind}-receipt.json'),
                       'unlisted, missing or duplicate archive member', destination=dest)
        # Rebuild a clean asset for the next independent malformed fixture.
        asset.unlink()
        assets = write_assets(packet, mapping, packet / f'assets-{kind}', f'fixture-{kind}',
                              expected_files=inventory(packet, mapping), shard_bytes=20480)
        asset = next((packet / f'assets-{kind}').glob('*.tar.gz'))
