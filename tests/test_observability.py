import json
import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.benchmark import compare_runs
from legal_auto_motion.failure_taxonomy import classify_failure
from legal_auto_motion.provenance import build_scene_provenance
from legal_auto_motion.state import StateGraph


class ObservabilityTests(unittest.TestCase):
    def test_failure_taxonomy_is_stable(self):
        self.assertEqual(classify_failure("429 rate limit exceeded", status="failed"), "provider_quota")
        self.assertEqual(classify_failure("scene-001 failed motion gate: freeze detected", status="failed"), "motion_quality")
        self.assertEqual(classify_failure("prompt exceeds context budget", status="failed"), "context_budget")
        self.assertEqual(classify_failure("sequence review rejected", status="failed"), "sequence_rejection")

    def test_scene_provenance_records_hashes_and_model_calls_without_raw_prompt(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            scene = run / "scenes" / "scene-001"
            (scene / "scenes").mkdir(parents=True)
            (scene / "artifacts").mkdir(parents=True)
            (scene / ".harness").mkdir(parents=True)
            (scene / "fact-contract.json").write_text(json.dumps({"grammar": "timeline", "subject": "规则"}), encoding="utf-8")
            (scene / "frame.md").write_text("frame", encoding="utf-8")
            (scene / "scenes" / "DefaultScene.tsx").write_text("export const x = 1", encoding="utf-8")
            (scene / "artifacts" / "creative-critique.json").write_text(json.dumps({"verdict": "pass", "total": 15, "scores": {"composition": 2}}), encoding="utf-8")
            (scene / ".harness" / "invocation-context.json").write_text(json.dumps({"policy_version": "scene-context-isolation-v1", "prompt_sha256": "abc", "raw_prompt": "DO NOT COPY"}), encoding="utf-8")
            graph = StateGraph(run / "harness-state.json")
            call = graph.begin_call(role="scene_worker", provider="claude", model="x", scope="scene-001")
            graph.finish_call(call, status="complete")

            manifest = build_scene_provenance(scene)

            encoded = json.dumps(manifest, ensure_ascii=False)
            self.assertEqual(manifest["critic"]["total"], 15)
            self.assertEqual(manifest["models"][0]["provider"], "claude")
            self.assertTrue(manifest["outputs"]["source_hash"])
            self.assertNotIn("DO NOT COPY", encoded)

    def test_benchmark_compares_completed_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runs = []
            for name, critic, revisions, cost in (("a", 15, 2, 1.2), ("b", 16, 0, 1.5)):
                run = root / name
                (run / "reports").mkdir(parents=True)
                (run / "completion-report.json").write_text(json.dumps({"status": "complete"}), encoding="utf-8")
                (run / "reports" / "production-metrics.json").write_text(json.dumps({"summary": {"calls": 4, "failed_calls": 0, "duration_seconds": 10, "estimated_cost_usd": cost}}), encoding="utf-8")
                (run / "reports" / "sequence-review.json").write_text(json.dumps({"status": "pass", "scene_count": 1, "rhythm": {"energy_range": 0.5}}), encoding="utf-8")
                (run / "reports" / "scene-provenance.json").write_text(json.dumps({"scene_count": 1, "scenes": [{"revision_calls": revisions, "critic": {"total": critic}}]}), encoding="utf-8")
                runs.append(run)

            report = compare_runs(runs)

            self.assertEqual(report["best"]["highest_critic_average"], "b")
            self.assertEqual(report["best"]["lowest_revision_rate"], "b")
            self.assertEqual(report["best"]["lowest_estimated_cost"], "a")


if __name__ == "__main__":
    unittest.main()
