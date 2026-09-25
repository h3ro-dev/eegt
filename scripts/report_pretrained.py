"""Render the frozen pretrained comparison, including an insufficient-data result."""
from collections import Counter
from pathlib import Path
import html
import json
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from eegt.acquire import ROOT, digest
from eegt.corpus import atomic_json
from report_repeated import table


def run(root=ROOT):
    root = Path(root)
    s = json.loads((root/'results/009/summary.json').read_text())
    p = json.loads((root/'results/009/prepared.json').read_text())
    inference = json.loads((root/'results/009/inference.json').read_text())
    for path, sha in s['inputs'].items():
        if digest(root/path) != sha: raise ValueError('analysis inputs changed')
    if digest(root/'results/009/analysis.sqlite') != s['analysis_sha256']:
        raise ValueError('database changed')
    t = s['totals']
    names = {'morphology':'Waveform shape', 'spectrum':'Spectrum', 'coordination':'Sensor coordination'}
    eligible = [r for r in p['records'] if r['status']=='ELIGIBLE']
    counts = Counter((r['source_subject'],r['session']) for r in eligible)
    pairs = sorted({(r['source_subject'],r['session']) for r in p['records']})
    coverage = [[person,session,counts[(person,session)],20] for person,session in pairs]
    ch = ['Source participant','Night','Eligible blocks','Candidate blocks']
    primary = [[r['metric'], names[r['view']], r['valid_blocks'], r['complete_participants'],
                r['status'], 'Not estimated' if 'p_greater' not in r else f"{r['p_bonferroni_six']:.4f}"]
               for r in s['primary_statistics']]
    ph = ['Comparison','View','Valid blocks','Complete participants','Outcome','Adjusted p']
    if any(r['status']!='INSUFFICIENT_PARTICIPANTS' for r in s['primary_statistics']):
        raise ValueError('this report text requires the observed insufficient-participant result')
    block_rows = []
    by_key = {(r['candidate_index'],r['view']):r for r in s['block_comparisons']}
    fmt = lambda value: 'Undefined' if value is None else f'{value:.3f}'
    for row in eligible:
        comparisons = [by_key[(row['candidate_index'],view)] for view in names]
        block_rows.append([row['candidate_index'],f"{row['source_subject']} / {row['session']}",row['start_seconds'],
                           *[fmt(c['geometry']) for c in comparisons], *[fmt(c['change']) for c in comparisons]])
    bh = ['Candidate','Person / night','Start (s)','Shape geometry','Spectrum geometry','Coordination geometry',
          'Shape change','Spectrum change','Coordination change']
    reason_rows = [[reason,count] for reason,count in s['rejection_counts'].items()]
    intro = (f"A pinned pretrained CodeBrain encoder completed {inference['block_variant_runs']} forward passes: "
             f"{t['eligible_blocks']} original segments and four waveform controls for each. "
             f"Only {t['eligible_blocks']} of {t['candidate_blocks']} candidate 30-second segments passed the frozen quality rules "
             f"({100*t['eligible_blocks']/t['candidate_blocks']:.2f}%); this is {t['eligible_seconds']/60:.1f} minutes from two selected hours.")
    finding = ('The planned participant-level test cannot be estimated. No participant has the required three eligible '
               'segments in both nights; the protocol requires at least three such participants. All six primary comparisons '
               'report INSUFFICIENT_PARTICIPANTS. There is no population agreement estimate or p value from this run.')
    selection = ('We fixed the first ten minutes of each of twelve previously exposed EESM23 recordings before inspecting '
                 'encoder outputs. All 240 candidates remain in the ledger. Rejection reasons overlap; their counts must not '
                 'be added to obtain the number of rejected segments. The initial ten minutes are not representative of whole '
                 'nights and may include setup or calibration. No later segment replaced an excluded one.')
    method = ('The encoder receives only finite numeric wave arrays: four in-ear channels, 30 seconds, resampled from 250 to '
              '200 Hz and scaled from microvolts by dividing by 100. The fixed preprocessing uses a 0.3–75 Hz bandpass and '
              '60 Hz notch. The source metadata reports 50 Hz mains; this model-recipe notch does not specifically remove '
              'that component. Every filter, validity rule and transformation is in the protocol. No identity, demographics, '
              'sleep-stage or task label enters preprocessing or inference; anonymous source keys are used afterward for evaluation.')
    comparisons = ('For each segment, we average embeddings across four channels and retain 28 one-second patch centers. '
                   'Geometry means the rank correlation between all pairwise encoder cosine distances and the corresponding '
                   'frozen numerical descriptor distances. Change means the rank correlation of 27 adjacent-step distances. '
                   'These are continuous change magnitudes, not diagnosed states, matched inflection events or discrete token IDs. '
                   'A high segment correlation may reflect common filtering, oscillations or artifacts.')
    architecture = ('This runs the published CodeBrain EEGSSM backbone with fixed weights; it does not run the full discrete '
                    'dual tokenizer or an LLM decoder. The authors trained on 19 scalp channels. Accepting four ear channels '
                    'computationally does not validate their spatial meaning. Pretraining overlap is unknown. The only source '
                    'portability edits move an attention mask to the input device and use a relative import; the adapter restores '
                    'the batch axis. Every checkpoint key is loaded strictly with safe weights-only loading.')
    controls = ('Every eligible segment is also run at half amplitude, with polarity reversed, with channel positions reversed, '
                'and with independent Fourier-phase randomization per channel. These are matched waveform probes. '
                'The JSON retains all 36 control comparisons, including undefined values and amplitude excursions. '
                'Participant-balanced control summaries are also unavailable because no person meets the two-night rule. '
                'We do not promote pooled segment summaries to a participant result.')
    conclusion = ('This experiment establishes a reproducible CPU execution path and exposes a sampling/compatibility bottleneck. '
                  'It does not establish universal geometry, semantic meaning, clinical diagnostic accuracy or physical Neurable transfer. '
                  'The next comparison should preregister a time-distributed sample within the already exposed recordings, '
                  'audit amplitude and missing-data eligibility without inspecting encoder agreement, and require enough complete '
                  'participants before inference. Untouched people and later sessions remain reserved. A second independently '
                  'trained encoder and cycle/burst-level controls follow after that input problem is resolved.')
    source_links = ('[Frozen protocol](../protocol/experiment-009.json) · [All candidates](../results/009/prepared.json) · '
                    '[Numerical results](../results/009/summary.json) · [Execution receipt](../results/009/inference.json) · '
                    '[Release](https://github.com/h3ro-dev/eegt/releases/tag/v0.5.0)')
    note = '# Research Notes · Experiment 009\n\nDate: 2026-09-25. Pinned pretrained encoder feasibility and congruence.\n\n'
    note += intro+'\n\n'+finding+'\n\n## Frozen quality selection\n\n'+selection+'\n\n'
    note += table(ch,coverage)+'\n'+table(['Rejection reason','Candidate blocks'],reason_rows)+'\n'+method+'\n\n'
    note += '## Six planned primary comparisons\n\n'+table(ph,primary)+'\n'+comparisons+'\n\n'
    note += '## Segment-level observations\n\nThese nine rows are descriptive only; their source grouping and dependencies remain visible.\n\n'+table(bh,block_rows)+'\n'
    note += '## What was actually run\n\n'+architecture+'\n\n'+controls+'\n\n'
    note += ('Source: [EESM23 v1.0.0](https://openneuro.org/datasets/ds005178/versions/1.0.0), '
             '[dataset paper](https://doi.org/10.1038/s41597-025-04579-8), '
             '[CodeBrain official source](https://github.com/jingyingma01/CodeBrain/tree/22d350caf68246d2fda4f630ef837420db3fb130), '
             '[pinned public weights](https://huggingface.co/YjMajy/CodeBrain/tree/bef08d2fdb1759685371cc635aad21ce59163689). '
             'Source data are CC0; the vendored model source retains Apache-2.0 terms and attribution.\n\n')
    note += '## What follows\n\n'+conclusion+'\n\n'+source_links+'\n'
    (root/'notes/experiment-009.md').write_text(note)
    site=root/'site'
    fig,ax=plt.subplots(figsize=(10,4.8),layout='constrained')
    fig.patch.set_facecolor('#f8f6f0')
    positions=np.arange(len(pairs));n=np.array([counts[pair] for pair in pairs])
    ax.bar(positions,20-n,bottom=n,color='#d8ddd8',label='Excluded')
    ax.bar(positions,n,color='#146550',label='Eligible')
    ax.set(xticks=positions,xticklabels=[f'{a}\nnight {b}' for a,b in pairs],ylim=(0,22),
           ylabel='30-second candidate segments',title='Frozen selection: 9 eligible segments out of 240')
    ax.legend(frameon=False,ncol=2);ax.spines[['top','right']].set_visible(False)
    fig.savefig(site/'data/pretrained-eligibility.png',dpi=170);plt.close(fig)
    sections = [('The input bottleneck',selection+''),('Wave-only input',method),('The representation',architecture)]
    body = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>EEGT · Experiment 009 · A pretrained view</title><meta name="description" content="A public pretrained EEG encoder ran on nine eligible ear-EEG segments. The planned participant test lacks enough data.">'
            '<link rel="stylesheet" href="styles.css"><style>main.model{max-width:1160px;margin:auto;padding:60px 24px}.model section{padding:32px 0;border-top:1px solid #d9dedb}.model h1{font-size:clamp(2.5rem,6vw,4.6rem);line-height:1.06;margin:24px 0}.model h2{font-size:1.7rem;margin-bottom:18px}.model p{max-width:85ch;margin:18px 0;line-height:1.7}.model table{width:100%;border-collapse:collapse;font-size:.85rem}.model th,.model td{text-align:left;padding:13px 9px;border-bottom:1px solid #d9dedb;vertical-align:top}.table-scroll{overflow:auto}.model img{width:100%;height:auto}.stats{display:flex;gap:34px;flex-wrap:wrap;margin:32px 0}.stats strong{display:block;font-size:2.1rem}</style></head><body><a class="skip-link" href="#main">Skip to content</a><main class="model" id="main">'
            '<a href="./">← EEGT research notebook</a><p class="eyebrow">Research Notes · Experiment 009</p><h1>A pretrained view.<br>An input bottleneck.</h1>'
            '<p>An LLM’s interpretation of your brainwaves · Open methods research</p>'
            '<div class="stats"><div><strong>9 / 240</strong>eligible segments</div><div><strong>45</strong>model forward passes</div><div><strong>0</strong>complete eligible participant pairs</div></div>')
    body += '<p>'+html.escape(intro)+'</p><p><strong>'+html.escape(finding)+'</strong></p>'
    body += '<section><h2>Every candidate stays visible</h2><p>'+html.escape(selection)+'</p><img src="data/pretrained-eligibility.png" alt="Twelve recordings each supply twenty candidates. Eligible counts by person and night are listed in the following table; nine pass in total.">'+table(ch,coverage,True)+table(['Rejection reason','Candidate blocks'],reason_rows,True)+'</section>'
    body += '<section><h2>Six planned comparisons</h2>'+table(ph,primary,True)+'<p>'+html.escape(comparisons)+'</p></section>'
    body += '<section><h2>The nine segment observations</h2><p>Descriptive rank correlations, with source grouping retained. These rows do not establish participant-level agreement.</p>'+table(bh,block_rows,True)+'</section>'
    for title,text in sections[1:]:body += '<section><h2>'+title+'</h2><p>'+html.escape(text)+'</p></section>'
    body += '<section><h2>Waveform controls</h2><p>'+html.escape(controls)+'</p></section><section><h2>What follows</h2><p>'+html.escape(conclusion)+'</p></section>'
    body += '<section><h2>Reproduce and inspect</h2><p><a href="https://github.com/h3ro-dev/eegt/blob/main/notes/experiment-009.md">Full Research Note and sources</a> · <a href="data/pretrained.json">All numerical results</a> · <a href="https://github.com/h3ro-dev/eegt/releases/tag/v0.5.0">Versioned data, source and checksums</a></p></section></main></body></html>'
    (site/'pretrained.html').write_text(body)
    atomic_json(site/'data/pretrained.json',s)
    for path in ['pretrained.html','data/pretrained.json','data/pretrained-eligibility.png']:
        shutil.copyfile(site/path,root/path)
    atomic_json(root/'results/009/report.json',dict(schema='eegt-pretrained-report/v1',
        inputs={path:digest(root/path) for path in ['results/009/summary.json','scripts/report_pretrained.py']},
        outputs={path:digest(root/path) for path in ['notes/experiment-009.md','site/pretrained.html','site/data/pretrained.json','site/data/pretrained-eligibility.png']}))


if __name__=='__main__':run()
