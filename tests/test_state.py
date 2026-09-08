import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.state import StateGraph, input_hash


class StateGraphTests(unittest.TestCase):
    def test_stale_running_calls_are_closed_on_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            graph = StateGraph(Path(folder) / "state.json")
            call_id = graph.begin_call(role="scene_worker", provider="claude", scope="scene-001")
            self.assertEqual(graph.close_interrupted_calls(), 1)
            event = next(item for item in graph.load()["usage"]["events"] if item["call_id"] == call_id)
            self.assertEqual(event["status"], "interrupted")
            self.assertEqual(event["error_category"], "interrupted")

    def test_hash_change_invalidates_only_requested_downstream(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "input.txt"
            output = root / "plan.json"
            source.write_text("one", encoding="utf-8")
            output.write_text("{}", encoding="utf-8")
            graph = StateGraph(root / "state.json")
            old = input_hash([source])
            graph.complete("directed", old, outputs=[output])
            graph.complete("prepared", "prepared")
            source.write_text("two", encoding="utf-8")
            self.assertFalse(graph.is_current("directed", input_hash([source])))
            removed = graph.invalidate_from("directed")
            self.assertEqual(removed, ["directed", "prepared"])

    def test_output_tampering_makes_node_stale(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "result.json"
            output.write_text("one", encoding="utf-8")
            graph = StateGraph(root / "state.json")
            graph.complete("rendered", "fingerprint", outputs=[output])
            output.write_text("two", encoding="utf-8")
            self.assertFalse(graph.is_current("rendered", "fingerprint"))

    def test_budget_blocks_call_before_it_starts(self):
        with tempfile.TemporaryDirectory() as folder:
            graph = StateGraph(Path(folder) / "state.json")
            graph.reserve_call(max_calls=1)
            with self.assertRaisesRegex(RuntimeError, "budget exhausted"):
                graph.reserve_call(max_calls=1)

    def test_call_lifecycle_records_role_duration_and_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            graph = StateGraph(Path(folder) / "state.json")
            call_id = graph.begin_call(role="scene_worker", provider="codex_worker", model="gpt")
            graph.finish_call(call_id, status="failed", error="quota exceeded")
            event = graph.load()["usage"]["events"][0]
            self.assertEqual(event["role"], "scene_worker")
            self.assertEqual(event["status"], "failed")
            self.assertEqual(event["error_category"], "quota")
            self.assertGreaterEqual(event["duration_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
