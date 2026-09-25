"""Deterministic v0.5.0 bundle; pinned weights are downloaded separately."""
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
    summary=json.loads((root/'results/009/summary.json').read_text())
    prep=json.loads((root/'results/009/prepared.json').read_text())
    inference=json.loads((root/'results/009/inference.json').read_text())
    for receipt in [summary,inference,prep]:
        for path,sha in receipt.get('inputs',{}).items():
            if digest(root/path)!=sha:raise ValueError(f'recorded input changed: {path}')
    for receipt in [prep,inference]:
        if digest(root/receipt['array_path'])!=receipt['array_sha256']:raise ValueError('array changed')
    if digest(root/'results/009/analysis.sqlite')!=summary['analysis_sha256']:raise ValueError('database changed')
    review=json.loads((root/'results/009/independent-review.json').read_text())
    if review.get('status')!='ACCEPTED':raise ValueError('independent review has not accepted release')
    paths=[]
    for directory in ['results/009','data/derived/009']:
        paths += [p for p in (root/directory).rglob('*') if p.is_file() and not p.name.endswith('.partial')]
    for directory in ['eegt','scripts','tests']:
        paths += [p for p in (root/directory).rglob('*.py') if '__pycache__' not in p.parts]
    paths += list((root/'protocol').glob('*.json'))
    paths += [root/p for p in ['results/003/model.json','results/008/features.json','results/008/qualification.json',
         'requirements.lock','requirements-encoder.lock','README.md','DATABASE.md','RUNBOOK.md','STRATEGY.md',
         'CITATION.cff','LICENSE','eegt/vendor/codebrain/LICENSE','eegt/vendor/codebrain/NOTICE',
         'notes/experiment-009.md','notes/validation-009.md','site/pretrained.html','site/styles.css',
         'site/data/pretrained.json','site/data/pretrained-eligibility.png','pretrained.html','styles.css',
         'data/pretrained.json','data/pretrained-eligibility.png']]
    paths=sorted(set(paths))
    content={str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=digest(p)) for p in paths}
    dest=out/'eegt-v0.5.0-data.tar.gz'
    with dest.with_suffix('.partial').open('wb') as handle:
        with gzip.GzipFile(fileobj=handle,mode='wb',filename='',mtime=0) as zipped:
            with tarfile.open(fileobj=zipped,mode='w|') as tar:
                for path in paths:
                    info=tar.gettarinfo(str(path),arcname=str(path.relative_to(root)))
                    info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0;info.mode=0o644
                    with path.open('rb') as f:tar.addfile(info,f)
    dest.with_suffix('.partial').replace(dest)
    manifest=dict(schema='eegt-release-manifest/v1',release='v0.5.0',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        totals=summary['totals'],primary_statuses=[r['status'] for r in summary['primary_statistics']],files=content,
        assets={dest.name:dict(bytes=dest.stat().st_size,sha256=digest(dest))},
        contents='Nine derived numerical wave blocks, aligned frozen descriptors, 45 encoder outputs, all240candidate receipts, comparisons, code and source attribution. Original full recordings and pretrained weights remain upstream. Raw-to-prepared reproduction also uses v0.4.0 feature archives and pinned raw sources.')
    manifest_path=out/'eegt-v0.5.0-manifest.json';atomic_json(manifest_path,manifest)
    (out/'SHA256SUMS-v0.5.0.txt').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in [dest,manifest_path]))
    print(json.dumps(manifest['assets']))


if __name__=='__main__':run()
