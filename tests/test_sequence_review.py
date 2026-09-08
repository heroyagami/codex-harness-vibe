import unittest

from PIL import Image

from legal_auto_motion.sequence_review import _silhouette_similarity, _similarity, analyze_director_rhythm


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

    def test_flat_energy_curve_is_rejected(self):
        scenes = [
            {"energy": 0.5, "density": "medium", "visual_reset": index == 0, "grammar": "timeline"}
            for index in range(5)
        ]
        report = analyze_director_rhythm(scenes)
        self.assertTrue(any("energy curve" in problem for problem in report["problems"]))

    def test_varied_rhythm_passes_without_problems(self):
        scenes = [
            {"energy": 0.9, "density": "medium", "visual_reset": True, "grammar": "object_demo"},
            {"energy": 0.4, "density": "low", "visual_reset": False, "grammar": "timeline"},
            {"energy": 0.8, "density": "high", "visual_reset": False, "grammar": "comparison"},
            {"energy": 0.3, "density": "low", "visual_reset": True, "grammar": "visual_rest"},
            {"energy": 0.7, "density": "medium", "visual_reset": False, "grammar": "document_evidence"},
        ]
        self.assertEqual(analyze_director_rhythm(scenes)["problems"], [])


if __name__ == "__main__":
    unittest.main()
