# Experiment013 v3 independent source-correction review

**CHANGES_REQUIRED.** The fresh-process qualification preserves the ten archived output fields and stays below 2 GiB on repeated reads of the exposed 008/001/001 fixture. Its CPU gate omits measurable worker CPU after the child's pre-send resource snapshot.

This reviews only the v3 delta against the accepted v2 correction. The accepted v2 review remains intact. Root owns canonical source, amendment002, admissions and empirical execution.

## Required change

`_qualification_process` samples `RUSAGE_SELF` before `connection.send` and process teardown. `_qualify_record_isolated` joins the child but passes that earlier CPU value to `IntakeResources`. In two exposed-fixture child reads, the complete reaped-child CPU exceeded the reported worker CPU by 0.129805 and 0.132184 seconds (0.261989 total). The v3 aggregate reported 4.553531 seconds; complete parent plus reaped-child CPU was 4.815520 seconds. A bound at 4.6845255 seconds would pass v3's snapshot and fail on actual total CPU. The accepted scientific bound remains 7,200 seconds and was not approached in this diagnostic; the issue is that the gate can undercount at its boundary. Count full child user plus system CPU after `join`, then apply the same bound.

## Independent checks

- The packet's declared five file hashes match. Applying `delta.patch` to a fresh scratch copy of exact v2 changes only `eegt/validation_intake.py` and `tests/test_validation_intake.py`, and the result hashes match the packet. The original protocol, source list, decoder and 2 GiB/one-worker/one-BLAS-thread limits remain exact.
- Pinned Python 3.12.14 corpus runtime: focused intake tests **11 passed, 1 skipped**; resource/provenance tests **7 passed, 9 subtests passed**. Root's `18 passed, 1 skipped` log is packet evidence only.
- Four sequential fresh child reads of the previously exposed Experiment008 sub-001/ses-001 fixture matched all ten archived qualification fields. Largest parent peak plus maximum child peak: **1,062,092,800 bytes**. Known decoder ValueError reason matched; an unexpected TypeError stopped; child source drift stopped before result; no child remained after the crash.
- Preserved second-failure log reports **2,420,178,944 bytes** against **2,147,483,648 bytes**. The trace's last reported record peak was 2,417,770,496 bytes. No quality or model outcome exists.
- The supplied accepted run manifest is the **prior v2 seal** (SHA256 `d1eaf8101bf2c11ba17baf3f1afa05af29e9dd5bfb4bede361f84a949d661dad`); it does not bind either v3 changed source. The fixture binding here is explicitly diagnostic only. An additive amendment002 and fresh staged admissions remain root work after source acceptance.

## Exact reviewed file inventory (SHA256)

