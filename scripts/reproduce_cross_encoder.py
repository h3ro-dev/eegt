"""Run frozen Experiment 011 or reproduce its evaluation without model calls."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eegt import cross_encoder_study as study


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "freeze", "infer", "evaluate", "reproduce", "compare"))
    parser.add_argument("--packet-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    packet = args.packet_root.resolve()
    root = packet / "repo"
    if args.action == "compare":
        if args.output_dir is None:
            parser.error("compare needs --output-dir of a fresh offline reproduction")
        original = study.read(root / "results/011/summary.json")
        reproduced = study.read(args.output_dir / "summary.json")
        study.compare_science(original, reproduced)
        print(json.dumps({"status": "PASS", "scientific_tolerance": 1e-12,
                          "original": str(root / "results/011/summary.json"),
                          "reproduced": str(args.output_dir / "summary.json")}))
        return
    if args.action in ("preflight", "freeze", "infer"):
        inputs = study.validate_inputs(packet)
        if args.action == "preflight":
            print(json.dumps({"status": "READY", "selected_blocks": len(inputs["selected"]),
                              "codebrain_hash_pairs": len(inputs["old_run"]["measurements"]),
                              "protocol_sha256": study.PROTOCOL_SHA256}))
        elif args.action == "freeze":
            study.freeze_manifest(inputs)
            print(json.dumps({"status": "FROZEN", "path": str(root / "results/011/run-manifest.json")}))
        else:
            receipt = study.infer(inputs)
            print(json.dumps({"status": receipt["status"], "forwards": receipt["block_variant_runs"],
                              "array_sha256": receipt["array_sha256"]}))
    else:
        if args.action == "reproduce" and args.output_dir is None:
            parser.error("reproduce needs a fresh --output-dir")
        output = (args.output_dir if args.action == "reproduce" else root / "results/011")
        result = study.evaluate(packet, output)
        print(json.dumps({"status": result["status"], "output_dir": str(output),
                          "primary": [{"metric": r["metric"], "status": r["status"], "test": r["test"]}
                                      for r in result["primary"]]}))


if __name__ == "__main__":
    main()
