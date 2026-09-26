"""Experiment013 intake stages. Empirical actions require the accepted freeze.

Run qualification, quality and preparation in the corpus runtime. The exposed fixture commands may
read only the previously released 001/001 source and write a new scratch path.
"""

import os
for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eegt import validation_intake as intake


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "acquire", "qualify", "quality", "prepare",
                                            "verify", "exposed-corpus", "exposed-prepare"))
    parser.add_argument("--root", type=Path, default=intake.ROOT)
    parser.add_argument("--phase", choices=("corpus", "encoder", "events"), default="corpus")
    parser.add_argument("--output", type=Path, help="new scratch directory for exposed fixture")
    args = parser.parse_args(argv)
    if args.action.startswith("exposed-"):
        if args.output is None:
            parser.error("exposed fixture requires --output to a new scratch directory")
        result = (intake.exposed_corpus_fixture(args.root, args.output) if
                  args.action == "exposed-corpus" else
                  intake.exposed_prepare_fixture(args.root, args.output))
    elif args.action == "preflight":
        seal, _, _ = intake.require_accepted_freeze(args.root, args.phase)
        result = {"status": seal["status"], "phase": args.phase,
                  "frozen_inputs": len(seal["inputs"])}
    elif args.action == "acquire":
        result = intake.acquire_sources(args.root)
    elif args.action == "qualify":
        result = intake.qualify_sources(args.root)
    elif args.action == "quality":
        result = intake.build_quality_census(args.root)
    elif args.action == "prepare":
        result = intake.prepare_validation(args.root)
    else:
        _, protocol, source = intake.require_accepted_freeze(args.root, "corpus")
        receipt = intake.read(args.root / "results/013/prepared.json")
        gates = intake.validate_prepared(args.root, receipt, protocol, source)
        result = {"status": "VERIFIED", "inference_gates": gates}
    print(json.dumps({k: v for k, v in result.items()
                      if k in ("schema", "status", "phase", "frozen_inputs", "totals",
                               "inference_gates", "candidate_rows", "selected_rows",
                               "baseline_masks_equal", "selected_prepared_bytes_equal")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
