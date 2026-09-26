"""Experiment 013 source and numeric preparation, before any model or event call.

The ordinary entry points require the root-owned accepted run-source manifest.
The exposed fixture entry points are restricted to the published 001/001 source.
Curator identities stay in JSON; numerical archives contain arrays only.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import gc
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import resource
import time

import numpy as np

from .acquire import ROOT, digest
from .corpus import atomic_json, safe_path
from .validation_provenance import verify_loaded_sources


COHORTS = ("new_people", "new_sessions")
CHANNELS = ("RB", "RT", "LB", "LT")
RATE = 250
BLOCK_SAMPLES = 7500
BLOCKS_PER_RECORD = 480
FREEZE_PATH = "results/013/RUN-SOURCE-MANIFEST.json"
SOURCE_PATH = "protocol/corpus-manifest-013.json"
PROTOCOL_PATH = "protocol/experiment-013.json"
REQUIRED_FROZEN = (
    PROTOCOL_PATH, SOURCE_PATH, "eegt/validation_provenance.py", "eegt/validation_intake.py",
    "scripts/prepare_validation.py", "tests/test_validation_intake.py",
    "eegt/validation_study.py", "scripts/reproduce_validation.py",
    "tests/test_validation_study.py",
    "eegt/repeated.py", "eegt/transitions.py", "eegt/pretrained_study.py",
    "eegt/distributed_study.py", "requirements.lock", "requirements-encoder.lock",
)
THREAD_ENV = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")


def read(path):
    return json.loads(Path(path).read_text())


def _inside(root, relative):
    path = safe_path(root, relative)
    if not path.is_file():
        raise ValueError(f"missing frozen input: {relative}")
    return path


def _runtime(phase):
    import scipy
    result = dict(python=platform.python_version(), numpy=np.__version__,
                  scipy=scipy.__version__)
    if phase == "corpus":
        import mne
        result["mne"] = mne.__version__
    elif phase == "events":
        result.update(bycycle=version("bycycle"), neurodsp=version("neurodsp"))
    return result


def _require_one_numeric_thread(phase):
    unset = [name for name in THREAD_ENV if os.environ.get(name) != "1"]
    if unset:
        raise ValueError("numeric thread cap is not one: " + ", ".join(unset))
    if phase == "corpus":
        from threadpoolctl import threadpool_info
        active = [(pool.get("internal_api"), pool.get("num_threads"))
                  for pool in threadpool_info() if pool.get("num_threads") != 1]
        if active:
            raise ValueError(f"active numeric threadpool is not one: {active}")


def require_accepted_freeze(root=ROOT, phase="corpus"):
    """Fail before source access unless the accepted executable and runtime match."""
    root = Path(root)
    if phase not in ("corpus", "encoder", "events"):
        raise ValueError("phase must be corpus, encoder or events")
    seal = read(root / FREEZE_PATH)
    if seal.get("schema") != "eegt-validation-run-source-manifest/v1" or seal.get("status") != "ACCEPTED":
        raise ValueError("Experiment013 run-source freeze is not accepted")
    _require_one_numeric_thread(phase)
    inputs = seal.get("inputs")
    if not isinstance(inputs, dict) or not set(REQUIRED_FROZEN) <= inputs.keys():
        raise ValueError("accepted freeze lacks required source bindings")
    for name, expected in inputs.items():
        if not isinstance(expected, str) or len(expected) != 64 or digest(_inside(root, name)) != expected:
            raise ValueError(f"accepted freeze input changed: {name}")
    reviews = seal.get("accepted_reviews")
    if not isinstance(reviews, list) or not reviews:
        raise ValueError("accepted freeze lacks independent review references")
    for review in reviews:
        if review.get("status") != "ACCEPTED" or digest(_inside(root, review["path"])) != review.get("sha256"):
            raise ValueError("accepted review reference changed")
    models = seal.get("models")
    if not isinstance(models, dict) or set(models) != {"codebrain", "cbramod"}:
        raise ValueError("accepted freeze lacks both model identities")
    for model in models.values():
        checkpoint = model.get("checkpoint", {})
        if digest(_inside(root, checkpoint["path"])) != checkpoint.get("sha256"):
            raise ValueError("accepted model checkpoint changed")
        vendors = model.get("vendor_sources")
        if not isinstance(vendors, dict) or not vendors:
            raise ValueError("accepted model vendor source bindings missing")
        for name, expected_sha in vendors.items():
            if digest(_inside(root, name)) != expected_sha:
                raise ValueError("accepted model vendor source changed")
    bounds = seal.get("resource_bounds", {})
    if (bounds.get("max_download_bytes", 0) < 3312979776 or
            bounds.get("numeric_processes") != 1 or bounds.get("blas_threads") != 1 or
            any(not isinstance(bounds.get(k), (int, float)) or bounds[k] <= 0
                for k in ("cpu_seconds", "rss_bytes", "artifact_bytes")) or
            bounds.get("first_block_required") is not True):
        raise ValueError("accepted resource bounds missing or too small")
    verify_loaded_sources(seal)
    expected = seal.get("runtimes", {}).get(phase)
    actual = _runtime(phase)
    if not isinstance(expected, dict) or any(expected.get(k) != v for k, v in actual.items()):
        raise ValueError(f"accepted {phase} runtime mismatch: expected {expected}, actual {actual}")
    protocol, source = read(root / PROTOCOL_PATH), read(root / SOURCE_PATH)
    if protocol.get("state") != "FROZEN":
        raise ValueError("Experiment013 protocol state is not FROZEN")
    validate_sources(source, protocol)
    return seal, protocol, source


class IntakeResources:
    """Measured record-boundary caps and a root-reviewed first-record gate.

    Checks occur before/after each bounded record, not as an OS hard limit.
    A stopped first-record pass may be replayed after root admission. Existing
    numeric archives are reused only when every array is exactly equal.
    """
    def __init__(self, root, seal, stage):
        self.root, self.seal, self.stage = Path(root), seal, stage
        self.cpu, self.wall = time.process_time(), time.monotonic()
        self.profile = self.root / f"results/013/first-record-{stage}.json"
        self.phase = "intake-" + stage
        self.check()
        if self.profile.exists():
            self.require_review()

    def check(self):
        from .validation_study import _resource_snapshot, _check_bounds
        verify_loaded_sources(self.seal)
        measured = _resource_snapshot(self.root, self.cpu, self.wall)
        _check_bounds(measured, self.seal["resource_bounds"])
        return measured

    def require_review(self):
        from .validation_study import require_first_block_review
        return require_first_block_review(self.root, self.profile, self.phase, self.seal)

    def after_record(self, index, recording_id):
        measured = self.check()
        if index == 0 and not self.profile.exists():
            atomic_json(self.profile, dict(schema="eegt-validation-intake-profile/v1",
                stage=self.stage, recording_id=recording_id, resources=measured,
                run_manifest_sha256=digest(self.root / FREEZE_PATH),
                measurement_boundary="one full record; caps checked at record boundaries"),
                immutable=True)
            raise RuntimeError(f"first-record review required: {self.phase}")
        return measured


def validate_sources(source, protocol):
    """Preserve the exact 20 pinned people/night keys and stable record order."""
    if tuple(protocol.get("channels", ())) != CHANNELS or protocol.get("rate_hz") != RATE:
        raise ValueError("validation channel/rate contract changed")
    cohorts = protocol.get("cohorts")
    if not isinstance(cohorts, list) or {c.get("id") for c in cohorts} != set(COHORTS):
        raise ValueError("expected two distinct validation cohorts")
    pairs = {(person, night): c["id"] for c in cohorts
             for person in c["people"] for night in c["sessions"]}
    records = source.get("records")
    if not isinstance(records, list) or len(records) != 20 or len(pairs) != 20:
        raise ValueError("expected exactly 20 planned recordings")
    if records != sorted(records, key=lambda r: (r["source_subject"], r["session"])):
        raise ValueError("source records must be sorted by person and session")
    if {(r["source_subject"], r["session"]) for r in records} != set(pairs):
        raise ValueError("source person/night set changed")
    src = source.get("source", {})
    if src.get("dataset") != "ds005178" or not src.get("commit"):
        raise ValueError("source dataset/version identity missing")
    ids = []
    for rec in records:
        f = rec["file"]
        expected_id = hashlib.sha256(
            f"{src['dataset']}:{src['commit']}:{f['path']}".encode()).hexdigest()[:24]
        if (rec["recording_id"] != expected_id or
                rec["cohort"] != pairs[rec["source_subject"], rec["session"]] or
                [c["name"] for c in rec["channels"]] != list(CHANNELS) or
                f.get("algorithm") != "sha256" or len(f.get("expected_digest", "")) != 64 or
                not isinstance(f.get("bytes"), int) or f["bytes"] <= 0):
            raise ValueError("source record identity, cohort, channel or upstream hash changed")
        ids.append(expected_id)
    if len(set(ids)) != 20:
        raise ValueError("duplicate source recording ID")
    return records


def _record_path(root, source, rec):
    return safe_path(Path(root) / "data/cache" / source["source"]["dataset"], rec["file"]["path"])


def _verify_qualification(source, receipt):
    records = source["records"]
    rows = receipt.get("records", [])
    if len(rows) != len(records) or [r["recording_id"] for r in rows] != [r["recording_id"] for r in records]:
        raise ValueError("qualification recording census mismatch")
    for src, row in zip(records, rows, strict=True):
        if any(row.get(key) != src[key] for key in ("source_subject", "session", "cohort")):
            raise ValueError("qualification identity/cohort mismatch")
        if row.get("status") == "QUALIFIED" and (row.get("sample_rate_hz") != RATE or
                                                  row.get("channels") != list(CHANNELS) or
                                                  row.get("sha256") != src["file"]["expected_digest"]):
            raise ValueError("qualified source technical or byte identity mismatch")
    return rows


def _check_input_bindings(root, receipt):
    inputs = receipt.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        raise ValueError("receipt lacks input SHA256 bindings")
    for name, expected in inputs.items():
        if digest(_inside(root, name)) != expected:
            raise ValueError(f"receipt input changed: {name}")


def acquire_sources(root=ROOT):
    """Future sequential acquisition; unavailable before the accepted freeze."""
    from .corpus import acquire_file

    root = Path(root)
    seal, _, source = require_accepted_freeze(root, "corpus")
    planned = sum(r["file"]["bytes"] for r in source["records"])
    if planned > seal["resource_bounds"]["max_download_bytes"]:
        raise ValueError("pinned source bytes exceed accepted acquisition bound")
    destination = root / "results/013/acquisition.json"
    expected = [dict(recording_id=r["recording_id"], source_subject=r["source_subject"],
                     session=r["session"], cohort=r["cohort"],
                     path=str(_record_path(root, source, r).relative_to(root)),
                     expected_bytes=r["file"]["bytes"],
                     expected_sha256=r["file"]["expected_digest"],
                     source_url=r["file"]["url"], status="PENDING", bytes=None,
                     sha256=None, reason=None) for r in source["records"]]
    if destination.exists():
        receipt = read(destination)
        if (receipt.get("manifest_sha256") != digest(root / SOURCE_PATH) or
                [(r["recording_id"], r["path"]) for r in receipt.get("records", [])] !=
                [(r["recording_id"], r["path"]) for r in expected]):
            raise ValueError("existing acquisition receipt/source identity changed")
    else:
        receipt = dict(schema="eegt-validation-acquisition/v1",
                       manifest_sha256=digest(root / SOURCE_PATH), records=expected,
                       completed=False)
        atomic_json(destination, receipt)
    for row, rec in zip(receipt["records"], source["records"], strict=True):
        path = _record_path(root, source, rec)
        if row["status"] == "VERIFIED":
            if (not path.is_file() or path.stat().st_size != rec["file"]["bytes"] or
                    digest(path) != row["sha256"] or row["sha256"] != rec["file"]["expected_digest"]):
                raise ValueError("previously verified acquisition bytes changed")
            continue
        part = path.with_name(path.name + ".partial")
        if part.exists() and part.stat().st_size == rec["file"]["bytes"] and \
                digest(part) != rec["file"]["expected_digest"]:
            failed = part.with_name(part.name + ".failed-" + digest(part)[:12])
            part.rename(failed)
            row["failed_partial"] = dict(path=str(failed.relative_to(root)),
                                         bytes=failed.stat().st_size, sha256=digest(failed))
        try:
            sha = acquire_file(rec["file"], path, attempts=2)
            row.update(status="VERIFIED", bytes=path.stat().st_size,
                       sha256=sha, reason=None)
        except (OSError, ValueError) as exc:
            row.update(status="FAILED", reason=f"{type(exc).__name__}: {exc}")
            if part.exists():
                row["failed_partial"] = dict(path=str(part.relative_to(root)),
                                             bytes=part.stat().st_size, sha256=digest(part))
        receipt["completed"] = all(r["status"] != "PENDING" for r in receipt["records"])
        atomic_json(destination, receipt)
    return receipt


def qualify_sources(root=ROOT):
    """Qualify previously acquired, pinned files; missing rows remain visible."""
    from .repeated import qualify_record

    root = Path(root)
    seal, protocol, source = require_accepted_freeze(root, "corpus")
    acq_path = root / "results/013/acquisition.json"
    acquisition = read(acq_path)
    if (acquisition.get("manifest_sha256") != digest(root / SOURCE_PATH) or
            not acquisition.get("completed") or
            any(r.get("status") == "PENDING" for r in acquisition.get("records", []))):
        raise ValueError("acquisition/source manifest hash mismatch")
    by_id = {r["recording_id"]: r for r in acquisition.get("records", [])}
    if len(by_id) != 20 or set(by_id) != {r["recording_id"] for r in source["records"]}:
        raise ValueError("acquisition must retain all 20 planned rows")
    technical = dict(expected_channels=list(CHANNELS), expected_sample_rate_hz=RATE,
                     analysis_seconds=0)  # short support is censused, not hidden here
    rows = []
    guard = IntakeResources(root, seal, "qualify")
    for index, rec in enumerate(source["records"]):
        guard.check()
        f = rec["file"]
        acq = by_id[rec["recording_id"]]
        path = _record_path(root, source, rec)
        row = dict(recording_id=rec["recording_id"], source_subject=rec["source_subject"],
                   session=rec["session"], cohort=rec["cohort"], path=str(path.relative_to(root)),
                   expected_bytes=f["bytes"], expected_sha256=f["expected_digest"],
                   bytes=acq.get("bytes"), sha256=acq.get("sha256"), status="QUARANTINED",
                   reason=acq.get("reason") or "SOURCE_MISSING")
        if acq.get("status") == "VERIFIED":
            if path.is_file():
                row.update(bytes=path.stat().st_size, sha256=digest(path))
            if not path.is_file() or row["bytes"] != f["bytes"]:
                row["reason"] = "SOURCE_BYTES_MISMATCH"
            elif acq.get("bytes") != f["bytes"]:
                row["reason"] = "ACQUISITION_RECEIPT_MISMATCH"
            elif row["sha256"] != f["expected_digest"] or acq.get("sha256") != f["expected_digest"]:
                row["reason"] = "SOURCE_SHA256_MISMATCH"
            else:
                row.update(bytes=f["bytes"], sha256=f["expected_digest"])
                try:
                    row.update(qualify_record(path, rec, technical))
                    row["gap_seconds"] = [dict(start_sample=a, stop_sample=b,
                                               start_seconds=a / RATE, stop_seconds=b / RATE)
                                          for a, b in row["gaps"]]
                    row["acquisition_clock_verified"] = None
                    row.update(status="QUALIFIED", reason=None)
                except (ValueError, KeyError, OSError, IndexError) as exc:
                    row["reason"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
        # The EEGLAB decoder can leave unreachable cycles holding native arrays.
        # Reclaim them before the per-record RSS admission check.
        gc.collect()
        guard.after_record(index, rec["recording_id"])
    receipt = dict(schema="eegt-validation-qualification/v1", records=rows,
                   resources=guard.check(),
                   inputs={SOURCE_PATH: digest(root / SOURCE_PATH),
                           PROTOCOL_PATH: digest(root / PROTOCOL_PATH),
                           FREEZE_PATH: digest(root / FREEZE_PATH),
                           "results/013/acquisition.json": digest(acq_path)},
                   runtime=_runtime("corpus"), created_at_utc=datetime.now(timezone.utc).isoformat())
    atomic_json(root / "results/013/qualification.json", receipt, immutable=True)
    return receipt


def _gap_reasons(gaps, start, stop):
    reasons = []
    for gap in gaps:
        if isinstance(gap, dict):
            a, b = gap["start_sample"], gap["stop_sample"]
        else:
            a, b = gap
        if a == b and start < a < stop:
            reasons.append("NATIVE_BOUNDARY")
        elif a < stop and b > start:
            reasons.append("NATIVE_GAP")
    return list(dict.fromkeys(reasons))


def baseline_counts(times, valid, *, blocks=BLOCKS_PER_RECORD):
    """Use Experiment010's 28 exact centers from inherited 008 features."""
    times = np.asarray(times, dtype=np.float64)
    valid = np.asarray(valid)
    if (times.ndim != 1 or valid.shape != times.shape or valid.dtype != np.bool_ or
            not np.isfinite(times).all() or np.any(np.diff(times) <= 0)):
        raise ValueError("invalid baseline time/valid arrays")
    counts = []
    for block in range(blocks):
        target = block * 30 + np.arange(1.5, 29, 1)
        ix = np.searchsorted(times, target)
        aligned = ix < len(times)
        aligned[aligned] &= times[ix[aligned]] == target[aligned]
        counts.append(int(valid[ix[aligned]].sum()))
    return counts


