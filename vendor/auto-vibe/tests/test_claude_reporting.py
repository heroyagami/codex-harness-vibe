import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


class ClaudeReportingTest(unittest.TestCase):
    def test_runner_exposes_each_brief_message_before_claude_exits(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scene_dir = root / "scene-smoke"
            fake_bin = root / "bin"
            scene_dir.mkdir()
            fake_bin.mkdir()

            runner = scene_dir / "run-claude-ai.sh"
            shutil.copy2(PROJECT_DIR / "sceneFolder" / runner.name, runner)
            (scene_dir / "claude-scene-prompt.md").write_text(
                "# reporting smoke test\n", encoding="utf-8"
            )

            first = {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "SendUserMessage",
                            "input": {
                                "message": "[[USER_MESSAGE]]first stage",
                                "status": "normal",
                            },
                        }
                    ]
                },
            }
            second = {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "SendUserMessage",
                            "input": {
                                "message": "[[USER_MESSAGE]]second stage",
                                "status": "normal",
                            },
                        }
                    ]
                },
            }
            fake_claude = fake_bin / "claude"
            fake_claude.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                '[[ "${CLAUDE_CODE_BRIEF:-}" == "1" ]]\n'
                '[[ " $* " == *" --brief "* ]]\n'
                f"printf '%s\\n' {json.dumps(json.dumps(first))}\n"
                "sleep 3\n"
                f"printf '%s\\n' {json.dumps(json.dumps(second))}\n",
                encoding="utf-8",
            )
            fake_claude.chmod(0o755)

            user_log = root / "user.log"
            env = {
                **os.environ,
                "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
                "RAW_LOG": str(root / "raw.jsonl"),
                "STDERR_LOG": str(root / "stderr.log"),
                "USER_LOG": str(user_log),
            }
            process = subprocess.Popen(
                [str(runner)],
                cwd=scene_dir,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            first_wait = subprocess.run(
                [str(runner), "--wait-message", "1"],
                cwd=scene_dir,
                env=env,
                text=True,
                capture_output=True,
                timeout=5,
            )
            self.assertEqual(first_wait.returncode, 0, first_wait.stderr)
            self.assertEqual(
                first_wait.stdout.strip(), "[[USER_MESSAGE]]first stage"
            )
            self.assertIsNone(process.poll())

            second_wait = subprocess.run(
                [str(runner), "--wait-message", "2"],
                cwd=scene_dir,
                env=env,
                text=True,
                capture_output=True,
                timeout=6,
            )
            self.assertEqual(second_wait.returncode, 0, second_wait.stderr)
            self.assertEqual(
                second_wait.stdout.strip(), "[[USER_MESSAGE]]second stage"
            )

            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stderr)
            self.assertEqual(
                user_log.read_text(encoding="utf-8").splitlines(),
                [
                    "[[USER_MESSAGE]]first stage",
                    "[[USER_MESSAGE]]second stage",
                    "[[USER_MESSAGE]]claude 进程已结束，exit_code=0",
                ],
            )
            self.assertIn("[[USER_MESSAGE]]first stage", stdout)


if __name__ == "__main__":
    unittest.main()
