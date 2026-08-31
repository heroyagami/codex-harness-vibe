import unittest

from legal_auto_motion.motion_gate import analyze_motion_scores


class MotionGateTests(unittest.TestCase):
    def test_rejects_more_than_five_seconds_without_meaningful_change(self):
        report = analyze_motion_scores([0.001] * 12, sample_interval=0.5)
        self.assertEqual(report["status"], "rejected")
        self.assertGreaterEqual(report["max_idle_seconds"], 5.0)

    def test_accepts_staged_visual_changes(self):
        report = analyze_motion_scores(
            [0.002, 0.025, 0.018, 0.003, 0.022, 0.019, 0.002, 0.03],
            sample_interval=0.5,
        )
        self.assertEqual(report["status"], "accepted")
        self.assertGreaterEqual(report["meaningful_changes"], 4)


if __name__ == "__main__":
    unittest.main()
