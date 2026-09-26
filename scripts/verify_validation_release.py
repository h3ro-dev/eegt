"""Additional release checks around the unchanged frozen Experiment013 replay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def require_complete_replay(receipt,root):
    if (receipt.get('status')!='REPLAYED_RECORDED_EVENTS' or receipt.get('full_scientific_summary') is not True
        or receipt.get('completed_blocks')!=174 or receipt.get('partitions')!=4002
        or receipt.get('detector_regenerated') is not False
        or receipt.get('run_manifest_sha256')!=digest(root/'results/013/RUN-SOURCE-MANIFEST.json')
        or receipt.get('input_acceptance_sha256')!=digest(root/'results/013/INPUT-ACCEPTANCE.json')):
        raise ValueError('Replay is not the complete source-bound174block/4002partition ledger')


def morphology(root):
    from eegt import validation_study as study
    freeze=study.require_accepted_freeze(root,stage='events')
    study.require_input_acceptance(root,freeze)
    summary=json.loads((root/'results/013/summary.json').read_text())
    if summary['status']!='COMPLETE_NUMERICAL_RECORD':raise ValueError('Complete summary required')
    path=root/'results/013/analysis.sqlite';before=digest(path)
    total=0
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
        completed=[x[0] for x in db.execute('SELECT candidate_index FROM completed_blocks ORDER BY candidate_index')]
        if len(completed)!=174:raise ValueError('Full selected block census required')
        for ci in completed:
            part=study.partition_path(root,ci,'native','primary')
            row=db.execute("SELECT sha256 FROM partitions WHERE candidate_index=? AND branch='native' AND variant='primary'",(ci,)).fetchone()
            if not row or digest(part)!=row[0]:raise ValueError('Native primary partition changed')
            _,events=study.read_partition(part)
            actual=study.old.morphology_summary(study.old.morphology_groups(events))
            saved=[]
            for channel,family,band,definition,receipt_json in db.execute('SELECT channel,family,band,definition,receipt_json FROM morphology_block WHERE candidate_index=?',(ci,)):
                entry=json.loads(receipt_json)
                if (channel!=entry['channel'] or family!=entry['family'] or band!=study.canonical(entry['band_hz']) or definition!=entry['definition']):
                    raise ValueError(f'Morphology index keys differ from receipt: {ci}')
                saved.append(entry)
            if sorted(map(study.canonical,actual))!=sorted(map(study.canonical,saved)):
                raise ValueError(f'Morphology differs from recorded partition: {ci}')
            total+=len(saved)
        if total!=summary['morphology_rows'] or db.execute('SELECT count(*) FROM morphology_block').fetchone()[0]!=total:
            raise ValueError('Morphology total differs')
    if digest(path)!=before:raise ValueError('Read-only release check changed index')
    return {'schema':'eegt-013-morphology-replay/v1','status':'MORPHOLOGY_REPRODUCED_FROM_RECORDED_EVENTS','blocks':174,'rows':total,'index_sha256':before,'summary_sha256':digest(root/'results/013/summary.json'),'run_manifest_sha256':digest(root/'results/013/RUN-SOURCE-MANIFEST.json'),'detector_regenerated':False}


def approve(stage_path,review_path,replay_path,morphology_path,extraction_path):
    read=lambda p:json.loads(p.read_text())
    stage,review,replay,morph,extraction=map(read,[stage_path,review_path,replay_path,morphology_path,extraction_path])
    if review.get('status')!='ACCEPTED' or not review.get('reviewer_actor') or not review.get('reviewer_thread'):
        raise ValueError('Independent final review missing')
    evidence={str(p.resolve()):digest(p) for p in [stage_path,replay_path,morphology_path,extraction_path]}
    if review.get('evidence')!=evidence or review.get('files')!=stage['files']:
        raise ValueError('Review does not bind exact stage and reproduction evidence')
    if (replay.get('full_scientific_summary') is not True or replay.get('completed_blocks')!=174 or replay.get('partitions')!=4002
        or replay.get('status')!='REPLAYED_RECORDED_EVENTS' or replay.get('detector_regenerated') is not False
        or replay.get('run_manifest_sha256')!=stage['run_manifest_sha256']
        or replay.get('input_acceptance_sha256')!=stage['files']['repo/results/013/INPUT-ACCEPTANCE.json']['sha256']):
        raise ValueError('Incomplete replay')
    if (morph.get('status')!='MORPHOLOGY_REPRODUCED_FROM_RECORDED_EVENTS' or morph.get('blocks')!=174
        or morph.get('detector_regenerated') is not False
        or type(morph.get('rows')) is not int or morph['rows']<=0 or morph['rows']!=stage.get('morphology_rows')
        or morph.get('run_manifest_sha256')!=stage['run_manifest_sha256']
        or morph.get('summary_sha256')!=stage['files']['repo/results/013/summary.json']['sha256']
        or morph.get('index_sha256')!=stage['files']['repo/results/013/analysis.sqlite']['sha256']):
        raise ValueError('Morphology proof missing')
    if extraction.get('status')!='EXTRACTED_AND_VERIFIED' or extraction.get('release_manifest_sha256')!=digest(stage_path):
        raise ValueError('Exact extraction missing')
    expected={n:{k:r[k] for k in ['bytes','sha256']} for n,r in stage['files'].items()}
    if extraction.get('files')!=expected:raise ValueError('Extracted member inventory differs')
    for name,row in stage['assets'].items():
        p=stage_path.parent/name
        if p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise ValueError('Staged asset changed')
    return {'schema':'eegt-013-release-acceptance/v1','status':'ACCEPTED_FOR_PUBLICATION','evidence':evidence,'review_sha256':digest(review_path),'run_manifest_sha256':stage['run_manifest_sha256'],'files':stage['files'],'assets':stage['assets']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['morphology','check-replay','approve']);p.add_argument('--root',type=Path);p.add_argument('--stage',type=Path);p.add_argument('--review',type=Path);p.add_argument('--replay',type=Path);p.add_argument('--morphology',type=Path);p.add_argument('--extraction',type=Path);a=p.parse_args()
    if a.action=='morphology':r=morphology(a.root)
    elif a.action=='check-replay':
        r=json.loads(a.replay.read_text());require_complete_replay(r,a.root)
    else:r=approve(a.stage,a.review,a.replay,a.morphology,a.extraction)
    print(json.dumps(r,sort_keys=True))
