"""Stage the curator catalog, its exact inputs and an offline rebuild workflow."""
import argparse,json,sys,hashlib
from pathlib import Path
from build_database import sha,confined,validate_summary


def stage(root,manifest_path,database_path,summary_path,output):
    root=Path(root).resolve();manifest_path=Path(manifest_path).resolve();database_path=Path(database_path).resolve();summary_path=Path(summary_path).resolve();output=Path(output)
    if output.exists():raise FileExistsError(output)
    manifest_bytes=manifest_path.read_bytes();manifest_hash=hashlib.sha256(manifest_bytes).hexdigest()
    manifest=json.loads(manifest_bytes);summary=json.loads(summary_path.read_text())
    if manifest.get('state')!='CONSOLIDATED_RELEASE_CANDIDATE':raise ValueError('Accepted validation publication is required')
    if summary['input_manifest_sha256']!=sha(manifest_path) or summary['database_sha256']!=sha(database_path):raise ValueError('Catalog build binding differs')
    validate_summary(database_path,summary)
    if summary['state']!=manifest['state'] or summary['inputs']!=manifest['inputs']:raise ValueError('Catalog manifest/database evidence differs')
    mapping={}
    def add(path):
        relative=path.resolve().relative_to(root).as_posix();mapping['workspace/'+relative]=relative
    for relative,digest in manifest['inputs'].items():
        path=confined(root,relative)
        if sha(path)!=digest:raise ValueError('Changed curator input: '+relative)
        add(path)
    for path in [manifest_path,database_path,summary_path]:add(path)
    for name in ['build_database.py','prepare_index.py','report_catalog.py','package_catalog.py','test_database.py','test_catalog_publication.py','QUERIES.md','REPRODUCE.md','SYNTHESIS.md','DOI-METADATA.json']:
        add(root/'work/database-release'/name)
    for name in ['scripts/package_event_assets.py','scripts/extract_event_assets.py','LICENSE','DATA_CARD.md','MODEL_CARD.md','CITATION.cff','CONTRIBUTING.md','DATABASE.md']:
        add(root/'outputs/eegt'/name)
    sys.path.insert(0,str(root/'outputs/eegt/scripts'))
    from package_event_assets import inventory,write_assets
    files=inventory(root,mapping)
    staged=write_assets(root,mapping,output,'eegt-v0.10.0-catalog',expected_files=files)
    if sha(manifest_path)!=manifest_hash:raise ValueError('Manifest changed during packaging')
    staged.update(state='CANDIDATE_NOT_ACCEPTED',input_manifest_sha256=manifest_hash,database_sha256=sha(database_path),acceptance='Independent extracted rebuild/schema/lineage review and public download readback required')
    p=output/'eegt-v0.10.0-catalog-manifest.json';p.write_text(json.dumps(staged,indent=2,sort_keys=True)+'\n')
    sums={n:r['sha256'] for n,r in staged['assets'].items()};sums[p.name]=sha(p)
    (output/'eegt-v0.10.0-catalog-SHA256SUMS.txt').write_text(''.join(f'{h}  {n}\n' for n,h in sorted(sums.items())))
    return dict(status='STAGED_NOT_ACCEPTED',files=len(files),assets=len(staged['assets']),manifest_sha256=sha(p),database_sha256=sha(database_path))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['root','manifest','database','summary','output']:p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args();print(json.dumps(stage(a.root,a.manifest,a.database,a.summary,a.output),indent=2))
