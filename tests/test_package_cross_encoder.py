"""Consequential release guards: a draft review and changed bytes must fail."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('package_cross_encoder', Path(__file__).resolve().parents[1] / 'scripts/package_cross_encoder.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


def test_release_requires_accepted_exact_source_and_data(tmp_path):
    (tmp_path / 'code.py').write_text('version = 1\n')
    (tmp_path / 'data.bin').write_bytes(b'frozen data')
    mapping = {'repo/code.py': 'code.py', 'repo/data.bin': 'data.bin'}
    h = package.hashes(tmp_path, mapping)
    with pytest.raises(ValueError, match='not accepted'):
        package.verify_review(tmp_path, mapping, {'status': 'DRAFT', 'files_sha256': h})
    accepted = {'status': 'ACCEPTED', 'files_sha256': h}
    package.verify_review(tmp_path, mapping, accepted)
    (tmp_path / 'data.bin').write_bytes(b'changed data')
    with pytest.raises(ValueError, match='changed'):
        package.verify_review(tmp_path, mapping, accepted)
    (tmp_path / 'data.bin').write_bytes(b'frozen data')
    (tmp_path / 'code.py').write_text('version = 2\n')
    with pytest.raises(ValueError, match='changed'):
        package.verify_review(tmp_path, mapping, accepted)


def test_release_refuses_missing_reviewed_member(tmp_path):
    (tmp_path / 'data.bin').write_bytes(b'frozen data')
    mapping = {'repo/data.bin': 'data.bin'}
    with pytest.raises(ValueError, match='changed'):
        package.verify_review(tmp_path, mapping, {'status': 'ACCEPTED', 'files_sha256': {}})
