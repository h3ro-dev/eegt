import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from eegt import distributed_study as study
from eegt import pretrained_study as old


class DistributedTests(unittest.TestCase):
    def test_lower_median_per_stratum_is_order_independent(self):
        rows=[dict(candidate_index=i,recording_id='a',stratum_index=i//4,
                   start_seconds=i*30,quality_status='PASS' if i!=5 else 'FAIL') for i in range(8)]
        self.assertEqual(study.selected_indices(rows),[1,6])
        self.assertEqual(study.selected_indices(rows[::-1]),[1,6])
        rows.append(dict(candidate_index=10,recording_id='b',stratum_index=0,start_seconds=0,quality_status='PASS'))
        self.assertEqual(study.selected_indices(rows),[1,6,10])

    def test_gate_requires_both_nights_and_enough_people(self):
        rows=[]
        for person,n1,n2 in [('001',3,3),('002',12,2),('003',4,4),('004',3,3)]:
            for session,n in [('001',n1),('002',n2)]:
                rows.extend(dict(source_subject=person,session=session,status='ELIGIBLE') for _ in range(n))
        gate=study.paired_gate(rows)
        self.assertEqual(gate['complete_participants'],['001','003','004'])
        self.assertEqual(gate['status'],'READY')
        self.assertEqual(study.paired_gate(rows[:-1])['status'],'INSUFFICIENT_PARTICIPANTS')

    def fixture(self,root):
        protocol={'source':{'subjects':[f'{i:03}' for i in range(1,7)],'sessions':['001','002']},
                  'quality':{'minimum_blocks_per_record':3,'minimum_complete_participants':3}}
        (root/'protocol').mkdir();(root/'protocol/experiment-010.json').write_text(json.dumps(protocol))
        rows=[]
        for person in protocol['source']['subjects']:
            for session in protocol['source']['sessions']:
                for start in range(0,14400,30):
                    quality=start in (30,60,90,1230,2430)
                    rows.append(dict(candidate_index=len(rows),recording_id=person+session,
                                     source_subject=person,session=session,start_seconds=start,stratum_index=start//1200,
                                     quality_status='PASS' if quality else 'FAIL',status='QUALIFIED_UNSELECTED' if quality else 'REJECTED',
                                     reasons=[] if quality else ['BASELINE_QC']))
        selected=set(study.selected_indices(rows));n=len(selected)
        arrays=dict(patches=np.zeros((n,4,30,200),dtype=np.float32),candidate_indices=np.array(sorted(selected)))
        for view in old.VIEWS:arrays['baseline_'+view]=np.zeros((n,28,1))
        index=0
        for row in rows:
            if row['candidate_index'] in selected:
                row.update(status='ELIGIBLE',array_row=index,prepared_array_sha256=old.array_hash(arrays['patches'][index]),
                           baseline_array_sha256={v:old.array_hash(arrays['baseline_'+v][index]) for v in old.VIEWS})
                index+=1
        old.save_arrays(root/'prepared.npz',**arrays)
        receipt=dict(inputs={'protocol/experiment-010.json':old.digest(root/'protocol/experiment-010.json')},
                     records=rows,inference_gate=study.paired_gate(rows),array_path='prepared.npz',array_sha256=old.digest(root/'prepared.npz'))
        return receipt,protocol

    def test_census_validates_and_rejects_alternative_qualifying_selection(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);receipt,protocol=self.fixture(root)
            self.assertEqual(study.validate_selection(root,receipt,protocol)['complete_participant_count'],6)
            changed=copy.deepcopy(receipt)
            changed['records'][1]['status']='ELIGIBLE'
            changed['records'][2]['status']='QUALIFIED_UNSELECTED'
            with self.assertRaisesRegex(ValueError,'selection mismatch'):study.validate_selection(root,changed,protocol)

    def test_refuses_missing_time_or_forged_gate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);receipt,protocol=self.fixture(root)
            changed=copy.deepcopy(receipt);changed['records'][10]['start_seconds']=270
            with self.assertRaisesRegex(ValueError,'interval census'):study.validate_selection(root,changed,protocol)
            changed=copy.deepcopy(receipt);changed['inference_gate']['complete_participant_count']=99
            with self.assertRaisesRegex(ValueError,'gate mismatch'):study.validate_selection(root,changed,protocol)
            changed=copy.deepcopy(receipt);changed['records'][2]['reasons']=['BASELINE_QC']
            with self.assertRaisesRegex(ValueError,'status/reason'):study.validate_selection(root,changed,protocol)

    def test_refuses_protocol_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);receipt,protocol=self.fixture(root)
            (root/'protocol/experiment-010.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'prepared input changed'):study.validate_selection(root,receipt,protocol)


if __name__=='__main__':unittest.main()
