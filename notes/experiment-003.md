# Research Notes · Experiment 003

Date: 2026-09-25. State: numerical transition analysis computed.

We measure changes in waveform morphology, spectrum and sensor coordination at 0.5-, 2- and 8-second context scales, using two-second windows stepped every half-second. A training-only median/IQR reference and training 95th-percentile threshold are fixed before evaluation. Primary results use the 2-second context; all scales remain in the database. Geometry records pre/post distance, trajectory length, speed, angle and endpoint return distance. These are multivariate changes, not raw-wave mathematical inflection points, inferred recovery or millisecond microstates.

These are LLM-authored numerical representations, not independent pretrained LLMs discovering a language. F1 measures timing agreement within one second; it is not accuracy against brain-state labels. Neither high agreement nor a change score establishes semantic meaning, a diagnosis or universal geometry.

| Group | Records | Valid/all multichannel windows | Shape / spectrum F1 | Shape / coordination F1 | Spectrum / coordination F1 |
| --- | --- | --- | --- | --- | --- |
| train | 24 | 230,452/232,332 | 0.387 [0.335, 0.432]; n=24 | 0.453 [0.418, 0.511]; n=24 | 0.341 [0.287, 0.396]; n=24 |
| validation | 6 | 53,765/54,089 | 0.400 [0.316, 0.460]; n=6 | 0.474 [0.322, 0.550]; n=6 | 0.400 [0.287, 0.504]; n=6 |
| test | 6 | 53,535/53,802 | 0.270 [0.213, 0.347]; n=6 | 0.369 [0.277, 0.470]; n=6 | 0.288 [0.220, 0.300]; n=6 |
| external_exposed | 2 | 121,110/175,610 | 0.566 [0.546, 0.586]; n=2 | 0.163 [0.121, 0.205]; n=2 | 0.143 [0.095, 0.191]; n=2 |
| external_unexposed | 16 | 618,537/1,092,838 | 0.487 [0.468, 0.592]; n=16 | 0.245 [0.192, 0.271]; n=16 | 0.207 [0.198, 0.227]; n=16 |

Entries are per-record medians, participant-bootstrap 95% intervals and contributing record counts. Event counts are pooled over continuous segments within a recording before calculating F1; empty/empty cases contribute no evidence to this aggregate. The overlapping windows are not independent statistical units.

[Protocol](../protocol/experiment-003.json) · [Methods](../protocol/transition-methods.md) · [Per-record main results](../results/003/summary.json) · [Control results](../results/006/summary.json) · [Transfer summary](../results/007/summary.json) · [Release downloads](https://github.com/h3ro-dev/eegt/releases)

## Transition geometry

| Group | Numerical view | Pre/post distance | Turning angle (radians) |
| --- | --- | --- | --- |
| train | morphology | 1.343 [1.307, 1.388]; n=24 | 1.549 [1.515, 1.576]; n=24 |
| train | spectrum | 0.753 [0.726, 0.771]; n=24 | 1.558 [1.548, 1.560]; n=24 |
| train | coordination | 1.433 [1.416, 1.479]; n=24 | 1.427 [1.351, 1.497]; n=24 |
| validation | morphology | 1.327 [1.247, 1.370]; n=6 | 1.612 [1.521, 1.720]; n=6 |
| validation | spectrum | 0.749 [0.720, 0.810]; n=6 | 1.547 [1.540, 1.591]; n=6 |
| validation | coordination | 1.460 [1.371, 1.480]; n=6 | 1.462 [1.400, 1.549]; n=6 |
| test | morphology | 1.266 [1.219, 1.302]; n=6 | 1.579 [1.520, 1.601]; n=6 |
| test | spectrum | 0.725 [0.704, 0.733]; n=6 | 1.559 [1.518, 1.601]; n=6 |
| test | coordination | 1.385 [1.346, 1.402]; n=6 | 1.506 [1.467, 1.548]; n=6 |
| external_exposed | morphology | 1.469 [1.389, 1.548]; n=2 | 1.411 [1.298, 1.525]; n=2 |
| external_exposed | spectrum | 0.725 [0.715, 0.734]; n=2 | 1.447 [1.346, 1.549]; n=2 |
| external_exposed | coordination | 1.317 [1.312, 1.323]; n=2 | 1.421 [1.283, 1.560]; n=2 |
| external_unexposed | morphology | 1.574 [1.421, 1.648]; n=16 | 1.419 [1.376, 1.444]; n=16 |
| external_unexposed | spectrum | 0.728 [0.717, 0.741]; n=16 | 1.551 [1.506, 1.561]; n=16 |
| external_unexposed | coordination | 1.338 [1.323, 1.358]; n=16 | 1.430 [1.290, 1.481]; n=16 |

Geometry summarizes the median event within each recording, then the median across recordings. Distances use each view’s training-scaled feature coordinates; speed is distance per second and angle is radians. Different views do not share a proven common coordinate system. Endpoint return distance is not a recovery time. All five descriptors and contributing event counts are in the JSON and SQLite release.
