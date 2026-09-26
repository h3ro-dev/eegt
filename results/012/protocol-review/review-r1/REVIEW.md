# Experiment012 protocol candidate: independent pre-freeze review

**Verdict: CHANGES_REQUIRED.** The candidate cannot yet be implemented in full without scientific choices about native phase controls, support accounting and mask/time transformations. The original root owns those choices and the freeze. No empirical EEG, model weights or reserved people were accessed.

## What is already specified

- Native 250 Hz, 7,500-sample µV extraction is distinct from the exact 200 Hz, 6,000-sample prepared µV/100 encoder input and its x100 numeric event conversion; the latter has inherited .3–75 Hz/60 Hz-notch preprocessing and no native timing precision.
- The five prepared variants and seed 9009+candidate_index agree with the 010/011 source contract; the protocol requires matching both encoders’ recorded input hashes and does not request new forwards.
- The accepted module exposes waveform-only versus separate cycle/envelope branches, complete sign-flank/filter support, fixed matcher cap/tie order, and null empty/empty matching. Native cycles and two burst definitions stay separate.
- Primary endpoints are exactly two encoders × geometry/change, with original-minus-independent_phase paired block effects, common intervals, recording medians, equal two-night person means, exact participant sign flips and Bonferroni ×4. For five nonzero complete person effects the minimum two-sided raw p is 2/32=.0625 and adjusted p is .25.
- The draft explicitly prohibits cross-night event-time alignment, new reserve exposure, fitted descriptors, per-window model APIs, and semantic or clinical claims; controls are fixed before data analysis.

## Findings requiring repair

### P012-01 · BLOCKER · input/PROTOCOL-DRAFT.md:35

The native 250 Hz independent_phase and shared_phase controls refer to a pinned Fourier implementation, but the supplied source defines only the prepared 200 Hz independent_phase variant. It does not fix the native FFT domain when masks/gaps exist, shared draw order, output dtype, or realization hashes.

**Consequence:** Two implementations can produce different controls and event counts from the same selected block; the native phase controls cannot be reproduced or audited from the current candidate.

**Minimal repair:** Before freeze, pin the exact native transform source and hash. State whether a block with any invalid sample abstains or how each uninterrupted run is transformed; specify per-frequency RNG draw order for independent and shared phases, DC/Nyquist handling, dtype, and per-block transformed-array hashes. Keep seed 12012+candidate_index and the prepared 200 Hz variant unchanged.

**Source cross-check:** input/pretrained_study.py:64-83, input/METHODS.md:61.

### P012-02 · BLOCKER · input/PROTOCOL-DRAFT.md:23,38

A waveform row already expands its sign-flank interval by the measured filter guard. The draft then requires full row support inside a common guarded timeline, without saying whether the matcher receives raw valid intervals or already guard-trimmed intervals. The latter applies the guard twice. The common-duration denominator also changes with that choice.

**Consequence:** Control matches, directional fractions, F1 and rates can differ near every edge or gap; pooling signature strata can also count the same common duration more than once.

**Minimal repair:** Define raw valid overlap, guarded event-center eligibility, and full event-support eligibility separately. State the exact interval pairs passed to match_events and whether an additional guard beyond the row support is intentional. Record one common duration per channel/variant timeline; if pooling family/polarity strata, sum their counts and matches but do not sum duplicate timeline durations.

**Source cross-check:** input/waveform_events.py:325-346, input/waveform_events.py:519-529, input/METHODS.md:47-49.

### P012-03 · BLOCKER · input/PROTOCOL-DRAFT.md:32,36-38

The common-mean transform does not say what happens when one of four contacts is invalid. The shift says to copy samples, but does not explicitly shift validity/segment information. Subtracting 0.2 s only from event timestamps would leave support and valid intervals on different clocks.

**Consequence:** A partial-contact reference or mismapped shifted mask can manufacture valid support, filter through an invalid sample, or produce false/missing time-shift matches.

**Minimal repair:** Specify that common-mean samples require all four valid contacts, or predeclare another exact abstention rule. Shift the waveform, Boolean mask and segment boundaries together, with 50 invalid prefix samples and no wrap. For the comparison only, subtract 0.2 s from every shifted event time, support endpoint and valid interval; retain original emitted rows and report residual signed lag.

**Source cross-check:** input/waveform_events.py:227-238, input/waveform_events.py:487-529.

### P012-04 · MAJOR · input/PROTOCOL-DRAFT.md:42-46

The 16-D count endpoint does not explicitly choose the integer event index over optional fractional interpolation at a one-second boundary, fix component order, or say whether a zero-norm vector makes the whole prespecified metric null rather than triggering interval deletion. The three other variants have no stated descriptive support rule.

**Consequence:** The same candidate can yield different interval counts or different geometry/change pairs, and post hoc deletion can change the primary paired support.

**Minimal repair:** Bind bins to integer event index using [200k,200(k+1)) on the prepared branch; name the four-channel and four-event component order. Keep the original/independent_phase all-channel interval intersection fixed for both encoders. State metric-level NOT_ESTIMABLE for any required zero-norm/nonfinite vector or constant distance sequence, with no salvage by deleting intervals after the support gate. Give each other variant a fixed descriptive support comparison rule and denominator without altering primary support.

**Source cross-check:** input/waveform_events.py:177-195, input/waveform_events.py:334-346, input/cross_encoder_study.py:482-490.

