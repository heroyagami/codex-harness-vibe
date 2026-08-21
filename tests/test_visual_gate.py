import unittest

from PIL import Image


class VisualGateEdgeMathTests(unittest.TestCase):
    def test_outer_edge_strip_detects_clipped_foreground(self):
        background = Image.new("RGB", (1080, 1440), "black")
        frame = background.copy()
        for x in range(0, 80):
            for y in range(200, 700):
                frame.putpixel((x, y), (255, 255, 255))
        difference = __import__("PIL.ImageChops", fromlist=["difference"]).difference(frame, background).convert("L")
        strip = difference.crop((0, 100, 60, 1000))
        ratio = sum(1 for value in strip.get_flattened_data() if value > 20) / (60 * 900)
        self.assertGreaterEqual(ratio, 0.025)


if __name__ == "__main__":
    unittest.main()
