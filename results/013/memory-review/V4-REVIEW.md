# Experiment013 v4 independent source-correction review

**ACCEPTED for the bounded source correction.** V4 closes the complete-child CPU accounting defect documented in the preserved v3 CHANGES_REQUIRED review. This is not validation completion or a 20-record memory-fit result.

V4 takes `RUSAGE_CHILDREN` before spawn and again after join, then adds the complete child user plus system CPU to the parent stage total. The single numerical child is reaped before the next read. Memory remains a conservative parent peak plus maximum completed-child peak, with the child's own peak retained as a floor. The accepted 2 GiB RSS and 7,200-second CPU bounds are unchanged.

## Evidence

- Both v4 packet manifests matched all declared file hashes. The final scratch overlay differs from v3 only in `eegt/validation_intake.py` and `tests/test_validation_intake.py`; the latter is the final regression file from `update-root-v4-regression`.
- Pinned Python 3.12.14 focused intake suite: **11 passed, 1 skipped**. The CPU equality regression fails on v3 (1.799833 reported versus 1.940039 seconds complete child CPU) and passes on v4. Root's `18 passed, 1 skipped` is packet evidence only.
- Four fresh sequential reads of the already exposed Experiment008 sub-001/ses-001 fixture matched all ten archived qualification fields. Each v4 worker CPU delta equaled the independently sampled reaped-child delta (four 0.0-second gaps). Peak parent plus maximum child RSS was **1,063,059,456 bytes**, below **2,147,483,648 bytes**.
- A known decoder ValueError kept its exact reason; an unexpected TypeError stopped; deliberate child source drift stopped without a result; no child remained. Original protocol, source list, decoder, scientific code and limits retain their accepted hashes.
- The prior varied-record v2 attempt failed at **2,420,178,944 bytes**. Exposed-fixture parity does not establish varied 20-record fit. No quality or model outcomes exist.

The supplied accepted seal is still the **v2 seal** (`d1eaf8101bf2c11ba17baf3f1afa05af29e9dd5bfb4bede361f84a949d661dad`) and cannot authorize v4. The probe used an explicitly unaccepted diagnostic binding. Root must integrate the exact final source and test, check actual bindings, preserve failed attempts and original unknown-subset exposure, create additive amendment002, and obtain fresh staged admissions before empirical work.

## Exact reviewed file inventory (SHA256)

