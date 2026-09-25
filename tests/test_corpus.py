import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from eegt import corpus
from eegt.acquire import digest


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_path_traversal_and_symlink_escape(self):
        for value in ['../escape', '/tmp/escape', 'sub/../../escape', r'sub\escape']:
            with self.assertRaises(ValueError):
                corpus.safe_path(self.root, value)
        (self.root / 'link').symlink_to(self.root.parent)
        with self.assertRaises(ValueError):
            corpus.safe_path(self.root, 'link/escape')

    def test_pinned_identity_and_existing_wrong_cache_are_not_overwritten(self):
        sha = hashlib.sha256(b'expected').hexdigest()
        spec = corpus.annex_identity(f'../../SHA256E-s8--{sha}.fdt')
        target = self.root / 'record.fdt'
        target.write_bytes(b'corrupt!')
        with patch.object(corpus.urllib.request, 'urlopen') as request:
            with self.assertRaisesRegex(ValueError, 'preserve for investigation'):
                corpus.acquire_file(spec, target)
            request.assert_not_called()
        self.assertEqual(target.read_bytes(), b'corrupt!')
        with self.assertRaises(ValueError):
            corpus.annex_identity('SHA256E-s8--abcd.fdt')

    def test_sealed_artifacts_reject_changes(self):
        path = self.root / 'frozen.json'
        corpus.atomic_json(path, {'a': 1}, immutable=True)
        with self.assertRaises(ValueError):
            corpus.atomic_json(path, {'a': 2}, immutable=True)
        self.assertEqual(json.loads(path.read_text()), {'a': 1})

    def fixture(self):
        protocol = self.root / 'protocol/corpus-v1.json'
        protocol.parent.mkdir()
        protocol.write_text('{}')
        rec = dict(recording_id='anon', dataset='ds-test', subject_key='ds-test:sub-001',
                   source_subject='001', session_id='001', split='test', prior_project_exposure=False,
                   metadata=dict(SamplingFrequency=250, EEGChannelCount=2, RecordingDuration=10),
                   channels=[dict(name=n, type='EEG', units='uV', status='good') for n in ['E1','E2']], files=[])
        receipts = []
        for ext in ['set','fdt']:
            path = f'sub-001/eeg/record.{ext}'
            target = self.root / 'data/cache/ds-test' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(ext.encode())
            rec['files'].append(dict(path=path, bytes=3, algorithm='sha256', expected_digest=digest(target)))
            receipts.append(dict(dataset='ds-test', path=path, bytes=3, status='VERIFIED', sha256=digest(target)))
        manifest = dict(protocol_sha256=digest(protocol), sources=[dict(dataset='ds-test',version='1',git_commit='a',metadata={'License':'CC0'})],recordings=[rec],source_recordings=1)
        corpus.atomic_json(self.root / 'protocol/corpus-manifest-v1.json', manifest)
        corpus.atomic_json(self.root / 'results/corpus-v1/acquisition.json', dict(completed=True,manifest_sha256=digest(self.root / 'protocol/corpus-manifest-v1.json'), files=receipts, verified_bytes=6))
        class FakeRaw:
            info={'sfreq':250}
            n_times=2500
            ch_names=['E1','E2']
            annotations=type('Annotations',(),dict(onset=np.array([4.,6.]),duration=np.array([0.,1.]),description=np.array(['boundary','BAD_dropout'])))()
            def close(self): pass
        return FakeRaw()

    def test_qualification_preserves_discontinuities_and_sql_denominators(self):
        raw = self.fixture()
        with patch('mne.io.read_raw_eeglab', return_value=raw):
            summary = corpus.qualify(self.root)
        self.assertEqual(summary['qualified_recordings'], 1)
        conn = sqlite3.connect(self.root / 'results/corpus-v1/corpus.sqlite')
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute('SELECT start_sample,stop_sample,kind FROM discontinuities ORDER BY start_sample').fetchall(), [(1000,1000,'BOUNDARY'),(1500,1750,'BAD_INTERVAL')])
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM source_files').fetchone()[0], 2)
        self.assertEqual(conn.execute('SELECT source_participant_records,source_sessions FROM coverage').fetchone(), (1,1))
        self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_metadata_mismatch_quarantines_and_keeps_denominator(self):
        raw = self.fixture()
        raw.n_times=2600
        with patch('mne.io.read_raw_eeglab', return_value=raw):
            summary = corpus.qualify(self.root)
        self.assertEqual(summary['source_recordings'], 1)
        self.assertEqual(summary['qualified_recordings'], 0)
        self.assertEqual(summary['coverage'][0]['source_participant_records'], 1)
        self.assertIn('duration discrepancy',summary['records'][0]['reason'])


if __name__ == '__main__':
    unittest.main()
