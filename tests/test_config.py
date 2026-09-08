import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.config import ModelRoute, load_config
from legal_auto_motion.providers import claude_command


class ConfigTests(unittest.TestCase):
    def test_empty_model_inherits_claude_default(self):
        config = load_config()
        self.assertEqual(config.route("director").provider, "codex_text")
        command = claude_command("claude", config.route("scene_worker"))
        self.assertNotIn("--model", command)
        self.assertEqual(config.video["width"], 1080)
        self.assertEqual(config.video["height"], 1440)
        self.assertEqual(config.safe_zone["left"], 110)

    def test_explicit_model_and_fallback_are_loaded(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "harness.toml"
            path.write_text(
                '[models.scene_worker]\nprovider="claude"\nmodel="cheap"\nfallback_model="strong"\n',
                encoding="utf-8",
            )
            route = load_config(path).route("scene_worker")
            self.assertEqual(route, ModelRoute("claude", "cheap", "strong", 0.0))
            self.assertEqual(claude_command("claude", route)[-2:], ["--model", "cheap"])

    def test_cost_cap_requires_per_call_estimates(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "harness.toml"
            path.write_text("[budget]\nmax_total_cost_usd=1.0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "estimated_cost_usd"):
                load_config(path)

    def test_safe_zone_must_fit_canvas(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "harness.toml"
            path.write_text(
                "[video]\nwidth=1080\nheight=1440\nfps=30\n"
                "[safe_zone]\nleft=100\nright=1200\ntop=100\ncontent_bottom=1000\nsubtitle_bottom=1300\nedge_guard=60\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "left/right"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
