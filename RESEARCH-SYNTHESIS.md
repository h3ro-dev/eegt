# EEGT research synthesis — consolidated evidence

EEGT asks whether recurring patterns in anonymous around-ear voltage measurements can be described consistently by different numerical methods. The published work now includes explicit waveform landmarks and two independently pretrained continuous EEG encoders. It has not established a universal token vocabulary, semantic meaning, brain-state diagnosis or thought decoding.

The original 11.4% result meant 393 accepted assignments among 3,458 external windows in Experiment 001's scalp seed. It was an acceptance/coverage measure, not 11.4% accuracy or 11.4% of a person's brain activity. Later experiments changed the source, representation and quality rules, so their coverage is not a controlled improvement over that percentage. Each displayed fraction must retain its own numerator, denominator and experiment.

Experiment 002's three small representation families partitioned waves differently. Shared spectrum objectives produced more agreement than phase-sensitive waveform shape, and high assignment coverage sometimes accompanied a concentrated vocabulary. That separates three questions: can a model assign a code, does the code distinguish varied patterns, and do independent models agree? None alone supplies meaning.

The expanded source catalog distinguishes candidate recordings, qualified recordings, source-local people, nights, recorded hours, quality windows and selected support. Reprocessing one recording with another model adds no people or hours. The historical public baseline through 012 has 67 candidate / 66 qualified recordings and 309.854187 qualified source hours. The consolidated catalog adds the two accepted EESM19 engineering recordings and twenty qualified Experiment 013 recordings: 89 candidates, 88 qualified recordings and 476.053296 qualified source hours. These are source-recording totals, not a globally deduplicated people count.

Experiments009–012 keep failed eligibility and inconclusive results. A small first slice had too little qualified paired support. Experiment 010 therefore used a separately frozen time-distributed census within already exposed recordings. Experiments011–012 reused its 122 selected thirty-second blocks (61 selected minutes within 48 already examined hours), with five complete paired people and 110 primary blocks. CodeBrain and CBraMod ran as fixed continuous encoders, not independent language models discovering a discrete alphabet.

Experiment 011's two adjusted tests remain inconclusive at 0.125. Experiment 012 compared direct event counts with each encoder's geometry/change representation. All four adjusted tests remain inconclusive (.50,.25,1,1). Its complete 2,806-partition ledger and queryable index preserve every event candidate, rejection and control. Two complete extracted ledger replays reproduced the results; detector regeneration was checked separately on six prespecified fixtures.

Numerical landmarks survive some transformations by construction. At 25 milliseconds tolerance, independently phase-randomized signals retained about 0.835 pooled landmark agreement. Dense landmarks and tolerance can create high matching after local timing changes; this is a limitation, not evidence of the same biological state. Synthetic noise also produces cycles and bursts. Source reference, gain, filtering, spatial layout and residual artifacts remain plausible contributors.

## Final validation — independently reproduced and published

Experiment 013 acquired all 20 pinned sources under a reviewed pre-access scientific protocol. Qualification initially hit the fixed memory bound. The failed attempts remain preserved; an independently reviewed process-isolation correction then qualified all 20 records without changing the scientific rules. Independent extracted replay and final output review are accepted. The original replay exceeded the unchanged CPU bound and remains in the evidence. A reviewed additive verifier completed the same full checks within 5,306.66 CPU seconds and 1,447,821,312 bytes peak RSS; it changed no scientific rule. All ten public release assets matched their hashes after publication.

| Denominator | Actual support | Meaning |
|---|---:|---|
| Qualified recordings | 20 | Separate source records, not independent people |
| Recorded source duration | 151.848631 hours | Full qualified recording duration |
| Prespecified candidate grid | 9,600 × 30 seconds = 80 hours | First four hours of each recording |
| Quality-passing blocks | 4,117 | Includes unselected blocks |
| Fixed selected blocks | 174 × 30 seconds = 87 minutes | Before detector guards |
| New-session cohort | 6 complete people; 130 blocks | Eligible for fixed encoder comparisons |
| New-person cohort | 2 complete people; 44 blocks | Below the frozen minimum of 3 people |
| Encoder calls | 650 per encoder | 130 eligible blocks × 5 variants |
| Event ledger | 4,002 partitions | All 174 selected blocks |

The new-session comparisons each use six complete people. All four new-person comparisons are not estimable because the cohort fails its support gate. The primary correction family remains eight tests.

| New-session endpoint | Mean effect | Adjusted p |
|---|---:|---:|
| CodeBrain geometry | 0.01269593 | 1.00 |
| CodeBrain change | −0.06168301 | 0.25 |
| CBraMod geometry | 0.03799173 | 0.50 |
| CBraMod change | 0.00745507 | 1.00 |

None meets the adjusted threshold. The negative CodeBrain change contrast and differing model directions are retained; no formal between-model difference was established. With six people, the smallest possible two-sided sign-reversal p is 2/64. Correction across eight tests makes the minimum 0.25, so this bounded design cannot establish adjusted significance at 0.05 even with maximally consistent effects. Observed effect sizes, directions and exclusions remain useful; overlapping windows do not increase the independent participant count.

The separate EESM19 engineering check completed two 30-second sessions from one person using 12 native contacts at 500 Hz. It supports a native-detector technical check only. No four-channel encoder mapping or physical Neurable equivalence is inferred.

## What the open release enables

A researcher can inspect the frozen choices, reconstruct selected inputs, replay published event/model evidence, see every exclusion and propose a new falsifiable test. The catalog must preserve original source terms, hash identities, masks, exposure state and immutable release links. Discovery receives numeric arrays; grouping metadata stays in provenance/evaluation. Anonymous inputs still contain measurement and pretrained-model assumptions.

The next justified claims require more independent people and acquisition setups, demonstrated measurement compatibility, and a method frozen before those data are examined. Meaning would require a separate appropriately designed study; this program defers that work. Physical Neurable capture and the exact custom domain retain their separate acceptance boundaries.

Evidence: [Experiment 001](https://github.com/h3ro-dev/eegt/blob/main/notes/experiment-001.md), [Experiment 002](https://github.com/h3ro-dev/eegt/blob/main/notes/experiment-002.md), [Experiment 011 summary](https://github.com/h3ro-dev/eegt/blob/main/results/011/summary.json), [Experiment 012 summary](https://github.com/h3ro-dev/eegt/blob/main/results/012/summary.json), and the published [v0.8.0 release](https://github.com/h3ro-dev/eegt/releases/tag/v0.8.0). Experiment 013 is published as [v0.9.0](https://github.com/h3ro-dev/eegt/releases/tag/v0.9.0); its [independent review](https://github.com/h3ro-dev/eegt/blob/main/results/013/release-review.json) and [acceptance](https://github.com/h3ro-dev/eegt/blob/main/results/013/release-acceptance.json) retain exact source hashes. The consolidated catalog remains a release candidate until its independent rebuild and public readback are complete.
