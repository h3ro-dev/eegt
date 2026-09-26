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


if __name__ == '__main__':
    unittest.main()
