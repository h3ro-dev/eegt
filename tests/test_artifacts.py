import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from eegt import evaluate
from eegt.acquire import digest
from eegt.artifacts import PREPARED_FILES, RECEIPT, seal_prepared_inputs, verify_prepared_inputs


class ArtifactBindingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in PREPARED_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n")
        self.wave_path = self.root / "data/derived/analysis-waves.npz"
        self.index_path = self.root / "results/002/evaluation-index.npz"
        np.savez(self.wave_path, samples_uv=np.zeros((3, 200)), window_index=[4, 5, 8])
        self.index(window_index=[4, 5, 8], recording_index=[0, 1, 2], split=["train", "test", "external"])
        qc = {"qc_pass": 3, "protocol_sha256": digest(self.root / "protocol/experiment-002.json")}
        (self.root / "results/002/qc.json").write_text(json.dumps(qc))
        seal_prepared_inputs(self.root)

    def index(self, **arrays):
        np.savez(self.index_path, **arrays)

    def test_prepared_bundle_and_missing_receipt(self):
        self.assertEqual(set(verify_prepared_inputs(self.root)), set(PREPARED_FILES))
        (self.root / RECEIPT).unlink()
        with self.assertRaisesRegex(ValueError, "receipt missing"):
            verify_prepared_inputs(self.root)

    def test_same_length_row_permutation_rejected_before_fit(self):
        self.index(window_index=[8, 5, 4], recording_index=[2, 1, 0], split=["external", "test", "train"])
        with patch.object(evaluate, "ROOT", self.root), patch.object(evaluate.Tokenizer, "fit") as fit:
            with self.assertRaisesRegex(ValueError, "prepared input identity mismatch"):
                evaluate.run()
            fit.assert_not_called()

    def test_window_identity_checked_even_after_resealing(self):
        self.index(window_index=[8, 5, 4], recording_index=[2, 1, 0], split=["external", "test", "train"])
        seal_prepared_inputs(self.root)
        with patch.object(evaluate, "ROOT", self.root), patch.object(evaluate.Tokenizer, "fit") as fit:
            with self.assertRaisesRegex(ValueError, "window identity mismatch"):
                evaluate.run()
            fit.assert_not_called()

    def test_modified_waves_or_omitted_bound_file_rejected(self):
        np.savez(self.wave_path, samples_uv=np.ones((3, 200)), window_index=[4, 5, 8])
        with self.assertRaisesRegex(ValueError, "prepared input identity mismatch"):
            verify_prepared_inputs(self.root)
        seal_prepared_inputs(self.root)
        p = self.root / RECEIPT
        receipt = json.loads(p.read_text())
        del receipt["files"]["results/002/provenance.json"]
        p.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "unsupported file set"):
            verify_prepared_inputs(self.root)


if __name__ == "__main__":
    unittest.main()
