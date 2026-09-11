import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.benchmark import memory_ab_summary, summarize_run


class MemoryABBenchmarkTests(unittest.TestCase):
    def test_memory_ab_favors_better_memory_on_group(self):
        rows = [
            {"complete": True, "memory_variant": "memory_off", "critic_average": 13.0, "revision_calls_per_scene": 0.8, "failure_rate": 0.2, "estimated_cost_usd": 2.0, "repeated_motion_signature_runs": 1, "attention_failures": 2},
            {"complete": True, "memory_variant": "memory_on:quality_ranked", "critic_average": 15.0, "revision_calls_per_scene": 0.3, "failure_rate": 0.05, "estimated_cost_usd": 2.1, "repeated_motion_signature_runs": 0, "attention_failures": 0},
        ]
        report = memory_ab_summary(rows)
        self.assertEqual(report["verdict"], "memory_on_favored")
        self.assertEqual(report["variants"]["memory_off"]["runs"], 1)

    def test_summarize_run_reads_memory_variant(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            (run / "reports").mkdir()
            (run / "harness.toml").write_text("[memory]\nenabled = false\n", encoding="utf-8")
            row = summarize_run(run)
            self.assertEqual(row["memory_variant"], "memory_off")


if __name__ == "__main__":
    unittest.main()
