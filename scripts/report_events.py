"""Render Experiment 012 from its complete, immutable numerical record.

Presentation only: no detector calls, model forwards, selection or new tests.
"""
from collections import defaultdict
import hashlib
import html
import json
from pathlib import Path
import shutil
import sqlite3


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def primary_rows(summary):
    rows = []
    for endpoint in summary['primary_endpoints']:
        complete = {p['person'] for p in endpoint['participants'] if p['status'] == 'COMPLETE'}
        rows.append(dict(model=endpoint['model'], metric=endpoint['metric'], people=len(complete),
                         primary_blocks=sum(r['paired_valid_blocks'] for r in endpoint['records'] if r['person'] in complete),
                         all_paired_valid_blocks=endpoint['paired_valid_blocks'], **endpoint['test']))
    return rows


def collect(root):
    source = root / 'results/012/summary.json'
    summary = json.loads(source.read_text())
    progress = json.loads((root / 'results/012/run-progress.json').read_text())
    if summary['status'] != 'COMPLETE_NUMERICAL_RECORD' or progress['completed_blocks'] != 122:
        raise ValueError('complete 122-block scientific record required')
    db_path = root / 'results/012/analysis.sqlite'
    db = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        counts = {t: db.execute('SELECT count(*) FROM ' + t).fetchone()[0] for t in
                  ('candidates', 'partitions', 'native_match', 'prepared_metric', 'block_effect', 'completed_blocks')}
        expected = dict(candidates=5760, partitions=2806, native_match=99552,
                        prepared_metric=2440, block_effect=488, completed_blocks=122)
        if counts != expected or db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('incomplete or corrupt numerical index')
        controls = defaultdict(lambda: dict(strata=0, undefined_strata=0, n_a=0, n_b=0, matched=0))
        for variant, tolerance, receipt in db.execute('SELECT variant,tolerance_seconds,receipt_json FROM native_match'):
            r = json.loads(receipt)
            d = controls[variant, tolerance]
            d['strata'] += 1
            d['undefined_strata'] += r['agreement'] is None
            for key in ('n_a', 'n_b', 'matched'):
                d[key] += r[key]
        control_rows = []
        for (variant, tolerance), values in sorted(controls.items()):
            denominator = values['n_a'] + values['n_b']
            control_rows.append(dict(variant=variant, tolerance_seconds=tolerance, **values,
                                     pooled_agreement=2 * values['matched'] / denominator if denominator else None))
        native_counts = dict(zip(('candidate_event_rows', 'accepted_event_rows', 'rejected_event_rows'),
                                db.execute("SELECT sum(event_rows),sum(accepted_rows),sum(rejected_rows) FROM partitions WHERE branch='native' AND variant='primary'").fetchone()))
    finally:
        db.close()
    noise = []
    for name, row in sorted(summary['synthetic_noise_false_detection'].items()):
        for method, values in sorted(row['oscillation_subsets']['all100'].items()):
            noise.append(dict(noise=name, method_and_band=method, trials=values['scored_trials'],
                              trials_with_detection=values['false_detection_trials_n'],
                              detection_rows=values['false_detection_rows_n']))
    return dict(schema='eegt-012-presentation/v1', summary_sha256=sha(source), index_sha256=sha(db_path),
                primary=primary_rows(summary), native_controls=control_rows, native_primary=native_counts,
                index_counts=counts, noise_controls=noise, resources=progress, full_scientific_summary=summary)


def table(headers, rows, web=False):
    if web:
        cells = lambda row, tag: ''.join(f'<{tag}>{html.escape(str(v))}</{tag}>' for v in row)
        return '<div class="table-scroll"><table><thead><tr>' + cells(headers, 'th') + '</tr></thead><tbody>' + ''.join('<tr>' + cells(row, 'td') + '</tr>' for row in rows) + '</tbody></table></div>'
    return '| ' + ' | '.join(headers) + ' |\n| ' + ' | '.join(['---'] * len(headers)) + ' |\n' + ''.join('| ' + ' | '.join(map(str, row)) + ' |\n' for row in rows)


def number(value):
    return 'not estimable' if value is None else f'{value:.4f}'


def resolution_text(primary):
    largest = max(r['people'] for r in primary)
    if largest < 2:
        return 'No endpoint has two complete people, so no participant-level exact test is estimable.'
    minimum = 2 / 2 ** largest
    return (f'The largest eligible endpoint has {largest} complete people. Its smallest attainable two-sided raw p is '
            f'2/{2 ** largest} = {minimum:g}; with four primary tests the smallest adjusted p is {min(1, 4 * minimum):g}. '
            'A smaller eligible sample makes resolution coarser. These p values are not probabilities that a universal language exists. '
            'New people supply independent replication; thousands of windows from the same people do not.')


