# Research Notes · Experiment 006

Date: 2026-09-25. State: bounded phase and nuisance control battery computed.

54 of 55 source records have a technically eligible control segment. The first native continuous interval long enough is used: 120 central seconds with 12-second halos on each side. This is a bounded control sample, not all 235 metadata-hours; ineligible records retain reasons.

Independent Fourier phase randomization preserves each channel's Fourier magnitudes. Shared randomization also preserves cross-spectra. Both change temporal localization. The same frozen detector is applied, with validity counts and matched original/variant supports for rate comparisons. Gain×1.1, polarity reversal and time reversal test nuisance sensitivity; reversal is reported with reflected timing and separate quality exposure.

| Control | Records | Valid windows | Shape / spectrum F1 | Shape / coordination F1 | Spectrum / coordination F1 |
| --- | --- | --- | --- | --- | --- |
| original | 16 | 3265 | 0.387 [0.303, 0.545]; n=15 | 0.368 [0.182, 0.400]; n=15 | 0.286 [0.182, 0.444]; n=15 |
| independent_phase | 16 | 2174 | 0.000 [0.000, 0.000]; n=2 | 0.000 [0.000, 0.000]; n=2 | NA |
| shared_phase | 16 | 2246 | 0.000 [0.000, 0.154]; n=9 | 0.062 [0.000, 0.286]; n=8 | 0.000 [0.000, 0.667]; n=5 |
| gain_1.1 | 16 | 3185 | 0.381 [0.323, 0.538]; n=15 | 0.333 [0.190, 0.400]; n=15 | 0.316 [0.182, 0.444]; n=15 |
| polarity_reverse | 16 | 3265 | 0.387 [0.303, 0.545]; n=15 | 0.368 [0.182, 0.400]; n=15 | 0.286 [0.182, 0.444]; n=15 |
| time_reverse | 16 | 3265 | 0.485 [0.316, 0.527]; n=15 | 0.200 [0.105, 0.316]; n=15 | 0.353 [0.200, 0.381]; n=15 |

This table uses prior-unexposed external records and each variant's own valid support. Paired-support rate differences are in the machine-readable summary; do not interpret changes in the table as entirely biological when validity differs. These controls are not a complete biological null and are not clinical validation.

These are LLM-authored numerical representations, not independent pretrained LLMs discovering a language. F1 measures timing agreement within one second; it is not accuracy against brain-state labels. Neither high agreement nor a change score establishes semantic meaning, a diagnosis or universal geometry.

[Protocol](../protocol/experiment-003.json) · [Methods](../protocol/transition-methods.md) · [Per-record main results](../results/003/summary.json) · [Control results](../results/006/summary.json) · [Transfer summary](../results/007/summary.json) · [Release downloads](https://github.com/h3ro-dev/eegt/releases)
