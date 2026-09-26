# Experiment 011 worker report

**State:** Ready for Root’s independent review. No publication or external message was made.

The fixed 010 selection supplied 122 previously exposed 30-second blocks (3,660 seconds) from six people. Five had at least three paired-valid blocks in both sessions; person 003 remained descriptive because session 001 had one selected block. Both encoders produced finite metrics on all 122 blocks. CBraMod ran exactly 610 new forwards; CodeBrain was reused from its 010 archive.

| Primary paired effect | Mean of five person effects | Original rho on paired support | Phase rho on paired support | Exact two-sided p | Two-test corrected p |
|---|---:|---:|---:|---:|---:|
| geometry | 0.071326 | 0.170742 | 0.100801 | 0.0625 | 0.125 |
| change | 0.094719 | 0.193987 | 0.137454 | 0.0625 | 0.125 |

Each block effect is its original cross-model Spearman rho minus the rho on the **same paired phase-scrambled block**. Recording medians are computed on these block differences, then the two session medians are averaged for each person. The reported original and phase summaries use identical paired support, but their separately taken medians need not subtract to the median of block differences. The exact sign-flip test enumerated 32 assignments for five people; its smallest possible two-sided p is 0.0625, or 0.125 after correction. The positive observed effects do not establish a population effect.

## Descriptive cross-model controls

| Variant | Geometry mean person rho | Change mean person rho | Valid blocks |
|---|---:|---:|---:|
| original | 0.170742 | 0.193987 | 122 |
| gain_half | 0.172816 | 0.218895 | 122 |
| polarity_flip | 0.172099 | 0.207692 | 122 |
| channel_reverse | 0.144539 | 0.133455 | 122 |
| independent_phase | 0.100801 | 0.137454 | 122 |

The [summary](../repo/results/011/summary.json) and [SQLite ledger](../repo/results/011/analysis.sqlite) retain every block, recording and person result: all five cross-model variants, four within-model controls for each model, and three descriptor views for each model. They include exact abstention and exclusion fields, source candidate statuses, and both primary tests. The ledger has 5,760 candidate rows, 1,220 model-output hash rows, 610 cross-model rows, 976 within-model rows, 732 descriptor rows, 244 paired rows and 60 aggregate statistics. SQLite integrity and foreign-key checks passed. No secondary p-values were computed.

## Inference and reproducibility

The [run manifest](../repo/results/011/run-manifest.json) was frozen before CBraMod inference (SHA-256 `60ac1312851e60017dc7e21c89f5570ebb36c1288354a69822db74d1fc3c590a`). The accepted checkpoint matched its pinned 19,775,842 bytes and SHA-256. The [inference receipt](../repo/results/011/inference.json) records each input/output hash and forward time; the [full latent grid](../repo/data/derived/011/embeddings.npz) is float32 `[122,5,4,30,200]`. The run took 72.95 seconds wall time, peaked at 524.1 MiB process RSS, and used one Torch/BLAS numerical thread. Python 3.12.14, PyTorch 2.4.1, NumPy 1.26.4 and SciPy 1.14.1 were used. Native agent dollar cost is UNKNOWN.

The final offline evaluation and a fresh reproduction both ran with **no checkpoint file** in the packet. [Both summaries](../repo/results/011/offline-reproduction/summary.json) and both SQLite databases are byte identical; the recursive scientific comparison passed at 1e-12. The final synthetic gate is [9 passed](tests-final.log). Commands and logs are listed in [commands.txt](commands.txt). The source/result SHA-256 and byte inventory is [FILES.json](FILES.json).

## Post-inference analysis amendment

The first evaluation failed at SQLite JSON writing because a valid-block count was a NumPy integer. The [failed database partial](../repo/results/011/analysis-failed-1.partial), traceback and original source are preserved. A type-only cast repaired serialization. A later reproduction check exposed an unnecessary checkpoint-file requirement in offline validation; that requirement was removed while retaining the pinned checkpoint identity in the inference receipt. The [amendment](../repo/results/011/analysis-amendment.json) and [diff](analysis-amendment-final.diff) record both post-inference code changes and the original manifest. No extra model forward ran, and comparison with the preserved earlier evaluation found identical scientific values. The final analysis source hash differs from the pre-inference manifest; Root should review that exception explicitly.

## Interpretation and limits

On this exposed development sample, the encoders had modest positive within-block agreement, with larger paired agreement on original inputs than on independently phase-scrambled inputs. The phase transform preserves per-channel Fourier magnitude and is a nuisance comparator, not a biological null. Shared architecture or pretraining material, waveform processing, four-ear-channel mapping, device effects and artifacts can explain agreement. The inherited 60 Hz notch does not specifically remove this dataset’s 50 Hz mains. These results say nothing about semantic meaning, diagnosis, universal tokens, unseen people, or physical Neurable transfer. Participants 007–010 and unexamined later sessions remained unopened.

## Licensed sources for Root’s note

- [EESM23 ds005178 v1.0.0](https://openneuro.org/datasets/ds005178/versions/1.0.0) — publisher metadata in `protocol/corpus-manifest-008.json` declares CC0.
- [CodeBrain code, pinned commit](https://github.com/jingyingma01/CodeBrain/tree/22d350caf68246d2fda4f630ef837420db3fb130) and [checkpoint revision](https://huggingface.co/YjMajy/CodeBrain/tree/bef08d2fdb1759685371cc635aad21ce59163689) — Apache-2.0 notices are retained in the repo.
- [CBraMod code, pinned commit](https://github.com/wjq-learning/CBraMod/tree/b9e961003214326972c567eff390e75b0287e32a/models) and [checkpoint revision](https://huggingface.co/weighting666/CBraMod/blob/500543c7e30bda1b22bfd51a49301b238dee21fd/pretrained_weights.pth) — vendored code is MIT with a local notice; the checkpoint model card declares Apache-2.0.

Root owns independent review, integration, Research Note 011 and release.
