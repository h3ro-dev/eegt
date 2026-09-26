"""Unbound, stale or source-only evidence must not authorize publication."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
spec = importlib.util.spec_from_file_location('package_events', Path(__file__).parents[1] / 'scripts/package_events.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class ReviewBoundary(unittest.TestCase):
    def test_review_requires_matching_independent_native_provenance(self):
        files = {'repo/note.md': dict(source_path='repo/note.md', bytes=9, sha256='a' * 64)}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reviewer = '01a0dc45-5aa8-7f21-9138-a2437735cd5c'
            def fixture(scope='FINAL_RELEASE', thread=reviewer, dispositions=None):
                evidence = dict(status='ACCEPTED', scope=scope, reviewer_thread_id=thread,
                                files_inventory_sha256=package.object_sha(files),
                                dispositions=dispositions if dispositions is not None else [dict(id='R1', status='RESOLVED')])
                (root / 'review.json').write_text(json.dumps(evidence))
                native = dict(thread_id=thread, turn_id='test-turn', turn_status='completed', observed_utc='2026-01-01T00:00:00Z',
                              review_artifact_sha256=package.digest(root / 'review.json'), native_source='synthetic test fixture')
                (root / 'native.json').write_text(json.dumps(native))
                return dict(status='ACCEPTED', files=files, reviewer_thread_id=thread,
                            review_artifact_path='review.json', review_artifact_sha256=package.digest(root / 'review.json'),
                            native_handoff_path='native.json', native_handoff_sha256=package.digest(root / 'native.json'))
            good = fixture()
            package.verify_review(root, files, good)
            for bad in [dict(status='ACCEPTED', files=files), {**good, 'files': {}},
                        {**good, 'review_artifact_sha256': 'b' * 64}, {**good, 'native_handoff_path': '../native.json'}]:
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    package.verify_review(root, files, bad)
            for options in [dict(scope='CODE_ONLY'), dict(thread='01a0d46f-1d63-72f3-95d0-692535ad6615'),
                            dict(dispositions=[]), dict(dispositions=[dict(id='R1', status='OPEN')])]:
                with self.subTest(options=options), self.assertRaises(ValueError):
                    package.verify_review(root, files, fixture(**options))

    def test_review_hash_covers_path_size_and_bytes(self):
        original = {'repo/a': dict(source_path='p/a', bytes=4, sha256='f' * 64)}
        for key, value in [('source_path', 'p/b'), ('bytes', 5), ('sha256', 'a' * 64)]:
            changed = copy.deepcopy(original)
            changed['repo/a'][key] = value
            self.assertNotEqual(package.object_sha(original), package.object_sha(changed))


if __name__ == '__main__':
    unittest.main()
