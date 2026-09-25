"""Package only the named public database/protocol files; no raw/private cache."""
from pathlib import Path
import hashlib
import json
import tarfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    destination=ROOT/'dist';destination.mkdir(exist_ok=True)
    files=[]
    for directory in ['results/corpus-v1','results/003','results/006','results/007','protocol','notes']:
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in {'.json','.md','.sqlite'})
    files.extend(ROOT/p for p in ['README.md','DATABASE.md','STRATEGY.md','LICENSE','DATA_CARD.md','CITATION.cff','requirements.lock'])
    files=sorted(set(files))
    manifest={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files}
    receipt=destination/'eegt-v0.3.0-database-manifest.json';receipt.write_text(json.dumps(dict(schema='eegt-release-database/v1',files=manifest),indent=2)+'\n')
    archive=destination/'eegt-v0.3.0-database.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as t:
        for p in files:t.add(p,arcname=str(p.relative_to(ROOT)))
        t.add(receipt,arcname=receipt.name)
    with tarfile.open(archive,'r:gz') as t:
        for name,identity in manifest.items():
            value=t.extractfile(name).read()
            if len(value)!=identity['bytes'] or hashlib.sha256(value).hexdigest()!=identity['sha256']:raise ValueError('archive content mismatch: '+name)
    print(json.dumps(dict(asset=archive.name,bytes=archive.stat().st_size,verified_entries=len(manifest),sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))


if __name__=='__main__':main()
