"""Regression checks for independent review findings; synthetic data only."""
from pathlib import Path
import tempfile
import unittest

from eegt import validation_study as study
from tests.test_validation_study import synthetic_case, synthetic_frozen_root


class LedgerMembershipTests(unittest.TestCase):
    def test_zero_eligible_has_explicit_no_experiment_status(self):
        case = synthetic_case()
        pairs = {(r['source_subject'], r['session']) for r in case[1]['records']}
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_frozen_root(Path(tmp), synthetic_case(failed_pairs=pairs))
            inputs = study.load_inputs(root)
            db = study.open_index(root, inputs, 'synthetic-freeze', 'synthetic-acceptance')
            try:
                result = study.evaluate_index(root, inputs, db, 'synthetic-freeze', 'synthetic-acceptance')
                self.assertEqual(result['status'], 'NO_ELIGIBLE_BLOCKS')
                self.assertEqual(result['completed_event_blocks'], 0)
                self.assertEqual(len(result['primary_endpoints']), 8)
                self.assertTrue(all(e['test']['status'] == 'NOT_ESTIMABLE'
                                    for e in result['primary_endpoints']))
            finally:
                db.close()

    def test_correct_partition_count_with_wrong_block_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_frozen_root(Path(tmp), synthetic_case())
            inputs = study.load_inputs(root)
            db = study.open_index(root, inputs, 'synthetic-freeze', 'synthetic-acceptance')
            try:
                db.execute('INSERT INTO completed_blocks VALUES(0,?)', ('synthetic',))
                for branch, variants in [('native', study.NATIVE_VARIANTS), ('prepared', study.PREPARED_VARIANTS)]:
                    for variant in variants:
                        db.execute('INSERT INTO partitions VALUES(?,?,?,?,?,?,?)',
                                   (1, branch, variant, 'unused', 'unused', 0, '{}'))
                self.assertEqual(db.execute('SELECT count(*) FROM partitions').fetchone()[0], 23)
                with self.assertRaisesRegex(ValueError, 'completed-block membership'):
                    study.verify_indexed_partitions(root, db)
            finally:
                db.close()

    def test_resume_rejects_each_changed_candidate_field(self):
        changes = {'candidate_index':999, 'array_row':999, 'cohort':'wrong-cohort',
                   'person':'wrong-person', 'night':'wrong-night',
                   'recording_id':'wrong-recording', 'status':'wrong-status',
                   'reasons_json':'["wrong-reason"]'}
        for field, value in changes.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = synthetic_frozen_root(Path(tmp), synthetic_case())
                inputs = study.load_inputs(root)
                db = study.open_index(root, inputs, 'synthetic-freeze', 'synthetic-acceptance')
                db.execute(f'UPDATE candidates SET {field}=? WHERE candidate_index=0', (value,))
                db.commit()
                db.close()
                with self.assertRaisesRegex(ValueError, 'identity/census mismatch'):
                    study.open_index(root, inputs, 'synthetic-freeze', 'synthetic-acceptance')

    def test_unselected_completed_candidate_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_frozen_root(Path(tmp), synthetic_case())
            inputs = study.load_inputs(root)
            db = study.open_index(root, inputs, 'synthetic-freeze', 'synthetic-acceptance')
            try:
                db.execute('INSERT INTO completed_blocks VALUES(1,?)', ('synthetic',))
                with self.assertRaisesRegex(ValueError, 'not a selected candidate'):
                    study.verify_indexed_partitions(root, db)
            finally:
                db.close()


if __name__ == '__main__':
    unittest.main()
