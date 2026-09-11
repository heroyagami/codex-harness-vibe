import unittest

from PIL import Image, ImageDraw

from legal_auto_motion.visual_attention import analyze_attention_frame, summarize_attention


class VisualAttentionTests(unittest.TestCase):
    def test_centered_subject_is_accepted(self):
        background = Image.new("RGB", (200, 200), "black")
        frame = background.copy()
        draw = ImageDraw.Draw(frame)
        draw.rectangle((70, 55, 130, 145), fill="white")
        report = analyze_attention_frame(frame, background)
        self.assertEqual(report["status"], "accepted")
        self.assertGreater(report["foreground_ratio"], 0.05)
        self.assertAlmostEqual(report["centroid"]["x"], 0.5, delta=0.08)

    def test_tiny_subject_is_rejected(self):
        background = Image.new("RGB", (200, 200), "black")
        frame = background.copy()
        draw = ImageDraw.Draw(frame)
        draw.rectangle((99, 99, 101, 101), fill="white")
        report = analyze_attention_frame(frame, background)
        self.assertEqual(report["status"], "rejected")

    def test_two_bad_frames_reject_summary(self):
        bad = {"status": "rejected", "centroid": {"x": 0.05, "y": 0.5}}
        good = {"status": "accepted", "centroid": {"x": 0.5, "y": 0.5}}
        summary = summarize_attention([bad, bad, good])
        self.assertEqual(summary["status"], "rejected")
        self.assertEqual(summary["representative_failures"], 2)


if __name__ == "__main__":
    unittest.main()
