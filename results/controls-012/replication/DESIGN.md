# Independent-person replication design — metadata stage, 2026-09-28

The available cohort depends on the acquisition family. The pinned EESM19 inventory contains **20 people and 200 sleep sessions: 80 PSG sessions across all 20 people and 120 ear-only sessions across 10 people**. The accepted EEGT catalog records two exposed ear-only sessions from one person. Excluding that whole person leaves **9 ear-only candidates with 108 sessions**, or **19 PSG-session candidates with 76 sessions**. The combined 184 candidate sessions still represent only 19 people. These counts are metadata capacity, not qualified participants, usable hours, windows or events. Reserved waveform qualification is `NOT_ASSESSED`; source hours and selected windows are unknown.

This refines the prior synthetic proposal's nineteen-person upper bound. A twelve-person target cannot be achieved from the remaining ear-only acquisition alone. Nineteen is a valid metadata upper bound only for a design that includes the PSG-session ear contacts. The source files declare twelve ear contacts for both acquisition families, but declaration does not establish equal reference, calibration, acquisition quality, or compatibility with the four-channel encoders. The additional PSG channels must not silently enter numeric discovery.

## Evidence and exposure boundary

`audit_capacity.py` recomputes person/session/acquisition counts from the already acquired OpenNeuro inventory, matches every SET/FDT pair, checks all twenty pinned session tables and their accepted hashes, and compares whole-person exclusions with the accepted consolidated catalog. `CAPACITY.json` records exact input and code hashes and the curator-level public source identifiers. These identifiers support provenance only; they do not enter discovery arrays. This audit reads no reserved waveform, private recording, scoring label, or media. Source IDs establish source-local people only. Cross-dataset person overlap, external analyses and foundation-model pretraining exposure remain `UNKNOWN`; resolve relevant overlap before calling the final cohort fully independent of earlier project evidence.

Sources: [EESM19 version 1.0.2](https://openneuro.org/datasets/ds005185/versions/1.0.2), [pinned source tree](https://github.com/OpenNeuroDatasets/ds005185/tree/0857858f7a2ba1582930f23eca3ec56f90a96da9), and the accepted local catalog and source receipt identified in `CAPACITY.json`. Source metadata are reused, not downloaded again. The author paper describes the broader acquisition families: [Mikkelsen et al., 2025](https://doi.org/10.1038/s41597-025-04579-8).

## Candidate designs

| Design | Recorded-unexposed metadata capacity | Consequence |
| --- | --- | --- |
| Ear-only sessions, same acquisition family as current EESM19 engineering inputs | 9 people, 108 sessions | Cannot supply twelve complete people. Repeated nights improve within-person reliability but do not add independent people. Another cohort is needed if the final power target exceeds nine. |
| Ear contacts from PSG sessions only | 19 people, 76 sessions | A feasible candidate pool, subject to a reviewed twelve-contact measurement contract, quality eligibility and a power calculation. No claim of sufficient power or sufficient qualified people yet. |
| Mixed acquisition families | 19 people, 184 sessions | Requires prespecified acquisition stratification and one aggregate per person. It cannot be justified by simply adding session counts or treating both families as interchangeable. |

The preferred next preparation step is **metadata/header contract design for the PSG-session ear contacts**, because it can assess a larger independent-person candidate pool. This is a proposal for a future protocol, not permission to inspect reserved amplitudes. Complete its contact/reference/clock rules and independent review first. Continue measurement development on the already exposed sources in the meantime.

## Prospective design commitments and unresolved choices

The new empirical density-control tranche is exploratory and cannot retroactively replace the frozen 012/013 endpoints. Before any new-person waveform access, write a separate prospective protocol containing:

1. A measurement claim narrow enough to test: timing agreement in excess of a specified density/coarse-time null, or a separately justified representation endpoint. A positive contrast would establish deviation from that null, not neural origin, meaning, diagnosis or a universal EEG language.
2. One prespecified person-level aggregate; equal person weighting; fixed rules for eligible nights, common support, minimum valid events and failed controls. A person lacking the required nights or support remains an explicit exclusion. No favorable-night or favorable-channel selection after inspection.
3. A justified primary endpoint and smallest scientifically worthwhile **raw-unit** effect, plus a defensible person-level variance assumption or externally justified bound. Both remain **UNRESOLVED**. The exposed empirical controls may inform engineering feasibility, but their selected population is not an independent estimate of replication success.
4. A proposed planning target of at least 80% power at family-wise alpha 0.05; final confirmation and the multiplicity family are frozen before access. Retain the existing eight-test family when replicating those eight claims. A new single-endpoint study must have a separately justified scientific question, not an after-the-fact reduction in multiplicity.
5. A test justified by its actual null assumptions. The existing exact mean sign-flip proposal requires independent person-level sign exchangeability/symmetry under the null; a zero mean alone is insufficient. Freeze a valid alternative if that assumption is not defensible.
6. Source version and person allocation, exclusion of all previously exposed people, acquisition family, twelve-contact order, reference set, units and gain, timebase/gap handling, filtering, quality masks and any separately reviewed encoder adapter. Physical Neurable equivalence remains `UNKNOWN`.
7. Fixed resource limits, seeds, draw count, null-validation failure rules, no outcome-dependent stopping or replacement, reproducible input seals and independent protocol/output review.

The accepted prototype simulated a single hypothetical Normal-effect endpoint against an eight-test threshold: power at standardized effect 1 was 0.221 for nine people and 0.505 for twelve. Those are hypothetical scenario results, not estimates for this cohort. The same prototype showed that nine is the first possible sample size to reach a two-sided exact sign-flip Bonferroni-adjusted p below 0.05 for eight tests. This attainable-p floor must not be relabeled adequate power. No new power simulation has been run here. Qualification probabilities for nineteen candidates must not be applied to the nine-person ear-only pool.

## Reproduction and release boundary

Run `python3 work/next-study/replication/audit_capacity.py` from the project root. It uses only the Python standard library and read-only metadata/catalog access. The output is deterministic and asserts agreement across independently represented inventory, session-table and prior receipt counts. `CAPACITY.json` is pending independent scientific review until the separate review receipt accepts it. Old published results and earlier prototype artifacts remain unchanged.
