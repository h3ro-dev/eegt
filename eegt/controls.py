"""Matched-source nuisance and Fourier-phase controls for Experiment 003."""
import argparse
import json
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from .acquire import ROOT,digest
from .corpus import atomic_json
from .growth import VIEWS,catalog,source_raw,json_ready,evaluate_arrays,verified_features
from . import transitions as methods


def pack(samples,sf,p,reverse_grid=False):
    f=methods.extract_features(samples,sf,window_seconds=p['window_seconds'],hop_seconds=p['hop_seconds'])
    t=f['times']; halo=p['halo_seconds']; duration=p['controls']['maximum_seconds_per_recording']
    keep=(t>halo)&(t<=halo+duration) if reverse_grid else (t>=halo)&(t<halo+duration)
    return dict(times=t[keep]-halo,valid=f['valid'][keep],segment=np.zeros(keep.sum(),dtype=np.int32),**{v:f['views'][v][keep] for v in VIEWS})


def reduce_events(events,scored,agreement,p):
    out=dict(windows_scored=scored,agreement=agreement,event_counts={},primary_event_times={})
    for key,n in scored.items():
        view,scale=key.split(':'); times=[e['time'] for e in events if e['view']==view and e['scale']==scale]
        out['event_counts'][key]=dict(count=len(times),scored_center_seconds=n*p['hop_seconds'],events_per_scored_minute=len(times)/(n*p['hop_seconds']/60) if n else None)
        if float(scale)==p['boundary']['primary_scale_seconds']: out['primary_event_times'][view]=times
    return out


def cached_row(path,inputs,index,recording_id):
    expected=index['files'].get(path.name)
    if not expected or digest(path)!=expected:raise ValueError('unbound or altered cached control row')
    saved=json.loads(path.read_text())
    if saved['inputs']!=inputs or saved['result']['recording_id']!=recording_id:raise ValueError('control row identity mismatch')
    row=saved['result']
    if row['status']=='EVALUATED' and set(row['variants'])!={'original','independent_phase','shared_phase','gain_1.1','polarity_reverse','time_reverse'}:raise ValueError('incomplete cached control variants')
    return row