def noise_text(rows):
    trials = sorted({r['trials'] for r in rows})
    cycles = [r for r in rows if r['method_and_band'].startswith('bycycle_1.2.0:')]
    universal_detection = bool(cycles) and all(r['trials_with_detection'] == r['trials'] for r in cycles)
    description = ('Cycle events occurred in every scored trial for all listed noise/band combinations. '
                   if universal_detection else 'Cycle detections varied across the scored noise/band combinations. ')
    return (f'The earlier synthetic battery scored {", ".join(map(str, trials))} independently seeded trials per listed condition, '
            'using white or colored noise without a planted oscillator. ' + description +
            'The table reports every condition, including burst detections. A detected oscillation or turning point cannot by itself establish a biological state. '
            'These are numerical control detections, not clinical false-positive rates.')


def run(root=ROOT):
    root = Path(root)
    data = collect(root)
    primary = data['primary']
    summary = data['full_scientific_summary']
    title = 'Measuring where the waveform turns.'
    tested = [r for r in primary if r['p_bonferroni_four'] is not None]
    positive = sum(r['p_bonferroni_four'] < .05 for r in tested)
    intro = (f"We measured extrema, inflections, cycles and bursts on 122 previously selected ear-EEG segments. "
             f"Of four prespecified event-to-encoder tests, {len(tested)} were estimable and {positive} had an adjusted p below 0.05. "
             'This measures numerical relationships; it does not establish universal tokens or diagnose brain states.')
    primary_table = (['Encoder', 'Metric', 'Paired people', 'Primary blocks', 'Mean paired difference', 'Raw p', 'Adjusted p'],
                     [[r['model'], r['metric'], r['people'], r['primary_blocks'], number(r['observed_mean']),
                       number(r['p_two_sided']), number(r['p_bonferroni_four'])] for r in primary])
    control_table = (['Input change', 'Eligible original events', 'Eligible changed events', 'Matched', 'Pooled agreement', 'Undefined strata / all'],
                     [[r['variant'], r['n_a'], r['n_b'], r['matched'], number(r['pooled_agreement']),
                       f"{r['undefined_strata']} / {r['strata']}"] for r in data['native_controls'] if r['tolerance_seconds'] == .025])
    noise_table = (['Noise', 'Method and band (Hz)', 'Trials with detection / scored', 'Detected rows'],
                   [[r['noise'], r['method_and_band'], f"{r['trials_with_detection']} / {r['trials']}", r['detection_rows']] for r in data['noise_controls']])
    resources = data['resources']
    native = data['native_primary']
    middle = {r['variant']: r for r in data['native_controls'] if r['tolerance_seconds'] == .025}
    unavailable = [name for name, row in middle.items() if row['pooled_agreement'] is None]
    control_interpretation = (f"Independently phase-randomized signals still have pooled landmark agreement {number(middle['independent_phase']['pooled_agreement'])} at 25 milliseconds. "
                              'Dense landmarks and a nonzero matching tolerance can produce high agreement even after local timing is disrupted; this is not evidence of the same brain state. '
                              'Gain, offset and aligned polarity controls test expected numerical invariances. ')
    if unavailable:
        control_interpretation += 'The following controls have no estimable pooled agreement after the frozen support rules: ' + ', '.join(unavailable) + '. Undefined comparisons are retained, not scored as zero or perfect agreement.'
    sections = [
        ('The question', 'Do recurring turns in the signal provide a useful numerical description, and do two fixed EEG encoders reflect that description? A reproducible landmark is a starting point. Universality would additionally require stability across new people, sessions, devices and datasets. No semantic or clinical labels enter this experiment.'),
        ('What a turn means here', 'An extremum is a peak or trough in a filtered signal; an inflection is a change in curvature. These are separately defined derivative events. We also retain cycle shape, period, amplitude, slope, curvature, rise/decay asymmetry and two burst definitions. These engineered measurements are not automatically transitions between biological states. Waveform path length, turning angle and return distance remain undefined because no direct-waveform geometry was frozen for them.'),
        ('The complete denominator', f"The earlier census had 5,760 candidate thirty-second blocks, 2,973 quality passes and 122 time-selected blocks from six people and twelve recordings. Those 122 blocks represent 61 selected minutes within 48 already examined hours. This run adds zero source people or hours and makes zero new encoder forward passes. The native primary branch retains {native['candidate_event_rows']:,} event candidates: {native['accepted_event_rows']:,} accepted and {native['rejected_event_rows']:,} rejected. These counts include different and overlapping event families; they are not independent tokens or additional recordings."),
        ('Direct events and two encoders', 'The native branch analyzes the original selected 250 Hz microvolt data with 18 frozen variants. A separate branch analyzes five archived 200 Hz variants used by CodeBrain and CBraMod. For that comparison, accepted peaks, troughs and the two inflection directions form a 16-component count vector for each one-second interval across four channels. Geometry compares pairwise cosine-distance ranks; change compares adjacent-interval distance ranks. Each learned encoder vector still has whole-block context. These tests associate event-count patterns with continuous embeddings; they do not localize the models’ causal attention or learn a discrete vocabulary.'),
        ('Four primary tests', 'For each model and metric, the block effect is original event-to-embedding correlation minus its independently phase-randomized counterpart. A common complete support is required. Zero norms, insufficient intervals and arithmetically constant distance sequences abstain. Each recording needs at least three paired valid blocks; we take its median effect, average two nights, then weight each complete person equally. The table counts only blocks from complete people. All excluded people, nights and blocks remain in the machine-readable record. The exact two-sided sign-flip test assumes independent people and sign symmetry; four-test Bonferroni adjustment was frozen before output.'),
        ('The resolution of the test', resolution_text(primary)),
        ('Do landmarks survive changes to the input?', 'Every control is retained: gain, polarity, offset, known time shift, reference, passband, smoothing, line noise, phase, clipping and impulses. Synthetic gap tests are retained separately in the earlier detector validation. The table shows the middle prespecified tolerance, 25 milliseconds; 10 and 50 milliseconds are also reported in the data. Known time shifts and polarity are explicitly aligned. Matching requires full support inside common guarded intervals and one-to-one pairs. Pooled agreement is twice matched events divided by eligible events in both signals. It is a descriptive event-weighted score, not a participant-level test. Empty strata remain undefined, never perfect agreement.'),
        ('How to read high agreement and missing comparisons', control_interpretation),
        ('Cycles and bursts also occur in noise', noise_text(data['noise_controls'])),
        ('Support, filtering and exposure', 'Every candidate and rejection remains in a compressed, hash-bound ledger with masks, filter coefficients, transformed input hashes and temporal support. Native event filtering and the inherited 200 Hz encoder preprocessing are distinct. Encoder inputs retain the earlier 0.3–75 Hz passband, 60 Hz notch and µV/100 scaling; the source reports 50 Hz mains. Neither this numerical scale nor successful execution proves scalp-to-ear positional or physiological calibration equivalence. Pretraining overlap remains unknown. The six development people and their selected nights are exposed data; reserved people 007–010 and later sessions remain untouched.'),
        ('Anonymous measurements still have assumptions', 'Input arrays contain wave values without identity, history, task or semantic labels. Curator keys join only for provenance and evaluation so repeated nights are not counted as independent people. Filtering, detector definitions, model pretraining and one-second bins still encode assumptions. Agreement among these procedures is evidence to investigate, not proof of an assumption-free or universal representation.'),
        ('Runtime and a transparent storage expansion', f"The complete detection and aggregation record reports {resources['cumulative_cpu_seconds']:.2f} CPU seconds, {resources['cumulative_wall_seconds']:.2f} cumulative work seconds and {resources['process_peak_rss_bytes']/1024**2:.1f} MiB peak process RSS. Work seconds exclude idle time between checkpoints. The first block projected more than the original 3 GB artifact ceiling. After verifying the checkpoint on a second host, the lead raised only storage to 6 GB, preserving the two-hour CPU and 2 GiB memory limits. Actual analysis artifacts total {resources['analysis_artifact_bytes']:,} bytes. Code and methods were frozen before the first empirical event call; no thresholds or tests were tuned on these results. Native provider cost is UNKNOWN. There was no paid API call per window."),
        ('Reproduce and continue', 'The release includes all 2,806 compressed partitions, the queryable SQLite index, exact selected numerical arrays, both archived latent arrays, frozen source, tests and reviews. The offline command verifies every partition and recomputes matching, correlations, participant aggregation and the complete scientific summary. It replays the archived event ledger; detector regeneration is a separate operation. The next dependency is a locked protocol for untouched people and later sessions, followed by its run and a consolidated provenance database. Negative and inconclusive findings remain part of that ledger.')]
    tables = {'Four primary tests': primary_table, 'Do landmarks survive changes to the input?': control_table,
              'Cycles and bursts also occur in noise': noise_table}
    links = [('Frozen protocol', 'https://github.com/h3ro-dev/eegt/blob/main/protocol/experiment-012.json'),
             ('Exact methods', 'https://github.com/h3ro-dev/eegt/blob/main/protocol/experiment-012-methods.md'),
             ('Reproduction instructions', 'https://github.com/h3ro-dev/eegt/blob/main/REPRODUCE-012.md'),
             ('Data release v0.8.0', 'https://github.com/h3ro-dev/eegt/releases/tag/v0.8.0'),
             ('EESM23 source', 'https://openneuro.org/datasets/ds005178/versions/1.0.0')]
    note = '# Research Notes · Experiment 012\n\nSeptember 2026 · ' + title + '\n\n' + intro + '\n\n'
    for heading, paragraph in sections:
        note += '## ' + heading + '\n\n' + paragraph + '\n\n'
        if heading in tables:
            note += table(*tables[heading]) + '\n'
    note += '## Sources and data\n\n' + ' · '.join(f'[{label}]({url})' for label, url in links) + '\n'
    (root / 'notes/experiment-012.md').write_text(note)
    site = root / 'site'
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout='constrained')
    fig.patch.set_facecolor('#f8f6f0')
    for ax, endpoint in zip(axes.flat, summary['primary_endpoints'], strict=True):
        people = [p for p in endpoint['participants'] if p['status'] == 'COMPLETE']
        ax.axvline(0, color='#adb5ac', lw=1)
        ax.scatter([p['effect'] for p in people], range(len(people)), color='#146550')
        ax.set(yticks=range(len(people)), yticklabels=['Person ' + p['person'] for p in people],
               xlabel='Original minus phase: mean of two night medians',
               title=endpoint['model'] + ' · ' + endpoint['metric'] + '\nadjusted p = ' + number(endpoint['test']['p_bonferroni_four']))
        ax.spines[['top', 'right']].set_visible(False)
        ax.invert_yaxis()
    fig.savefig(site / 'data/events-summary.png', dpi=170)
    plt.close(fig)
    body = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EEGT · Experiment 012 · Waveform turns</title><meta name="description" content="A reproducible comparison of direct waveform landmarks and two pretrained EEG encoders, with full controls and exclusions."><link rel="stylesheet" href="styles.css"><style>main.study{max-width:1160px;margin:auto;padding:60px 24px}.study section{padding:28px 0;border-top:1px solid #d9dedb}.study h1{font-size:clamp(2.5rem,6vw,4.6rem);line-height:1.06;margin:24px 0}.study h2{font-size:1.7rem;margin-bottom:18px}.study p{max-width:88ch;margin:18px 0;line-height:1.7}.study table{width:100%;border-collapse:collapse;font-size:.85rem}.study th,.study td{text-align:left;padding:12px 9px;border-bottom:1px solid #d9dedb;vertical-align:top}.table-scroll{overflow:auto}.study img{width:100%;height:auto}</style></head><body><a class="skip-link" href="#main">Skip to content</a><main class="study" id="main"><a href="./">← EEGT research notebook</a><p class="eyebrow">Research Notes · Experiment 012 · September 2026</p><h1>' + title + '</h1><p><small>Project subtitle</small><br>An LLM’s interpretation of your brainwaves</p><p>This run measures numerical waveform landmarks. It does not interpret thoughts or run an LLM decoder.</p><p>' + html.escape(intro) + '</p><img src="data/events-summary.png" alt="One dot per complete person for each of four event-to-encoder comparisons. Zero marks no original-minus-phase difference; adjusted p values are printed in each panel.">'
    for heading, paragraph in sections:
        body += '<section><h2>' + html.escape(heading) + '</h2><p>' + html.escape(paragraph) + '</p>'
        if heading in tables:
            body += table(*tables[heading], web=True)
        body += '</section>'
    body += '<section><h2>Sources and reproducible data</h2><p>' + ' · '.join(f'<a href="{url}">{html.escape(label)}</a>' for label, url in links) + '</p><p><a href="data/events.json">All results, controls and exclusions</a> · <a href="cross-encoder.html">Earlier Experiment 011</a></p><p>EEGT source: MIT. Public EEG: CC0. Author source and model notices remain in the release; model checkpoints remain upstream.</p></section></main></body></html>'
    (site / 'events.html').write_text(body)
    (site / 'data/events.json').write_text(json.dumps(data, indent=2) + '\n')
    for relative in ('events.html', 'data/events-summary.png', 'data/events.json'):
        shutil.copyfile(site / relative, root / relative)


if __name__ == '__main__':
    run()
