import tempfile
import unittest
from pathlib import Path

import numpy as np

from eegt.acquire import digest
from eegt import pretrained_study as study


class StudyTests(unittest.TestCase):
    def test_rank_ties_and_undefined_constant(self):
        self.assertAlmostEqual(study.correlation([1,1,3,4],[8,8,9,10]),1)
        self.assertAlmostEqual(study.correlation([1,1,3,4],[8,8,7,6]),-1)
        self.assertIsNone(study.correlation([1,1,1],[2,3,4]))
        self.assertIsNone(study.correlation([1,2,3],[2,np.nan,4]))

    def test_distances_have_known_geometry(self):
        x=np.array([[1,0],[0,1],[-1,0]])
        np.testing.assert_allclose(study.cosine_distances(x),[[0,1,2],[1,0,1],[2,1,0]])
        self.assertEqual(study.rms_distances(np.array([[0,0],[3,4]]))[0,1],np.sqrt(12.5))
        with self.assertRaises(ValueError):study.cosine_distances(np.zeros((3,2)))

    def test_participant_balancing_and_incomplete_pair(self):
        rows=[];values=[]
        for person,session,count,value in [('a','001',3,0),('a','002',7,2),('b','001',9,4),('b','002',3,6),('c','001',4,100)]:
            rows.extend(dict(recording_id=person+session,source_subject=person,session=session) for _ in range(count))
            values.extend([value]*count)
        result,records,people=study.aggregate(values,rows)
        self.assertEqual(result[0],3)  # mean(person a=1, person b=5), c incomplete
        self.assertEqual(len(people),2)
        self.assertEqual(len(records),5)
        null,_,_=study.aggregate(np.array([values,np.array(values)+1]),rows)
        np.testing.assert_equal(null,[3,4])

    def test_waveform_controls_preserve_their_definitions(self):
        rng=np.random.default_rng(3);x=(rng.normal(size=(4,30,200))*.1).astype(np.float32)
        np.testing.assert_equal(study.waveform_variant(x,'gain_half',3),x*.5)
        np.testing.assert_equal(study.waveform_variant(x,'polarity_flip',3),-x)
        np.testing.assert_equal(study.waveform_variant(x,'channel_reverse',3),x[::-1])
        phase=study.waveform_variant(x,'independent_phase',3)
        np.testing.assert_equal(phase,study.waveform_variant(x,'independent_phase',3))
        np.testing.assert_allclose(np.abs(np.fft.rfft(phase.reshape(4,6000))),np.abs(np.fft.rfft(x.reshape(4,6000))),rtol=3e-5,atol=2e-6)
        self.assertFalse(np.array_equal(x,phase))

    def test_preprocessing_rejects_missing_flat_and_wrong_duration(self):
        with self.assertRaises(ValueError):study.preprocess_block(np.zeros((4,7500)))
        with self.assertRaises(ValueError):study.preprocess_block(np.zeros((4,6000)))
        t=np.arange(7500)/250;x=np.tile(10*np.sin(2*np.pi*10*t),(4,1))
        patches,peak=study.preprocess_block(x)
        self.assertEqual(patches.shape,(4,30,200));self.assertEqual(patches.dtype,np.float32)
        self.assertGreater(peak,5);self.assertLess(peak,30)
        x[0,5]=np.nan
        with self.assertRaises(ValueError):study.preprocess_block(x)

    def test_hash_binding_rejects_same_length_source_permutation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'prepared.npz'
            x=np.zeros((2,4,30,200),np.float32);x[1]=1
            arrays=dict(patches=x,candidate_indices=np.array([3,9]))
            for view in study.VIEWS:arrays['baseline_'+view]=np.arange(56,dtype=float).reshape(2,28,1)
            study.save_arrays(path,**arrays)
            rows=[dict(status='ELIGIBLE',candidate_index=int(c),array_row=i,prepared_array_sha256=study.array_hash(x[i]),baseline_array_sha256={v:study.array_hash(arrays['baseline_'+v][i]) for v in study.VIEWS}) for i,c in enumerate([3,9])]
            receipt=dict(array_path='prepared.npz',array_sha256=digest(path),records=rows)
            study.validate_prepared(root,receipt)
            arrays['baseline_morphology']=arrays['baseline_morphology'][::-1]
            study.save_arrays(path,**arrays);receipt['array_sha256']=digest(path)
            with self.assertRaisesRegex(ValueError,'descriptor/source identity'):study.validate_prepared(root,receipt)
            arrays['baseline_morphology']=arrays['baseline_morphology'][::-1]
            arrays['patches']=x[::-1]
            study.save_arrays(path,**arrays);receipt['array_sha256']=digest(path)
            with self.assertRaisesRegex(ValueError,'waveform/source identity'):study.validate_prepared(root,receipt)

    def test_known_alignment_exceeds_cyclic_control(self):
        rng=np.random.default_rng(4);x=rng.normal(size=(28,12));x/=np.linalg.norm(x,axis=1,keepdims=True)
        r=study.block_comparison(x,x)
        self.assertAlmostEqual(r['geometry'],1)
        self.assertAlmostEqual(r['change'],1)
        self.assertLess(max(r['geometry_null']),1)
        self.assertEqual(len(r['geometry_null']),27);self.assertEqual(len(r['change_null']),26)


if __name__=='__main__':unittest.main()
