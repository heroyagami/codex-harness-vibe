import json
import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.revision_router import choose_revision_route, discover_revision_route, revision_prompt


class RevisionRouterTests(unittest.TestCase):
    def test_fact_violation_routes_to_fact_only(self):
        route = choose_revision_route(stage="fact", report={"problems": ["金额与事实源不一致"]})
        self.assertEqual(route.kind, "fact")
        self.assertIn("不得改镜头结构", route.instruction)

    def test_timing_violation_routes_to_timing(self):
        route = choose_revision_route(stage="beat", report={"problems": ["anchor too late"]})
        self.assertEqual(route.kind, "timing")

    def test_motion_violation_routes_to_motion(self):
        route = choose_revision_route(stage="motion", report={"problems": ["freeze lasts 1.2 seconds"]})
        self.assertEqual(route.kind, "motion")

    def test_low_composition_score_routes_to_composition(self):
        route = choose_revision_route(report={"scores": {"composition": 1, "information_density": 2}})
        self.assertEqual(route.kind, "composition")

    def test_semantic_failure_falls_back_to_creative(self):
        route = choose_revision_route(report={"scores": {"composition": 2, "information_density": 2}, "problems": ["visual thesis weak"]})
        self.assertEqual(route.kind, "creative")

    def test_prompt_is_narrow_and_references_report(self):
        route = choose_revision_route(stage="visual", report={"problems": ["clipped"]})
        prompt = revision_prompt(route, "artifacts/visual-gate/visual-gate.json")
        self.assertIn("artifacts/visual-gate/visual-gate.json", prompt)
        self.assertIn("只处理报告中列出的失败项", prompt)

    def test_discovers_motion_revision_from_pipeline_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder) / "scene-001"
            report = scene / "artifacts" / "visual-revision-request.json"
            report.parent.mkdir(parents=True)
            report.write_text(json.dumps({"problems": ["freeze lasts 1.2 seconds"]}), encoding="utf-8")
            discovered = discover_revision_route(scene, "修复全部可见性或动画节奏问题")
            self.assertIsNotNone(discovered)
            route, report_path, _ = discovered
            self.assertEqual(route.kind, "motion")
            self.assertEqual(report_path, "artifacts/visual-revision-request.json")

    def test_discovers_creative_composition_route_from_critic(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder) / "scene-001"
            report = scene / "artifacts" / "creative-critique.json"
            report.parent.mkdir(parents=True)
            report.write_text(json.dumps({"scores": {"composition": 1, "information_density": 2}}), encoding="utf-8")
            discovered = discover_revision_route(scene, "读取 artifacts/creative-critique.json 并返工")
            self.assertIsNotNone(discovered)
            route, _, _ = discovered
            self.assertEqual(route.kind, "composition")


if __name__ == "__main__":
    unittest.main()
