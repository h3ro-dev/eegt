"""Independent ledger/statistical checks; imports no EEGT study implementation."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import sqlite3
import statistics
import time
import numpy as np
from scipy.stats import spearmanr

checks = 0
maximum_error = 0.0


def check(condition, label):
    global checks
    if not condition:
        raise AssertionError(label)
    checks += 1


def equal(actual, expected, label):
    global maximum_error
    if actual is None or expected is None:
        check(actual is expected, label)
        return
    error = abs(float(actual) - float(expected))
    maximum_error = max(maximum_error, error)
    check(math.isfinite(float(actual)) and error < 1e-12, label)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def counts_and_support(path):
    matrix = np.zeros((30, 16), dtype=np.int64)
    columns = {'peak': 0, 'trough': 1, 'curvature_positive_to_negative': 2, 'curvature_negative_to_positive': 3}
    with gzip.open(path, 'rt') as f:
        first = json.loads(next(f))
        check(first['type'] == 'header', 'partition header')
        h = first['value']
        result = h['result']
        check(result['sample_rate_hz'] == 200, 'prepared physical rate')
        n = 0
        for line in f:
            item = json.loads(line)
            check(item['type'] == 'event', 'event record')
            r = item['value']
            n += 1
            if r['accepted'] and r['family'] in ('extremum', 'inflection'):
                ch = int(r['channel_key'].split('_')[-1])
                key = r['polarity'] if r['family'] == 'extremum' else r['direction']
                check(type(r['index']) is int and 0 <= r['index'] < 6000 and 0 <= ch < 4, 'sample coordinate')
                matrix[r['index'] // 200, ch * 4 + columns[key]] += 1
        check(n == h['event_rows'], 'partition row count')
    spans = defaultdict(list)
    for r in result['runs']:
        if r['status'] == 'OK':
            origin = r['clock_start_seconds'] - r['segment_start_sample'] / 200
            a = origin + (r['start_sample'] + r['guard_samples']) / 200
            b = origin + (r['end_sample'] - r['guard_samples']) / 200
            spans[r['channel_key']].append((a, b))
    support = {k for k in range(1, 29) if all(any(a <= k and k + 1 <= b for a, b in spans['channel_' + str(c)]) for c in range(4))}
    return matrix, support


def distance_vector(x, pairs):
    norms = np.linalg.norm(x, axis=1)
    if not np.isfinite(x).all() or (norms == 0).any() or not np.isfinite(norms).all():
        return None
    # This numerical convention is prescribed by the frozen protocol. Spearman
    # and hierarchical aggregation below use independent library/stdlb routes.
    rows = x / norms[:, None]
    values = np.asarray([1.0 - np.dot(rows[a], rows[b]) for a, b in pairs])
    if not len(values) or not np.isfinite(values).all() or np.ptp(values) <= 32 * np.finfo(float).eps * max(1., np.max(np.abs(values))):
        return None
    return values


def correlation(counts, latent, indices, metric):
    pairs = list(itertools.combinations(indices, 2)) if metric == 'geometry' else [(a, a + 1) for a in indices if a + 1 in indices]
    if (metric == 'geometry' and len(indices) < 8) or (metric == 'change' and len(pairs) < 7):
        return None
    # Required endpoints differ for adjacent pairs; do not salvage a bad vector.
    required = sorted(set(itertools.chain.from_iterable(pairs)))
    positions = {k: i for i, k in enumerate(required)}
    local = [(positions[a], positions[b]) for a, b in pairs]
    a, b = distance_vector(counts[required].astype(float), local), distance_vector(latent[required], local)
    if a is None or b is None:
        return None
    rho = float(spearmanr(a, b).statistic)
    return rho if math.isfinite(rho) else None


def run(packet, output):
    start = time.process_time()
    root = packet / 'repo'
    summary = read(root / 'results/012/summary.json')
    check(summary['status'] == 'COMPLETE_NUMERICAL_RECORD', 'complete scientific record')
    db_path = root / 'results/012/analysis.sqlite'
    db = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)
    check(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'SQLite integrity')
    expected_counts = dict(candidates=5760, partitions=2806, native_timeline=8296, native_match=99552,
                           prepared_metric=2440, block_effect=488, morphology_block=5368, completed_blocks=122)
    for table, count in expected_counts.items():
        check(db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == count, table)
    for name, row in read(packet / 'SOURCE-MANIFEST.json')['files'].items():
        check(sha(packet / name) == row['sha256'], 'inherited ' + name)
    for name, expected in db.execute('SELECT path,sha256 FROM partitions'):
        check(sha(root / name) == expected, 'partition hash ' + name)
    selected = [r for r in read(root / 'results/010/prepared.json')['records'] if r['status'] == 'ELIGIBLE']
    check(len(selected) == 122 and len({r['candidate_index'] for r in selected}) == 122, 'selection')
    latents = {model: np.load(root / path, allow_pickle=False)['embeddings'] for model, path in
               [('codebrain', 'data/derived/010/embeddings.npz'), ('cbramod', 'data/derived/011/embeddings.npz')]}
    metrics = {(i, v, m, k): json.loads(r) for i, v, m, k, r in db.execute('SELECT * FROM prepared_metric')}
    effects = {(i, m, k): (value, reason) for i, ci, m, k, value, reason, receipt in db.execute('SELECT * FROM block_effect')}
    values = {}
    for i, selected_row in enumerate(selected):
        branch = root / 'data/derived/012/events' / f'row-{i:03d}'
        inputs = {v: counts_and_support(branch / ('prepared-' + v + '.jsonl.gz')) for v in ['original', 'independent_phase']}
        support = sorted(inputs['original'][1] & inputs['independent_phase'][1])
        adjacent = [[a, a + 1] for a in support if a + 1 in support]
        for model, array in latents.items():
            for metric in ('geometry', 'change'):
                results = []
                for v in ('original', 'independent_phase'):
                    j = 0 if v == 'original' else 3
                    # Variant order is read from the actual archived array below.
                    archive = root / ('data/derived/010/embeddings.npz' if model == 'codebrain' else 'data/derived/011/embeddings.npz')
                    with np.load(archive, allow_pickle=False) as z:
                        j = list(z['variants']).index(v)
                    row = metrics[i, v, model, metric]
                    check(row['support']['interval_indices'] == support and row['support']['adjacent_pairs'] == adjacent, 'common support')
                    latent = np.mean(array[i, j], axis=0, dtype=np.float64)
                    rho = correlation(inputs[v][0], latent, support, metric)
                    equal(row['rho'], rho, f'correlation {i}/{model}/{metric}/{v}')
                    check((row['status'] == 'ESTIMABLE') == (rho is not None), 'estimability')
                    results.append(rho)
                delta = None if any(x is None for x in results) else results[0] - results[1]
                equal(effects[i, model, metric][0], delta, 'paired block effect')
                values[i, model, metric] = delta
    primary = []
    for endpoint in summary['primary_endpoints']:
        model, metric = endpoint['model'], endpoint['metric']
        groups = defaultdict(list)
        for i, r in enumerate(selected):
            groups[r['source_subject'], r['session'], r['recording_id']].append(values[i, model, metric])
        medians = {}
        valid_blocks = {}
        for row in endpoint['records']:
            key = row['person'], row['night'], row['recording_id']
            group = groups[key]
            valid = [v for v in group if v is not None]
            check(len(group) == row['selected_blocks'] and len(valid) == row['paired_valid_blocks'], 'record denominator')
            median = statistics.median(valid) if len(valid) >= 3 else None
            equal(row['median_effect'], median, 'night median')
            medians[row['person'], row['night']] = median
            valid_blocks[row['person'], row['night']] = len(valid)
        people = []
        primary_blocks = 0
        for row in endpoint['participants']:
            pair = [medians.get((row['person'], n)) for n in ('001', '002')]
            complete = all(v is not None for v in pair)
            effect = statistics.mean(pair) if complete else None
            equal(row['effect'], effect, 'participant effect')
            check((row['status'] == 'COMPLETE') == complete, 'participant status')
            if complete:
                people.append(effect)
                primary_blocks += sum(valid_blocks[row['person'], n] for n in ('001', '002'))
        test = endpoint['test']
        check(test['n'] == len(people), 'independent people')
        if len(people) >= 2:
            mean = statistics.mean(people)
            null = [statistics.mean(v * s for v, s in zip(people, signs)) for signs in itertools.product((-1, 1), repeat=len(people))]
            extreme = sum(abs(x) >= abs(mean) - 1e-12 for x in null)
            equal(test['observed_mean'], mean, 'primary mean')
            check(test['assignments'] == len(null) and test['extreme_count'] == extreme, 'exact null enumeration')
            equal(test['p_two_sided'], extreme / len(null), 'raw p')
            equal(test['p_bonferroni_four'], min(1, 4 * extreme / len(null)), 'adjusted p')
        primary.append(dict(model=model, metric=metric, people=len(people), primary_blocks=primary_blocks, test=test))
    for receipt, in db.execute('SELECT receipt_json FROM native_match'):
        r = json.loads(receipt)
        pairs = r['matched_input_index_pairs']
        check(len(pairs) == r['matched'] == len(r['signed_lags_seconds']), 'matching count')
        check(len({p[0] for p in pairs}) == len(pairs) == len({p[1] for p in pairs}), 'one-to-one matching')
        check(all(abs(x) <= r['tolerance_seconds'] + 1e-12 for x in r['signed_lags_seconds']), 'lag bound')
        denominator = r['n_a'] + r['n_b']
        equal(r['agreement'], 2 * r['matched'] / denominator if denominator else None, 'agreement arithmetic')
        check(r['matched'] <= min(r['n_a'], r['n_b']), 'eligible match count')
    db.close()
    receipt = dict(status='PASS', schema='eegt-012-independent-numerical-check/v1', assertions=checks,
                   maximum_absolute_error=maximum_error, primary=primary, expected_table_counts=expected_counts,
                   summary_sha256=sha(root / 'results/012/summary.json'), index_sha256=sha(db_path),
                   checker_sha256=sha(Path(__file__)), cpu_seconds=time.process_time() - start,
                   scope='No EEGT study imports: all inherited/partition hashes; complete original/phase event counts, support, 976 correlations and 488 effects; exact night/person tests; all 99,552 matching row invariants. Detector event regeneration and secondary metrics are separate checks.')
    output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.packet, args.output)
