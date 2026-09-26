"""Render Experiment 011 directly from the frozen comparison outputs."""
from pathlib import Path
import html
import json
import shutil
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eegt.acquire import ROOT


def table(headers, rows, web=False):
    if web:
        cells = lambda values, tag: ''.join(f'<{tag}>{html.escape(str(v))}</{tag}>' for v in values)
        return '<div class="table-scroll"><table><thead><tr>' + cells(headers, 'th') + '</tr></thead><tbody>' + ''.join('<tr>' + cells(row, 'td') + '</tr>' for row in rows) + '</tbody></table></div>'
    return '| ' + ' | '.join(headers) + ' |\n| ' + ' | '.join(['---'] * len(headers)) + ' |\n' + ''.join('| ' + ' | '.join(map(str, row)) + ' |\n' for row in rows)


def run(root=ROOT):
    root = Path(root)
    s = json.loads((root / 'results/011/summary.json').read_text())
    inf = json.loads((root / 'results/011/inference.json').read_text())
    primary = []
    for p in s['primary']:
        a = p['aggregates']
        people = {r['source_subject'] for r in a['delta']['participants'] if r['status'] == 'COMPLETE'}
        blocks = sum(r['valid_blocks'] for r in a['delta']['records'] if r['source_subject'] in people)
        primary.append([p['metric'].capitalize(), len(people), blocks,
                        f"{a['original_rho']['mean_participant_value']:.4f}",
                        f"{a['independent_phase_rho']['mean_participant_value']:.4f}",
                        f"{a['delta']['mean_participant_value']:.4f}",
                        f"{p['test']['p_two_sided']:.4f}", f"{p['test']['p_bonferroni_two']:.3f}"])
    ph = ['Measurement', 'Paired people', 'Blocks', 'Original rho', 'Phase rho', 'Paired difference', 'Raw p', 'Adjusted p']
    cross = []
    for variant in inf['variants']:
        entries = {r['metric']: r['aggregate'] for r in s['secondary'] if r['family'] == 'cross_model' and r['variant'] == variant}
        cross.append([variant.replace('_', ' '), f"{entries['geometry']['mean_participant_value']:.4f}", f"{entries['change']['mean_participant_value']:.4f}"])
    ch = ['Input to both models', 'Geometry rho', 'Change-profile rho']
    within = []
    for model in ('codebrain', 'cbramod'):
        for variant in inf['variants'][1:]:
            entries = {r['metric']: r['aggregate'] for r in s['secondary'] if r['family'] == 'within_model' and r['model'] == model and r['variant'] == variant}
            within.append([model, variant.replace('_', ' '), *[f"{entries[m]['mean_participant_value']:.4f}" for m in ('geometry_rho', 'change_rho', 'rms_embedding_displacement')]])
    wh = ['Model', 'Control vs original', 'Geometry rho', 'Change rho', 'Embedding RMS displacement']
    desc = []
    for model in ('codebrain', 'cbramod'):
        for view in ('morphology', 'spectrum', 'coordination'):
            entries = {r['metric']: r['aggregate'] for r in s['secondary'] if r['family'] == 'descriptor' and r['model'] == model and r['view'] == view}
            desc.append([model, view, f"{entries['geometry']['mean_participant_value']:.4f}", f"{entries['change']['mean_participant_value']:.4f}"])
    dh = ['Model', 'Numerical descriptor', 'Geometry rho', 'Change rho']

    title = 'Two encoders. Some alignment. An open question.'
    intro = ('CodeBrain and CBraMod show modest agreement on the same ear-EEG segments. In each of the five paired people, '
             'both primary paired original-minus-phase effects are positive. '
             'The adjusted tests remain inconclusive: p = 0.125 for geometry and change. This does not establish universal tokens.')
    sections = [
        ('What was measured', 'We reused the 122 thirty-second inputs selected in Experiment 010, including its five input variants per segment. '
         'CBraMod completed 610 new forward passes; the 610 archived CodeBrain outputs were reused after input/output hash checks. '
         'These are two fixed pretrained EEG encoders producing continuous vectors. No discrete vocabulary is learned here, and no LLM decoder runs.'),
        ('The paired result', 'Geometry compares the rankings of 378 pairwise cosine distances among 28 one-second patch vectors. '
         'Change compares the 27 adjacent-step distances. Channels are averaged and the first/last patches are excluded; each retained vector still has the model’s whole thirty-second context. '
         'These are within-segment relationships, not directly localized waveform inflections or evidence that a particular event repeats across nights.'),
        ('Why five people matters', 'The primary analysis uses five people, ten recordings and 110 selected blocks. All 122 blocks from six people and twelve recordings remain in descriptive outputs. '
         'Person 003 has one selected block in the first night and fails the unchanged minimum of three per night. '
         'Each block’s effect is original rho minus phase-control rho. We take the median of those differences within a recording, the mean across its person’s two nights, and then an unweighted mean across complete people. '
         'Separately summarized original and phase medians need not subtract to the paired difference.'),
        ('The test cannot settle this with five people', 'The exact two-sided sign-flip test enumerates all 32 sign assignments to the five person-level effects. '
         'Both outcomes reach its smallest attainable raw p value, 2/32 = 0.0625. Correcting the two primary tests gives 0.125. '
         'That resolution limit was specified before the run; we did not change tests after seeing the outcome. The test also assumes independent people and sign symmetry under a zero effect. '
         'A larger effect or more windows cannot overcome this five-person resolution limit. These p values are not probabilities that a universal language exists.'),
        ('What the phase control removes', 'Both models receive the same independently phase-randomized signal for each block. This preserves each channel’s Fourier magnitudes while changing local timing and relations among channels. '
         'It is a nuisance comparison, not a complete biological null. Positive agreement also remains after this transformation, so shared spectra, processing or other structure can contribute. '
         'The cross-model table reports all five variants without selecting a winner.'),
        ('How each model responds to controls', 'These descriptive rows compare each encoder with itself under four input changes. Correlations and embedding displacement answer different questions. '
         'No secondary p values were calculated. All per-block, recording and person rows, including exclusions, are available in the data release.'),
        ('Transparent numerical comparisons', 'The original inputs also retain the frozen waveform-shape, spectral and sensor-coordination descriptor comparisons. '
         'These reference views have explicit engineered assumptions. Their descriptive correlations do not give the learned vectors semantic meaning.'),
        ('Anonymous input, learned priors', 'The model input contains only four numerical ear channels: no identity, history, sleep-stage, task or semantic labels. '
         'Curator keys join only during evaluation so that two nights from one person are not counted as two independent people. '
         'The pretrained encoders carry learned priors, and our filters and patching impose choices. Anonymous numerical input is therefore not an assumption-free blank slate. '
         'Both source architectures were developed with scalp EEG; four-ear-channel execution does not validate spatial equivalence. Pretraining overlap remains unknown.'),
        ('Exposure and preprocessing', 'The 61 selected minutes come from the already examined first four hours of twelve EESM23 recordings. '
         'The preceding census contained 5,760 candidate blocks, of which 2,973 passed fixed quality rules; selection used quality and time rather than model agreement. '
         'This experiment adds no source people or recorded hours. Participants 007–010 and unexamined later sessions remain reserved. '
         'The inherited input processing is 0.3–75 Hz, a 60 Hz notch, resampling from 250 to 200 Hz and scaling calibrated microvolts as µV/100. '
         'That numerical scale follows the documented CodeBrain pretraining convention and the audited CBraMod trainer. It does not validate amplitude distributions, reference/calibration equivalence or four-ear-channel positional mapping against either model’s scalp pretraining inputs. '
         'Our per-block filtering is an EEGT engineering choice, not byte-identical author preprocessing. The source reports 50 Hz mains, so the 60 Hz notch does not specifically remove it. '
         'The first and last selected blocks had already been used in adapter checks; this is exposed development data, not pristine validation.'),
        ('Reproducibility and corrections', f"The new inference took {inf['elapsed_seconds']:.2f} seconds with one numerical thread and about {inf['maximum_rss_native']/1024**2:.1f} MiB peak process RSS. "
         'The protocol and initial code manifest were sealed before inference. A later analysis amendment fixed integer serialization and removed an unnecessary checkpoint-file requirement from offline evaluation. '
         'It changed no metric, selection, aggregation or model forward; the original code, failed partial output and amendment remain available. '
         'A separate calculation checked 6,858 scalar/hash/database assertions; its largest numerical discrepancy was below 4×10⁻¹⁶. '
         'Offline reproduction matched all scientific values and SQLite contents. Database file hashes can differ across SQLite runtimes. Native agent monetary cost is UNKNOWN; no paid model API call was made per window.'),
        ('What comes next', 'Test direct extrema, inflections, cycles and bursts against known synthetic waves, noise, gaps and artifacts, then compare their timing on exposed EEG under a new frozen protocol. '
         'After the methods are fixed, test new people and new sessions separately and incorporate the newly qualified open-data intake into a consolidated database. '
         'Shared numerical structure is worth testing further; semantic meaning, diagnosis and physical Neurable transfer remain unestablished.')
    ]
    source_links = [
        ('EESM23 source v1.0.0', 'https://openneuro.org/datasets/ds005178/versions/1.0.0'),
        ('Pinned CodeBrain source', 'https://github.com/jingyingma01/CodeBrain/tree/22d350caf68246d2fda4f630ef837420db3fb130'),
        ('CodeBrain pretraining convention', 'https://arxiv.org/html/2506.09110v4'),
        ('CBraMod pretraining scale', 'https://github.com/wjq-learning/CBraMod/blob/b9e961003214326972c567eff390e75b0287e32a/pretrain_trainer.py#L58-L73'),
        ('Pinned CBraMod source', 'https://github.com/wjq-learning/CBraMod/tree/b9e961003214326972c567eff390e75b0287e32a'),
        ('Pinned CBraMod weights', 'https://huggingface.co/weighting666/CBraMod/blob/500543c7e30bda1b22bfd51a49301b238dee21fd/pretrained_weights.pth'),
        ('Frozen protocol', 'https://github.com/h3ro-dev/eegt/blob/v0.7.0/protocol/experiment-011.json'),
        ('Validation record', 'https://github.com/h3ro-dev/eegt/blob/v0.7.0/notes/validation-011.md'),
        ('Release and data', 'https://github.com/h3ro-dev/eegt/releases/tag/v0.7.0')]
    tables = {'The paired result': (ph, primary), 'What the phase control removes': (ch, cross),
              'How each model responds to controls': (wh, within), 'Transparent numerical comparisons': (dh, desc)}
    note = '# Research Notes · Experiment 011\n\nSeptember 25, 2026 · ' + title + '\n\n' + intro + '\n\n'
    for heading, text in sections:
        note += '## ' + heading + '\n\n' + text + '\n\n'
        if heading in tables:
            note += table(*tables[heading]) + '\n'
    note += '## Sources and data\n\n' + ' · '.join(f'[{label}]({url})' for label, url in source_links) + '\n\n'
    note += 'Public EEG source: CC0. EEGT and CBraMod source: MIT. CodeBrain source and pretrained checkpoint notices retain their upstream terms; CBraMod checkpoint card declares Apache-2.0. Checkpoints remain upstream.\n'
    (root / 'notes/experiment-011.md').write_text(note)

    site = root / 'site'
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), layout='constrained')
    fig.patch.set_facecolor('#f8f6f0')
    for row, p in enumerate(s['primary']):
        people = [r['source_subject'] for r in p['aggregates']['delta']['participants'] if r['status'] == 'COMPLETE']
        get = lambda field: [next(r['mean_two_sessions'] for r in p['aggregates'][field]['participants'] if r['source_subject'] == person) for person in people]
        a, b, d = get('original_rho'), get('independent_phase_rho'), get('delta')
        for i in range(5):
            axes[row, 0].plot([b[i], a[i]], [i, i], color='#b2bbb3', zorder=1)
        axes[row, 0].scatter(b, range(5), color='#8a7d69', marker='s', label='Phase control')
        axes[row, 0].scatter(a, range(5), color='#146550', label='Original')
        axes[row, 0].set(yticks=range(5), yticklabels=['Person ' + x for x in people], xlim=(-.1, .4), xlabel='Mean of two night medians (rho)', title=p['metric'].capitalize() + ': original and phase')
        axes[row, 1].scatter(d, range(5), color='#146550')
        axes[row, 1].axvline(0, color='#aeb5ac', lw=1)
        axes[row, 1].set(yticks=range(5), yticklabels=people, xlim=(-.05, .25), xlabel='Mean of two night median paired differences', title='All five effects positive · adjusted p = 0.125')
        for ax in axes[row]:
            ax.invert_yaxis()
            ax.spines[['top', 'right']].set_visible(False)
    axes[0, 0].legend(frameon=False, fontsize=9, loc='lower right')
    fig.savefig(site / 'data/cross-encoder-summary.png', dpi=170)
    plt.close(fig)
    body = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EEGT · Experiment 011 · Two encoders</title><meta name="description" content="Two pretrained EEG encoders show modest agreement; five-person adjusted tests remain inconclusive."><link rel="stylesheet" href="styles.css"><style>main.study{max-width:1160px;margin:auto;padding:60px 24px}.study section{padding:28px 0;border-top:1px solid #d9dedb}.study h1{font-size:clamp(2.5rem,6vw,4.6rem);line-height:1.06;margin:24px 0}.study h2{font-size:1.7rem;margin-bottom:18px}.study p{max-width:88ch;margin:18px 0;line-height:1.7}.study table{width:100%;border-collapse:collapse;font-size:.85rem}.study th,.study td{text-align:left;padding:12px 9px;border-bottom:1px solid #d9dedb;vertical-align:top}.table-scroll{overflow:auto}.study img{width:100%;height:auto}.stats{display:flex;gap:32px;flex-wrap:wrap;margin:32px 0}.stats strong{display:block;font-size:2.1rem}</style></head><body><a class="skip-link" href="#main">Skip to content</a><main class="study" id="main"><a href="./">← EEGT research notebook</a><p class="eyebrow">Research Notes · Experiment 011 · September 25, 2026</p><h1>' + title + '</h1><p><small>Project subtitle</small><br>An LLM’s interpretation of your brainwaves</p><p>This run compares numerical EEG encoders. It does not interpret thoughts or run an LLM decoder.</p><div class="stats"><div><strong>2</strong>pretrained encoders</div><div><strong>122</strong>selected blocks</div><div><strong>5</strong>paired people</div><div><strong>610</strong>new forward passes</div></div><p>' + html.escape(intro) + '</p><img src="data/cross-encoder-summary.png" alt="Original and phase-control correlations for each of five people, with positive paired geometry and change effects; both adjusted tests are inconclusive at p equals 0.125.">'
    for heading, text in sections:
        body += '<section><h2>' + html.escape(heading) + '</h2><p>' + html.escape(text) + '</p>'
        if heading in tables:
            body += table(*tables[heading], web=True)
        body += '</section>'
    body += '<section><h2>Sources and reproducible data</h2><p>' + ' · '.join(f'<a href="{url}">{html.escape(label)}</a>' for label, url in source_links) + '</p><p>Public EEG: CC0; project and CBraMod code: MIT. Upstream model notices are retained; checkpoints remain upstream.</p><p><a href="data/cross-encoder.json">All numerical results and exclusions</a> · <a href="distributed.html">Earlier Experiment 010</a></p></section></main></body></html>'
    (site / 'cross-encoder.html').write_text(body)
    (site / 'data/cross-encoder.json').write_text(json.dumps(s, indent=2) + '\n')
    for rel in ['cross-encoder.html', 'data/cross-encoder.json', 'data/cross-encoder-summary.png']:
        shutil.copyfile(site / rel, root / rel)


if __name__ == '__main__':
    run()
