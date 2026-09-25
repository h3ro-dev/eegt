"""Build traceable research notes and a static website from sealed run results."""
from collections import defaultdict
import html
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eegt.acquire import ROOT,digest
from eegt.corpus import atomic_json
from eegt.growth import bootstrap,json_ready,VIEWS


def grouped(record):
    if record['split']=='external': return 'external_exposed' if record['prior_exposure'] else 'external_unexposed'
    return record['split']


def pooled_agreement(rows):
    groups=defaultdict(lambda: [0,0,0])
    for row in rows:
        key=f"{row['view_a']} / {row['view_b']} @ {row['scale']}s"
        groups[key][0]+=row['n_a'];groups[key][1]+=row['n_b'];groups[key][2]+=row['matched']
    return {k:dict(n_a=a,n_b=b,matched=m,f1=2*m/(a+b) if a+b else None) for k,(a,b,m) in groups.items()}


def fmt(stat):
    if stat['median'] is None:return 'NA'
    value=f"{stat['median']:.3f}"
    if stat['ci95'] is not None:value+=f" [{stat['ci95'][0]:.3f}, {stat['ci95'][1]:.3f}]"
    return value+f"; n={stat['n']}"


def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(x) for x in r)+' |\n' for r in rows)


def html_table(headers,rows):
    esc=lambda x:html.escape(str(x))
    return '<div style="overflow:auto"><table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def main():
    root=ROOT
    corpus=json.loads((root/'results/corpus-v1/summary.json').read_text())
    result=json.loads((root/'results/003/summary.json').read_text())
    controls=json.loads((root/'results/006/summary.json').read_text())
    if digest(root/'results/003/analysis.sqlite')!=result['analysis_sha256']:raise ValueError('analysis database changed')
    if digest(root/'results/corpus-v1/corpus.sqlite')!=corpus['corpus_sha256']:raise ValueError('corpus database changed')
    for key,expected in result['inputs'].items():
        if digest(root/key)!=expected:raise ValueError('analysis input changed: '+key)
    for key,expected in controls['inputs'].items():
        if digest(root/key)!=expected:raise ValueError('control input changed: '+key)
    groups=defaultdict(list)
    for r in result['records']:groups[grouped(r)].append(r)
    group_summary={}
    pair_keys=[f'{a} / {b} @ 2.0s' for a,b in [('morphology','spectrum'),('morphology','coordination'),('spectrum','coordination')]]
    for group,records in groups.items():
        agreement=[pooled_agreement(r['agreement']) for r in records]
        group_summary[group]=dict(records=len(records),windows=sum(r['windows'] for r in records),valid_windows=sum(r['valid_windows'] for r in records),agreement={key:bootstrap([a.get(key,{}).get('f1') for a in agreement]) for key in pair_keys},rates={v:bootstrap([r['event_counts'][v+':2.0']['events_per_scored_minute'] for r in records]) for v in VIEWS})
    control_summary={}
    for variant in ['original','independent_phase','shared_phase','gain_1.1','polarity_reverse','time_reverse']:
        chosen=[r for r in controls['records'] if r['status']=='EVALUATED']
        bygroup={}
        for group in groups:
            rr=[r for r in chosen if grouped(r)==group];agreements=[pooled_agreement(r['variants'][variant]['agreement']) for r in rr]
            bygroup[group]=dict(records=len(rr),valid_windows=sum(r['variants'][variant]['valid_windows'] for r in rr),agreement={key:bootstrap([a.get(key,{}).get('f1') for a in agreements]) for key in pair_keys},rates={},paired_rate_difference={})
            for v in VIEWS:
                key=v+':2.0'
                bygroup[group]['rates'][v]=bootstrap([r['variants'][variant]['event_counts'][key]['events_per_scored_minute'] for r in rr])
                differences=[]
                for r in rr:
                    pair=r['variants'][variant].get('paired_support')
                    if not pair:continue
                    a=pair['original']['event_counts'][key]['events_per_scored_minute'];b=pair['variant']['event_counts'][key]['events_per_scored_minute']
                    if a is not None and b is not None:differences.append(b-a)
                bygroup[group]['paired_rate_difference'][v]=bootstrap(differences)
        control_summary[variant]=bygroup
    report=dict(schema='eegt-transfer-summary/v1',groups=group_summary,controls=control_summary,
        input_hashes={p:digest(root/p) for p in ['results/corpus-v1/summary.json','results/003/summary.json','results/006/summary.json','scripts/report_growth.py']},
        aggregation='Pool event-match counts within each recording; bootstrap medians across source participant-recordings. Empty/empty event sets are missing for aggregate F1, not perfect biological agreement. Intervals are descriptive, not simultaneous or confirmatory confidence bounds.')
    atomic_json(root/'results/007/summary.json',json_ready(report),immutable=True)
    crows=[[r['dataset_id'],r['status'],r['source_participant_records'],r['source_sessions'],f"{r['recording_hours']:.2f}" if r['recording_hours'] is not None else 'NA'] for r in corpus['coverage']]
    headers=['Source','Status','Participant records','Sessions','Recorded hours']
    frows=[[g,s['records'],f"{s['valid_windows']:,}/{s['windows']:,}",*[fmt(s['agreement'][k]) for k in pair_keys]] for g,s in group_summary.items()]
    fheaders=['Group','Records','Valid/all multichannel windows','Shape / spectrum F1','Shape / coordination F1','Spectrum / coordination F1']
    rates=[[g,*[fmt(s['rates'][v]) for v in VIEWS]] for g,s in group_summary.items()]
    rheaders=['Group','Shape changes/min','Spectrum changes/min','Coordination changes/min']
    ctrlrows=[]
    for variant,g in control_summary.items():
        s=g.get('external_unexposed')
        if s:ctrlrows.append([variant,s['records'],s['valid_windows'],*[fmt(s['agreement'][k]) for k in pair_keys]])
    cheaders=['Control','Records','Valid windows','Shape / spectrum F1','Shape / coordination F1','Spectrum / coordination F1']
    common='These are LLM-authored numerical representations, not independent pretrained LLMs discovering a language. F1 measures timing agreement within one second; it is not accuracy against brain-state labels. Neither high agreement nor a change score establishes semantic meaning, a diagnosis or universal geometry.'
    artifacts='[Protocol](../protocol/experiment-003.json) · [Methods](../protocol/transition-methods.md) · [Per-record main results](../results/003/summary.json) · [Control results](../results/006/summary.json) · [Transfer summary](../results/007/summary.json) · [Release downloads](https://github.com/h3ro-dev/eegt/releases)'
    (root/'notes/experiment-004.md').write_text('# Research Notes · Experiment 004\n\nDate: 2026-09-25. State: acquired and technically qualified.\n\n'+f"Acquired **{corpus['downloaded_verified_bytes']:,} verified bytes**, covering **{corpus['source_recordings']} source recordings**. **{corpus['qualified_recordings']}** qualify. Failed or quarantined records remain in the denominator.\n\n"+table(headers,crows)+'\nThese are source-local participant records; cross-source identity overlap is unknown. Recorded hours describe sample duration, not guaranteed unbroken wall-clock time. Source discontinuities are preserved in SQLite. Acquired exposure, analyzable windows and accepted context differ. A new overlapping window is not a new person.\n\n'+f"The transition run processed {result['totals']['windows']:,} two-second **multichannel** windows on a half-second grid; {result['totals']['valid_windows']:,} pass its engineering gate. Experiment 002 counted per-channel windows, so the window totals are not comparable.\n\n"+'The source snapshots are [ds004015 v1.0.2](https://openneuro.org/datasets/ds004015/versions/1.0.2) and [ds005207 v1.0.0](https://openneuro.org/datasets/ds005207/versions/1.0.0). This includes 19 available raw around-ear sleep files; the collection describes 20 study participants, which is not the same denominator.\n\n'+artifacts+'\n')
    (root/'notes/experiment-003.md').write_text('# Research Notes · Experiment 003\n\nDate: 2026-09-25. State: numerical transition analysis computed.\n\nWe measure changes in waveform morphology, spectrum and sensor coordination at 0.5-, 2- and 8-second context scales, using two-second windows stepped every half-second. A training-only median/IQR reference and training 95th-percentile threshold are fixed before evaluation. Primary results use the 2-second context; all scales remain in the database. Geometry records pre/post distance, trajectory length, speed, angle and endpoint return distance. These are multivariate changes, not raw-wave mathematical inflection points, inferred recovery or millisecond microstates.\n\n'+common+'\n\n'+table(fheaders,frows)+'\nEntries are per-record medians, participant-bootstrap 95% intervals and contributing record counts. Event counts are pooled over continuous segments within a recording before calculating F1; empty/empty cases contribute no evidence to this aggregate. The overlapping windows are not independent statistical units.\n\n'+artifacts+'\n')
    (root/'notes/experiment-006.md').write_text('# Research Notes · Experiment 006\n\nDate: 2026-09-25. State: bounded phase and nuisance control battery computed.\n\n'+f"{controls['evaluated_recordings']} of {controls['candidate_recordings']} source records have a technically eligible control segment. The first native continuous interval long enough is used: 120 central seconds with 12-second halos on each side. This is a bounded control sample, not all 235 metadata-hours; ineligible records retain reasons.\n\n"+'Independent Fourier phase randomization preserves each channel\'s Fourier magnitudes. Shared randomization also preserves cross-spectra. Both change temporal localization. The same frozen detector is applied, with validity counts and matched original/variant supports for rate comparisons. Gain×1.1, polarity reversal and time reversal test nuisance sensitivity; reversal is reported with reflected timing and separate quality exposure.\n\n'+table(cheaders,ctrlrows)+'\nThis table uses prior-unexposed external records and each variant\'s own valid support. Paired-support rate differences are in the machine-readable summary; do not interpret changes in the table as entirely biological when validity differs. These controls are not a complete biological null and are not clinical validation.\n\n'+common+'\n\n'+artifacts+'\n')
    (root/'notes/experiment-007.md').write_text('# Research Notes · Experiment 007\n\nDate: 2026-09-25. State: frozen transfer evaluation computed.\n\nThe split uses source participants 001–024 for fitting, 025–030 for validation reporting and 031–036 for same-source tests. Sleep records form an external dataset; 001/003 were previously explored and remain separated from the other 17. There is one recording per participant in these snapshots: repeated-session reliability and verified device transfer remain unmeasured.\n\nHeld-out means a participant did not teach the detector its reference or thresholds. It does not prove independence from an LLM\'s pretraining, erase earlier exploration, or establish the absence of a shared person across public archives.\n\n'+table(rheaders,rates)+'\nRates use eligible scored-window centers × 0.5 seconds as exposure, not raw wall-clock time. Entries are per-record medians with descriptive participant-bootstrap 95% intervals. No labels exist to turn these rates into accuracy, sensitivity or specificity. A changed rate on sleep data can reflect acquisition, channel count, reference, artifact mix or actual physiological differences.\n\n'+table(fheaders,frows)+'\n'+common+'\n\n'+artifacts+'\n')
    site=root/'site';(site/'data').mkdir(exist_ok=True)
    atomic_json(site/'data/growth.json',json_ready(dict(corpus=corpus['coverage'],totals=result['totals'],groups=group_summary,controls=control_summary)))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    names=[g for g in ['test','external_unexposed','external_exposed'] if g in group_summary]
    values=np.array([[group_summary[g]['agreement'][k]['median'] if group_summary[g]['agreement'][k]['median'] is not None else np.nan for g in names] for k in pair_keys])
    fig,ax=plt.subplots(figsize=(8.5,4));im=ax.imshow(values,vmin=0,vmax=1,cmap='Blues')
    ax.set_xticks(range(len(names)),[n.replace('_','\n')+f"\nn={group_summary[n]['records']}" for n in names]);ax.set_yticks(range(3),['Shape / spectrum','Shape / coordination','Spectrum / coordination'])
    for (y,x),v in np.ndenumerate(values):ax.text(x,y,'NA' if not np.isfinite(v) else f'{v:.3f}',ha='center',va='center',color='white' if v>.6 else '#152738')
    ax.set_title('Transition timing agreement · median participant-recording F1\n2-second context; 1-second match tolerance',pad=15);fig.colorbar(im,ax=ax,label='F1 agreement, not accuracy');fig.tight_layout();fig.savefig(site/'data/transition-agreement.png',dpi=170);plt.close(fig)
    links=''.join(f'<a class="button button-ink" href="https://github.com/h3ro-dev/eegt/blob/main/notes/experiment-{i:03d}.md">Experiment {i:03d}</a> ' for i in [3,4,6,7])
    hours=sum(r['recording_hours'] or 0 for r in corpus['coverage'])
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EEGT · Continuous corpus and transitions</title><meta name="description" content="Measured EEG database growth, transition geometry, noise controls and transfer results."><link rel="stylesheet" href="styles.css"><style>main.growth{{max-width:1120px;margin:auto;padding:60px 24px}}.growth section{{padding:35px 0;border-top:1px solid #d9dedb}}.growth h1{{font-size:clamp(2.4rem,5vw,4.3rem);line-height:1.08;margin:20px 0}}.growth h2{{font-size:1.8rem;margin-bottom:18px}}.growth p{{max-width:82ch;margin:16px 0;line-height:1.7}}.growth table{{width:100%;border-collapse:collapse;font-size:.86rem}}.growth th,.growth td{{padding:13px 10px;text-align:left;border-bottom:1px solid #d9dedb;vertical-align:top}}.growth th{{font-weight:600}}.growth .stats{{display:flex;gap:30px;flex-wrap:wrap;margin:32px 0}}.growth .stats strong{{display:block;font-size:2.1rem}}.growth img{{width:100%;height:auto;max-width:850px}}.growth .downloads{{display:flex;gap:10px;flex-wrap:wrap}}</style></head><body><a class="skip-link" href="#main">Skip to content</a><main id="main" class="growth"><a href="./">← EEGT research notebook</a><p class="eyebrow">Research Notes · 003 / 004 / 006 / 007</p><h1>More recordings.<br>Testable transitions.</h1><p>An LLM’s interpretation of your brainwaves</p><p>We expanded the public around-ear EEG corpus and tested whether different numerical views locate the same changes. Every reported result is linked to a frozen protocol and source record.</p><div class="stats"><div><strong>{corpus['source_recordings']}</strong>source participant-recordings</div><div><strong>{hours:.1f} h</strong>qualified sample hours</div><div><strong>{result['totals']['valid_windows']:,}</strong>QC-passing multichannel windows</div></div><p>{html.escape(common)}</p><section><h2>004 · The continuous corpus</h2>{html_table(headers,crows)}<p>Source-local participant records are not a verified global person census. Gaps are retained. Overlapping windows add observations, not people. These are cEEGrid records; physical Neurable capture remains unverified.</p></section><section><h2>003 · Where do the methods agree?</h2><img src="data/transition-agreement.png" alt="Median per-recording boundary F1 for three pairs of numerical views. Exact values and denominators appear in the following table.">{html_table(fheaders,frows)}<p>Each entry is a participant-recording median, a descriptive95% bootstrap interval and the contributing count. Empty event sets contribute no aggregate evidence. Primary context is2seconds; matches must fall within1second.</p></section><section><h2>006 · Can controls produce similar structure?</h2>{html_table(cheaders,ctrlrows)}<p>The table shows prior-unexposed external records in a bounded120-second control sample, using each variant’s valid support. Paired-support rate differences and all groups are in the downloadable results. Phase-randomized signals can retain structure; these are limited controls, not a complete test of biological meaning.</p></section><section><h2>007 · Does the frozen detector transfer?</h2>{html_table(rheaders,rates)}<p>Rates are changes per minute of eligible scored-window centers. No known brain-state labels were used, so these numbers are not diagnostic accuracy. The external exposed group contains two records used earlier; the external input pool includes 17 previously unused records; the tables count those actually analyzed.</p></section><section><h2>005 · Neurable pilot</h2><p>Protocol prepared; physical data collection has not run. The next device step is a documented raw Research Kit export or supported stream, verified channel order and calibration, measured sample loss, and repeated sessions. Consumer focus summaries cannot substitute for raw EEG.</p><a href="https://github.com/h3ro-dev/eegt/blob/main/protocol/neurable-pilot.md">Read the capture protocol ↗</a></section><section><h2>Reproduce and inspect</h2><div class="downloads">{links}<a class="button button-ink" href="https://github.com/h3ro-dev/eegt/releases">Database downloads</a></div><p><a href="https://github.com/h3ro-dev/eegt">Source and tests</a> · <a href="https://github.com/h3ro-dev/eegt/blob/main/notes/research-intake-2026-09-25.md">Research context and next feature priorities</a> · <a href="data/growth.json">Machine-readable website results</a></p><p>Experiments001 and002 remain available in the earlier ledger. Numerical detection, clinical interpretation and a universal token vocabulary are separate claims.</p></section></main></body></html>'''
    # Normalize prose spacing without rewriting identifiers or artifact names.
    for a,b in [('descriptive95%','descriptive 95%'),('is2seconds','is 2 seconds'),('within1second','within 1 second'),('bounded120-second','bounded 120-second'),('contains17','contains 17'),('Experiments001','Experiments 001'),('and002','and 002')]:page=page.replace(a,b)
    (site/'growth.html').write_text(page)
    print(json.dumps(dict(source_recordings=corpus['source_recordings'],recorded_hours=hours,groups=group_summary),indent=2))


if __name__=='__main__':main()
