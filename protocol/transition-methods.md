# EEG transition primitives

This packet provides numerical, label-blind measurements of change in continuous multichannel EEG. It assigns no physiological state, participant identity, task label, source, anatomical connection, or clinical interpretation. The caller chooses channels, reference montage, train split, detector scale, and threshold; those choices remain part of any result.

## Interface and units

`extract_features(samples_uv, sample_rate_hz, *, valid_samples=None, window_seconds=2.0, hop_seconds=0.5)` accepts a real `[channels, time]` array in microvolts at a native rate of at least 100 Hz. `valid_samples`, when supplied, is a matching Boolean array. A window uses every sample from each participating channel; even one invalid or nonfinite sample excludes that channel from the window. Start and hop are rounded to whole samples. `times` are float64 window centers in seconds from the first input sample. A recording shorter than one window produces empty arrays with fixed view widths.

The channel quality gate removes any channel-window with peak-to-peak amplitude **above 500 µV**, raw standard deviation **below 0.05 µV**, invalid/nonfinite samples, or native 50/60 Hz line-bin power fraction **above 0.3**. Native line power is the summed Hann-periodogram power within ±1 Hz of 50 and 60 Hz divided by power at frequencies at or above 1 Hz. The line test runs only when native Nyquist is **above 65 Hz**; otherwise `metadata.line_check_available` is false and the test is unavailable. Frequencies beyond Nyquist are never reconstructed. After filtering, a channel whose retained signal is below 0.05 µV standard deviation is also excluded. A feature window needs at least two channels and at least 75% of the supplied channels. Invalid windows have NaN rows in every view; gaps are never filled.

Each usable channel is processed **within its own window** with a 1–40 Hz Butterworth bandpass in second-order sections, forward and backward via SciPy `sosfiltfilt`. The SciPy order parameter is 4, giving an eighth-order bandpass transfer function before the forward/backward pass. Its reflection padding uses only that valid window. The first and last `min(round(0.5 × rate), window_samples // 4)` samples are discarded before features. For the default two-second window this leaves the central one second. The reflection and trimming reduce, but cannot remove, edge bias near 1 Hz; the estimates depend on window length and should not be read as high-resolution 1 Hz power. No filter state crosses an invalid span. Window-local processing also makes an aligned interior window identical whether extracted from a full recording or a haloed chunk. Corpus integration should retain the planned ≥12 s halo and discard it, and align chunk starts to the same hop grid to avoid edge/window-grid differences.

The returned views have the same number and ordering of columns for every channel count:

| View | Per-channel or sensor-space values | Aggregation |
| --- | --- | --- |
| `morphology` | log10 RMS in µV, log10 Hjorth mobility per second, Hjorth complexity, normalized 100 ms autocorrelation | median and interquartile range across usable channels |
| `spectrum` | log10 integrated periodogram density in 2 Hz cells from 1 Hz upward; the last cell is clipped to 39–40 Hz | median and interquartile range across usable channels |
| `coordination` | pairwise clipped robust correlations: signed median, interquartile range, absolute median; leading correlation eigenvalue divided by channel count; entropy effective rank divided by channel count | one sensor-space vector |

For the spectrum, zero-padding sets a numerical frequency grid of at most 0.25 Hz spacing; it interpolates the periodogram and **does not increase physical resolution or recover frequencies**. Correlation first centers each retained channel by its median, scales by MAD, and clips at ±5 before unit-norm correlation. The eigenvalue summaries use the correlation matrix rather than a channel-count-dependent covariance eigensystem. Output widths are fixed, while estimates can still change with montage, channel count, reference, sampling rate, window length, and artifact distribution. These sensor correlations are **not anatomical connectivity**.

## Train-scaled boundaries

For downstream calls, concatenate the view matrices in a chosen, fixed order, for example:

```python
import numpy as np

order = ("morphology", "spectrum", "coordination")
features = np.concatenate([result["views"][name] for name in order], axis=1)
reference = fit_reference(features[train_rows & result["valid"]])
scores = boundary_scores(features, result["times"], result["valid"], reference)
indices = select_boundaries(scores["2.0"], result["times"], threshold=chosen_threshold)
rows = transition_geometry(features, result["times"], result["valid"], reference, indices)
```

