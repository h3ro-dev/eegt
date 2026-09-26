"""Pure synthetic catalog publication boundaries, no EEG computation."""
import json,sqlite3,tempfile,unittest
from contextlib import closing
from pathlib import Path
from build_database import sha
import report_catalog,package_catalog

class CatalogPublication(unittest.TestCase):
    def fixture(self,root,endpoints=True):
        from build_database import build
        receipt=root/'receipt.json';receipt.write_text('{}')
        path='receipt.json'
        rows=[{'cohort':c,'model':m,'metric':k,'test':{'status':'NOT_ESTIMABLE','n':0,'observed_mean':None,'p_bonferroni_eight':None}} for c in ('new_people','new_sessions') for m in ('codebrain','cbramod') for k in ('geometry','change')] if endpoints else []
        proof={'primary_endpoints':rows,'candidate_blocks':0,'selected_blocks':0,'cohort_inference_gates':{c:{'complete_participant_count':0,'status':'INSUFFICIENT_PARTICIPANTS','minimum_complete_participants':3} for c in ('new_people','new_sessions')}}
        manifest={'schema':'eegt-consolidated-index-input/v1','state':'CONSOLIDATED_RELEASE_CANDIDATE','inputs':{path:sha(receipt)},'recordings':[dict(recording_id='a',dataset_id='synthetic',version='1',revision='r',source_subject='p',session_id='s',status='QUALIFIED',reason=None,sample_rate_hz=None,channels=None,duration_seconds=None,receipt_path=path,receipt={})],'experiments':[dict(experiment_id='013',status='SYNTHETIC',release_url='https://example.invalid',protocol_path=path,receipt_path=path,receipt={})],'results':[dict(experiment_id='013',endpoint_id=str(i),model_id=None,metric=r['metric'],cohort=r['cohort'],receipt_path=path,receipt=r) for i,r in enumerate(rows)],'artifacts':[dict(artifact_id='outputs/eegt/results/013/summary.json',sha256=None,bytes=None,kind='scientific_summary',release_url=None,member_path=None,receipt_path=path,receipt=proof)]}
        source=root/'input.json';source.write_text(json.dumps(manifest));p=root/'catalog.sqlite'
        s=build(source,root,p);summary=root/'summary.json';summary.write_text(json.dumps(s));return p,summary
    def test_fabricated_counts_rejected_by_render_and_stage(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,s=self.fixture(root);data=json.loads(s.read_text());data['totals']['candidate_recordings']=999;s.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'database-derived'):report_catalog.render(root/'out',s,p)
            with self.assertRaisesRegex(ValueError,'database-derived'):package_catalog.stage(root,root/'input.json',p,s,root/'stage')
    def test_unknown_duration_remains_visible(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,s=self.fixture(root);report_catalog.render(root/'site-output',s,p)
            self.assertIn('UNKNOWN qualified source hours',(root/'site-output/catalog.html').read_text())
            self.assertIsNone(json.loads((root/'site-output/data/catalog.json').read_text())['coverage'][0]['known_recording_hours'])
    def test_missing_endpoint_family_cannot_render(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,s=self.fixture(root,False)
            with self.assertRaisesRegex(ValueError,'endpoint family'):report_catalog.render(root/'site-output',s,p)
            self.assertFalse((root/'site-output').exists())
    def test_preparation_cannot_stage_as_final_catalog(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,s=self.fixture(root);manifest=root/'preparation.json';manifest.write_text(json.dumps({'state':'PREPARATION_ONLY_013_PENDING'}))
            with self.assertRaisesRegex(ValueError,'Accepted validation publication'):package_catalog.stage(root,manifest,p,s,root/'stage')
            self.assertFalse((root/'stage').exists())
if __name__=='__main__':unittest.main()
