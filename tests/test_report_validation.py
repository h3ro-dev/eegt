"""A partial or wrongly bound run cannot be presented as Experiment013."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('report_validation',Path(__file__).resolve().parents[1]/'scripts/report_validation.py')
report=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(report)

class PresentationBoundary(unittest.TestCase):
    def fixture(self,root,status='COMPLETE_NUMERICAL_RECORD'):
        records=[dict(cohort=c,model=m,metric=k) for c in ('new_people','new_sessions') for m in ('codebrain','cbramod') for k in ('geometry','change')]
        data={'results/013/summary.json':{'status':status,'primary_endpoints':records},'results/013/prepared.json':{},'results/013/qualification.json':{},'results/013/engineering/summary.json':{'status':'COMPLETE_TECHNICAL_RECORD'},'protocol/experiment-013.json':{'primary_endpoints':records},'results/013/INPUT-ACCEPTANCE.json':{'status':'ACCEPTED'}}
        for name,value in data.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
        return root/'results/013/summary.json'

    def test_partial_execution_is_not_rendered(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);self.fixture(root,'PARTIAL_NUMERICAL_RECORD')
            with self.assertRaisesRegex(ValueError,'Complete primary'):report.render(root)
            self.assertFalse((root/'validation.html').exists())

    def test_duplicate_endpoint_cannot_replace_missing_family_member(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=self.fixture(root);s=json.loads(p.read_text());s['primary_endpoints'][-1]=s['primary_endpoints'][0];p.write_text(json.dumps(s))
            with self.assertRaisesRegex(ValueError,'endpoint identities'):report.render(root)
            self.assertFalse((root/'validation.html').exists())

    def test_changed_protocol_binding_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=self.fixture(root);s=json.loads(p.read_text());s.update(protocol_sha256='0'*64,input_acceptance_sha256='0'*64);p.write_text(json.dumps(s))
            with self.assertRaisesRegex(ValueError,'input bindings'):report.render(root)
            self.assertFalse((root/'validation.html').exists())

if __name__=='__main__':unittest.main()
