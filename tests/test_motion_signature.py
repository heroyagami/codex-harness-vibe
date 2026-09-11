import unittest

from legal_auto_motion.motion_signature import motion_signature, repeated_signature_runs


class MotionSignatureTests(unittest.TestCase):
    def test_front_loaded_signature(self):
        report = motion_signature([0.08, 0.07, 0.06, 0.01, 0.005, 0.004])
        self.assertEqual(report["phase_bias"], "front_loaded")
        self.assertIn(report["intensity"], {"medium", "high"})

    def test_back_loaded_signature(self):
        report = motion_signature([0.004, 0.006, 0.01, 0.06, 0.07, 0.08])
        self.assertEqual(report["phase_bias"], "back_loaded")

    def test_repeated_three_scene_signature_is_detected(self):
        items = [
            {"scene_id": "scene-001", "signature": "medium:balanced:low:medium"},
            {"scene_id": "scene-002", "signature": "medium:balanced:low:medium"},
            {"scene_id": "scene-003", "signature": "medium:balanced:low:medium"},
            {"scene_id": "scene-004", "signature": "high:front_loaded:medium:high"},
        ]
        self.assertEqual(repeated_signature_runs(items), [["scene-001", "scene-002", "scene-003"]])

    def test_different_signatures_do_not_form_run(self):
        items = [
            {"scene_id": "scene-001", "signature": "low:balanced:low:low"},
            {"scene_id": "scene-002", "signature": "medium:front_loaded:medium:medium"},
            {"scene_id": "scene-003", "signature": "high:back_loaded:high:high"},
        ]
        self.assertEqual(repeated_signature_runs(items), [])


if __name__ == "__main__":
    unittest.main()
