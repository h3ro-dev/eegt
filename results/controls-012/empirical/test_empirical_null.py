"""Synthetic-only checks of the proposed sealed-event adapter and matcher."""

from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from empirical_null import (ResourceStop, _checked_match, _partition,
                            descriptive_summary, digest, in_support,
                            order_summary, pooled_f1, resource_guard,
                            runtime_versions, seed_for)
from null_controls import timing_matched_control


def event(t, *, channel=0):
    return {"accepted": True, "seconds": float(t),
            "support_start_seconds": float(t)-.002,
            "support_end_seconds": float(t)+.002,
            "segment_key": "segment_0", "channel_key": f"channel_{channel}",
            "family": "extremum", "polarity": "peak",
            "direction": "positive_to_negative"}


class SyntheticAdapterTests(unittest.TestCase):
    def test_partition_digest_header_and_count_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "example.jsonl.gz"
            header = {"schema": "eegt-012-event-partition/v1", "event_rows": 2}
            rows = [event(.5), event(1.5)]
            with gzip.open(path, "wt") as handle:
                handle.write(json.dumps({"type": "header", "value": header})+"\n")
                for row in rows:
                    handle.write(json.dumps({"type": "event", "value": row})+"\n")
            entry = {"path": path.name, "sha256": digest(path), "bytes": path.stat().st_size,
                     "header": header, "event_rows": 2, "accepted_rows": 2,
                     "variant": "primary"}
            self.assertEqual(_partition(root, entry), rows)
            with self.assertRaisesRegex(ValueError, "PARTITION_HASH_MISMATCH"):
                _partition(root, {**entry, "sha256": "0"*64})
            with self.assertRaisesRegex(ValueError, "PARTITION_HEADER_MISMATCH"):
                _partition(root, {**entry, "header": {**header, "event_rows": 3}})
            with self.assertRaisesRegex(ValueError, "PARTITION_ROW_COUNT_MISMATCH"):
                _partition(root, {**entry, "accepted_rows": 1})

    def test_common_support_and_fixed_seed(self):
        self.assertTrue(in_support(event(1.), [(0., 2.)]))
        self.assertFalse(in_support(event(2.), [(0., 2.)]))
        seeds = [seed_for(4201200, row, channel, stratum, draw)
                 for row in (0, 112) for channel in range(4)
                 for stratum in range(4) for draw in range(99)]
        self.assertEqual(len(seeds), len(set(seeds)))

    def test_recomputed_match_parity_and_dense_chance(self):
        a = [event((i+.5)*.05) for i in range(100)]
        b = [event((i+.5)*.05) for i in range(100)]
        raw = _checked_match(a, b, [(0., 5.)], [(0., 5.)], .025)
        self.assertEqual(raw["agreement"], 1.)
        self.assertEqual(_checked_match(a, b, [(0., 5.)], [(0., 5.)], .025,
                                        raw)["matched"], 100)
        with self.assertRaisesRegex(ValueError, "ACCEPTED_MATCH_DIVERGENCE"):
            _checked_match(a, b, [(0., 5.)], [(0., 5.)], .025,
                           {**raw, "matched": 99})
        shuffled, receipt = timing_matched_control(b, support_intervals=[(0., 5.)],
                                                   bin_seconds=1., seed=1)
        chance = _checked_match(a, shuffled, [(0., 5.)], [(0., 5.)], .025)
        self.assertEqual(receipt["count_preserved"], 100)
        self.assertEqual(chance["n_b"], 100)
        self.assertGreater(chance["agreement"], .3)
        self.assertEqual(pooled_f1([chance]), chance["agreement"])

    def test_order_summary_and_person_denominators(self):
        summary = order_summary([i/100 for i in range(99)])
        self.assertEqual((summary["order_05"], summary["median"], summary["order_95"]),
                         (.04, .49, .94))
        self.assertEqual(order_summary([.5]*98)["status"], "NOT_ESTIMABLE")
        rows = [{"status": "OK", "source_subject": person, "session": session,
                 "by_tolerance": {"0.025": {"exploratory_excess_vs_null_median": value}}}
                for person, session, value in
                (("001", "001", .2), ("001", "002", .4), ("002", "001", .1))]
        denom = descriptive_summary(rows, planned_rows=12)
        self.assertEqual(denom["distinct_people"], 2)
        self.assertEqual(denom["distinct_person_sessions"], 3)
        self.assertEqual(denom["two_session_complete_people"], 1)
        self.assertEqual(denom["estimable_two_session_people"], 1)
        self.assertAlmostEqual(denom["descriptive_person_excess_25ms"]["001"], .3)
        self.assertEqual(denom["inference"],
                         "NONE; people and nights are described, blocks are not independent people")

    def test_runtime_identity_and_graceful_resource_refusal(self):
        self.assertEqual(runtime_versions(), {"python": "3.12.12", "numpy": "2.5.3",
                                              "scipy": "1.18.1"})
        with self.assertRaisesRegex(ResourceStop, "CPU_PREEMPTIVE_STOP"):
            resource_guard(-100000., 7200, 2*1024**3)
        with self.assertRaisesRegex(ResourceStop, "RSS_LIMIT_AT_DRAW_BOUNDARY"):
            resource_guard(0., 1000000000, 1)


if __name__ == "__main__":
    unittest.main()
