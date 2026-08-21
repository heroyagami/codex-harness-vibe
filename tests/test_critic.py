import unittest

from legal_auto_motion.pipeline import _validate_creative_critique


class CreativeCriticTests(unittest.TestCase):
    evidence = [
        {"frame": "early", "observation": "主体进入"},
        {"frame": "mid", "observation": "关系展开"},
        {"frame": "late", "observation": "结论定格"},
    ]

    def test_pass_requires_fourteen_and_no_zero(self):
        report = {"scores": {
            "semantic_clarity": 2, "visual_thesis": 2, "information_density": 2,
            "composition": 2, "motion_purpose": 2, "rhythm": 1,
            "continuity": 1, "caption_safety": 2,
        }, "visual_evidence": self.evidence}
        self.assertEqual(_validate_creative_critique(report)["verdict"], "pass")

    def test_zero_forces_revision_even_when_other_scores_are_high(self):
        report = {"scores": {
            "semantic_clarity": 0, "visual_thesis": 2, "information_density": 2,
            "composition": 2, "motion_purpose": 2, "rhythm": 2,
            "continuity": 2, "caption_safety": 2,
        }, "visual_evidence": self.evidence}
        self.assertEqual(_validate_creative_critique(report)["verdict"], "revise")

    def test_rejects_scores_without_direct_frame_evidence(self):
        report = {"scores": {
            "semantic_clarity": 2, "visual_thesis": 2, "information_density": 2,
            "composition": 2, "motion_purpose": 2, "rhythm": 2,
            "continuity": 2, "caption_safety": 2,
        }, "problems": ["无法直接读取图片"]}
        self.assertEqual(_validate_creative_critique(report)["verdict"], "revise")


if __name__ == "__main__":
    unittest.main()
