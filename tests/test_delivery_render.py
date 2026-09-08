import unittest
from pathlib import Path


class DeliveryRenderTests(unittest.TestCase):
    def test_remotion_delivery_accepts_explicit_single_concurrency(self):
        script = Path(__file__).parents[1] / "vendor" / "auto-vibe" / "sceneFolder" / "scripts" / "remotion-render.mjs"
        text = script.read_text(encoding="utf-8")
        self.assertIn('process.env.REMOTION_CONCURRENCY || "1"', text)
        self.assertIn('"--concurrency"', text)


if __name__ == "__main__":
    unittest.main()
