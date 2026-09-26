import copy
import importlib.util
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch,Mock
from types import SimpleNamespace
import numpy as np
from eegt.validation_engineering import read_window,digest,prepare


class EngineeringTests(unittest.TestCase):
    def test_unaccepted_freeze_prevents_source_access(self):
        gate=Mock(side_effect=ValueError('freeze not accepted'))
        with patch.dict('sys.modules',{'eegt.validation_intake':
                                      SimpleNamespace(require_accepted_freeze=gate)}):
            with patch('eegt.validation_engineering.read_window') as reader:
                with self.assertRaisesRegex(ValueError,'freeze not accepted'):
                    prepare('/missing-root','/missing-raw','/missing-contract','/missing-destination')
                reader.assert_not_called()
                gate.assert_called_once_with(root=Path('/missing-root'),phase='events')

    def fixture(self,directory,frames=40):
        data=np.arange(frames*13,dtype='<f4').reshape(frames,13)
        data[2,3]=np.nan
        path=Path(directory)/'fixture.fdt';data.tofile(path)
        names=['E'+str(i) for i in range(12)]+['EOGr']
        record=dict(status='QUALIFIED',stored_units='uV',sample_rate_hz=500,
            fdt_source=dict(path=path.name,bytes=path.stat().st_size,sha256=digest(path)),
            header=dict(nbchan=13,pnts=frames,trials=1,srate_hz=500,channel_names=names),
            native_eeg_pick_indices=list(range(12)),
            channels=[dict(index_0based=i,name=n,type='EEG' if i<12 else 'EOG',
                units='uV',included_in_ear_eeg=i<12,missing_intervals=[]) for i,n in enumerate(names)],
            common_zero_intervals=[dict(start_sample=8,stop_sample=10)])
        return data,record

    @unittest.skipUnless(importlib.util.find_spec('scipy'),'requires pinned events runtime')
    def test_preparation_receipt_array_join(self):
        from eegt.pretrained_study import array_hash
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'results/013').mkdir(parents=True)
            _,record=self.fixture(tmp,frames=15000)
            record.update(source_person='sub-001',finite_mask_set_sha256='synthetic-mask')
            records=[]
            for session in ('005','006'):
                row=copy.deepcopy(record)
                row.update(source_session='ses-'+session,recording_id='fixture-'+session)
                records.append(row)
            contract=root/'contract.json'
            contract.write_text(json.dumps(dict(schema='eegt-013-engineering-input-contract/v1',
                records=records,selection=dict(start_sample=0,samples=15000,seconds=30,
                                               adaptive_replacement=False))))
            module=root/'helper.py';module.write_text('# synthetic sealed helper identity\n')
            (root/'results/013/RUN-SOURCE-MANIFEST.json').write_text(json.dumps(dict(
                inputs={'helper.py':digest(module),'contract.json':digest(contract)})))
            with patch.dict('sys.modules',{'eegt.validation_intake':SimpleNamespace(
                    require_accepted_freeze=Mock())}):
                with patch('eegt.validation_engineering.__file__',str(module)):
                    result=prepare(root,root,contract,root/'prepared')
            self.assertEqual([r['session'] for r in result['records']],['005','006'])
            with np.load(root/result['array_path'],allow_pickle=False) as data:
                self.assertEqual(data['samples_uv'].shape,(2,12,15000))
                self.assertEqual(data['valid'].dtype,np.bool_)
                for index,row in enumerate(result['records']):
                    self.assertEqual(row['native_array_sha256'],array_hash(data['samples_uv'][index]))
                    self.assertEqual(row['valid_mask_sha256'],array_hash(data['valid'][index]))
            self.assertEqual(result['array_sha256'],digest(root/result['array_path']))

    def test_layout_contact_order_and_masks(self):
        with tempfile.TemporaryDirectory() as tmp:
            data,record=self.fixture(tmp)
            record['channels'][1]['missing_intervals']=[dict(start_sample=4,stop_sample=6)]
            samples,valid,names=read_window(tmp,record,count=10)
            np.testing.assert_equal(samples,data[:10,:12].T.astype(np.float64))
            self.assertEqual(samples.dtype,np.float64)
            self.assertEqual(valid.dtype,np.bool_)
            self.assertFalse(valid[3,2]);self.assertFalse(valid[:,8:].any())
            self.assertFalse(valid[1,4:6].any());self.assertTrue(valid[0,0])
            self.assertNotIn('EOGr',names)

    def test_source_change_and_short_support_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            data,record=self.fixture(tmp)
            with self.assertRaisesRegex(ValueError,'frame support'):
                read_window(tmp,record,count=41)
            with (Path(tmp)/'fixture.fdt').open('ab') as stream:stream.write(b'x')
            with self.assertRaisesRegex(ValueError,'changed FDT'):
                read_window(tmp,record,count=10)

    def test_no_undeclared_contact_or_unit_substitution(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,record=self.fixture(tmp)
            for field,value in [('stored_units','V'),('sample_rate_hz',250)]:
                bad=copy.deepcopy(record);bad[field]=value
                with self.assertRaises(ValueError):read_window(tmp,bad,count=10)
            bad=copy.deepcopy(record);bad['native_eeg_pick_indices'][-1]=12
            with self.assertRaisesRegex(ValueError,'non-EEG'):
                read_window(tmp,bad,count=10)
            bad=copy.deepcopy(record);bad['native_eeg_pick_indices'][-1]=0
            with self.assertRaisesRegex(ValueError,'picks'):
                read_window(tmp,bad,count=10)


if __name__=='__main__':unittest.main()
