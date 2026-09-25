"""Streaming, provenance-bound transition experiment on the continuous corpus.

The curator retains source identity; the imported numerical methods see only
arrays, time coordinates, validity and frozen training parameters.
"""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import combinations
import json
from pathlib import Path
import shutil
import sqlite3

import mne
import numpy as np
from threadpoolctl import threadpool_limits

from .acquire import ROOT, digest
from .corpus import atomic_json, canonical_json, safe_path
from . import transitions as methods

VIEWS = ('morphology', 'spectrum', 'coordination')


def continuous_intervals(n_samples, boundaries):
    """Preserve a zero-length boundary as a split; omit positive BAD/gap spans."""
    cursor = 0
    result = []
    for start, stop in sorted(boundaries):
        if start < 0 or stop < start or stop > n_samples:
            raise ValueError('invalid native discontinuity')
        if start > cursor:
            result.append((cursor, start))
        cursor = max(cursor, stop)
    if cursor < n_samples:
        result.append((cursor, n_samples))
    return result


def json_ready(value):
    if isinstance(value, dict): return {str(k):json_ready(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [json_ready(v) for v in value]
    if isinstance(value, np.ndarray): return json_ready(value.tolist())
    if isinstance(value, np.generic): return json_ready(value.item())
    if isinstance(value, float) and not np.isfinite(value): return None
    return value


def input_identity(root):
    names = ['protocol/experiment-003.json', 'protocol/corpus-v1.json',
             'protocol/corpus-manifest-v1.json', 'results/corpus-v1/corpus.sqlite',
             'results/corpus-v1/summary.json', 'eegt/transitions.py', 'eegt/growth.py',
             'results/corpus-v1/calibration.json', 'eegt/calibrate.py',
             'requirements.lock']
    return {p:digest(root/p) for p in names}


def catalog(root):
    conn=sqlite3.connect(root/'results/corpus-v1/corpus.sqlite')
    conn.row_factory=sqlite3.Row
    records=[dict(r) for r in conn.execute('SELECT * FROM recordings ORDER BY dataset_id,source_subject')]
    return conn,records


def source_raw(root, conn, rec):
    files=[dict(r) for r in conn.execute('SELECT * FROM source_files WHERE recording_id=? ORDER BY path',(rec['recording_id'],))]
    for f in files:
        path=safe_path(root/'data/cache'/rec['dataset_id'],f['path'])
        if path.stat().st_size!=f['bytes'] or digest(path)!=f['sha256']:
            raise ValueError('raw source identity changed after qualification')
    f=next(f for f in files if f['path'].endswith('.set'))
    raw=mne.io.read_raw_eeglab(safe_path(root/'data/cache'/rec['dataset_id'],f['path']),preload=False,verbose='ERROR')
    channels=[dict(r) for r in conn.execute('SELECT * FROM channels WHERE recording_id=? ORDER BY channel_index',(rec['recording_id'],))]
    picks=[raw.ch_names.index(c['name']) for c in channels if c['type'].upper()=='EEG' and c['status'].lower()!='bad']
    if len(picks)<2: raw.close(); raise ValueError('fewer than two usable source EEG channels')
    gaps=conn.execute('SELECT start_sample,stop_sample FROM discontinuities WHERE recording_id=?',(rec['recording_id'],)).fetchall()
    return raw,picks,continuous_intervals(raw.n_times,[(r[0],r[1]) for r in gaps])


def extract_record(root, conn, rec, protocol):
    raw,picks,intervals=source_raw(root,conn,rec)
    sf=float(raw.info['sfreq'])
    chunk=int(round(protocol['chunk_seconds']*sf)); halo=int(round(protocol['halo_seconds']*sf))
    arrays=defaultdict(list); segment_rows=[]
    try:
        for seg,(start,stop) in enumerate(intervals):
            if stop-start < round(protocol['window_seconds']*sf): continue
            segment_rows.append(dict(segment=seg,start_sample=start,stop_sample=stop))
            for core in range(start,stop,chunk):
                end=min(stop,core+chunk); left=max(start,core-halo); right=min(stop,end+halo)
                if right-left<round(protocol['window_seconds']*sf): continue
                samples=raw.get_data(picks=picks,start=left,stop=right)*1e6
                out=methods.extract_features(samples,sf,window_seconds=protocol['window_seconds'],hop_seconds=protocol['hop_seconds'])
                times=out['times']+left/sf
                keep=(times>=core/sf)&(times<end/sf)
                arrays['times'].append(times[keep]); arrays['valid'].append(out['valid'][keep])
                arrays['segment'].append(np.full(int(keep.sum()),seg,dtype=np.int32))
                for view in VIEWS: arrays[view].append(out['views'][view][keep])
        if not arrays['times']: raise ValueError('no two-second windows in native continuous intervals')
        packed={k:np.concatenate(v,axis=0) for k,v in arrays.items()}
        if len(packed['times'])>1 and not np.all(np.diff(packed['times'])>0): raise ValueError('overlapping or unordered feature times')
        outdir=root/'data/derived/003';outdir.mkdir(parents=True,exist_ok=True)
        path=outdir/(rec['recording_id']+'.npz')
        with path.with_suffix('.partial').open('wb') as f: np.savez_compressed(f,**packed)
        path.with_suffix('.partial').replace(path)
        return dict(recording_id=rec['recording_id'],status='EXTRACTED',path=str(path.relative_to(root)),
                    sha256=digest(path),windows=len(packed['times']),valid_windows=int(packed['valid'].sum()),
                    analyzed_channels=len(picks),segments=segment_rows,
                    continuous_sample_seconds=sum(b-a for a,b in intervals)/sf,
                    window_center_exposure_seconds=len(packed['times'])*protocol['hop_seconds'],
                    valid_window_center_exposure_seconds=int(packed['valid'].sum())*protocol['hop_seconds'],
                    feature_names=out['feature_names'],feature_metadata=out['metadata'])
    finally: raw.close()


def extract_one(root, rec, protocol):
    conn,_=catalog(root)
    try:
        with threadpool_limits(limits=1): return extract_record(root,conn,rec,protocol)
    except (ValueError,OSError) as exc:
        return dict(recording_id=rec['recording_id'],status='FAILED',reason=str(exc))
    finally: conn.close()


def extract(root=ROOT, workers=1):
    root=Path(root); p=json.loads((root/'protocol/experiment-003.json').read_text())
    receipt=root/'results/003/features.json'; identity=input_identity(root)
    saved=json.loads(receipt.read_text()) if receipt.exists() else dict(schema='eegt-feature-receipt/v1',inputs=identity,records=[])
    if saved['inputs']!=identity: raise ValueError('inputs changed; preserve prior run and use a fresh output directory')
    done={r['recording_id']:r for r in saved['records']}
    conn,records=catalog(root);conn.close()
    if workers<1: raise ValueError('workers must be positive')
    todo=[]
    for rec in records:
        rid=rec['recording_id']
        if rid in done:
            old=done[rid]
            if old['status']=='EXTRACTED' and digest(root/old['path'])!=old['sha256']: raise ValueError('feature cache changed')
        elif rec['status']!='QUALIFIED':
            saved['records'].append(dict(recording_id=rid,status='SOURCE_QUARANTINED',reason=rec['reason']))
        else: todo.append(rec)
    # One process owns each recording's feature file; only this parent writes
    # the run receipt. BLAS stays single-threaded in every numerical process.
    with ProcessPoolExecutor(max_workers=workers) as pool:
        pending=[pool.submit(extract_one,root,rec,p) for rec in todo]
        for future in as_completed(pending):
            row=future.result(); saved['records'].append(row)
            atomic_json(receipt,json_ready(saved))
            print(json.dumps({k:v for k,v in row.items() if k not in ['segments','feature_names','feature_metadata']}),flush=True)
    saved['records'].sort(key=lambda r:r['recording_id'])
    saved['completed']=True
    atomic_json(receipt,json_ready(saved))
    return saved


def verified_features(root):
    receipt=json.loads((root/'results/003/features.json').read_text())
    if not receipt.get('completed') or receipt['inputs']!=input_identity(root): raise ValueError('unsealed or changed feature run')
    conn,records=catalog(root);conn.close()
    expected={r['recording_id']:r for r in records}
    calibration=json.loads((root/'results/corpus-v1/calibration.json').read_text())
    cal={r['recording_id']:r['status'] for r in calibration['records']}
    if calibration['corpus_sha256']!=digest(root/'results/corpus-v1/corpus.sqlite') or set(cal)!=set(expected) or any(cal[rid]!='PASS' for rid,r in expected.items() if r['status']=='QUALIFIED'):raise ValueError('digital unit calibration is not verified for the qualified corpus')
    ids=[r['recording_id'] for r in receipt['records']]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected): raise ValueError('feature receipt must contain every catalog record exactly once')
    for r in receipt['records']:
        rid=r['recording_id'];qualified=expected[rid]['status']=='QUALIFIED'
        if r['status'] not in ('EXTRACTED','FAILED','SOURCE_QUARANTINED'): raise ValueError('invalid feature status')
        if qualified == (r['status']=='SOURCE_QUARANTINED'): raise ValueError('feature status disagrees with source catalog')
        if r['status']=='EXTRACTED':
            if r['path']!=f'data/derived/003/{rid}.npz' or digest(root/r['path'])!=r['sha256']: raise ValueError('feature identity mismatch')
        elif not r.get('reason'): raise ValueError('non-extracted record requires a reason')
    return receipt


def load_features(root, row):
    with np.load(root/row['path'],allow_pickle=False) as z: return {k:z[k] for k in z.files}


def segments(arrays):
    for seg in np.unique(arrays['segment']):
        ix=arrays['segment']==seg
        yield int(seg), {k:v[ix] for k,v in arrays.items()}


def fit(root, records, feature_rows, protocol):
    pools={v:[] for v in VIEWS}
    train=[r for r in records if r['split']=='train' and r['recording_id'] in feature_rows]
    for r in train:
        a=load_features(root,feature_rows[r['recording_id']]); valid=np.flatnonzero(a['valid'])
        take=valid[np.linspace(0,len(valid)-1,min(len(valid),protocol['fit']['maximum_feature_rows_per_recording']),dtype=int)] if len(valid) else valid
        for view in VIEWS: pools[view].append(a[view][take])
    references={v:methods.fit_reference(pools[v]) for v in VIEWS}
    scores={v:defaultdict(list) for v in VIEWS}
    for r in train:
        a=load_features(root,feature_rows[r['recording_id']]); per={v:defaultdict(list) for v in VIEWS}
        for _,s in segments(a):
            if len(s['times'])<2: continue
            for v in VIEWS:
                out=methods.boundary_scores(s[v],s['times'],s['valid'],references[v],scales_seconds=tuple(protocol['boundary']['scales_seconds']))
                for scale,arr in out.items(): per[v][scale].append(arr[np.isfinite(arr)])
        for v in VIEWS:
            for scale,parts in per[v].items():
                x=np.concatenate(parts)
                take=np.linspace(0,len(x)-1,min(len(x),protocol['fit']['maximum_feature_rows_per_recording']),dtype=int) if len(x) else []
                scores[v][scale].append(x[take])
    thresholds={v:{scale:float(np.quantile(np.concatenate(parts),protocol['fit']['threshold_quantile'])) for scale,parts in scores[v].items()} for v in VIEWS}
    return references, thresholds, [r['recording_id'] for r in train]


def evaluate_arrays(a, references, thresholds, protocol):
    events=[]; scores_count=defaultdict(int); agreements=[]
    for seg,s in segments(a):
        if len(s['times'])<2: continue
        found={}
        for v in VIEWS:
            scores=methods.boundary_scores(s[v],s['times'],s['valid'],references[v],scales_seconds=tuple(protocol['boundary']['scales_seconds']))
            for scale,x in scores.items():
                ids=methods.select_boundaries(x,s['times'],threshold=thresholds[v][scale],min_separation_seconds=protocol['boundary']['minimum_separation_seconds'])
                found[v,scale]=s['times'][ids]
                scores_count[f'{v}:{scale}']+=int(np.isfinite(x).sum())
                geometry=methods.transition_geometry(s[v],s['times'],s['valid'],references[v],ids,context_seconds=2)
                geom={int(g['index']):g for g in geometry}
                for idx in ids:
                    events.append(dict(view=v,scale=scale,segment=seg,index=int(idx),time=float(s['times'][idx]),score=float(x[idx]),geometry=geom.get(int(idx))))
        for scale in thresholds[VIEWS[0]]:
            for va,vb in combinations(VIEWS,2):
                m=methods.match_boundaries(found[va,scale],found[vb,scale],tolerance_seconds=protocol['boundary']['match_tolerance_seconds'])
                agreements.append(dict(segment=seg,scale=scale,view_a=va,view_b=vb,**m))
    return events,dict(scores_count),agreements


def bootstrap(values, seed=17):
    x=np.asarray([v for v in values if v is not None and np.isfinite(v)],dtype=float)
    if not len(x): return dict(n=0,median=None,ci95=None)
    ci=None
    if len(x)>1:
        rng=np.random.default_rng(seed)
        sims=np.median(rng.choice(x,size=(1000,len(x)),replace=True),axis=1)
        ci=np.quantile(sims,[.025,.975]).tolist()
    return dict(n=len(x),median=float(np.median(x)),ci95=ci)


def evaluate(root=ROOT):
    root=Path(root);p=json.loads((root/'protocol/experiment-003.json').read_text());receipt=verified_features(root)
    rows={r['recording_id']:r for r in receipt['records'] if r['status']=='EXTRACTED'}
    conn,records=catalog(root)
    references,thresholds,trained=fit(root,records,rows,p)
    out=root/'results/003';out.mkdir(parents=True,exist_ok=True)
    final=out/'analysis.sqlite'
    if final.exists(): raise ValueError('analysis is immutable; retain previous result before a new run')
    temp=out/'analysis.sqlite.partial';shutil.copyfile(root/'results/corpus-v1/corpus.sqlite',temp)
    db=sqlite3.connect(temp);db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''CREATE TABLE feature_files(recording_id TEXT PRIMARY KEY REFERENCES recordings(recording_id),path TEXT,sha256 TEXT,windows INTEGER,valid_windows INTEGER,receipt_json TEXT);
    CREATE TABLE transition_events(recording_id TEXT REFERENCES recordings(recording_id),view TEXT,scale_seconds REAL,segment INTEGER,time_seconds REAL,score REAL,geometry_json TEXT);
    CREATE INDEX event_lookup ON transition_events(recording_id,view,scale_seconds,time_seconds);
    CREATE TABLE analysis_metrics(recording_id TEXT REFERENCES recordings(recording_id),kind TEXT,metrics_json TEXT);
    CREATE TABLE model_reference(view TEXT PRIMARY KEY,parameters_json TEXT,thresholds_json TEXT);
    ''')
    for view in VIEWS: db.execute('INSERT INTO model_reference VALUES (?,?,?)',(view,canonical_json(json_ready(references[view])),canonical_json(thresholds[view])))
    summaries=[]
    try:
        for rec in records:
            rid=rec['recording_id']
            if rid not in rows: continue
            row=rows[rid];a=load_features(root,row)
            events,scored,agreement=evaluate_arrays(a,references,thresholds,p)
            db.execute('INSERT INTO feature_files VALUES (?,?,?,?,?,?)',(rid,row['path'],row['sha256'],row['windows'],row['valid_windows'],canonical_json(row)))
            db.executemany('INSERT INTO transition_events VALUES (?,?,?,?,?,?,?)',[(rid,e['view'],float(e['scale']),e['segment'],e['time'],e['score'],canonical_json(json_ready(e['geometry']))) for e in events])
            metrics=dict(recording_id=rid,dataset=rec['dataset_id'],split=rec['split'],prior_exposure=bool(rec['prior_exposure']),windows=row['windows'],valid_windows=row['valid_windows'],event_counts={},scored_windows=scored,agreement=agreement)
            for view in VIEWS:
                for scale in thresholds[view]:
                    key=f'{view}:{scale}'; count=sum(e['view']==view and e['scale']==scale for e in events)
                    metrics['event_counts'][key]=dict(count=count,scored_center_seconds=scored.get(key,0)*p['hop_seconds'],events_per_scored_minute=count/(scored[key]*p['hop_seconds']/60) if scored.get(key) else None)
            db.execute('INSERT INTO analysis_metrics VALUES (?,?,?)',(rid,'main',canonical_json(json_ready(metrics))))
            summaries.append(metrics); db.commit()
            print(json.dumps(dict(recording_id=rid,phase='evaluated',windows=row['windows'],events=len(events))),flush=True)
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('analysis database integrity failed')
    finally: db.close();conn.close()
    temp.replace(final)
    model=dict(schema='eegt-transition-reference/v1',train_recordings=trained,references=references,thresholds=thresholds)
    atomic_json(out/'model.json',json_ready(model),immutable=True)
    status_rows=[dict(recording_id=r['recording_id'],dataset=r['dataset_id'],split=r['split'],prior_exposure=bool(r['prior_exposure']),**{k:v for k,v in next(f for f in receipt['records'] if f['recording_id']==r['recording_id']).items() if k in ('status','reason')}) for r in records]
    result=dict(schema='eegt-transition-results/v1',inputs=receipt['inputs'],features_receipt_sha256=digest(out/'features.json'),analysis_sha256=digest(final),records=summaries,record_statuses=status_rows,train_recordings=trained,
                totals=dict(source_recordings=len(records),analyzed_recordings=len(summaries),windows=sum(r['windows'] for r in summaries),valid_windows=sum(r['valid_windows'] for r in summaries)))
    atomic_json(out/'summary.json',json_ready(result),immutable=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['extract','evaluate']);parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--workers',type=int,default=1);args=parser.parse_args()
    with threadpool_limits(limits=1):
        if args.action=='extract': extract(args.root,workers=args.workers)
        else: evaluate(args.root)
