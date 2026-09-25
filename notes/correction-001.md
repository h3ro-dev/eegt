# Correction and scope update for Experiment 001

2026-09-24. The historical Experiment001 note is retained verbatim. Two descriptions need precision:

1. “Untouched external split” means **held out from codebook fitting**. The wider project had previously exposed source data; this was not a new, globally unseen corpus.
2. The metric key `within_record_channel_shuffle_cross_entropy_bits` uses **temporal shuffling within each contiguous accepted span for a recording/channel**, then evaluates adjacent shuffled tokens. It does not permute channels. The original note's phrase “within-record channel-shuffle control” was ambiguous. The measured numbers are unchanged.

The original note's proposed next datasets are historical. James's revised scope prioritizes around-ear EEG compatible with Neurable acquisition and defers meaning/independent-replication studies. Experiment002 uses public ds004015 and ds005207 cEEGrid data under the revised protocol. Its results must not be described as a controlled coverage improvement over Experiment001.
