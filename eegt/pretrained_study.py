"""Frozen Experiment 009: an exposed-data comparison, without learned refits."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import resource
import sqlite3
import time

import numpy as np
from scipy import signal
from scipy.stats import rankdata

from .acquire import ROOT, digest
from .corpus import atomic_json, canonical_json

VIEWS = ('morphology', 'spectrum', 'coordination')
VARIANTS = ('original', 'gain_half', 'polarity_flip', 'channel_reverse', 'independent_phase')


def read(path):
    return json.loads(Path(path).read_text())


def array_hash(array):
    a = np.ascontiguousarray(array)
    return hashlib.sha256(a.dtype.str.encode() + str(a.shape).encode() + a.tobytes()).hexdigest()


def save_arrays(path, **arrays):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.partial')
    with temp.open('wb') as handle:
        np.savez_compressed(handle, **arrays)
    temp.replace(path)


def preprocess_block(samples_uv, sample_rate_hz=250):
    """Numerical input only. Reject missing samples before any filtering."""
    x = np.asarray(samples_uv)
    if x.shape != (4, 7500) or sample_rate_hz != 250 or x.dtype.kind not in 'fi':
        raise ValueError('expected four channels and exactly 30 seconds at 250 Hz')
    if not np.isfinite(x).all():
        raise ValueError('nonfinite native samples')
    x = x.astype(np.float64)
    if np.any(np.std(x, axis=1) < .05):
        raise ValueError('flat native channel')
    sos = signal.butter(4, (.3, 75), btype='bandpass', fs=250, output='sos')
    filtered = signal.sosfiltfilt(sos, x, axis=1, padtype='odd', padlen=2500)
    b, a = signal.iirnotch(60, 30, fs=250)
    filtered = signal.filtfilt(b, a, filtered, axis=1, padtype='odd', padlen=2500)
    resampled = signal.resample_poly(filtered, 4, 5, axis=1)
    if resampled.shape != (4, 6000) or not np.isfinite(resampled).all():
        raise ValueError('resampling failed')
    peak = float(np.max(np.abs(resampled)))
    if peak > 100:
        raise ValueError('preprocessed absolute amplitude exceeds 100 uV')
    return (resampled / 100).astype(np.float32).reshape(4, 30, 200), peak


def waveform_variant(patches, kind, seed):
    x = np.asarray(patches)
    if x.shape != (4, 30, 200) or x.dtype != np.float32 or not np.isfinite(x).all():
        raise ValueError('invalid prepared block')
    if kind == 'original':
        return x.copy()
    if kind == 'gain_half':
        return x * np.float32(.5)
    if kind == 'polarity_flip':
        return -x
    if kind == 'channel_reverse':
        return x[::-1].copy()
    if kind == 'independent_phase':
        wave = x.reshape(4, 6000).astype(np.float64)
        spectrum = np.fft.rfft(wave, axis=1)
        rng = np.random.default_rng(seed)
        phase = rng.uniform(-np.pi, np.pi, spectrum.shape)
        phase[:, 0] = phase[:, -1] = 0
        return np.fft.irfft(spectrum * np.exp(1j * phase), n=6000, axis=1).astype(np.float32).reshape(x.shape)
    raise ValueError('unknown waveform variant')


def prepare(root=ROOT):
    import mne
    root = Path(root)
    out = root / 'results/009'
    if (out / 'prepared.json').exists():
        raise FileExistsError('preserve existing prepared run; use a separate checkout')
    p = read(root / 'protocol/experiment-009.json')
    fixed = {
        p['source']['source_manifest']: p['source']['source_manifest_sha256'],
        p['source']['qualification']: p['source']['qualification_sha256'],
        p['baseline']['features']: p['baseline']['features_receipt_sha256'],
        p['baseline']['model']: p['baseline']['model_sha256'],
    }
    for path, expected in fixed.items():
        if digest(root / path) != expected:
            raise ValueError(f'frozen input changed: {path}')
    q = read(root / p['source']['qualification'])
    f = read(root / p['baseline']['features'])
    model = read(root / p['baseline']['model'])
    features = {r['recording_id']: r for r in f['records']}
    rows, patches, baselines = [], [], {v: [] for v in VIEWS}
    records = sorted(q['records'], key=lambda r: (r['source_subject'], r['session']))
    expected_pairs = {(s, t) for s in p['source']['subjects'] for t in p['source']['sessions']}
    if {(r['source_subject'], r['session']) for r in records} != expected_pairs or len(records) != 12:
        raise ValueError('recording set changed')
    source_hashes = {}
    for rec in records:
        if rec['status'] != 'QUALIFIED' or rec['channels'] != p['source']['channels'] or rec['sample_rate_hz'] != 250:
            raise ValueError('source qualification changed')
        path = root / rec['path']
        if digest(path) != rec['sha256']:
            raise ValueError('raw source changed')
        fr = features[rec['recording_id']]
        fp = root / fr['path']
        if digest(fp) != fr['sha256']:
            raise ValueError('baseline feature file changed')
        source_hashes[rec['path']] = rec['sha256']
        source_hashes[fr['path']] = fr['sha256']
        raw = mne.io.read_raw_eeglab(path, preload=False, verbose='ERROR')
        if raw.info['sfreq'] != 250 or any(ch not in raw.ch_names for ch in rec['channels']):
            raise ValueError('decoded rate/channel contract changed')
        data = raw.get_data(picks=rec['channels'], start=0, stop=150000) * 1e6
        raw.close()
        if data.shape != (4, 150000):
            raise ValueError('recording shorter than selected exposure')
        with np.load(fp, allow_pickle=False) as a:
            for block in range(20):
                start = block * 30
                idx = len(rows)
                row = dict(candidate_index=idx, recording_id=rec['recording_id'], source_subject=rec['source_subject'],
                           session=rec['session'], start_seconds=start, duration_seconds=30, array_row=None,
                           status='REJECTED', reasons=[])
                target = start + np.arange(1.5, 29, 1)
                ix = np.searchsorted(a['times'], target)
                if np.any(ix >= len(a['times'])) or not np.array_equal(a['times'][ix], target):
                    raise ValueError('baseline time alignment mismatch')
                row['baseline_valid_centers'] = int(a['valid'][ix].sum())
                if row['baseline_valid_centers'] != 28:
                    row['reasons'].append('BASELINE_QC')
                # Native gap receipt uses start/stop seconds; never concatenate across a gap.
                for gap in rec.get('gaps', []):
                    if not isinstance(gap, dict) or not {'start_seconds', 'stop_seconds'} <= gap.keys():
                        raise ValueError('unknown native gap schema')
                    if gap['start_seconds'] < start + 30 and gap['stop_seconds'] > start:
                        row['reasons'].append('NATIVE_GAP')
                try:
                    prepared, peak = preprocess_block(data[:, start * 250:(start + 30) * 250])
                    row['preprocessed_peak_uv'] = peak
                except ValueError as exc:
                    row['reasons'].append(str(exc))
                    prepared = None
                if not row['reasons']:
                    row['array_row'] = len(patches)
                    row['status'] = 'ELIGIBLE'
                    row['prepared_array_sha256'] = array_hash(prepared)
                    row['baseline_array_sha256'] = {}
                    patches.append(prepared)
                    for view in VIEWS:
                        ref = model['references'][view]
                        values = (a[view][ix] - np.array(ref['center'])) / np.array(ref['scale'])
                        if not np.isfinite(values).all():
                            raise ValueError('eligible baseline is nonfinite')
                        row['baseline_array_sha256'][view] = array_hash(values)
                        baselines[view].append(values)
                rows.append(row)
        print(f"prepared {rec['recording_id']}: {sum(r['status']=='ELIGIBLE' for r in rows[-20:])}/20", flush=True)
    arrays = dict(patches=np.stack(patches) if patches else np.empty((0, 4, 30, 200), dtype=np.float32),
                  candidate_indices=np.array([r['candidate_index'] for r in rows if r['status']=='ELIGIBLE'], dtype=np.int64))
    for view in VIEWS:
        dim = len(model['references'][view]['center'])
        arrays['baseline_' + view] = np.stack(baselines[view]) if baselines[view] else np.empty((0, 28, dim))
    dest = root / 'data/derived/009/prepared.npz'
    save_arrays(dest, **arrays)
    fixed.update({'protocol/experiment-009.json': digest(root/'protocol/experiment-009.json'),
                  'eegt/pretrained_study.py': digest(root/'eegt/pretrained_study.py'),
                  'requirements.lock': digest(root/'requirements.lock')})
    receipt = dict(schema='eegt-pretrained-prepared/v1',created_at_utc=datetime.now(timezone.utc).isoformat(),
                   inputs=fixed,source_hashes=source_hashes,records=rows,
                   array_path=str(dest.relative_to(root)),array_sha256=digest(dest),
                   totals=dict(candidate_recordings=12,candidate_blocks=len(rows),candidate_hours=2,
                               eligible_blocks=len(patches),eligible_seconds=len(patches)*30,
                               rejected_blocks=len(rows)-len(patches)),
                   rejection_counts=dict(Counter(reason for row in rows for reason in row['reasons'])),
                   discovery_contract='The encoder receives only numeric patches; source grouping remains in this curator receipt.')
    atomic_json(out/'prepared.json',receipt)
    return receipt


def validate_prepared(root, receipt):
    root = Path(root)
    if digest(root/receipt['array_path']) != receipt['array_sha256']:
        raise ValueError('prepared archive changed')
    data = dict(np.load(root/receipt['array_path'], allow_pickle=False))
    selected = [r for r in receipt['records'] if r['status']=='ELIGIBLE']
    if not np.array_equal(data['candidate_indices'], [r['candidate_index'] for r in selected]):
        raise ValueError('prepared source row order mismatch')
    if len(data['patches']) != len(selected):
        raise ValueError('prepared source row count mismatch')
    for index, row in enumerate(selected):
        if row['array_row'] != index or array_hash(data['patches'][index]) != row['prepared_array_sha256']:
            raise ValueError('prepared waveform/source identity mismatch')
        for view in VIEWS:
            if array_hash(data['baseline_'+view][index]) != row['baseline_array_sha256'][view]:
                raise ValueError('prepared descriptor/source identity mismatch')
    for view in VIEWS:
        if data['baseline_'+view].shape[:2] != (len(selected),28) or not np.isfinite(data['baseline_'+view]).all():
            raise ValueError('baseline shape or validity mismatch')
    return data, selected


def infer(checkpoint, root=ROOT):
    from .pretrained import CodeBrainEncoder
    import torch
    root = Path(root)
    if (root/'results/009/inference.json').exists():
        raise FileExistsError('preserve existing inference run')
    receipt = read(root/'results/009/prepared.json')
    data, selected = validate_prepared(root,receipt)
    protocol = read(root/'protocol/experiment-009.json')
    if digest(root/'protocol/experiment-009.json') != receipt['inputs']['protocol/experiment-009.json']:
        raise ValueError('protocol changed after preparation')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    encoder = CodeBrainEncoder(checkpoint)
    outputs, measurements = [], []
    started = time.monotonic()
    for index, row in enumerate(selected):
        variants = []
        for name in VARIANTS:
            x = waveform_variant(data['patches'][index],name,9009+row['candidate_index'])
            t = time.monotonic()
            y = encoder.encode(x[None])
            if y.shape != (1,4,30,200) or y.dtype != np.float32 or not np.isfinite(y).all():
                raise ValueError('encoder output contract failed')
            variants.append(y[0])
            measurements.append(dict(candidate_index=row['candidate_index'],variant=name,
                                     input_sha256=array_hash(x),output_sha256=array_hash(y[0]),
                                     maximum_absolute_prepared_uv=float(np.max(np.abs(x))*100),
                                     seconds=time.monotonic()-t))
        outputs.append(np.stack(variants))
        if index % 10 == 0:
            print(f'inferred {index+1}/{len(selected)} blocks; five variants each',flush=True)
    embeddings = np.stack(outputs) if outputs else np.empty((0,5,4,30,200),dtype=np.float32)
    path = root/'data/derived/009/embeddings.npz'
    save_arrays(path, embeddings=embeddings,candidate_indices=data['candidate_indices'],variants=np.array(VARIANTS))
    code_paths = ['eegt/pretrained_study.py','eegt/pretrained.py']
    code_paths += [str(p.relative_to(root)) for p in (root/'eegt/vendor/codebrain').glob('*.py')]
    result = dict(schema='eegt-pretrained-inference/v1',status='COMPLETE',
                  prepared_receipt_sha256=digest(root/'results/009/prepared.json'),
                  prepared_archive_sha256=receipt['array_sha256'],protocol_sha256=digest(root/'protocol/experiment-009.json'),
                  checkpoint_sha256=digest(Path(checkpoint)),code_sha256={p:digest(root/p) for p in code_paths},
                  array_path=str(path.relative_to(root)),array_sha256=digest(path),
                  shape=list(embeddings.shape),variants=list(VARIANTS),block_variant_runs=len(measurements),
                  elapsed_seconds=time.monotonic()-started,maximum_rss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  torch_version=torch.__version__,numpy_version=np.__version__,torch_threads=torch.get_num_threads(),
                  observed_at_utc=datetime.now(timezone.utc).isoformat(),measurements=measurements)
    if result['checkpoint_sha256'] != protocol['encoder']['weight_sha256']:
        raise ValueError('checkpoint identity changed')
    atomic_json(root/'results/009/inference.json',result)
    return result


def cosine_distances(x):
    x = np.asarray(x,dtype=np.float64)
    if x.ndim != 2 or not np.isfinite(x).all():
        raise ValueError('undefined cosine geometry')
    norms = np.linalg.norm(x,axis=1)
    if np.any(norms <= 1e-12):raise ValueError('undefined cosine geometry')
    z = x/norms[:,None]
    d = 1-np.clip(z@z.T,-1,1)
    np.fill_diagonal(d,0)
    return d


def rms_distances(x):
    x = np.asarray(x,dtype=np.float64)
    if x.ndim != 2 or x.shape[1] == 0 or not np.isfinite(x).all():
        raise ValueError('invalid numerical descriptors')
    return np.sqrt(np.mean((x[:,None,:]-x[None,:,:])**2,axis=2))


def correlation(a,b):
    a,b = np.asarray(a).ravel(),np.asarray(b).ravel()
    if a.shape != b.shape or len(a)<3 or not np.isfinite(a).all() or not np.isfinite(b).all():
        return None
    x,y = rankdata(a),rankdata(b)
    x-=x.mean();y-=y.mean()
    den=np.linalg.norm(x)*np.linalg.norm(y)
    return float(np.clip(np.dot(x,y)/den,-1,1)) if den>0 else None


def block_comparison(embedding, baseline):
    model = cosine_distances(embedding)
    numerical = rms_distances(baseline)
    upper = np.triu_indices(len(model),1)
    profile = np.diag(model,1)
    reference = np.diag(numerical,1)
    geometry = correlation(model[upper],numerical[upper])
    change = correlation(profile,reference)
    geometry_null = [correlation(np.roll(np.roll(model,k,axis=0),k,axis=1)[upper],numerical[upper]) for k in range(1,len(model))]
    change_null = [correlation(np.roll(profile,k),reference) for k in range(1,len(profile))]
    return dict(geometry=geometry,change=change,geometry_null=geometry_null,change_null=change_null)


def aggregate(values, rows, minimum_blocks=3):
    """Exact nested record -> two-session person -> mean-person aggregation."""
    values=np.asarray(values,dtype=np.float64)
    if values.ndim==1:values=values[None]
    if values.shape[1] != len(rows):raise ValueError('row mismatch')
    record_scores,record_meta={},[]
    for record in sorted({r['recording_id'] for r in rows}):
        indices=[i for i,r in enumerate(rows) if r['recording_id']==record]
        first=rows[indices[0]]
        if len(indices)<minimum_blocks:continue
        score=np.median(values[:,indices],axis=1)
        record_scores[(first['source_subject'],first['session'])]=score
        record_meta.append(dict(recording_id=record,source_subject=first['source_subject'],session=first['session'],blocks=len(indices),median=float(score[0])))
    people=[];scores=[]
    for person in sorted({r['source_subject'] for r in rows}):
        if (person,'001') in record_scores and (person,'002') in record_scores:
            score=(record_scores[(person,'001')]+record_scores[(person,'002')])/2
            scores.append(score);people.append(dict(source_subject=person,mean_two_sessions=float(score[0])))
    return (np.mean(scores,axis=0) if scores else None),record_meta,people


def evaluate(root=ROOT):
    root=Path(root);out=root/'results/009'
    if (out/'summary.json').exists():raise FileExistsError('preserve existing comparison')
    prep=read(out/'prepared.json');run=read(out/'inference.json');p=read(root/'protocol/experiment-009.json')
    if digest(out/'prepared.json')!=run['prepared_receipt_sha256'] or prep['array_sha256']!=run['prepared_archive_sha256']:
        raise ValueError('inference input binding mismatch')
    if digest(root/'protocol/experiment-009.json')!=run['protocol_sha256'] or run['checkpoint_sha256']!=p['encoder']['weight_sha256']:
        raise ValueError('inference protocol/checkpoint binding mismatch')
    data,rows=validate_prepared(root,prep)
    if digest(root/run['array_path'])!=run['array_sha256']:raise ValueError('embeddings changed')
    with np.load(root/run['array_path'],allow_pickle=False) as a:
        if not np.array_equal(a['candidate_indices'],data['candidate_indices']) or tuple(a['variants'])!=VARIANTS:
            raise ValueError('embedding row or variant order mismatch')
        full=a['embeddings'].copy()
    if full.shape!=(len(rows),5,4,30,200) or not np.isfinite(full).all():raise ValueError('invalid embeddings')
    by_key={(r['candidate_index'],r['variant']):r for r in run['measurements']}
    for i,row in enumerate(rows):
        for j,variant in enumerate(VARIANTS):
            if array_hash(full[i,j])!=by_key[(row['candidate_index'],variant)]['output_sha256']:
                raise ValueError('embedding output-row identity mismatch')
    pooled=full.astype(np.float64).mean(axis=2)[:,:,1:29]
    comparisons=[];controls=[]
    for i,row in enumerate(rows):
        for view in VIEWS:
            try:result=block_comparison(pooled[i,0],data['baseline_'+view][i])
            except ValueError:result=dict(geometry=None,change=None,geometry_null=[None]*27,change_null=[None]*26)
            comparisons.append(dict(candidate_index=row['candidate_index'],view=view,**result))
        upper=np.triu_indices(28,1)
        for j,variant in enumerate(VARIANTS[1:],1):
            try:
                original=cosine_distances(pooled[i,0]);changed=cosine_distances(pooled[i,j])
                geometry_rho=correlation(original[upper],changed[upper])
                change_rho=correlation(np.diag(original,1),np.diag(changed,1))
            except ValueError:geometry_rho=change_rho=None
            controls.append(dict(candidate_index=row['candidate_index'],variant=variant,
                geometry_rho=geometry_rho,change_rho=change_rho,
                rms_embedding_displacement=float(np.sqrt(np.mean((pooled[i,j]-pooled[i,0])**2))),
                maximum_absolute_prepared_uv=by_key[(row['candidate_index'],variant)]['maximum_absolute_prepared_uv']))
    source={r['candidate_index']:r for r in rows};stats=[];rng=np.random.default_rng(9009)
    for metric in ('geometry','change'):
        for view in VIEWS:
            valid=[r for r in comparisons if r['view']==view and r[metric] is not None and all(x is not None for x in r[metric+'_null'])]
            used=[source[r['candidate_index']] for r in valid]
            observed,record_scores,people=aggregate([r[metric] for r in valid],used)
            entry=dict(metric=metric,view=view,valid_blocks=len(valid),records=record_scores,participants=people,
                       complete_participants=len(people),status='INSUFFICIENT_PARTICIPANTS')
            if observed is not None:
                entry['observed_mean_participant_rho']=float(observed[0])
            if len(people)>=p['quality']['minimum_complete_participants']:
                choices=np.array([r[metric+'_null'] for r in valid])
                shifts=rng.integers(0,choices.shape[1],size=(p['inference']['replicates'],len(valid)))
                draws=choices[np.arange(len(valid))[None,:],shifts]
                null,_,_=aggregate(draws,used)
                count=int(np.count_nonzero(null>=observed[0]-1e-12))
                probability=(1+count)/(len(null)+1)
                entry.update(status='COMPARED',null_replicates=len(null),null_mean=float(null.mean()),
                             null_quantiles=np.quantile(null,[.025,.5,.975]).tolist(),upper_tail_count=count,
                             p_greater=probability,p_bonferroni_six=min(1,6*probability),null_values=null.tolist())
            stats.append(entry)
    control_summary=[]
    for variant in VARIANTS[1:]:
        for metric in ('geometry_rho','change_rho','rms_embedding_displacement'):
            valid=[r for r in controls if r['variant']==variant and r[metric] is not None]
            value,record_scores,people=aggregate([r[metric] for r in valid],[source[r['candidate_index']] for r in valid])
            control_summary.append(dict(variant=variant,metric=metric,complete_participants=len(people),
                mean_participant_value=None if value is None else float(value[0]),records=record_scores,participants=people,
                status='DESCRIPTIVE' if people else 'INSUFFICIENT_PARTICIPANTS'))
    dbpath=out/'analysis.sqlite';tmp=dbpath.with_suffix('.partial');tmp.unlink(missing_ok=True)
    db=sqlite3.connect(tmp)
    db.executescript('''CREATE TABLE candidates(candidate_index INTEGER PRIMARY KEY,recording_id TEXT,source_subject TEXT,session TEXT,start_seconds REAL,status TEXT,receipt_json TEXT);
      CREATE TABLE comparisons(candidate_index INTEGER REFERENCES candidates(candidate_index),view TEXT,geometry REAL,change REAL,receipt_json TEXT,PRIMARY KEY(candidate_index,view));
      CREATE TABLE controls(candidate_index INTEGER REFERENCES candidates(candidate_index),variant TEXT,receipt_json TEXT,PRIMARY KEY(candidate_index,variant));''')
    db.execute('PRAGMA foreign_keys=ON')
    for r in prep['records']:db.execute('INSERT INTO candidates VALUES(?,?,?,?,?,?,?)',(r['candidate_index'],r['recording_id'],r['source_subject'],r['session'],r['start_seconds'],r['status'],canonical_json(r)))
    for r in comparisons:db.execute('INSERT INTO comparisons VALUES(?,?,?,?,?)',(r['candidate_index'],r['view'],r['geometry'],r['change'],canonical_json(r)))
    for r in controls:db.execute('INSERT INTO controls VALUES(?,?,?)',(r['candidate_index'],r['variant'],canonical_json(r)))
    db.commit()
    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('database integrity')
    db.close();tmp.replace(dbpath)
    result=dict(schema='eegt-pretrained-comparison/v1',totals=prep['totals'],rejection_counts=prep['rejection_counts'],
        primary_statistics=stats,control_summaries=control_summary,block_comparisons=comparisons,block_controls=controls,
        analysis_sha256=digest(dbpath),inputs={path:digest(root/path) for path in ['protocol/experiment-009.json','results/009/prepared.json','results/009/inference.json','eegt/pretrained_study.py']},
        interpretation='Exploratory conditional within-recording alignment on exposed data. Shared filtered-wave dynamics, architecture, montage and artifacts can explain agreement; cyclic-shift exchangeability is an assumption. No independent pretrained generalization, universal tokens, brain meaning or physical Neurable transfer is established.')
    atomic_json(out/'summary.json',result)
    print(json.dumps({k:result[k] for k in ['totals','rejection_counts']}))
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','infer','evaluate']);ap.add_argument('--checkpoint')
    a=ap.parse_args()
    if a.action=='prepare':prepare()
    elif a.action=='infer':
        if not a.checkpoint:ap.error('--checkpoint is required')
        infer(a.checkpoint)
    else:evaluate()


if __name__=='__main__':main()
