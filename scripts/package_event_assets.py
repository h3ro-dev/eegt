"""Deterministic, bounded-size tar assets for the full waveform-event ledger.

This is an archive writer, not a scientific or independent-review gate. The
Experiment 012 release command must supply its accepted exact file mapping.
"""
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile


GITHUB_ASSET_LIMIT = 2 * 1024 ** 3  # GitHub Docs, About releases, checked 2026-09-26.
DEFAULT_SHARD_BYTES = 1_500_000_000


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inventory(root, mapping):
    """Reject escapes/symlinks and bind both source and archive identities."""
    root = Path(root).resolve()
    if not mapping:
        raise ValueError('empty release mapping')
    files = {}
    for name, relative in sorted(mapping.items()):
        for value in (name, relative):
            path = PurePosixPath(value)
            if (not value or path.is_absolute() or '..' in path.parts
                    or path.as_posix() != value or '\\' in value):
                raise ValueError('noncanonical or unsafe release path')
        if name == 'FILE-MANIFEST.json':
            raise ValueError('reserved manifest name')
        target = root / relative
        if not target.is_file() or target.is_symlink() or not target.resolve().is_relative_to(root):
            raise ValueError('missing or unsafe release source: ' + relative)
        # Reject symlinked directories too, even if they resolve inside root.
        if any(parent.is_symlink() for parent in target.parents if parent != root and parent.is_relative_to(root)):
            raise ValueError('symlinked release source directory')
        files[name] = dict(source_path=relative, bytes=target.stat().st_size, sha256=digest(target))
    return files


def _tar_size(files, manifest_bytes):
    """Exact uncompressed PAX archive length, including block padding."""
    size = 0
    for name, byte_count in [*((n, r['bytes']) for n, r in files.items()), ('FILE-MANIFEST.json', manifest_bytes)]:
        info = tarfile.TarInfo(name)
        info.size = byte_count
        info.mode = 0o644
        size += len(info.tobuf(format=tarfile.PAX_FORMAT)) + ((byte_count + 511) // 512) * 512
    size += 1024
    return ((size + tarfile.RECORDSIZE - 1) // tarfile.RECORDSIZE) * tarfile.RECORDSIZE


def plan_shards(files, manifest_bytes, shard_bytes=DEFAULT_SHARD_BYTES):
    if shard_bytes < 10240 or shard_bytes >= GITHUB_ASSET_LIMIT:
        raise ValueError('invalid shard byte bound')
    groups, current = [], {}
    for name, row in sorted(files.items()):
        proposed = {**current, name: row}
        if _tar_size(proposed, manifest_bytes) > shard_bytes:
            if not current:
                raise ValueError('single member exceeds shard bound: ' + name)
            groups.append(current)
            current = {name: row}
            if _tar_size(current, manifest_bytes) > shard_bytes:
                raise ValueError('single member exceeds shard bound: ' + name)
        else:
            current = proposed
    if current:
        groups.append(current)
    if not groups:
        raise ValueError('empty shard plan')
    return groups


def write_assets(root, mapping, output, prefix, *, expected_files, shard_bytes=DEFAULT_SHARD_BYTES):
    """Write checked, immutable shards; each holds the same complete manifest.

    The cap applies to the uncompressed tar plus a post-write compressed-size
    check. Input files are streamed. Existing or failed output is never replaced.
    """
    root, output = Path(root).resolve(), Path(output)
    if not prefix or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in prefix):
        raise ValueError('unsafe asset prefix')
    files = inventory(root, mapping)
    if files != expected_files:
        raise ValueError('release inputs differ from accepted inventory')
    manifest = (json.dumps({'schema': 'eegt-release-content/v1', 'files': files}, sort_keys=True, indent=2) + '\n').encode()
    groups = plan_shards(files, len(manifest), shard_bytes)
    targets = [output / f'{prefix}-part-{i+1:03d}-of-{len(groups):03d}.tar.gz' for i in range(len(groups))]
    if any(p.exists() or p.with_suffix('.partial').exists() for p in targets):
        raise FileExistsError('preserve existing or partial release asset')
    output.mkdir(parents=True, exist_ok=True)
    assets = {}
    for target, group in zip(targets, groups, strict=True):
        partial = target.with_suffix('.partial')
        with partial.open('xb') as handle:
            with gzip.GzipFile(filename='', fileobj=handle, mode='wb', mtime=0, compresslevel=1) as zipped:
                with tarfile.open(fileobj=zipped, mode='w|', format=tarfile.PAX_FORMAT) as archive:
                    for name, row in group.items():
                        source = root / row['source_path']
                        if source.stat().st_size != row['bytes'] or digest(source) != row['sha256']:
                            raise ValueError('release input changed during packaging: ' + name)
                        info = tarfile.TarInfo(name)
                        info.size, info.mode = row['bytes'], 0o644
                        with source.open('rb') as src:
                            archive.addfile(info, src)
                    info = tarfile.TarInfo('FILE-MANIFEST.json')
                    info.size, info.mode = len(manifest), 0o644
                    archive.addfile(info, io.BytesIO(manifest))
        if partial.stat().st_size >= GITHUB_ASSET_LIMIT:
            raise ValueError('compressed asset exceeds GitHub limit; retained partial')
        # Read the actual archive, proving streamed bytes and duplicate exclusion.
        with tarfile.open(partial, 'r:gz') as archive:
            members = archive.getmembers()
            if len(members) != len(group) + 1 or {m.name for m in members} != set(group) | {'FILE-MANIFEST.json'}:
                raise ValueError('archive member inventory mismatch')
            for member in members:
                if not member.isfile():
                    raise ValueError('non-file release member')
                src = archive.extractfile(member)
                h = hashlib.sha256()
                for block in iter(lambda: src.read(1024 * 1024), b''):
                    h.update(block)
                expected = hashlib.sha256(manifest).hexdigest() if member.name == 'FILE-MANIFEST.json' else group[member.name]['sha256']
                if h.hexdigest() != expected:
                    raise ValueError('archive content mismatch: ' + member.name)
        partial.replace(target)
        assets[target.name] = dict(bytes=target.stat().st_size, sha256=digest(target), members=sorted(group))
    return dict(schema='eegt-sharded-assets/v1', files=files, assets=assets,
                manifest_sha256=hashlib.sha256(manifest).hexdigest(),
                shard_uncompressed_byte_bound=shard_bytes, asset_exclusive_byte_limit=GITHUB_ASSET_LIMIT)