def extract_baseline_valid(samples_uv, gaps=()):
    """Run the unchanged 008 window predicate with its full chunk/halo grid."""
    from .growth import continuous_intervals
    from .transitions import extract_features

    x = np.asarray(samples_uv)
    if x.ndim != 2 or x.shape[0] != 4 or x.dtype != np.float64:
        raise ValueError("expected native float64 [4,time] microvolt array")
    limit = min(x.shape[1], 4 * 3600 * RATE)
    clipped = [(min(limit, a), min(limit, b)) for a, b in gaps if a < limit]
    intervals = continuous_intervals(limit, clipped)
    all_times, all_valid = [], []
    chunk, halo = 600 * RATE, 12 * RATE
    for start, stop in intervals:
        for core in range(start, stop, chunk):
            end = min(stop, core + chunk)
            left, right = max(start, core - halo), min(stop, end + halo)
            if right - left < 2 * RATE:
                continue
            output = extract_features(x[:, left:right], RATE,
                                      window_seconds=2, hop_seconds=0.5)
            centers2 = np.rint(output["times"] * RATE * 2).astype(np.int64) + left * 2
            keep = (centers2 >= core * 2) & (centers2 < end * 2)
            all_times.append(centers2[keep] / (2 * RATE))
            all_valid.append(output["valid"][keep])
    if not all_times:
        return np.empty(0, np.float64), np.empty(0, bool)
    times, valid = np.concatenate(all_times), np.concatenate(all_valid)
    if np.any(np.diff(times) <= 0):
        raise ValueError("baseline centers are unordered or duplicated")
    return times, valid


