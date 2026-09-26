"""Synthetic checks for the intake first-record and resource admission gate."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import numpy as np
from eegt import validation_intake as intake
from eegt import validation_study
from eegt.validation_provenance import loaded_sources

class ResourceAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.seal = {"resource_bounds":dict(cpu_seconds=7200, rss_bytes=2147483648,
                    artifact_bytes=10000000000, first_block_required=True)}
        self.seal["inputs"] = {name:intake.digest(path) for name,path in loaded_sources().items()}
        freeze=self.root / intake.FREEZE_PATH
        freeze.parent.mkdir(parents=True)
        freeze.write_text(json.dumps(self.seal))

    def test_first_record_stops_then_requires_hash_bound_admission(self):
        guard=intake.IntakeResources(self.root,self.seal,"quality")
        with self.assertRaisesRegex(RuntimeError,"first-record review required"):
            guard.after_record(0,"record-001")
        with self.assertRaises(FileNotFoundError):
            intake.IntakeResources(self.root,self.seal,"quality")
        review=dict(schema="eegt-validation-first-block-review/v1",status="ADMITTED",
            phase=guard.phase,profile_sha256=intake.digest(guard.profile),
            run_manifest_sha256=intake.digest(self.root/intake.FREEZE_PATH),
            resource_bounds=self.seal["resource_bounds"],admitted_by="synthetic-test")
        path=self.root/f"results/013/first-block-review-{guard.phase}.json"
        path.write_text(json.dumps(review))
        guard2=intake.IntakeResources(self.root,self.seal,"quality")
        guard2.after_record(0,"record-001")
        guard.profile.write_text("tampered")
        with self.assertRaisesRegex(ValueError,"missing or stale"):
            intake.IntakeResources(self.root,self.seal,"quality")

    def test_each_bound_refuses_before_work(self):
        base=dict(cpu_seconds=1,wall_seconds=1,process_peak_rss_bytes=100,artifact_bytes=100)
        for key,value in (("cpu_seconds",7201),("process_peak_rss_bytes",2147483649),
                          ("artifact_bytes",10000000001)):
            with self.subTest(bound=key), patch("eegt.validation_study._resource_snapshot",
                    return_value={**base,key:value}):
                with self.assertRaisesRegex(RuntimeError,"bound exceeded"):
                    intake.IntakeResources(self.root,self.seal,"quality")

    def test_archive_replay_requires_identical_arrays_and_preserves_bytes(self):
        path=self.root/"example.npz"
        values=np.array([1.,float("nan")])
        intake._save_numeric(path,samples=values)
        before=path.read_bytes()
        intake._save_numeric(path,samples=values)
        self.assertEqual(before,path.read_bytes())
        with self.assertRaises(FileExistsError):
            intake._save_numeric(path,samples=np.array([2.,float("nan")]))
        self.assertEqual(before,path.read_bytes())

if __name__=="__main__": unittest.main()
