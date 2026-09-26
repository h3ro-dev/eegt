"""A stale or unaccepted review must never authorize a release."""
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
spec = importlib.util.spec_from_file_location('package_events', Path(__file__).parents[1] / 'scripts/package_events.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class ReviewBoundary(unittest.TestCase):
    def test_hash_path_size_and_status_drift_fail_closed(self):
        files = {'repo/note.md': dict(source_path='repo/note.md', bytes=9, sha256='a' * 64)}
        package.verify_review(files, dict(status='ACCEPTED', files=files))
        for changed in [dict(status='PENDING', files=files), dict(status='ACCEPTED', files={}),
                        dict(status='ACCEPTED', files={'repo/note.md': dict(source_path='repo/note.md', bytes=9, sha256='b' * 64)}),
                        dict(status='ACCEPTED', files={'repo/note.md': dict(source_path='wrong.md', bytes=9, sha256='a' * 64)}),
                        dict(status='ACCEPTED', files={'repo/note.md': dict(source_path='repo/note.md', bytes=10, sha256='a' * 64)})]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                package.verify_review(files, changed)


if __name__ == '__main__':
    unittest.main()
