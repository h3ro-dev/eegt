# Offline Experiment 012 timing-control packet — pre-release plan

**Current state:** explicit file plan and relocation adapter prepared for independent review. No offline empirical replay, final archive, external send or publication is authorized by this document. The accepted source, protocol, control, empirical and replication files stay byte-for-byte unchanged.

The packet preserves the project's relative layout so the frozen `empirical_null.py` imports its unchanged `eegt.waveform_events` matcher and `null_controls` helper. Its `PROTOCOL.json` intentionally retains original absolute provenance paths and hash seals. `replay_adapter.py` verifies the frozen protocol, review, all 12 protocol source files, 24 selected compressed event partitions, 26 metadata/catalog inputs and every explicitly listed support file. It maps the provenance paths to the corresponding packet-relative locations and calls the unchanged runner's `evaluate_row` on the fixed twelve rows. It compares every returned row object, including all 99 null draws at 10/25/50 ms, plus the six-person descriptive summary, to the original accepted stage receipts. It writes a **new** `work/next-study/release/replay/EMPIRICAL-REPLAY.json`; it never invokes the frozen runner's original stage entry point or writes its `FIRST-UNIT.json` or `REMAINING.json`. Relocation changes file lookup only, not seeds, timing bins, tolerance, matched support, event selection, or scientific computation.

`FILE-MANIFEST.json` is the exact allowlist and authority for file count and byte sizes. Its categories are 12 protocol-pinned sources, 24 selected event partitions, 26 capacity-pinned metadata/catalog inputs, and the explicit support paths in `build_packet.py`, totaling roughly **519 MB** before compression. There is no recursive copy or glob. The package contains no private tree, vendor/mailbox receipt, raw waveform array, model weight, personal recording/media or credential. The accepted `analysis.sqlite` is copied whole, read-only in the packet, at its original relative path; the builder never edits, vacuums or subsets it. The optional density figure is derived only from saved receipts and includes the PNG, SVG, figure script and hash manifest. The 110 other exposed selected blocks' event partitions and all reserved waveforms are absent, and those blocks receive no new timing-control analysis; the full accepted index and summary still contain their original release receipts. A gzip level-1 sizing pass compressed the 468,275,200-byte analysis index to 45,699,396 bytes and the 14,528,512-byte catalog to 1,837,432 bytes. This gives a conservative **~84 MB** estimate before compressing the remaining files; the final archive size will be recorded after review.

From the original project root, using the existing Python 3.12.12 environment, the **planning** commands are:

```sh
python work/next-study/release/build_packet.py plan
python work/next-study/release/build_packet.py verify
```

After independent privacy and adapter review, `python work/next-study/release/build_packet.py build` copies the allowlist into `work/next-study/release/stage/packet/` and verifies every copied hash. It refuses an existing destination. The builder also copies `FILE-MANIFEST.json` into the packet. The planned final archive name is `eegt-v0.11.0-controls.tar.gz`; tar creation and final checksum are separate release steps after replay and release review. This script does not publish or archive anything.

For **offline replay after independent adapter acceptance**, supply Python 3.12.12 with NumPy 2.5.3 and SciPy 1.18.1. The accepted local environment also has SQLite 3.50.4. All five numerical thread variables must equal one before starting the process; no package download or environment installation is performed by this packet. The figure script alone optionally uses Matplotlib 3.11.2. On a POSIX runtime supporting `resource.RLIMIT_CPU` and `SIGXCPU`, run one process at a time from the extracted packet root:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
python work/next-study/release/replay_adapter.py verify
python work/next-study/release/replay_adapter.py metadata
python work/next-study/release/replay_adapter.py empirical
```

`verify` hashes the complete allowlist without reading compressed event bodies. `metadata` invokes the unchanged `audit_capacity.py` against its 26 pinned metadata/catalog inputs, redirects only its output into `work/next-study/release/replay/metadata/CAPACITY.json`, and requires a byte-for-byte match to the accepted capacity receipt. It never opens an EEG payload. `empirical` opens only the pinned accepted 012 event partitions and read-only analysis index, sets the accepted 7,200 CPU-second hard limit with a 7,190-second soft signal, checks CPU before draws at 6,900 seconds and checks RSS against 2 GiB. A caught stop or row mismatch leaves a failure receipt and names unrun rows. Every replay output uses exclusive creation to preserve earlier evidence. Do not launch a second numerical process concurrently.

The replay tests *reproducibility of this fixed, exposed, exploratory twelve-block analysis*. The timing null preserves coarse 1-second-bin counts while removing fine within-bin timing and other waveform constraints. A matching replay is not new independent data, a significance result, physiological attribution, or replication on untouched people. EESM19 capacity is metadata-only: nine recorded-unexposed ear-only candidate people (108 sessions) or nineteen PSG-session ear-contact candidates (76 sessions), with eligibility and power still unestablished. The original broader Experiment 012 metric remains unchanged.
