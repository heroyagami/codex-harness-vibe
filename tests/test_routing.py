import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from legal_auto_motion.config import HarnessConfig, ModelRoute
from legal_auto_motion.pipeline import WorkerQuotaExceeded, _run_role, scene_fingerprints
from legal_auto_motion.state import StateGraph


class RoutingTests(unittest.TestCase):
    def test_cheap_model_failure_escalates_to_fallback(self):
        config = HarnessConfig(
            models={"scene_worker": ModelRoute("claude", "cheap", "strong")},
            budget={"max_model_calls": 0, "max_total_cost_usd": 0.0},
            production={},
        )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            graph = StateGraph(root / "state.json")
            with patch(
                "legal_auto_motion.pipeline._run_claude",
                side_effect=[WorkerQuotaExceeded("429"), "done"],
            ) as mocked:
                result = _run_role(root, "work", 10, config=config, role="scene_worker", state_graph=graph)
            self.assertEqual(result, "done")
            self.assertEqual(mocked.call_args_list[1].kwargs["route"].model, "strong")

    def test_worker_and_critic_model_changes_have_separate_fingerprints(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder)
            (scene / "artifacts" / "visual-gate").mkdir(parents=True)
            for path in (scene / "fact-contract.json", scene / "scene-metadata.json", scene / "claude-scene-prompt.md"):
                path.write_text("{}", encoding="utf-8")
            for label in ("early", "mid", "late"):
                (scene / "artifacts" / "visual-gate" / f"{label}-review.jpg").write_bytes(b"image")
            base = HarnessConfig(
                models={
                    "scene_worker": ModelRoute("claude", "cheap"),
                    "critic": ModelRoute("codex_images", "vision-a"),
                }, budget={}, production={},
            )
            critic_changed = HarnessConfig(
                models={
                    "scene_worker": ModelRoute("claude", "cheap"),
                    "critic": ModelRoute("codex_images", "vision-b"),
                }, budget={}, production={},
            )
            authored_a, critic_a = scene_fingerprints(scene, base)
            authored_b, critic_b = scene_fingerprints(scene, critic_changed)
            self.assertEqual(authored_a, authored_b)
            self.assertNotEqual(critic_a, critic_b)


if __name__ == "__main__":
    unittest.main()