def _save_numeric(path, **arrays):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with np.load(path, allow_pickle=False) as prior:
            if (set(prior.files) == set(arrays) and all(
                    prior[k].dtype == a.dtype and prior[k].shape == a.shape and
                    np.array_equal(prior[k], a, equal_nan=True) for k, a in arrays.items())):
                return
        raise FileExistsError(f"preserve changed numeric archive: {path}")
    part = path.with_suffix(path.suffix + ".partial")
    with part.open("wb") as stream:
        np.savez_compressed(stream, **arrays)
    part.replace(path)


def _quality_rows_for_record(rec, record_index, times=None, baseline_valid=None):
    counts = baseline_counts(times, baseline_valid) if times is not None else None
    n = rec.get("samples_per_channel", 0) if rec["status"] == "QUALIFIED" else 0
    rows = []
    for block in range(BLOCKS_PER_RECORD):
        start = block * BLOCK_SAMPLES
        reasons = []
        if rec["status"] != "QUALIFIED":
            reasons.append("SOURCE_UNQUALIFIED")
            if rec.get("reason") in ("SOURCE_MISSING", "SOURCE_BYTES_MISMATCH",
                                     "SOURCE_SHA256_MISMATCH"):
                reasons.append(rec["reason"])
        else:
            if start + BLOCK_SAMPLES > n:
                reasons.append("SHORT_SUPPORT")
            reasons.extend(_gap_reasons(rec.get("gaps", ()), start, start + BLOCK_SAMPLES))
            if counts[block] != 28:
                reasons.append("BASELINE_QC")
        rows.append(dict(candidate_index=record_index * BLOCKS_PER_RECORD + block,
                         recording_id=rec["recording_id"], source_subject=rec["source_subject"],
                         session=rec["session"], cohort=rec["cohort"],
                         start_seconds=block * 30, duration_seconds=30,
                         stratum_index=block // 40,
                         baseline_valid_centers=counts[block] if counts is not None else None,
                         source_qualification_reason=rec.get("reason") if rec["status"] != "QUALIFIED" else None,
                         reasons=list(dict.fromkeys(reasons))))
    return rows


