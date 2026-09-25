"""Create a deterministic v0.4.0 derivative bundle; original EEG stays upstream."""
from pathlib import Path
import gzip
import json
import subprocess
import sys
import tarfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eegt.acquire import ROOT,digest
from eegt.corpus import atomic_json


def run(root=ROOT):
    root=Path(root);out=root/'dist';out.mkdir(exist_ok=True)
    summary=json.loads((root/'results/008/summary.json').read_text())
    features=json.loads((root/'results/008/features.json').read_text())
    for path,sha in summary['inputs'].items():
        if digest(root/path)!=sha:raise ValueError(f'analysis input changed: {path}')
    for row in features['records']:
        if row['status']=='EXTRACTED' and digest(root/row['path'])!=row['sha256']:raise ValueError('feature archive changed')
    review=json.loads((root/'results/008/independent-review.json').read_text())
    if review.get('status')!='ACCEPTED':raise ValueError('independent review has not accepted the release')
    paths=[]
    for directory in ['results/008','results/corpus-v2','data/derived/008']:
        paths += [p for p in (root/directory).rglob('*') if p.is_file() and not p.name.endswith('.partial')]
    paths += [root/p for p in ['results/corpus-v1/corpus.sqlite','results/corpus-v1/summary.json','results/003/model.json','protocol/experiment-008.json','protocol/corpus-manifest-008.json','notes/experiment-008.md','notes/model-compatibility-2026-09-25.md','notes/validation-008.md','requirements.lock']]
    paths=sorted(set(paths))
    content={str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=digest(p)) for p in paths}
    dest=out/'eegt-v0.4.0-data.tar.gz'
    with dest.with_suffix('.partial').open('wb') as handle:
        with gzip.GzipFile(fileobj=handle,mode='wb',filename='',mtime=0) as zipped:
            with tarfile.open(fileobj=zipped,mode='w|') as tar:
                for path in paths:
                    info=tar.gettarinfo(str(path),arcname=str(path.relative_to(root)))
                    info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0;info.mode=0o644
                    with path.open('rb') as f:tar.addfile(info,f)
    dest.with_suffix('.partial').replace(dest)
    manifest=dict(schema='eegt-release-manifest/v1',release='v0.4.0',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        totals=summary['totals'],index=json.loads((root/'results/corpus-v2/summary.json').read_text())['totals'],files=content,
        assets={dest.name:dict(bytes=dest.stat().st_size,sha256=digest(dest))},
        original_waves='Not bundled. Reacquire pinned OpenNeuro bytes using python -m eegt.repeated acquire; no private EEG is included.')
    manifest_path=out/'eegt-v0.4.0-manifest.json';atomic_json(manifest_path,manifest)
    (out/'SHA256SUMS-v0.4.0.txt').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in [dest,manifest_path]))
    print(json.dumps(manifest['assets']))


if __name__=='__main__':run()
