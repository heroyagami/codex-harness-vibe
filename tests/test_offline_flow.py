import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from legal_auto_motion.pipeline import build_from_director, init_run, sync_run_inputs


SRT = """1
00:00:00,000 --> 00:00:01,000
先说事实

2
00:00:01,000 --> 00:00:02,000
再说结论
"""


class OfflineFlowTests(unittest.TestCase):
    def test_init_plan_and_changed_input_resume_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            vendor = root / "vendor"
            vendor.mkdir()
            (vendor / "marker.txt").write_text("template", encoding="utf-8")
            srt = root / "input.srt"
            audio = root / "audio.wav"
            config = root / "config.toml"
            run = root / "run"
            srt.write_text(SRT, encoding="utf-8")
            audio.write_bytes(b"RIFF-offline-fixture")
            config.write_text("[models.director]\nprovider='codex_text'\n", encoding="utf-8")
            with patch("legal_auto_motion.pipeline.VENDOR", vendor):
                init_run(run, srt, audio, config)
            director = run / "director-plan.json"
            director.write_text(json.dumps({"scenes": [
                {"start": 0.0, "end": 1.0, "meaning": "事实", "visual_goal": "事实进入", "grammar": "object_demo", "section": "facts", "on_screen_copy": ["事实"]},
                {"start": 1.0, "end": 2.0, "meaning": "结论", "visual_goal": "结论落定", "grammar": "document_evidence", "section": "conclusion", "on_screen_copy": ["结论"]},
            ]}, ensure_ascii=False), encoding="utf-8")
            plan, contracts = build_from_director(run, director)
            self.assertEqual(len(plan["scenes"]), 2)
            self.assertEqual(len(contracts), 2)
            self.assertFalse(sync_run_inputs(run, srt, audio))
            srt.write_text(SRT.replace("再说结论", "最后结论"), encoding="utf-8")
            self.assertTrue(sync_run_inputs(run, srt, audio))
            self.assertFalse((run / "scene-plan.json").exists())

    def test_scene_plan_bridges_natural_subtitle_gaps(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            (run / "transcription.srt").write_text(
                "1\n00:00:00,000 --> 00:00:01,000\n甲\n\n"
                "2\n00:00:02,000 --> 00:00:03,000\n乙\n",
                encoding="utf-8",
            )
            director = run / "director.json"
            director.write_text(json.dumps({"scenes": [
                {"start": 0.0, "end": 1.0, "meaning": "甲"},
                {"start": 2.0, "end": 3.0, "meaning": "乙"},
            ]}, ensure_ascii=False), encoding="utf-8")
            plan, _ = build_from_director(run, director)
            self.assertEqual(plan["scenes"][0]["time_range_seconds"], ["0.000", "2.000"])
            self.assertEqual(plan["scenes"][1]["time_range_seconds"], ["2.000", "3.000"])


if __name__ == "__main__":
    unittest.main()
