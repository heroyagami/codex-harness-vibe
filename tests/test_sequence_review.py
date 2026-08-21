import tempfile
import unittest
from pathlib import Path

from PIL import Image

from legal_auto_motion.sequence_review import _silhouette_similarity, _similarity


class SequenceReviewTests(unittest.TestCase):
    def test_identical_midpoints_are_detected_as_repeated(self):
        frame = Image.new("RGB", (100, 100), "black")
        self.assertEqual(_similarity(frame, frame), 1.0)

    def test_different_midpoints_are_not_marked_identical(self):
        left = Image.new("RGB", (100, 100), "black")
        right = Image.new("RGB", (100, 100), "white")
        self.assertLess(_similarity(left, right), 0.94)

    def test_shared_background_does_not_hide_different_silhouettes(self):
        background = Image.new("RGB", (100, 100), "black")
        left = background.copy()
        right = background.copy()
        for x in range(10, 40):
            for y in range(10, 90):
                left.putpixel((x, y), (255, 255, 255))
        for x in range(60, 90):
            for y in range(10, 90):
                right.putpixel((x, y), (255, 255, 255))
        self.assertLess(_silhouette_similarity(left, right, background), 0.94)


if __name__ == "__main__":
    unittest.main()