| File | SHA256 |
| --- | --- |
| `AMENDMENT-CONTRACT.md` | `31f6673062635f688a011d69e63d5bda0937c7c7277c5ab94d9cbd0417196335` |
| `PLAN.md` | `aafdb2e104e2b70cc518dfe68fecb21fe9ad9171277f90d28d234cab8df6a981` |
| `evidence/qualification-output.json` | `beaaf226d72b9988b6893a9a8f95809a8e8dc95fdbc3e45d635023555355ede0` |
| `out/REVIEW.json` | `c541d61d2a2d824afbe4f1ebcf70b46f738fc2bdc0eff689d18995f04fd6081f` |
| `out/REVIEW.md` | `799637f43001e6067ee458330a860def54ad6bde02aec878de18c2fbd38a2451` |
| `scratch/v3-diagnostic-binding.json` | `3c9df28613eab51b5ea1a3a5106d7900f768cfadc594b0bbc6e0f359976e38b6` |
| `scratch/v3-repo/eegt/repeated.py` | `5f39bbd820147fb4d4d1df715cd5b818c8fd9f3be46797cf090098812105b6c3` |
| `scratch/v3-repo/eegt/validation_intake.py` | `e103cfb1d1b45a649f9446d3b4f1e9f7580c510b129e13efcac6b0641eab1225` |
| `scratch/v3-repo/eegt/validation_study.py` | `31568d7d54fd363bc0030bf28af999f6757ba02d45cd0dd13bbb7060aa97cdec` |
| `scratch/v3-repo/protocol/corpus-manifest-013.json` | `533ec22c1bae6d6a2e31c531d60ace463afd32513d7dc24129f17c489f2cb7d3` |
| `scratch/v3-repo/protocol/engineering-input-013.json` | `93d4769d8d1653f26ed4c64bfaf312083f1e0511a47fb830c4319d2a5326fe17` |
| `scratch/v3-repo/protocol/experiment-013.json` | `680b442a3d3cb556748c541e3f50ab8711164b95ef6deff170e1d12c1c5bf9f9` |
| `scratch/v3-repo/tests/test_validation_intake.py` | `99bef8f1f68e407fa01d2415f101b6677d5534161b06ad4b20f750a63cb6e4c2` |
| `update-root-v2/eegt/validation_intake.py` | `eb9cdbe5bc464d7ff4f3a56ab5c0bacd8189933e174d50b1c6f50ec05bd0b4cf` |
| `update-root-v2/tests/test_validation_intake.py` | `5431a2a821e80af6df62e068f4dc5a5bccfd6c73357c10600d770c79f5ac195b` |
| `update-root-v3/INPUT-MANIFEST.json` | `0c43c28957149598ed1fe261c4d7fe75ec757e292badf998cce215bcb6414aae` |
| `update-root-v3/delta.patch` | `b081105cd4bf7f6a4b674404ab6658d852574b4f1072282ae80bdf516d519bab` |
| `update-root-v3/eegt/validation_intake.py` | `e103cfb1d1b45a649f9446d3b4f1e9f7580c510b129e13efcac6b0641eab1225` |
| `update-root-v3/failure-evidence/qualify-amendment-first.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `update-root-v3/failure-evidence/qualify-amendment-first.resource.log` | `8a3eecb3f422448fd8a93675f439059098598ca7e44bd7258196af2ffb786a65` |
| `update-root-v3/failure-evidence/qualify-amendment-full.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `update-root-v3/failure-evidence/qualify-amendment-full.resource.log` | `a526b560d979c18e320340fccae870d40d96885b9836d77ae85b13af25d093e3` |
| `update-root-v3/failure-evidence/qualify-memory-trace.log` | `908e494671c07948166f2385a5cbe8070726bc05352eed37a4b0a040fa1506cc` |
| `update-root-v3/local-tests.log` | `b91c24b98df34b94062f5874676b5a9596e3e2a5ca4a059a6134c64d164eb019` |
| `update-root-v3/results/013/RUN-SOURCE-MANIFEST.json` | `d1eaf8101bf2c11ba17baf3f1afa05af29e9dd5bfb4bede361f84a949d661dad` |
| `update-root-v3/tests/test_validation_intake.py` | `99bef8f1f68e407fa01d2415f101b6677d5534161b06ad4b20f750a63cb6e4c2` |

## Raw independent evidence (SHA256)

| File | SHA256 |
| --- | --- |
| `out/raw/v3-cpu-audit.json` | `bcb1450c3ad9bda42f10b496e509dbc1442c2031a0214b95f8a22b4ef295e330` |
| `out/raw/v3-cpu-crosscheck.log` | `23056a531a3507f14db6dad031e7dac6ea9b9b9ff9d85c44dec249e7c374e3be` |
| `out/raw/v3-fixture-probe.log` | `b52b945642d2f41845f71c0a06110f4e32dabd1dddfc8d551a89c148f0cee81f` |
| `out/raw/v3-focused-tests.log` | `f0dca88eabf7d2f141cb376c6c8d2a1a36b9c258d104e421617b5000e9f6ab91` |
| `out/raw/v3-packet-audit.json` | `5e8a21e85ceb847e860065495370d59a889642b526b350084284a4d46fc9b2c0` |
| `out/raw/v3-resource-provenance-tests.log` | `742bb66502d6b0b86d42663840e28ab0f0c651ce8325b855fd299a147e0360a3` |
| `out/raw/v3-runtime.json` | `0b0c0d76eb9e5e904a551452d5b9a332f0a6a29ad1c2401710e0df8868a3a7ae` |
| `scratch/v3_audit.py` | `0fd38d44e1c023f17f3987e4ada45cce9d38a584f70babeec54c2703dcf2341d` |
| `scratch/v3_cpu_audit.py` | `cacbea796465982c7e5102eb5e31fa8370f556acb3e8b77e811415d27d1d8b81` |
| `scratch/v3_fixture_probe.py` | `b62cdfb558deec26972424fb68f75c9702268124d90e1c2c9879945bcc87cefe` |

Scope: source-correction acceptance only. The exposed fixture does not establish varied 20-record fit. Original pre-access seal, failed attempts and the original unknown-subset technical exposure remain preserved. No reserve source was read, no empirical stage resumed, and no canonical source was changed. Dollar cost: **UNKNOWN**; no paid per-window API was used.
