import unittest

from legal_auto_motion.beat_gate import validate_beats


class BeatGateTests(unittest.TestCase):
    words = [
        {"text": "法院", "start": 1.0},
        {"text": "认为", "start": 1.3},
        {"text": "医院", "start": 1.8},
        {"text": "担责", "start": 2.2},
    ]

    def test_accepts_beat_near_spoken_anchor_with_tail_room(self):
        report = validate_beats(
            [{"time_seconds": 1.82, "anchor": "医院", "what": "医院节点出现"}],
            self.words, scene_start=1.0, scene_end=3.0, tolerance=0.1, tail_seconds=0.5,
        )
        self.assertEqual(report["status"], "accepted")

    def test_rejects_hand_timed_or_too_late_beat(self):
        report = validate_beats(
            [{"time_seconds": 2.7, "anchor": "医院", "what": "医院节点出现"}],
            self.words, scene_start=1.0, scene_end=3.0, tolerance=0.1, tail_seconds=0.5,
        )
        self.assertEqual(report["status"], "rejected")
        self.assertTrue(report["problems"])


if __name__ == "__main__":
    unittest.main()
