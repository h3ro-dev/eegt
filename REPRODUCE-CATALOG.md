# Rebuild the consolidated EEGT catalog

Version 0.10.0 catalog reproduction. The independent review accompanies the immutable candidate snapshot, whose historical status fields are preserved.

The catalog is a curator index of accepted numerical releases. Rebuilding it reads receipts and SQLite rows; it does not decode EEG, regenerate events, run encoders or acquire new participants. Large event ledgers stay in their own immutable releases. Source-local people are scoped to dataset and must not be summed as globally unique people.

Download the complete `eegt-v0.10.0-catalog` assets, manifest and SHA256SUMS, then verify every checksum. Use the versioned `extract_event_assets.py`, verifying its SHA256 against the manifest before executing it. Extract once into a new directory. The extractor rejects unexpected, missing or changed members and unsafe paths.

From the extracted `workspace` directory, with Python 3.11 or newer:

```sh
python3 work/database-release/build_database.py \
  --manifest work/database-release/final/catalog-input.json \
  --root . \
  --destination catalog-rebuilt.sqlite > catalog-rebuilt-summary.json
```

The destination must not already exist. Compare the rebuilt summary to `work/database-release/final/catalog-summary.json`; the input-manifest and logical-content hashes must match, together with all coverage/source totals and original receipt rows. The downloaded database file must match its published file checksum. SQLite records its writer version and page layout in the database file ([official file-format specification](https://www.sqlite.org/fileformat.html)). A rebuild can therefore have different SQLite page bytes or header version across runtimes; compare all summary fields except `database_sha256` and retain that distinct rebuilt file hash. The logical hash covers every user schema definition and every table row as sorted canonical JSON. Inspect `PRAGMA integrity_check` and `PRAGMA foreign_key_check`, then run the examples in `QUERIES.md`. Every normalized source, experiment and result row retains the exact source receipt. Missing fields stay null; unavailable p-values and unqualified recordings do not become zeros or disappear.

The package retains the input paths beneath `workspace` so all original hash bindings remain meaningful. Do not flatten its directories or modify receipts. To create a genuinely new catalog version, produce a new input manifest and review it independently; never overwrite a released version.

Recorded source hours, candidate windows, selected support and independent people have different denominators. Experiment joins add no source recordings or hours. This database contains numerical pattern evidence; no universal vocabulary, semantic decoder, diagnostic performance or physical Neurable equivalence has been established. A DOI-ready metadata file is preparation only; an identifier remains NOT_ISSUED until an actual deposit is verified.
