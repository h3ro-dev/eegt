"""Guard public denominators against counting incomplete people as primary."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('report_events', Path(__file__).parents[1] / 'scripts/report_events.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class ReportDenominators(unittest.TestCase):
    def test_incomplete_people_are_retained_but_not_primary(self):
        endpoint = dict(model='encoder', metric='geometry', paired_valid_blocks=15,
                        participants=[dict(person='a', status='COMPLETE'), dict(person='b', status='INCOMPLETE_NIGHTS')],
                        records=[dict(person='a', paired_valid_blocks=3), dict(person='a', paired_valid_blocks=4),
                                 dict(person='b', paired_valid_blocks=1), dict(person='b', paired_valid_blocks=7)],
                        test=dict(status='NOT_ESTIMABLE', p_two_sided=None))
        row, = report.primary_rows(dict(primary_endpoints=[endpoint]))
        self.assertEqual((row['people'], row['primary_blocks'], row['all_paired_valid_blocks']), (1, 7, 15))
        self.assertIsNone(row['p_two_sided'])

    def test_resolution_and_noise_prose_follow_actual_values(self):
        self.assertIn('0.125', report.resolution_text([dict(people=6)]))
        self.assertIn('0.25', report.resolution_text([dict(people=5)]))
        self.assertIn('not', report.number(None))
        rows = [dict(trials=100, trials_with_detection=99, method_and_band='bycycle_1.2.0:4-8')]
        self.assertIn('varied', report.noise_text(rows))
        rows[0]['trials_with_detection'] = 100
        self.assertIn('every scored trial', report.noise_text(rows))


if __name__ == '__main__':
    unittest.main()
