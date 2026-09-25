# Experiment 003: pre-fit integration corrections

Date: 2026-09-25. No model reference, threshold, held-out score or control result
had been fitted or evaluated when these corrections were made. Technical QC
counts from feature extraction were visible. The independent source review and
the initial extraction are retained; the corrected extraction is regenerated.

- Require exactly one feature status row per catalog record, reject duplicate
  or missing IDs, bind each extracted path to its recording ID, and retain all
  non-extracted statuses/reasons in the main result. Missing data cannot silently
  disappear from the analysis denominator.
- Bind each cached control row to a separate receipt hash. Verify row identity
  and variant completeness on resume and bind row files into the final summary.
- Check digital unit conversion independently: raw little-endian float32 FDT
  values, declared microvolts, must equal MNE-decoded volts multiplied by one
  million. The start, middle and end of each qualified file are probed; a
  generated known-value EEGLAB fixture tests the same conversion. This does not
  prove the original amplifier's physical calibration.
- Align reversed feature windows on the exact reflected original center grid,
  use common reflected validity, and account for the half-second boundary-label
  convention. The unpaired reversal result is retained separately. This fixes a
  coordinate/support comparison, without choosing thresholds from its outcome.
- Produce the prespecified participant-recording medians and 1,000-bootstrap
  intervals in Experiment007's sealed aggregation. Pool segment match counts
  within each record first; empty/empty event sets contribute no aggregate F1
  evidence. Keep previously exposed external records separate.
- Describe one-draw phase controls as limited, descriptive perturbation checks.
  They do not establish statistical significance, biological specificity, or a
  universal state geometry. Shared preprocessing and surviving artifacts remain
  possible explanations.

The integration also replaced a dense timing-match implementation with a
sparse dynamic program preserving maximum cardinality and minimum total timing
error. An independent exhaustive oracle agreed on 500 small randomized cases.
The source corpus, participant split, numeric features, QC criteria, context
scales and threshold quantile remain as frozen in the original protocol.

Source qualification retained 55 candidates and quarantined ds005207 sub-026:
its native sample count differs from declared duration by 503 samples at 250 Hz.
The source bytes match upstream hashes. The discrepancy is preserved and the
record remains excluded under the one-sample duration rule; no silent duration
repair or interpolation was applied.

## Additional corrections before held-out evaluation

The first fitting attempt stopped at the timing-grid guard during the training
threshold pass. Floating-point chunk ownership had admitted near-duplicate
centers in 11 auditory recordings. Transient training reference statistics had
been calculated, but no model or threshold artifact was frozen and no held-out
or control result was produced. Window ownership now uses integer native
half-sample coordinates. A 1,202-second off-grid regression fixture reproduces
the seam and verifies exactly one row per center. Features were regenerated
before fitting. Earlier feature receipts remain preserved as historical
intermediates; they are not the final analysis inputs.

Independent re-review also identified a reporting edge case: a control cohort
could disappear when it had no analyzable main-run record. Control groups now
derive from control eligibility independently, and a focused regression checks
this case. Final reports and the audit verify every control row against its
separate hash receipt and the summary. These changes do not alter the frozen
split, feature definitions, QC rules, thresholds or boundary matching criteria.
