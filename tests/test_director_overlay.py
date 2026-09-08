import json
import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.director_overlay import apply_director_overlays


class DirectorOverlayTests(unittest.TestCase):
    def _write_fixture(self, root: Path, scenes: list[dict]) -> None:
        (root / "director-plan.json").write_text(
            json.dumps({"scenes": scenes}, ensure_ascii=False), encoding="utf-8"
        )
        plan_scenes = []
        for index in range(len(scenes)):
            start = index * 3.0
            plan_scenes.append(
                {
                    "time_range_seconds": [f"{start:.3f}", f"{start + 3.0:.3f}"],
                    "subtitle_text": "x",
                    "research_brief": "x",
                    "image_resources": [],
                }
            )
        (root / "scene-plan.json").write_text(
            json.dumps(
                {
                    "fps": 30,
                    "total_duration_seconds": f"{len(scenes) * 3.0:.3f}",
                    "scenes": plan_scenes,
                    "transitions": [{"type": "hard_cut", "reason": "old"} for _ in range(len(scenes) - 1)],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        contracts = {
            f"scene-{index:03d}": {
                "scene_id": f"scene-{index:03d}",
                "narration": "x",
                "approved_copy": [],
                "meaning": "x",
                "visual_goal": "x",
            }
            for index in range(1, len(scenes) + 1)
        }
        (root / "fact-contracts.json").write_text(
            json.dumps(contracts, ensure_ascii=False), encoding="utf-8"
        )

    def test_semantic_intent_replaces_modulo_transition_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scenes = [
                {"section": "facts", "transition_intent": "hard_cut", "subject": "A", "energy": 0.8},
                {"section": "facts", "transition_intent": "flow", "subject": "B", "energy": 0.6},
                {"section": "rule", "transition_intent": "carry", "subject": "C", "energy": 0.7},
            ]
            self._write_fixture(root, scenes)
            result = apply_director_overlays(root)
            plan = json.loads((root / "scene-plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["transitions"][0]["type"], "parallax")
            self.assertEqual(plan["transitions"][0]["director_intent"], "flow")
            self.assertEqual(plan["transitions"][1]["type"], "hard_cut")
            self.assertEqual(result["rendered_transition_count"], 1)

    def test_contract_receives_rhythm_and_safe_zone(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scenes = [
                {
                    "section": "hook",
                    "transition_intent": "hard_cut",
                    "subject": "付款关系",
                    "grammar": "relationship_diagram",
                    "energy": 0.9,
                    "density": "medium",
                    "visual_reset": True,
                    "contrast_with_previous": "strong",
                }
            ]
            self._write_fixture(root, scenes)
            apply_director_overlays(root)
            contracts = json.loads((root / "fact-contracts.json").read_text(encoding="utf-8"))
            contract = contracts["scene-001"]
            self.assertEqual(contract["subject"], "付款关系")
            self.assertEqual(contract["energy"], 0.9)
            self.assertTrue(contract["visual_reset"])
            self.assertEqual(contract["safe_zone"]["left"], 110)


if __name__ == "__main__":
    unittest.main()
