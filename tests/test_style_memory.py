import json
import tempfile
import time
import unittest
from pathlib import Path

from legal_auto_motion.style_memory import StyleMemory, memory_quality


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

    def test_higher_quality_lesson_ranks_first(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = StyleMemory(Path(folder))
            memory.record(
                scene_id="scene-low", grammar="timeline", visual_goal="低质量经验",
                verdict="pass", scores={"semantic_clarity": 1, "composition": 1}, problems=[], revision=[],
            )
            memory.record(
                scene_id="scene-high", grammar="timeline", visual_goal="高质量经验",
                verdict="pass", scores={"semantic_clarity": 2, "composition": 2}, problems=[], revision=[],
            )
            guidance = memory.guidance("timeline", limit=2)
            self.assertLess(guidance.index("高质量经验"), guidance.index("低质量经验"))

    def test_duplicate_lessons_keep_one_canonical_record(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = StyleMemory(Path(folder))
            kwargs = dict(
                grammar="timeline", visual_goal="同一经验", verdict="pass",
                scores={"semantic_clarity": 2}, problems=[], revision=[],
            )
            memory.record(scene_id="scene-001", **kwargs)
            memory.record(scene_id="scene-002", **kwargs)
            records = list((Path(folder) / "good-scenes").glob("*.json"))
            self.assertEqual(len(records), 1)

    def test_stale_weak_lessons_are_pruned(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = StyleMemory(Path(folder))
            path = memory.record(
                scene_id="scene-old", grammar="timeline", visual_goal="旧经验",
                verdict="pass", scores={"semantic_clarity": 0}, problems=[], revision=[],
            )
            record = json.loads(path.read_text(encoding="utf-8"))
            record["recorded_at"] = time.time() - 500 * 86400
            record["quality_score"] = memory_quality(record)
            path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            result = memory.prune(grammar="timeline", stale_days=365)
            self.assertEqual(result["removed"], 1)
            self.assertFalse(path.exists())

    def test_stats_exposes_memory_quality(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = StyleMemory(Path(folder))
            memory.record(
                scene_id="scene-001", grammar="timeline", visual_goal="经验",
                verdict="pass", scores={"semantic_clarity": 2}, problems=[], revision=[],
            )
            stats = memory.stats()
            self.assertEqual(stats["good_scenes"], 1)
            self.assertGreater(stats["average_quality"], 0)


if __name__ == "__main__":
    unittest.main()
