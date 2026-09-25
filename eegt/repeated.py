"""Experiment 008 curator and paired evaluator; earlier experiments are immutable."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import io
import itertools
import json
from pathlib import Path
import re
import shutil
import sqlite3
import warnings
import zipfile

import mne
from mne._fiff.constants import FIFF
import numpy as np
from scipy.io import loadmat
from threadpoolctl import threadpool_limits

from .acquire import ROOT, digest
from .corpus import atomic_json, canonical_json, annex_identity, fetch, parse_channels, acquire_file, safe_path
from .growth import continuous_intervals, json_ready, segments, VIEWS
from . import transitions as methods


def read_json(path):
    return json.loads(Path(path).read_text())


def freeze(root=ROOT):
    root = Path(root)
    p = read_json(root/'protocol/experiment-008.json')
    output = root/'protocol/corpus-manifest-008.json'
    if output.exists():
        result = read_json(output)
        if result['protocol_sha256'] != digest(root/'protocol/experiment-008.json'):
            raise ValueError('protocol changed after metadata freeze')
        return result
    src = p['source']; ds, commit = src['dataset'], src['commit']
    archive = fetch(f'https://codeload.github.com/OpenNeuroDatasets/{ds}/zip/{commit}')
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        files = {n.split('/', 1)[1]: n for n in z.namelist() if '/' in n and not n.endswith('/')}
        def read(path): return z.read(files[path]).decode('utf-8-sig')
        description = json.loads(read('dataset_description.json'))
        if description['License'] != src['license']:
            raise ValueError('source license mismatch')
        records = []
        reserved = []
        for path in sorted(files):
            if not path.endswith('_acq-earEEG_eeg.set'): continue
            subject = re.search(r'sub-([^/]+)', path)[1]
            session = re.search(r'ses-([^/]+)', path)[1]
            if subject not in p['subjects'] or session not in p['sessions']:
                reserved.append(dict(path=path, source_subject=subject, session=session))
                continue
            prefix = path[:-len('_eeg.set')]
            meta = json.loads(read(prefix+'_eeg.json'))
            channel_text = read(prefix+'_channels.tsv')
            ident = annex_identity(read(path))
            records.append(dict(recording_id=hashlib.sha256(f'{ds}:{commit}:{path}'.encode()).hexdigest()[:24],
                source_subject=subject, session=session, metadata=meta, channels=parse_channels(channel_text),
                metadata_sha256=hashlib.sha256(canonical_json(meta).encode()).hexdigest(),
                channels_sha256=hashlib.sha256(channel_text.encode()).hexdigest(),
                file=dict(path=path, **ident, url=f'https://s3.amazonaws.com/openneuro.org/{ds}/{path}')))
        expected = set(itertools.product(p['subjects'], p['sessions']))
        observed = [(r['source_subject'], r['session']) for r in records]
        if len(observed) != len(expected) or set(observed) != expected:
            raise ValueError('selected source pairs are incomplete or duplicated')
        total = sum(r['file']['bytes'] for r in records)
        if total > p['maximum_download_bytes']: raise ValueError('download exceeds frozen bound')
        result = dict(schema='eegt-repeat-manifest/v1', frozen_at=datetime.now(timezone.utc).isoformat(),
            protocol_sha256=digest(root/'protocol/experiment-008.json'), source=src,
            archive_sha256=hashlib.sha256(archive).hexdigest(), description=description,
            readme=read('README'), records=records, reserved=reserved, total_download_bytes=total)
    atomic_json(output, result, immutable=True)
    return result


def acquire(root=ROOT):
    root = Path(root); manifest = freeze(root)
    rows = []
    for rec in manifest['records']:
        f = rec['file']; path = safe_path(root/'data/cache'/manifest['source']['dataset'], f['path'])
        sha = acquire_file(f, path)
        rows.append(dict(recording_id=rec['recording_id'], path=str(path.relative_to(root)), sha256=sha, bytes=path.stat().st_size))
        atomic_json(root/'results/008/acquisition.json', dict(schema='eegt-repeat-acquisition/v1',
            manifest_sha256=digest(root/'protocol/corpus-manifest-008.json'), completed=False, records=rows))
        print(json.dumps(dict(phase='acquired', **rows[-1])), flush=True)
    atomic_json(root/'results/008/acquisition.json', dict(schema='eegt-repeat-acquisition/v1',
        manifest_sha256=digest(root/'protocol/corpus-manifest-008.json'), completed=True, records=rows))
    return rows


def qualify_record(path, rec, protocol):
    """Check technical consistency and digital conversion; return no wave samples."""
    declared = rec['channels']
    if [c['name'] for c in declared] != protocol['expected_channels']:
        raise ValueError('ear-channel allowlist differs from frozen source contract')
    if any(c['type'].upper() != 'EEG' or c['units'] != 'uV' for c in declared):
        raise ValueError('declared EEG microvolt units required')
    meta = rec['metadata']
    if meta['EEGReference'] != 'average' or meta['SamplingFrequency'] != protocol['expected_sample_rate_hz']:
        raise ValueError('source rate/reference mismatch')
    native = loadmat(path, simplify_cells=True)
    native = native.get('EEG', native)
    if native['trials'] != 1 or native['data'].ndim != 2:
        raise ValueError('continuous embedded EEG required')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        raw = mne.io.read_raw_eeglab(path, preload=True, verbose='ERROR')
    try:
        sf = float(raw.info['sfreq']); count = int(raw.n_times)
        if sf != meta['SamplingFrequency'] or native['srate'] != sf:
            raise ValueError('decoded rate mismatch')
        if native['data'].shape != (len(raw.ch_names), count) or native['pnts'] != count:
            raise ValueError('native/decoded shape mismatch')
        names = [c['labels'] for c in native['chanlocs']]
        if names != raw.ch_names or len(set(names)) != len(names):
            raise ValueError('native/decoded channel ordering mismatch')
        picks = [raw.ch_names.index(c['name']) for c in declared]
        if any(raw.info['chs'][i]['unit'] != FIFF.FIFF_UNIT_V for i in picks):
            raise ValueError('decoder does not declare volts')
        delta = count - float(meta['RecordingDuration'])*sf
        if abs(delta) > 1.01: raise ValueError('duration differs by more than one sample')
        if count < round(protocol['analysis_seconds']*sf):
            raise ValueError('shorter than frozen four-hour analysis interval')
        errors = []; checked = 0
        for start in sorted(set([0, max(0, count//2-16), max(0, count-32)])):
            stop = min(count, start+32)
            direct = np.asarray(native['data'][picks, start:stop], dtype=float)
            decoded = raw.get_data(picks=picks, start=start, stop=stop)*1e6
            finite = np.isfinite(direct)
            if not np.array_equal(finite, np.isfinite(decoded)):
                raise ValueError('native/decoded finite masks differ')
            if not np.allclose(direct[finite], decoded[finite], rtol=1e-12, atol=1e-9):
                raise ValueError('native microvolt conversion mismatch')
            checked += int(finite.sum())
            errors.append(float(np.max(np.abs(direct[finite]-decoded[finite]))) if finite.any() else 0.)
        if not checked: raise ValueError('no finite native values in digital calibration probes')
        gaps = []
        for onset, span, desc in zip(raw.annotations.onset, raw.annotations.duration, raw.annotations.description, strict=True):
            if 'boundary' in desc.lower() or desc.lower().startswith('bad'):
                a = max(0, min(count, int(np.floor(onset*sf))))
                b = max(a, min(count, int(np.ceil((onset+max(0, span))*sf))))
                gaps.append([a,b])
        return dict(sample_rate_hz=sf, samples_per_channel=count, duration_seconds=count/sf,
            duration_metadata_error_samples=delta, channels=[raw.ch_names[i] for i in picks],
            excluded_undeclared_channels=[n for n in names if n not in protocol['expected_channels']],
            native_nonfinite_samples_by_channel={raw.ch_names[i]:int((~np.isfinite(native['data'][i])).sum()) for i in picks},
            gaps=gaps, decoder_warnings=[str(w.message) for w in caught],
            digital_conversion=dict(checked_values=checked, maximum_absolute_error_uv=max(errors),
                decoder_unit='V', factor_to_uv=1e6, physical_calibration_verified=False))
    finally:
        raw.close()


def qualify(root=ROOT):
    root = Path(root); p = read_json(root/'protocol/experiment-008.json'); manifest = freeze(root)
    acq = read_json(root/'results/008/acquisition.json')
    if not acq['completed'] or acq['manifest_sha256'] != digest(root/'protocol/corpus-manifest-008.json'):
        raise ValueError('source acquisition is incomplete or manifest changed')
    rows = []
    for rec in manifest['records']:
        f = rec['file']; path = safe_path(root/'data/cache'/p['source']['dataset'], f['path'])
        if path.stat().st_size != f['bytes'] or digest(path,f['algorithm']) != f['expected_digest']:
            raise ValueError('pinned raw source mismatch')
        row = dict(recording_id=rec['recording_id'], source_subject=rec['source_subject'], session=rec['session'],
            path=str(path.relative_to(root)), sha256=digest(path), bytes=f['bytes'], status='QUALIFIED', reason=None)
        try: row.update(qualify_record(path,rec,p))
        except (ValueError,KeyError,OSError,IndexError) as exc:
            row.update(status='QUARANTINED', reason=f'{type(exc).__name__}: {exc}')
        rows.append(row)
        print(json.dumps(row),flush=True)
    result = dict(schema='eegt-repeat-qualification/v1', records=rows, mne_version=mne.__version__,
        protocol_sha256=digest(root/'protocol/experiment-008.json'),
        manifest_sha256=digest(root/'protocol/corpus-manifest-008.json'))
    atomic_json(root/'results/008/qualification.json',result,immutable=True)
    final = root/'results/008/catalog.sqlite'
    if not final.exists():
        temp = final.with_suffix('.partial'); temp.unlink(missing_ok=True)
        db=sqlite3.connect(temp)
        db.execute('CREATE TABLE recordings(recording_id TEXT PRIMARY KEY,source_subject TEXT,session TEXT,status TEXT,source_sha256 TEXT,receipt_json TEXT,UNIQUE(source_subject,session))')
        db.executemany('INSERT INTO recordings VALUES (?,?,?,?,?,?)',[(r['recording_id'],r['source_subject'],r['session'],r['status'],r['sha256'],canonical_json(r)) for r in rows])
        db.commit();db.close();temp.replace(final)
    return result


def input_identity(root):
    paths=['protocol/experiment-008.json','protocol/corpus-manifest-008.json','results/008/qualification.json',
           'results/008/catalog.sqlite','results/003/model.json','eegt/repeated.py','eegt/transitions.py',
           'eegt/growth.py','eegt/corpus.py','eegt/acquire.py','requirements.lock']
    return {path:digest(root/path) for path in paths}


def extract_record(root, rec, protocol):
    path=root/rec['path']
    if digest(path)!=rec['sha256']: raise ValueError('raw bytes changed after qualification')
    raw=mne.io.read_raw_eeglab(path,preload=True,verbose='ERROR')
    arrays=defaultdict(list)
    try:
        sf=rec['sample_rate_hz']; picks=[raw.ch_names.index(n) for n in rec['channels']]
        limit=int(round(protocol['analysis_seconds']*sf))
        intervals=continuous_intervals(raw.n_times,rec['gaps'])
        intervals=[(a,min(b,limit)) for a,b in intervals if a<limit]
        chunk=int(round(protocol['chunk_seconds']*sf)); halo=int(round(protocol['halo_seconds']*sf))
        for seg,(start,stop) in enumerate(intervals):
            for core in range(start,stop,chunk):
                end=min(stop,core+chunk);left=max(start,core-halo);right=min(stop,end+halo)
                if right-left<round(protocol['window_seconds']*sf):continue
                x=raw.get_data(picks=picks,start=left,stop=right)*1e6
                out=methods.extract_features(x,sf,window_seconds=protocol['window_seconds'],hop_seconds=protocol['hop_seconds'])
                centers2=np.rint(out['times']*sf*2).astype(np.int64)+left*2
                keep=(centers2>=core*2)&(centers2<end*2)
                arrays['times'].append(centers2[keep]/(2*sf)); arrays['valid'].append(out['valid'][keep])
                arrays['segment'].append(np.full(int(keep.sum()),seg,dtype=np.int32))
                for v in VIEWS:arrays[v].append(out['views'][v][keep])
        if not arrays['times']:raise ValueError('no complete feature windows')
        packed={k:np.concatenate(v) for k,v in arrays.items()}
        if np.any(np.diff(packed['times'])<=0):raise ValueError('duplicate or unordered windows')
        dest=root/'data/derived/008'/(rec['recording_id']+'.npz');dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.with_suffix('.partial').open('wb') as f:np.savez_compressed(f,**packed)
        dest.with_suffix('.partial').replace(dest)
        return dict(recording_id=rec['recording_id'],status='EXTRACTED',path=str(dest.relative_to(root)),
            sha256=digest(dest),windows=len(packed['times']),valid_windows=int(packed['valid'].sum()),
            continuous_analyzed_seconds=sum(b-a for a,b in intervals)/sf,
            feature_metadata=out['metadata'],feature_names=out['feature_names'])
    finally:raw.close()


def extract(root=ROOT):
    root=Path(root);p=read_json(root/'protocol/experiment-008.json');identity=input_identity(root)
    if identity['results/003/model.json']!=p['baseline_model']['sha256']:raise ValueError('frozen baseline changed')
    dest=root/'results/008/features.json'
    result=read_json(dest) if dest.exists() else dict(schema='eegt-repeat-features/v1',inputs=identity,records=[])
    if result['inputs']!=identity:raise ValueError('run input changed; preserve prior receipt')
    done={r['recording_id']:r for r in result['records']}
    for rec in read_json(root/'results/008/qualification.json')['records']:
        rid=rec['recording_id']
        if rid in done:
            if done[rid]['status']=='EXTRACTED' and digest(root/done[rid]['path'])!=done[rid]['sha256']:
                raise ValueError('feature bytes changed')
            continue
        if rec['status']!='QUALIFIED':row=dict(recording_id=rid,status='SOURCE_QUARANTINED',reason=rec['reason'])
        else:
            try:row=extract_record(root,rec,p)
            except (ValueError,OSError) as exc:row=dict(recording_id=rid,status='FAILED',reason=str(exc))
        result['records'].append(row);atomic_json(dest,result)
        print(json.dumps({k:v for k,v in row.items() if k not in ('feature_names','feature_metadata')}),flush=True)
    result['completed']=True;atomic_json(dest,result)
    return result


def paired_distances(first, second):
    """Exact paired-summary permutation test; no identifiers enter this function."""
    a,b=np.asarray(first,dtype=float),np.asarray(second,dtype=float)
    if a.ndim!=2 or a.shape!=b.shape or a.shape[1]<1 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('paired finite matrices of the same nonzero width required')
    n=len(a)
    if not 3<=n<=8:raise ValueError('exact paired test requires 3 to 8 pairs')
    d=np.sqrt(np.mean((a[:,None,:]-b[None,:,:])**2,axis=2))
    observed=float(np.diag(d).mean())
    perm=np.array([np.mean(d[np.arange(n),order]) for order in itertools.permutations(range(n))])
    # Equality tolerance protects exact ties against summation-order roundoff.
    p=float(np.count_nonzero(perm<=observed+1e-12)/len(perm))
    off=float(d[~np.eye(n,dtype=bool)].mean())
    return dict(n_pairs=n,distance_matrix=d.tolist(),same_person_mean_distance=observed,
        different_person_mean_distance=off,mean_distance_advantage=off-observed,
        permutation_count=len(perm),permutation_p_lower=p,p_bonferroni_three_views=min(1.,3*p),
        permutation_matched_means=perm.tolist())


def record_metrics(a, model, p):
    events=[];scored=defaultdict(int);agreement=[]
    for seg,s in segments(a):
        if len(s['times'])<2:continue
        found={}
        for v in VIEWS:
            scores=methods.boundary_scores(s[v],s['times'],s['valid'],model['references'][v],scales_seconds=(2.,))['2.0']
            ids=methods.select_boundaries(scores,s['times'],threshold=model['thresholds'][v]['2.0'],min_separation_seconds=p['boundary']['minimum_separation_seconds'])
            found[v]=s['times'][ids];scored[v]+=int(np.isfinite(scores).sum())
            events.extend(dict(view=v,segment=seg,time=float(s['times'][i]),score=float(scores[i])) for i in ids)
        for va,vb in itertools.combinations(VIEWS,2):
            m=methods.match_boundaries(found[va],found[vb],tolerance_seconds=p['boundary']['match_tolerance_seconds'])
            agreement.append(dict(segment=seg,view_a=va,view_b=vb,**m))
    count=int(a['valid'].sum());summaries={};rates={}
    for v in VIEWS:
        ref=model['references'][v]
        summaries[v]=((np.median(a[v][a['valid']],axis=0)-np.asarray(ref['center']))/np.asarray(ref['scale'])).tolist() if count else None
        n=sum(e['view']==v for e in events);seconds=scored[v]*p['hop_seconds']
        rates[v]=dict(events=n,scored_windows=scored[v],scored_center_seconds=seconds,events_per_scored_minute=n/(seconds/60) if seconds else None)
    return dict(windows=len(a['times']),valid_windows=count,qc_pass_fraction=count/len(a['times']),standardized_medians=summaries,transition_rates=rates,agreement=agreement),events


def evaluate(root=ROOT):
    root=Path(root);p=read_json(root/'protocol/experiment-008.json');receipt=read_json(root/'results/008/features.json')
    if not receipt.get('completed') or receipt['inputs']!=input_identity(root):raise ValueError('incomplete or changed feature run')
    model=read_json(root/'results/003/model.json')
    records=read_json(root/'results/008/qualification.json')['records'];features={r['recording_id']:r for r in receipt['records']}
    if len(features)!=len(receipt['records']) or set(features)!={r['recording_id'] for r in records}:raise ValueError('feature denominator differs from catalog')
    final=root/'results/008/analysis.sqlite'
    if final.exists():raise ValueError('immutable analysis already exists')
    temp=final.with_suffix('.partial');shutil.copyfile(root/'results/008/catalog.sqlite',temp)
    db=sqlite3.connect(temp);db.execute('PRAGMA foreign_keys=ON')
    db.executescript('CREATE TABLE metrics(recording_id TEXT PRIMARY KEY REFERENCES recordings(recording_id),metrics_json TEXT); CREATE TABLE events(recording_id TEXT REFERENCES recordings(recording_id),view TEXT,segment INTEGER,time_seconds REAL,score REAL);')
    evaluated=[];pair_rows=[];stats={}
    try:
        for rec in records:
            f=features[rec['recording_id']]
            if f['status']!='EXTRACTED':continue
            if digest(root/f['path'])!=f['sha256']:raise ValueError('changed feature archive')
            with np.load(root/f['path'],allow_pickle=False) as z:a={k:z[k] for k in z.files}
            met,events=record_metrics(a,model,p)
            if met['windows']!=f['windows'] or met['valid_windows']!=f['valid_windows']:raise ValueError('feature count differs from receipt')
            row=dict(recording_id=rec['recording_id'],source_subject=rec['source_subject'],session=rec['session'],**met)
            evaluated.append(row);db.execute('INSERT INTO metrics VALUES (?,?)',(rec['recording_id'],canonical_json(json_ready(met))))
            db.executemany('INSERT INTO events VALUES (?,?,?,?,?)',[(rec['recording_id'],e['view'],e['segment'],e['time'],e['score']) for e in events]);db.commit()
        by_pair={(r['source_subject'],r['session']):r for r in evaluated}
        complete=[]
        for sub in p['subjects']:
            pair=[by_pair.get((sub,s)) for s in p['sessions']]
            eligible=all(r is not None and r['valid_windows']>=p['minimum_valid_windows_for_pair'] for r in pair)
            row=dict(source_subject=sub,status='PAIRED' if eligible else 'INSUFFICIENT_PAIR',recording_ids=[r['recording_id'] if r else None for r in pair])
            if eligible:
                complete.append(pair)
                row['absolute_rate_difference_per_minute']={v:abs(pair[0]['transition_rates'][v]['events_per_scored_minute']-pair[1]['transition_rates'][v]['events_per_scored_minute']) if all(r['transition_rates'][v]['events_per_scored_minute'] is not None for r in pair) else None for v in VIEWS}
            pair_rows.append(row)
        for v in VIEWS:
            stats[v]=paired_distances([pair[0]['standardized_medians'][v] for pair in complete],[pair[1]['standardized_medians'][v] for pair in complete]) if len(complete)>=3 else dict(n_pairs=len(complete),status='INSUFFICIENT_PAIRS')
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('database integrity failed')
    finally:db.close()
    temp.replace(final)
    result=dict(schema='eegt-repeat-results/v1',inputs=receipt['inputs'],features_sha256=digest(root/'results/008/features.json'),analysis_sha256=digest(final),
        totals=dict(candidate_recordings=len(records),qualified_recordings=sum(r['status']=='QUALIFIED' for r in records),analyzed_recordings=len(evaluated),complete_pairs=len(complete),
            full_qualified_hours=sum(r['duration_seconds'] for r in records if r['status']=='QUALIFIED')/3600,
            selected_analysis_hours=len(evaluated)*p['analysis_seconds']/3600,
            windows=sum(r['windows'] for r in evaluated),valid_windows=sum(r['valid_windows'] for r in evaluated),transition_events=sum(t['events'] for r in evaluated for t in r['transition_rates'].values())),
        records=evaluated,pairs=pair_rows,paired_statistics=stats)
    atomic_json(root/'results/008/summary.json',json_ready(result),immutable=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['freeze', 'acquire','qualify','extract','evaluate'])
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        result = globals()[args.action](args.root)
    print(json.dumps({'action':args.action,'status':'COMPLETE'}))
