import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from scene_plan import ScenePlanError, read_scene_plan_document  # noqa: E402


def background(theme="dark"):
    filename = "lightbg.png" if theme == "light" else "darkbg.png"
    return {
        "source": f"resources/backgrounds/{filename}",
        "target": f"public/img/{filename}",
        "width": 1480,
        "height": 1840,
    }


def two_scene_plan(transition=None):
    return {
        "fps": 30,
        "visual_theme": "dark",
        "total_duration_seconds": "5.500",
        "background": background(),
        "scenes": [
            {
                "time_range_seconds": ["0.000", "2.250"],
                "subtitle_text": "00:00:00,000 --> 00:00:02,000\n第一句",
                "research_brief": "无额外补充",
                "image_resources": [],
            },
            {
                "time_range_seconds": ["2.250", "5.500"],
                "subtitle_text": "00:00:02,500 --> 00:00:05,500\n第二句",
                "research_brief": "无额外补充",
                "image_resources": [],
            },
        ],
        "transitions": [
            transition
            or {
                "type": "parallax",
                "time_range_seconds": ["1.750", "2.750"],
                "reason": "语义连续推进。",
            }
        ],
    }


class ScenePlanTest(unittest.TestCase):
    def read(self, plan, srt=None, prompt_theme=None):
        if srt is None:
            srt = (
                "1\n00:00:00,000 --> 00:00:02,000\n第一句\n\n"
                "2\n00:00:02,500 --> 00:00:05,500\n第二句\n"
            )
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        (root / "transcription.srt").write_text(srt, encoding="utf-8")
        if prompt_theme is not None:
            (root / "codex-prompt.md").write_text(
                f"---\nvisual_theme: {prompt_theme}\n---\n\n读取当前目录。\n",
                encoding="utf-8",
            )
        selected_background = plan.get("background")
        if selected_background is None:
            selected_background = background(
                plan.get("visual_theme", prompt_theme or "dark")
            )
        background_path = root / selected_background["source"]
        background_path.parent.mkdir(parents=True, exist_ok=True)
        background_path.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + (13).to_bytes(4, "big")
            + b"IHDR"
            + selected_background["width"].to_bytes(4, "big")
            + selected_background["height"].to_bytes(4, "big")
        )
        plan_path = root / "scene-plan.json"
        plan_path.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return read_scene_plan_document(plan_path)

    def test_parallax_transition_replaces_timeline_time_without_changing_total(self):
        document = self.read(two_scene_plan())
        self.assertEqual(document["total_duration_frames"], 165)
        self.assertEqual(
            [item["id"] for item in document["timeline_segments"]],
            ["scene-001", "transition-001", "scene-002"],
        )
        self.assertEqual(
            [item["duration_in_frames"] for item in document["timeline_segments"]],
            [53, 30, 82],
        )
        self.assertEqual(
            document["scenes"][0]["render_range_seconds"],
            ["0.000", "1.750"],
        )
        self.assertEqual(
            document["scenes"][1]["render_range_seconds"],
            ["2.750", "5.500"],
        )
        self.assertIn("exit", document["scenes"][0]["boundary_contract"])
        self.assertIn("entry", document["scenes"][1]["boundary_contract"])

    def test_light_theme_uses_lightbg_preset(self):
        plan = two_scene_plan()
        plan["visual_theme"] = "light"
        plan["background"] = background("light")
        document = self.read(plan)
        self.assertEqual(document["visual_theme"], "light")
        self.assertEqual(document["background"]["fallback_color"], "#eadeca")
        self.assertTrue(
            all(scene["visual_theme"] == "light" for scene in document["scenes"])
        )

    def test_background_is_derived_from_visual_theme_when_omitted(self):
        plan = two_scene_plan()
        del plan["background"]
        document = self.read(plan)
        self.assertEqual(document["background"]["source"], "resources/backgrounds/darkbg.png")
        self.assertEqual(document["background"]["target"], "public/img/darkbg.png")
        self.assertEqual(document["background"]["width"], 1480)
        self.assertEqual(document["background"]["height"], 1840)

    def test_visual_theme_is_loaded_from_codex_prompt_front_matter(self):
        plan = two_scene_plan()
        del plan["visual_theme"]
        del plan["background"]
        document = self.read(plan, prompt_theme="light")
        self.assertEqual(document["visual_theme"], "light")
        self.assertEqual(
            document["background"]["source"],
            "resources/backgrounds/lightbg.png",
        )

    def test_plan_theme_must_match_codex_prompt_front_matter(self):
        with self.assertRaisesRegex(ScenePlanError, "does not match"):
            self.read(two_scene_plan(), prompt_theme="light")

    def test_theme_and_background_must_match(self):
        plan = two_scene_plan()
        plan["visual_theme"] = "light"
        with self.assertRaisesRegex(ScenePlanError, "light visual_theme requires"):
            self.read(plan)

    def test_visual_theme_is_required(self):
        plan = two_scene_plan()
        del plan["visual_theme"]
        with self.assertRaisesRegex(ScenePlanError, "visual_theme must be light or dark"):
            self.read(plan)

    def test_hard_cut_keeps_full_scenes_and_adds_no_timeline_clip(self):
        plan = two_scene_plan({"type": "hard_cut", "reason": "语义重击需要明确切点。"})
        document = self.read(plan)
        self.assertEqual(
            [item["id"] for item in document["timeline_segments"]],
            ["scene-001", "scene-002"],
        )
        self.assertEqual(
            [item["duration_in_frames"] for item in document["timeline_segments"]],
            [68, 97],
        )
        self.assertEqual(document["scenes"][0]["render_range_seconds"], ["0.000", "2.250"])
        self.assertEqual(document["scenes"][1]["render_range_seconds"], ["2.250", "5.500"])
        self.assertEqual(document["scenes"][0]["boundary_contract"], {})
        self.assertEqual(document["scenes"][1]["boundary_contract"], {})

    def test_unknown_transition_type_is_rejected(self):
        plan = two_scene_plan({"type": "dissolve", "reason": "语义连续。"})
        with self.assertRaisesRegex(ScenePlanError, "type must be parallax, custom, or hard_cut"):
            self.read(plan)

    def test_background_anchor_follows_four_corner_loop(self):
        plan = two_scene_plan()
        first = plan["scenes"][0]
        plan["total_duration_seconds"] = "5.500"
        plan["scenes"] = [
            {
                **first,
                "time_range_seconds": [f"{index}.000", f"{index + 1}.000"],
                "subtitle_text": (
                    f"00:00:0{index},000 --> 00:00:0{index + 1},000\n{index + 1}"
                ),
            }
            for index in range(5)
        ]
        plan["scenes"][-1]["time_range_seconds"] = ["4.000", "5.500"]
        plan["scenes"][-1]["subtitle_text"] = "00:00:04,000 --> 00:00:05,500\n5"
        plan["transitions"] = [
            {
                "type": "custom",
                "time_range_seconds": [f"{index - 0.2:.3f}", f"{index + 0.2:.3f}"],
                "reason": "连续镜头。",
            }
            for index in range(1, 5)
        ]
        srt = "\n\n".join(
            [
                f"{index + 1}\n00:00:0{index},000 --> 00:00:0{index + 1},000\n{index + 1}"
                for index in range(4)
            ]
            + ["5\n00:00:04,000 --> 00:00:05,500\n5"]
        )
        document = self.read(plan, srt)
        self.assertEqual(
            [scene["background_anchor"]["name"] for scene in document["scenes"]],
            ["top_left", "top_right", "bottom_right", "bottom_left", "top_left"],
        )

    def test_single_scene_requires_empty_transition_list(self):
        plan = two_scene_plan()
        plan["scenes"] = [
            {
                **plan["scenes"][0],
                "time_range_seconds": ["0.000", "5.500"],
                "subtitle_text": (
                    "00:00:00,000 --> 00:00:02,000\n第一句\n"
                    "00:00:02,500 --> 00:00:05,500\n第二句"
                ),
            }
        ]
        plan["transitions"] = []
        document = self.read(plan)
        self.assertEqual(len(document["timeline_segments"]), 1)
        self.assertEqual(document["timeline_segments"][0]["duration_in_frames"], 165)

    def test_missing_boundary_decision_fails(self):
        plan = two_scene_plan()
        plan["transitions"] = []
        with self.assertRaisesRegex(ScenePlanError, "must contain 1 item"):
            self.read(plan)

    def test_custom_transition_must_straddle_boundary(self):
        plan = two_scene_plan()
        plan["transitions"][0]["type"] = "custom"
        plan["transitions"][0]["time_range_seconds"] = ["0.500", "1.500"]
        with self.assertRaisesRegex(ScenePlanError, "must straddle scene boundary"):
            self.read(plan)

    def test_transition_overlap_cannot_consume_middle_scene(self):
        srt = (
            "1\n00:00:00,000 --> 00:00:01,000\nA\n\n"
            "2\n00:00:01,000 --> 00:00:02,000\nB\n\n"
            "3\n00:00:02,000 --> 00:00:03,000\nC\n"
        )
        plan = {
            "fps": 30,
            "visual_theme": "dark",
            "total_duration_seconds": "3.000",
            "background": background(),
            "scenes": [
                {
                    "time_range_seconds": [f"{index - 1}.000", f"{index}.000"],
                    "subtitle_text": f"00:00:0{index - 1},000 --> 00:00:0{index},000\n{chr(64 + index)}",
                    "research_brief": "无额外补充",
                    "image_resources": [],
                }
                for index in range(1, 4)
            ],
            "transitions": [
                {
                    "type": "custom",
                    "time_range_seconds": ["0.400", "1.600"],
                    "reason": "连续。",
                },
                {
                    "type": "custom",
                    "time_range_seconds": ["1.400", "2.600"],
                    "reason": "连续。",
                },
            ],
        }
        with self.assertRaisesRegex(
            ScenePlanError, "without a positive 30fps render range"
        ):
            self.read(plan, srt)

    def test_total_duration_must_match_exactly(self):
        plan = two_scene_plan()
        plan["total_duration_seconds"] = "5.501"
        with self.assertRaisesRegex(ScenePlanError, "does not match"):
            self.read(plan)

    def test_scene_cues_must_reproduce_srt_exactly_once(self):
        plan = two_scene_plan()
        plan["scenes"][1]["subtitle_text"] = (
            "00:00:02,500 --> 00:00:05,500\n改写后的第二句"
        )
        with self.assertRaisesRegex(
            ScenePlanError, "reproduce transcription.srt exactly once"
        ):
            self.read(plan)

    def test_silent_scene_can_have_empty_subtitle_text(self):
        srt = (
            "1\n00:00:00,000 --> 00:00:01,000\nA\n\n"
            "2\n00:00:02,000 --> 00:00:03,000\nB\n"
        )
        plan = {
            "fps": 30,
            "visual_theme": "dark",
            "total_duration_seconds": "3.000",
            "background": background(),
            "scenes": [
                {
                    "time_range_seconds": ["0.000", "1.000"],
                    "subtitle_text": "00:00:00,000 --> 00:00:01,000\nA",
                    "research_brief": "无额外补充",
                    "image_resources": [],
                },
                {
                    "time_range_seconds": ["1.000", "2.000"],
                    "subtitle_text": "",
                    "research_brief": "两条字幕之间的无字幕时段。",
                    "image_resources": [],
                },
                {
                    "time_range_seconds": ["2.000", "3.000"],
                    "subtitle_text": "00:00:02,000 --> 00:00:03,000\nB",
                    "research_brief": "无额外补充",
                    "image_resources": [],
                },
            ],
            "transitions": [
                {
                    "type": "custom",
                    "time_range_seconds": ["0.800", "1.200"],
                    "reason": "停顿开始。",
                },
                {
                    "type": "custom",
                    "time_range_seconds": ["1.800", "2.200"],
                    "reason": "停顿结束。",
                },
            ],
        }
        document = self.read(plan, srt)
        self.assertEqual(len(document["scenes"]), 3)

    def test_non_zero_srt_origin_uses_relative_global_frames(self):
        srt = "1\n00:00:00,100 --> 00:00:01,900\nA\n"
        plan = {
            "fps": 30,
            "visual_theme": "dark",
            "total_duration_seconds": "1.800",
            "background": background(),
            "scenes": [
                {
                    "time_range_seconds": ["0.100", "1.900"],
                    "subtitle_text": "00:00:00,100 --> 00:00:01,900\nA",
                    "research_brief": "无额外补充",
                    "image_resources": [],
                }
            ],
            "transitions": [],
        }
        document = self.read(plan, srt)
        self.assertEqual(document["total_duration_frames"], 54)
        self.assertEqual(document["scenes"][0]["frame_range"], [0, 54])

    def test_numeric_subtitle_text_is_not_mistaken_for_an_srt_index(self):
        srt = "1\n00:00:00,000 --> 00:00:01,000\n2026\n"
        plan = {
            "fps": 30,
            "visual_theme": "dark",
            "total_duration_seconds": "1.000",
            "background": background(),
            "scenes": [
                {
                    "time_range_seconds": ["0.000", "1.000"],
                    "subtitle_text": "00:00:00,000 --> 00:00:01,000\n2026",
                    "research_brief": "无额外补充",
                    "image_resources": [],
                }
            ],
            "transitions": [],
        }
        document = self.read(plan, srt)
        self.assertEqual(document["total_duration_frames"], 30)


if __name__ == "__main__":
    unittest.main()
