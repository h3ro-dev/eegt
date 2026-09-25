"""Experiment 010: quality-only, time-stratified sampling of exposed EEG."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import argparse
import resource
import time

import numpy as np

from .acquire import ROOT, digest
from .corpus import atomic_json
from . import pretrained_study as previous


def selected_indices(rows):
    """Choose the lower temporal median of each nonempty quality-pass stratum."""
    groups = {}
    for row in rows:
        if row['quality_status'] == 'PASS':
            key = (row['recording_id'], row['stratum_index'])
            groups.setdefault(key, []).append(row)
    selected = []
    for group in groups.values():
        ordered = sorted(group, key=lambda row: row['start_seconds'])
        selected.append(ordered[(len(ordered) - 1) // 2]['candidate_index'])
    return sorted(selected)


def paired_gate(rows, minimum_blocks=3, minimum_people=3):
    selected = [row for row in rows if row['status'] == 'ELIGIBLE']
    counts = Counter((r['source_subject'], r['session']) for r in selected)
    people = sorted({r['source_subject'] for r in rows})
    complete = [p for p in people if all(counts[p, s] >= minimum_blocks for s in ('001', '002'))]
    return dict(status='READY' if len(complete) >= minimum_people else 'INSUFFICIENT_PARTICIPANTS',
                complete_participants=complete, complete_participant_count=len(complete),
                minimum_blocks_per_night=minimum_blocks, minimum_complete_participants=minimum_people,
                records=[dict(source_subject=p, session=s, selected_blocks=counts[p, s])
                         for p in people for s in ('001', '002')])


def validate_selection(root, receipt, protocol):
    """Recompute selection and its gate; never trust an editable READY flag."""
    root = Path(root)
    for path, sha in receipt['inputs'].items():
        if digest(root/path) != sha:
            raise ValueError(f'prepared input changed: {path}')
    if protocol != previous.read(root/'protocol/experiment-010.json'):
        raise ValueError('protocol mismatch')
    rows = receipt['records']
    if len(rows) != 5760 or [r['candidate_index'] for r in rows] != list(range(5760)):
        raise ValueError('candidate census mismatch')
    pairs = {(p, s) for p in protocol['source']['subjects'] for s in protocol['source']['sessions']}
    found = {}
    for row in rows:
        pair = (row['source_subject'], row['session'])
        found.setdefault(pair, []).append(row)
        if row['quality_status'] not in ('PASS', 'FAIL') or (row['quality_status'] == 'PASS') != (not row['reasons']):
            raise ValueError('quality status/reason mismatch')
        if row['stratum_index'] != row['start_seconds'] // 1200:
            raise ValueError('stratum/time mismatch')
    if set(found) != pairs or len(pairs) != 12:
        raise ValueError('source pair census mismatch')
    record_ids = []
    for group in found.values():
        if sorted(r['start_seconds'] for r in group) != list(range(0, 14400, 30)):
            raise ValueError('source interval census mismatch')
        ids = {r['recording_id'] for r in group}
        if len(ids) != 1:
            raise ValueError('source record identity mismatch')
        record_ids.extend(ids)
    if len(set(record_ids)) != 12:
        raise ValueError('duplicate record identity')
    expected = set(selected_indices(rows))
    for row in rows:
        status = ('ELIGIBLE' if row['candidate_index'] in expected else
                  'QUALIFIED_UNSELECTED' if row['quality_status'] == 'PASS' else 'REJECTED')
        if row['status'] != status:
            raise ValueError('time-stratified selection mismatch')
    gate = paired_gate(rows, protocol['quality']['minimum_blocks_per_record'],
                       protocol['quality']['minimum_complete_participants'])
    if receipt['inference_gate'] != gate:
        raise ValueError('inference gate mismatch')
    previous.validate_prepared(root, receipt)
    return gate


def prepare(root=ROOT):
    import mne
    root = Path(root)
    out = root/'results/010'
    if (out/'prepared.json').exists():
        raise FileExistsError('preserve existing quality census')
    p = previous.read(root/'protocol/experiment-010.json')
    old = previous.read(root/'protocol/experiment-009.json')
    for key in ('source', 'encoder', 'preprocessing', 'baseline', 'representation', 'inference', 'controls'):
        if p[key] != old[key]:
            raise ValueError(f'inherited method changed: {key}')
    if {k:v for k,v in p['quality'].items() if k != 'rule'} != {k:v for k,v in old['quality'].items() if k != 'rule'}:
        raise ValueError('inherited quality thresholds changed')
    if digest(root/'protocol/experiment-009.json') != p['prior_exposure']['experiment_009_protocol_sha256']:
        raise ValueError('prior protocol identity changed')
    fixed = {p['source']['source_manifest']:p['source']['source_manifest_sha256'],
             p['source']['qualification']:p['source']['qualification_sha256'],
             p['baseline']['features']:p['baseline']['features_receipt_sha256'],
             p['baseline']['model']:p['baseline']['model_sha256']}
    for path, sha in fixed.items():
        if digest(root/path) != sha:
            raise ValueError(f'frozen input changed: {path}')
    qualification = previous.read(root/p['source']['qualification'])
    features = {r['recording_id']:r for r in previous.read(root/p['baseline']['features'])['records']}
    model = previous.read(root/p['baseline']['model'])
    records = sorted(qualification['records'], key=lambda r:(r['source_subject'],r['session']))
    pairs = {(s,t) for s in p['source']['subjects'] for t in p['source']['sessions']}
    if len(records) != 12 or {(r['source_subject'],r['session']) for r in records} != pairs:
        raise ValueError('source set changed')
    rows, patches, baselines, source_hashes = [], [], {v:[] for v in previous.VIEWS}, {}
    started = time.monotonic()
    for rec in records:
        if rec['status'] != 'QUALIFIED' or rec['channels'] != p['source']['channels'] or rec['sample_rate_hz'] != 250:
            raise ValueError('source qualification changed')
        fr = features[rec['recording_id']]
        for entry in (rec, fr):
            if digest(root/entry['path']) != entry['sha256']:
                raise ValueError('source or baseline bytes changed')
            source_hashes[entry['path']] = entry['sha256']
        raw = mne.io.read_raw_eeglab(root/rec['path'], preload=False, verbose='ERROR')
        try:
            if raw.info['sfreq'] != 250 or any(c not in raw.ch_names for c in rec['channels']):
                raise ValueError('decoded rate/channel contract changed')
            wave = raw.get_data(picks=rec['channels'], start=0, stop=3600000) * 1e6
        finally:
            raw.close()
        if wave.shape != (4, 3600000):
            raise ValueError('recording shorter than frozen interval')
        cache, record_rows = {}, []
        with np.load(root/fr['path'], allow_pickle=False) as archive:
            f = {key:archive[key] for key in ('times','valid',*previous.VIEWS)}
            for start in range(0, 14400, 30):
                row = dict(candidate_index=len(rows)+len(record_rows), recording_id=rec['recording_id'],
                           source_subject=rec['source_subject'], session=rec['session'], start_seconds=start,
                           duration_seconds=30, stratum_index=start//1200, array_row=None,
                           quality_status='FAIL', status='REJECTED', reasons=[])
                target = start + np.arange(1.5, 29, 1)
                ix = np.searchsorted(f['times'], target)
                if np.any(ix >= len(f['times'])) or not np.array_equal(f['times'][ix], target):
                    raise ValueError('baseline time alignment mismatch')
                row['baseline_valid_centers'] = int(f['valid'][ix].sum())
                if row['baseline_valid_centers'] != 28:
                    row['reasons'].append('BASELINE_QC')
                for gap in rec.get('gaps', []):
                    if not isinstance(gap,dict) or not {'start_seconds','stop_seconds'} <= gap.keys():
                        raise ValueError('unknown native gap schema')
                    if gap['start_seconds'] < start+30 and gap['stop_seconds'] > start:
                        row['reasons'].append('NATIVE_GAP')
                block = wave[:,start*250:(start+30)*250]
                row['nonfinite_samples_per_channel'] = (~np.isfinite(block)).sum(axis=1).tolist()
                try:
                    prepared, peak = previous.preprocess_block(block)
                    row['preprocessed_peak_uv'] = peak
                except ValueError as exc:
                    row['reasons'].append(str(exc))
                if not row['reasons']:
                    row['quality_status'] = 'PASS'
                    row['status'] = 'QUALIFIED_UNSELECTED'
                    cache[row['candidate_index']] = (prepared, ix)
                record_rows.append(row)
            chosen = set(selected_indices(record_rows))
            for row in record_rows:
                if row['candidate_index'] not in chosen:
                    continue
                prepared, ix = cache[row['candidate_index']]
                row.update(status='ELIGIBLE', array_row=len(patches), prepared_array_sha256=previous.array_hash(prepared),
                           baseline_array_sha256={})
                patches.append(prepared)
                for view in previous.VIEWS:
                    ref = model['references'][view]
                    values = (f[view][ix] - np.array(ref['center'])) / np.array(ref['scale'])
                    if not np.isfinite(values).all():
                        raise ValueError('selected baseline is nonfinite')
                    row['baseline_array_sha256'][view] = previous.array_hash(values)
                    baselines[view].append(values)
        rows.extend(record_rows)
        print(f"census {rec['recording_id']}: {len(cache)}/480 qualified, {len(chosen)} selected", flush=True)
        del wave, cache
    arrays = dict(patches=np.stack(patches) if patches else np.empty((0,4,30,200),dtype=np.float32),
                  candidate_indices=np.array([r['candidate_index'] for r in rows if r['status']=='ELIGIBLE'],dtype=np.int64))
    for view in previous.VIEWS:
        dim = len(model['references'][view]['center'])
        arrays['baseline_'+view] = np.stack(baselines[view]) if baselines[view] else np.empty((0,28,dim))
    dest = root/'data/derived/010/prepared.npz'
    previous.save_arrays(dest, **arrays)
    fixed.update({path:digest(root/path) for path in ['protocol/experiment-009.json','protocol/experiment-010.json',
                                                   'eegt/distributed_study.py','eegt/pretrained_study.py','requirements.lock']})
    qualified = sum(r['quality_status']=='PASS' for r in rows)
    receipt = dict(schema='eegt-distributed-prepared/v1',created_at_utc=datetime.now(timezone.utc).isoformat(),
                   inputs=fixed,source_hashes=source_hashes,records=rows,array_path=str(dest.relative_to(root)),
                   array_sha256=digest(dest),
                   totals=dict(candidate_recordings=12,candidate_people=6,candidate_blocks=len(rows),candidate_hours=48,
                               quality_qualified_blocks=qualified,quality_qualified_seconds=qualified*30,
                               eligible_blocks=len(patches),eligible_seconds=len(patches)*30,
                               qualified_unselected_blocks=qualified-len(patches),rejected_blocks=len(rows)-qualified),
                   rejection_counts=dict(Counter(reason for row in rows for reason in row['reasons'])),
                   inference_gate=paired_gate(rows),elapsed_seconds=time.monotonic()-started,
                   maximum_rss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   discovery_contract='Numeric arrays only enter preprocessing and encoder. Source grouping stays in curator receipts. ELIGIBLE means selected for inference; quality qualification is recorded separately.')
    validate_selection(root,receipt,p)
    atomic_json(out/'prepared.json',receipt)
    return receipt


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','infer','evaluate'])
    parser.add_argument('--checkpoint')
    args=parser.parse_args()
    if args.action=='prepare':
        result=prepare()
        print(result['totals'],result['inference_gate'])
    elif args.action=='infer':
        if not args.checkpoint:parser.error('--checkpoint required')
        previous.infer(args.checkpoint,experiment='010')
    else:
        previous.evaluate(experiment='010')


if __name__=='__main__':
    main()
