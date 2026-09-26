"""Independent root calculation from archives; does not import study analysis."""
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[name] = '1'
import datetime
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3
import numpy as np
from scipy.spatial.distance import pdist, squareform
from scipy.stats import spearmanr

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--packet-root', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    raise FileExistsError('preserve an existing independent check')
packet = args.packet_root.resolve()
root = packet / 'repo'
load = lambda p: json.loads((root / p).read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
summary = load('results/011/summary.json')
prepared = load('results/010/prepared.json')
selected = [r for r in prepared['records'] if r['status'] == 'ELIGIBLE']
ids = [r['candidate_index'] for r in selected]
index = {ci: i for i, ci in enumerate(ids)}
variants = ['original', 'gain_half', 'polarity_flip', 'channel_reverse', 'independent_phase']
checks = 0
max_error = 0.0

def close(observed, expected):
    global checks, max_error
    checks += 1
    if expected is None:
        assert observed is None
    else:
        error = abs(float(observed) - float(expected))
        max_error = max(error, max_error)
        assert error <= 1e-12, (observed, expected, error)

archives = {}
for model, experiment in [('codebrain', '010'), ('cbramod', '011')]:
    receipt = load(f'results/{experiment}/inference.json')
    archive_path = root / receipt['array_path']
    assert sha(archive_path) == receipt['array_sha256']
    with np.load(archive_path, allow_pickle=False) as f:
        assert list(f['candidate_indices']) == ids
        assert list(f['variants']) == variants
        a = f['embeddings']
    assert a.shape == (122, 5, 4, 30, 200) and a.dtype == np.float32
    for i, ci in enumerate(ids):
        for j, variant in enumerate(variants):
            r = receipt['measurements'][5 * i + j]
            x = np.ascontiguousarray(a[i, j])
            assert r['candidate_index'] == ci and r['variant'] == variant
            assert hashlib.sha256(x.dtype.str.encode() + str(x.shape).encode() + x.tobytes()).hexdigest() == r['output_sha256']
            checks += 1
    archives[model] = a.astype(np.float64).mean(axis=2)[:, :, 1:29]
with np.load(root / 'data/derived/010/prepared.npz', allow_pickle=False) as f:
    baselines = {view: f['baseline_' + view] for view in ('morphology', 'spectrum', 'coordination')}

def distances(x, descriptor=False):
    d = pdist(x, 'euclidean' if descriptor else 'cosine')
    if descriptor:
        d = d / np.sqrt(x.shape[1])
    return {'geometry': d, 'change': np.diag(squareform(d), k=1)}

vectors = {(m, i, j): distances(a[i, j]) for m, a in archives.items() for i in range(122) for j in range(5)}
cross = {}
for r in summary['block_cross_model']:
    i, j = index[r['candidate_index']], variants.index(r['variant'])
    for metric in ('geometry', 'change'):
        value = spearmanr(vectors['codebrain', i, j][metric], vectors['cbramod', i, j][metric]).statistic
        close(r[metric + '_rho'], value)
        assert r[metric + '_reason'] is None
        cross[r['candidate_index'], r['variant'], metric] = float(value)
for r in summary['block_within_model']:
    i, j, m = index[r['candidate_index']], variants.index(r['variant']), r['model']
    for metric in ('geometry', 'change'):
        close(r[metric + '_rho'], spearmanr(vectors[m, i, 0][metric], vectors[m, i, j][metric]).statistic)
    close(r['rms_embedding_displacement'], np.sqrt(np.mean((archives[m][i, j] - archives[m][i, 0]) ** 2)))
for r in summary['block_descriptors']:
    i, m = index[r['candidate_index']], r['model']
    d = distances(baselines[r['view']][i], True)
    for metric in ('geometry', 'change'):
        close(r[metric + '_rho'], spearmanr(vectors[m, i, 0][metric], d[metric]).statistic)

primary = []
for p in summary['primary']:
    metric = p['metric']
    effects = []
    support = []
    for person in sorted({r['source_subject'] for r in selected}):
        medians = []
        person_indices = []
        for session in ('001', '002'):
            group = [r for r in selected if r['source_subject'] == person and r['session'] == session]
            if len(group) < 3:
                break
            deltas = [cross[r['candidate_index'], 'original', metric] - cross[r['candidate_index'], 'independent_phase', metric] for r in group]
            medians.append(float(np.median(deltas)))
            person_indices.extend(r['candidate_index'] for r in group)
        expected = next(r for r in p['aggregates']['delta']['participants'] if r['source_subject'] == person)
        if len(medians) == 2:
            effect = float(np.mean(medians))
            close(expected['mean_two_sessions'], effect)
            effects.append(effect)
            support.extend(person_indices)
        else:
            assert expected['status'] == 'INCOMPLETE_SESSIONS' and expected['mean_two_sessions'] is None
    assert len(effects) == 5 and len(support) == 110
    effect = float(np.mean(effects))
    null = [np.mean(np.array(effects) * signs) for signs in itertools.product((-1, 1), repeat=5)]
    pv = sum(abs(x) >= abs(effect) - 1e-12 for x in null) / 32
    close(p['test']['observed_mean'], effect)
    close(p['test']['p_two_sided'], pv)
    close(p['test']['p_bonferroni_two'], min(1, 2 * pv))
    primary.append(dict(metric=metric, participants=5, contributing_blocks=110,
                        participant_effects=effects, mean_paired_delta=effect,
                        p_two_sided=pv, p_adjusted=min(1, 2 * pv)))

db = sqlite3.connect(root / 'results/011/analysis.sqlite')
assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
assert db.execute('PRAGMA foreign_key_check').fetchall() == []
for table, count in summary['database']['row_counts'].items():
    assert table.replace('_', '').isalpha()
    assert db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == count
    checks += 1
db.close()
assert sha(root / 'results/011/analysis.sqlite') == summary['database']['sha256']
result = dict(schema='eegt-cross-encoder-independent-numerical-review/v1', status='PASS',
              utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), reviewer='root Astra; independent of Sol implementation',
              calculation='SciPy pdist/squareform and spearmanr; no study analysis imported',
              scalar_and_hash_checks=checks, maximum_scalar_error=max_error, primary=primary,
              summary_sha256=sha(root / 'results/011/summary.json'),
              source_sha256=sha(root / 'eegt/cross_encoder_study.py'),
              scope='All cross-model, within-model and descriptor block metrics, primary participant contrasts, output hashes and database; release review remains separate')
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
