"""Independently reconcile released denominators and derivative/source joins."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def run():
    checks=[]
    def check(name,ok):
        if not bool(ok):raise AssertionError(name)
        checks.append(name)
    read=lambda name:json.loads((ROOT/name).read_text())
    manifest=read('protocol/corpus-manifest-v1.json');c=read('results/corpus-v1/summary.json');features=read('results/003/features.json');main=read('results/003/summary.json');ctrl=read('results/006/summary.json');model=read('results/003/model.json')
    check('manifest source denominator',len(manifest['recordings'])==c['source_recordings'])
    check('source bytes',sum(f['bytes'] for r in manifest['recordings'] for f in r['files'])==c['downloaded_verified_bytes'])
    check('corpus checksum',sha(ROOT/'results/corpus-v1/corpus.sqlite')==c['corpus_sha256'])
    check('analysis checksum',sha(ROOT/'results/003/analysis.sqlite')==main['analysis_sha256'])
    db=sqlite3.connect(ROOT/'results/003/analysis.sqlite');db.row_factory=sqlite3.Row
    check('SQL integrity',db.execute('PRAGMA integrity_check').fetchone()[0]=='ok')
    check('SQL foreign keys',not db.execute('PRAGMA foreign_key_check').fetchall())
    records={r['recording_id']:dict(r) for r in db.execute('SELECT * FROM recordings')}
    check('catalog source denominator',len(records)==c['source_recordings'])
    check('qualification denominator',sum(r['status']=='QUALIFIED' for r in records.values())==c['qualified_recordings'])
    train={r['recording_id'] for r in records.values() if r['split']=='train' and r['status']=='QUALIFIED'}
    check('training participant selection',set(model['train_recordings'])==train)
    measured={r['recording_id']:r for r in main['records']}
    n_windows=n_valid=0
    for row in features['records']:
        rid=row['recording_id'];check(rid+' exists',rid in records)
        if row['status']!='EXTRACTED':continue
        check(rid+' derivative hash',sha(ROOT/row['path'])==row['sha256'])
        with np.load(ROOT/row['path'],allow_pickle=False) as z:
            times=z['times'];valid=z['valid'];segments=z['segment']
            check(rid+' counts',len(times)==row['windows'] and int(valid.sum())==row['valid_windows'])
            check(rid+' positive times',np.isfinite(times).all() and np.all(np.diff(times)>0))
            for view in ['morphology','spectrum','coordination']:
                x=z[view];check(rid+' '+view+' validity',len(x)==len(times) and np.isfinite(x[valid]).all() and np.isnan(x[~valid]).all())
            for segment in row['segments']:
                t=times[segments==segment['segment']]
                if not len(t):continue
                sf=records[rid]['sample_rate_hz']
                check(rid+f" segment {segment['segment']} support",t.min()-1>=segment['start_sample']/sf-1e-8 and t.max()+1<=segment['stop_sample']/sf+1e-8)
                check(rid+f" segment {segment['segment']} grid",len(t)<2 or np.allclose(np.diff(t),.5,rtol=0,atol=1e-8))
            n_windows+=len(times);n_valid+=int(valid.sum())
        check(rid+' result exposure',measured[rid]['windows']==row['windows'] and measured[rid]['valid_windows']==row['valid_windows'])
        for key,metric in measured[rid]['event_counts'].items():
            view,scale=key.split(':')
            count=db.execute('SELECT COUNT(*) FROM transition_events WHERE recording_id=? AND view=? AND scale_seconds=?',(rid,view,float(scale))).fetchone()[0]
            check(rid+' '+key+' event denominator',count==metric['count'])
            exposure=metric['scored_center_seconds']/60
            check(rid+' '+key+' rate',(metric['events_per_scored_minute'] is None and not exposure) or (exposure>0 and np.isclose(metric['events_per_scored_minute'],count/exposure)))
    check('all window totals',n_windows==main['totals']['windows'] and n_valid==main['totals']['valid_windows'])
    check('control source denominator',len(ctrl['records'])==len(records))
    for r in ctrl['records']:
        if r['status']!='EVALUATED':continue
        check(r['recording_id']+' all controls',set(r['variants'])=={'original','independent_phase','shared_phase','gain_1.1','polarity_reverse','time_reverse'})
        for variant,v in r['variants'].items():
            check(r['recording_id']+' '+variant+' validity',0<=v['valid_windows']<=v['windows'])
            pair=v.get('paired_support')
            if pair:
                check(r['recording_id']+' '+variant+' matched context denominator',pair['original']['windows_scored']==pair['variant']['windows_scored'])
    db.close()
    result=dict(schema='eegt-growth-audit/v1',status='PASS',checks=len(checks),check_names=checks,windows=n_windows,valid_windows=n_valid,limitations='Numerical/source-join audit, not biological validation or a substitute for independent review.')
    out=ROOT/'results/007/audit.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='check_names'}))


if __name__=='__main__':run()
