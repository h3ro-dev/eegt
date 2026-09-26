"""Render the accepted-receipt catalog's counts without new scientific aggregation."""
import argparse,json,html,sqlite3
from contextlib import closing
from pathlib import Path
from build_database import sha,validate_summary,canonical


def render(repo,summary_path,database_path):
    repo=Path(repo);s=json.loads(Path(summary_path).read_text());dbpath=Path(database_path)
    if s['state']!='CONSOLIDATED_RELEASE_CANDIDATE' or sha(dbpath)!=s['database_sha256']:raise ValueError('Catalog summary/database binding differs')
    s=validate_summary(dbpath,s)
    with closing(sqlite3.connect(dbpath.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        experiments=[dict(r) for r in db.execute('SELECT experiment_id,status,release_url FROM experiments ORDER BY experiment_id')]
        result_rows=[json.loads(r[0]) for r in db.execute("SELECT receipt_json FROM results WHERE experiment_id='013' ORDER BY endpoint_id")]
        proof=db.execute("SELECT receipt_json FROM artifacts WHERE artifact_id='outputs/eegt/results/013/summary.json'").fetchone()
    expected={(c,m,k) for c in ('new_people','new_sessions') for m in ('codebrain','cbramod') for k in ('geometry','change')}
    actual=[(r['cohort'],r['model'],r['metric']) for r in result_rows]
    if len(actual)!=8 or set(actual)!=expected:raise ValueError('Complete fixed validation endpoint family required')
    if proof is None:raise ValueError('Validation summary evidence required')
    validation=json.loads(proof[0])
    if sorted(map(canonical,result_rows))!=sorted(map(canonical,validation['primary_endpoints'])):raise ValueError('Validation endpoint receipts differ')
    gates=validation['cohort_inference_gates']
    support=f"Experiment 013 censused {validation['candidate_blocks']:,} candidates and selected {validation['selected_blocks']:,} blocks. Complete people: {gates['new_sessions']['complete_participant_count']} in new sessions ({gates['new_sessions']['status']}); {gates['new_people']['complete_participant_count']} in new people ({gates['new_people']['status']}, fixed minimum {gates['new_people']['minimum_complete_participants']}). All {len(result_rows)} endpoints remain visible."
    compared=[r for r in result_rows if r['test']['status']=='COMPARED']
    significant=sum(r['test']['p_bonferroni_eight']<r['test']['alpha'] for r in compared)
    interpretation=f"{significant} of {len(compared)} estimable comparisons clear their adjusted threshold. Signed effects and model differences remain visible; no between-model significance is inferred. Continuous encoders are not discrete language models."
    def table(headers,rows):
        def cells(values,tag):return ''.join('<'+tag+'>'+html.escape(str(x))+'</'+tag+'>' for x in values)
        return '<div class="table-scroll"><table><thead><tr>'+cells(headers,'th')+'</tr></thead><tbody>'+''.join('<tr>'+cells(row,'td')+'</tr>' for row in rows)+'</tbody></table></div>'
    t=s['totals'];coverage=table(['Dataset','Status','Recordings','Source-local people','Sessions','Known hours','Unknown durations'],[[('UNKNOWN' if r[k] is None else (r[k] if k!='known_recording_hours' else f"{r[k]:.6f}")) for k in ['dataset_id','status','recordings','source_local_people','source_sessions','known_recording_hours','unknown_duration_recordings']] for r in s['coverage']])
    endpoints=table(['Cohort','Model','Metric','Status','People','Mean effect','Adjusted p'],[[r['cohort'],r['model'],r['metric'],r['test']['status'],r['test']['n'],r['test']['observed_mean'] if r['test']['observed_mean'] is not None else 'not estimable',r['test']['p_bonferroni_eight'] if r['test']['p_bonferroni_eight'] is not None else 'not estimable'] for r in result_rows])
    links=''.join('<li><a href="'+html.escape(r['release_url'],quote=True)+'">Experiment '+r['experiment_id']+'</a></li>' for r in experiments)
    known_hours='UNKNOWN' if t['known_qualified_hours'] is None else f"{t['known_qualified_hours']:.6f}"
    body=f'''<a href="./">← EEGT research notebook</a><p>Consolidated research catalog · release candidate</p><h1>What the evidence supports</h1><p><strong>Independent catalog review and public readback remain pending.</strong></p><p>EEGT describes recurring numerical patterns in public around-ear voltage recordings. Different representations can agree on some measurements while disagreeing on others. The work has not established a universal token vocabulary, semantic meaning, a brain-state diagnosis or thought decoding.</p><h2>The source catalog</h2><p>{t['candidate_recordings']} candidate recordings; {t['qualified_recordings']} qualified recordings; {known_hours} qualified source hours. {t['qualified_unknown_duration_recordings']} qualified recordings have unknown duration. Reusing a recording in another experiment adds no people, nights or source hours.</p>{coverage}<p>People counts are local to each dataset and status group; they are not globally unique identities and must not be summed as such. Source hours, quality windows, selected support, event rows and independent people are separate denominators. Missing and quarantined records remain visible.</p><h2>The final fixed validation</h2><p>{support}</p>{endpoints}<p>{interpretation}</p><h2>What earlier results mean</h2><p>The original 11.4% was 393 accepted assignments among 3,458 external scalp windows, a coverage measure. It was not diagnostic accuracy or a fraction of a person's brain activity. Later source, preparation and representation changes prevent a controlled improvement claim. Experiments 011 and 012 also retained inconclusive adjusted results. Dense landmarks can match after phase randomization, and cycles occur in noise; matching alone does not prove shared biological state.</p><h2>Inspect and rebuild</h2><p><a href="https://github.com/h3ro-dev/eegt/releases/tag/v0.10.0">Versioned catalog and checksum downloads</a> · <a href="https://github.com/h3ro-dev/eegt/blob/main/REPRODUCE-CATALOG.md">Offline rebuild instructions</a> · <a href="https://github.com/h3ro-dev/eegt/blob/main/CATALOG-QUERIES.md">Example SQL queries</a> · <a href="https://github.com/h3ro-dev/eegt/blob/main/RESEARCH-SYNTHESIS.md">Source-linked research synthesis</a></p><p>The small package includes the database builder and every hash-bound curator input. The larger model/event archives stay in their original releases. Rebuilding the catalog runs no model or detector and downloads no waves.</p><ul>{links}</ul><h2>Remaining boundaries</h2><p>Physiological calibration, exact reference/gain/clock compatibility, model-pretraining overlap and physical Neurable equivalence remain UNKNOWN. Private NoticingMind waves, personal history and semantic/task labels did not enter discovery. More independent people and acquisition setups, with a method frozen before access, are needed for stronger replication. Meaning requires a separate designed study. DOI metadata is prepared; no issued DOI is claimed.</p>'''
    page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EEGT · Evidence and catalog</title><link rel="stylesheet" href="styles.css"><style>main{max-width:1100px;margin:auto;padding:48px 24px}p{max-width:90ch;line-height:1.7}h1{font-size:clamp(2rem,6vw,4rem)}h2{margin-top:2rem}.table-scroll{overflow:auto}table{border-collapse:collapse;width:100%}th,td{padding:10px;text-align:left;border-bottom:1px solid #ccc}</style></head><body><a class="skip-link" href="#main">Skip to content</a><main id="main">'+body+'</main></body></html>'
    for base in [repo,repo/'site']:
        (base/'data').mkdir(parents=True,exist_ok=True);(base/'catalog.html').write_text(page);(base/'data/catalog.json').write_text(json.dumps(s,indent=2,sort_keys=True)+'\n')
    return {'status':'CANDIDATE_RENDERED','database_sha256':s['database_sha256'],'totals':t}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=Path);p.add_argument('--summary',required=True,type=Path);p.add_argument('--database',required=True,type=Path);a=p.parse_args();print(json.dumps(render(a.repo,a.summary,a.database)))
