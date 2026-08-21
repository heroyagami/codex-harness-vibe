import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.state import StateGraph, input_hash


class StateGraphTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
