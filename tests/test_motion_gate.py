import unittest

from legal_auto_motion.motion_gate import analyze_jitter_scores, analyze_motion_scores, parse_freeze_segments


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

    def test_parses_short_freeze_segments_from_ffmpeg_output(self):
        output = "freeze_start: 1.200\nfreeze_end: 2.150 | freeze_duration: 0.950\n"
        self.assertEqual(parse_freeze_segments(output)[0]["duration_seconds"], 0.95)

    def test_rejects_periodic_low_motion_raster_jitter(self):
        scores = [0.004, 0.018, 0.028, 0.006] * 8
        report = analyze_jitter_scores(scores)
        self.assertEqual(report["status"], "rejected")
        self.assertGreaterEqual(report["oscillating_frames"], 6)

    def test_skips_jitter_judgement_during_fast_motion(self):
        report = analyze_jitter_scores([0.12, 0.2, 0.15] * 8)
        self.assertEqual(report["status"], "not_applicable")


if __name__ == "__main__":
    unittest.main()
