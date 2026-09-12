import unittest
from pathlib import Path

from legal_auto_motion.runtime_readiness import (
    analyze_runtime_readiness,
    repo_runtime_readiness,
)
from legal_auto_motion.video_profile import CURRENT_RENDERER_PROFILE, VERTICAL_9_16_TARGET


class RuntimeReadinessTests(unittest.TestCase):
    def test_current_profile_can_be_ready_with_dynamic_runtime(self):
        report = analyze_runtime_readiness(
            CURRENT_RENDERER_PROFILE,
            background_dimensions=[("dark", 1480, 1840), ("light", 1480, 1840)],
            scene_runtime_dynamic=True,
            transition_runtime_dynamic=True,
        )
        self.assertEqual(report["status"], "ready")

    def test_vertical_profile_detects_background_and_runtime_blockers(self):
        report = analyze_runtime_readiness(
            VERTICAL_9_16_TARGET,
            background_dimensions=[("dark", 1480, 1840), ("light", 1480, 1840)],
            scene_runtime_dynamic=False,
            transition_runtime_dynamic=False,
        )
        self.assertEqual(report["status"], "blocked")
        text = " ".join(report["blockers"])
        self.assertIn("smaller than canvas", text)
        self.assertIn("scene runtime", text)
        self.assertIn("transition runtime", text)

    def test_repository_has_removed_scene_and_transition_canvas_blockers(self):
        repo_root = Path(__file__).resolve().parents[1]
        report = repo_runtime_readiness(repo_root, VERTICAL_9_16_TARGET)
        self.assertEqual(report["status"], "blocked")
        text = " ".join(report["blockers"])
        self.assertIn("smaller than canvas", text)
        self.assertNotIn("scene runtime", text)
        self.assertNotIn("transition runtime", text)


if __name__ == "__main__":
    unittest.main()
