"""Candidate verification adapter; independently review before an empirical replay.

Calls the unchanged frozen replay and numerical functions. Each payload is
decoded once during that replay, with index checks around the same read. The
final gate requires every payload and rechecks all compressed bytes.
"""
from pathlib import Path


class PartitionGate:
    def __init__(self, study, root, check_resources=lambda: None):
        self.study = study
        self.root = Path(root).resolve()
        self.original_read = study.read_partition
        self.inventory = None
        self.seen = set()
        self.calls = 0
        self.check_resources = check_resources

    def census(self, db):
        completed = {r[0] for r in db.execute('SELECT candidate_index FROM completed_blocks')}
        eligible = {r[0] for r in db.execute("SELECT candidate_index FROM candidates WHERE status='ELIGIBLE'")}
        if not completed or completed != eligible:
            raise ValueError('Full completed selected-block census required')
        expected = {(ci, branch, variant) for ci in completed
                    for branch, variants in (('native', self.study.NATIVE_VARIANTS),
                                             ('prepared', self.study.PREPARED_VARIANTS))
                    for variant in variants}
        rows = list(db.execute('SELECT candidate_index,branch,variant,path,sha256,bytes,header_json '
                               'FROM partitions ORDER BY candidate_index,branch,variant'))
        if len(rows) != len(expected) or {r[:3] for r in rows} != expected:
            raise ValueError('Partition inventory membership mismatch')
        inventory = {}
        for row in rows:
            ci, branch, variant, relative, *_ = row
            path = self.study._inside(self.root, relative).resolve()
            if path != self.study.partition_path(self.root, ci, branch, variant).resolve():
                raise ValueError('Partition path does not match its identity')
            if path in inventory:
                raise ValueError('Duplicate partition path')
            inventory[path] = row
        return inventory

    def check_bytes(self, path, row):
        if (not path.is_file() or path.stat().st_size != row[5]
                or self.study.digest(path) != row[4]):
            raise ValueError('Indexed partition bytes changed: ' + str(path))

    def verify(self, root, db):
        if Path(root).resolve() != self.root:
            raise ValueError('Replay root changed')
        self.calls += 1
        current = self.census(db)
        if self.calls == 1:
            self.inventory = current
        elif self.calls == 2:
            if current != self.inventory or self.seen != set(current):
                raise ValueError('Final inventory changed or payload validation incomplete')
            for path, row in current.items():
                self.check_bytes(path, row)
        else:
            raise ValueError('Unexpected partition verification call order')
        return len(current)

    def read(self, path):
        self.check_resources()
        path = Path(path).resolve()
        if self.calls != 1 or self.inventory is None or path not in self.inventory or path in self.seen:
            raise ValueError('Unexpected, repeated or unindexed payload read')
        row = self.inventory[path]
        self.check_bytes(path, row)
        # Frozen reader checks event count and canonical event content hash.
        header, result = self.original_read(path)
        if (self.study.canonical(header) != row[6]
                or (header['candidate_index'], header['branch'], header['variant']) != row[:3]):
            raise ValueError('Indexed partition header changed')
        self.seen.add(path)
        self.check_resources()
        return header, result


def replay(study, root, check_resources=lambda: None):
    root = Path(root).resolve()
    index = root / 'results/013/analysis.sqlite'
    before = study.digest(index)
    check_resources()
    gate = PartitionGate(study, root, check_resources)
    original_verify, original_read = study.verify_indexed_partitions, study.read_partition
    try:
        study.verify_indexed_partitions, study.read_partition = gate.verify, gate.read
        result = study.replay_events(root)
        if (gate.calls != 2 or gate.seen != set(gate.inventory or {})
                or result.get('full_scientific_summary') is not True
                or result.get('status') != 'REPLAYED_RECORDED_EVENTS'
                or result.get('partitions') != len(gate.seen)
                or result.get('detector_regenerated') is not False):
            raise ValueError('Full frozen replay result required')
        if study.digest(index) != before:
            raise ValueError('Replay changed the recorded SQLite index')
        check_resources()
        return dict(result, verification_adapter='single-payload-pass/v1',
                    decoded_partitions=len(gate.seen), final_compressed_bytes_rechecked=True)
    finally:
        study.verify_indexed_partitions, study.read_partition = original_verify, original_read


if __name__ == '__main__':
    import argparse
    import json
    import os
    import resource
    import sys
    import time
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.root.resolve()))
    from eegt import validation_study
    freeze = validation_study.require_accepted_freeze(args.root, stage='events')
    bounds = freeze['resource_bounds']
    old_limits = resource.getrlimit(resource.RLIMIT_CPU)
    limit = min([int(bounds['cpu_seconds'])] + [x for x in old_limits if x != resource.RLIM_INFINITY])
    resource.setrlimit(resource.RLIMIT_CPU, (limit, limit))

    def check_resources():
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform != 'darwin':
            rss *= 1024
        if time.process_time() > bounds['cpu_seconds'] or rss > bounds['rss_bytes']:
            raise RuntimeError('Fixed replay CPU/RSS bound exceeded')

    if validation_study._artifact_bytes(args.root) > bounds['artifact_bytes']:
        raise RuntimeError('Fixed artifact bound exceeded')
    result = replay(validation_study, args.root, check_resources)
    if validation_study._artifact_bytes(args.root) > bounds['artifact_bytes']:
        raise RuntimeError('Fixed artifact bound exceeded')
    print(json.dumps(result, sort_keys=True))
