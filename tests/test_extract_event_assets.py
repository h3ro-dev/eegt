"""A complete valid shard set extracts; malformed downloaded payloads do not."""
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from package_event_assets import inventory, write_assets, digest
from extract_event_assets import extract, safe_name


class ExtractionBoundary(unittest.TestCase):
    def test_paths_are_safe_on_posix_and_windows(self):
        for name in ('C:/escape.txt', 'D:relative.txt', 'repo/a:b', '//server/share/a',
                     'repo/.. /escape', 'repo/file.', 'repo/NUL', '../escape', '/escape'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_name(name)
        safe_name('repo/results/012/summary.json')

    def fixture(self, root):
        (root / 'source').mkdir()
        (root / 'source/a.py').write_text('print(1)\n')
        (root / 'source/b.bin').write_bytes(bytes(range(256)) * 40)
        mapping = {'repo/a.py': 'source/a.py', 'repo/b.bin': 'source/b.bin'}
        result = write_assets(root, mapping, root / 'assets', 'sample', expected_files=inventory(root, mapping), shard_bytes=20480)
        manifest = root / 'manifest.json'
        manifest.write_text(json.dumps(result))
        return manifest, result, sorted((root / 'assets').glob('*.tar.gz'))

    def test_complete_tree_and_refusal_to_reuse_destination(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            manifest, result, assets = self.fixture(root)
            receipt = extract(manifest, assets, root / 'out', root / 'receipt.json')
            self.assertEqual(set(receipt['files']), {'repo/a.py', 'repo/b.bin'})
            self.assertEqual((root / 'out/repo/b.bin').read_bytes(), (root / 'source/b.bin').read_bytes())
            (root / 'out/extra.py').write_text('unlisted')
            with self.assertRaises(ValueError):
                extract(manifest, assets, root / 'out', root / 'second.json')

    def test_missing_shards_and_corrupt_asset_refused_before_extraction(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            manifest, result, assets = self.fixture(root)
            with self.assertRaises(ValueError):
                extract(manifest, assets[:-1], root / 'out', root / 'receipt.json')
            with assets[0].open('ab') as f:
                f.write(b'changed')
            with self.assertRaises(ValueError):
                extract(manifest, assets, root / 'out', root / 'receipt.json')
            self.assertFalse((root / 'out').exists())

    def test_unlisted_and_link_members_refused_even_with_updated_asset_hash(self):
        for kind in ('unlisted', 'link'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as t:
                root = Path(t)
                manifest, result, assets = self.fixture(root)
                asset = assets[0]
                with tarfile.open(asset, 'r:gz') as f:
                    members = [(m, f.extractfile(m).read()) for m in f.getmembers()]
                with tarfile.open(asset, 'w:gz') as f:
                    for member, body in members:
                        if kind == 'link' and member.name != 'FILE-MANIFEST.json':
                            member.type = tarfile.SYMTYPE
                            member.linkname = '/tmp/outside'
                            member.size = 0
                            f.addfile(member)
                        else:
                            f.addfile(member, io.BytesIO(body))
                    if kind == 'unlisted':
                        member = tarfile.TarInfo('repo/extra.py')
                        member.size = 1
                        f.addfile(member, io.BytesIO(b'x'))
                result['assets'][asset.name].update(bytes=asset.stat().st_size, sha256=digest(asset))
                manifest.write_text(json.dumps(result))
                with self.assertRaises(ValueError):
                    extract(manifest, assets, root / 'out', root / 'receipt.json')
                self.assertFalse((root / 'out').exists())


if __name__ == '__main__':
    unittest.main()
