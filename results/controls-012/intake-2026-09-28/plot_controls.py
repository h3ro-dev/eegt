"""Render accepted-receipt arithmetic only; no event, waveform or model access."""
import hashlib
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
EMPIRICAL = HERE.parent / "empirical"
stages = [json.loads((EMPIRICAL / name).read_text()) for name in ("FIRST-UNIT.json", "REMAINING.json")]
assert all(stage["status"] == "COMPLETE" for stage in stages)
assert stages[0]["protocol_sha256"] == stages[1]["protocol_sha256"]
rows = [row for stage in stages for row in stage["rows"]]
assert len(rows) == 12 and len({row["array_row"] for row in rows}) == 12
people = sorted({row["source_subject"] for row in rows})
assert len(people) == 6
raw, control = [], []
for person in people:
    selected = [row for row in rows if row["source_subject"] == person]
    assert len(selected) == 2 and {row["session"] for row in selected} == {"001", "002"}
    raw.append(statistics.mean(row["by_tolerance"]["0.025"]["raw_recomputed_f1"] for row in selected))
    control.append(statistics.mean(row["by_tolerance"]["0.025"]["null_summary"]["median"] for row in selected))

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.hashsalt": "eegt-density-controls-20260928"})
fig, ax = plt.subplots(figsize=(10, 6.4))
fig.subplots_adjust(top=.76, bottom=.26, left=.10, right=.96)
for i, (a, b) in enumerate(zip(raw, control)):
    ax.plot([b, a], [i, i], color="#b2b9c2", linewidth=2, zorder=1)
ax.scatter(control, range(6), s=65, color="#666666", label="Original vs retimed phase events", zorder=3)
ax.scatter(raw, range(6), s=65, color="#1266a4", label="Original vs phase-randomized EEG", zorder=3)
ax.set_yticks(range(6), [f"P{int(person):02d}" for person in people])
ax.invert_yaxis()
ax.set_xlim(0, 1)
ax.set_xlabel("F1, mean of two session-specific blocks")
ax.set_ylabel("Source-local person")
ax.grid(axis="x", alpha=.2)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(loc="lower left", bbox_to_anchor=(-.005, 1.05), frameon=False, fontsize=10)
fig.suptitle("Landmark matching under a conditional timing control", x=.10, y=.97, ha="left", fontsize=17, fontweight="bold")
fig.text(.10, .91, "6 previously exposed people · 12 sessions · 12 existing 30-second blocks", fontsize=11)
fig.text(.10, .87, "25 ms matching tolerance; 99 timing draws per block. Descriptive, without a population test.", fontsize=10)
fig.text(.10, .16, f"Equal-person means: raw {statistics.mean(raw):.4f}; mean block-null median {statistics.mean(control):.4f}; gap {statistics.mean(raw)-statistics.mean(control):.4f}.", fontsize=11)
fig.text(.10, .115, "Retiming preserves 1-second-bin event counts and support widths, but breaks fine spacing and waveform constraints.", fontsize=9)
fig.text(.10, .080, "Positive gaps do not establish neural origin or meaning. The other 110 source blocks were not analyzed here.", fontsize=9)
fig.savefig(HERE / "density-control.png", dpi=180, metadata={"Software": "EEGT receipt-only plot"})
fig.savefig(HERE / "density-control.svg", metadata={"Date": None})
plt.close(fig)
manifest = {
    "schema": "eegt-receipt-only-figure/v1",
    "inputs": {name: hashlib.sha256((EMPIRICAL / name).read_bytes()).hexdigest() for name in ("FIRST-UNIT.json", "REMAINING.json")},
    "person_raw": dict(zip(people, raw)),
    "person_mean_block_null_median": dict(zip(people, control)),
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "outputs": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in ("density-control.png", "density-control.svg")},
    "scope": "Visualization of completed receipts only; no new numerical experiment or waveform access.",
}
(HERE / "FIGURE-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Receipt-only figure written; no experimental rerun.")
