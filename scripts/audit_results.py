"""Independent read-only arithmetic and artifact checks for EEGT Experiment002.
Adapted only to locate this checkout. Reads release artifacts; prints JSON on stdout.
"""
from __future__ import annotations
import csv, gzip, hashlib, io, json, math, re, zipfile
from pathlib import Path
import numpy as np
from sklearn.metrics import adjusted_rand_score, adjusted_mutual_info_score

ROOT = Path(__file__).resolve().parent
IN = ROOT.parent
RES = IN / "results/002"

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def close(a,b,tol=1e-12):
    return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)

def main():
    qc=json.loads((RES/'qc.json').read_text())
    metrics=json.loads((RES/'metrics.json').read_text())
    protocol=json.loads((IN/'protocol/experiment-002.json').read_text())
    manifest=json.loads((IN/'protocol/source-manifest.json').read_text())
    acquisition=json.loads((RES/'acquisition.json').read_text())
    provenance=json.loads((RES/'provenance.json').read_text())
    findings=[]
    checks=[]
    def check(name, ok, detail=''):
        checks.append({'name':name,'ok':bool(ok),'detail':detail})
        if not ok: findings.append({'name':name,'detail':detail})
    # CSV/QC denominator ledger.
    rows=[]
    with gzip.open(RES/'windows.csv.gz','rt',newline='') as f:
        rows=list(csv.DictReader(f))
    check('windows_csv_row_count', len(rows)==qc['total_windows'], f'{len(rows)} vs {qc["total_windows"]}')
    pass_rows=[r for r in rows if r['qc']=='PASS']
    abstain_rows=[r for r in rows if r['qc']=='ABSTAIN']
    check('windows_csv_qc_counts', len(pass_rows)==qc['qc_pass'] and len(abstain_rows)==qc['qc_abstain'], f'pass={len(pass_rows)} abstain={len(abstain_rows)} qc={qc["qc_pass"]}/{qc["qc_abstain"]}')
    for i,r in enumerate(rows): check(f'window_index_monotonic_{i}', int(r['window_index'])==i, 'first mismatch at '+str(i)) if int(r['window_index'])!=i else None
    # Per-record ledger from CSV against qc records.
    for rec in qc['records']:
        ri=rec['recording_index']
        rr=[r for r in rows if int(r['recording_index'])==ri]
        rp=[r for r in rr if r['qc']=='PASS']
        check(f'qc_record_{rec["recording"]}', len(rr)==rec['total_windows'] and len(rp)==rec['qc_pass'] and len(rr)-len(rp)==rec['qc_abstain'], f'csv={len(rr)}/{len(rp)} qc={rec["total_windows"]}/{rec["qc_pass"]}')
    # Source/metadata counts and hashes.
    check('source_manifest_protocol_binding', manifest['protocol_sha256']==sha256(IN/'protocol/experiment-002.json') and acquisition['source_manifest_sha256']==sha256(IN/'protocol/source-manifest.json') and qc['protocol_sha256']==sha256(IN/'protocol/experiment-002.json'), 'one or more protocol/manifest hashes differ')
    check('source_record_count', len(manifest['recordings'])==8 and len(provenance)==8 and len(qc['records'])==8, f'manifest={len(manifest["recordings"])} provenance={len(provenance)} qc={len(qc["records"])}')
    check('source_bytes_sum', acquisition['total_bytes']==manifest['total_download_bytes']==2769602360, f'{acquisition["total_bytes"]} / {manifest["total_download_bytes"]}')
    check('acquisition_file_count', len(acquisition['files'])==16 and all(x['bytes']>0 and len(x['sha256'])==64 for x in acquisition['files']), f'{len(acquisition["files"])}')
    expected_splits=['train','train','train','validation','test','test','external','external']
    actual_splits=[r['split'] for r in provenance]
    check('protocol_split_order', actual_splits==expected_splits, str(actual_splits))
    check('provenance_recording_indices', [r['recording_index'] for r in provenance]==list(range(8)), str([r['recording_index'] for r in provenance]))
    # Result arrays; explicit allow_pickle=False and dtype checks.
    with np.load(RES/'assignments.npz',allow_pickle=False) as ass, np.load(RES/'evaluation-index.npz',allow_pickle=False) as ev, np.load(RES/'models.npz',allow_pickle=False) as mod:
        window_index=ass['window_index']; rec_index=ev['recording_index']; split=ev['split']
        check('aligned_lengths', len(window_index)==len(rec_index)==len(split)==qc['qc_pass'], f'{len(window_index)}/{len(rec_index)}/{len(split)} vs {qc["qc_pass"]}')
        expected_pass=np.array([int(r['window_index']) for r in pass_rows],dtype=window_index.dtype)
        check('window_index_matches_csv_pass', np.array_equal(window_index,expected_pass), 'assignment index differs from CSV PASS rows')
        check('evaluation_recording_range', np.array_equal(np.sort(np.unique(rec_index)),np.arange(8)), str(np.unique(rec_index)))
        check('evaluation_split_matches_provenance', all(str(split[i])==provenance[int(rec_index[i])]['split'] for i in range(len(split))), 'evaluation split/group mismatch')
        # Expected 27 model keys, labels/accepted arrays all aligned.
        model_names=[f'{m}-k{k}-s{s}' for m in protocol['methods'] for k in protocol['vocabulary_sizes'] for s in protocol['seeds']]
        label_names=[k for k in ass.files if not k.endswith('__accepted') and k!='window_index']
        check('model_key_count', sorted(label_names)==sorted(model_names), f'{len(label_names)} labels vs {len(model_names)} expected')
        for key in model_names:
            labels=ass[key]; accepted=ass[key+'__accepted'];
            k=int(re.search(r'-k(\d+)-',key).group(1))
            check(f'{key}_array_shape', labels.shape==(qc['qc_pass'],) and accepted.shape==labels.shape, str((labels.shape,accepted.shape)))
            check(f'{key}_label_range', labels.dtype.kind in 'iu' and np.all((labels>=0)&(labels<k)), 'labels outside 0..k-1')
            check(f'{key}_accepted_bool', accepted.dtype.kind=='b', str(accepted.dtype))
        # NPZ entries have no object arrays and no pickle-bearing dtype headers.
        check('assignments_no_object', all(ass[k].dtype.kind!='O' for k in ass.files), 'object dtype present')
        check('evaluation_no_object', all(ev[k].dtype.kind!='O' for k in ev.files), 'object dtype present')
        check('models_no_object', all(mod[k].dtype.kind!='O' for k in mod.files), 'object dtype present')
        # Independent group counts and coverage/accepted/ood arithmetic for every model metric row.
        metric_by_key={m['model']:m for m in metrics['models']}
        check('metrics_model_count', len(metric_by_key)==27, str(len(metric_by_key)))
        groups={'train':split=='train','validation':split=='validation','test':split=='test','external':split=='external'}
        groups.update({f'r{int(g)+1:03}':rec_index==g for g in sorted(np.unique(rec_index))})
        qc_totals={r['split']:sum(x['total_windows'] for x in qc['records'] if x['split']==r['split']) for r in qc['records']}
        qc_totals.update({r['recording']:r['total_windows'] for r in qc['records']})
        for key,m in metric_by_key.items():
            labels=ass[key]; accepted=ass[key+'__accepted']
            row_by_group={row['group']:row for row in m['groups']}
            k=m['k']
            for name,mask in groups.items():
                row=row_by_group.get(name)
                n=int(mask.sum()); acc=int(accepted[mask].sum()); ood=n-acc
                total=qc_totals[name]
                check(f'{key}:{name}:counts', row is not None and row['qc_pass']==n and row['accepted']==acc and row['ood']==ood and row['total_windows']==total, f'row={row} expected total={total} qc={n} acc={acc} ood={ood}')
                if row is not None:
                    check(f'{key}:{name}:coverage', close(row['coverage_total'],acc/total) and close(row['coverage_qc_pass'],acc/n), f'row={row["coverage_total"]},{row["coverage_qc_pass"]} calc={acc/total},{acc/n}')
                    for occname in ('assignment_occupancy','accepted_occupancy'):
                        vals=labels[mask] if occname=='assignment_occupancy' else labels[mask & accepted]
                        counts=np.bincount(vals,minlength=k); occupied=int(np.count_nonzero(counts));
                        if len(vals):
                            p=counts[counts>0]/counts.sum(); eff=float(np.exp(-(p*np.log(p)).sum())); largest=float(p.max())
                            ok=row[occname]['occupied']==occupied and close(row[occname]['effective_vocabulary'],eff) and close(row[occname]['largest_token_fraction'],largest)
                        else: ok=row[occname]['occupied']==0 and row[occname]['effective_vocabulary']==0 and row[occname]['largest_token_fraction'] is None
                        check(f'{key}:{name}:{occname}',ok,'occupancy mismatch')
            # stored threshold is scalar and matches metrics.
            threshold=float(mod[key+'__threshold'])
            check(f'{key}:threshold', close(threshold,m['ood_threshold']), f'{threshold} vs {m["ood_threshold"]}')
        # Agreement rows: recompute all ARI/AMI including label permutation invariance.
        for j,row in enumerate(metrics['agreements']):
            a,b,name=row['a'],row['b'],row['group']; mask=groups[name]; inter=mask & ass[a+'__accepted'] & ass[b+'__accepted']
            for field, x,y in [('all_qc_pass',ass[a][mask],ass[b][mask]),('accepted_intersection',ass[a][inter],ass[b][inter])]:
                expected_n=len(x); calc_ari=None if expected_n<2 else adjusted_rand_score(x,y); calc_ami=None if expected_n<2 else adjusted_mutual_info_score(x,y)
                stored=row[field]
                check(f'agreement_{j}_{field}', stored['n']==expected_n and ((stored['ari'] is None and calc_ari is None) or close(stored['ari'],calc_ari,1e-10)) and ((stored['ami'] is None and calc_ami is None) or close(stored['ami'],calc_ami,1e-10)), f'{row["a"]}/{row["b"]}/{name} {field}')
            denom=int(mask.sum()); calc_int=float(inter.sum()/denom) if denom else None
            check(f'agreement_{j}_intersection', (row['intersection_over_qc_pass'] is None and calc_int is None) or close(row['intersection_over_qc_pass'],calc_int), f'{row["a"]}/{row["b"]}/{name}')
        # Models export has expected core arrays and finite values.
        for key in model_names:
            for suffix in ('scale_mean','scale_std','centroids','threshold','wave_reconstruction','spectrum_reconstruction'):
                arr=mod[key+'__'+suffix]
                check(f'{key}:{suffix}:finite', np.all(np.isfinite(arr)), 'nonfinite model array')
        # Header-level pickle scan for every npz member.
        for fn in ('assignments.npz','evaluation-index.npz','models.npz'):
            bad=[]
            with zipfile.ZipFile(RES/fn) as z:
                for name in z.namelist():
                    raw=z.read(name)
                    if b'object' in raw[:512] or b'\x80\x04' in raw[:512]: bad.append(name)
            check(f'{fn}_pickle_header_scan', not bad, str(bad))
    # Recomputed label permutation invariance and basic calibration boundary.
    check('ari_permutation_invariant', close(adjusted_rand_score([0,0,1,1],[7,7,2,2]),1.0), 'ARI failed neutral relabeling')
    # Source hash table should bind every current top-level eegt/protocol regular file.
    expected_hashes={str(f.relative_to(IN)):sha256(f) for folder in ('eegt','protocol') for f in sorted((IN/folder).glob('*')) if f.is_file()}
    check('metrics_source_hash_binding', metrics['source_hashes']==expected_hashes, 'metrics source hash table differs from current code/protocol')
    # No executable pickle in result archive; report omitted derived array as a limitation rather than a failure.
    check('analysis_wave_source_declared', isinstance(metrics.get('analysis_waves_sha256'),str) and len(metrics['analysis_waves_sha256'])==64, str(metrics.get('analysis_waves_sha256')))
    check('interpretation_scope', 'no universal' in metrics.get('interpretation','').lower() and 'semantic' in metrics.get('interpretation','').lower(), metrics.get('interpretation',''))
    print(json.dumps({'checks':checks,'failures':findings,'n_checks':len(checks),'n_failures':len(findings)}, indent=2, sort_keys=True))
    return 1 if findings else 0
if __name__=='__main__': raise SystemExit(main())
