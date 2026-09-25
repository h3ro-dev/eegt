"""Bind evaluation rows to the exact, completed preparation outputs."""
import json
from .acquire import digest


PREPARED_FILES = (
    "data/derived/analysis-waves.npz",
    "results/002/evaluation-index.npz",
    "results/002/windows.csv.gz",
    "results/002/provenance.json",
    "results/002/qc.json",
    "protocol/experiment-002.json",
    "protocol/source-manifest.json",
)
RECEIPT = "results/002/prepared-inputs.json"


def seal_prepared_inputs(root):
    """Called by preparation only, after every bound output is complete."""
    receipt = {"schema": "eegt-prepared-inputs/v1",
               "files": {name: digest(root / name) for name in PREPARED_FILES}}
    (root / RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n")


def verify_prepared_inputs(root):
    """Reject missing, mixed or modified artifacts before any fitting."""
    path = root / RECEIPT
    if not path.is_file():
        raise ValueError("prepared-input receipt missing; run preparation first")
    receipt = json.loads(path.read_text())
    hashes = receipt.get("files", {})
    if receipt.get("schema") != "eegt-prepared-inputs/v1" or set(hashes) != set(PREPARED_FILES):
        raise ValueError("prepared-input receipt has an unsupported file set or schema")
    for name in PREPARED_FILES:
        path = root / name
        if not path.is_file() or digest(path) != hashes[name]:
            raise ValueError(f"prepared input identity mismatch: {name}")
    return hashes
