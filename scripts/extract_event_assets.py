"""Verify every shard and safely extract one complete EEGT event release."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import tarfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def safe_name(name):
    p = PurePosixPath(name)
    if (not name or p.is_absolute() or '..' in p.parts or p.as_posix() != name or
            '\\' in name or ':' in name or PureWindowsPath(name).drive or
            any(part.rstrip(' .') != part or PureWindowsPath(part).is_reserved() for part in p.parts)):
        raise ValueError('unsafe archive path: ' + name)


def extract(manifest_path, assets, destination, receipt_path):
    manifest_path, destination, receipt_path = map(Path, (manifest_path, destination, receipt_path))
    manifest = json.loads(manifest_path.read_text())
    if destination.exists() or receipt_path.exists() or receipt_path.resolve().is_relative_to(destination.resolve()):
        raise ValueError('new extraction directory and external receipt path required')
    supplied = {Path(p).name: Path(p) for p in assets}
    if len(supplied) != len(assets) or set(supplied) != set(manifest['assets']):
        raise ValueError('supply exactly the shards listed in the trusted release manifest')
    files = manifest['files']
    expected_manifest = (json.dumps(dict(schema='eegt-release-content/v1', files=files), sort_keys=True, indent=2) + '\n').encode()
    if hashlib.sha256(expected_manifest).hexdigest() != manifest['manifest_sha256']:
        raise ValueError('release metadata and embedded-manifest hash disagree')
    for name in files:
        safe_name(name)
    memberships = [member for row in manifest['assets'].values() for member in row['members']]
    if len(memberships) != len(set(memberships)) or set(memberships) != set(files):
        raise ValueError('incomplete or duplicate shard member assignment')
    for name, path in supplied.items():
        expected = manifest['assets'][name]
        if path.stat().st_size != expected['bytes'] or digest(path) != expected['sha256']:
            raise ValueError('asset checksum mismatch: ' + name)
    # Validate the entire member/type inventory before creating any output file.
    for name, path in supplied.items():
        with tarfile.open(path, 'r:gz') as archive:
            members = archive.getmembers()
            names = [m.name for m in members]
            expected = set(manifest['assets'][name]['members']) | {'FILE-MANIFEST.json'}
            if len(names) != len(set(names)) or set(names) != expected:
                raise ValueError('unlisted, missing or duplicate archive member: ' + name)
            for m in members:
                safe_name(m.name)
                if not m.isfile():
                    raise ValueError('links and non-file members are forbidden')
                if m.name == 'FILE-MANIFEST.json' and m.size != len(expected_manifest):
                    raise ValueError('embedded manifest size differs')
                if m.name != 'FILE-MANIFEST.json' and m.size != files[m.name]['bytes']:
                    raise ValueError('member size differs from manifest')
    destination.mkdir(parents=True)
    manifest_bytes = None
    extracted = {}
    for name, path in sorted(supplied.items()):
        with tarfile.open(path, 'r:gz') as archive:
            for m in archive:
                safe_name(m.name)
                allowed = set(manifest['assets'][name]['members']) | {'FILE-MANIFEST.json'}
                if not m.isfile() or m.name not in allowed or m.name in extracted:
                    raise ValueError('archive changed after preflight')
                src = archive.extractfile(m)
                if m.name == 'FILE-MANIFEST.json':
                    if m.size != len(expected_manifest):
                        raise ValueError('embedded manifest changed after preflight')
                    value = src.read()
                    if (hashlib.sha256(value).hexdigest() != manifest['manifest_sha256'] or
                            json.loads(value)['files'] != files or
                            (manifest_bytes is not None and value != manifest_bytes)):
                        raise ValueError('inconsistent embedded file manifest')
                    if manifest_bytes is None:
                        (destination / m.name).write_bytes(value)
                        manifest_bytes = value
                    continue
                target = destination / m.name
                if m.size != files[m.name]['bytes']:
                    raise ValueError('member size changed after preflight')
                target.parent.mkdir(parents=True, exist_ok=True)
                h = hashlib.sha256()
                with target.open('xb') as out:
                    for block in iter(lambda: src.read(1048576), b''):
                        out.write(block)
                        h.update(block)
                if h.hexdigest() != files[m.name]['sha256']:
                    raise ValueError('extracted content mismatch: ' + m.name)
                extracted[m.name] = dict(bytes=target.stat().st_size, sha256=h.hexdigest())
    actual = {p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
    if actual != set(files) | {'FILE-MANIFEST.json'} or any(p.is_symlink() for p in destination.rglob('*')):
        raise ValueError('extracted tree inventory differs')
    receipt = dict(schema='eegt-verified-extraction/v1', status='EXTRACTED_AND_VERIFIED',
                   created_utc=datetime.now(timezone.utc).isoformat(),
                   release_manifest_path=str(manifest_path.resolve()), release_manifest_sha256=digest(manifest_path),
                   extraction_path=str(destination.resolve()), files=extracted,
                   assets={n: dict(bytes=p.stat().st_size, sha256=digest(p)) for n, p in sorted(supplied.items())},
                   embedded_manifest_sha256=manifest['manifest_sha256'])
    with receipt_path.open('x') as out:
        json.dump(receipt, out, sort_keys=True, indent=2)
        out.write('\n')
    return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--receipt', type=Path, required=True)
    p.add_argument('assets', type=Path, nargs='+')
    a = p.parse_args()
    result = extract(a.manifest, a.assets, a.destination, a.receipt)
    print(json.dumps(dict(status=result['status'], files=len(result['files']), path=result['extraction_path'])))
