"""Render only the completed Experiment013 receipts; perform no statistical tests."""
import argparse
import hashlib
import html
import json
from pathlib import Path


def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def num(x): return 'not estimable' if x is None else f'{x:.5g}'
def table(headers, rows):
    cells=lambda values,tag: ''.join(f'<{tag}>{html.escape(str(x))}</{tag}>' for x in values)
    return '<div class="table-scroll"><table><thead><tr>'+cells(headers,'th')+'</tr></thead><tbody>'+''.join('<tr>'+cells(r,'td')+'</tr>' for r in rows)+'</tbody></table></div>'


def render(root):
    result=root/'results/013'; summary=read(result/'summary.json');prepared=read(result/'prepared.json');qualification=read(result/'qualification.json');eng=read(result/'engineering/summary.json')
    if summary['status']!='COMPLETE_NUMERICAL_RECORD' or eng['status']!='COMPLETE_TECHNICAL_RECORD': raise ValueError('Complete primary and engineering records required')
    protocol=read(root/'protocol/experiment-013.json')
    expected={(x['cohort'],x['model'],x['metric']) for x in protocol['primary_endpoints']}
    actual=[(x['cohort'],x['model'],x['metric']) for x in summary['primary_endpoints']]
    if len(actual)!=8 or len(expected)!=8 or set(actual)!=expected: raise ValueError('Eight fixed endpoint identities required')
    if summary['protocol_sha256']!=sha(root/'protocol/experiment-013.json') or summary['input_acceptance_sha256']!=sha(result/'INPUT-ACCEPTANCE.json'): raise ValueError('Presentation input bindings changed')
    totals=prepared['totals']; tests=summary['primary_endpoints']
    endpoints=[]
    for e in tests:
        t=e['test'];complete={p['person'] for p in e['participants'] if p['status']=='COMPLETE'}
        endpoints.append([e['cohort'],e['model'],e['metric'],t['status'],t['n'],sum(r['paired_valid_blocks'] for r in e['records'] if r['person'] in complete),num(t['observed_mean']),num(t['p_two_sided']),num(t['p_bonferroni_eight'])])
    hours=sum(r['duration_seconds'] for r in qualification['records'] if r['status']=='QUALIFIED')/3600
    compared=sum(e['test']['status']=='COMPARED' for e in tests)
    significant=sum(e['test']['p_bonferroni_eight'] is not None and e['test']['p_bonferroni_eight']<.05 for e in tests)
    cohort_rows=[]
    for cid,gate in summary['cohort_inference_gates'].items():
        rows=[r for r in prepared['records'] if r['cohort']==cid]
        cohort_rows.append([cid,len(rows),sum(r['quality_status']=='PASS' for r in rows),sum(r['status']=='ELIGIBLE' for r in rows),gate['complete_participant_count'],gate['status']])
    models={name:read(result/f'inference-{name}.json') for name in ('codebrain','cbramod')}
    expected_model_blocks=sum(r['status']=='ELIGIBLE' and summary['cohort_inference_gates'][r['cohort']]['status']=='READY' for r in prepared['records'])
    fixed_variants=['original','gain_half','polarity_flip','channel_reverse','independent_phase']
    for name,d in models.items():
        if d['status']!='COMPLETE' or d['model']!=name or d['encoder_implementation']!='PINNED_CHECKPOINT': raise ValueError('Model completion/identity differs: '+name)
        if d['input_acceptance_sha256']!=summary['input_acceptance_sha256'] or d['prepared_receipt_sha256']!=sha(result/'prepared.json'): raise ValueError('Model input binding differs: '+name)
        if d['shape'][0]!=expected_model_blocks or d['variants']!=fixed_variants: raise ValueError('Model eligible support differs: '+name)
        if d['block_variant_runs']!=d['shape'][0]*len(d['variants']) or len(d['measurements'])!=d['block_variant_runs']: raise ValueError('Model forward census differs: '+name)
    model_text='; '.join(f"{name}: {d['block_variant_runs']} forwards ({d['shape'][0]} blocks × {len(d['variants'])} controls)" for name,d in models.items())
    payload={'schema':'eegt-013-presentation/v1','summary_sha256':sha(result/'summary.json'),'prepared_sha256':sha(result/'prepared.json'),'qualification_sha256':sha(result/'qualification.json'),'engineering_summary_sha256':sha(result/'engineering/summary.json'),'qualified_source_hours':hours,'totals':totals,'full_scientific_summary':summary,'engineering':eng,'models':{n:{k:v[k] for k in ['status','block_variant_runs','shape','resources','checkpoint_sha256']} for n,v in models.items()},'publication_state':'CANDIDATE_REVIEW_PENDING'}
    headline=f'{compared} of eight fixed comparisons were estimable; {significant} cleared the adjusted 0.05 threshold.'
    body=f'''<a href="./">← EEGT research notebook</a><p class="eyebrow">Research Notes · Experiment 013 · September 2026</p><h1>Fixed methods. New recordings.</h1><p><strong>Release candidate — independent output review and publication readback are pending.</strong></p><p>{headline} These are numerical comparisons of waveform events and two pretrained EEG encoders, not evidence of a universal language or a thought decoder.</p>
<section><h2>What was actually measured</h2><p>All 20 pinned recordings qualified, totaling {hours:.6f} source hours. The fixed first-four-hour candidate grid contains {totals['candidate_blocks']:,} thirty-second blocks. Quality rules passed {totals['quality_qualified_blocks']:,}; time-based selection retained {totals['eligible_blocks']}. Source hours, selected support and independent people are different denominators.</p>{table(['Cohort','Candidates','Quality pass','Selected blocks','Complete people at input gate','Input gate'],cohort_rows)}<p>The new-person cohort fails the frozen minimum of three complete participants. Its selected waveforms remain in the descriptive event ledger, but no model effects or primary tests are manufactured for that cohort. New-session evidence concerns new nights from development participants; it is not new-person replication.</p></section>
<section><h2>The complete eight-test family</h2><p>Geometry and change effects compare the original-minus-independent-phase event-to-encoder correlations. Fixed within-night medians are combined across both required nights, then tested at participant level. Missing results remain in the eight-test correction family.</p>{table(['Cohort','Model','Metric','Status','Test people','Primary paired blocks','Mean effect','Raw p','Adjusted p (×8)'],endpoints)}<p>With at most six complete people, the smallest possible two-sided exact p is 2/64 = 0.03125; multiplying by eight gives 0.25. This design cannot establish adjusted significance even with maximally consistent effects. Effect direction, magnitude, exclusions and replication limits are the useful record; thousands of windows do not create thousands of independent people.</p></section>
<section><h2>Captured evidence</h2><p>The ledger contains {summary['completed_event_blocks']} completed blocks and {summary['indexed_partitions']:,} event partitions. The pinned model runs are {model_text}, on the eligible new-session cohort. Selected inputs, masks, pinned model output hashes, partition membership and cohort gates remain linked to the frozen source.</p><p><a href="data/validation.json">Full results and exclusions as JSON</a>. The recorded-ledger replay checks every partition and recomputes comparisons and the scientific summary. It does not regenerate detectors or repeat neural inference.</p></section>
<section><h2>A separate 12-contact technical check</h2><p>EESM19 uses only the first 30 seconds of nights 005 and 006 from one source participant, all 12 true ear contacts and the documented validity masks. This check is descriptive and outside the eight primary endpoints. Four-channel encoders are not mapped onto these 12 contacts. Physiological calibration, reference equivalence and transfer to physical Neurable hardware remain unknown.</p></section>
<section><h2>Preserved failures and limits</h2><p>Qualification initially exceeded the unchanged 2 GiB memory cap. The first cleanup correction also exceeded it. An independently reviewed sequential-process correction retained the same decoder and scientific rules; all 20 sources subsequently qualified. The failed attempts and technical exposure history are preserved. There was no post-access threshold tuning or source replacement.</p><p>Waveform events can reflect reference, sensor and artifact structure. Encoder pretraining overlap is unknown. Continuous numerical embeddings are not discrete semantic tokens. Native provider monetary cost remains UNKNOWN; no paid API call was made per window.</p></section>
<section><h2>Reproduce</h2><p><a href="https://github.com/h3ro-dev/eegt/blob/main/protocol/experiment-013.json">Frozen protocol</a> · <a href="https://github.com/h3ro-dev/eegt/blob/main/REPRODUCE-013.md">Exact reproduction instructions</a> · <a href="https://github.com/h3ro-dev/eegt/releases/tag/v0.9.0">v0.9.0 release</a> · <a href="events.html">Earlier Experiment 012</a></p><p>The data release includes the recorded ledger and source. Full raw recordings and pinned checkpoint files remain upstream; the latter are declared hash-checked verifier dependencies even for replay.</p></section>'''
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EEGT · Experiment 013 · Fixed validation</title><link rel="stylesheet" href="styles.css"><style>main.study{max-width:1160px;margin:auto;padding:60px 24px}.study section{padding:28px 0;border-top:1px solid #d9dedb}.study h1{font-size:clamp(2.5rem,6vw,4.6rem);line-height:1.06;margin:24px 0}.study h2{font-size:1.7rem}.study p{max-width:88ch;margin:18px 0;line-height:1.7}.study table{width:100%;border-collapse:collapse;font-size:.85rem}.study th,.study td{text-align:left;padding:12px 9px;border-bottom:1px solid #d9dedb;vertical-align:top}.table-scroll{overflow:auto}</style></head><body><a class="skip-link" href="#main">Skip to content</a><main class="study" id="main">'''+body+'</main></body></html>'
    for prefix in [root,root/'site']:
        (prefix/'data').mkdir(exist_ok=True)
        (prefix/'validation.html').write_text(page)
        (prefix/'data/validation.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    return {'status':'CANDIDATE_RENDERED','summary_sha256':payload['summary_sha256'],'estimable':compared,'adjusted_significant':significant}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();print(json.dumps(render(a.root)))
