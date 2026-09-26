"""Release cannot accept partial replay or a substituted final review inventory."""
import importlib.util,json
from pathlib import Path
import tempfile,unittest
SPEC=importlib.util.spec_from_file_location('release_gate',Path(__file__).resolve().parents[1]/'scripts/verify_validation_release.py');g=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(g)
class ReleaseBoundary(unittest.TestCase):
    def test_partial_status_and_wrong_count_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'results/013';p.mkdir(parents=True)
            for n in ['RUN-SOURCE-MANIFEST.json','INPUT-ACCEPTANCE.json']:(p/n).write_text('{}')
            good=dict(status='REPLAYED_RECORDED_EVENTS',full_scientific_summary=True,completed_blocks=174,partitions=4002,detector_regenerated=False,run_manifest_sha256=g.digest(p/'RUN-SOURCE-MANIFEST.json'),input_acceptance_sha256=g.digest(p/'INPUT-ACCEPTANCE.json'))
            g.require_complete_replay(good,root)
            for update in [dict(full_scientific_summary=False),dict(completed_blocks=173),dict(partitions=3979),dict(run_manifest_sha256='0'*64),dict(detector_regenerated=True)]:
                with self.subTest(update=update),self.assertRaises(ValueError):g.require_complete_replay({**good,**update},root)
    def test_exact_review_and_asset_required(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); asset=root/'asset.tar.gz';asset.write_bytes(b'payload')
            files={n:{'source_path':n.removeprefix('repo/'),'bytes':1,'sha256':'a'*64} for n in ['repo/results/013/INPUT-ACCEPTANCE.json','repo/results/013/summary.json','repo/results/013/analysis.sqlite']}
            stage={'morphology_rows':100,'files':files,'assets':{asset.name:{'bytes':7,'sha256':g.digest(asset)}},'run_manifest_sha256':'f'*64}
            replay=dict(status='REPLAYED_RECORDED_EVENTS',full_scientific_summary=True,completed_blocks=174,partitions=4002,run_manifest_sha256='f'*64,detector_regenerated=False,input_acceptance_sha256='a'*64)
            morph=dict(rows=100,detector_regenerated=False,status='MORPHOLOGY_REPRODUCED_FROM_RECORDED_EVENTS',blocks=174,run_manifest_sha256='f'*64,summary_sha256='a'*64,index_sha256='a'*64)
            paths=[root/n for n in ['stage.json','review.json','replay.json','morph.json','extract.json']]
            for p,d in [(paths[0],stage),(paths[2],replay),(paths[3],morph)]:p.write_text(json.dumps(d))
            extraction={'status':'EXTRACTED_AND_VERIFIED','release_manifest_sha256':g.digest(paths[0]),'files':{n:{'bytes':1,'sha256':'a'*64} for n in files}};paths[4].write_text(json.dumps(extraction))
            review={'status':'ACCEPTED','reviewer_actor':'independent','reviewer_thread':'thread','files':files,'evidence':{str(p.resolve()):g.digest(p) for p in [paths[0],paths[2],paths[3],paths[4]]}};paths[1].write_text(json.dumps(review))
            self.assertEqual(g.approve(*paths)['status'],'ACCEPTED_FOR_PUBLICATION')
            for update in [dict(rows=0),dict(rows=99),dict(detector_regenerated=True)]:
                paths[3].write_text(json.dumps({**morph,**update}))
                review['evidence'][str(paths[3].resolve())]=g.digest(paths[3]);paths[1].write_text(json.dumps(review))
                with self.subTest(update=update),self.assertRaisesRegex(ValueError,'Morphology'):g.approve(*paths)
            paths[3].write_text(json.dumps(morph));review['evidence'][str(paths[3].resolve())]=g.digest(paths[3])
            review['files']={};paths[1].write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError,'exact stage'):g.approve(*paths)
            review['files']=files;paths[1].write_text(json.dumps(review));asset.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'asset changed'):g.approve(*paths)
if __name__=='__main__':unittest.main()
