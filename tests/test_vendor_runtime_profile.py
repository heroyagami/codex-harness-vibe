import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


VENDOR_DIR = Path(__file__).resolve().parents[1] / "vendor" / "auto-vibe"
MODULE_PATH = VENDOR_DIR / "runtime_profile.py"
spec = importlib.util.spec_from_file_location("vendor_runtime_profile", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)


class VendorRuntimeProfileTests(unittest.TestCase):
    def write_plan(self, payload: dict) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        )
        with handle:
            json.dump(payload, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    def test_legacy_plan_defaults_to_current_renderer_profile(self):
        path = self.write_plan({"fps": 30})
        profile = module.read_runtime_profile(path)
        self.assertEqual((profile.width, profile.height, profile.fps), (1080, 1440, 30))

    def test_explicit_runtime_profile_is_transported(self):
        path = self.write_plan(
            {
                "fps": 30,
                "runtime_profile": {"width": 1080, "height": 1920, "fps": 30},
            }
        )
        profile = module.read_runtime_profile(path)
        self.assertEqual((profile.width, profile.height, profile.fps), (1080, 1920, 30))

    def test_top_level_fps_must_match_runtime_profile(self):
        path = self.write_plan(
            {
                "fps": 30,
                "runtime_profile": {"width": 1080, "height": 1440, "fps": 60},
            }
        )
        with self.assertRaises(module.RuntimeProfileError):
            module.read_runtime_profile(path)

    def test_vertical_profile_accepts_small_cover_upscale(self):
        profile = module.RuntimeProfile(width=1080, height=1920, fps=30)
        geometry = module.validate_background_coverage(
            profile, {"width": 1480, "height": 1840}
        )
        self.assertAlmostEqual(geometry.scale, 1920 / 1840, places=6)
        self.assertGreaterEqual(geometry.rendered_height, 1920)
        self.assertGreaterEqual(geometry.rendered_width, 1080)

    def test_excessive_background_upscale_fails_closed(self):
        profile = module.RuntimeProfile(width=1080, height=1920, fps=30)
        with self.assertRaises(module.RuntimeProfileError):
            module.validate_background_coverage(
                profile, {"width": 800, "height": 1000}
            )

    def test_current_profile_accepts_existing_background(self):
        profile = module.RuntimeProfile(width=1080, height=1440, fps=30)
        geometry = module.validate_background_coverage(
            profile, {"width": 1480, "height": 1840}
        )
        self.assertLessEqual(geometry.scale, 1.0)


if __name__ == "__main__":
    unittest.main()
