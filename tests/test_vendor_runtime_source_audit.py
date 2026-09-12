import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VENDOR = REPO_ROOT / "vendor" / "auto-vibe"


class VendorRuntimeSourceAuditTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (VENDOR / relative).read_text(encoding="utf-8")

    def test_scene_and_parallax_share_cover_geometry(self):
        scene_root = self.read("sceneFolder/remotion/Root.tsx")
        parallax = self.read("transitionFolder/scenes/ParallaxTransition.tsx")
        helper = self.read("sceneFolder/remotion/background-geometry.ts")
        self.assertIn("coverBackgroundGeometry", scene_root)
        self.assertIn("coverBackgroundGeometry", parallax)
        self.assertIn("Math.max(\n    1,", helper)

    def test_transition_handle_renderer_has_no_fixed_canvas_contract(self):
        source = self.read("sceneFolder/scripts/render-transition-handles.mjs")
        self.assertNotIn("const WIDTH = 1080", source)
        self.assertNotIn("const HEIGHT = 1440", source)
        self.assertNotIn("value.fps !== 30", source)
        self.assertIn("metadata.width", source)
        self.assertIn("metadata.height", source)
        self.assertIn("metadata.fps", source)

    def test_render_verifier_has_no_fixed_canvas_contract(self):
        source = self.read("sceneFolder/scripts/verify-rendered-clip.mjs")
        self.assertNotIn("spec.width !== 1080", source)
        self.assertNotIn("spec.height !== 1440", source)
        self.assertNotIn("spec.fps !== 30", source)
        self.assertIn("video.width !== spec.width", source)
        self.assertIn("video.height !== spec.height", source)

    def test_transition_staging_uses_runtime_profile(self):
        source = self.read("stage-transition.py")
        self.assertNotIn('"width": 1080', source)
        self.assertNotIn('"height": 1440', source)
        self.assertIn("read_runtime_profile", source)
        self.assertIn('"width": profile.width', source)
        self.assertIn('"height": profile.height', source)


if __name__ == "__main__":
    unittest.main()
