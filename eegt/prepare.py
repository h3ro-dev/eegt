"""Acquisition steward: decode verified public sources; discard context at boundary."""
import csv
import gzip
import io
import json
import warnings
from collections import Counter
import mne
import numpy as np
from .acquire import ROOT, digest
from .artifacts import seal_prepared_inputs
from .contract import NumericRecording
from .signal import iter_windows


def prepare():
    protocol_path = ROOT / "protocol/experiment-002.json"
    p = json.loads(protocol_path.read_text())
    manifest = json.loads((ROOT / "protocol/source-manifest.json").read_text())
    if manifest["protocol_sha256"] != digest(protocol_path):
        raise ValueError("protocol changed since acquisition was frozen")
    out = ROOT / "results/002"
    derived = ROOT / "data/derived"
    out.mkdir(parents=True, exist_ok=True)
    derived.mkdir(parents=True, exist_ok=True)
    qc_rows, summaries, provenance, waves, accepted_indices = [], [], [], [], []
    record_indices, splits, native_arrays = [], [], {}
    for ri, record in enumerate(manifest["recordings"]):
        for file in record["files"]:
            path = ROOT / "data/cache" / record["dataset"] / file["path"]
            if path.stat().st_size != file["bytes"] or digest(path, file["algorithm"]) != file["expected_digest"]:
                raise ValueError("source bytes differ from pinned manifest")
        source = ROOT / "data/cache" / record["dataset"] / record["files"][0]["path"]
        channel_rows = list(csv.DictReader(io.StringIO(record["channels_tsv"].replace("\r\r\n", "\n")), delimiter="\t"))
        channels = [r["name"] for r in channel_rows if r.get("type") == "EEG"]
        if len(set(channels)) != len(channels) or not channels:
            raise ValueError("missing or duplicate declared EEG channel")
        if any(r["units"] not in ["microV", "uV", "µV"] for r in channel_rows if r.get("type") == "EEG"):
            raise ValueError("EEGLAB source must explicitly declare microvolt EEG units")
        with warnings.catch_warnings(record=True) as caught:
            raw = mne.io.read_raw_eeglab(source, preload=False, verbose="ERROR")
        md = record["metadata"]
        rate = float(raw.info["sfreq"])
        if rate != md["SamplingFrequency"] or len(channels) != md["EEGChannelCount"]:
            raise ValueError("declared/observed sampling or EEG channel count mismatch")
        if any(c not in raw.ch_names for c in channels) or len(set(raw.ch_names)) != len(raw.ch_names):
            raise ValueError("EEGLAB and channel table disagree")
        duration_error_samples = raw.n_times - md["RecordingDuration"] * rate
        if abs(duration_error_samples) > 1.01:
            raise ValueError("source duration mismatch exceeds one sample endpoint convention")
        start = round(p["slice_start_seconds"] * rate)
        stop = start + round(p["slice_duration_seconds"] * rate)
        if stop > raw.n_times:
            raise ValueError("fixed slice not available; do not select another segment silently")
        # MNE converts the documented EEGLAB microvolts to SI volts. Return to uV once.
        x = raw.get_data(picks=channels, start=start, stop=stop) * 1e6
        raw_count = int(raw.n_times)
        raw.close()
        numeric = NumericRecording.from_payload(dict(samples_uv=x, sample_rate_hz=rate,
                                                     valid_samples=np.isfinite(x)))
        native_arrays[f"samples_{ri}"] = x.astype("float32")
        native_arrays[f"rate_{ri}"] = np.array(rate)
        native_arrays[f"valid_{ri}"] = np.isfinite(x)
        counts, reasons = Counter(), Counter()
        for ci, offset, why, line_ratio, wave in iter_windows(numeric, p):
            index = len(qc_rows)
            counts["total"] += 1
            passed = wave is not None
            counts["pass" if passed else "abstain"] += 1
            reasons.update(why)
            qc_rows.append(dict(window_index=index, recording_index=ri, channel_index=ci,
                                native_start_sample=start + offset, sample_rate_hz=rate,
                                qc="PASS" if passed else "ABSTAIN", reasons="|".join(why),
                                line_ratio="" if line_ratio is None else line_ratio))
            if passed:
                accepted_indices.append(index)
                waves.append(wave.astype("float32"))
                record_indices.append(ri)
                splits.append(record["split"])
        summaries.append(dict(recording=record["recording"], recording_index=ri, split=record["split"],
                              native_sample_rate_hz=rate, eeg_channels=len(channels),
                              native_total_samples_per_channel=raw_count,
                              slice_samples_per_channel=stop - start,
                              duration_endpoint_difference_samples=float(duration_error_samples),
                              total_windows=counts["total"], qc_pass=counts["pass"], qc_abstain=counts["abstain"],
                              reasons=dict(reasons), adc_clipping_status="UNKNOWN_RAILS",
                              decoder_warnings=[str(w.message) for w in caught]))
        provenance.append(dict(recording_index=ri, recording=record["recording"], dataset=record["dataset"],
                               public_subject=record["subject"], split=record["split"],
                               ordered_eeg_channels=channels, source_reference=md.get("EEGReference"),
                               source_raw_channels=[r["name"] for r in channel_rows],
                               source_units="microvolts", source_git_commit=record["git_commit"],
                               source_set_path=record["files"][0]["path"]))
        print(json.dumps(summaries[-1]), flush=True)
    if not waves:
        raise ValueError("all selected windows abstained; preserve QC before planning next experiment")
    with gzip.open(out / "windows.csv.gz", "wt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(qc_rows[0]))
        writer.writeheader(); writer.writerows(qc_rows)
    # Array file has no source/identity labels. External table supplies evaluation grouping.
    np.savez_compressed(derived / "analysis-waves.npz", samples_uv=np.stack(waves),
                        window_index=np.array(accepted_indices, dtype="int64"), sample_rate_hz=np.array(100))
    np.savez_compressed(derived / "native-slices.npz", **native_arrays)
    np.savez_compressed(out / "evaluation-index.npz", window_index=np.array(accepted_indices, dtype="int64"),
                        recording_index=np.array(record_indices, dtype="int16"),
                        split=np.array(splits))
    (out / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (out / "qc.json").write_text(json.dumps(dict(schema="eegt-qc/v2", records=summaries,
        total_windows=len(qc_rows), qc_pass=len(waves), qc_abstain=len(qc_rows) - len(waves),
        protocol_sha256=digest(protocol_path)), indent=2) + "\n")
    seal_prepared_inputs(ROOT)


if __name__ == "__main__":
    prepare()
