# Experiment 005: Neurable acquisition pilot

Status: protocol prepared; physical recordings have not been acquired by EEGT.
The filename is a protocol, not evidence that the study ran.

## Outcome

Acquire repeatable, timestamped around-ear EEG with measured data loss and
contact quality. Determine whether the frozen transition detector survives a
new device and repeat sessions. This is an engineering and repeatability pilot,
not a diagnostic study or a test of what a person is thinking.

Neurable currently advertises a Research Kit with 12 EEG channels at 500 Hz,
raw EEG and accelerometer/gyroscope access. Its consumer FAQ distinguishes
consumer focus summaries from Research Kit raw streaming. These published
specifications are not proof that a usable kit is connected to this project.
Sources checked 2026-09-25: [Research Kit](https://www.neurable.com/products/research-kit)
and [FAQ](https://www.neurable.com/faqs).

## Acquisition sequence

1. Verify an actual raw Research Kit export or supported stream. Record device,
   firmware, exporter version, contact order, reference scheme, units, gain,
   sampling clock and missing-packet behavior. Preserve the native export and
   checksum it before conversion. Consumer focus scores cannot substitute for EEG.
2. Validate ten minutes of engineering capture. Confirm channel count, observed
   timestamps/sample count, units against exporter documentation, finite samples,
   discontinuities, and restart behavior. Unknown gain or contact order prevents
   admission into the numerical battery. Do not infer packet layout from a brand
   name or from the existing decoded-array adapter.
3. Start with one consenting adult and three sessions on different days. Each
   session includes five minutes of quiet sitting, five minutes of ordinary
   reading, and five minutes of an ordinary self-selected task. Repeat an earlier
   session's comfortable setting; take off and reseat the headset once, recording
   that boundary. End whenever the participant wishes. This estimates feasibility,
   not population generality.
4. After technical feasibility, expand to a target of ten adults with three
   sessions each, subject to actual participation and a suitable research/consent
   process. This is a planning target, not a power calculation or an acquired
   cohort. Never list participants who have not contributed data.
5. Freeze a discovery cohort before examining its waves. Reserve complete later
   participants and sessions for one-time evaluation. Count repeat sessions as
   sessions, not additional people. Record every exposure to a held-out set.

## Separate stores

- Raw: immutable export, native timestamps/counters, explicit missing-sample
  mask, technical capture sidecar, and checksum. A dropped interval is a gap;
  zero-filling or interpolation must not create an apparent transition.
- Discovery: EEG numeric arrays, sampling rate, and integrity mask only. The
  existing `mw75_decoded` interface validates a decoded 12-channel/500-Hz array;
  it does not establish live transport or calibrated hardware performance.
- Evaluation: randomized study key, session key, reseating/motion timestamps,
  optional event markers, and source-to-conversion provenance. Keep identities
  and consent records separately under the collection owner's access control.
  Public release of new participant data needs explicit participant permission;
  publish code, aggregate evidence and acquisition failures independently.
- Motion: if actually acquired by the kit, retain accelerometer/gyroscope as
  nuisance controls. Exclude them from EEG-only discovery. Do not claim those
  streams exist in cEEGrid files that do not contain them.

## Acceptance and stopping conditions

Every accepted recording has a parseable source, source hash, documented
calibration/contact order, duration reconciliation, gap mask, quality report,
and a reproducible numeric conversion. Report lost samples, valid minutes,
per-channel quality, and boundary distance from motion/reseating. Keep device
availability, successful connection, usable capture, numerical transfer and
semantic interpretation as separate statuses. The last two require their own
evidence and may fail despite a successful connection.

No acquisition is scheduled automatically, no people have been recruited by
this protocol, and no medical, emotional or identity labels enter discovery.