def run(root=ROOT):
    root=Path(root); verified_features(root)
    p=json.loads((root/'protocol/experiment-003.json').read_text());model=json.loads((root/'results/003/model.json').read_text())
    refs={v:{k:np.asarray(x) if isinstance(x,list) else x for k,x in r.items()} for v,r in model['references'].items()}
    thresholds=model['thresholds'];conn,records=catalog(root)
    out=root/'results/006';out.mkdir(parents=True,exist_ok=True)
    inputs={s:digest(root/s) for s in ['protocol/experiment-003.json','results/003/model.json','results/003/features.json','results/003/summary.json','eegt/transitions.py','eegt/controls.py']}
    index_path=out/'row-receipt.json'
    index=json.loads(index_path.read_text()) if index_path.exists() else dict(inputs=inputs,files={})
    if index['inputs']!=inputs:raise ValueError('control run inputs changed')
    result=dict(schema='eegt-transition-controls/v1',inputs=inputs,records=[])
    for rec in records:
        rid=rec['recording_id'];path=out/(rid+'.json')
        if path.exists():
            result['records'].append(cached_row(path,inputs,index,rid));continue
        row=dict(recording_id=rid,dataset=rec['dataset_id'],split=rec['split'],prior_exposure=bool(rec['prior_exposure']),status='INSUFFICIENT_CONTEXT')
        raw=None
        if rec['status']=='QUALIFIED':
            try:
                raw,picks,intervals=source_raw(root,conn,rec);sf=float(raw.info['sfreq'])
                needed=round((2*p['halo_seconds']+p['controls']['maximum_seconds_per_recording'])*sf)
                region=next(((a,a+needed) for a,b in intervals if b-a>=needed),None)
                if region:
                    a,b=region;samples=raw.get_data(picks=picks,start=a,stop=b)*1e6
                    original=pack(samples,sf,p); row.update(status='EVALUATED',start_sample=a,stop_sample=b,sample_rate_hz=sf,central_seconds=p['controls']['maximum_seconds_per_recording'],variants={})
                    for variant in p['controls']['variants']:
                        if variant=='original': x=samples
                        elif variant=='independent_phase': x=methods.phase_surrogate(samples,seed=p['controls']['seed'],shared_phase=False)
                        elif variant=='shared_phase': x=methods.phase_surrogate(samples,seed=p['controls']['seed'],shared_phase=True)
                        elif variant=='gain_1.1': x=samples*1.1
                        elif variant=='polarity_reverse': x=-samples
                        elif variant=='time_reverse': x=samples[:,::-1]
                        else: raise ValueError('unsupported preregistered control')
                        ar=original if variant=='original' else pack(x,sf,p,reverse_grid=variant=='time_reverse')
                        ev,sc,ag=evaluate_arrays(ar,refs,thresholds,p)
                        metrics=reduce_events(ev,sc,ag,p);metrics.update(windows=len(ar['times']),valid_windows=int(ar['valid'].sum()))
                        # Equal-support event-rate comparisons for surrogates and gain/polarity.
                        # Reversal changes the time coordinate and is reported separately.
                        if variant!='time_reverse':
                            mask=original['valid']&ar['valid']; ref={**original,'valid':mask}; other={**ar,'valid':mask}
                            e1,s1,g1=evaluate_arrays(ref,refs,thresholds,p);e2,s2,g2=evaluate_arrays(other,refs,thresholds,p)
                            m1=reduce_events(e1,s1,g1,p);m2=reduce_events(e2,s2,g2,p)
                            metrics['paired_support']=dict(valid_windows=int(mask.sum()),original=m1,variant=m2)
                            metrics['same_view_timing']={v:methods.match_boundaries(m1['primary_event_times'].get(v,[]),m2['primary_event_times'].get(v,[]),tolerance_seconds=p['boundary']['match_tolerance_seconds']) for v in VIEWS}
                        else:
                            duration=p['controls']['maximum_seconds_per_recording'];hop=p['hop_seconds']
                            if not np.allclose(original['times'],duration-ar['times'][::-1],rtol=0,atol=1e-9):raise ValueError('reversed center grid does not align')
                            base_ev,base_sc,base_ag=evaluate_arrays(original,refs,thresholds,p)
                            base=reduce_events(base_ev,base_sc,base_ag,p)
                            metrics['reflected_timing']={v:methods.match_boundaries(base['primary_event_times'].get(v,[]),np.sort(duration-np.asarray(metrics['primary_event_times'].get(v,[]))+hop),tolerance_seconds=p['boundary']['match_tolerance_seconds']) for v in VIEWS}
                            mask=original['valid']&ar['valid'][::-1]
                            e1,s1,g1=evaluate_arrays({**original,'valid':mask},refs,thresholds,p)
                            e2,s2,g2=evaluate_arrays({**ar,'valid':mask[::-1]},refs,thresholds,p)
                            m1=reduce_events(e1,s1,g1,p);m2=reduce_events(e2,s2,g2,p)
                            metrics['paired_support']=dict(valid_windows=int(mask.sum()),original=m1,variant=m2)
                            metrics['paired_reflected_timing']={v:methods.match_boundaries(m1['primary_event_times'].get(v,[]),np.sort(duration-np.asarray(m2['primary_event_times'].get(v,[]))+hop),tolerance_seconds=p['boundary']['match_tolerance_seconds']) for v in VIEWS}
                            metrics['reflection_note']='Reverse centers use the reflected original window grid. Reflect boundary labels as duration-time+hop because a boundary is labeled by its post-change window center. Paired results use reflected common validity; the unpaired result is retained separately.'
                        row['variants'][variant]=metrics
            except (ValueError,OSError) as exc: row.update(status='FAILED',reason=str(exc))
            finally:
                if raw is not None: raw.close()
        else: row.update(status='SOURCE_QUARANTINED',reason=rec['reason'])
        atomic_json(path,json_ready(dict(inputs=inputs,result=row)),immutable=True)
        index['files'][path.name]=digest(path)
        atomic_json(index_path,index)
        result['records'].append(row)
        print(json.dumps(dict(recording_id=rid,status=row['status'])),flush=True)
    conn.close()
    result['evaluated_recordings']=sum(r['status']=='EVALUATED' for r in result['records'])
    result['candidate_recordings']=len(records)
    result['row_files']=index['files']
    result['row_receipt_sha256']=digest(index_path)
    atomic_json(out/'summary.json',json_ready(result),immutable=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT);args=parser.parse_args()
    with threadpool_limits(limits=1): run(args.root)
