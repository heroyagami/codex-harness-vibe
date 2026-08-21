import unittest

from legal_auto_motion.director import extract_json_object, validate_and_normalize_director
from legal_auto_motion.srt import Cue


class DirectorValidationTests(unittest.TestCase):
    def setUp(self):
        self.cues = [
            Cue(1, 0.0, 1.0, "甲", "00:00:00,000 --> 00:00:01,000"),
            Cue(2, 1.0, 2.0, "乙", "00:00:01,000 --> 00:00:02,000"),
            Cue(3, 2.0, 3.0, "丙", "00:00:02,000 --> 00:00:03,000"),
        ]

    def test_normalizes_contiguous_cue_ranges(self):
        plan = {"scenes": [
            {"cue_start": 1, "cue_end": 2, "meaning": "事实", "visual_goal": "人物走到责任节点", "grammar": "relationship_diagram"},
            {"cue_start": 3, "cue_end": 3, "meaning": "结论", "visual_goal": "结论落入裁判框", "grammar": "document_evidence"},
        ]}
        result = validate_and_normalize_director(plan, self.cues)
        self.assertEqual(result["scenes"][0]["start"], 0.0)
        self.assertEqual(result["scenes"][-1]["end"], 3.0)

    def test_rejects_missing_cue(self):
        plan = {"scenes": [
            {"cue_start": 2, "cue_end": 3, "meaning": "跳过", "visual_goal": "错误", "grammar": "timeline"}
        ]}
        with self.assertRaisesRegex(ValueError, "non-contiguous"):
            validate_and_normalize_director(plan, self.cues)

    def test_rejects_invented_on_screen_copy(self):
        plan = {"scenes": [
            {"cue_start": 1, "cue_end": 3, "meaning": "事实", "visual_goal": "人物关系展开", "grammar": "relationship_diagram", "on_screen_copy": ["不存在"]}
        ]}
        with self.assertRaisesRegex(ValueError, "not found"):
            validate_and_normalize_director(plan, self.cues)

    def test_extracts_plain_json(self):
        self.assertEqual(extract_json_object('{"scenes": []}'), {"scenes": []})

    def test_extracts_json_from_markdown_fence(self):
        output = '说明如下：\n```json\n{"scenes": [{"cue_start": 1}]}\n```\n完成。'
        self.assertEqual(extract_json_object(output)["scenes"][0]["cue_start"], 1)

    def test_extracts_json_surrounded_by_text(self):
        output = '分析文字 {"scenes": [{"cue_start": 1, "meaning": "事实"}]} 后续文字'
        self.assertEqual(extract_json_object(output)["scenes"][0]["meaning"], "事实")

    def test_extracts_structured_output_envelope(self):
        output = '{"type":"result","structured_output":{"scenes":[{"cue_start":1}]}}'
        self.assertEqual(extract_json_object(output)["scenes"][0]["cue_start"], 1)

    def test_rejects_output_without_json(self):
        with self.assertRaisesRegex(ValueError, "no valid JSON"):
            extract_json_object("请问是否需要拆成两个镜头？")


if __name__ == "__main__":
    unittest.main()
