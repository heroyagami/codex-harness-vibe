import unittest

from legal_auto_motion.video_profile import CURRENT_RENDERER_PROFILE, VERTICAL_9_16_TARGET, renderer_compatible


class VideoProfileTests(unittest.TestCase):
    def test_current_profile_is_renderer_compatible(self):
        self.assertTrue(renderer_compatible(CURRENT_RENDERER_PROFILE))

    def test_vertical_target_is_declared_but_not_yet_renderer_compatible(self):
        self.assertFalse(renderer_compatible(VERTICAL_9_16_TARGET))
        self.assertEqual((VERTICAL_9_16_TARGET.width, VERTICAL_9_16_TARGET.height), (1080, 1920))

    def test_subtitle_style_is_derived_from_profile(self):
        style = CURRENT_RENDERER_PROFILE.subtitle_force_style()
        self.assertIn("MarginL=110", style)
        self.assertIn("MarginR=110", style)
        self.assertIn("MarginV=145", style)

    def test_safe_zone_prompt_is_not_hardcoded_elsewhere(self):
        prompt = VERTICAL_9_16_TARGET.safe_zone_prompt()
        self.assertIn("x=90..990", prompt)
        self.assertIn("y=180..1420", prompt)
        self.assertIn("y=1740", prompt)


if __name__ == "__main__":
    unittest.main()
