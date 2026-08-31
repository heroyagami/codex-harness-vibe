import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.agent_adapters import build_invocation
from legal_auto_motion.config import ModelRoute


class AgentAdapterTests(unittest.TestCase):
    def test_codex_worker_is_workspace_writable(self):
        with tempfile.TemporaryDirectory() as folder:
            invocation = build_invocation(
                Path(folder), "make the scene", ModelRoute("codex_worker", "gpt-test")
            )
            self.assertIn("workspace-write", invocation.command)
            self.assertIn("gpt-test", invocation.command)
            self.assertEqual(invocation.stdin, "make the scene")

    def test_generic_cli_expands_safe_placeholders(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            route = ModelRoute(
                "generic_cli", "qwen-test", command=(
                    "qwen", "run", "--cwd", "{cwd}", "--model", "{model}",
                    "--prompt-file", "{prompt_file}", "--response-file", "{response_file}",
                )
            )
            invocation = build_invocation(root, "author scene", route)
            self.assertEqual(invocation.command[0], "qwen")
            self.assertIn(str(root.resolve()), invocation.command)
            self.assertIn("qwen-test", invocation.command)
            self.assertTrue(invocation.prompt_path.exists())
            self.assertEqual(invocation.prompt_path.read_text(encoding="utf-8"), "author scene")
            self.assertIsNone(invocation.stdin)

    def test_generic_cli_requires_an_explicit_command(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "command"):
                build_invocation(Path(folder), "task", ModelRoute("generic_cli"))


if __name__ == "__main__":
    unittest.main()
