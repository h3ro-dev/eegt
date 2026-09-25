# CodeBrain EEGSSM adapter handoff

**Result:** The pinned CodeBrain stage-2 backbone runs on CPU through `CodeBrainEncoder`. This lane ran synthetic arrays only. The real-data numeric protocol and all scientific comparisons remain with the EEGT root.

## Files and continuation paths

- Copy `pretrained.py` to `eegt/pretrained.py` and the three files in `vendor/codebrain/` to `eegt/vendor/codebrain/`. Existing `eegt` package initialization can remain as it is. `test_pretrained.py` imports that final package path.
- Exact official checkpoint on Studio4: `/Users/codynewreward/lanes.noindex/eco-uzwh8s.23/scratch/CodeBrain.pth` (60,901,006 bytes; SHA-256 `d9714b8732c9883a04d022ee66254cd578ae1fa27f5458e6ab7f1aa96e9a7352`). Keep it outside the source release.
- Tested isolated Python: `/Users/codynewreward/lanes.noindex/eco-uzwh8s.23/scratch/venv/bin/python` (Python 3.12.14, Torch 2.4.1). `requirements-encoder.lock` records all installed versions. These paths are local to Studio4 and suitable for continuation in this lane.
- `MODEL-RECEIPT.json` has hashes, checkpoint keys and parameter counts, native model/effort evidence, test details and performance. `checkpoint-keys.tsv`, `vendor.patch`, `test-output.txt`, and `benchmark.json` are supporting evidence.

## Source and exact compatibility changes

The vendored source is [jingyingma01/CodeBrain at commit 22d350c](https://github.com/jingyingma01/CodeBrain/tree/22d350caf68246d2fda4f630ef837420db3fb130). The only source modifications are `from Models.SGConv` to the relative import `from .SGConv`, and the local attention mask transfer from `.cuda()` to `.to(h_s.device)`. `SGConv.py` and the [Apache 2.0 LICENSE](https://github.com/jingyingma01/CodeBrain/blob/22d350caf68246d2fda4f630ef837420db3fb130/LICENSE) are byte identical to the archive. No learned weights or arithmetic were changed.

The architecture arguments come from `Pretrain/pretrain_EEGSSM.py`: 200 input/output/model channels, eight residual layers, `s4_lmax=570`, `s4_d_state=64`, bidirectional GConv, and 4096-size temporal/frequency heads. `if_codebook=False` selects its existing full-feature return branch; all 269 checkpoint tensors, including both unused codebook heads, load with `strict=True`. The original feature branch calls `squeeze()`, so batch one returns `[4,30,200]` while batch two returns `[2,4,30,200]`. The adapter restores only the missing batch axis for batch one. It never pools patch or channel features.

The official [CodeBrain.pth](https://huggingface.co/YjMajy/CodeBrain/blob/bef08d2fdb1759685371cc635aad21ce59163689/CodeBrain.pth) was verified by exact size and SHA-256 before `torch.load(weights_only=True, map_location="cpu")`. Every key had the single `module.` prefix saved by DataParallel; the adapter removes exactly that prefix and refuses any other wrapper. No unsafe pickle fallback or checkpoint training was used.

## Verification

Seven tests passed in the scratch package matching `eegt` paths. They cover strict load and frozen eval parameters; batch-one and batch-two float32 shapes; finite zero, sine and noise outputs; bitwise repeated-output determinism; batch versus single outputs (`atol=rtol=2e-5`); malformed shape, channel/patch permutation, dtype and nonfinite refusal; same-size checkpoint tamper refusal before `torch.load`; one-position attention mask values; and a full CPU forward against the original pinned source (`atol=rtol=1e-6`). For the original CPU reference alone, the test makes the original `.cuda()` mask transfer a no-op; its numerical code remains unchanged. The test also checks that forward runs inside `inference_mode`.

Run from this lane with `PYTHONPATH=$PWD/scratch/pkg`, `CODEBRAIN_CHECKPOINT=$PWD/scratch/CodeBrain.pth`, `CODEBRAIN_UPSTREAM_ZIP=$PWD/input/codebrain.zip`, `TMPDIR=$PWD/scratch/tmp`, and `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1` before `scratch/venv/bin/python -W default out/test_pretrained.py`. The final run recorded `Ran 7 tests ... OK` in `test-output.txt`.

For one `[1,4,30,200]` synthetic 30-second window after one warmup, five forwards had median wall time **1.480 s** (range 1.171–1.570 s), median process CPU time **0.337 s**, and peak/current RSS **373.97 MiB**. Torch intraop and interop were each 1; the process showed one `ps -M` thread row after warmup. This stayed within the initial 2 GiB / one numerical CPU demand; scratch usage was 0.85 GiB, below the 2 GiB disk bound. The retained checkpoint and uv cache total less than 0.5 GiB; exact network transfer bytes were not logged. Full timings are in `benchmark.json`.

Torch issued the upstream `weight_norm` deprecation and the `dropout2d` 3D-input behavior warning. Warnings were not globally suppressed. The `dropout2d` operation is inactive in eval mode, but the source arithmetic remains untouched.

One input manifest entry differs: `input/fleet-context.json` is 249,113 bytes in both places, but the manifest lists SHA-256 `da5662cbc45e19961b94d00e1f7828f780c8ff32284520323d6620eb1c4e8b3f`, while the present file is `ddc8dbe440c214411a71c77036bb12e485015186b0b051da1d44c120605b88ab`. Its timestamp predates this session. The root confirmed this was a telemetry refresh after manifest generation; the CodeBrain ZIP and all other input entries match their manifests. This lane did not edit `input/`.

## Interface boundary

`encode` accepts only finite NumPy `float32` `[B,4,30,200]` arrays with `B>=1`, already preprocessed and scaled by the caller in microvolts/100. It returns finite NumPy `float32` arrays of the same shape. It has no names, coordinates, identity or task fields. The official spatial kernel spans 19 channel positions and operates on the four supplied channel slots; the adapter cannot validate spatial meaning. No real EEG, task output, or scientific transfer claim was evaluated here.
