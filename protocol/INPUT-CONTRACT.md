# Numeric input contract v2

`NumericRecording` accepts only `samples_uv` (channels by native sample, calibrated microvolts), `sample_rate_hz`, and `valid_samples` (engineering integrity). Channel position is an ordered integer axis. No identity, source name, date, task, stage, narrative, diagnostic or semantic field is accepted. Unknown fields fail closed. Inputs are copied and immutable. The discovery functions consume arrays only; grouping and provenance live in a separate acquisition/evaluation process.

The model cannot be promised freedom from all indirect information: voltage and hardware artifacts can themselves encode subject or device differences. “Anonymous” here means explicit metadata exclusion, not a guarantee of biological anonymity. The public sources already use pseudonyms. Their source IDs remain in a separate provenance table for scientific audit and disjoint grouping.

The MW75 adapter accepts already decoded 12-channel, 500 Hz microvolt arrays with an explicit verified contact order and per-sample integrity mask. It refuses other rates, channel counts, orders, units or missing integrity. This is an import contract, not a Bluetooth decoder or evidence that a physical headset was tested. REF/DRL/IMU are not silently treated as EEG. Contact positions and reference remain provenance; channelwise discovery avoids invented correspondences across layouts.

Raw source samples remain unchanged. Experiment 002 explicitly analyzes a fixed slice and performs a fixed bandpass/resampling transform. “Raw” therefore means no identity/meaning labels guide discovery; it does not mean no signal processing occurred. Preprocessing and its numerical assumptions are public.

Protocol `experiment-002.json` is frozen before waveform inspection or fitting. A change requires a new numbered version or an explicitly logged amendment. Token names are neutral integers. Algorithms authored by an LLM are not automatically independent LLM discoveries, and no result here establishes a universal brain language.
