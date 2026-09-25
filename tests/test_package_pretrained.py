import tempfile
import unittest
from pathlib import Path

from eegt.acquire import digest
from scripts.package_pretrained import MODEL_SOURCES, REVIEW_INPUTS, verify_code_and_review


class ReleaseBindingTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        for name in REVIEW_INPUTS:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(name+'\n')
        self.inference={'code_sha256':{p:digest(self.root/p) for p in MODEL_SOURCES}}
        self.review={'status':'ACCEPTED','input_hashes':{'snapshot_files_sha256':{p:digest(self.root/p) for p in REVIEW_INPUTS}}}

    def test_exact_binding_and_changed_model(self):
        self.assertEqual(set(verify_code_and_review(self.root,self.inference,self.review)),REVIEW_INPUTS)
        (self.root/'eegt/pretrained.py').write_text('changed adapter\n')
        with self.assertRaisesRegex(ValueError,'inference source changed'):
            verify_code_and_review(self.root,self.inference,self.review)

    def test_changed_reviewed_document(self):
        (self.root/'README.md').write_text('changed claims\n')
        with self.assertRaisesRegex(ValueError,'reviewed input changed'):
            verify_code_and_review(self.root,self.inference,self.review)

    def test_incomplete_or_unaccepted_review_is_not_a_gate(self):
        del self.review['input_hashes']['snapshot_files_sha256']['eegt/pretrained.py']
        with self.assertRaisesRegex(ValueError,'review input binding missing'):
            verify_code_and_review(self.root,self.inference,self.review)

        self.review['status']='CHANGES_REQUIRED'
        with self.assertRaisesRegex(ValueError,'has not accepted'):
            verify_code_and_review(self.root,self.inference,self.review)

    def test_distributed_release_requires_new_sampler_and_review(self):
        required={p.replace('009','010').replace('report_pretrained.py','report_distributed.py') for p in REVIEW_INPUTS}
        required|={'eegt/distributed_study.py','scripts/package_distributed.py'}
        for name in required:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(name+'\n')
        code=MODEL_SOURCES|{'eegt/distributed_study.py'}
        inference={'code_sha256':{p:digest(self.root/p) for p in code}}
        review={'status':'ACCEPTED','input_hashes':{'snapshot_files_sha256':{p:digest(self.root/p) for p in required}}}
        verify_code_and_review(self.root,inference,review,'010')
        del inference['code_sha256']['eegt/distributed_study.py']
        with self.assertRaisesRegex(ValueError,'inference source binding missing'):
            verify_code_and_review(self.root,inference,review,'010')


if __name__=='__main__':unittest.main()