def build_quality_census(root=ROOT):
    """Hash-check source, decode only after freeze, and retain numeric handoff."""
    import mne

    root = Path(root)
    seal, _, source = require_accepted_freeze(root, "corpus")
    qualification_path = root / "results/013/qualification.json"
    qualification = read(qualification_path)
    _check_input_bindings(root, qualification)
    if qualification.get("inputs", {}).get(SOURCE_PATH) != digest(root / SOURCE_PATH):
        raise ValueError("qualification/source binding mismatch")
    qualified = _verify_qualification(source, qualification)
    rows, native_archives, baseline_archives = [], {}, {}
    started = time.monotonic()
    guard = IntakeResources(root, seal, "quality")
    for i, (src, rec) in enumerate(zip(source["records"], qualified, strict=True)):
        guard.check()
        if rec["status"] != "QUALIFIED":
            rows.extend(_quality_rows_for_record(rec, i))
            guard.after_record(i, rec["recording_id"])
            continue
        path = _record_path(root, source, src)
        if digest(path) != rec["sha256"]:
            raise ValueError("qualified source bytes changed")
        raw = mne.io.read_raw_eeglab(path, preload=False, verbose="ERROR")
        try:
            if raw.info["sfreq"] != RATE or any(c not in raw.ch_names for c in CHANNELS):
                raise ValueError("decoded channel/rate mismatch")
            n = min(raw.n_times, 4 * 3600 * RATE)
            x = np.asarray(raw.get_data(picks=list(CHANNELS), start=0, stop=n) * 1e6,
                           dtype=np.float64)
        finally:
            raw.close()
            # Embedded EEGLAB reads cache full arrays even with preload=False.
            del raw
            gc.collect()
        if x.shape != (4, n) or n != min(rec["samples_per_channel"], 4 * 3600 * RATE):
            raise ValueError("native source support changed")
        gaps = [tuple(g) if not isinstance(g, dict) else
                (g["start_sample"], g["stop_sample"]) for g in rec.get("gaps", [])]
        valid = np.isfinite(x)
        for a, b in gaps:
            if b > a:
                valid[:, max(0, a):min(n, b)] = False
        times, baseline_valid = extract_baseline_valid(x, gaps)
        native_rel = f"data/derived/013/native-first-four-hours/{rec['recording_id']}.npz"
        baseline_rel = f"data/derived/013/baseline-valid/{rec['recording_id']}.npz"
        _save_numeric(root / native_rel, samples_uv=x, valid=valid)
        _save_numeric(root / baseline_rel, times=times, valid=baseline_valid)
        native_archives[rec["recording_id"]] = dict(path=native_rel, sha256=digest(root / native_rel))
        baseline_archives[rec["recording_id"]] = dict(path=baseline_rel, sha256=digest(root / baseline_rel))
        rows.extend(_quality_rows_for_record(rec, i, times, baseline_valid))
        guard.after_record(i, rec["recording_id"])
    receipt = dict(schema="eegt-validation-baseline-quality/v1", records=rows,
                   resources=guard.check(),
                   inputs={SOURCE_PATH: digest(root / SOURCE_PATH),
                           PROTOCOL_PATH: digest(root / PROTOCOL_PATH),
                           FREEZE_PATH: digest(root / FREEZE_PATH),
                           "results/013/qualification.json": digest(qualification_path)},
                   native_archives=native_archives, baseline_archives=baseline_archives,
                   runtime=_runtime("corpus"), elapsed_seconds=time.monotonic() - started,
                   maximum_rss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    atomic_json(root / "results/013/baseline-quality.json", receipt, immutable=True)
    return receipt


def inference_gates(rows, protocol):
    """Recompute each cohort from its own exact people and named nights."""
    counts = Counter((r["cohort"], r["source_subject"], r["session"])
                     for r in rows if r["status"] == "ELIGIBLE")
    minimum_blocks = protocol["quality"]["minimum_blocks_per_record"]
    minimum_people = protocol["quality"]["minimum_complete_participants"]
    gates = {}
    for cohort in protocol["cohorts"]:
        cid, people, sessions = cohort["id"], cohort["people"], cohort["sessions"]
        records = [dict(source_subject=person, session=session,
                        selected_blocks=counts[cid, person, session])
                   for person in people for session in sessions]
        complete = [person for person in people
                    if all(counts[cid, person, session] >= minimum_blocks for session in sessions)]
        gates[cid] = dict(status="READY" if len(complete) >= minimum_people else
                          "INSUFFICIENT_PARTICIPANTS",
                          complete_participants=complete,
                          complete_participant_count=len(complete),
                          minimum_blocks_per_night=minimum_blocks,
                          minimum_complete_participants=minimum_people,
                          records=records)
    return gates


def _checked_numeric(root, reference, expected_samples):
    path = _inside(root, reference["path"])
    if digest(path) != reference["sha256"]:
        raise ValueError("numeric handoff archive hash changed")
    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != {"samples_uv", "valid"}:
            raise ValueError("numeric handoff array names changed")
        samples, valid = archive["samples_uv"], archive["valid"]
    if (samples.dtype != np.float64 or valid.dtype != np.bool_ or
            samples.shape != valid.shape or samples.shape != (4, expected_samples)):
        raise ValueError("numeric handoff shape/dtype/mask changed")
    return samples, valid


def _checked_baseline(root, reference):
    path = _inside(root, reference["path"])
    if digest(path) != reference["sha256"]:
        raise ValueError("baseline handoff archive hash changed")
    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != {"times", "valid"}:
            raise ValueError("baseline handoff array names changed")
        times, valid = archive["times"], archive["valid"]
    baseline_counts(times, valid, blocks=1)
    return times, valid


def prepare_from_handoff(root, source, protocol, qualification, quality, *,
                         output_prefix="013", bindings=None, resource_guard=None):
    """Filter in the corpus runtime, then select with unchanged Experiment010 rule.

    This numerical core accepts a smaller, explicitly exposed fixture only
    through the separate fixture command. Normal callers validate the accepted
    freeze and exact 20-record source before invoking it.
    """
    from .distributed_study import selected_indices
    from .pretrained_study import array_hash, preprocess_block
    if resource_guard:
        verify_loaded_sources(resource_guard.seal)

    root = Path(root)
    source_rows, qualified = source["records"], qualification["records"]
    qrows = quality.get("records", [])
    if len(qualified) != len(source_rows) or len(qrows) != len(source_rows) * BLOCKS_PER_RECORD:
        raise ValueError("quality/qualification candidate census mismatch")
    rows, prepared, native, masks, indices = [], [], [], [], []
    started = time.monotonic()
    for record_index, (src, rec) in enumerate(zip(source_rows, qualified, strict=True)):
        if resource_guard:
            resource_guard.check()
        if any(rec.get(k) != src[k] for k in ("recording_id", "source_subject", "session", "cohort")):
            raise ValueError("qualification/source identity mismatch")
        rid = rec["recording_id"]
        if rec["status"] == "QUALIFIED":
            ref = quality.get("native_archives", {}).get(rid)
            baseline_ref = quality.get("baseline_archives", {}).get(rid)
            if not isinstance(ref, dict) or not isinstance(baseline_ref, dict):
                raise ValueError("qualified source lacks numeric/baseline handoff")
            samples, valid = _checked_numeric(root, ref,
                                              min(rec["samples_per_channel"], 4 * 3600 * RATE))
            expected_valid = np.isfinite(samples)
            for gap in rec.get("gaps", []):
                a, b = ((gap["start_sample"], gap["stop_sample"]) if isinstance(gap, dict)
                        else gap)
                if b > a:
                    expected_valid[:, max(0, a):min(samples.shape[1], b)] = False
            if not np.array_equal(valid, expected_valid):
                raise ValueError("native validity mask changed")
            times, baseline_valid = _checked_baseline(root, baseline_ref)
            expected_quality = _quality_rows_for_record(rec, record_index, times, baseline_valid)
        else:
            samples = valid = None
            expected_quality = _quality_rows_for_record(rec, record_index)
        group = []
        for block in range(BLOCKS_PER_RECORD):
            prior = qrows[record_index * BLOCKS_PER_RECORD + block]
            index = record_index * BLOCKS_PER_RECORD + block
            if (prior.get("candidate_index") != index or prior.get("recording_id") != rid or
                    prior.get("source_subject") != rec["source_subject"] or
                    prior.get("session") != rec["session"] or
                    prior.get("cohort") != rec["cohort"] or
                    prior.get("start_seconds") != block * 30 or
                    prior.get("stratum_index") != block // 40):
                raise ValueError("quality candidate identity/order mismatch")
            if (prior.get("baseline_valid_centers") != expected_quality[block]["baseline_valid_centers"] or
                    prior.get("reasons") != expected_quality[block]["reasons"]):
                raise ValueError("baseline quality/gap/short-support handoff changed")
            row = dict(prior)
            row["reasons"] = list(prior["reasons"])
            row.update(array_row=None, quality_status="FAIL", status="REJECTED",
                       prepared_array_sha256=None, native_array_sha256=None,
                       valid_mask_sha256=None)
            if samples is not None:
                start, stop = block * BLOCK_SAMPLES, (block + 1) * BLOCK_SAMPLES
                wave, mask = samples[:, start:stop], valid[:, start:stop]
                if wave.shape == (4, BLOCK_SAMPLES):
                    row["nonfinite_samples_per_channel"] = (~np.isfinite(wave)).sum(axis=1).tolist()
                    if not mask.all() and np.isfinite(wave).all() and not any(
                            reason in row["reasons"] for reason in ("NATIVE_GAP", "NATIVE_BOUNDARY")):
                        row["reasons"].append("INVALID_NATIVE_MASK")
                    try:
                        patch, peak = preprocess_block(wave, RATE)
                        row["preprocessed_peak_uv"] = peak
                    except ValueError as exc:
                        row["reasons"].append(str(exc))
                    else:
                        if not row["reasons"]:
                            row["quality_status"] = "PASS"
                            row["status"] = "QUALIFIED_UNSELECTED"
                            group.append((index, wave.copy(), mask.copy(), patch))
                elif "SHORT_SUPPORT" not in row["reasons"]:
                    raise ValueError("quality census failed to record short support")
            row["reasons"] = list(dict.fromkeys(row["reasons"]))
            rows.append(row)
        chosen = set(selected_indices(rows[-BLOCKS_PER_RECORD:]))
        for index, wave, mask, patch in group:
            if index not in chosen:
                continue
            if not mask.all() or not np.isfinite(wave).all():
                raise ValueError("selected native support is invalid")
            row = rows[index]
            row.update(status="ELIGIBLE", array_row=len(indices),
                       prepared_array_sha256=array_hash(patch),
                       native_array_sha256=array_hash(wave),
                       valid_mask_sha256=array_hash(mask))
            indices.append(index)
            prepared.append(patch)
            native.append(wave)
            masks.append(mask)
        if resource_guard:
            resource_guard.after_record(record_index, rid)
    prepared_array = (np.stack(prepared) if prepared else
                      np.empty((0, 4, 30, 200), dtype=np.float32))
    native_array = (np.stack(native) if native else
                    np.empty((0, 4, BLOCK_SAMPLES), dtype=np.float64))
    valid_array = (np.stack(masks) if masks else
                   np.empty((0, 4, BLOCK_SAMPLES), dtype=bool))
    selected_indices_array = np.asarray(indices, dtype=np.int64)
    native_rel = f"data/derived/{output_prefix}/native-selected.npz"
    prepared_rel = f"data/derived/{output_prefix}/prepared.npz"
    _save_numeric(root / native_rel, samples_uv=native_array, valid=valid_array,
                  candidate_indices=selected_indices_array)
    _save_numeric(root / prepared_rel, patches=prepared_array,
                  candidate_indices=selected_indices_array)
    qualified_count = sum(r["quality_status"] == "PASS" for r in rows)
    receipt = dict(schema="eegt-validation-prepared/v1", records=rows,
                   inputs=bindings or {},
                   source_hashes={r["path"]: r["sha256"] for r in qualified
                                  if r["status"] == "QUALIFIED"},
                   native_archives=quality.get("native_archives", {}),
                   baseline_archives=quality.get("baseline_archives", {}),
                   native_array_path=native_rel, native_array_sha256=digest(root / native_rel),
                   array_path=prepared_rel, array_sha256=digest(root / prepared_rel),
                   totals=dict(candidate_recordings=len(source_rows),
                               candidate_blocks=len(rows),
                               quality_qualified_blocks=qualified_count,
                               eligible_blocks=len(indices),
                               qualified_unselected_blocks=qualified_count-len(indices),
                               rejected_blocks=len(rows)-qualified_count),
                   rejection_counts=dict(Counter(reason for row in rows for reason in row["reasons"])),
                   inference_gates=inference_gates(rows, protocol),
                   runtime=_runtime("corpus"), elapsed_seconds=time.monotonic()-started,
                   maximum_rss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   discovery_contract="Only numeric arrays enter preprocessing/model/event functions; curator identities and cohorts remain in receipts.")
    if resource_guard:
        receipt["resources"] = resource_guard.check()
    validate_prepared(root, receipt, protocol, source, expected_records=len(source_rows))
    atomic_json(root / f"results/{output_prefix}/prepared.json", receipt, immutable=True)
    return receipt


def prepare_validation(root=ROOT):
    root = Path(root)
    seal, protocol, source = require_accepted_freeze(root, "corpus")
    qualification_path = root / "results/013/qualification.json"
    quality_path = root / "results/013/baseline-quality.json"
    qualification, quality = read(qualification_path), read(quality_path)
    _check_input_bindings(root, qualification)
    _check_input_bindings(root, quality)
    if (qualification.get("inputs", {}).get(SOURCE_PATH) != digest(root / SOURCE_PATH) or
            quality.get("inputs", {}).get("results/013/qualification.json") != digest(qualification_path)):
        raise ValueError("qualification or quality receipt input binding changed")
    _verify_qualification(source, qualification)
    return prepare_from_handoff(root, source, protocol, qualification, quality,
                                resource_guard=IntakeResources(root, seal, "prepare"),
                                bindings={SOURCE_PATH: digest(root / SOURCE_PATH),
                                          PROTOCOL_PATH: digest(root / PROTOCOL_PATH),
                                          FREEZE_PATH: digest(root / FREEZE_PATH),
                                          "results/013/qualification.json": digest(qualification_path),
                                          "results/013/baseline-quality.json": digest(quality_path)})


def validate_prepared(root, receipt, protocol, source, *, expected_records=20):
    """Recompute the full census, selection, gates and per-row numeric hashes."""
    from .distributed_study import selected_indices
    from .pretrained_study import array_hash

    root = Path(root)
    rows = receipt.get("records", [])
    if (len(source["records"]) != expected_records or
            len(rows) != expected_records * BLOCKS_PER_RECORD or
            [r.get("candidate_index") for r in rows] != list(range(len(rows)))):
        raise ValueError("prepared candidate census mismatch")
    for path, expected in receipt.get("inputs", {}).items():
        if digest(_inside(root, path)) != expected:
            raise ValueError(f"prepared input changed: {path}")
    for record_index, src in enumerate(source["records"]):
        for block in range(BLOCKS_PER_RECORD):
            row = rows[record_index * BLOCKS_PER_RECORD + block]
            if (any(row.get(k) != src[k] for k in ("recording_id", "source_subject", "session", "cohort")) or
                    row.get("start_seconds") != block * 30 or row.get("duration_seconds") != 30 or
                    row.get("stratum_index") != block // 40 or
                    row.get("quality_status") not in ("PASS", "FAIL") or
                    (row["quality_status"] == "PASS") != (not row.get("reasons"))):
                raise ValueError("prepared candidate identity or quality mismatch")
    chosen = set(selected_indices(rows))
    selected = [r for r in rows if r["status"] == "ELIGIBLE"]
    if [r["array_row"] for r in selected] != list(range(len(selected))):
        raise ValueError("selected array row order mismatch")
    for row in rows:
        expected = ("ELIGIBLE" if row["candidate_index"] in chosen else
                    "QUALIFIED_UNSELECTED" if row["quality_status"] == "PASS" else "REJECTED")
        if row["status"] != expected or (row["array_row"] is not None) != (expected == "ELIGIBLE"):
            raise ValueError("prepared time-stratified selection mismatch")
    if receipt["inference_gates"] != inference_gates(rows, protocol):
        raise ValueError("prepared cohort inference gate mismatch")
    native_path = _inside(root, receipt["native_array_path"])
    prepared_path = _inside(root, receipt["array_path"])
    if digest(native_path) != receipt["native_array_sha256"] or digest(prepared_path) != receipt["array_sha256"]:
        raise ValueError("selected numeric archive changed")
    with np.load(native_path, allow_pickle=False) as n, np.load(prepared_path, allow_pickle=False) as p:
        x, valid, ni = n["samples_uv"], n["valid"], n["candidate_indices"]
        patches, pi = p["patches"], p["candidate_indices"]
        expected_indices = np.asarray([r["candidate_index"] for r in selected], dtype=np.int64)
        if (x.shape != (len(selected), 4, BLOCK_SAMPLES) or x.dtype != np.float64 or
                valid.shape != x.shape or valid.dtype != np.bool_ or
                patches.shape != (len(selected), 4, 30, 200) or patches.dtype != np.float32 or
                ni.dtype != np.int64 or pi.dtype != np.int64 or
                not np.array_equal(ni, expected_indices) or not np.array_equal(pi, expected_indices) or
                not valid.all() or not np.isfinite(x).all() or not np.isfinite(patches).all()):
            raise ValueError("selected numeric shape, dtype, support or index mismatch")
        for row in selected:
            i = row["array_row"]
            if (array_hash(x[i]) != row["native_array_sha256"] or
                    array_hash(valid[i]) != row["valid_mask_sha256"] or
                    array_hash(patches[i]) != row["prepared_array_sha256"]):
                raise ValueError("selected per-row array hash mismatch")
    return receipt["inference_gates"]


def exposed_corpus_fixture(root, output):
    """Recompute only released 001/001 baseline validity into new scratch."""
    import mne

    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(root):
        raise FileExistsError("exposed fixture needs a new scratch destination outside the repo")
    p010 = read(root / "protocol/experiment-010.json")
    p008 = read(root / "protocol/experiment-008.json")
    if (p008["window_seconds"], p008["hop_seconds"]) != (2, .5):
        raise ValueError("released 008 baseline grid changed")
    if digest(root / "protocol/corpus-manifest-008.json") != p010["source"]["source_manifest_sha256"]:
        raise ValueError("exposed source manifest changed")
    qualification_path = root / p010["source"]["qualification"]
    if digest(qualification_path) != p010["source"]["qualification_sha256"]:
        raise ValueError("exposed qualification changed")
    old_qualified = read(qualification_path)["records"]
    matches = [r for r in old_qualified if (r["source_subject"], r["session"]) == ("001", "001")]
    if len(matches) != 1 or matches[0]["status"] != "QUALIFIED":
        raise ValueError("exposed 001/001 fixture unavailable")
    old = matches[0]
    if old["recording_id"] != "994b9095fb35625b16fd1e8f":
        raise ValueError("exposed fixture recording ID changed")
    raw_path = _inside(root, old["path"])
    if digest(raw_path) != old["sha256"]:
        raise ValueError("exposed source hash changed")
    features_receipt_path = root / "results/008/features.json"
    feature_rows = read(features_receipt_path)["records"]
    fr = next(r for r in feature_rows if r["recording_id"] == old["recording_id"])
    if digest(_inside(root, fr["path"])) != fr["sha256"]:
        raise ValueError("exposed baseline archive hash changed")
    raw = mne.io.read_raw_eeglab(raw_path, preload=False, verbose="ERROR")
    try:
        x = np.asarray(raw.get_data(picks=list(CHANNELS), start=0,
                                    stop=4 * 3600 * RATE) * 1e6, dtype=np.float64)
    finally:
        raw.close()
    if x.shape != (4, 4 * 3600 * RATE):
        raise ValueError("exposed source support changed")
    gaps = [tuple(g) for g in old.get("gaps", [])]
    valid = np.isfinite(x)
    for a, b in gaps:
        if b > a:
            valid[:, max(0, a):min(x.shape[1], b)] = False
    started = time.monotonic()
    times, baseline_valid = extract_baseline_valid(x, gaps)
    with np.load(root / fr["path"], allow_pickle=False) as prior:
        if (not np.array_equal(times, prior["times"]) or
                not np.array_equal(baseline_valid, prior["valid"])):
            raise ValueError("exposed 008 baseline time/valid parity failed")
    output.mkdir(parents=True)
    rid = old["recording_id"]
    native_rel = f"data/derived/exposed/native-first-four-hours/{rid}.npz"
    baseline_rel = f"data/derived/exposed/baseline-valid/{rid}.npz"
    _save_numeric(output / native_rel, samples_uv=x, valid=valid)
    _save_numeric(output / baseline_rel, times=times, valid=baseline_valid)
    rec = {**old, "cohort": "exposed_fixture"}
    protocol = dict(cohorts=[dict(id="exposed_fixture", people=["001"], sessions=["001"])],
                    quality=dict(minimum_blocks_per_record=3,
                                 minimum_complete_participants=3))
    source = dict(records=[dict(recording_id=rid, source_subject="001", session="001",
                                cohort="exposed_fixture")])
    qualification = dict(records=[rec])
    quality = dict(records=_quality_rows_for_record(rec, 0, times, baseline_valid),
                   native_archives={rid:dict(path=native_rel, sha256=digest(output / native_rel))},
                   baseline_archives={rid:dict(path=baseline_rel, sha256=digest(output / baseline_rel))})
    provenance = dict(schema="eegt-validation-exposed-fixture/v1", mode="EXPOSED_001_001_ONLY",
                      source_root=str(root), baseline_centers=len(times),
                      baseline_valid_centers=int(baseline_valid.sum()),
                      elapsed_seconds=time.monotonic()-started,
                      maximum_rss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      input_sha256={old["path"]: old["sha256"],
                                    fr["path"]: fr["sha256"],
                                    "results/008/features.json": digest(features_receipt_path),
                                    p010["source"]["qualification"]: digest(qualification_path),
                                    "results/010/prepared.json": digest(root / "results/010/prepared.json")},
                      runtime=_runtime("corpus"))
    for name, value in (("protocol", protocol), ("source", source),
                        ("qualification", qualification), ("quality", quality),
                        ("provenance", provenance)):
        atomic_json(output / f"{name}.json", value, immutable=True)
    return provenance


def exposed_prepare_fixture(root, output):
    """Reproduce 480 exposed candidate decisions and selected prepared bytes."""
    root, output = Path(root).resolve(), Path(output).resolve()
    provenance = read(output / "provenance.json")
    if (provenance.get("mode") != "EXPOSED_001_001_ONLY" or
            provenance.get("source_root") != str(root)):
        raise ValueError("exposed fixture provenance/root mismatch")
    for name, expected in provenance["input_sha256"].items():
        if digest(_inside(root, name)) != expected:
            raise ValueError(f"exposed fixture input changed: {name}")
    source, protocol = read(output / "source.json"), read(output / "protocol.json")
    qualification, quality = read(output / "qualification.json"), read(output / "quality.json")
    result = prepare_from_handoff(output, source, protocol, qualification, quality,
                                  output_prefix="exposed",
                                  bindings={name + ".json": digest(output / (name + ".json"))
                                            for name in ("provenance", "source", "protocol",
                                                         "qualification", "quality")})
    old = read(root / "results/010/prepared.json")
    old_rows = old["records"][:BLOCKS_PER_RECORD]
    for new, prior in zip(result["records"], old_rows, strict=True):
        for field in ("candidate_index", "start_seconds", "stratum_index",
                      "baseline_valid_centers", "nonfinite_samples_per_channel",
                      "quality_status", "status", "reasons", "preprocessed_peak_uv",
                      "prepared_array_sha256"):
            if new.get(field) != prior.get(field):
                raise ValueError(f"exposed 010 candidate {new['candidate_index']} {field} parity failed")
    selected = [r for r in result["records"] if r["status"] == "ELIGIBLE"]
    with np.load(output / result["array_path"], allow_pickle=False) as actual, \
         np.load(root / old["array_path"], allow_pickle=False) as previous:
        for row in selected:
            old_row = old_rows[row["candidate_index"]]
            if not np.array_equal(actual["patches"][row["array_row"]],
                                  previous["patches"][old_row["array_row"]]):
                raise ValueError("exposed selected prepared bytes changed")
    parity = dict(schema="eegt-validation-exposed-parity/v1", candidate_rows=480,
                  baseline_masks_equal=True, selected_rows=len(selected),
                  selected_prepared_bytes_equal=True,
                  old_prepared_sha256=digest(root / "results/010/prepared.json"),
                  new_prepared_sha256=digest(output / "results/exposed/prepared.json"),
                  runtime=_runtime("corpus"))
    atomic_json(output / "parity.json", parity, immutable=True)
    return parity
