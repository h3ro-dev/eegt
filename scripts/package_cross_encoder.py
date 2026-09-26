"""Package the exact Experiment 011 reproduction packet and reviewed report."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def collect(root):
    root = Path(root).resolve()
    paths = set()
    for folder in ('eegt', 'scripts', 'tests'):
        paths.update(p.relative_to(root).as_posix() for p in (root / folder).rglob('*.py') if '__pycache__' not in p.parts)
    paths.update(p.relative_to(root).as_posix() for p in (root / 'protocol').glob('*.json'))
    for p in (root / 'results/011').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.name not in ('release-review.json', 'release-files.json'):
            paths.add(p.relative_to(root).as_posix())
    paths.update([
        'data/derived/010/prepared.npz', 'data/derived/010/embeddings.npz', 'data/derived/011/embeddings.npz',
        'results/010/prepared.json', 'results/010/inference.json', 'results/010/summary.json',
        'results/008/features.json', 'results/008/qualification.json', 'results/003/model.json',
        'requirements.lock', 'requirements-encoder.lock', 'pyproject.toml',
        'README.md', 'REPRODUCE-011.md', 'DATABASE.md', 'RUNBOOK.md', 'STRATEGY.md', 'CITATION.cff', 'LICENSE',
        'eegt/vendor/codebrain/LICENSE', 'eegt/vendor/codebrain/NOTICE',
        'eegt/vendor/cbramod/LICENSE', 'eegt/vendor/cbramod/NOTICE',
        'notes/experiment-011.md', 'notes/validation-011.md',
        'site/cross-encoder.html', 'site/index.html', 'site/styles.css', 'site/script.js', 'site/favicon.svg',
        'site/data/cross-encoder.json', 'site/data/cross-encoder-summary.png',
        'cross-encoder.html', 'index.html', 'styles.css', 'script.js', 'favicon.svg',
        'data/cross-encoder.json', 'data/cross-encoder-summary.png'])
    mapping = {'repo/' + p: p for p in sorted(paths)}
    # Retain the exact test source bound by the pre-inference manifest. The current
    # checkout adds only optional packet lookup; both versions remain in the bundle.
    mapping['repo/tests/test_cross_encoder_study.py'] = 'results/011/frozen-tests/test_cross_encoder_study.py'
    mapping['repo/results/011/current-test-harness.py'] = 'tests/test_cross_encoder_study.py'
    for name in ('FREEZE.json', 'adapter-acceptance.json', 'experiment-011.json'):
        mapping['input/' + name] = 'results/011/reproduction-inputs/' + name
    mapping['README.md'] = 'REPRODUCE-011.md'
    for archive, local in mapping.items():
        for value in (archive, local):
            p = PurePosixPath(value)
            if p.is_absolute() or '..' in p.parts:
                raise ValueError('archive path escapes its root')
        target = root / local
        if not target.is_file() or target.is_symlink() or not target.resolve().is_relative_to(root):
            raise ValueError('missing or unsafe release input: ' + local)
    return mapping


def hashes(root, mapping):
    return {p: digest(Path(root) / p) for p in sorted(set(mapping.values()))}


def verify_review(root, mapping, review):
    if review.get('status') != 'ACCEPTED':
        raise ValueError('independent release review is not accepted')
    if review.get('files_sha256') != hashes(root, mapping):
        raise ValueError('reviewed source, report or data changed')


def verify_science(root):
    root = Path(root)
    read = lambda p: json.loads((root / p).read_text())
    s = read('results/011/summary.json')
    i = read('results/011/inference.json')
    if s['protocol_sha256'] != digest(root / 'protocol/experiment-011.json'):
        raise ValueError('protocol changed')
    for p, sha in read('protocol/experiment-011.json')['inputs'].items():
        if digest(root / p) != sha:
            raise ValueError('frozen input changed: ' + p)
    if i['status'] != 'COMPLETE' or i['block_variant_runs'] != 610:
        raise ValueError('inference is incomplete')
    if digest(root / i['array_path']) != i['array_sha256'] or digest(root / 'results/011/analysis.sqlite') != s['database']['sha256']:
        raise ValueError('scientific output changed')
    if i['run_manifest_sha256'] != digest(root / 'results/011/run-manifest.json'):
        raise ValueError('run manifest changed')
    return s


def package(root=ROOT, stage=False):
    root = Path(root).resolve()
    mapping = collect(root)
    scientific = verify_science(root)
    expected = hashes(root, mapping)
    if not stage:
        review = json.loads((root / 'results/011/release-review.json').read_text())
        verify_review(root, mapping, review)
        mapping['repo/results/011/release-review.json'] = 'results/011/release-review.json'
    out = root / 'dist'
    out.mkdir(exist_ok=True)
    stem = 'eegt-v0.7.0-' + ('review' if stage else 'data')
    target = out / (stem + '.tar.gz')
    if target.exists() or target.with_suffix('.partial').exists():
        raise FileExistsError('preserve existing release artifact')
    files = {arc: {'source_path': local, 'bytes': (root / local).stat().st_size, 'sha256': digest(root / local)} for arc, local in sorted(mapping.items())}
    file_manifest = (json.dumps({'schema': 'eegt-release-content/v1', 'files': files}, sort_keys=True, indent=2) + '\n').encode()
    with target.with_suffix('.partial').open('xb') as handle:
        with gzip.GzipFile(filename='', fileobj=handle, mode='wb', mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w|') as archive:
                for name, local in sorted(mapping.items()):
                    path = root / local
                    info = tarfile.TarInfo(name)
                    info.size = path.stat().st_size
                    info.mode = 0o644
                    with path.open('rb') as f:
                        archive.addfile(info, f)
                info = tarfile.TarInfo('FILE-MANIFEST.json')
                info.size = len(file_manifest)
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(file_manifest))
    target.with_suffix('.partial').replace(target)
    manifest = {'schema': 'eegt-release-manifest/v2', 'release': 'v0.7.0',
                'state': 'CANDIDATE_NOT_ACCEPTED' if stage else 'REVIEWED_UNPUBLISHED',
                'build_base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
                'files': files, 'archive_members': len(files) + 1,
                'assets': {target.name: {'bytes': target.stat().st_size, 'sha256': digest(target)}},
                'review_input_hashes': expected,
                'denominators': {'selected_blocks': scientific['selected_blocks'], 'new_cbramod_forwards': 610, 'reused_codebrain_forwards': 610, 'paired_people': 5, 'primary_blocks': 110},
                'contents': 'Captured repo/input layout, both latent archives, selected numeric waves, complete candidate and analysis ledger, frozen source and corrections, independent evidence and publication. No model weights or full raw recordings.'}
    manifest_path = out / (stem + '-manifest.json')
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    if not stage:
        (out / 'SHA256SUMS-v0.7.0.txt').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in (target, manifest_path)))
    print(json.dumps({'state': manifest['state'], 'members': manifest['archive_members'], 'assets': manifest['assets']}))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--stage', action='store_true', help='Create an explicitly unaccepted review candidate; never publish it')
    args = parser.parse_args()
    package(args.root, args.stage)
