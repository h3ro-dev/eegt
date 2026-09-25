"""Versioned raw-source catalog, resumable acquisition and continuous EEG inventory.

This is the curator side of EEGT. Source/participant metadata never enters a
discovery function. Published experiments 001 and 002 are not modified.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import time
import urllib.request
import warnings
import zipfile

from .acquire import ROOT, digest


def canonical_json(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"


def atomic_json(path, value, *, immutable=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = canonical_json(value)
    if immutable and path.exists():
        if path.read_text() != text:
            raise ValueError(f"refusing to change sealed artifact: {path}")
        return
    part = path.with_name(path.name + ".partial")
    part.write_text(text)
    part.replace(path)


def safe_path(root, relative):
    p = PurePosixPath(relative)
    if p.is_absolute() or not p.parts or ".." in p.parts or "\\" in relative:
        raise ValueError("unsafe source path")
    target = Path(root).joinpath(*p.parts)
    if not target.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError("source path escapes cache")
    return target


def annex_identity(pointer):
    match = re.search(r"(SHA256|MD5)E-s(\d+)--([a-f0-9]+)\.", pointer)
    if not match or len(match[3]) != {"SHA256": 64, "MD5": 32}[match[1]]:
        raise ValueError("unsupported upstream git-annex content identity")
    return dict(bytes=int(match[2]), algorithm=match[1].lower(), expected_digest=match[3])


def parse_channels(text):
    rows = list(csv.DictReader(io.StringIO(text.replace("\r\r\n", "\n")), delimiter="\t"))
    names = [r.get("name") for r in rows]
    if not rows or any(not n for n in names) or len(set(names)) != len(names):
        raise ValueError("empty or duplicated channel table")
    return rows


def fetch(url, *, maximum_bytes=25_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": "EEGT-corpus/0.3"})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read(maximum_bytes + 1)
    if len(data) > maximum_bytes:
        raise ValueError("metadata download exceeds bound")
    return data


def freeze(root=ROOT):
    root = Path(root)
    protocol_path = root / "protocol/corpus-v1.json"
    protocol = json.loads(protocol_path.read_text())
    out = root / "protocol/corpus-manifest-v1.json"
    if out.exists():
        m = json.loads(out.read_text())
        if m["protocol_sha256"] != digest(protocol_path):
            raise ValueError("corpus protocol changed after freeze")
        return m
    manifest = dict(schema="eegt-corpus-manifest/v1", protocol_sha256=digest(protocol_path),
                    sources=[], recordings=[], exclusions=[])
    for source in protocol["sources"]:
        ds, commit = source["dataset"], source["git_commit"]
        archive = fetch(f"https://codeload.github.com/OpenNeuroDatasets/{ds}/zip/{commit}")
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            files = {n.split("/", 1)[1]: n for n in z.namelist() if "/" in n and not n.endswith("/")}
            def read(path):
                return z.read(files[path]).decode("utf-8-sig")
            desc = json.loads(read("dataset_description.json"))
            if desc.get("License") != "CC0":
                raise ValueError("the two admitted snapshots must retain their declared CC0 terms")
            manifest["sources"].append(dict(**source, metadata=desc, readme=read("README"),
                archive_sha256=hashlib.sha256(archive).hexdigest(),
                participant_table_source_sha256=hashlib.sha256(read("participants.tsv").encode()).hexdigest()))
            raw_sets = sorted(p for p in files if p.startswith("sub-") and p.endswith("_eeg.set"))
            selected = [p for p in raw_sets if "cEEGrid" in p]
            for path in raw_sets:
                if path not in selected:
                    manifest["exclusions"].append(dict(dataset=ds,path=path,reason="NOT_AROUND_EAR_EEG"))
            for path in selected:
                prefix = path[:-len("_eeg.set")]
                subject = re.search(r"(?:^|/)sub-([^/]+)", path)[1]
                session = re.search(r"(?:^|/)ses-([^/]+)", path)
                native = json.loads(read(prefix + "_eeg.json"))
                channels_text = read(prefix + "_channels.tsv")
                channels = parse_channels(channels_text)
                files_out = []
                for extension in ("set", "fdt"):
                    file_path = prefix + "_eeg." + extension
                    files_out.append(dict(path=file_path, **annex_identity(read(file_path)),
                        url=f"https://s3.amazonaws.com/openneuro.org/{ds}/{file_path}"))
                if ds == "ds004015":
                    split = next(k for k, (a,b) in protocol["split"][ds].items() if a <= int(subject) <= b)
                else:
                    split = "external"
                rid = hashlib.sha256(f"{ds}:{commit}:{path}".encode()).hexdigest()[:24]
                manifest["recordings"].append(dict(recording_id=rid,dataset=ds,source_subject=subject,
                    subject_key=f"{ds}:sub-{subject}", session_id=session[1] if session else "unspecified",
                    split=split, prior_project_exposure=subject in protocol["split"]["prior_exposure"][ds],
                    metadata=native,channels=channels, files=files_out,
                    metadata_sha256=hashlib.sha256(canonical_json(native).encode()).hexdigest(),
                    channels_sha256=hashlib.sha256(channels_text.encode()).hexdigest()))
    manifest["total_download_bytes"] = sum(f["bytes"] for r in manifest["recordings"] for f in r["files"])
    manifest["source_recordings"] = len(manifest["recordings"])
    atomic_json(out, manifest, immutable=True)
    return manifest


def verified_file(path, file):
    return path.exists() and path.stat().st_size == file["bytes"] and digest(path, file["algorithm"]) == file["expected_digest"]


def acquire_file(file, destination, *, attempts=2):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not verified_file(destination, file):
            raise ValueError("existing cache bytes differ from pinned source; preserve for investigation")
        return digest(destination)
    part = destination.with_name(destination.name + ".partial")
    for attempt in range(attempts):
        try:
            start = part.stat().st_size if part.exists() else 0
            if start == file["bytes"]:
                if verified_file(part,file):
                    part.replace(destination)
                    return digest(destination)
                # Only unverified partial content is discarded on a checksum failure.
                part.unlink()
                start=0
            if start > file["bytes"]:
                raise ValueError("partial exceeds expected size")
            headers={"User-Agent":"EEGT-corpus/0.3"}
            if start: headers["Range"] = f"bytes={start}-"
            req=urllib.request.Request(file["url"],headers=headers)
            with urllib.request.urlopen(req,timeout=60) as response:
                if start and response.status == 206:
                    cr=response.headers.get("Content-Range", "")
                    if not cr.startswith(f"bytes {start}-"):
                        raise ValueError("incorrect resumed content range")
                else:
                    start=0
                received=start
                with part.open("ab" if start else "wb") as output:
                    while block := response.read(1024*1024):
                        received += len(block)
                        if received > file["bytes"]: raise ValueError("source download exceeded pinned bytes")
                        output.write(block)
            if not verified_file(part,file): raise ValueError("source size/checksum mismatch")
            part.replace(destination)
            return digest(destination)
        except (OSError,ValueError):
            if attempt+1 == attempts: raise
            time.sleep(1)
    raise RuntimeError("unreachable acquisition state")


def download(root=ROOT, *, max_bytes=100_000_000_000, workers=2):
    root=Path(root)
    manifest=freeze(root)
    if manifest["total_download_bytes"] > max_bytes: raise ValueError("manifest exceeds acquisition budget")
    cache=root/"data/cache"
    cache.mkdir(parents=True,exist_ok=True)
    needed=sum(f["bytes"] for r in manifest["recordings"] for f in r["files"]
               if not safe_path(cache/r["dataset"],f["path"]).exists())
    if shutil.disk_usage(cache).free < needed + 5_000_000_000: raise ValueError("insufficient storage for sources and derivative workspace")
    result=dict(schema="eegt-corpus-acquisition/v1",manifest_sha256=digest(root/"protocol/corpus-manifest-v1.json"),files=[])
    if workers not in (1,2): raise ValueError("acquisition supports one or two bounded streams")
    def task(rec,file):
        row=dict(recording_id=rec["recording_id"],dataset=rec["dataset"],path=file["path"],bytes=file["bytes"])
        try:
            row["sha256"]=acquire_file(file,safe_path(cache/rec["dataset"],file["path"]))
            row["status"]="VERIFIED"
        except (OSError,ValueError) as exc:
            row.update(status="QUARANTINED",reason=str(exc))
        return row
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending=[pool.submit(task,rec,file) for rec in manifest["recordings"] for file in rec["files"]]
        for future in as_completed(pending):
            row=future.result()
            result["files"].append(row)
            atomic_json(root/"results/corpus-v1/acquisition.json",result)
            print(json.dumps(row),flush=True)
    result["completed"] = True
    result["files"].sort(key=lambda r:(r["dataset"],r["path"]))
    result["verified_bytes"]=sum(x["bytes"] for x in result["files"] if x["status"]=="VERIFIED")
    atomic_json(root/"results/corpus-v1/acquisition.json",result)
    return result


DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE datasets (dataset_id TEXT PRIMARY KEY, version TEXT NOT NULL, git_commit TEXT NOT NULL, license TEXT NOT NULL, metadata_json TEXT NOT NULL);
CREATE TABLE recordings (recording_id TEXT PRIMARY KEY, dataset_id TEXT REFERENCES datasets(dataset_id), subject_key TEXT NOT NULL, source_subject TEXT NOT NULL, session_id TEXT NOT NULL, split TEXT NOT NULL, prior_exposure INTEGER NOT NULL CHECK(prior_exposure IN (0,1)), status TEXT NOT NULL, reason TEXT, sample_rate_hz REAL, samples_per_channel INTEGER, eeg_channels INTEGER, duration_seconds REAL, reference TEXT, metadata_json TEXT NOT NULL);
CREATE TABLE source_files (dataset_id TEXT NOT NULL REFERENCES datasets(dataset_id), path TEXT NOT NULL, recording_id TEXT NOT NULL REFERENCES recordings(recording_id), bytes INTEGER NOT NULL, source_hash_algorithm TEXT NOT NULL, source_digest TEXT NOT NULL, sha256 TEXT, status TEXT NOT NULL, PRIMARY KEY(dataset_id,path));
CREATE TABLE channels (recording_id TEXT REFERENCES recordings(recording_id), channel_index INTEGER, name TEXT, type TEXT, units TEXT, status TEXT, PRIMARY KEY(recording_id,channel_index));
CREATE TABLE discontinuities (recording_id TEXT REFERENCES recordings(recording_id), start_sample INTEGER NOT NULL, stop_sample INTEGER NOT NULL, kind TEXT NOT NULL, CHECK(stop_sample>=start_sample));
CREATE INDEX recording_group ON recordings(dataset_id,subject_key,session_id);
CREATE VIEW coverage AS SELECT dataset_id,status,COUNT(*) recordings,COUNT(DISTINCT subject_key) source_participant_records,COUNT(DISTINCT subject_key||':'||session_id) source_sessions,SUM(duration_seconds)/3600.0 recording_hours,SUM(samples_per_channel*eeg_channels) raw_eeg_values FROM recordings GROUP BY dataset_id,status;
"""


