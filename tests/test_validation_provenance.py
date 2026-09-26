"""Actual loader source bindings: equal copies allowed, shadowed bytes refused."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import sys
import types
from unittest.mock import patch
from eegt import validation_study as study
from eegt.validation_provenance import loaded_sources, verify_loaded_sources

class LoadedSourceTests(unittest.TestCase):
    def seal(self):
        return dict(inputs={name:hashlib.sha256(path.read_bytes()).hexdigest()
                            for name,path in loaded_sources().items()})

    def test_current_loaded_files_are_bound(self):
        verify_loaded_sources(self.seal())

    def test_different_executing_self_or_scientific_dependency_refused(self):
        seal=self.seal()
        with tempfile.TemporaryDirectory() as tmp:
            stale=Path(tmp)/'stale.py';stale.write_text('# different executable source\n')
            for module in (study, study.old, study.pretrained_study, study.wave):
                with self.subTest(module=module.__name__), patch.object(module,'__file__',str(stale)):
                    with self.assertRaisesRegex(ValueError,'loaded EEGT source differs'):
                        verify_loaded_sources(seal)

    def test_both_normal_cli_entrypoints_are_bound(self):
        for name in ('prepare_validation.py', 'reproduce_validation.py'):
            with self.subTest(script=name), tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/name;path.write_text('# canonical CLI fixture\n')
                seal=self.seal()
                seal['inputs']['scripts/'+name]=hashlib.sha256(path.read_bytes()).hexdigest()
                main=types.SimpleNamespace(__file__=str(path),__spec__=None)
                with patch.dict(sys.modules, {'__main__':main}):
                    verify_loaded_sources(seal)
                    path.write_text('# shadowed CLI fixture\n')
                    with self.assertRaisesRegex(ValueError,'loaded EEGT source differs'):
                        verify_loaded_sources(seal)

    def test_equal_source_copy_allowed_and_unbound_import_refused(self):
        seal=self.seal()
        with tempfile.TemporaryDirectory() as tmp:
            copy=Path(tmp)/'copy.py';copy.write_bytes(Path(study.__file__).read_bytes())
            with patch.object(study,'__file__',str(copy)):
                verify_loaded_sources(seal)
        seal['inputs'].pop('eegt/validation_study.py')
        with self.assertRaisesRegex(ValueError,'loaded EEGT source differs'):
            verify_loaded_sources(seal)

if __name__=='__main__':unittest.main()
