# Research Notes · Experiment 008

Date: 2026-09-25. State: computed; publication and review evidence accompany the release.

Twelve newly selected ear-EEG recordings from six source participants add **86.38 qualified recorded hours**. We analyze the first four hours of each file: **48 hours**, **345,564 overlapping multichannel windows**, and **306,392 QC-passing windows**. The full index now has **66 qualified recordings** and **309.85 recorded hours** across three datasets.

Same-participant nights are closer on average in all three views. Waveform shape has the smallest raw pairing p, but all three adjusted p values exceed 0.05. This first six-person battery gives a limited recurrence signal, not decisive evidence of stable universal tokens.

Source: [EESM23 / OpenNeuro ds005178 v1.0.0](https://openneuro.org/datasets/ds005178/versions/1.0.0), commit `a57deb78cf1294497db88d73aaed06813850f236`, CC0. It exports RB, RT, LB and LT at 250 Hz, with an average reference. Any other native channel (including ELE) is excluded. The study is described by [Mikkelsen and colleagues, 2025](https://doi.org/10.1038/s41597-025-04579-8). This in-ear montage is not a Neurable headset or a cEEGrid-equivalent acquisition.

## Repeat-night comparison

| View | Pairs | Same-person distance | Different-person distance | Exact pairing p | Adjusted p (3 views) |
|---|---|---|---|---|---|
| Waveform shape | 6 | 0.554 | 0.766 | 0.0306 | 0.0917 |
| Spectrum | 6 | 0.529 | 0.621 | 0.0944 | 0.2833 |
| Sensor coordination | 6 | 0.552 | 0.676 | 0.1847 | 0.5542 |

Distances compare per-recording feature medians, in the frozen cEEGrid training coordinates, between the first two nights. Smaller means more similar within that view. These are session summaries, not matches between individual wave events or validated tokens. Distances cannot be compared across views as if they shared one universal coordinate system.

The test enumerates every assignment of night-two summaries to night-one participants (720 assignments for six complete pairs). A low pairing p means the observed pairing is unusually close under that permutation model. It does not identify the cause: anatomy, electrode fit, reference and stable artifacts may contribute. Six selected participants do not support a population-wide universality claim; the adjustment covers the three prespecified primary views.

Experiment008 adds an exact session-pairing permutation comparison; it does not rerun the Fourier-phase battery from Experiment006 on these new files. Session recurrence alone cannot distinguish neural structure from persistent measurement effects.

## Every analyzed recording

| Source participant | Night | QC-pass / all windows | QC-pass fraction | Shape changes/min | Spectrum changes/min | Coordination changes/min |
|---|---|---|---|---|---|---|
| 001 | 001 | 27,916/28,797 | 96.9% | 5.248 | 1.114 | 1.225 |
| 001 | 002 | 27,857/28,797 | 96.7% | 4.924 | 1.046 | 0.821 |
| 002 | 001 | 28,217/28,797 | 98.0% | 7.862 | 18.973 | 3.581 |
| 002 | 002 | 27,809/28,797 | 96.6% | 9.536 | 6.540 | 6.915 |
| 003 | 001 | 27,992/28,797 | 97.2% | 8.024 | 7.545 | 3.933 |
| 003 | 002 | 28,020/28,797 | 97.3% | 7.186 | 4.451 | 2.201 |
| 004 | 001 | 27,864/28,797 | 96.8% | 10.100 | 12.979 | 3.420 |
| 004 | 002 | 23,832/28,797 | 82.8% | 12.013 | 8.665 | 3.285 |
| 005 | 001 | 22,851/28,797 | 79.4% | 5.605 | 6.088 | 6.438 |
| 005 | 002 | 27,987/28,797 | 97.2% | 8.134 | 10.771 | 4.572 |
| 006 | 001 | 19,646/28,797 | 68.2% | 12.117 | 3.782 | 5.941 |
| 006 | 002 | 16,401/28,797 | 57.0% | 12.327 | 4.069 | 4.428 |

Changes/minute use eligible scored-window centers, not all wall-clock minutes. QC fraction is accepted windows divided by all candidate windows; neither percentage is diagnostic accuracy.

The numerical methods receive only wave arrays, sampling rate and technical validity. The evaluator uses anonymous source grouping keys to pair nights after descriptors are fixed. No sleep stages, diaries, demographic fields or clinical labels enter the analysis. The first four hours can include calibration and wakefulness; we do not label them as four hours of sleep.

Four remaining participants are untouched by waveform analysis. The other ten sessions of each exposed participant also remain reserved, but they would be new-session tests, not new-person tests. All six participants and the 12 analyzed recordings are now exposed for future claims.

Digital conversion was checked against native values at three deterministic positions in each file. This is a decoding check, not physical amplifier calibration. Native gaps are preserved; undocumented gaps remain unknown. Every candidate passed source qualification; pair eligibility is reported separately in the JSON.

[Frozen protocol](../protocol/experiment-008.json) · [Source manifest](../protocol/corpus-manifest-008.json) · [Qualification](../results/008/qualification.json) · [Per-record and pairing results](../results/008/summary.json) · [Expanded database index](../results/corpus-v2/summary.json) · [Release](https://github.com/h3ro-dev/eegt/releases/tag/v0.4.0)
