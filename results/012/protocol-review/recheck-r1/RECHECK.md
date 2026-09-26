# Experiment012 revision r1: independent protocol recheck

**Verdict: ACCEPTED for protocol design.** Revision `86f41254` resolves all six findings in the original source-only review. This does not freeze the protocol or accept any empirical result. The original root owns the input/implementation gates, freeze and release.

The revised matching rule intentionally intersects **guarded** timelines and then requires complete, already expanded event support inside that intersection. This additional restriction follows accepted METHODS line 47. It must remain in the implementation; raw-valid overlap is recorded separately and cannot replace it.

## Prior finding dispositions

| Finding | Disposition | Exact revision evidence |
| --- | --- | --- |
| P012-01 | RESOLVED | `input/revision-r1/PROTOCOL-DRAFT.md:69-73`, `input/revision-r1/transitions.py:493-510`, `input/revision-r1/PREPARATION-ACCEPTANCE.json:1-12` |
| P012-02 | RESOLVED | `input/revision-r1/PROTOCOL-DRAFT.md:75-79`, `input/METHODS.md:47-49`, `input/waveform_events.py:325-346`, `input/waveform_events.py:519-529` |
| P012-03 | RESOLVED | `input/revision-r1/PROTOCOL-DRAFT.md:81-87`, `input/waveform_events.py:219-238`, `input/waveform_events.py:487-529` |
| P012-04 | RESOLVED | `input/revision-r1/PROTOCOL-DRAFT.md:89-95`, `input/waveform_events.py:177-195`, `input/cross_encoder_study.py:482-490` |
| P012-05 | RESOLVED | `input/revision-r1/PROTOCOL-DRAFT.md:48`, `input/revision-r1/PROTOCOL-DRAFT.md:97-101`, `input/cross_encoder_study.py:411-421` |
| P012-06 | RESOLVED_AS_PRE_RUN_GATE | `input/revision-r1/PROTOCOL-DRAFT.md:103-107`, `input/revision-r1/ARTIFACT-ESTIMATE-DETAIL.json:1-9`, `input/revision-r1/PREPARATION-ACCEPTANCE.json:1-12` |

### P012-01

The revision pins one native float64 [4,7500] phase_surrogate source, seed, whole-block invalid-mask abstention, 3749 rotated positive-frequency bins, independent [4,3749] versus shared [1,3749] draw shapes, unchanged DC/Nyquist, output hashes and a separate 200 Hz prepared path. The supplied function implements those FFT and RNG operations. The preparation receipt is a root-owned acceptance assertion; this source review does not re-open its array.

### P012-02

The revision explicitly chooses the conservative two-stage rule required by accepted METHODS: intersect guarded center intervals, then require each complete already expanded row support inside that intersection. It separately records raw overlap and guarded C duration, reports C once per channel/variant, and pools counts/matches without duplicating exposure. No matching-row event rate is inferred from C.

### P012-03

Common reference requires all four contact masks true and never averages a changing subset. Shift copies samples and masks by exactly 50 at 250 Hz, retains an invalid prefix, refuses multi-segment inputs, and maps all seconds/support/valid and guarded intervals into comparison-only source-clock copies. Native emitted rows remain unchanged. The polarity comparison copy maps peak/trough and both curvature directions.

### P012-04

Prepared bins use integer indices [200k,200(k+1)), fixed channel/event component order, and the original/independent_phase all-channel eligible set K for both models. Geometry and change use fixed required vectors/pairs and whole-metric abstention, never post hoc interval deletion. Each other variant has a fixed K intersection and shared descriptive support across encoders.

### P012-05

The exact person-level sign-flip comparison reuses the Experiment011 1e-12 inclusive-tie convention, with all 2^n assignments and Bonferroni across four endpoints. Recording quantiles, method-specific guarded exposure, no duplicated time, null zero-exposure rates and night002-minus-night001 differences are now explicit.

### P012-06

The planning estimate is reproducible from the supplied fixture receipt: 122*(1,539,410 + 22*1,197,694)=3,402,418,716 compressed bytes, already above the 3 GB reassessment point before metadata. The protocol now fixes the first selected block, measures all 18 native settings, five prepared variants and archived representations, projects CPU/RSS/complete compressed bytes, and stops before the remaining 121 blocks if unsupported. Complete rows and denominators cannot be dropped to fit.

## Residual contradictions requiring a scientific choice

None found in this bounded source review. The six prior repair requests now have fixed executable rules.

## Remaining UNKNOWN and root gates

- This source-only recheck does not independently establish the 122 native masks as all true: PREPARATION-ACCEPTANCE.json states 244 independent checks and array/curator hashes but does not expose per-mask counts, and the underlying array/script bytes were not supplied. The frozen preflight must reject any changed or invalid mask for a native phase variant as specified.
- The actual 010 prepared and both 010/011 embedding archives, model weights and native SET bytes were not supplied or opened. Their hash, row-order, calibration and model-output checks remain root-owned input gates, not findings about the protocol design.
- Actual first-block detector CPU/RSS/compressed bytes and the 122-block projection are unknown until the explicitly bounded post-freeze measurement. The 3,402,418,716-byte receipt is a development-fixture estimate, not observed Experiment012 size.
- Event counts, support loss under the intentional additional guard, endpoint estimability, person-level effects and night differences are unknown. No empirical outcome or reserve was inspected in this recheck.
- The protocol remains an unfrozen candidate. Freeze, implementation/release verification and publication are owned by the original root. Native model monetary cost remains UNKNOWN.

## Source-bound arithmetic and verification

- The native `rfft` on 7,500 even-length samples rotates 3,749 interior positive-frequency bins. The pinned function uses the declared independent and shared draw shapes and returns a float64-length-preserving `irfft` result.
- The artifact receipt recomputes exactly: `122 × (1,539,410 + 22 × 1,197,694) = 3,402,418,716` compressed bytes. This exceeds the decimal 3 GB reassessment point by 402,418,716 bytes before metadata. The fixed first-block measurement and stop rule make that projected overage explicit.
- All four revision manifest entries matched both SHA-256 and byte count; the manifest itself and the prior review/accepted source contracts were hashed. No detector, EEG array, model weight or reserve was run or opened.

## Exact new input hashes

| File | SHA-256 |
| --- | --- |
| `input/revision-r1/ARTIFACT-ESTIMATE-DETAIL.json` | `73c765fa59f484be644cf7971d79c6be997a9a6495f9c27db658aca23e0dd102` |
| `input/revision-r1/MANIFEST.json` | `5a2d0ef72a6a7076183b3a3c4207f227695b8dcb174b863ca994a30252c6f280` |
| `input/revision-r1/PREPARATION-ACCEPTANCE.json` | `e3f985cdbb6572179f8ac5bdb00592325aee414399434f3bf9561fbd2cb198a7` |
| `input/revision-r1/PROTOCOL-DRAFT.md` | `86f41254f1fc35a0d95e4e9aab45bec0e12d1964ec18d8a38a7d92c57daf92e9` |
| `input/revision-r1/transitions.py` | `f0c7c3dbf47f819aed52216369a7878cdf792b305999759704a86bcc3615bf0d` |

Reference hashes and the digest of each review output are in `FILES.json` and `RECHECK.json`.
