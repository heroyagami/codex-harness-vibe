import json
import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.reporting import build_production_report
from legal_auto_motion.state import StateGraph


class ReportingTests(unittest.TestCase):
    def test_report_aggregates_nested_agent_calls(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            scene = run / "scenes" / "scene-001"
            scene.mkdir(parents=True)
            graph = StateGraph(scene / "scene-state.json")
            call_id = graph.begin_call(
                role="scene_worker", provider="claude", model="fable", estimated_cost_usd=0.25
            )
            graph.finish_call(call_id, status="complete")

            report = build_production_report(run)

            self.assertEqual(report["summary"]["calls"], 1)
            self.assertEqual(report["summary"]["estimated_cost_usd"], 0.25)
            self.assertEqual(report["by_role"]["scene_worker"]["calls"], 1)
            self.assertTrue((run / "reports" / "production-metrics.json").exists())
            saved = json.loads((run / "reports" / "production-metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["summary"]["failed_calls"], 0)


if __name__ == "__main__":
    unittest.main()