| File | SHA256 |
| --- | --- |
| `AMENDMENT-CONTRACT.md` | `31f6673062635f688a011d69e63d5bda0937c7c7277c5ab94d9cbd0417196335` |
| `evidence/qualification-output.json` | `beaaf226d72b9988b6893a9a8f95809a8e8dc95fdbc3e45d635023555355ede0` |
| `out/REVIEW.json` | `c541d61d2a2d824afbe4f1ebcf70b46f738fc2bdc0eff689d18995f04fd6081f` |
| `out/REVIEW.md` | `799637f43001e6067ee458330a860def54ad6bde02aec878de18c2fbd38a2451` |
| `out/V3-REVIEW.json` | `79157968698009487083fd1bf5091c5f2f0e9463a556d2c4327afefacca76528` |
| `out/V3-REVIEW.md` | `b268fe785518ccb9fa125e5dff2ff9530ce5451353618a5225e0b6e080c92fae` |
| `scratch/v4-diagnostic-binding.json` | `3059b4325b3a7c3b115dbdcfe16ffd8fee438c5e182f0245ee1e67d7eeb9076c` |
| `scratch/v4-repo/eegt/repeated.py` | `5f39bbd820147fb4d4d1df715cd5b818c8fd9f3be46797cf090098812105b6c3` |
| `scratch/v4-repo/eegt/validation_intake.py` | `5429ea4e10da40ccafdf3d1baacdcd0d8f1f8edb5dba787443bb1a6182a1b2a8` |
| `scratch/v4-repo/eegt/validation_study.py` | `31568d7d54fd363bc0030bf28af999f6757ba02d45cd0dd13bbb7060aa97cdec` |
| `scratch/v4-repo/protocol/corpus-manifest-013.json` | `533ec22c1bae6d6a2e31c531d60ace463afd32513d7dc24129f17c489f2cb7d3` |
| `scratch/v4-repo/protocol/engineering-input-013.json` | `93d4769d8d1653f26ed4c64bfaf312083f1e0511a47fb830c4319d2a5326fe17` |
| `scratch/v4-repo/protocol/experiment-013.json` | `680b442a3d3cb556748c541e3f50ab8711164b95ef6deff170e1d12c1c5bf9f9` |
| `scratch/v4-repo/tests/test_validation_intake.py` | `ad9ca755e75e90ce274a49b3f19d4d5b7632e016354ce2a0be377f3912b122f3` |
| `update-root-v3/eegt/validation_intake.py` | `e103cfb1d1b45a649f9446d3b4f1e9f7580c510b129e13efcac6b0641eab1225` |
| `update-root-v3/failure-evidence/qualify-amendment-full.resource.log` | `a526b560d979c18e320340fccae870d40d96885b9836d77ae85b13af25d093e3` |
| `update-root-v3/failure-evidence/qualify-memory-trace.log` | `908e494671c07948166f2385a5cbe8070726bc05352eed37a4b0a040fa1506cc` |
| `update-root-v3/results/013/RUN-SOURCE-MANIFEST.json` | `d1eaf8101bf2c11ba17baf3f1afa05af29e9dd5bfb4bede361f84a949d661dad` |
| `update-root-v3/tests/test_validation_intake.py` | `99bef8f1f68e407fa01d2415f101b6677d5534161b06ad4b20f750a63cb6e4c2` |
| `update-root-v4-regression/INPUT-MANIFEST.json` | `b53be427d230285e072e2540771f4ff127ac7b91d37bf5f9c74081948befe6ee` |
| `update-root-v4-regression/local-tests.log` | `a942b01338d9d6aed44d06dda2720e7ae3e912a2b3d25fbb1f68a63bceca8866` |
| `update-root-v4-regression/test_validation_intake.py` | `ad9ca755e75e90ce274a49b3f19d4d5b7632e016354ce2a0be377f3912b122f3` |
| `update-root-v4/INPUT-MANIFEST.json` | `a80347f0771f01162e346b1b3ce80389088bae75b22a662024b6ade10708f612` |
| `update-root-v4/eegt/validation_intake.py` | `5429ea4e10da40ccafdf3d1baacdcd0d8f1f8edb5dba787443bb1a6182a1b2a8` |
| `update-root-v4/local-tests.log` | `55064e952a17678705be90e29d2ceb59439eeb5917cba7f1a124ca03b0305bac` |
| `update-root-v4/tests/test_validation_intake.py` | `a4c0bd0eeeabc60379af7c036b9ef3f02ecedcc8d8ef03d23a9180368ad6e90a` |

## Raw independent evidence (SHA256)

| File | SHA256 |
| --- | --- |
| `out/raw/v3-runtime.json` | `0b0c0d76eb9e5e904a551452d5b9a332f0a6a29ad1c2401710e0df8868a3a7ae` |
| `out/raw/v4-fixture-probe.log` | `06551838eab23105bec30401f06046b2cab01d8b182fce64e972fcc4aec03fcb` |
| `out/raw/v4-focused-tests.log` | `9b48a8ad237b8d205f7fd0f275f053fe7fd9da6b62139bd88867d3ad33fdc7bf` |
| `out/raw/v4-packet-audit.json` | `7950e66a5fdce2e5886f49bbd5e0d519e24002559cdc1174d36a4c665fab5c8c` |
| `out/raw/v4-regression-red-on-v3.log` | `5b99c7def736300468e06a39c08805d7a9601e7fc6a50c9f2969f42a143ce7cb` |
| `out/raw/v4-source.diff` | `7001a24795f6619b7711c82d3e93f799c5b07755d61891bc6476c1f2d5615026` |
| `out/raw/v4-test.diff` | `98489261f4bb04f962e77093ebd842d315e1e74e676242a7a31870a9d1d969d8` |
| `scratch/v3_fixture_probe.py` | `b62cdfb558deec26972424fb68f75c9702268124d90e1c2c9879945bcc87cefe` |
| `scratch/v4_audit.py` | `12b224b5182f30bc929760eeeb371b8cad11aa4d921b259fe43489aff5cda5b7` |
| `scratch/v4_fixture_probe.py` | `033c2f0859ca4c734e815680fa2b3f817902cf7a97cdd87f52d0d3b573a1d931` |

Dollar cost: **UNKNOWN**. No paid per-window API, reserve waveform, empirical resume, canonical source mutation, publication or parent closure.
