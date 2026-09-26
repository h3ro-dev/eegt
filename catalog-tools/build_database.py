"""Build a deterministic curator index from a hash-bound normalized manifest.

No waveform decoding, model execution or scientific aggregation occurs here.
The importer retains complete source receipts and rejects conflicting identities.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def confined(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('input path must be relative and confined')
    result = (root / path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError('input path escapes root')
    return result


SCHEMA = '''
CREATE TABLE catalog_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE inputs(path TEXT PRIMARY KEY,sha256 TEXT NOT NULL);
CREATE TABLE recordings(
 recording_id TEXT PRIMARY KEY,dataset_id TEXT NOT NULL,version TEXT NOT NULL,
 revision TEXT NOT NULL,source_subject TEXT NOT NULL,session_id TEXT NOT NULL,
 status TEXT NOT NULL,reason TEXT,sample_rate_hz REAL,channels INTEGER,
 duration_seconds REAL,receipt_path TEXT NOT NULL REFERENCES inputs(path),
 receipt_json TEXT NOT NULL,
 UNIQUE(dataset_id,revision,source_subject,session_id),
 CHECK(duration_seconds IS NULL OR duration_seconds>=0));
CREATE TABLE source_files(
 file_id TEXT PRIMARY KEY,dataset_id TEXT NOT NULL,revision TEXT NOT NULL,
 path TEXT NOT NULL,bytes INTEGER,sha256 TEXT,url TEXT,status TEXT NOT NULL,
 receipt_path TEXT NOT NULL REFERENCES inputs(path),receipt_json TEXT NOT NULL,
 UNIQUE(dataset_id,revision,path),CHECK(bytes IS NULL OR bytes>=0));
CREATE TABLE recording_files(
 recording_id TEXT REFERENCES recordings(recording_id),
 file_id TEXT REFERENCES source_files(file_id),PRIMARY KEY(recording_id,file_id));
CREATE TABLE experiments(
 experiment_id TEXT PRIMARY KEY,status TEXT NOT NULL,release_url TEXT,
 protocol_path TEXT REFERENCES inputs(path),receipt_path TEXT NOT NULL REFERENCES inputs(path),
 receipt_json TEXT NOT NULL);
CREATE TABLE experiment_recordings(
 experiment_id TEXT REFERENCES experiments(experiment_id),
 recording_id TEXT REFERENCES recordings(recording_id),role TEXT NOT NULL,
 receipt_path TEXT NOT NULL REFERENCES inputs(path),receipt_json TEXT NOT NULL,
 PRIMARY KEY(experiment_id,recording_id));
CREATE TABLE models(
 model_id TEXT PRIMARY KEY,kind TEXT NOT NULL,checkpoint_sha256 TEXT,
 receipt_path TEXT NOT NULL REFERENCES inputs(path),receipt_json TEXT NOT NULL);
CREATE TABLE experiment_models(
 experiment_id TEXT REFERENCES experiments(experiment_id),
 model_id TEXT REFERENCES models(model_id),role TEXT NOT NULL,
 PRIMARY KEY(experiment_id,model_id));
CREATE TABLE results(
 experiment_id TEXT REFERENCES experiments(experiment_id),endpoint_id TEXT NOT NULL,
 model_id TEXT REFERENCES models(model_id),metric TEXT,cohort TEXT,
 receipt_path TEXT NOT NULL REFERENCES inputs(path),receipt_json TEXT NOT NULL,
 PRIMARY KEY(experiment_id,endpoint_id));
CREATE TABLE artifacts(
 artifact_id TEXT PRIMARY KEY,sha256 TEXT,bytes INTEGER,kind TEXT NOT NULL,
 release_url TEXT,member_path TEXT,receipt_path TEXT NOT NULL REFERENCES inputs(path),
 receipt_json TEXT NOT NULL);
CREATE TABLE lineage(
 parent_id TEXT REFERENCES artifacts(artifact_id),
 child_id TEXT REFERENCES artifacts(artifact_id),relation TEXT NOT NULL,
 receipt_path TEXT NOT NULL REFERENCES inputs(path),
 PRIMARY KEY(parent_id,child_id,relation),CHECK(parent_id<>child_id));
CREATE VIEW coverage AS SELECT dataset_id,status,COUNT(*) AS recordings,
 COUNT(DISTINCT source_subject) AS source_local_people,
 COUNT(DISTINCT source_subject||':'||session_id) AS source_sessions,
 SUM(duration_seconds)/3600.0 AS known_recording_hours,
 SUM(duration_seconds IS NULL) AS unknown_duration_recordings
 FROM recordings GROUP BY dataset_id,status;
'''


def rows(db, query):
    return [dict(r) for r in db.execute(query)]


def logical_digest(db):
    """Hash every user schema definition and table row, independent of file layout."""
    schema=[dict(r) for r in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL ORDER BY type,name")]
    tables={}
    for item in schema:
        if item['type']=='table':
            name=item['name']
            # Names originate in this fixed builder's schema, never input SQL.
            if not name.replace('_','').isalnum():raise ValueError('Unexpected table name')
            tables[name]=sorted([dict(r) for r in db.execute('SELECT * FROM "'+name+'"')],key=canonical)
    return hashlib.sha256(canonical({'schema':schema,'tables':tables}).encode()).hexdigest()


def insert_rows(db, table, values, fields):
    columns = fields + ['receipt_json']
    for item in sorted(values, key=canonical):
        # Duplicate primary identities are errors even if their JSON is identical:
        # adapters must deduplicate explicitly, retaining the source proof.
        data = [item.get(key) for key in fields] + [canonical(item['receipt'])]
        db.execute('INSERT INTO ' + table + '(' + ','.join(columns) + ') VALUES (' +
                   ','.join('?' for _ in data) + ')', data)


def database_summary(db):
    metadata=dict(db.execute('SELECT key,value FROM catalog_metadata'))
    return {
        'schema':'eegt-consolidated-index-summary/v1',
        'state':metadata['state'],
        'coverage':rows(db,'SELECT * FROM coverage ORDER BY dataset_id,status'),
        'totals':dict(db.execute('''SELECT COUNT(*) AS candidate_recordings,
          SUM(status='QUALIFIED') AS qualified_recordings,
          SUM(CASE WHEN status='QUALIFIED' THEN duration_seconds END)/3600.0 AS known_qualified_hours,
          SUM(status='QUALIFIED' AND duration_seconds IS NULL) AS qualified_unknown_duration_recordings
          FROM recordings''').fetchone()),
        'source_files':dict(db.execute('''SELECT COUNT(*) AS files,SUM(bytes) AS known_bytes,
          SUM(bytes IS NULL) AS unknown_byte_files FROM source_files''').fetchone()),
        'limitation':'Source-local people are not globally unique people. Experiment joins add no source hours.',
        'logical_content_sha256':logical_digest(db),
        'logical_hash_contract':'user schema SQL plus all table rows; canonical sorted JSON',
        'input_manifest_sha256':metadata['input_manifest_sha256'],
        'inputs':dict(db.execute('SELECT path,sha256 FROM inputs ORDER BY path')),
    }


def validate_summary(database_path, summary):
    from contextlib import closing
    path=Path(database_path)
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        actual=dict(database_summary(db),database_sha256=sha(path))
    if canonical(actual)!=canonical(summary):
        raise ValueError('Catalog summary differs from database-derived evidence')
    return actual


def build(manifest_path, root, destination):
    root, destination = Path(root), Path(destination)
    manifest_bytes = Path(manifest_path).read_bytes()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes)
    if manifest.get('schema') != 'eegt-consolidated-index-input/v1':
        raise ValueError('unknown manifest schema')
    if destination.exists():
        raise FileExistsError(destination)
    inputs = manifest['inputs']
    if not inputs:
        raise ValueError('no input evidence')
    for path, digest in inputs.items():
        if sha(confined(root, path)) != digest:
            raise ValueError('changed input: ' + path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.partial')
    if temporary.exists():
        raise FileExistsError(temporary)
    db = sqlite3.connect(temporary)
    try:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.executescript(SCHEMA)
        db.executemany('INSERT INTO catalog_metadata VALUES (?,?)',
                       [('input_manifest_sha256',manifest_hash),('state',manifest.get('state','PREPARATION_ONLY'))])
        db.executemany('INSERT INTO inputs VALUES (?,?)', sorted(inputs.items()))
        insert_rows(db, 'recordings', manifest.get('recordings', []), [
            'recording_id','dataset_id','version','revision','source_subject','session_id',
            'status','reason','sample_rate_hz','channels','duration_seconds','receipt_path'])
        insert_rows(db, 'source_files', manifest.get('source_files', []), [
            'file_id','dataset_id','revision','path','bytes','sha256','url','status','receipt_path'])
        for item in sorted(manifest.get('recording_files', []), key=canonical):
            db.execute('INSERT INTO recording_files VALUES (?,?)',
                       (item['recording_id'], item['file_id']))
        insert_rows(db, 'experiments', manifest.get('experiments', []), [
            'experiment_id','status','release_url','protocol_path','receipt_path'])
        insert_rows(db, 'experiment_recordings', manifest.get('experiment_recordings', []), [
            'experiment_id','recording_id','role','receipt_path'])
        insert_rows(db, 'models', manifest.get('models', []), [
            'model_id','kind','checkpoint_sha256','receipt_path'])
        for item in sorted(manifest.get('experiment_models', []), key=canonical):
            db.execute('INSERT INTO experiment_models VALUES (?,?,?)',
                       tuple(item[k] for k in ['experiment_id','model_id','role']))
        insert_rows(db, 'results', manifest.get('results', []), [
            'experiment_id','endpoint_id','model_id','metric','cohort','receipt_path'])
        insert_rows(db, 'artifacts', manifest.get('artifacts', []), [
            'artifact_id','sha256','bytes','kind','release_url','member_path','receipt_path'])
        for item in sorted(manifest.get('lineage', []), key=canonical):
            db.execute('INSERT INTO lineage VALUES (?,?,?,?)', tuple(item[k] for k in
                       ['parent_id','child_id','relation','receipt_path']))
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('broken lineage reference')
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('database integrity failed')
        summary = database_summary(db)
        for path, digest in inputs.items():
            if sha(confined(root, path)) != digest:
                raise ValueError('input changed during build: ' + path)
        if sha(manifest_path)!=manifest_hash:
            raise ValueError('manifest changed during build')
        db.commit()
    except BaseException:
        db.close()
        temporary.unlink(missing_ok=True)
        raise
    db.close()
    if sha(manifest_path)!=manifest_hash:
        temporary.unlink()
        raise ValueError('manifest changed before return')
    temporary.rename(destination)
    summary['database_sha256'] = sha(destination)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.manifest,args.root,args.destination), indent=2, sort_keys=True))
