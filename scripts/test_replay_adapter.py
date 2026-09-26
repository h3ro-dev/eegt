"""Small synthetic verification fixtures only; no EEG or empirical run."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest

from replay_validation_bounded import PartitionGate, replay


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.executescript('CREATE TABLE completed_blocks(candidate_index INTEGER);'
                             'CREATE TABLE candidates(candidate_index INTEGER,status TEXT);'
                             'CREATE TABLE partitions(candidate_index INTEGER,branch TEXT,variant TEXT,'
                             'path TEXT,sha256 TEXT,bytes INTEGER,header_json TEXT);'
                             "INSERT INTO completed_blocks VALUES(0);INSERT INTO candidates VALUES(0,'ELIGIBLE');")
        self.calls = 0
        canonical = lambda x: json.dumps(x, sort_keys=True)
        digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        path = lambda root, ci, branch, variant: Path(root) / f'{ci}-{branch}-{variant}.json'

        def read(p):
            self.calls += 1
            return json.loads(Path(p).read_text()), {'events': []}

        self.study = SimpleNamespace(NATIVE_VARIANTS=('primary', 'control'), PREPARED_VARIANTS=('original',),
                                     canonical=canonical, digest=digest, _inside=lambda r, p: r / p,
                                     partition_path=path, read_partition=read,
                                     verify_indexed_partitions=lambda *_: None)
        for branch, variants in [('native', self.study.NATIVE_VARIANTS), ('prepared', self.study.PREPARED_VARIANTS)]:
            for variant in variants:
                p = path(self.root, 0, branch, variant)
                header = dict(candidate_index=0, branch=branch, variant=variant)
                p.write_text(canonical(header))
                self.db.execute('INSERT INTO partitions VALUES(?,?,?,?,?,?,?)',
                                (0, branch, variant, p.name, digest(p), p.stat().st_size, canonical(header)))
        self.gate = PartitionGate(self.study, self.root)

    def all_reads(self):
        for p in self.gate.inventory:
            self.gate.read(p)

    def test_single_payload_pass_and_two_gates(self):
        self.assertEqual(self.gate.verify(self.root, self.db), 3)
        self.all_reads()
        self.assertEqual(self.calls, 3)
        self.assertEqual(self.gate.verify(self.root, self.db), 3)
        self.assertEqual(self.calls, 3)

    def test_missing_read_fails_final_gate(self):
        self.gate.verify(self.root, self.db)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.gate.verify(self.root, self.db)

    def test_changed_compressed_bytes_rejected_before_read(self):
        self.gate.verify(self.root, self.db)
        p = next(iter(self.gate.inventory)); p.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'bytes changed'):
            self.gate.read(p)

    def test_changed_bytes_after_read_rejected_at_final_gate(self):
        self.gate.verify(self.root, self.db); self.all_reads()
        next(iter(self.gate.inventory)).write_text('changed')
        with self.assertRaisesRegex(ValueError, 'bytes changed'):
            self.gate.verify(self.root, self.db)

    def test_wrong_saved_header_rejected(self):
        self.db.execute("UPDATE partitions SET header_json='{}'")
        self.gate.verify(self.root, self.db)
        with self.assertRaisesRegex(ValueError, 'header changed'):
            self.gate.read(next(iter(self.gate.inventory)))

    def test_wrong_decoded_identity_rejected_even_with_matching_saved_header(self):
        p = self.root / '0-native-primary.json'
        header = dict(candidate_index=999, branch='native', variant='primary')
        p.write_text(self.study.canonical(header))
        self.db.execute('UPDATE partitions SET sha256=?,bytes=?,header_json=? WHERE path=?',
                        (self.study.digest(p), p.stat().st_size, self.study.canonical(header), p.name))
        self.gate.verify(self.root, self.db)
        with self.assertRaisesRegex(ValueError, 'header changed'):
            self.gate.read(p)

    def test_altered_inventory_rejected(self):
        self.gate.verify(self.root, self.db); self.all_reads()
        self.db.execute("UPDATE partitions SET sha256='different'")
        with self.assertRaisesRegex(ValueError, 'inventory changed'):
            self.gate.verify(self.root, self.db)

    def test_duplicate_identity_rejected(self):
        self.db.execute('INSERT INTO partitions SELECT * FROM partitions LIMIT 1')
        with self.assertRaisesRegex(ValueError, 'membership'):
            self.gate.verify(self.root, self.db)

    def test_incomplete_blocks_rejected(self):
        self.db.execute("INSERT INTO candidates VALUES(1,'ELIGIBLE')")
        with self.assertRaisesRegex(ValueError, 'completed selected-block'):
            self.gate.verify(self.root, self.db)

    def test_repeated_read_and_unexpected_third_gate_rejected(self):
        self.gate.verify(self.root, self.db); self.all_reads()
        with self.assertRaisesRegex(ValueError, 'repeated'):
            self.gate.read(next(iter(self.gate.inventory)))
        self.gate.verify(self.root, self.db)
        with self.assertRaisesRegex(ValueError, 'call order'):
            self.gate.verify(self.root, self.db)

    def test_frozen_reader_failure_propagates(self):
        self.gate.original_read = lambda p: (_ for _ in ()).throw(ValueError('event hash mismatch'))
        self.gate.verify(self.root, self.db)
        with self.assertRaisesRegex(ValueError, 'event hash'):
            self.gate.read(next(iter(self.gate.inventory)))
        self.assertFalse(self.gate.seen)

    def test_wrapper_restores_functions_and_refuses_partial_summary(self):
        index = self.root / 'results/013/analysis.sqlite'
        index.parent.mkdir(parents=True); index.write_bytes(b'fixture index')
        old_read, old_verify = self.study.read_partition, self.study.verify_indexed_partitions

        def fake_frozen(root):
            self.study.verify_indexed_partitions(root, self.db)
            for p in sorted(root.glob('*.json')):
                self.study.read_partition(p)
            self.study.verify_indexed_partitions(root, self.db)
            return dict(status='REPLAYED_RECORDED_EVENTS', full_scientific_summary=False,
                        partitions=3, detector_regenerated=False)

        self.study.replay_events = fake_frozen
        with self.assertRaisesRegex(ValueError, 'Full frozen replay'):
            replay(self.study, self.root)
        self.assertIs(self.study.read_partition, old_read)
        self.assertIs(self.study.verify_indexed_partitions, old_verify)

    def test_resource_failure_prevents_payload_acceptance(self):
        def fail():
            raise RuntimeError('Fixed RSS bound exceeded')
        gate = PartitionGate(self.study, self.root, fail)
        gate.verify(self.root, self.db)
        with self.assertRaisesRegex(RuntimeError, 'RSS'):
            gate.read(next(iter(gate.inventory)))
        self.assertFalse(gate.seen)

    def test_complete_wrapper_returns_disclosed_adapter_and_restores_functions(self):
        index = self.root / 'results/013/analysis.sqlite'
        index.parent.mkdir(parents=True); index.write_bytes(b'fixture index')
        old_read, old_verify = self.study.read_partition, self.study.verify_indexed_partitions

        def fake_frozen(root):
            self.study.verify_indexed_partitions(root, self.db)
            for p in sorted(root.glob('*.json')):
                self.study.read_partition(p)
            self.study.verify_indexed_partitions(root, self.db)
            return dict(status='REPLAYED_RECORDED_EVENTS', full_scientific_summary=True,
                        partitions=3, detector_regenerated=False)

        self.study.replay_events = fake_frozen
        result = replay(self.study, self.root)
        self.assertEqual(result['decoded_partitions'], 3)
        self.assertTrue(result['final_compressed_bytes_rechecked'])
        self.assertEqual(result['verification_adapter'], 'single-payload-pass/v1')
        self.assertIs(self.study.read_partition, old_read)
        self.assertIs(self.study.verify_indexed_partitions, old_verify)


if __name__ == '__main__':
    unittest.main()