def connect_catalog(path):
    connection=sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def qualify(root=ROOT):
    import mne
    import numpy as np
    root=Path(root)
    manifest=freeze(root)
    acquisition=json.loads((root/"results/corpus-v1/acquisition.json").read_text())
    if acquisition["manifest_sha256"] != digest(root/"protocol/corpus-manifest-v1.json") or not acquisition.get("completed"):
        raise ValueError("acquisition incomplete or manifest mismatch")
    receipts={(r["dataset"],r["path"]):r for r in acquisition["files"]}
    out=root/"results/corpus-v1"
    final=out/"corpus.sqlite"
    if final.exists(): raise ValueError("catalog is immutable; use a fresh run directory for a new qualification")
    temporary=out/"corpus.sqlite.partial"
    if temporary.exists(): temporary.unlink()
    conn=connect_catalog(temporary)
    conn.executescript(DDL)
    conn.execute("INSERT INTO meta VALUES (?,?)",("schema","eegt-corpus/v1"))
    conn.execute("INSERT INTO meta VALUES (?,?)",("manifest_sha256",digest(root/"protocol/corpus-manifest-v1.json")))
    conn.execute("INSERT INTO meta VALUES (?,?)",("code_sha256",digest(Path(__file__))))
    for src in manifest["sources"]:
        conn.execute("INSERT INTO datasets VALUES (?,?,?,?,?)",(src["dataset"],src["version"],src["git_commit"],src["metadata"]["License"],canonical_json(src["metadata"])))
    records=[]
    for rec in manifest["recordings"]:
        rid=rec["recording_id"]
        result=dict(recording_id=rid,dataset=rec["dataset"],subject_key=rec["subject_key"],split=rec["split"],status="QUALIFIED",reason=None)
        raw=None
        boundaries=[]
        observed_rate=None; n_samples=None; duration=None; eeg=[]
        try:
            for file in rec["files"]:
                receipt=receipts[(rec["dataset"],file["path"])]
                path=safe_path(root/"data/cache"/rec["dataset"],file["path"])
                if receipt["status"]!="VERIFIED" or not verified_file(path,file) or digest(path)!=receipt["sha256"]:
                    raise ValueError("unverified or altered source payload")
            eeg=[c for c in rec["channels"] if c["type"].upper()=="EEG"]
            if len(eeg)<2 or any(c["units"] not in ["microV","uV","µV"] for c in eeg):
                raise ValueError("unsupported channel count or units")
            source=safe_path(root/"data/cache"/rec["dataset"],rec["files"][0]["path"])
            with warnings.catch_warnings(record=True) as caught:
                raw=mne.io.read_raw_eeglab(source,preload=False,verbose="ERROR")
            result["decoder_warnings"]=[str(w.message) for w in caught]
            observed_rate=float(raw.info["sfreq"]); n_samples=int(raw.n_times)
            if observed_rate < 100 or observed_rate!=rec["metadata"]["SamplingFrequency"]:
                raise ValueError("unsupported or mismatched sampling rate")
            if len(eeg)!=rec["metadata"]["EEGChannelCount"] or not set(c["name"] for c in eeg).issubset(raw.ch_names):
                raise ValueError("declared and observed channels disagree")
            if len(set(raw.ch_names))!=len(raw.ch_names): raise ValueError("duplicate source channel names")
            duration=n_samples/observed_rate
            result["duration_metadata_error_samples"]=float(n_samples-rec["metadata"]["RecordingDuration"]*observed_rate)
            if abs(result["duration_metadata_error_samples"])>1.01: raise ValueError("duration discrepancy greater than one sample")
            for onset,span,desc in zip(raw.annotations.onset,raw.annotations.duration,raw.annotations.description,strict=True):
                if "boundary" in desc.lower() or desc.lower().startswith("bad"):
                    a=max(0,min(n_samples,int(np.floor(onset*observed_rate))))
                    b=max(a,min(n_samples,int(np.ceil((onset+max(0,span))*observed_rate))))
                    boundaries.append((rid,a,b,"BOUNDARY" if "boundary" in desc.lower() else "BAD_INTERVAL"))
            result.update(sample_rate_hz=observed_rate,samples_per_channel=n_samples,eeg_channels=len(eeg),duration_seconds=duration,discontinuities=len(boundaries))
        except Exception as exc:
            result.update(status="QUARANTINED",reason=f"{type(exc).__name__}: {exc}")
            observed_rate=None;n_samples=None;duration=None;boundaries=[]
        finally:
            if raw is not None: raw.close()
        conn.execute("INSERT INTO recordings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,rec["dataset"],rec["subject_key"],rec["source_subject"],rec["session_id"],rec["split"],int(rec["prior_project_exposure"]),result["status"],result["reason"],observed_rate,n_samples,len(eeg),duration,str(rec["metadata"].get("EEGReference","UNKNOWN")),canonical_json(rec["metadata"])))
        for file in rec["files"]:
            receipt=receipts[(rec["dataset"],file["path"])]
            conn.execute("INSERT INTO source_files VALUES (?,?,?,?,?,?,?,?)",(rec["dataset"],file["path"],rid,file["bytes"],file["algorithm"],file["expected_digest"],receipt.get("sha256"),receipt["status"]))
        for i,c in enumerate(rec["channels"]):
            conn.execute("INSERT INTO channels VALUES (?,?,?,?,?,?)",(rid,i,c["name"],c["type"],c["units"],c.get("status","unknown")))
        conn.executemany("INSERT INTO discontinuities VALUES (?,?,?,?)",boundaries)
        conn.commit()
        records.append(result)
        print(json.dumps(result),flush=True)
    if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or conn.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("database integrity failed")
    conn.row_factory=sqlite3.Row
    coverage=[dict(row) for row in conn.execute("SELECT * FROM coverage ORDER BY dataset_id,status")]
    duplicates=[dict(row) for row in conn.execute("SELECT sha256,COUNT(*) n FROM source_files WHERE path LIKE '%.fdt' AND sha256 IS NOT NULL GROUP BY sha256 HAVING COUNT(*)>1")]
    conn.close()
    temporary.replace(final)
    summary=dict(schema="eegt-corpus-summary/v1",records=records,coverage=coverage,duplicate_payload_groups=duplicates,
        downloaded_verified_bytes=acquisition["verified_bytes"],source_recordings=manifest["source_recordings"],
        qualified_recordings=sum(r["status"]=="QUALIFIED" for r in records),
        corpus_sha256=digest(final),manifest_sha256=digest(root/"protocol/corpus-manifest-v1.json"),
        limitations=["Source participant records are not a verified cross-dataset unique-person census.",
            "Recorded samples are not necessarily continuous wall-clock time: logged discontinuities are preserved; undocumented gaps are unknown.",
            "Full source acquisition is distinct from analyzed exposure and valid exposure.",
            "These are cEEGrid recordings, not physical Neurable recordings."])
    atomic_json(out/"summary.json",summary,immutable=True)
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["freeze","download","qualify"])
    parser.add_argument("--root",type=Path,default=ROOT)
    parser.add_argument("--max-bytes",type=int,default=100_000_000_000)
    args=parser.parse_args()
    if args.action=="freeze":
        m=freeze(args.root);print(json.dumps({k:m[k] for k in ["source_recordings","total_download_bytes"]}))
    elif args.action=="download":download(args.root,max_bytes=args.max_bytes)
    else:qualify(args.root)
