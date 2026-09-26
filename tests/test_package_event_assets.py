import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('event_assets', Path(__file__).resolve().parents[1] / 'scripts/package_event_assets.py')
assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assets)


class EventAssetTests(unittest.TestCase):
    def test_shards_roundtrip_repeatability_and_immutability(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            for i in range(5):
                (base / f'{i}.bin').write_bytes(bytes(range(256)) * 24)
            mapping = {f'repo/{i}.bin': f'{i}.bin' for i in range(5)}
            expected = assets.inventory(base, mapping)
            a = assets.write_assets(base, mapping, base / 'a', 'eegt-test', expected_files=expected, shard_bytes=20480)
            b = assets.write_assets(base, mapping, base / 'b', 'eegt-test', expected_files=expected, shard_bytes=20480)
            self.assertGreater(len(a['assets']), 1)
            self.assertEqual(a, b)
            all_members = [x for row in a['assets'].values() for x in row['members']]
            self.assertEqual(sorted(all_members), sorted(mapping))
            with self.assertRaises(FileExistsError):
                assets.write_assets(base, mapping, base / 'a', 'eegt-test', expected_files=expected, shard_bytes=20480)
            (base / '0.bin').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'accepted inventory'):
                assets.write_assets(base, mapping, base / 'c', 'eegt-test', expected_files=expected)

    def test_reject_unsafe_paths_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base / 'safe').write_bytes(b'x')
            (base / 'link').symlink_to(base / 'safe')
            for name, path in [('../escape', 'safe'), ('/absolute', 'safe'), ('repo/safe', '../safe'),
                               ('repo//safe', 'safe'), ('repo/safe', 'link'), ('FILE-MANIFEST.json', 'safe')]:
                with self.subTest(name=name, path=path), self.assertRaises(ValueError):
                    assets.inventory(base, {name: path})

    def test_long_names_and_oversized_member(self):
        files = {'repo/' + 'a' * 180 + '.gz': {'bytes': 5000, 'sha256': 'unused', 'source_path': 'unused'}}
        groups = assets.plan_shards(files, 300, shard_bytes=20480)
        self.assertEqual(len(groups), 1)
        files[next(iter(files))]['bytes'] = 50000
        with self.assertRaisesRegex(ValueError, 'single member'):
            assets.plan_shards(files, 300, shard_bytes=20480)


if __name__ == '__main__':
    unittest.main()
