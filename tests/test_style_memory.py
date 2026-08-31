import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.style_memory import StyleMemory


class StyleMemoryTests(unittest.TestCase):
    def test_passed_and_failed_scenes_become_reusable_guidance(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = StyleMemory(Path(folder))
            memory.record(
                scene_id="scene-001", grammar="timeline", visual_goal="看懂事件先后",
                verdict="pass", scores={"semantic_clarity": 2}, problems=[], revision=[],
            )
            memory.record(
                scene_id="scene-002", grammar="timeline", visual_goal="看懂责任变化",
                verdict="revise", scores={"semantic_clarity": 1},
                problems=["节点太密"], revision=["减少节点"],
            )

            guidance = memory.guidance("timeline")

            self.assertIn("看懂事件先后", guidance)
            self.assertIn("节点太密", guidance)
            self.assertTrue(any((Path(folder) / "good-scenes").glob("*.json")))
            self.assertTrue(any((Path(folder) / "bad-scenes").glob("*.json")))


if __name__ == "__main__":
    unittest.main()
