# EEGT public research notebook

This is a static site. Publish `index.html`, `styles.css`, `script.js`, `favicon.svg`, and `data/` together. It has no package install, build step, remote font, or absolute asset path.

For local preview, run `python3 -m http.server 8000` in this directory and open `http://localhost:8000/`. The page itself works without JavaScript; the optional Experiment 002 result needs HTTP so `fetch()` can read its JSON file.

## Add the verified Experiment 002 result

Create `data/experiment-002.json` only after the numerical outcome and referenced downloads have been checked. The page automatically replaces its pending message and updates the note badge. Use this shape:

```json
{
  "status": "verified status",
  "headline": "verified numerical finding",
  "summary": "Brief interpretation with denominator and scope.",
  "metrics": [
    { "label": "Metric name", "value": "measured value", "detail": "Definition and denominator" }
  ],
  "downloads": [
    { "label": "Run manifest", "url": "./data/experiment-002-manifest.json" }
  ],
  "limitations": ["A limitation supported by the run evidence."]
}
```

`status`, `headline`, and `summary` must be nonempty strings. `metrics`, `downloads`, and `limitations` may be empty arrays. Download URLs may be relative to the page or HTTP(S); invalid schemes are skipped. Text is inserted as text, so JSON cannot add HTML. Keep linked files in the deployed directory or use verified public URLs. Do not put unverified outcome numbers in the JSON.

For another experiment, add an anchor-linked `<article>` in the Research Notes ledger, a corresponding JSON file in `data/`, and a loader based on `renderExperiment002` in `script.js`. State fixed inputs separately from results, keep a truthful pending state in the HTML, and update the downloads section if the result has released artifacts. Use only verified counts and document denominators.

## Scientific boundary

Experiment 001 is a historical, single-channel scalp-trained spectral baseline. Its source summary is `data/experiment-001.json`. Experiment 002 uses eight fixed-selected around-ear recordings and 600-second slices from 60 seconds onward. Source samples stay intact. Any filter, re-reference, resampling, or window setting must be fixed and documented with the run before reporting its outcome. Neither entry supports semantic, clinical, or hardware-validation claims.

The external dataset links point to OpenNeuro `ds004015` and `ds005207`. The repository links are set to <https://github.com/h3ro-dev/eegt> for the integration owner to verify. No custom domain is claimed.
