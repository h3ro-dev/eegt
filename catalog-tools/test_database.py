import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from build_database import build, logical_digest
from prepare_index import prepare, add_validation
from build_database import sha

ROOT = Path(__file__).resolve().parents[2]


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = prepare(ROOT,False)
        cls.combined = prepare(ROOT,True)

    def run_manifest(self,manifest,tmp,name='index'):
        source=Path(tmp)/(name+'.json')
        source.write_text(json.dumps(manifest,sort_keys=True))
        return build(source,ROOT,Path(tmp)/(name+'.sqlite'))

    def test_baseline_and_addition(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=self.run_manifest(self.base,tmp,'old')
            combined=self.run_manifest(self.combined,tmp,'combined')
            self.assertEqual(base['totals']['candidate_recordings'],67)
            self.assertEqual(base['totals']['qualified_recordings'],66)
            self.assertAlmostEqual(base['totals']['known_qualified_hours'],309.85418666666667,8)
            self.assertEqual(combined['totals']['candidate_recordings'],69)
            self.assertEqual(combined['totals']['qualified_recordings'],68)
            self.assertAlmostEqual(combined['totals']['known_qualified_hours'],324.20466444444445,8)
            self.assertEqual(combined['source_files']['files']-base['source_files']['files'],16)
            self.assertEqual(combined['source_files']['known_bytes']-base['source_files']['known_bytes'],2066532007)
            self.assertEqual(len(combined['coverage']),5)

    def test_byte_deterministic_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            one=self.run_manifest(self.combined,tmp,'one')
            two=self.run_manifest(self.combined,tmp,'two')
            self.assertEqual(one,two)
            with self.assertRaises(FileExistsError):
                self.run_manifest(self.combined,tmp,'one')

    def test_logical_hash_ignores_page_layout_but_detects_changed_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=self.run_manifest(self.combined,tmp)
            db=sqlite3.connect(Path(tmp)/'index.sqlite')
            try:
                db.row_factory=sqlite3.Row
                self.assertEqual(logical_digest(db),result['logical_content_sha256'])
                db.execute('PRAGMA page_size=8192');db.execute('VACUUM')
                self.assertEqual(logical_digest(db),result['logical_content_sha256'])
                self.assertNotEqual(sha(Path(tmp)/'index.sqlite'),result['database_sha256'])
                db.execute("UPDATE recordings SET reason='SYNTHETIC_CHANGED_PROVENANCE' WHERE recording_id=(SELECT MIN(recording_id) FROM recordings)")
                self.assertNotEqual(logical_digest(db),result['logical_content_sha256'])
            finally:db.close()

    def test_duplicate_record_or_source_identity_refused(self):
        for key in ['recordings','source_files']:
            manifest=copy.deepcopy(self.combined)
            manifest[key].append(copy.deepcopy(manifest[key][0]))
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(sqlite3.IntegrityError):
                    self.run_manifest(manifest,tmp)
                self.assertFalse((Path(tmp)/'index.sqlite').exists())

    def test_changed_evidence_refused(self):
        manifest=copy.deepcopy(self.combined)
        manifest['inputs'][next(iter(manifest['inputs']))]='0'*64
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'changed input'):
                self.run_manifest(manifest,tmp)

    def test_missing_join_refused(self):
        manifest=copy.deepcopy(self.combined)
        manifest['recording_files'][0]['recording_id']='invented'
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(sqlite3.IntegrityError):
                self.run_manifest(manifest,tmp)

    def test_unknown_duration_not_zero(self):
        manifest=copy.deepcopy(self.combined)
        record=next(r for r in manifest['recordings'] if r['status']=='QUALIFIED')
        record['duration_seconds']=None
        with tempfile.TemporaryDirectory() as tmp:
            result=self.run_manifest(manifest,tmp)
            self.assertEqual(result['totals']['qualified_unknown_duration_recordings'],1)
            self.assertEqual(result['totals']['qualified_recordings'],68)

    def test_reanalysis_does_not_add_source_hours(self):
        manifest=copy.deepcopy(self.combined)
        path=next(iter(manifest['inputs']))
        for identifier in ['010','011','012']:
            manifest['experiments'].append(dict(experiment_id=identifier,status='SYNTHETIC_JOIN_TEST',
                release_url=None,protocol_path=None,receipt_path=path,receipt={}))
            for record in manifest['recordings']:
                manifest['experiment_recordings'].append(dict(experiment_id=identifier,
                    recording_id=record['recording_id'],role='fixture',receipt_path=path,receipt={}))
        with tempfile.TemporaryDirectory() as tmp:
            before=self.run_manifest(self.combined,tmp,'before')
            after=self.run_manifest(manifest,tmp,'after')
            self.assertEqual(before['totals'],after['totals'])
            self.assertEqual(before['coverage'],after['coverage'])

    def test_actual_history_preserves_statistics_and_totals(self):
        manifest=prepare(ROOT,True,True)
        with tempfile.TemporaryDirectory() as tmp:
            result=self.run_manifest(manifest,tmp)
            self.assertEqual(result['totals']['candidate_recordings'],69)
            db=sqlite3.connect(Path(tmp)/'index.sqlite')
            try:
                for experiment,key in [('009','primary_statistics'),('010','primary_statistics'),('011','primary'),('012','primary_endpoints')]:
                    expected=json.loads((ROOT/f'outputs/eegt/results/{experiment}/summary.json').read_text())[key]
                    actual=[json.loads(r[0]) for r in db.execute(
                        'SELECT receipt_json FROM results WHERE experiment_id=?',(experiment,))]
                    self.assertCountEqual(expected,actual)
                expected=json.loads((ROOT/'outputs/eegt/results/008/summary.json').read_text())['paired_statistics']
                actual={r[0]:json.loads(r[1]) for r in db.execute(
                    "SELECT endpoint_id,receipt_json FROM results WHERE experiment_id='008'")}
                self.assertEqual(expected,actual)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM experiments').fetchone()[0],8)
                self.assertGreater(db.execute('SELECT COUNT(*) FROM lineage').fetchone()[0],0)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM recordings').fetchone()[0],69)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM experiment_recordings').fetchone()[0],36)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM models').fetchone()[0],2)
            finally:
                db.close()

    def test_manifest_mutation_during_build_rejected(self):
        from unittest.mock import patch
        import build_database
        original=build_database.insert_rows
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'input.json';source.write_text(json.dumps(self.base))
            def mutate(*args,**kwargs):
                source.write_text(json.dumps(dict(self.base,state='MUTATED')))
                return original(*args,**kwargs)
            with patch.object(build_database,'insert_rows',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'manifest changed'):build(source,ROOT,Path(tmp)/'out.sqlite')
            self.assertFalse((Path(tmp)/'out.sqlite').exists())

    def test_shared_file_coalesces_links_and_preserves_receipts(self):
        from prepare_index import coalesce_files
        row=copy.deepcopy(self.base['source_files'][0]);other=copy.deepcopy(row);other['receipt']={'second':True}
        manifest={'source_files':[row,other],'recording_files':[{'recording_id':'a','file_id':row['file_id']},{'recording_id':'b','file_id':row['file_id']}]}
        coalesce_files(manifest)
        self.assertEqual(len(manifest['source_files']),1);self.assertEqual(len(manifest['recording_files']),2)
        self.assertEqual(len(manifest['source_files'][0]['receipt']['evidence']),2)
        other['sha256']='conflict';manifest['source_files']=[row,other]
        with self.assertRaisesRegex(ValueError,'Conflicting'):coalesce_files(manifest)


