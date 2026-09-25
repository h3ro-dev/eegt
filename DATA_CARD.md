# Data card: Experiment 002

This is a fixed, small around-ear EEG pilot, not a representative population sample or a diagnostic dataset. Sources are publicly released pseudonymous recordings. Excluding explicit identity metadata does not guarantee that neural or hardware signals carry no identifying information.

## Source data

The pinned publisher metadata for **OpenNeuro ds004015 v1.0.2** and **ds005207 v1.0.0** declare **CC0**. Code has an independent MIT license; it does not relicense third-party data. EEGT's derived numeric arrays, token assignments and numeric codebooks from these CC0 sources are released under CC0-1.0. Source authors and citations are retained in `protocol/source-manifest.json`. Source bytes are obtained from the public OpenNeuro S3 bucket and checked against the Git-annex MD5/SHA256 identities at pinned Git commits; every downloaded file also receives a SHA256 receipt.

- ds004015: first six public subjects in identifier order, native 500 Hz, 18 around-ear channels; https://openneuro.org/datasets/ds004015/versions/1.0.2 ; https://doi.org/10.3389/fnins.2022.869426 .
- ds005207: first two available public cEEGrid subjects, native 250 Hz, 15 and 12 EEG channels. IMU channels excluded from token discovery; https://openneuro.org/datasets/ds005207/versions/1.0.0 ; https://doi.org/10.1111/jsr.12786 . The source reports lost cEEGrid–PSG alignment. No PSG, sleep stages or claimed aligned labels are used. Its generic 10/20 placement metadata is not used to invent electrode positions.

These are cEEGrid recordings, not MW75 recordings. Both measure around-ear voltages, but their electrode contacts, reference, amplifier, environment and source tasks differ from a Neurable headset. A common passband and sampling rate do not erase those differences. MW75 Research Kit compatibility currently means an explicitly tested **decoded input interface** (12 ordered channels, 500 Hz, microvolts, integrity); physical hardware validation is unperformed.

## Selection and transformations

Eight full recordings (16 SET/FDT files), **2,769,602,360 bytes**, are downloaded. A fixed 600-second slice starts 60 seconds into each. This is **80 recording-minutes**, with **40,500 two-second channel windows**; simultaneous channels are separate windows, not independent participants. The 3/1/2 train/validation/test subjects from ds004015 and two external ds005207 subjects are disjoint by public IDs. Cross-dataset real-person overlap cannot be verified from pseudonyms. No hyperparameter or model is selected from the validation set in this pilot.

The native sliced microvolt arrays are exported unchanged at float32 source precision. The analysis arrays explicitly receive mean removal, fourth-order 1–40 Hz forward/backward filtering with a fixed half-second padding duration, and polyphase resampling to 100 Hz. Window edge effects remain. The raw downloads remain independently available upstream. Filter/resampling documentation and a prefit padding clarification are in `protocol/`.

QC withholds incomplete, invalid/nonfinite, flat, high-amplitude or line-dominated windows. Thresholds are engineering choices; passing is not proof of clean brain signal. ADC clipping is **unknown** because rail information is absent, rather than inferred from large amplitude. Reason counts may overlap; pass+abstain is the exclusive total. `results/002/windows.csv.gz` records every window, including withheld ones.

## Files and separation

- `native-slices.npz`: numeric native EEG samples, sample rates and integrity arrays, indexed by recording integer; release asset.
- `analysis-waves.npz`: 200-sample, 100 Hz analysis windows after QC and explicit transforms; release asset.
- `results/002/provenance.json`: separate mapping to source pseudonyms, channel order, reference and splits; never fed into discovery.
- `results/002/evaluation-index.npz`: grouping used by evaluation, outside model inputs.
- `results/002/prepared-inputs.json`: digest binding of the prepared waves, evaluation index, QC/window ledger, provenance and source/protocol manifests. Evaluation requires identical window IDs and rejects modified or mixed files before fitting.
- `results/002/window-hashes.csv.gz`: SHA256 for every native two-second window represented as calibrated little-endian float32 microvolts, including withheld windows. This corresponds to the native-slice export precision, not a hash of the original file's encoded byte offsets.
- `results/002/assignments.npz`: aligned original window indices, neutral integer assignments, and Boolean acceptance masks for all 27 models. An assignment exists for every QC-passing window; only a true acceptance mask means a token passes the training-distance threshold.
- `results/002/models.npz`: numeric centroids, train-fitted transforms and thresholds; no executable pickle.
- `results/002/metrics.json`: all settings, group denominators, controls, agreement, versions and hashes.

Use `numpy.load(..., allow_pickle=False)`. Do not interpret token IDs as interchangeable across models. Compare partitions with the published permutation-invariant metrics. Do not infer thoughts, emotions, attention, sleep states, medical conditions or identity from these exploratory tokens.
