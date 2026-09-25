"""Meaningful checks for exact session-pair inference and missing-data behavior."""
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
from scipy.io import savemat
from eegt.repeated import paired_distances, record_metrics, qualify_record
from eegt.growth import VIEWS


class RepeatedTests(unittest.TestCase):
    def test_embedded_decode_calibration_aux_exclusion_and_json_receipt(self):
        names=['RB','RT','LB','LT','ELE'];sf=250;n=1250
        x=np.tile(20*np.sin(2*np.pi*9*np.arange(n)/sf),(5,1)).astype('float32')
        channels=np.array([(name,) for name in names],dtype=[('labels','O')])
        with TemporaryDirectory() as td:
            path=Path(td)/'test.set'
            savemat(path,dict(data=x,srate=sf,nbchan=5,pnts=n,trials=1,xmin=0,xmax=(n-1)/sf,chanlocs=channels))
            p={'expected_channels':names[:4],'expected_sample_rate_hz':sf,'analysis_seconds':4}
            rec={'channels':[dict(name=name,type='EEG',units='uV') for name in names[:4]],
                 'metadata':dict(EEGReference='average',SamplingFrequency=sf,RecordingDuration=(n-1)/sf)}
            r=qualify_record(path,rec,p)
            self.assertEqual(r['excluded_undeclared_channels'],['ELE'])
            self.assertEqual(r['duration_metadata_error_samples'],1)
            self.assertEqual(r['digital_conversion']['checked_values'],384)
            json.dumps(r,allow_nan=False)
            rec['channels'][0]['units']='V'
            with self.assertRaises(ValueError):qualify_record(path,rec,p)

    def test_exact_pairing_and_multiplicity(self):
        r=paired_distances([[0],[10],[20]],[[0],[10],[20]])
        self.assertEqual(r['same_person_mean_distance'],0)
        self.assertAlmostEqual(r['different_person_mean_distance'],80/6)
        self.assertEqual(r['permutation_count'],6)
        self.assertEqual(r['permutation_p_lower'],1/6)
        self.assertEqual(r['p_bonferroni_three_views'],.5)

    def test_no_pairing_information_has_p_one(self):
        r=paired_distances(np.ones((3,2)),np.ones((3,2)))
        self.assertEqual(r['permutation_p_lower'],1)
        self.assertEqual(r['mean_distance_advantage'],0)

    def test_renaming_and_feature_order_do_not_change_statistic(self):
        a=np.array([[0,2],[10,3],[20,4]]);b=a+1
        r=paired_distances(a,b)
        s=paired_distances(a[[2,0,1],::-1],b[[2,0,1],::-1])
        self.assertAlmostEqual(r['same_person_mean_distance'],s['same_person_mean_distance'])
        self.assertEqual(r['permutation_p_lower'],s['permutation_p_lower'])

    def test_invalid_pairs_are_not_silently_imputed(self):
        for a,b in [([[1],[2]],[[1],[2]]),([[1],[2],[3]],[[1],[2],[np.nan]]),([[1],[2],[3]],[[1,2],[2,3],[3,4]])]:
            with self.assertRaises(ValueError):paired_distances(a,b)

    def test_all_invalid_windows_report_missing_summaries_and_rates(self):
        a={'times':np.arange(20)/2,'segment':np.zeros(20,dtype=int),'valid':np.zeros(20,dtype=bool)}
        model={'references':{},'thresholds':{}}
        for v in VIEWS:
            a[v]=np.full((20,2),np.nan);model['references'][v]={'center':[0,0],'scale':[1,1]};model['thresholds'][v]={'2.0':1}
        r,e=record_metrics(a,model,{'hop_seconds':.5,'boundary':{'minimum_separation_seconds':2,'match_tolerance_seconds':1}})
        self.assertEqual(e,[])
        self.assertEqual(r['valid_windows'],0)
        self.assertTrue(all(x is None for x in r['standardized_medians'].values()))
        self.assertTrue(all(x['events_per_scored_minute'] is None for x in r['transition_rates'].values()))


if __name__=='__main__':unittest.main()