### P012-05 · MINOR · input/PROTOCOL-DRAFT.md:48

The exact sign-flip rule says inclusive ties but does not state its floating-point tie convention. Experiment011 used abs(mean_signed) >= abs(mean_observed)-1e-12.

**Consequence:** Near-tie sign assignments can produce different exact p values across implementations, despite the same person effects.

**Minimal repair:** Pin the comparison convention in the frozen analysis code or prose, explicitly reusing the Experiment011 rule or declaring strict floating-point >=. Keep all 2^n assignments, n<2 abstention and four-endpoint Bonferroni family.

**Source cross-check:** input/experiment-011.json:82-87, input/cross_encoder_study.py:411-421.

### P012-06 · MAJOR · input/PROTOCOL-DRAFT.md:23,50-60

The plan retains every control candidate/rejection across 18 native settings and all 122 blocks, plus one full morphology pass, while setting a 3 GB artifact reassessment point. The source fixture reports 7,352 guarded derivative rows for one four-channel 30-second block; extrapolating that illustrative density to the 18 native settings gives about 16.1 million derivative rows. This is a planning estimate, not an empirical result on the selected blocks.

**Consequence:** A verbose row archive may cross 3 GB before completion; a runtime-only one-block estimate cannot establish storage fit. Silent row omission would violate the protocol.

**Minimal repair:** At the already planned one-block post-freeze resource check, measure bytes and CPU for the full control set, full native morphology and prepared branch; project all 122 blocks. Use a lossless queryable compact representation or stop at the stated reassessment point and append an amendment. Keep all candidates, masks and denominators.

**Source cross-check:** input/ROOT-R1-CHECK.json:3-12, input/REPORT.md:3-20.

## Remaining UNKNOWN

- The review packet has source contracts and synthetic receipts, but no Experiment010 prepared archive, either encoder output archive, native SET file, live source masks or exact 011 inference receipts. Their bytes and hashes remain a freeze-time/native-source verification task; no empirical input or model weight was opened here.
- Actual event counts, support loss, zero-norm prevalence and the number of complete participants for each of the four endpoints are unknown until the authorized analysis. The expected five-person p-value resolution is arithmetic, not an observed result.
- Actual resource cost and compressed artifact size for the 122-block run remain unknown until the bounded post-freeze planning measurement. The 16.1 million-row calculation only illustrates a possible scale.
- The live experiment ledger number 012 and final release/reproduction artifact hashes were not in this isolated packet; the root must verify and pin them before freeze/publication.
- Sign symmetry and independence of person effects are assumptions of the exploratory test, not established by this source review; no population, biological, diagnostic or physical-device transfer claim follows.

## Exact reviewed inputs

| File | SHA-256 |
| --- | --- |
| `input/MANIFEST.json` | `d944de7ec3482b63ae9bb63c8f133be01d64bef6affbc931b63fd3061cc70f50` |
| `input/METHOD-RECHECK.json` | `3c7e055404f2e7c894d9f806c89994c85c50aa8f739baf8a787eaf4021bf9869` |
| `input/METHODS.md` | `7aefc9cb2fee774bc24d1ec3a6a85c467311e4e8660e2388792cfa7dde2df10c` |
| `input/PROTOCOL-DRAFT.md` | `a63ec70031c58ca1ebb56677c903a522d70eb4e776d99fbb9dafc3061788346a` |
| `input/REPORT.md` | `5c57c80b1dec7ad025f5d7863a261eff95e11667f3ffefae812c75540f5c118c` |
| `input/ROOT-R1-CHECK.json` | `3f1b8fd6b7ac9562bb4d4943dddc0aaafeaff135df35daf840f8e373b82f03fa` |
| `input/SYNTHETIC.json` | `bc8f2ec07e520f4c08901ab7785fa416854e39b52b3f80c628c0ee0e3072fd37` |
| `input/cross_encoder_study.py` | `cfc934775d663396713f3105dd121878186ff1d375c9531398f25a5a5c389eae` |
| `input/distributed_study.py` | `0f4f670b16494c6626a0edd36f53e94cbae2c1462c466209bede6108e5996266` |
| `input/experiment-011.json` | `792b56402d7d95eef8a7ed4b727d73b22819a521b6b99af34a37cacf2877ca2e` |
| `input/pretrained_study.py` | `80187b84274606d4d7d4c514d7eb05b892b4b8df96b8a92b6ea099293a232e3c` |
| `input/reproduce_cross_encoder.py` | `34ef60cb572e1242040a46860de8b7daae60b6bc18d0e0ae37ae411129da022f` |
| `input/requirements-events.lock` | `0397711648cd5473266b6196d4ae010ba8cd713362b2ff69d5d282b01e6fe7c4` |
| `input/test_waveform_events.py` | `a6c53c4a416062c6b7a59dd79fc737ddbf293894a867cff749356ba2704783ac` |
| `input/waveform_events.py` | `80a9b8f62693e551c7f385a911fa15ca321325b7983f63da8fc7373ba451f572` |

## Verification and handoff

- All 14 MANIFEST entries matched the local input bytes. `MANIFEST.json` itself was hashed independently.
- No detector battery, empirical analysis, model forward or download was run. The root’s reported .33 checks are context, not my independent execution.
- The 18-setting and 16.1 million-row figures are source-based planning arithmetic; they are not measured selected-block counts.
- The root should resolve the blocker choices, freeze source and protocol hashes, and obtain a fresh source review before running Experiment012.
