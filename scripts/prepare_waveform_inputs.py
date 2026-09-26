"""Extract only the previously selected Experiment010 native windows, without analysis."""
import argparse
import hashlib
import json
import resource
import time
from datetime import datetime, timezone
from pathlib import Path

import mne
import numpy as np


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def array_digest(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def prepare(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError("preserve existing input preparation; use a fresh directory")
    protocol = json.loads((root / "protocol/experiment-011.json").read_text())
    prepared_path = root / "results/010/prepared.json"
    if digest(prepared_path) != protocol["inputs"]["results/010/prepared.json"]:
        raise ValueError("Experiment010 selection receipt changed")
    previous = json.loads(prepared_path.read_text())
    p010 = json.loads((root / "protocol/experiment-010.json").read_text())
    qualification_path = root / p010["source"]["qualification"]
    if digest(qualification_path) != p010["source"]["qualification_sha256"]:
        raise ValueError("source qualification changed")
    qualified = {r["recording_id"]: r for r in json.loads(qualification_path.read_text())["records"]}
    chosen = sorted((r for r in previous["records"] if r["status"] == "ELIGIBLE"),
                    key=lambda r: r["array_row"])
    if len(chosen) != 122 or [r["array_row"] for r in chosen] != list(range(122)):
        raise ValueError("selected input order changed")
    channels = ["RB", "RT", "LB", "LT"]
    waves = np.empty((122, 4, 7500), dtype=np.float64)
    masks = np.zeros(waves.shape, dtype=bool)
    curator = []
    started = time.monotonic()
    for rid in dict.fromkeys(r["recording_id"] for r in chosen):
        record = qualified[rid]
        if (record["status"] != "QUALIFIED" or record["channels"] != channels or
                record["sample_rate_hz"] != 250 or record["source_subject"] not in p010["source"]["subjects"] or
                record["session"] not in p010["source"]["sessions"]):
            raise ValueError("source is outside the exposed qualified contract")
        path = root / record["path"]
        sha = digest(path)
        if sha != record["sha256"] or previous["source_hashes"][record["path"]] != sha:
            raise ValueError("source byte identity changed")
        raw = mne.io.read_raw_eeglab(path, preload=False, verbose="ERROR")
        try:
            if raw.info["sfreq"] != 250 or any(c not in raw.ch_names for c in channels):
                raise ValueError("decoded channel/rate mismatch")
            for row in (r for r in chosen if r["recording_id"] == rid):
                start = int(row["start_seconds"] * 250)
                end = start + 7500
                if start < 0 or end > 3600000 or row["duration_seconds"] != 30:
                    raise ValueError("attempted extraction outside the exposed four-hour interval")
                if any(g["start_seconds"] < end / 250 and g["stop_seconds"] > start / 250
                       for g in record.get("gaps", [])):
                    raise ValueError("selected block unexpectedly overlaps a native gap")
                wave = raw.get_data(picks=channels, start=start, stop=end) * 1e6
                if wave.shape != (4, 7500) or not np.isfinite(wave).all():
                    raise ValueError("selected finite-sample contract changed")
                index = row["array_row"]
                waves[index], masks[index] = wave, np.isfinite(wave)
                curator.append({**row, "source_path": record["path"], "source_sha256": sha,
                                "channels": channels, "native_start_sample": start,
                                "native_end_sample_exclusive": end, "native_sample_rate_hz": 250,
                                "native_array_sha256": array_digest(wave),
                                "valid_mask_sha256": array_digest(masks[index]),
                                "source_gaps": record.get("gaps", []),
                                "sample_mask_rule": "finite native samples; selected010 rows have no native gaps and passed frozen whole-block/baseline QC"})
        finally:
            raw.close()
        print(f"extracted selected intervals from {rid}", flush=True)
    output.mkdir(parents=True)
    destination = output / "native-selected.npz"
    np.savez_compressed(destination, samples_uv=waves, valid=masks,
                        sample_rate_hz=np.array(250.0))
    receipt = {"schema": "eegt-selected-native-input/v1", "created_utc": datetime.now(timezone.utc).isoformat(),
               "scope": "input extraction only; no direct-event analysis or new exposure",
               "input_sha256": {"results/010/prepared.json": digest(prepared_path),
                                p010["source"]["qualification"]: digest(qualification_path)},
               "array_path": destination.name, "array_sha256": digest(destination),
               "array_shape": list(waves.shape), "units": "microvolt",
               "conversion": "MNE decoded numeric volts multiplied by1e6; no filter/resample/rereference",
               "physical_calibration": "Independent hardware calibration UNKNOWN",
               "discovery_contract": "NPZ numeric arrays only; this curator receipt is joined only for provenance/evaluation",
               "records": sorted(curator, key=lambda r: r["array_row"]),
               "runtime_seconds": time.monotonic() - started,
               "max_rss_native": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               "versions": {"mne": mne.__version__, "numpy": np.__version__}}
    (output / "native-selected-curator.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.root, args.output)
    print(json.dumps({k: result[k] for k in ("array_sha256", "array_shape", "runtime_seconds", "max_rss_native")}))
