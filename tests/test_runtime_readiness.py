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

    def test_vertical_profile_accepts_bounded_cover_upscale(self):
        report = analyze_runtime_readiness(
            VERTICAL_9_16_TARGET,
            background_dimensions=[("dark", 1480, 1840), ("light", 1480, 1840)],
            scene_runtime_dynamic=True,
            transition_runtime_dynamic=True,
            scene_background_cover=True,
            transition_background_cover=True,
        )
        self.assertEqual(report["status"], "ready")
        self.assertAlmostEqual(
            report["backgrounds"][0]["cover_scale"], 1920 / 1840, places=6
        )
        self.assertTrue(report["backgrounds"][0]["upscale_required"])

    def test_vertical_profile_still_blocks_excessive_upscale(self):
        report = analyze_runtime_readiness(
            VERTICAL_9_16_TARGET,
            background_dimensions=[("tiny", 800, 1000)],
            scene_runtime_dynamic=True,
            transition_runtime_dynamic=True,
        )
        self.assertEqual(report["status"], "blocked")
        self.assertIn("maximum allowed", " ".join(report["blockers"]))

    def test_cover_geometry_is_required_in_both_runtimes(self):
        report = analyze_runtime_readiness(
            VERTICAL_9_16_TARGET,
            background_dimensions=[("dark", 1480, 1840)],
            scene_runtime_dynamic=True,
            transition_runtime_dynamic=True,
            scene_background_cover=False,
            transition_background_cover=False,
        )
        text = " ".join(report["blockers"])
        self.assertIn("scene runtime does not use cover-scale", text)
        self.assertIn("transition runtime does not use cover-scale", text)

    def test_repository_runtime_layer_is_9x16_ready(self):
        repo_root = Path(__file__).resolve().parents[1]
        report = repo_runtime_readiness(repo_root, VERTICAL_9_16_TARGET)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["blockers"], [])


if __name__ == "__main__":
    unittest.main()
