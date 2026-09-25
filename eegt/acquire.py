"""Pinned OpenNeuro sources, bounded streaming download, immutable receipts."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fetch_bytes(url):
    request = urllib.request.Request(url, headers={"User-Agent": "EEGT-reproducible-research/0.2"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def create_manifest():
    protocol = json.loads((ROOT / "protocol/experiment-002.json").read_text())
    rows = []
    descriptions = []
    for source in protocol["sources"]:
        ds, commit = source["dataset"], source["git_commit"]
        base = f"https://raw.githubusercontent.com/OpenNeuroDatasets/{ds}/{commit}/"
        description = json.loads(fetch_bytes(base + "dataset_description.json"))
        if description.get("License") != "CC0":
            raise ValueError("source terms differ from the frozen CC0 source declaration")
        descriptions.append(dict(dataset=ds, git_commit=commit, description=description,
                                 readme=fetch_bytes(base + "README").decode()))
        for subject, split in zip(source["subjects"], source["splits"], strict=True):
            s = f"sub-{subject}"
            prefix = (f"{s}/eeg/{s}_task-AttendedSpeakerParadigmcEEGridAttention" if ds == "ds004015"
                      else f"{s}/ses-001/eeg/{s}_ses-001_task-sleep_acq-cEEGrid")
            metadata = json.loads(fetch_bytes(base + prefix + "_eeg.json"))
            channel_tsv = fetch_bytes(base + prefix + "_channels.tsv").decode()
            files = []
            for extension in ["set", "fdt"]:
                path = prefix + "_eeg." + extension
                annex = fetch_bytes(base + path).decode().strip()
                match = re.search(r"(SHA256|MD5)E-s(\d+)--([a-f0-9]+)\.", annex)
                if not match:
                    raise ValueError(f"unrecognized annex identity: {path}")
                files.append(dict(path=path, bytes=int(match[2]), algorithm=match[1].lower(),
                                  expected_digest=match[3], annex=annex,
                                  url=f"https://s3.amazonaws.com/openneuro.org/{ds}/{path}"))
            rows.append(dict(recording=f"r{len(rows) + 1:03}", dataset=ds, subject=subject,
                             split=split, git_commit=commit, metadata=metadata,
                             channels_tsv=channel_tsv, files=files))
    result = dict(schema="eegt-source-manifest/v2", protocol_sha256=digest(ROOT / "protocol/experiment-002.json"),
                  dataset_descriptions=descriptions, recordings=rows,
                  total_download_bytes=sum(f["bytes"] for r in rows for f in r["files"]))
    if result["total_download_bytes"] > 3_000_000_000:
        raise ValueError("source manifest exceeds the initial 3 GB budget")
    path = ROOT / "protocol/source-manifest.json"
    text = json.dumps(result, indent=2) + "\n"
    if path.exists() and path.read_text() != text:
        raise ValueError("refusing to replace an existing different source manifest")
    path.write_text(text)
    print(json.dumps(dict(state="manifest_frozen", recordings=len(rows), bytes=result["total_download_bytes"],
                          sha256=digest(path))), flush=True)


def download():
    manifest = json.loads((ROOT / "protocol/source-manifest.json").read_text())
    receipt = []
    for row in manifest["recordings"]:
        for file in row["files"]:
            dest = ROOT / "data/cache" / row["dataset"] / file["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                part = dest.with_suffix(dest.suffix + ".partial")
                print(json.dumps(dict(state="downloading", recording=row["recording"],
                                      file=dest.name, bytes=file["bytes"])), flush=True)
                with urllib.request.urlopen(file["url"], timeout=120) as response, part.open("wb") as output:
                    received = 0
                    while block := response.read(1024 * 1024):
                        received += len(block)
                        if received > file["bytes"]:
                            raise ValueError("download exceeds pinned size")
                        output.write(block)
                if part.stat().st_size != file["bytes"] or digest(part, file["algorithm"]) != file["expected_digest"]:
                    raise ValueError(f"source checksum/size mismatch: {dest.name}")
                part.replace(dest)
            if dest.stat().st_size != file["bytes"] or digest(dest, file["algorithm"]) != file["expected_digest"]:
                raise ValueError(f"cached file checksum/size mismatch: {dest.name}")
            receipt.append(dict(recording=row["recording"], dataset=row["dataset"], path=file["path"],
                                bytes=dest.stat().st_size, sha256=digest(dest),
                                upstream_algorithm=file["algorithm"], upstream_digest=file["expected_digest"]))
            print(json.dumps(dict(state="verified", recording=row["recording"], file=dest.name)), flush=True)
    out = ROOT / "results/002"
    out.mkdir(parents=True, exist_ok=True)
    (out / "acquisition.json").write_text(json.dumps(dict(schema="eegt-acquisition/v2", files=receipt,
        total_bytes=sum(r["bytes"] for r in receipt), source_manifest_sha256=digest(ROOT / "protocol/source-manifest.json")), indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["manifest", "download"])
    args = parser.parse_args()
    create_manifest() if args.action == "manifest" else download()