class ValidationAdapterTests(unittest.TestCase):
    def seal(self,root):
        files={}
        for relative in ('protocol/corpus-manifest-013.json','protocol/experiment-013.json',
                         'results/013/qualification.json','results/013/summary.json'):
            path=root/'outputs/eegt'/relative
            files['repo/'+relative]=dict(sha256=sha(path),bytes=path.stat().st_size)
        stage=root/'synthetic-stage.json'
        stage.write_text(json.dumps(dict(files=files),sort_keys=True))
        (root/'synthetic-publication.json').write_text(json.dumps(dict(
            status='PUBLISHED_AND_VERIFIED',release='https://example.invalid/synthetic',
            release_data_manifest=dict(path='synthetic-stage.json',sha256=sha(stage))),sort_keys=True))

    def fixture(self, root, status='NO_ELIGIBLE_BLOCKS'):
        source=json.loads((ROOT/'outputs/eegt/protocol/corpus-manifest-013.json').read_text())
        protocol=json.loads((ROOT/'outputs/eegt/protocol/experiment-013.json').read_text())
        manifest=dict(inputs={},recordings=[],source_files=[],recording_files=[],
            experiment_recordings=[],experiments=[],experiment_models=[],results=[],artifacts=[])
        def put(rel,obj):
            p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps(obj,sort_keys=True))
        def bind(rel):
            manifest['inputs'][rel]=sha(root/rel);return rel
        put('outputs/eegt/protocol/corpus-manifest-013.json',source)
        put('outputs/eegt/protocol/experiment-013.json',protocol)
        qualification=dict(records=[dict(recording_id=r['recording_id'],
            source_subject=r['source_subject'],session=r['session'],cohort=r['cohort'],
            status='QUARANTINED',reason='SOURCE_MISSING',bytes=None,sha256=None)
            for r in source['records']])
        put('outputs/eegt/results/013/qualification.json',qualification)
        summary=dict(status=status,protocol_sha256=sha(root/'outputs/eegt/protocol/experiment-013.json'),
            source_manifest_sha256=sha(root/'outputs/eegt/protocol/corpus-manifest-013.json'),
            primary_endpoints=[dict(e,test=dict(status='NOT_ESTIMABLE',p_raw=None,p_adjusted=None))
                              for e in protocol['primary_endpoints']])
        put('outputs/eegt/results/013/summary.json',summary)
        # Synthetic receipt in temporary directory only; never a public acceptance.
        self.seal(root)
        return manifest,bind,summary,qualification,put

    def test_negative_census_preserves_missing_hours_and_all_endpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest,bind,summary,_,_=self.fixture(root)
            add_validation(root,manifest,bind,'synthetic-publication.json')
            self.assertEqual(len(manifest['recordings']),20)
            self.assertTrue(all(r['duration_seconds'] is None for r in manifest['recordings']))
            self.assertEqual([r['receipt'] for r in manifest['results']],summary['primary_endpoints'])
            self.assertEqual(len(manifest['source_files']),20)
            self.assertEqual(len(manifest['experiment_recordings']),20)

    def test_partial_execution_or_wrong_endpoint_family_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest,bind,summary,_,put=self.fixture(root,'PARTIAL')
            with self.assertRaisesRegex(ValueError,'incomplete'):
                add_validation(root,manifest,bind,'synthetic-publication.json')
            summary['status']='COMPLETE_NUMERICAL_RECORD'
            summary['primary_endpoints']=summary['primary_endpoints'][:-1]
            put('outputs/eegt/results/013/summary.json',summary)
            self.seal(root)
            with self.assertRaisesRegex(ValueError,'endpoint census'):
                add_validation(root,manifest,bind,'synthetic-publication.json')

    def test_qualified_metadata_without_verified_bytes_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest,bind,_,qualification,put=self.fixture(root)
            qualification['records'][0].update(status='QUALIFIED',duration_seconds=999999)
            put('outputs/eegt/results/013/qualification.json',qualification)
            self.seal(root)
            with self.assertRaisesRegex(ValueError,'verified bytes/duration'):
                add_validation(root,manifest,bind,'synthetic-publication.json')

    def test_changed_local_summary_cannot_inherit_publication_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest,bind,summary,_,put=self.fixture(root)
            summary['primary_endpoints'][0]['test']['p_adjusted']=0.001
            put('outputs/eegt/results/013/summary.json',summary)
            with self.assertRaisesRegex(ValueError,'differs from published member'):
                add_validation(root,manifest,bind,'synthetic-publication.json')

    def test_member_manifest_identity_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest,bind,_,_,put=self.fixture(root)
            put('synthetic-stage.json',dict(files={}))
            with self.assertRaisesRegex(ValueError,'member manifest changed'):
                add_validation(root,manifest,bind,'synthetic-publication.json')
            put('synthetic-publication.json',dict(status='PUBLISHED_AND_VERIFIED'))
            with self.assertRaisesRegex(ValueError,'member binding missing'):
                add_validation(root,manifest,bind,'synthetic-publication.json')

    def test_publication_paths_cannot_escape_before_binding(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binder=Mock()
            for path in ('/tmp/outside.json','../outside.json'):
                with self.assertRaisesRegex(ValueError,'confined'):add_validation(root,{},binder,path)
            (root/'outside').symlink_to(root.parent)
            with self.assertRaisesRegex(ValueError,'escapes'):add_validation(root,{},binder,'outside/file.json')
            binder.assert_not_called()


if __name__=='__main__':
    unittest.main()