`fit_reference` accepts one finite 2-D training matrix or a sequence of such matrices. It returns copied per-column training medians and interquartile ranges; a constant column uses scale 1. It has no split metadata and performs no split selection. Freeze this reference before scoring validation or test material. Threshold and scale selection also belong outside held-out evaluation.

`boundary_scores` first subtracts the frozen center and divides by the frozen scale. At candidate index `i`, it compares the mean of `k = ceil(scale_seconds / nominal_hop)` rows before `i` with the mean of `k` rows starting at `i`, using root-mean-square distance over feature coordinates. The score is NaN unless all `2k` rows and all intervening time steps are finite, valid, and contiguous. Candidate `i` denotes the change between windows `i-1` and `i`. Times must be strictly increasing and uniform within valid runs. A timestamp jump is accepted only when an endpoint is explicitly invalid, and no score crosses it. The nominal hop is inferred from adjacent valid rows. Scale keys are `str(scale)`.

`select_boundaries` chooses finite local maxima at or above `threshold`; a flat maximum uses its earliest index. It then retains stronger peaks first, with lower index breaking a tie, until selected peaks are separated by at least `min_separation_seconds`. Returned indices are sorted int64. NaNs split peak runs; they are not interpolated.

## Geometry and matching

`transition_geometry` uses `ceil(context_seconds / nominal_hop)` contiguous finite feature rows on each side of each supplied boundary. Unsupported metrics are JSON `null`. Distances are root-mean-square Euclidean distances in the frozen, train-scaled feature coordinates:

| Field | Definition |
| --- | --- |
| `pre_post_distance` | distance between pre-context and post-context mean vectors |
| `path_length` | sum of consecutive feature-step distances through both contexts |
| `mean_speed` | path length divided by elapsed time from first to last context center |
| `turning_angle_radians` | angle between the pre-context start-to-end displacement and post-context start-to-end displacement; null for a zero or undefined direction |
| `return_distance` | distance from the last post-context vector to the pre-context mean |

`return_distance` is an endpoint similarity, **not detected recovery or a recovery time**. There is no dwell-time measurement or scalar mathematical inflection measure. Path length, speed, angle, and distance depend on feature coordinates, train reference, sample/window resolution, context duration, and overlapping-window correlation. A two-row context cannot define a within-side turning direction, so its angle is null.

`match_boundaries(times_a, times_b, *, tolerance_seconds=1.0)` sorts finite input times internally and finds the maximum number of ordered one-to-one pairs within tolerance, then the smallest total absolute timing error among those matches. It never double-counts a boundary. `a` is the reference set for recall; `b` is the detection set for precision. F1 is their harmonic mean. Both empty sets give precision, recall, and F1 of 1 as a declared perfect-empty agreement; exactly one empty set gives 0. The median absolute error is null with no matches. The integrated implementation uses a sparse dynamic program over pairs within the tolerance, preserving maximum count and minimum total error. It takes O(E log(n_b)) time and O(E+n_b) storage for E eligible pairs, bounded to four million eligible pairs; tied optimal chains use the earlier constructed state. Total timing error is also reported. A bisected neighbor check accelerates minimum event separation without changing its selection rule. These integration changes were made before corpus feature analysis.

`phase_surrogate` rotates rFFT phases while preserving each channel's Fourier amplitudes and mean. Even-length Nyquist bins stay real and unchanged; the odd-length last bin is an ordinary complex bin and is rotated. `shared_phase=True` applies the same rotation to every channel at each frequency and preserves cross-spectra. The default independent rotations generally disrupt cross-channel phase. Neither mode is a biological null model by itself; the parent separately handles time-reversal and gain controls.

## Verification and limits

`python3 -m unittest discover -s out -p 'test_transitions.py' -v` runs small synthetic contract checks for artifacts and gaps, a constructed frequency shift, chunk alignment, fixed dimensions, frozen reference, timestamp validation, geometry nulls, matching, and even/odd surrogates. These fixtures check numerical behavior only. They are **not independent biological validation**, universal validation, or evidence of clinical utility. A continuous corpus still needs montage selection, provenance, split discipline, threshold calibration, sensitivity checks across acquisition setups, and domain review.

HMM/HSMM training, PAC, clinical modules, physiological state labels, dwell inference, and detected recovery are **not implemented** in this packet.
