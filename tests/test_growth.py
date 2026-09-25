from functools import lru_cache
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,Mock
import json

import numpy as np

from eegt import growth,transitions as tr
from eegt import controls,calibrate


class GrowthTests(unittest.TestCase):
    def test_completed_receipt_rejects_missing_or_duplicated_records(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'results/003').mkdir(parents=True);(root/'results/corpus-v1').mkdir()
            records=[dict(recording_id=k,status='QUALIFIED') for k in ['train','test','external']]
            (root/'results/corpus-v1/calibration.json').write_text(json.dumps(dict(corpus_sha256='sha',records=[dict(recording_id=r['recording_id'],status='PASS') for r in records])))
            for ids in [[],['train','test'],['train','test','external','external']]:
                receipt=dict(inputs={},completed=True,records=[dict(recording_id=i,status='FAILED',reason='fixture') for i in ids])
                (root/'results/003/features.json').write_text(json.dumps(receipt))
                with patch.object(growth,'input_identity',return_value={}),patch.object(growth,'catalog',return_value=(Mock(),records)),patch.object(growth,'digest',return_value='sha'):
                    with self.assertRaisesRegex(ValueError,'every catalog record exactly once'):growth.verified_features(root)

    def test_cached_controls_reject_changed_count_and_wrong_id(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'record.json';inputs={'source':'known'}
            value=dict(inputs=inputs,result=dict(recording_id='record',status='INSUFFICIENT_CONTEXT'))
            path.write_text(json.dumps(value));index={'files':{path.name:controls.digest(path)}}
            self.assertEqual(controls.cached_row(path,inputs,index,'record'),value['result'])
            value['result']['event_count']=999;path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'altered cached'):controls.cached_row(path,inputs,index,'record')
            index['files'][path.name]=controls.digest(path)
            with self.assertRaisesRegex(ValueError,'identity mismatch'):controls.cached_row(path,inputs,index,'different')

    def test_reversal_uses_identical_reflected_window_grid(self):
        rate=100;t=np.arange(14400)/rate;x=np.array([12*np.sin(2*np.pi*(8+i)*t) for i in range(4)])
        p={'window_seconds':2,'hop_seconds':.5,'halo_seconds':12,'controls':{'maximum_seconds_per_recording':120}}
        a=controls.pack(x,rate,p);b=controls.pack(x[:,::-1],rate,p,reverse_grid=True)
        np.testing.assert_allclose(a['times'],120-b['times'][::-1],atol=1e-12)
        np.testing.assert_array_equal(a['valid'],b['valid'][::-1])

    def test_known_native_values_decode_as_microvolts(self):
        import mne
        from scipy.io import savemat
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);wave=np.array([[1.,-2.,3.,-4.]*25,[5.,-6.,7.,-8.]*25],dtype='<f4')
            fdt=root/'known.fdt';wave.T.tofile(fdt)
            locs=np.empty(2,dtype=[('labels','O')]);locs['labels']=['E1','E2']
            savemat(root/'known.set',{'EEG':dict(data='known.fdt',srate=200.,pnts=100.,nbchan=2.,trials=1.,chanlocs=locs,xmin=0.,xmax=.495)})
            raw=mne.io.read_raw_eeglab(root/'known.set',preload=False,verbose='ERROR')
            self.addCleanup(raw.close)
            result=calibrate.verify_conversion(raw,fdt,[0,1])
            self.assertLess(result['maximum_absolute_error_uv'],1e-9)
            with patch.object(raw,'get_data',return_value=np.ones((2,32))):
                with self.assertRaisesRegex(ValueError,'native microvolts'):calibrate.verify_conversion(raw,fdt,[0,1])

    def test_continuity_preserves_zero_boundary_and_merges_bad_intervals(self):
        self.assertEqual(growth.continuous_intervals(100,[(20,20),(40,60),(50,70),(80,80)]),[(0,20),(20,40),(70,80),(80,100)])
        with self.assertRaises(ValueError): growth.continuous_intervals(100,[(60,50)])

    def test_sparse_matching_equals_independent_exhaustive_small_optimum(self):
        rng=np.random.default_rng(19)
        for _ in range(40):
            a=np.sort(rng.uniform(0,5,size=5));b=np.sort(rng.uniform(0,5,size=6)); tolerance=.7
            @lru_cache(None)
            def brute(i,j):
                if i==len(a) or j==len(b):return (0,0.)
                opts=[brute(i+1,j),brute(i,j+1)]
                if abs(a[i]-b[j])<=tolerance:
                    n,cost=brute(i+1,j+1);opts.append((n+1,cost+abs(a[i]-b[j])))
                return min(opts,key=lambda x:(-x[0],x[1]))
            expected=brute(0,0);got=tr.match_boundaries(a,b,tolerance_seconds=tolerance)
            self.assertEqual(got['matched'],expected[0])
            self.assertAlmostEqual(got['total_abs_error_seconds'],expected[1])
        a=np.arange(3000)*3.
        large=tr.match_boundaries(a,a+.1)
        self.assertEqual(large['matched'],3000)

    def test_chunk_integration_keeps_native_gap_and_matches_direct_features(self):
        rate=100;time=np.arange(9000)/rate
        samples=np.array([12*np.sin(2*np.pi*(8+i)*time+.2*i) for i in range(4)])
        class Raw:
            info={'sfreq':rate}
            def get_data(self,picks,start,stop):return samples[picks,start:stop]/1e6
            def close(self):pass
        protocol=dict(chunk_seconds=12,halo_seconds=12,window_seconds=2,hop_seconds=.5)
        with tempfile.TemporaryDirectory() as d, patch.object(growth,'source_raw',return_value=(Raw(),[0,1,2,3],[(0,4000),(5000,9000)])):
            root=Path(d)
            row=growth.extract_record(root,None,{'recording_id':'test'},protocol)
            a=growth.load_features(root,row)
            self.assertFalse(np.any((a['times']>39)&(a['times']<51)))
            expected=tr.extract_features(samples[:,:4000],rate)
            first=a['segment']==0
            np.testing.assert_array_equal(a['times'][first],expected['times'])
            for view in growth.VIEWS:np.testing.assert_allclose(a[view][first],expected['views'][view],equal_nan=True,atol=1e-12)

    def test_fit_does_not_load_test_or_external_rows(self):
        records=[dict(recording_id=s,split=s) for s in ['train','test','external']]
        calls=[]
        def load(root,row):
            calls.append(row['id']);self.assertEqual(row['id'],'train')
            t=np.arange(100)*.5
            return dict(times=t,valid=np.ones(100,dtype=bool),segment=np.zeros(100,dtype=int),**{v:np.c_[np.sin(t),np.cos(t)] for v in growth.VIEWS})
        p={'fit':{'maximum_feature_rows_per_recording':20,'threshold_quantile':.95},'boundary':{'scales_seconds':[.5,2.,8.]}}
        with patch.object(growth,'load_features',side_effect=load):
            _,thresholds,ids=growth.fit(Path('.'),records,{s:{'id':s} for s in ['train','test','external']},p)
        self.assertEqual(ids,['train']);self.assertEqual(calls,['train','train'])
        self.assertTrue(all(np.isfinite(x) for t in thresholds.values() for x in t.values()))


if __name__=='__main__':unittest.main()
