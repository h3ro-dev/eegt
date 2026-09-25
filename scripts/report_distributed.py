"""Render Experiment 010 from its frozen candidate and comparison receipts."""
from collections import Counter
from pathlib import Path
import html
import json
import shutil
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eegt.acquire import ROOT


def markdown_table(headers, rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)


def html_table(headers, rows):
    cell=lambda value:html.escape(str(value))
    return '<div class="table-scroll"><table><thead><tr>'+''.join('<th scope="col">'+cell(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+cell(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def run(root=ROOT):
    root=Path(root)
    read=lambda path:json.loads((root/path).read_text())
    p=read('results/010/prepared.json');s=read('results/010/summary.json');inference=read('results/010/inference.json')
    t=p['totals'];rows=p['records'];pairs=sorted({(r['source_subject'],r['session']) for r in rows})
    qualified=Counter((r['source_subject'],r['session']) for r in rows if r['quality_status']=='PASS')
    selected=Counter((r['source_subject'],r['session']) for r in rows if r['status']=='ELIGIBLE')
    coverage=[[a,b,480,qualified[a,b],selected[a,b]] for a,b in pairs]
    ch=['Source person','Night','Candidate blocks','Quality-qualified','Selected']
    names={'morphology':'Waveform shape','spectrum':'Spectrum','coordination':'Sensor coordination'}
    primary=[]
    for r in s['primary_statistics']:
        people={v['source_subject'] for v in r['participants']}
        support=sum(v['blocks'] for v in r['records'] if v['source_subject'] in people)
        primary.append([r['metric'].capitalize(),names[r['view']],r['complete_participants'],support,
                        f"{r['observed_mean_participant_rho']:.4f}",f"{r['p_greater']:.4f}",f"{r['p_bonferroni_six']:.3f}"])
    ph=['Comparison','Numerical view','Paired people','Contributing blocks','Mean rho','Raw p','Adjusted p']
    controls=[]
    for variant in ('gain_half','polarity_flip','channel_reverse','independent_phase'):
        by={r['metric']:r for r in s['control_summaries'] if r['variant']==variant}
        controls.append([variant.replace('_',' '),f"{by['geometry_rho']['mean_participant_value']:.3f}",
                         f"{by['change_rho']['mean_participant_value']:.3f}",
                         f"{by['rms_embedding_displacement']['mean_participant_value']:.3f}"])
    coh=['Waveform control','Geometry vs original rho','Change vs original rho','Embedding RMS displacement']
    intro=(f"The fixed pretrained EEG backbone completed {inference['block_variant_runs']:,} forward passes on {t['eligible_blocks']} "
           f"time-distributed segments and four controls per segment. Five people supplied enough selected data from both nights. "
           "The three geometry comparisons show weak positive alignment; the three change-profile comparisons do not clear the adjusted tests.")
    selection=(f"We checked all {t['candidate_blocks']:,} nonoverlapping thirty-second blocks in the already examined first four hours "
               f"of twelve EESM23 recordings. {t['quality_qualified_blocks']:,} passed the unchanged combined numerical quality gate "
               f"({100*t['quality_qualified_blocks']/t['candidate_blocks']:.2f}%, {t['quality_qualified_seconds']/3600:.3f} hours). "
               f"In each fixed twenty-minute interval we selected the lower temporal median qualifying block: {t['eligible_blocks']} blocks, "
               f"or {t['eligible_seconds']/60:.0f} minutes. Selection used quality and time only, before encoder outputs. "
               "This adds no source recordings, people or source hours. It is a new analysis of previously exposed data.")
    denominator=("Quality-qualified means passing the fixed signal/model-compatibility rules, not accuracy or biological validity. "
                 f"{t['rejected_blocks']:,} blocks fail quality; {t['qualified_unselected_blocks']:,} pass but are not selected by the time rule. Rejection reasons overlap and must not be summed. "
                 "All selected blocks are kept in the descriptive results. Person 003 has only one selected block in the first night, "
                 "so that person's twelve selected blocks do not enter the paired estimates. Each primary result uses five people, ten recordings and 110 blocks.")
    finding=("Mean geometry rank correlations are 0.0815 for waveform shape, 0.0381 for spectrum and 0.0419 for sensor coordination. "
             "All three exceed the specified cyclic-shift null with adjusted p = 0.003. These are small effects. "
             "Mean change-profile correlations are 0.0342, 0.0141 and 0.0270; adjusted p values are 0.387, 1.000 and 0.639. "
             "This run does not establish agreement in transition timing or a universal wave language.")
    definition=("Geometry compares pairwise distances among 28 one-second patch vectors inside each selected segment: encoder cosine "
                "distances versus frozen numerical-descriptor distances. Change compares the 27 adjacent-step distances. "
                "These are continuous measurements, not discrete inflection events or diagnosed brain states. The descriptors and their "
                "normalization were frozen previously; no codebook or model is fitted here.")
    inference_text=("Correlations are aggregated as a median within a recording, then a mean over the two nights, then a mean over five people. "
                    "We do not treat the 110 contributing blocks as 110 independent people. Each of 1,999 null replicates applies a nonzero cyclic "
                    "shift within each block and repeats the same aggregation; Bonferroni correction covers all six tests. The p values are conditional "
                    "on this shift construction. Nonstationary EEG can violate its exchangeability assumption, and these values are not probabilities "
                    "that universal geometry exists. They also do not prove that individual patterns repeat across nights.")
    control_text=("The same selected signals are run at half amplitude, with reversed polarity, with reversed channel order, and with independent "
                  "Fourier-phase randomization in each channel. These summaries compare the encoder with itself under each transformation; they do "
                  "not establish cross-model agreement. High half-gain agreement and low phase-randomized agreement suggest sensitivity to temporal "
                  "organization, while polarity and channel changes still affect the representation. This does not separate neural structure from artifacts.")
    method=("Inputs contain only four numeric ear-EEG channels, native microvolts, thirty seconds at 250 Hz, bandpassed at 0.3–75 Hz, "
            "notched at 60 Hz, resampled to 200 Hz and divided by 100. The source reports 50 Hz mains; the retained 60 Hz notch does not specifically "
            "remove it. Neither identity, history, sleep stage nor task labels enter the numerical functions or the encoder. Source keys remain in "
            "separate curator records for traceability and participant-level evaluation. No private NoticingMind waves or untouched participants were used.")
    limits=("This is the fixed CodeBrain EEGSSM continuous backbone, not the full discrete tokenizer or an LLM decoder. "
            "Its training on 19 scalp channels does not validate transfer to four ear contacts. Pretraining overlap is unknown. "
            "Shared filters, signal spectra, stable references, sensor effects and artifacts can explain agreement. The quality selection changes "
            "which parts of each night are represented; it is not a random or representative sample of all brain activity. No semantic, clinical, "
            "universal or physically calibrated Neurable claim is supported.")
    next_step=("The input bottleneck is resolved for a bounded five-person comparison under this rule. Next, freeze a second compatible, independently "
               "trained encoder and cycle/burst plus artifact/reference controls on exposed data. Compare change events explicitly if testing inflection "
               "geometry. Preserve participants 007–010 and unexamined later sessions until the new method is fixed. Publish the weak and null results alongside future outcomes.")
    sections=[('A frozen selection across time',selection),('What the denominators mean',denominator),('Weak geometry, unconfirmed transitions',finding),
              ('What geometry and change measure',definition),('How the tests work',inference_text),('Waveform controls',control_text),
              ('Numeric input and fixed preprocessing',method),('What this cannot establish',limits),('Next experiment',next_step)]
    sources=('[EESM23 v1.0.0](https://openneuro.org/datasets/ds005178/versions/1.0.0) · '
             '[CodeBrain pinned source](https://github.com/jingyingma01/CodeBrain/tree/22d350caf68246d2fda4f630ef837420db3fb130) · '
             '[Frozen protocol](../protocol/experiment-010.json) · [All candidate rows](../results/010/prepared.json) · '
             '[Results](../results/010/summary.json) · [Validation](validation-010.md) · '
             '[Release v0.6.0](https://github.com/h3ro-dev/eegt/releases/tag/v0.6.0)')
    note='# Research Notes · Experiment 010\n\nDate: 2026-09-25. Time-distributed pretrained comparison on exposed ear EEG.\n\n'+intro+'\n\n'
    for title,text in sections:
        note+='## '+title+'\n\n'+text+'\n\n'
        if title=='A frozen selection across time':note+=markdown_table(ch,coverage)+'\n'
        if title=='Weak geometry, unconfirmed transitions':note+=markdown_table(ph,primary)+'\n'
        if title=='Waveform controls':note+=markdown_table(coh,controls)+'\n'
    note+='## Rejection ledger\n\n'+markdown_table(['Reason','Blocks'],list(p['rejection_counts'].items()))+'\n'+sources+'\n'
    (root/'notes/experiment-010.md').write_text(note)
    site=root/'site';(site/'data').mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(2,1,figsize=(10.5,7.5),layout='constrained',height_ratios=[1.3,1])
    fig.patch.set_facecolor('#f8f6f0');x=np.arange(12)
    q=np.array([qualified[pair] for pair in pairs]);n=np.array([selected[pair] for pair in pairs])
    axes[0].bar(x,n,color='#146550',label='Selected for encoder')
    axes[0].bar(x,q-n,bottom=n,color='#82aa98',label='Qualified, unselected')
    axes[0].bar(x,480-q,bottom=q,color='#d9dedb',label='Rejected')
    axes[0].set(xticks=x,xticklabels=[f'{a}\nnight {b}' for a,b in pairs],ylim=(0,500),ylabel='30-second blocks',title='5,760 candidates → 2,973 quality-qualified → 122 selected')
    axes[0].legend(frameon=False,ncol=3,fontsize=8)
    labels=[r['metric']+' / '+names[r['view']] for r in s['primary_statistics']]
    values=[r['observed_mean_participant_rho'] for r in s['primary_statistics']]
    axes[1].scatter(values,np.arange(6),color=['#146550']*3+['#7f7667']*3,zorder=3)
    axes[1].axvline(0,color='#c5ccc5',lw=1)
    axes[1].set(yticks=np.arange(6),yticklabels=labels,xlim=(-1,1),xlabel='Mean participant rank correlation (rho)',title='Small geometry effects; change tests do not clear correction')
    axes[1].invert_yaxis()
    for ax in axes:ax.spines[['top','right']].set_visible(False)
    fig.savefig(site/'data/distributed-summary.png',dpi=170);plt.close(fig)
    body='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EEGT · Experiment 010 · Weak shared geometry</title><meta name="description" content="A time-distributed EEG sample supports a five-person pretrained comparison: weak geometry alignment, no adjusted change-profile finding."><link rel="stylesheet" href="styles.css"><style>main.study{max-width:1160px;margin:auto;padding:60px 24px}.study section{padding:28px 0;border-top:1px solid #d9dedb}.study h1{font-size:clamp(2.5rem,6vw,4.6rem);line-height:1.06;margin:24px 0}.study h2{font-size:1.7rem;margin-bottom:18px}.study p{max-width:88ch;margin:18px 0;line-height:1.7}.study table{width:100%;border-collapse:collapse;font-size:.85rem}.study th,.study td{text-align:left;padding:12px 9px;border-bottom:1px solid #d9dedb;vertical-align:top}.table-scroll{overflow:auto}.study img{width:100%;height:auto}.stats{display:flex;gap:32px;flex-wrap:wrap;margin:32px 0}.stats strong{display:block;font-size:2.1rem}</style></head><body><a class="skip-link" href="#main">Skip to content</a><main class="study" id="main"><a href="./">← EEGT research notebook</a><p class="eyebrow">Research Notes · Experiment 010 · September 25, 2026</p><h1>More usable waves.<br>Weak shared geometry.</h1><p>An LLM’s interpretation of your brainwaves · Open methods research</p><div class="stats"><div><strong>5,760</strong>blocks checked</div><div><strong>122</strong>blocks selected</div><div><strong>5</strong>paired people</div><div><strong>610</strong>model forward passes</div></div><p>'+html.escape(intro)+'</p><img src="data/distributed-summary.png" alt="Quality and selection counts for twelve recordings, followed by the six small mean correlation effects on a scale from minus one to one.">'
    for title,text in sections:
        body+='<section><h2>'+title+'</h2><p>'+html.escape(text)+'</p>'
        if title=='A frozen selection across time':body+=html_table(ch,coverage)
        if title=='Weak geometry, unconfirmed transitions':body+=html_table(ph,primary)
        if title=='Waveform controls':body+=html_table(coh,controls)
        body+='</section>'
    body+='<section><h2>Every exclusion stays visible</h2>'+html_table(['Reason','Blocks'],list(p['rejection_counts'].items()))+'<p>Reason counts overlap. A block can fail more than one criterion.</p><p><a href="data/distributed.json">Full numerical results</a> · <a href="https://github.com/h3ro-dev/eegt/blob/main/protocol/experiment-010.json">Frozen protocol</a> · <a href="https://github.com/h3ro-dev/eegt/blob/main/notes/validation-010.md">Validation</a> · <a href="https://github.com/h3ro-dev/eegt/releases/tag/v0.6.0">Code and data release</a> · <a href="pretrained.html">Earlier Experiment 009</a></p></section></main></body></html>'
    (site/'distributed.html').write_text(body)
    (site/'data/distributed.json').write_text(json.dumps(dict(experiment='010',totals=t,inference_gate=p['inference_gate'],
        primary_statistics=s['primary_statistics'],control_summaries=s['control_summaries'],rejection_counts=p['rejection_counts'],coverage=coverage),indent=2)+'\n')
    for path in ['distributed.html','data/distributed.json','data/distributed-summary.png']:
        (root/path).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(site/path,root/path)


if __name__=='__main__':run()
