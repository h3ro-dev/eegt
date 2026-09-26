"""Normalize the accepted pre-013 catalog inputs; no new-source import yet."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
from build_database import canonical, sha, confined


def query(path, table):
    with closing(sqlite3.connect('file:' + str(path.resolve()) + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        return [dict(r) for r in db.execute('SELECT * FROM ' + table)]


def prepare(root, include_eesm19=True, include_history=False, validation_publication=None):
    root = Path(root)
    old_path = 'outputs/eegt/results/corpus-v2/corpus.sqlite'
    first_path = 'outputs/eegt/protocol/corpus-manifest-v1.json'
    ear_path = 'outputs/eegt/protocol/corpus-manifest-008.json'
    sources = json.loads(confined(root,first_path).read_text())['sources']
    versions = {s['dataset']:(s['version'],s['git_commit']) for s in sources}
    s = json.loads(confined(root,ear_path).read_text())['source']
    versions[s['dataset']] = (s['version'],s['commit'])
    manifest = dict(schema='eegt-consolidated-index-input/v1',state='PREPARATION_ONLY_013_PENDING',
                    inputs={},recordings=[],source_files=[],recording_files=[],experiments=[],
                    experiment_recordings=[],artifacts=[],lineage=[])

    def bind(path):
        manifest['inputs'][path] = sha(confined(root,path))
        return path

    for path in [old_path,first_path,ear_path]:
        bind(path)
    recording_map = {}
    for row in query(confined(root,old_path),'recordings'):
        version, revision = versions[row['dataset_id']]
        item = {key:row.get(key) for key in ['recording_id','dataset_id','source_subject',
                'session_id','status','reason','sample_rate_hz','channels','duration_seconds']}
        item.update(version=version,revision=revision,receipt_path=old_path,receipt=row)
        manifest['recordings'].append(item)
        recording_map[row['recording_id']] = item

    def add_file(row, dataset, revision, path, source, status, recording_id=None):
        import hashlib
        identity = canonical([dataset,revision,path])
        file_id = hashlib.sha256(identity.encode()).hexdigest()
        item = dict(file_id=file_id,dataset_id=dataset,revision=revision,path=path,
                    bytes=row.get('bytes'),sha256=row.get('sha256'),url=row.get('url'),
                    status=status,receipt_path=source,receipt=row)
        manifest['source_files'].append(item)
        if recording_id is not None:
            manifest['recording_files'].append(dict(recording_id=recording_id,file_id=file_id))

    for row in query(confined(root,old_path),'source_files'):
        record = recording_map[row['recording_id']]
        prefix = 'data/cache/' + record['dataset_id'] + '/'
        path = row['path'].removeprefix(prefix)
        add_file(row,record['dataset_id'],record['revision'],path,old_path,
                 'HASH_RECORDED' if row['sha256'] else 'HASH_UNAVAILABLE',row['recording_id'])

    if include_eesm19:
        acceptance_path = bind('outputs/research/eesm19-intake/ACCEPTANCE.json')
        acceptance = json.loads(confined(root,acceptance_path).read_text())
        catalog_json = bind('work/eesm19-intake/out/catalog.json')
        catalog_path = bind('work/eesm19-intake/out/catalog.sqlite')
        if acceptance['status'] != 'ACCEPTED' or acceptance['catalog_sha256'] != manifest['inputs'][catalog_path]:
            raise ValueError('EESM19 acceptance changed')
        rows = query(confined(root,catalog_path),'recordings')
        catalog = json.loads(confined(root,catalog_json).read_text())
        if len(rows) != acceptance['source_recordings'] or len(catalog['records']) != len(rows):
            raise ValueError('EESM19 recording census changed')
        # The SQLite source is independently reviewed; retain complete qualification
        # JSON instead of flattening away its masks/calibration/clock distinctions.
        for row in rows:
            dataset,version = row['dataset_version'].split(':',1)
            manifest['recordings'].append(dict(recording_id=row['recording_id'],dataset_id=dataset,
                version=version,revision=row['source_revision'],source_subject=row['source_person'].removeprefix('sub-'),
                session_id=row['source_session'].removeprefix('ses-'),status=row['status'],reason=row['reason'],
                sample_rate_hz=row['sample_rate_hz'],channels=row['eeg_channel_count'],
                duration_seconds=row['source_duration_seconds'],receipt_path=catalog_path,receipt=row))
        revisions = {row['source_revision'] for row in rows}
        if len(revisions) != 1:
            raise ValueError('ambiguous shared metadata revision')
        for row in query(confined(root,catalog_path),'source_files'):
            add_file(row,'ds005185',next(iter(revisions)),row['path'],catalog_path,
                     row['status'],row['recording_id'])
    if include_history:
        add_recent_history(root,manifest,bind)
        add_earlier_history(root,manifest,bind)
    if validation_publication is not None:
        if not include_history:
            raise ValueError('validation requires model/history provenance')
        add_validation(root,manifest,bind,validation_publication)
        manifest['state']='CONSOLIDATED_RELEASE_CANDIDATE'
    coalesce_files(manifest)
    return manifest


def coalesce_files(manifest):
    """One physical source identity, retaining every recording link and receipt."""
    grouped={}
    for row in manifest['source_files']:
        identity=(row['dataset_id'],row['revision'],row['path'])
        if identity not in grouped:
            grouped[identity]=dict(row)
            grouped[identity]['receipt']={'evidence':[{'receipt_path':row['receipt_path'],'receipt':row['receipt']}]}
        else:
            previous=grouped[identity]
            if any(previous.get(k)!=row.get(k) for k in ('file_id','bytes','sha256','url','status')):
                raise ValueError('Conflicting shared source file evidence')
            evidence={'receipt_path':row['receipt_path'],'receipt':row['receipt']}
            if evidence not in previous['receipt']['evidence']:
                previous['receipt']['evidence'].append(evidence)
    manifest['source_files']=[grouped[k] for k in sorted(grouped)]
    manifest['recording_files']=[json.loads(v) for v in sorted({canonical(r) for r in manifest['recording_files']})]


def add_validation(root,manifest,bind,publication_path):
    """Import actual accepted 013 receipts; never qualify metadata predictions."""
    import hashlib
    confined(root,publication_path)
    publication_path=bind(publication_path)
    acceptance=json.loads(confined(root,publication_path).read_text())
    if acceptance.get('status')!='PUBLISHED_AND_VERIFIED':
        raise ValueError('013 publication not accepted')
    binding=acceptance.get('release_data_manifest')
    if not isinstance(binding,dict) or not binding.get('path') or not binding.get('sha256'):
        raise ValueError('013 published member binding missing')
    confined(root,binding['path'])
    stage_path=bind(binding['path'])
    if manifest['inputs'][stage_path]!=binding['sha256']:
        raise ValueError('013 published member manifest changed')
    stage=json.loads(confined(root,stage_path).read_text())
    for relative in ('protocol/corpus-manifest-013.json','protocol/experiment-013.json',
                     'results/013/qualification.json','results/013/summary.json'):
        actual=confined(root,'outputs/eegt/'+relative)
        member=stage.get('files',{}).get('repo/'+relative,{})
        if member.get('sha256')!=sha(actual) or member.get('bytes')!=actual.stat().st_size:
            raise ValueError('013 imported file differs from published member: '+relative)
    release=acceptance['release']
    if isinstance(release,str):
        url=release
    else:
        native=release.get('release',release)
        url=native.get('html_url') or native['url']
    source_path=bind('outputs/eegt/protocol/corpus-manifest-013.json')
    source=json.loads(confined(root,source_path).read_text())
    qualification_path=bind('outputs/eegt/results/013/qualification.json')
    qualification=json.loads(confined(root,qualification_path).read_text())
    expected={r['recording_id']:r for r in source['records']}
    actual=qualification['records']
    if len(actual)!=len(expected) or {r['recording_id'] for r in actual}!=set(expected):
        raise ValueError('013 qualification census differs from frozen source')
    summary_path=bind('outputs/eegt/results/013/summary.json')
    summary=json.loads(confined(root,summary_path).read_text())
    if summary.get('status') not in ('COMPLETE_NUMERICAL_RECORD','NO_ELIGIBLE_BLOCKS'):
        raise ValueError('013 numerical execution is incomplete')
    protocol_path=bind('outputs/eegt/protocol/experiment-013.json')
    if summary['protocol_sha256']!=manifest['inputs'][protocol_path] or summary['source_manifest_sha256']!=manifest['inputs'][source_path]:
        raise ValueError('013 protocol/source identity mismatch')
    protocol=json.loads(confined(root,protocol_path).read_text())
    endpoint_keys={(e['cohort'],e['model'],e['metric']) for e in protocol['primary_endpoints']}
    endpoints=summary['primary_endpoints']
    if (len(endpoints)!=len(endpoint_keys) or
            {(e['cohort'],e['model'],e['metric']) for e in endpoints}!=endpoint_keys):
        raise ValueError('013 endpoint census mismatch')
    origin=source['source']
    for row in actual:
        src=expected[row['recording_id']]
        if any(row[k]!=src[k] for k in ('source_subject','session','cohort')):
            raise ValueError('013 curator identity mismatch')
        qualified=row['status']=='QUALIFIED'
        if qualified and (row.get('sha256')!=src['file']['expected_digest'] or
                          row.get('duration_seconds') is None):
            raise ValueError('013 qualified source lacks verified bytes/duration')
        manifest['recordings'].append(dict(recording_id=row['recording_id'],dataset_id=origin['dataset'],
            version=origin['version'],revision=origin['commit'],source_subject=row['source_subject'],
            session_id=row['session'],status=row['status'],reason=row.get('reason'),
            sample_rate_hz=row.get('sample_rate_hz'),channels=len(row['channels']) if row.get('channels') else None,
            duration_seconds=row.get('duration_seconds'),receipt_path=qualification_path,receipt=row))
        file_id=hashlib.sha256(canonical([origin['dataset'],origin['commit'],src['file']['path']]).encode()).hexdigest()
        manifest['source_files'].append(dict(file_id=file_id,dataset_id=origin['dataset'],revision=origin['commit'],
            path=src['file']['path'],bytes=row.get('bytes'),sha256=row.get('sha256'),url=src['file']['url'],
            status=row['status'],receipt_path=qualification_path,receipt=dict(source=src,qualification=row)))
        manifest['recording_files'].append(dict(recording_id=row['recording_id'],file_id=file_id))
        manifest['experiment_recordings'].append(dict(experiment_id='013',recording_id=row['recording_id'],
            role=src['cohort'],receipt_path=qualification_path,receipt=row))
    manifest['experiments'].append(dict(experiment_id='013',status=acceptance['status'],release_url=url,
        protocol_path=protocol_path,receipt_path=publication_path,receipt=acceptance))
    for model in ('codebrain','cbramod'):
        manifest['experiment_models'].append(dict(experiment_id='013',model_id=model,role='fixed_encoder'))
    for endpoint in endpoints:
        manifest['results'].append(dict(experiment_id='013',endpoint_id=':'.join(endpoint[k] for k in ('cohort','model','metric')),
            model_id=endpoint['model'],metric=endpoint['metric'],cohort=endpoint['cohort'],receipt_path=summary_path,receipt=endpoint))
    manifest['artifacts'].append(dict(artifact_id=summary_path,sha256=manifest['inputs'][summary_path],
        bytes=confined(root,summary_path).stat().st_size,kind='scientific_summary',release_url=url,member_path=None,
        receipt_path=summary_path,receipt=summary))


def add_recent_history(root,manifest,bind):
    """Import exact 010-012 statistics without conflating their test families."""
    manifest.update(models=[],experiment_models=[],results=[])
    for model,number in [('codebrain','010'),('cbramod','011')]:
        path=bind(f'outputs/eegt/results/{number}/inference.json')
        receipt=json.loads(confined(root,path).read_text())
        manifest['models'].append(dict(model_id=model,kind='continuous_pretrained_EEG_encoder',
            checkpoint_sha256=receipt['checkpoint_sha256'],receipt_path=path,receipt=receipt))
    for number,version,key in [('010','0.6.0','primary_statistics'),
                               ('011','0.7.0','primary'),('012','0.8.0','primary_endpoints')]:
        acceptance_path=bind(f'outputs/research/EEGT-v{version}-PUBLICATION.json')
        acceptance=json.loads(confined(root,acceptance_path).read_text())
        if acceptance['status']!='PUBLISHED_AND_VERIFIED':
            raise ValueError('publication not accepted')
        release=acceptance['release']
        url=release if isinstance(release,str) else release['html_url']
        protocol_path=bind(f'outputs/eegt/protocol/experiment-{number}.json')
        manifest['experiments'].append(dict(experiment_id=number,status=acceptance['status'],
            release_url=url,protocol_path=protocol_path,receipt_path=acceptance_path,receipt=acceptance))
        model_ids=['codebrain'] if number=='010' else ['codebrain','cbramod']
        manifest['experiment_models'].extend(dict(experiment_id=number,model_id=m,
            role='fixed_encoder') for m in model_ids)
        path=bind(f'outputs/eegt/results/{number}/summary.json')
        summary=json.loads(confined(root,path).read_text())
        manifest['artifacts'].append(dict(artifact_id=path,sha256=manifest['inputs'][path],
            bytes=confined(root,path).stat().st_size,kind='scientific_summary',release_url=url,
            member_path=None,receipt_path=path,receipt=summary))
        # Every endpoint's original JSON includes its exact aggregation, all
        # exclusions and p-value field name.  No p value is recomputed here.
        for endpoint in summary[key]:
            identifier=':'.join(str(endpoint.get(k,'')) for k in ['model','view','metric'])
            model=endpoint.get('model') or ('codebrain' if number=='010' else None)
            manifest['results'].append(dict(experiment_id=number,endpoint_id=identifier,
                model_id=model,metric=endpoint['metric'],cohort='exposed_development',
                receipt_path=path,receipt=endpoint))
        selection_path=bind('outputs/eegt/results/010/prepared.json')
        selection=json.loads(confined(root,selection_path).read_text())
        ids=sorted({r['recording_id'] for r in selection['records']})
        for recording_id in ids:
            candidate_rows=[r for r in selection['records'] if r['recording_id']==recording_id]
            manifest['experiment_recordings'].append(dict(experiment_id=number,
                recording_id=recording_id,role='reused_exposed_support',receipt_path=selection_path,
                receipt=dict(candidate_rows=candidate_rows,
                    limitation='These are selection denominators, not per-endpoint primary sample sizes.')))


def add_earlier_history(root,manifest,bind):
    """Retain earlier summaries and their actual publication receipt vocabulary.

    Experiments 006/007 reuse 003's methods; no nonexistent standalone protocol
    is invented. Full JSON preserves heterogeneous historical denominators.
    """
    for number,version in [('003','0.3.0'),('006','0.3.0'),('007','0.3.0'),
                           ('008','0.4.0'),('009','0.5.0')]:
        acceptance_path=bind(f'outputs/research/EEGT-v{version}-PUBLICATION.json')
        acceptance=json.loads(confined(root,acceptance_path).read_text())
        if acceptance['status'] not in ('VERIFIED','PUBLISHED_AND_VERIFIED'):
            raise ValueError('historical publication not accepted')
        release=acceptance['release']
        if isinstance(release,str):
            url=release
        else:
            native=release.get('release',release)
            url=native.get('html_url') or native['url']
        protocol_number='003' if number in ('006','007') else number
        protocol_path=bind(f'outputs/eegt/protocol/experiment-{protocol_number}.json')
        manifest['experiments'].append(dict(experiment_id=number,status=acceptance['status'],
            release_url=url,protocol_path=protocol_path,receipt_path=acceptance_path,receipt=acceptance))
        path=bind(f'outputs/eegt/results/{number}/summary.json')
        summary=json.loads(confined(root,path).read_text())
        manifest['artifacts'].append(dict(artifact_id=path,sha256=manifest['inputs'][path],
            bytes=confined(root,path).stat().st_size,kind='scientific_summary',release_url=url,
            member_path=None,receipt_path=path,receipt=summary))
        if number=='008':
            for view,endpoint in summary['paired_statistics'].items():
                manifest['results'].append(dict(experiment_id=number,endpoint_id=view,
                    model_id=None,metric='paired_distance:'+view,cohort='historical_repeated_sessions',
                    receipt_path=path,receipt=endpoint))
        if number=='009':
            inference_path=bind('outputs/eegt/results/009/inference.json')
            inference=json.loads(confined(root,inference_path).read_text())
            checkpoint=next(m['checkpoint_sha256'] for m in manifest['models']
                            if m['model_id']=='codebrain')
            if inference['checkpoint_sha256']!=checkpoint:
                raise ValueError('historical CodeBrain checkpoint differs')
            manifest['experiment_models'].append(dict(experiment_id=number,
                model_id='codebrain',role='fixed_encoder'))
            for endpoint in summary['primary_statistics']:
                manifest['results'].append(dict(experiment_id=number,
                    endpoint_id=endpoint['view']+':'+endpoint['metric'],model_id='codebrain',
                    metric=endpoint['metric'],cohort='exposed_development',receipt_path=path,
                    receipt=endpoint))
    # Link only explicit, hash-matching summary dependencies; a shared filename
    # alone is insufficient evidence of lineage across changing source versions.
    indexed={a['artifact_id']:a for a in manifest['artifacts']}
    for child in list(indexed.values()):
        receipt=child['receipt']
        for relative,digest in receipt.get('inputs',receipt.get('input_hashes',{})).items():
            parent_id='outputs/eegt/'+relative
            if parent_id in indexed and indexed[parent_id]['sha256']==digest:
                manifest['lineage'].append(dict(parent_id=parent_id,child_id=child['artifact_id'],
                    relation='explicit_hash_bound_input',receipt_path=child['receipt_path']))


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--include-recent-history',action='store_true')
    parser.add_argument('--validation-publication',help='Accepted actual 013 publication receipt, relative to root')
    args=parser.parse_args()
    target=Path(args.output)
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(prepare(args.root,include_history=args.include_recent_history,
                                       validation_publication=args.validation_publication),
                                indent=2,sort_keys=True,allow_nan=False)+'\n')
