"""Independent stdlib readback of the four archived Experiment 012 tests."""
import itertools
import json
import math
from pathlib import Path
import sqlite3
import statistics


BASE = Path(__file__).resolve().parents[1]
summary = json.loads((BASE / 'repo/results/012/summary.json').read_text())
public = json.loads((BASE / 'repo/site/data/events.json').read_text())
db = sqlite3.connect((BASE / 'scratch/analysis.sqlite').resolve().as_uri() + '?mode=ro', uri=True)

expected_counts = dict(candidates=5760, partitions=2806, native_timeline=8296,
                       native_match=99552, prepared_metric=2440, block_effect=488,
                       morphology_block=5368, completed_blocks=122)
actual_counts = {table: db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
                 for table in expected_counts}
assert actual_counts == expected_counts
assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
assert public['full_scientific_summary'] == summary

checks = []
for endpoint, public_row in zip(summary['primary_endpoints'], public['primary'], strict=True):
    rows = list(db.execute('SELECT array_row,effect FROM block_effect WHERE model=? AND metric=? ORDER BY array_row',
                           (endpoint['model'], endpoint['metric'])))
    assert [row[0] for row in rows] == list(range(122))
    offset, medians = 0, {}
    for record in endpoint['records']:
        count = record['selected_blocks']
        segment = rows[offset:offset + count]
        assert [row[0] for row in segment] == list(range(offset, offset + count))
        values = [effect for _, effect in segment if effect is not None and math.isfinite(effect)]
        median = statistics.median(values) if len(values) >= 3 else None
        assert record['paired_valid_blocks'] == len(values)
        expected = record['median_effect']
        assert (median is None and expected is None) or (median is not None and math.isclose(median, expected, abs_tol=1e-14))
        medians[record['person'], record['night']] = median
        offset += count
    assert offset == 122
    effects = []
    complete_people = []
    for person in sorted({p for p, _ in medians}):
        pair = [medians[person, night] for night in ('001', '002')]
        reported = next(p for p in endpoint['participants'] if p['person'] == person)
        if all(value is not None for value in pair):
            value = sum(pair) / 2
            assert reported['status'] == 'COMPLETE' and math.isclose(value, reported['effect'], abs_tol=1e-14)
            effects.append(value)
            complete_people.append(person)
        else:
            assert reported['status'] == 'INCOMPLETE_NIGHTS' and reported['effect'] is None
    mean = sum(effects) / len(effects)
    extreme = sum(abs(sum(value * sign for value, sign in zip(effects, signs)) / len(effects)) >= abs(mean) - 1e-14
                  for signs in itertools.product((-1, 1), repeat=len(effects)))
    test = endpoint['test']
    assert test['n'] == len(effects) == public_row['people']
    assert test['assignments'] == 2 ** len(effects) and test['extreme_count'] == extreme
    assert math.isclose(test['observed_mean'], mean, abs_tol=1e-14)
    assert math.isclose(test['p_two_sided'], extreme / 2 ** len(effects), abs_tol=1e-14)
    assert math.isclose(test['p_bonferroni_four'], min(1, 4 * test['p_two_sided']), abs_tol=1e-14)
    complete_blocks = sum(record['paired_valid_blocks'] for record in endpoint['records']
                          if record['person'] in complete_people)
    assert complete_blocks == public_row['primary_blocks'] == 110
    checks.append(dict(model=endpoint['model'], metric=endpoint['metric'], complete_people=complete_people,
                       primary_blocks=complete_blocks, all_paired_blocks=122, night_medians_checked=12,
                       mean=mean, assignments=2 ** len(effects), extreme=extreme,
                       raw_p=test['p_two_sided'], adjusted_p=test['p_bonferroni_four']))

print(json.dumps(dict(status='PASS', sqlite_tables=actual_counts, endpoints=checks), indent=2, sort_keys=True))
db.close()
