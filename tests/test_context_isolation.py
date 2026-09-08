import json
import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.agent_adapters import build_invocation
from legal_auto_motion.config import ModelRoute, load_config
from legal_auto_motion.context_policy import CONTEXT_POLICY_VERSION, build_boundary_context
from legal_auto_motion.style_memory import StyleMemory


class ContextIsolationTests(unittest.TestCase):
    def test_boundary_summary_excludes_raw_generation_history(self):
        scenes = [
            {
                "section": "facts",
                "subject": "付款关系",
                "visual_goal": "两方资金流向展开",
                "grammar": "relationship_diagram",
                "energy": 0.7,
                "density": "medium",
                "visual_reset": False,
                "transition_intent": "flow",
                "narration": "THIS MUST NOT LEAK",
                "frame_md": "OTHER SCENE FRAME",
                "source_code": "OTHER SCENE CODE",
            },
            {"section": "rule", "subject": "责任", "visual_goal": "责任边界落位", "grammar": "document_evidence"},
        ]
        context = build_boundary_context(scenes, 1, max_chars=700)
        encoded = json.dumps(context, ensure_ascii=False)
        self.assertIn("付款关系", encoded)
        self.assertNotIn("THIS MUST NOT LEAK", encoded)
        self.assertNotIn("OTHER SCENE FRAME", encoded)
        self.assertNotIn("OTHER SCENE CODE", encoded)

    def test_style_memory_is_bounded_and_does_not_store_source_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = StyleMemory(Path(folder))
            path = memory.record(
                scene_id="scene-001",
                grammar="timeline",
                visual_goal="目标" * 500,
                verdict="pass",
                scores={"composition": 2},
                problems=["问题" * 300],
                revision=["修改" * 300],
                source_run="run-a",
            )
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("source_code", record)
            self.assertLessEqual(len(record["visual_goal"]), 300)
            guidance = memory.guidance("timeline", limit=2, max_chars=600)
            self.assertLessEqual(len(guidance), 601)
            self.assertIn("不包含历史 scene 的完整布局", guidance)

    def test_scene_generic_cli_uses_fresh_prompt_file_and_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder) / "scenes" / "scene-001"
            scene.mkdir(parents=True)
            route = ModelRoute(
                provider="generic_cli",
                model="test",
                command=("runner", "--prompt", "{prompt_file}"),
            )
            invocation = build_invocation(scene, "只制作当前镜头", route)
            self.assertIsNone(invocation.stdin)
            self.assertIsNotNone(invocation.prompt_path)
            prompt_text = invocation.prompt_path.read_text(encoding="utf-8")
            self.assertIn(CONTEXT_POLICY_VERSION, prompt_text)
            self.assertIn("只制作当前镜头", prompt_text)
            manifest = json.loads((scene / ".harness" / "invocation-context.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["fresh_context"])
            self.assertFalse(manifest["session_history_inherited"])
            self.assertFalse(manifest["sibling_scene_history_allowed"])
            self.assertEqual(manifest["scene_id"], "scene-001")

    def test_scene_prompt_over_budget_fails_before_invocation(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder) / "scenes" / "scene-001"
            scene.mkdir(parents=True)
            route = ModelRoute(provider="generic_cli", command=("runner", "{prompt_file}"))
            with self.assertRaisesRegex(ValueError, "context budget"):
                build_invocation(scene, "x" * 2000, route, max_prompt_chars=500)

    def test_style_memory_over_configured_budget_fails_before_invocation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "harness.toml").write_text(
                "[context]\nmax_style_memory_chars=200\nmax_prompt_chars=18000\nmax_neighbor_summary_chars=700\n",
                encoding="utf-8",
            )
            scene = root / "scenes" / "scene-001"
            (scene / "artifacts").mkdir(parents=True)
            (scene / "artifacts" / "style-memory-guidance.md").write_text("x" * 300, encoding="utf-8")
            route = ModelRoute(provider="generic_cli", command=("runner", "{prompt_file}"))
            with self.assertRaisesRegex(ValueError, "Style Memory exceeds"):
                build_invocation(scene, "current scene", route)

    def test_generic_scene_worker_config_requires_prompt_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "harness.toml"
            path.write_text(
                '[models.scene_worker]\nprovider="generic_cli"\ncommand=["runner", "--session", "shared"]\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "prompt_file"):
                load_config(path)

    def test_context_isolation_cannot_be_disabled(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "harness.toml"
            path.write_text("[context]\nrequire_scene_isolation=false\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mandatory production invariant"):
                load_config(path)

    def test_context_defaults_are_fail_closed(self):
        config = load_config()
        self.assertTrue(config.context["require_scene_isolation"])
        self.assertTrue(config.context["forbid_sibling_scene_reads"])
        self.assertLess(config.context["max_style_memory_chars"], config.context["max_prompt_chars"])


if __name__ == "__main__":
    unittest.main()
