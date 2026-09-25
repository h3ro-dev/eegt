# Research Notes · Experiment 007

Date: 2026-09-25. State: frozen transfer evaluation computed.

The split uses source participants 001–024 for fitting, 025–030 for validation reporting and 031–036 for same-source tests. Sleep records form an external dataset; 001/003 were previously explored and remain separated from the other 17. There is one recording per participant in these snapshots: repeated-session reliability and verified device transfer remain unmeasured.

Held-out means a participant did not teach the detector its reference or thresholds. It does not prove independence from an LLM's pretraining, erase earlier exploration, or establish the absence of a shared person across public archives.

| Group | Shape changes/min | Spectrum changes/min | Coordination changes/min |
| --- | --- | --- | --- |
| train | 1.739 [1.506, 2.342]; n=24 | 2.296 [1.696, 2.908]; n=24 | 2.019 [1.666, 2.708]; n=24 |
| validation | 1.985 [1.141, 2.306]; n=6 | 2.087 [1.114, 4.636]; n=6 | 1.814 [1.542, 3.719]; n=6 |
| test | 1.610 [1.131, 2.023]; n=6 | 2.670 [1.197, 3.163]; n=6 | 1.932 [0.840, 2.915]; n=6 |
| external_exposed | 11.852 [10.394, 13.309]; n=2 | 13.221 [11.157, 15.285]; n=2 | 1.629 [1.160, 2.099]; n=2 |
| external_unexposed | 12.398 [7.366, 15.019]; n=16 | 8.747 [7.271, 13.197]; n=16 | 2.013 [1.604, 2.982]; n=16 |

Rates use eligible scored-window centers × 0.5 seconds as exposure, not raw wall-clock time. Entries are per-record medians with descriptive participant-bootstrap 95% intervals. No labels exist to turn these rates into accuracy, sensitivity or specificity. A changed rate on sleep data can reflect acquisition, channel count, reference, artifact mix or actual physiological differences.

| Group | Records | Valid/all multichannel windows | Shape / spectrum F1 | Shape / coordination F1 | Spectrum / coordination F1 |
| --- | --- | --- | --- | --- | --- |
| train | 24 | 230,452/232,332 | 0.387 [0.335, 0.432]; n=24 | 0.453 [0.418, 0.511]; n=24 | 0.341 [0.287, 0.396]; n=24 |
| validation | 6 | 53,765/54,089 | 0.400 [0.316, 0.460]; n=6 | 0.474 [0.322, 0.550]; n=6 | 0.400 [0.287, 0.504]; n=6 |
| test | 6 | 53,535/53,802 | 0.270 [0.213, 0.347]; n=6 | 0.369 [0.277, 0.470]; n=6 | 0.288 [0.220, 0.300]; n=6 |
| external_exposed | 2 | 121,110/175,610 | 0.566 [0.546, 0.586]; n=2 | 0.163 [0.121, 0.205]; n=2 | 0.143 [0.095, 0.191]; n=2 |
| external_unexposed | 16 | 618,537/1,092,838 | 0.487 [0.468, 0.592]; n=16 | 0.245 [0.192, 0.271]; n=16 | 0.207 [0.198, 0.227]; n=16 |

These are LLM-authored numerical representations, not independent pretrained LLMs discovering a language. F1 measures timing agreement within one second; it is not accuracy against brain-state labels. Neither high agreement nor a change score establishes semantic meaning, a diagnosis or universal geometry.

[Protocol](../protocol/experiment-003.json) · [Methods](../protocol/transition-methods.md) · [Per-record main results](../results/003/summary.json) · [Control results](../results/006/summary.json) · [Transfer summary](../results/007/summary.json) · [Release downloads](https://github.com/h3ro-dev/eegt/releases)
