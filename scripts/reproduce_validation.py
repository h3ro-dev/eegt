#!/usr/bin/env python3
"""Bounded Experiment 013 validation runner and read-only exposed-012 parity."""
from __future__ import annotations

import os
for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eegt import validation_study as study  # noqa: E402


def preflight(root: Path) -> dict:
    """Read-only source check; this action makes no empirical call."""
    protocol_path = root / "protocol/experiment-013.json"
    source_path = root / "protocol/corpus-manifest-013.json"
    if not protocol_path.exists() or not source_path.exists():
        return dict(status="AWAITING_FINAL_PROTOCOL_AND_SOURCE", protocol_exists=protocol_path.exists(),
                    source_manifest_exists=source_path.exists(), empirical_call=False)
    protocol, source = study.read_json(protocol_path), study.read_json(source_path)
    records = study.verify_source(protocol, source)
    freeze_path = root / "results/013/RUN-SOURCE-MANIFEST.json"
    acceptance_path = root / "results/013/INPUT-ACCEPTANCE.json"
    result = dict(status="SOURCE_CENSUS_VERIFIED", source_records=len(records),
                  protocol_sha256=study.digest(protocol_path),
                  source_manifest_sha256=study.digest(source_path),
                  freeze_present=freeze_path.exists(), input_acceptance_present=acceptance_path.exists(),
                  empirical_call=False)
    if freeze_path.exists():
        study.require_accepted_freeze(root)
        result["freeze_status"] = "ACCEPTED_AND_HASH_VERIFIED"
    if acceptance_path.exists():
        freeze = study.require_accepted_freeze(root)
        study.require_input_acceptance(root, freeze)
        inputs = study.load_inputs(root)
        result.update(selected_blocks=len(inputs.selected), cohort_inference_gates=inputs.gates,
                      input_status="ACCEPTED_AND_NUMERICALLY_VERIFIED")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "infer", "events", "evaluate", "replay",
                                           "engineering", "exposed-parity"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--model", choices=study.MODELS)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--supplement", type=Path)
    parser.add_argument("--sqlite", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.action == "preflight":
            result = preflight(root)
        elif args.action == "exposed-parity":
            if args.supplement is None or args.sqlite is None:
                parser.error("exposed-parity requires --supplement and --sqlite")
            packet = root.parent
            result = study.verify_exposed_012(packet, args.supplement.resolve(), args.sqlite.resolve())
        elif args.action == "infer":
            if args.model is None:
                parser.error("infer requires --model")
            result = study.run_inference(root, args.model, resume=args.resume)
        elif args.action == "events":
            result = study.run_events(root, resume=args.resume)
        elif args.action == "engineering":
            result = study.run_engineering(root, resume=args.resume)
        elif args.action == "replay":
            result = study.replay_events(root)
        else:
            freeze = study.require_accepted_freeze(root, stage="events")
            study.require_input_acceptance(root, freeze)
            inputs = study.load_inputs(root)
            freeze_sha = study.digest(root / "results/013/RUN-SOURCE-MANIFEST.json")
            acceptance_sha = study.digest(root / "results/013/INPUT-ACCEPTANCE.json")
            db = study.open_index(root, inputs, freeze_sha, acceptance_sha)
            try:
                result = study.evaluate_index(root, inputs, db, freeze_sha, acceptance_sha)
                study.write_json(root / "results/013/summary.json", result)
            finally:
                db.close()
        print(study.canonical(result))
        return 0
    except Exception as error:
        failure = dict(schema="eegt-validation-failed-attempt/v1", action=args.action,
                       observed_utc=datetime.now(timezone.utc).isoformat(),
                       error_type=type(error).__name__, reason=str(error),
                       traceback=traceback.format_exc(),
                       freeze_sha256=study.digest(root / "results/013/RUN-SOURCE-MANIFEST.json")
                       if (root / "results/013/RUN-SOURCE-MANIFEST.json").exists() else None)
        if args.action not in ("preflight", "exposed-parity"):
            path = root / "results/013" / ("failed-attempt-" +
                datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
            study.write_json(path, failure, exclusive=True)
        print(json.dumps(failure, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
