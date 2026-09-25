"""Render Experiment008 and build a queryable cross-release source index."""
from pathlib import Path
import html
import json
import sqlite3
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from eegt.acquire import ROOT,digest
from eegt.corpus import atomic_json,canonical_json
from eegt.repeated import read_json


def build_index(root):
    dest=root/'results/corpus-v2/corpus.sqlite';dest.parent.mkdir(parents=True,exist_ok=True)
    temp=dest.with_suffix('.partial');temp.unlink(missing_ok=True)
    db=sqlite3.connect(temp);db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
    CREATE TABLE recordings(recording_id TEXT PRIMARY KEY,dataset_id TEXT,source_subject TEXT,session_id TEXT,status TEXT,reason TEXT,sample_rate_hz REAL,channels INTEGER,duration_seconds REAL,catalog_origin TEXT,source_receipt_json TEXT);
    CREATE TABLE source_files(recording_id TEXT REFERENCES recordings(recording_id),path TEXT,bytes INTEGER,sha256 TEXT,PRIMARY KEY(recording_id,path));
    CREATE VIEW coverage AS SELECT dataset_id,status,COUNT(*) recordings,COUNT(DISTINCT source_subject) source_participants,SUM(duration_seconds)/3600.0 recorded_hours FROM recordings GROUP BY dataset_id,status;
    ''')
    old=sqlite3.connect(root/'results/corpus-v1/corpus.sqlite');old.row_factory=sqlite3.Row
    for row in old.execute('SELECT * FROM recordings ORDER BY recording_id'):
        r=dict(row)
        db.execute('INSERT INTO recordings VALUES (?,?,?,?,?,?,?,?,?,?,?)',(r['recording_id'],r['dataset_id'],r['source_subject'],r['session_id'],r['status'],r['reason'],r['sample_rate_hz'],r['eeg_channels'],r['duration_seconds'],'corpus-v1',canonical_json(r)))
    for r in old.execute('SELECT * FROM source_files ORDER BY recording_id,path'):
        db.execute('INSERT INTO source_files VALUES (?,?,?,?)',(r['recording_id'],r['path'],r['bytes'],r['sha256']))
    old.close()
    for r in read_json(root/'results/008/qualification.json')['records']:
        db.execute('INSERT INTO recordings VALUES (?,?,?,?,?,?,?,?,?,?,?)',(r['recording_id'],'ds005178',r['source_subject'],r['session'],r['status'],r['reason'],r.get('sample_rate_hz'),len(r.get('channels',[])),r.get('duration_seconds'),'008',canonical_json(r)))
        db.execute('INSERT INTO source_files VALUES (?,?,?,?)',(r['recording_id'],r['path'],r['bytes'],r['sha256']))
    db.commit();db.row_factory=sqlite3.Row
    coverage=[dict(r) for r in db.execute('SELECT * FROM coverage ORDER BY dataset_id,status')]
    totals=dict(candidate_recordings=db.execute('SELECT COUNT(*) FROM recordings').fetchone()[0],
        qualified_recordings=db.execute("SELECT COUNT(*) FROM recordings WHERE status='QUALIFIED'").fetchone()[0],
        qualified_hours=db.execute("SELECT SUM(duration_seconds)/3600 FROM recordings WHERE status='QUALIFIED'").fetchone()[0],
        source_local_participants=db.execute('SELECT COUNT(*) FROM (SELECT DISTINCT dataset_id,source_subject FROM recordings)').fetchone()[0],
        source_files=db.execute('SELECT COUNT(*) FROM source_files').fetchone()[0],
        verified_download_bytes=db.execute('SELECT SUM(bytes) FROM source_files').fetchone()[0])
    duplicates=[dict(r) for r in db.execute('SELECT sha256,COUNT(*) AS n FROM source_files GROUP BY sha256 HAVING COUNT(*)>1')]
    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('index integrity failed')
    db.close();temp.replace(dest)
    result=dict(schema='eegt-corpus-index/v2',coverage=coverage,totals=totals,duplicate_file_hashes=duplicates,
        source_hashes={p:digest(root/p) for p in ['results/corpus-v1/corpus.sqlite','results/008/catalog.sqlite','results/008/qualification.json']},
        database_sha256=digest(dest),limitation='Source-local participant counts do not establish unique global people. This index is an inventory, not a new analysis of earlier raw data.')
    atomic_json(root/'results/corpus-v2/summary.json',result)
    return result


def table(headers,rows,web=False):
    if web:
        return '<div class="table-scroll"><table><thead><tr>'+''.join('<th scope="col">'+html.escape(str(c))+'</th>' for c in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(c))+'</td>' for c in r)+'</tr>' for r in rows)+'</tbody></table></div>'
    return '| '+' | '.join(headers)+' |\n|'+'|'.join('---' for _ in headers)+'|\n'+''.join('| '+' | '.join(str(c) for c in r)+' |\n' for r in rows)


def run(root=ROOT):
    root=Path(root);s=read_json(root/'results/008/summary.json');q=read_json(root/'results/008/qualification.json');t=s['totals'];index=build_index(root)
    if s['analysis_sha256']!=digest(root/'results/008/analysis.sqlite'):raise ValueError('analysis changed')
    names={'morphology':'Waveform shape','spectrum':'Spectrum','coordination':'Sensor coordination'}
    rows=[]
    for v,name in names.items():
        r=s['paired_statistics'][v]
        if r.get('status')=='INSUFFICIENT_PAIRS':rows.append([name,r['n_pairs'],'NA','NA','NA','NA']);continue
        rows.append([name,r['n_pairs'],f"{r['same_person_mean_distance']:.3f}",f"{r['different_person_mean_distance']:.3f}",f"{r['permutation_p_lower']:.4f}",f"{r['p_bonferroni_three_views']:.4f}"])
    headers=['View','Pairs','Same-person distance','Different-person distance','Exact pairing p','Adjusted p (3 views)']
    per=[[r['source_subject'],r['session'],f"{r['valid_windows']:,}/{r['windows']:,}",f"{100*r['qc_pass_fraction']:.1f}%",*[f"{r['transition_rates'][v]['events_per_scored_minute']:.3f}" if r['transition_rates'][v]['events_per_scored_minute'] is not None else 'NA' for v in names]] for r in s['records']]
    ph=['Source participant','Night','QC-pass / all windows','QC-pass fraction','Shape changes/min','Spectrum changes/min','Coordination changes/min']
    intro=f"Twelve newly selected ear-EEG recordings from six source participants add **{t['full_qualified_hours']:.2f} qualified recorded hours**. We analyze the first four hours of each file: **{t['selected_analysis_hours']:.0f} hours**, **{t['windows']:,} overlapping multichannel windows**, and **{t['valid_windows']:,} QC-passing windows**. The full index now has **{index['totals']['qualified_recordings']} qualified recordings** and **{index['totals']['qualified_hours']:.2f} recorded hours** across three datasets."
    interpretation='Distances compare per-recording feature medians, in the frozen cEEGrid training coordinates, between the first two nights. Smaller means more similar within that view. These are session summaries, not matches between individual wave events or validated tokens. Distances cannot be compared across views as if they shared one universal coordinate system.'
    inference='The test enumerates every assignment of night-two summaries to night-one participants (720 assignments for six complete pairs). A low pairing p means the observed pairing is unusually close under that permutation model. It does not identify the cause: anatomy, electrode fit, reference and stable artifacts may contribute. Six selected participants do not support a population-wide universality claim; the adjustment covers the three prespecified primary views.'
    finding='Same-participant nights are closer on average in all three views. Waveform shape has the smallest raw pairing p, but all three adjusted p values exceed 0.05. This first six-person battery gives a limited recurrence signal, not decisive evidence of stable universal tokens.'
    boundaries='The numerical methods receive only wave arrays, sampling rate and technical validity. The evaluator uses anonymous source grouping keys to pair nights after descriptors are fixed. No sleep stages, diaries, demographic fields or clinical labels enter the analysis. The first four hours can include calibration and wakefulness; we do not label them as four hours of sleep.'
    reserve='Four remaining participants are untouched by waveform analysis. The other ten sessions of each exposed participant also remain reserved, but they would be new-session tests, not new-person tests. All six participants and the 12 analyzed recordings are now exposed for future claims.'
    controls='Experiment008 adds an exact session-pairing permutation comparison; it does not rerun the Fourier-phase battery from Experiment006 on these new files. Session recurrence alone cannot distinguish neural structure from persistent measurement effects.'
    source='Source: [EESM23 / OpenNeuro ds005178 v1.0.0](https://openneuro.org/datasets/ds005178/versions/1.0.0), commit `a57deb78cf1294497db88d73aaed06813850f236`, CC0. It exports RB, RT, LB and LT at 250 Hz, with an average reference. Any other native channel (including ELE) is excluded. The study is described by [Mikkelsen and colleagues, 2025](https://doi.org/10.1038/s41597-025-04579-8). This in-ear montage is not a Neurable headset or a cEEGrid-equivalent acquisition.'
    artifacts='[Frozen protocol](../protocol/experiment-008.json) · [Source manifest](../protocol/corpus-manifest-008.json) · [Qualification](../results/008/qualification.json) · [Per-record and pairing results](../results/008/summary.json) · [Expanded database index](../results/corpus-v2/summary.json) · [Release](https://github.com/h3ro-dev/eegt/releases/tag/v0.4.0)'
    note='# Research Notes · Experiment 008\n\nDate: 2026-09-25. State: computed; publication and review evidence accompany the release.\n\n'+intro+'\n\n'+finding+'\n\n'+source+'\n\n## Repeat-night comparison\n\n'+table(headers,rows)+'\n'+interpretation+'\n\n'+inference+'\n\n'+controls+'\n\n## Every analyzed recording\n\n'+table(ph,per)+'\nChanges/minute use eligible scored-window centers, not all wall-clock minutes. QC fraction is accepted windows divided by all candidate windows; neither percentage is diagnostic accuracy.\n\n'+boundaries+'\n\n'+reserve+'\n\nDigital conversion was checked against native values at three deterministic positions in each file. This is a decoding check, not physical amplifier calibration. Native gaps are preserved; undocumented gaps remain unknown. Every candidate passed source qualification; pair eligibility is reported separately in the JSON.\n\n'+artifacts+'\n'
    (root/'notes/experiment-008.md').write_text(note)
    site=root/'site';(site/'data').mkdir(exist_ok=True)
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    fig.patch.set_facecolor('#f8f6f0')
    for ax,(v,name) in zip(axes,names.items(),strict=True):
        r=s['paired_statistics'][v]
        if 'distance_matrix' not in r:ax.text(.5,.5,'Insufficient pairs',ha='center');continue
        d=np.asarray(r['distance_matrix']);im=ax.imshow(d,cmap='YlGnBu_r',vmin=0)
        ax.set(title=name,xlabel='Night 2 · anonymous index',ylabel='Night 1 · anonymous index',xticks=range(len(d)),yticks=range(len(d)),xticklabels=range(1,len(d)+1),yticklabels=range(1,len(d)+1))
        fig.colorbar(im,ax=ax,shrink=.75,label='Distance within this view')
    fig.savefig(site/'data/session-distances.png',dpi=170);plt.close(fig)
    sections=[('<h2>Do measurements recur across nights?</h2>','<p>'+finding+'</p>'+table(headers,rows,True)+'<p>'+interpretation+'</p><img src="data/session-distances.png" alt="Three cross-night distance matrices. Row and column with the same index refer to the same participant. The linked result JSON contains every cell value. Each view has its own color scale."><p>'+inference+'</p><p>'+controls+'</p>'),
        ('<h2>Every recording stays visible</h2>',table(ph,per,True)+'<p>Changes per minute use eligible scored-window centers. QC fraction means accepted windows divided by all candidate windows. These numbers are not diagnostic accuracy.</p>'),
        ('<h2>Raw discovery, separate evaluation</h2>','<p>'+boundaries+'</p><p>'+reserve+'</p><p>In-ear sensors differ from both cEEGrid and Neurable. Physical headset transfer and universal token meaning remain unproven.</p>'),
        ('<h2>Independent pretrained models</h2>','<p>The separate <a href="https://github.com/h3ro-dev/eegt/blob/main/notes/model-compatibility-2026-09-25.md">checkpoint compatibility audit</a> checks whether published models can accept these inputs. This experiment uses the unchanged numerical baseline; it does not represent pretrained-model inference.</p>'),
        ('<h2>Reproduce and inspect</h2>','<p><a href="https://github.com/h3ro-dev/eegt/blob/main/notes/experiment-008.md">Full Research Note</a> · <a href="data/repeated-sessions.json">All numerical results (JSON)</a> · <a href="https://github.com/h3ro-dev/eegt/releases/tag/v0.4.0">Versioned data and checksums</a> · <a href="https://openneuro.org/datasets/ds005178/versions/1.0.0">Original open dataset</a></p>')]
    body='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EEGT · Experiment 008 · Across nights</title><meta name="description" content="A frozen comparison of twelve ear-EEG recordings from six participants across two nights."><link rel="stylesheet" href="styles.css"><style>main.repeat{max-width:1160px;margin:auto;padding:60px 24px}.repeat section{padding:34px 0;border-top:1px solid #d9dedb}.repeat h1{font-size:clamp(2.5rem,6vw,4.6rem);line-height:1.06;margin:24px 0}.repeat h2{font-size:1.7rem;margin-bottom:18px}.repeat p{max-width:85ch;margin:18px 0;line-height:1.7}.repeat table{width:100%;border-collapse:collapse;font-size:.85rem}.repeat th,.repeat td{text-align:left;padding:13px 9px;border-bottom:1px solid #d9dedb;vertical-align:top}.table-scroll{overflow:auto}.repeat img{width:100%;height:auto}.stats{display:flex;gap:34px;flex-wrap:wrap;margin:32px 0}.stats strong{display:block;font-size:2.1rem}</style></head><body><a class="skip-link" href="#main">Skip to content</a><main class="repeat" id="main"><a href="./">← EEGT research notebook</a><p class="eyebrow">Research Notes · Experiment 008</p><h1>Different night.<br>The same patterns?</h1><p>A frozen numerical study of repeated ear-EEG recordings</p><p>We added repeated recordings so that stability can be measured across nights, using the same frozen numerical rules.</p>'
    body+=f'<div class="stats"><div><strong>{t["complete_pairs"]}</strong>complete participant pairs</div><div><strong>{t["full_qualified_hours"]:.1f} h</strong>new qualified recordings</div><div><strong>{t["selected_analysis_hours"]:.0f} h</strong>selected for analysis</div></div><p>{t["valid_windows"]:,} of {t["windows"]:,} multichannel windows pass the engineering quality gate. These overlapping windows are measurements, not independent participants.</p>'
    body+=''.join('<section>'+h+c+'</section>' for h,c in sections)+'</main></body></html>'
    (site/'repeated-sessions.html').write_text(body)
    atomic_json(site/'data/repeated-sessions.json',s)
    atomic_json(root/'results/008/report.json',dict(schema='eegt-repeat-report/v1',inputs={p:digest(root/p) for p in ['results/008/summary.json','scripts/report_repeated.py']},outputs={p:digest(root/p) for p in ['notes/experiment-008.md','site/repeated-sessions.html','site/data/repeated-sessions.json','site/data/session-distances.png','results/corpus-v2/corpus.sqlite','results/corpus-v2/summary.json']}))
    print(json.dumps(index['totals']))


if __name__=='__main__':run()
