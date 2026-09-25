# EEGT v0.3.0 · Continuous EEG and transition geometry

This release expands the earlier 80-minute analysis to 54 technically qualified
continuous source recordings totaling 223.47 decoded sample-hours. The inventory
contains 55 recordings and 21,535,181,808 checksum-verified bytes. One source
remains quarantined for a duration discrepancy; its failure is visible.

The run produced 1,608,671 two-second multichannel windows, including 1,077,399
passing the engineering quality gate. Passing this gate is not proof that all
remaining variation comes from the brain. Windows overlap and are not people.

The three numerical views locate partly overlapping transitions. In the 16
previously unused external records, median timing F1 was 0.487 for waveform shape
versus spectrum, 0.245 for shape versus sensor coordination, and 0.207 for
spectrum versus coordination. These are one-second timing matches, not accuracy
against a known brain state. We have not established a universal geometry.

Phase randomization substantially changed the bounded control results, but it
also changed valid exposure and often left few or no detected events. The
published controls retain those denominators and matched-support rate changes.
They do not isolate biological meaning from every artifact or acquisition
feature. Time reversal is also imperfectly invariant under this detector; no
claim of causal brain dynamics follows from that asymmetry.

Research Notes 003, 004, 006 and 007 contain the methods and measurements.
Experiment 005 remains a prepared protocol for actual Neurable capture. The
next scientific priority is repeated sessions and verified raw device data,
followed by additional waveform descriptors and compatible independent learned
representations. Dataset/task/identity labels remain outside discovery inputs.

The release includes source code, frozen protocols, source and transition SQLite
databases, numeric feature arrays, per-record results, controls, tests and
checksums. Original 21.54-GB source files remain at their pinned public archives
with a reproducible downloader. Code is MIT; these CC0-source numeric derivatives
retain CC0 attribution. Earlier releases remain unchanged.

See [the results page](https://h3ro-dev.github.io/eegt/growth.html),
[database contract](../DATABASE.md), [reproduction commands](../README.md), and
[ordered next steps](../STRATEGY.md).
