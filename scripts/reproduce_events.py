"""Freeze, execute and reproduce the bounded Experiment 012 event study."""
from __future__ import annotations

import os
for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import argparse
from datetime import datetime, timezone
import gzip
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import sqlite3
import sys
import time
import traceback

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT.parent
sys.path.insert(0, str(ROOT))
from eegt import event_study as study, pretrained_study, waveform_events as wave  # noqa: E402

OUT = ROOT / "results/012"
EVENTS = ROOT / "data/derived/012/events"
MANIFEST = OUT / "RUN-SOURCE-MANIFEST.json"
DB = OUT / "analysis.sqlite"
PROGRESS = OUT / "run-progress.json"
SOURCE_PATHS = (
    "eegt/event_study.py", "scripts/reproduce_events.py", "tests/test_event_study.py",
    "eegt/waveform_events.py", "eegt/transitions.py", "eegt/pretrained_study.py",
    "eegt/acquire.py", "eegt/__init__.py", "requirements-events.lock", "pyproject.toml",
)
INPUT_PATHS = study.ROOT_INPUTS
CEILINGS = dict(rss_bytes=2147483648, artifact_bytes=3000000000, cpu_seconds=7200.)


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        handle.write(study.canonical(value) + "\n")
    return path


def write_derived(path, value):
    """Replace a derived report only; immutable manifests and partitions use x."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".partial")
    temp.write_text(study.canonical(value) + "\n")
    temp.replace(path)


def file_entry(path, relative_to):
    return dict(path=str(path.relative_to(relative_to)), bytes=path.stat().st_size,
                sha256=study.digest(path))


def runtime():
    versions = {name: importlib.metadata.version(name) for name in
                ("numpy", "scipy", "bycycle", "neurodsp", "pandas")}
    if versions["numpy"] != "1.26.4" or versions["scipy"] != "1.14.1":
        raise ValueError("pinned numerical runtime mismatch")
    python = Path(sys.executable).resolve()
    return dict(python=sys.version, python_major_minor=list(sys.version_info[:2]),
                executable=str(python), executable_sha256=study.digest(python),
                platform=platform.platform(), packages=versions,
                threads={name: os.environ[name] for name in
                         ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                          "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")})


def freeze():
    if MANIFEST.exists():
        raise FileExistsError("run source freeze already exists; preserve it")
    inputs = study.verify_arrays(PACKET)
    source_files = {name: file_entry(ROOT / name, ROOT) for name in SOURCE_PATHS}
    input_files = {name: file_entry(ROOT / name, ROOT) for name in INPUT_PATHS}
    input_files["SOURCE-MANIFEST.json"] = file_entry(PACKET / "SOURCE-MANIFEST.json", PACKET)
    input_files["input/synthetic-validation.json"] = file_entry(PACKET / "input/synthetic-validation.json", PACKET)
    manifest = dict(schema="eegt-012-run-source-manifest/v1", status="FROZEN_BEFORE_EMPIRICAL_EVENT_CALL",
                    frozen_utc=now(), work_id="eco-uzwh8s.34.2",
                    wrapper_sha256="60f02a8dce9a086be3a89fe612eb9437088054f007d14348c827292fae34e138",
                    method_sha256="86f41254f1fc35a0d95e4e9aab45bec0e12d1964ec18d8a38a7d92c57daf92e9",
                    inherited_files_verified=len(inputs["source"]["files"]),
                    native_rows_verified=122, prepared_variant_hashes_verified=inputs["verified_prepared_pairs"],
                    inference_output_hashes_verified=inputs["verified_inference_outputs"],
                    source_files=source_files, input_files=input_files, runtime=runtime(),
                    first_array_row=0, first_candidate_index=62, ceilings=CEILINGS)
    write_new(MANIFEST, manifest)
    MANIFEST.chmod(0o444)
    print(study.canonical(dict(status="FROZEN", manifest=str(MANIFEST), sha256=study.digest(MANIFEST))))


def verify_freeze():
    manifest = study.read_json(MANIFEST)
    if manifest["schema"] != "eegt-012-run-source-manifest/v1" or manifest["status"] != "FROZEN_BEFORE_EMPIRICAL_EVENT_CALL":
        raise ValueError("run source manifest invalid")
    for name, record in manifest["source_files"].items():
        path = ROOT / name
        if file_entry(path, ROOT) != record:
            raise ValueError(f"post-freeze source amendment required: {name}")
    for name, record in manifest["input_files"].items():
        path = PACKET / name if name.startswith("input/") or name == "SOURCE-MANIFEST.json" else ROOT / name
        parent = PACKET if path == PACKET / name else ROOT
        if file_entry(path, parent) != record:
            raise ValueError(f"frozen input changed: {name}")
    current = runtime()
    if (current["packages"] != manifest["runtime"]["packages"] or
        current["python_major_minor"] != manifest["runtime"]["python_major_minor"]):
        raise ValueError("pinned scientific runtime versions changed")
    return manifest


def partition_path(row, branch, variant):
    return EVENTS / f"row-{row:03d}" / f"{branch}-{variant}.jsonl.gz"


def write_partition(path, header, rows):
    if path.exists():
        raise FileExistsError(f"preserve completed observation: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".jsonl.gz.partial")
    if temp.exists():
        raise FileExistsError(f"preserve failed partial observation: {temp}")
    with temp.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz:
            gz.write((study.canonical({"type": "header", "value": header})+"\n").encode())
            for row in rows:
                gz.write((study.canonical({"type": "event", "value": row})+"\n").encode())
    temp.rename(path)


def read_partition(path):
    with gzip.open(path, "rt") as handle:
        first = json.loads(next(handle))
        if first["type"] != "header":
            raise ValueError("partition header missing")
        rows = []
        for line in handle:
            item = json.loads(line)
            if item["type"] != "event":
                raise ValueError("partition event record mismatch")
            rows.append(item["value"])
    header = first["value"]
    if len(rows) != header["event_rows"]:
        raise ValueError("partition event count mismatch")
    return header, rows


def saved_result(row, branch, name, x, mask, config, transform, *, full=False):
    path = partition_path(row, branch, name)
    if path.exists():
        header, rows = read_partition(path)
        if (header["array_sha256"] != pretrained_study.array_hash(x) or
            header["mask_sha256"] != study.array_digest(mask) or
            header["run_manifest_sha256"] != study.digest(MANIFEST)):
            raise ValueError(f"existing partition input/freeze mismatch: {path}")
        result = dict(header["result"], events=rows)
    else:
        result = wave.discover(x, 250 if branch == "native" else 200, mask,
                               [(0, x.shape[1], 0.)], include_cycles=full,
                               include_envelopes=full, **config)
        header = dict(schema="eegt-012-event-partition/v1", array_row=row, branch=branch, variant=name,
                      run_manifest_sha256=study.digest(MANIFEST), array_sha256=pretrained_study.array_hash(x),
                      mask_sha256=study.array_digest(mask), transform=transform,
                      event_rows=len(result["events"]), accepted_rows=sum(r["accepted"] for r in result["events"]),
                      rejected_rows=sum(not r["accepted"] for r in result["events"]),
                      result={k: v for k, v in result.items() if k != "events"})
        write_partition(path, header, result["events"])
    return path, header, result


def open_index(inputs):
    first = not DB.exists()
    db = sqlite3.connect(DB)
    db.execute("PRAGMA journal_mode=DELETE")
    if first:
        db.executescript("""
        CREATE TABLE candidates(candidate_index INTEGER PRIMARY KEY,array_row INTEGER,status TEXT,
          reasons_json TEXT,curator_json TEXT);
        CREATE TABLE partitions(array_row INTEGER,branch TEXT,variant TEXT,path TEXT,sha256 TEXT,bytes INTEGER,
          event_rows INTEGER,accepted_rows INTEGER,rejected_rows INTEGER,header_json TEXT,
          PRIMARY KEY(array_row,branch,variant));
        CREATE TABLE native_timeline(array_row INTEGER,variant TEXT,channel INTEGER,receipt_json TEXT,
          PRIMARY KEY(array_row,variant,channel));
        CREATE TABLE native_match(array_row INTEGER,variant TEXT,channel INTEGER,family TEXT,polarity TEXT,
          direction TEXT,tolerance_seconds REAL,receipt_json TEXT,
          PRIMARY KEY(array_row,variant,channel,family,polarity,direction,tolerance_seconds));
        CREATE TABLE prepared_metric(array_row INTEGER,variant TEXT,model TEXT,metric TEXT,receipt_json TEXT,
          PRIMARY KEY(array_row,variant,model,metric));
        CREATE TABLE block_effect(array_row INTEGER,candidate_index INTEGER,model TEXT,metric TEXT,
          effect REAL,reason TEXT,receipt_json TEXT,PRIMARY KEY(array_row,model,metric));
        CREATE TABLE morphology_block(array_row INTEGER,channel INTEGER,family TEXT,band TEXT,definition TEXT,
          receipt_json TEXT,PRIMARY KEY(array_row,channel,family,band,definition));
        CREATE TABLE completed_blocks(array_row INTEGER PRIMARY KEY,candidate_index INTEGER,completed_utc TEXT);
        """)
        for r in study.read_json(ROOT / "results/010/prepared.json")["records"]:
            db.execute("INSERT INTO candidates VALUES(?,?,?,?,?)",
                       (r["candidate_index"], r["array_row"], r["status"],
                        study.canonical(r["reasons"]), None))
        db.commit()
    if db.execute("SELECT count(*) FROM candidates").fetchone()[0] != 5760:
        raise ValueError("candidate denominator index mismatch")
    return db


def process_block(i, inputs, db):
    selected = inputs["selected"][i]
    ci = selected["candidate_index"]
    native = inputs["native"]["samples_uv"][i]
    valid = inputs["native"]["valid"][i]
    prepared = inputs["prepared"]["patches"][i]
    partitions, native_results, prepared_results = [], {}, {}
    native_transforms, matches, timelines = {}, [], []
    for name in study.NATIVE_VARIANTS:
        x, mask, config, transform = study.native_variant(native, valid, name, ci)
        native_transforms[name] = transform
        path, header, result = saved_result(i, "native", name, x, mask, config, transform, full=name == "primary")
        partitions.append((path, header))
        native_results[name] = result
        if name != "primary":
            t, m = study.native_matches(native_results["primary"], result, name)
            timelines += [dict(variant=name, **row) for row in t]
            matches += [dict(variant=name, **row) for row in m]
    for name in study.PREPARED_VARIANTS:
        x32 = pretrained_study.waveform_variant(prepared, name, 9009+ci)
        measured = [inputs["receipts"][model]["measurements"][5*i+study.PREPARED_VARIANTS.index(name)]
                    for model in study.MODELS]
        h = pretrained_study.array_hash(x32)
        if any(m["input_sha256"] != h for m in measured):
            raise ValueError(f"pre-conversion dual input hash mismatch: {ci}/{name}")
        x = x32.reshape(4, 6000).astype(np.float64)*100
        mask = np.ones(x.shape, dtype=bool)
        transform = dict(name=name, source_float32_sha256=h, source_dtype="float32",
                         source_units="microvolt/100", analyzed_dtype="float64", analyzed_units="microvolt",
                         source_rate_hz=200, seed=9009+ci if name == "independent_phase" else None)
        path, header, result = saved_result(i, "prepared", name, x, mask, {}, transform)
        partitions.append((path, header))
        prepared_results[name] = result
    counts, supports, comparisons, effects = study.prepared_comparisons(
        prepared_results, {model: inputs["encoders"][model]["embeddings"][i] for model in study.MODELS})
    morphology = study.morphology_summary(study.morphology_groups(native_results["primary"]))
    with db:
        if db.execute("SELECT 1 FROM completed_blocks WHERE array_row=?", (i,)).fetchone():
            raise ValueError("block already indexed; refusing duplicate execution")
        for path, header in partitions:
            db.execute("INSERT INTO partitions VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (i, header["branch"], header["variant"], str(path.relative_to(ROOT)),
                        study.digest(path), path.stat().st_size, header["event_rows"],
                        header["accepted_rows"], header["rejected_rows"], study.canonical(header)))
        for row in timelines:
            db.execute("INSERT INTO native_timeline VALUES(?,?,?,?)",
                       (i, row["variant"], row["channel"], study.canonical(row)))
        for row in matches:
            db.execute("INSERT INTO native_match VALUES(?,?,?,?,?,?,?,?)",
                       (i, row["variant"], row["channel"], row["family"], row["polarity"], row["direction"],
                        row["tolerance_seconds"], study.canonical(row)))
        for row in comparisons:
            db.execute("INSERT INTO prepared_metric VALUES(?,?,?,?,?)",
                       (i, row["variant"], row["model"], row["metric"], study.canonical(row)))
        for row in effects:
            db.execute("INSERT INTO block_effect VALUES(?,?,?,?,?,?,?)",
                       (i, ci, row["model"], row["metric"], row["effect"], row["reason"], study.canonical(row)))
        for row in morphology:
            db.execute("INSERT INTO morphology_block VALUES(?,?,?,?,?,?)",
                       (i, row["channel"], row["family"], study.canonical(row["band_hz"]),
                        row["definition"], study.canonical(row)))
        db.execute("INSERT INTO completed_blocks VALUES(?,?,?)", (i, ci, now()))
    return dict(array_row=i, candidate_index=ci, partitions=len(partitions),
                compressed_partition_bytes=sum(p.stat().st_size for p, _ in partitions),
                native_event_rows=sum(h["event_rows"] for _, h in partitions if h["branch"] == "native"),
                prepared_event_rows=sum(h["event_rows"] for _, h in partitions if h["branch"] == "prepared"),
                matches=len(matches), metrics=len(comparisons), effects=effects,
                native_transforms=native_transforms, prepared_support=supports,
                prepared_count_vectors={name: counts[name].tolist() for name in study.PREPARED_VARIANTS})


def indexed_bytes(db):
    db.commit()
    return DB.stat().st_size


def resource_state(db, elapsed_cpu, elapsed_wall):
    compressed = db.execute("SELECT coalesce(sum(bytes),0) FROM partitions").fetchone()[0]
    other_artifacts = sum(path.stat().st_size for path in OUT.rglob("*") if path.is_file()
                          and "protocol-review" not in path.relative_to(OUT).parts)
    return dict(wall_seconds=elapsed_wall, cpu_seconds=elapsed_cpu,
                process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                compressed_partition_bytes=compressed, index_bytes=indexed_bytes(db),
                other_artifact_bytes=other_artifacts,
                actual_artifact_bytes=compressed+other_artifacts)


def save_progress(db, detection_cpu, detection_wall, *, aggregation=None):
    measured = resource_state(db, detection_cpu, detection_wall)
    old_progress_bytes = PROGRESS.stat().st_size if PROGRESS.exists() else 0
    progress = dict(schema="eegt-012-run-progress/v1", completed_blocks=db.execute(
        "SELECT count(*) FROM completed_blocks").fetchone()[0],
        cumulative_detection_cpu_seconds=detection_cpu,
        cumulative_detection_wall_seconds=detection_wall,
        aggregation=aggregation,
        cumulative_cpu_seconds=detection_cpu+(aggregation["cpu_seconds"] if aggregation else 0.),
        cumulative_wall_seconds=detection_wall+(aggregation["wall_seconds"] if aggregation else 0.),
        process_peak_rss_bytes=measured["process_peak_rss_bytes"],
        compressed_partition_bytes=measured["compressed_partition_bytes"],
        analysis_artifact_bytes=measured["actual_artifact_bytes"], updated_utc=now())
    for _ in range(3):
        new_bytes = len((study.canonical(progress)+"\n").encode())
        exact = measured["actual_artifact_bytes"]-old_progress_bytes+new_bytes
        if progress["analysis_artifact_bytes"] == exact:
            break
        progress["analysis_artifact_bytes"] = exact
    write_derived(PROGRESS, progress)
    if resource_state(db, detection_cpu, detection_wall)["actual_artifact_bytes"] != progress["analysis_artifact_bytes"]:
        raise ValueError("cumulative artifact accounting mismatch")
    return progress


def ceiling_for(authorization):
    if authorization is None:
        return CEILINGS
    receipt = study.read_json(authorization)
    if (receipt.get("schema") != "eegt-012-resource-expansion/v1" or
        receipt.get("protocol_sha256") != study.digest(ROOT / "protocol/experiment-012.json") or
        receipt.get("first_block_checkpoint_sha256") != study.digest(OUT / "first-block-checkpoint.json") or
        receipt.get("status") != "AUTHORIZED_RESOURCE_ONLY"):
        raise ValueError("resource expansion receipt mismatch")
    limits = receipt.get("limits", {})
    if any(limits.get(k, 0) < CEILINGS[k] for k in CEILINGS):
        raise ValueError("resource expansion cannot lower original bounds")
    return limits


def scientific_summary(inputs, db):
    rows = []
    for i, ci, model, metric, effect, reason, receipt in db.execute(
        "SELECT array_row,candidate_index,model,metric,effect,reason,receipt_json FROM block_effect ORDER BY array_row,model,metric"):
        rows.append(dict(array_row=i, candidate_index=ci, model=model, metric=metric,
                         effect=effect, reason=reason, receipt=json.loads(receipt)))
    endpoints = study.aggregate_effects(rows, inputs["selected"])
    def primary_loader(i):
        path = partition_path(i, "native", "primary")
        header, events = read_partition(path)
        return dict(header["result"], events=events)
    nights, differences = study.combine_morphology(inputs["selected"], primary_loader)
    synthetic = study.read_json(PACKET / "input/synthetic-validation.json")
    return dict(schema="eegt-012-scientific-summary/v1", status="COMPLETE_NUMERICAL_RECORD",
                selected_blocks=122, candidate_blocks=5760, native_variants=18, prepared_variants=5,
                curator_source_receipt=dict(path="repo/data/derived/012/native-selected-curator.json",
                                            sha256=study.digest(ROOT / "data/derived/012/native-selected-curator.json")),
                primary_endpoints=endpoints, native_morphology_nights=nights,
                native_morphology_night_differences=differences,
                synthetic_noise_false_detection=synthetic["control_aggregate"],
                synthetic_receipt_sha256=study.digest(PACKET / "input/synthetic-validation.json"),
                waveform_path_length=None, waveform_turning_angle=None, waveform_return_distance=None,
                undefined_geometry_reason="no frozen direct-waveform path geometry")


def report(state, inputs, db, profile, limits, *, summary=None, reason=None):
    counts = dict(indexed_blocks=db.execute("SELECT count(*) FROM completed_blocks").fetchone()[0],
                  partitions=db.execute("SELECT count(*) FROM partitions").fetchone()[0],
                  native_matches=db.execute("SELECT count(*) FROM native_match").fetchone()[0],
                  prepared_metrics=db.execute("SELECT count(*) FROM prepared_metric").fetchone()[0],
                  candidate_rows=db.execute("SELECT count(*) FROM candidates").fetchone()[0])
    files = {str(Path(path).relative_to(PACKET)): dict(bytes=bytes_, sha256=sha)
             for path, sha, bytes_ in [(str(ROOT / row[0]), row[1], row[2])
                                       for row in db.execute("SELECT path,sha256,bytes FROM partitions")]}
    for path in (MANIFEST, DB, OUT / "first-block-checkpoint.json"):
        if path.exists():
            files[str(path.relative_to(PACKET))] = file_entry(path, PACKET)
    if (OUT / "summary.json").exists():
        files[str((OUT / "summary.json").relative_to(PACKET))] = file_entry(OUT / "summary.json", PACKET)
    if PROGRESS.exists():
        files[str(PROGRESS.relative_to(PACKET))] = file_entry(PROGRESS, PACKET)
    test_receipt = PACKET / "out/TEST-RESULTS.json"
    if test_receipt.exists():
        files[str(test_receipt.relative_to(PACKET))] = file_entry(test_receipt, PACKET)
    next_command = (None if state == "COMPLETE" else
                    "OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 "
                    "NUMEXPR_NUM_THREADS=1 scratch/.venv/bin/python repo/scripts/reproduce_events.py "
                    "run --resume --resource-authorization PATH_TO_ROOT_RESOURCE_ONLY_RECEIPT")
    result = dict(schema="eegt-012-worker-report/v1", status=state, reason=reason,
                  frozen_manifest_sha256=study.digest(MANIFEST),
                  protocol_sha256=study.digest(ROOT / "protocol/experiment-012.json"),
                  method_sha256=study.digest(ROOT / "protocol/experiment-012-methods.md"),
                  input_sha256={name: study.digest(ROOT / name) for name in INPUT_PATHS},
                  source_sha256={name: study.digest(ROOT / name) for name in SOURCE_PATHS},
                  verified_prepared_variant_hashes=inputs["verified_prepared_pairs"],
                  verified_model_output_hashes=inputs["verified_inference_outputs"],
                  counts=counts, first_block_profile=profile, ceilings=limits,
                  cumulative_resources=study.read_json(PROGRESS) if PROGRESS.exists() else None,
                  artifact_files=files, summary=summary, next_command=next_command,
                  test_results=study.read_json(test_receipt) if test_receipt.exists() else None,
                  provider_cost=None, provider_cost_reason="native provider did not supply task billing",
                  interpretation_limits="Two continuous EEG encoders; numeric detector events are not universal meaning, semantic tokens, or clinical criteria. High synthetic noise false cycles/bursts remain visible.")
    write_derived(PACKET / "out/REPORT.json", result)
    lines = ["# Experiment 012 bounded numerical run", "", f"State: **{state}**.",
             f"Reason: {reason or 'None'}.", "", "## Evidence", "",
             f"Frozen run manifest: `{MANIFEST.relative_to(PACKET)}` ({result['frozen_manifest_sha256']}).",
             f"Indexed blocks: {counts['indexed_blocks']}/122; partitions: {counts['partitions']}; candidate rows: 5760.",
             f"Prepared variant inputs verified: {inputs['verified_prepared_pairs']}/610 against both receipts; model outputs: {inputs['verified_inference_outputs']}/1220.",
             f"First block wall {profile['wall_seconds']:.3f}s, CPU {profile['cpu_seconds']:.3f}s, peak RSS {profile['process_peak_rss_bytes']} bytes, compressed partitions {profile['compressed_partition_bytes']} bytes, index {profile['index_bytes']} bytes.",
             f"122-block projection: CPU {profile['projected_cpu_seconds']:.3f}s, artifacts {profile['projected_artifact_bytes']} bytes; RSS planning floor {profile['process_peak_rss_bytes']} bytes (future peak unknown).",
             (f"Cumulative CPU {study.read_json(PROGRESS)['cumulative_cpu_seconds']:.3f}s, "
              f"wall {study.read_json(PROGRESS)['cumulative_wall_seconds']:.3f}s, "
              f"artifacts {study.read_json(PROGRESS)['analysis_artifact_bytes']} bytes; "
              f"receipt `{PROGRESS.relative_to(PACKET)}`.") if PROGRESS.exists() else "Cumulative resource receipt unavailable.",
             f"Tests: `{test_receipt.relative_to(PACKET)}`." if test_receipt.exists() else "Tests: receipt unavailable.",
             "", "## Reproduction", "",
             "Exact freeze: `scratch/.venv/bin/python repo/scripts/reproduce_events.py freeze`.",
             "Exact run: `scratch/.venv/bin/python repo/scripts/reproduce_events.py run` with all five thread environment variables set to 1.",
             "Readback: `scratch/.venv/bin/python repo/scripts/reproduce_events.py reproduce` with the same environment.",
             f"Next deterministic command: `{next_command}`." if next_command else "Next: root independent source/numeric review and extracted reproduction.",
             "", "## Scientific limits", "",
             "The two encoders are continuous EEG backbones. Numeric events and weak or shared effects do not establish universal meaning or clinical diagnostic criteria.",
             "A cosine distance sequence with range at most 32 float64 eps times max(1, maximum absolute distance) abstains as arithmetically constant; this was fixed on analytic proportional vectors before empirical analysis.",
             "The accepted synthetic receipt retains 100-seed oscillator-absent noise false cycle and burst counts in `input/synthetic-validation.json` and the full summary.",
             "No threshold was tuned on empirical output. Curator identities enter only the evaluation/index stage."]
    markdown = PACKET / "out/REPORT.md"
    markdown.parent.mkdir(parents=True, exist_ok=True)
    temp = markdown.with_name(markdown.name + ".partial")
    temp.write_text("\n".join(lines) + "\n")
    temp.replace(markdown)
    return result


def run(resume=False, resource_authorization=None):
    verify_freeze()
    inputs = study.verify_arrays(PACKET)
    existing = (OUT / "first-block-checkpoint.json").exists()
    if resume != existing:
        raise ValueError("use run for first block and run --resume after checkpoint")
    db = open_index(inputs)
    if not existing:
        if db.execute("SELECT count(*) FROM completed_blocks").fetchone()[0]:
            raise ValueError("unexpected indexed block before first checkpoint")
        start_wall, start_cpu = time.monotonic(), time.process_time()
        block = process_block(0, inputs, db)
        elapsed_wall, elapsed_cpu = time.monotonic()-start_wall, time.process_time()-start_cpu
        measured = resource_state(db, elapsed_cpu, elapsed_wall)
        profile = dict(**measured, projected_cpu_seconds=elapsed_cpu*122,
                       projected_artifact_bytes=measured["actual_artifact_bytes"]*122,
                       projected_wall_seconds=elapsed_wall*122,
                       first_block=block)
        write_new(OUT / "first-block-checkpoint.json",
                  dict(schema="eegt-012-first-block-checkpoint/v1", status="MEASURED",
                       run_manifest_sha256=study.digest(MANIFEST), profile=profile,
                       indexed_partitions=[dict(path=row[0], sha256=row[1], bytes=row[2])
                                           for row in db.execute("SELECT path,sha256,bytes FROM partitions ORDER BY path")]))
        (OUT / "first-block-checkpoint.json").chmod(0o444)
        progress = save_progress(db, elapsed_cpu, elapsed_wall)
    else:
        profile = study.read_json(OUT / "first-block-checkpoint.json")["profile"]
        progress = study.read_json(PROGRESS)
        if progress["completed_blocks"] != db.execute("SELECT count(*) FROM completed_blocks").fetchone()[0]:
            raise ValueError("resume progress/index count mismatch")
    limits = ceiling_for(resource_authorization)
    exceeded = [name for name, actual in (("cpu_seconds", profile["projected_cpu_seconds"]),
                                           ("artifact_bytes", profile["projected_artifact_bytes"]),
                                           ("rss_bytes", profile["process_peak_rss_bytes"])) if actual > limits[name]]
    if exceeded:
        result = report("RESOURCE_REASSESSMENT_REQUIRED", inputs, db, profile, limits,
                        reason="first-block projection exceeds " + ", ".join(exceeded))
        db.close()
        print(study.canonical({"status": result["status"], "exceeded": exceeded,
                               "profile": profile, "report": str(PACKET / "out/REPORT.json")}))
        return
    base_cpu = progress["cumulative_detection_cpu_seconds"]
    base_wall = progress["cumulative_detection_wall_seconds"]
    resumed_cpu = time.process_time()
    resumed_wall = time.monotonic()
    for i in range(1, 122):
        if db.execute("SELECT 1 FROM completed_blocks WHERE array_row=?", (i,)).fetchone():
            continue
        predicted = [name for name, actual in (
            ("cpu_seconds", progress["cumulative_cpu_seconds"]+profile["cpu_seconds"]),
            ("artifact_bytes", progress["analysis_artifact_bytes"]+profile["actual_artifact_bytes"]),
            ("rss_bytes", progress["process_peak_rss_bytes"])) if actual > limits[name]]
        if predicted:
            report("RESOURCE_REASSESSMENT_REQUIRED", inputs, db, profile, limits,
                   reason="next block may exceed cumulative bound before row " + str(i) + ": " + ", ".join(predicted))
            db.close()
            return
        process_block(i, inputs, db)
        progress = save_progress(db, base_cpu+time.process_time()-resumed_cpu,
                                 base_wall+time.monotonic()-resumed_wall)
        breached = [name for name, actual in (("cpu_seconds", progress["cumulative_cpu_seconds"]),
                                              ("artifact_bytes", progress["analysis_artifact_bytes"]),
                                              ("rss_bytes", progress["process_peak_rss_bytes"])) if actual > limits[name]]
        if breached:
            report("RESOURCE_REASSESSMENT_REQUIRED", inputs, db, profile, limits,
                   reason="actual bound exceeded after row " + str(i) + ": " + ", ".join(breached))
            db.close()
            return
        print(study.canonical(dict(array_row=i, completed=i+1,
                                   cumulative_cpu_seconds=progress["cumulative_cpu_seconds"],
                                   artifact_bytes=progress["analysis_artifact_bytes"])), flush=True)
    if db.execute("SELECT count(*) FROM completed_blocks").fetchone()[0] != 122:
        raise ValueError("full numerical run incomplete")
    if (progress["cumulative_cpu_seconds"]+profile["cpu_seconds"] > limits["cpu_seconds"] or
        progress["analysis_artifact_bytes"]+profile["actual_artifact_bytes"] > limits["artifact_bytes"]):
        report("RESOURCE_REASSESSMENT_REQUIRED", inputs, db, profile, limits,
               reason="insufficient remaining cumulative budget for final aggregation")
        db.close()
        return
    agg_cpu, agg_wall = time.process_time(), time.monotonic()
    summary = scientific_summary(inputs, db)
    write_new(OUT / "summary.json", summary)
    aggregation = dict(cpu_seconds=time.process_time()-agg_cpu, wall_seconds=time.monotonic()-agg_wall,
                       output_sha256=study.digest(OUT / "summary.json"))
    progress = save_progress(db, base_cpu+time.process_time()-resumed_cpu-aggregation["cpu_seconds"],
                             base_wall+time.monotonic()-resumed_wall-aggregation["wall_seconds"],
                             aggregation=aggregation)
    breached = [name for name, actual in (("cpu_seconds", progress["cumulative_cpu_seconds"]),
                                          ("artifact_bytes", progress["analysis_artifact_bytes"]),
                                          ("rss_bytes", progress["process_peak_rss_bytes"])) if actual > limits[name]]
    if breached:
        report("RESOURCE_REASSESSMENT_REQUIRED", inputs, db, profile, limits,
               reason="final aggregation exceeded actual bound: " + ", ".join(breached),
               summary=dict(path="repo/results/012/summary.json", sha256=study.digest(OUT / "summary.json")))
        db.close()
        return
    report("COMPLETE", inputs, db, profile, limits, summary=dict(path="repo/results/012/summary.json",
                                                                  sha256=study.digest(OUT / "summary.json")))
    db.close()


def reproduce():
    replay_cpu, replay_wall = time.process_time(), time.monotonic()
    manifest = verify_freeze()
    inputs = study.verify_arrays(PACKET)
    if not DB.exists():
        raise FileNotFoundError("analysis index missing from extracted package")
    db = open_index(inputs)
    n = db.execute("SELECT count(*) FROM completed_blocks").fetchone()[0]
    checked = 0
    for path, expected, header_json in db.execute("SELECT path,sha256,header_json FROM partitions ORDER BY path"):
        full = ROOT / path
        if study.digest(full) != expected:
            raise ValueError(f"partition SHA256 mismatch: {path}")
        header, rows = read_partition(full)
        if study.canonical(header) != header_json:
            raise ValueError(f"partition header mismatch: {path}")
        checked += 1
    if checked != 23*n:
        raise ValueError("partition denominator mismatch")
    for i in range(n):
        prepared = {name: dict(read_partition(partition_path(i, "prepared", name))[0]["result"],
                               events=read_partition(partition_path(i, "prepared", name))[1])
                    for name in study.PREPARED_VARIANTS}
        _, _, metrics, effects = study.prepared_comparisons(
            prepared, {model: inputs["encoders"][model]["embeddings"][i] for model in study.MODELS})
        indexed = [json.loads(row[0]) for row in db.execute(
            "SELECT receipt_json FROM prepared_metric WHERE array_row=? ORDER BY model,metric,variant", (i,))]
        if sorted(map(study.canonical, indexed)) != sorted(map(study.canonical, metrics)):
            raise ValueError(f"prepared metric reproduction mismatch: {i}")
        indexed_effects = [json.loads(row[0]) for row in db.execute(
            "SELECT receipt_json FROM block_effect WHERE array_row=?", (i,))]
        if sorted(map(study.canonical, indexed_effects)) != sorted(map(study.canonical, effects)):
            raise ValueError(f"block effect reproduction mismatch: {i}")
        primary_h, primary_e = read_partition(partition_path(i, "native", "primary"))
        primary = dict(primary_h["result"], events=primary_e)
        for name in study.NATIVE_VARIANTS[1:]:
            h, e = read_partition(partition_path(i, "native", name))
            timeline, matches = study.native_matches(primary, dict(h["result"], events=e), name)
            timeline = [dict(variant=name, **row) for row in timeline]
            matches = [dict(variant=name, **row) for row in matches]
            old_t = [json.loads(row[0]) for row in db.execute(
                "SELECT receipt_json FROM native_timeline WHERE array_row=? AND variant=?", (i, name))]
            old_m = [json.loads(row[0]) for row in db.execute(
                "SELECT receipt_json FROM native_match WHERE array_row=? AND variant=?", (i, name))]
            if (sorted(map(study.canonical, old_t)) != sorted(map(study.canonical, timeline)) or
                sorted(map(study.canonical, old_m)) != sorted(map(study.canonical, matches))):
                raise ValueError(f"native match reproduction mismatch: {i}/{name}")
    if n == 122:
        summary = scientific_summary(inputs, db)
        if study.canonical(summary) != study.canonical(study.read_json(OUT / "summary.json")):
            raise ValueError("full scientific summary reproduction mismatch")
    current_runtime = runtime()
    index_sha = study.digest(DB)
    receipt = dict(schema="eegt-012-reproduction/v1", status="REPRODUCED", blocks=n,
                   partitions=checked, full_scientific_summary=n == 122,
                   cpu_seconds=time.process_time()-replay_cpu,
                   wall_seconds=time.monotonic()-replay_wall,
                   process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   original_runtime=manifest["runtime"], reproduction_runtime=current_runtime,
                   runtime_differences={key: [manifest["runtime"].get(key), current_runtime.get(key)]
                                        for key in ("executable", "executable_sha256", "platform", "python")
                                        if manifest["runtime"].get(key) != current_runtime.get(key)},
                   run_manifest_sha256=study.digest(MANIFEST), index_sha256=index_sha)
    destination = OUT / ("reproduction-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+".json")
    write_new(destination, receipt)
    report_path = PACKET / "out/REPORT.json"
    if report_path.exists():
        current_report = study.read_json(report_path)
        current_report["reproduction"] = dict(path=str(destination.relative_to(PACKET)),
                                               sha256=study.digest(destination), **receipt)
        current_report["artifact_files"][str(destination.relative_to(PACKET))] = file_entry(destination, PACKET)
        write_derived(report_path, current_report)
        markdown = PACKET / "out/REPORT.md"
        with markdown.open("a") as handle:
            handle.write(f"\n## Readback\n\nReproduced {n} blocks and {checked} hash-bound partitions; CPU {receipt['cpu_seconds']:.3f}s, wall {receipt['wall_seconds']:.3f}s. Receipt: `{destination.relative_to(PACKET)}`.\n")
    print(study.canonical(receipt))
    db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "freeze", "run", "reproduce"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--resource-authorization", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "preflight":
            inputs = study.verify_arrays(PACKET)
            print(study.canonical(dict(status="PREFLIGHT_OK", inherited_files=len(inputs["source"]["files"]),
                                       native_rows=122, prepared_variants=inputs["verified_prepared_pairs"],
                                       model_outputs=inputs["verified_inference_outputs"])))
        elif args.action == "freeze": freeze()
        elif args.action == "run": run(args.resume, args.resource_authorization)
        else: reproduce()
    except Exception as error:
        OUT.mkdir(parents=True, exist_ok=True)
        failure = dict(schema="eegt-012-failed-attempt/v1", observed_utc=now(),
                       action=args.action, error_type=type(error).__name__, error=str(error),
                       traceback=traceback.format_exc(), run_manifest_sha256=study.digest(MANIFEST) if MANIFEST.exists() else None)
        path = OUT / ("failed-attempt-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        write_new(path, failure)
        raise


if __name__ == "__main__":
    main()
