import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from legal_auto_motion.providers import ProviderUnavailable, is_retryable_model_failure, read_manual_critique
from legal_auto_motion.pipeline import _run_claude
from legal_auto_motion.config import ModelRoute


class ProviderTests(unittest.TestCase):
    @patch("legal_auto_motion.pipeline.subprocess.run")
    @patch("legal_auto_motion.pipeline._claude_executable", return_value="claude")
    def test_claude_subagents_inherit_explicit_worker_model(self, _executable, run):
        run.return_value.returncode = 0
        run.return_value.stdout = "ok"
        run.return_value.stderr = ""
        with tempfile.TemporaryDirectory() as folder:
            result = _run_claude(
                Path(folder), "prompt", 30,
                route=ModelRoute("claude", "opus", ""),
            )
        self.assertEqual(result, "ok")
        self.assertEqual(run.call_args.kwargs["env"]["CLAUDE_CODE_SUBAGENT_MODEL"], "opus")
    def test_quota_and_rate_limit_are_resumable(self):
        self.assertTrue(is_retryable_model_failure("HTTP 429 usage limit"))
        self.assertTrue(is_retryable_model_failure("service overloaded"))
        self.assertFalse(is_retryable_model_failure("syntax error"))

    def test_manual_critic_fails_closed_without_report(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder)
            (scene / "artifacts").mkdir()
            with self.assertRaises(ProviderUnavailable):
                read_manual_critique(scene)


if __name__ == "__main__":
    unittest.main()
