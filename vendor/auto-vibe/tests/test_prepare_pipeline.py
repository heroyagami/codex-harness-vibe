import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from scene_plan import read_scene_plan_document  # noqa: E402


class PreparePipelineTest(unittest.TestCase):
    def run_command(self, command, env=None):
        result = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"{command}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_shared_background_flows_through_scene_and_transition_staging(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scenes_dir = root / "scenes"
            transitions_dir = root / "transitions"
            template_dir = root / "sceneFolder"
            shutil.copytree(
                PROJECT_DIR / "sceneFolder",
                template_dir,
                ignore=shutil.ignore_patterns("node_modules", "out"),
            )
            design_systems_dir = root / "design-systems"
            for name in ("light-fixture", "dark-fixture"):
                (design_systems_dir / name).mkdir(parents=True)
                (design_systems_dir / name / "DESIGN.md").write_text(
                    f"# {name}\n", encoding="utf-8"
                )
            (design_systems_dir / "weights.json").write_text(
                json.dumps(
                    {
                        "light-fixture": {"theme": "light", "weight": 0.1},
                        "dark-fixture": {"theme": "dark", "weight": 50},
                    }
                ),
                encoding="utf-8",
            )
            (root / "transcription.srt").write_text(
                "1\n00:00:00,000 --> 00:00:02,000\n第一句\n\n"
                "2\n00:00:02,500 --> 00:00:05,500\n第二句\n",
                encoding="utf-8",
            )
            (root / "codex-prompt.md").write_text(
                "---\nvisual_theme: light\n---\n\n读取当前目录。\n",
                encoding="utf-8",
            )
            background_path = root / "resources" / "backgrounds" / "lightbg.png"
            background_path.parent.mkdir(parents=True)
            shutil.copy2(
                PROJECT_DIR / "resources" / "backgrounds" / "lightbg.png",
                background_path,
            )
            plan = {
                "fps": 30,
                "total_duration_seconds": "5.500",
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
                    {
                        "type": "custom",
                        "time_range_seconds": ["1.750", "2.750"],
                        "reason": "连续镜头。",
                    }
                ],
            }
            plan_path = root / "scene-plan.json"
            plan_path.write_text(
                json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            pnpm_log = root / "pnpm.log"
            fake_pnpm = root / "pnpm"
            fake_pnpm.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                'printf \'%s\\t%s\\n\' "$PWD" "$*" >> "$FAKE_PNPM_LOG"\n'
                "mkdir -p node_modules/.pnpm node_modules/.bin\n",
                encoding="utf-8",
            )
            fake_pnpm.chmod(0o755)
            env = {
                **os.environ,
                "PYTHON_BIN": sys.executable,
                "PNPM_BIN": str(fake_pnpm),
                "FAKE_PNPM_LOG": str(pnpm_log),
                "TEMPLATE_DIR": str(template_dir),
                "SCENES_DIR": str(scenes_dir),
                "DESIGN_SYSTEMS_DIR": str(design_systems_dir),
                "TRANSITION_TEMPLATE_DIR": str(PROJECT_DIR / "transitionFolder"),
                "TRANSITIONS_DIR": str(transitions_dir),
            }
            self.run_command(
                [str(PROJECT_DIR / "prepare-scenes.sh"), str(plan_path)],
                env=env,
            )

            install_lines = pnpm_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                install_lines,
                [
                    f"{template_dir.resolve()}\tinstall --frozen-lockfile "
                    "--registry=https://registry.npmmirror.com",
                ],
            )
            shared_node_modules = template_dir / "node_modules"
            generated_projects = [
                scenes_dir / "scene-001",
                scenes_dir / "scene-002",
                transitions_dir / "transition-001",
            ]
            for generated_project in generated_projects:
                node_modules = generated_project / "node_modules"
                self.assertTrue(node_modules.is_dir())
                self.assertFalse(node_modules.is_symlink())
                self.assertTrue((node_modules / ".cache").is_dir())
                self.assertFalse((node_modules / ".cache").is_symlink())
                shared_marker = node_modules / ".shared-dependencies"
                self.assertTrue(shared_marker.is_file())
                self.assertFalse(
                    Path(shared_marker.read_text(encoding="utf-8").strip()).is_absolute()
                )
                self.assertTrue((node_modules / ".pnpm").is_symlink())
                self.assertEqual(
                    (node_modules / ".pnpm").resolve(),
                    (shared_node_modules / ".pnpm").resolve(),
                )
                self.assertFalse(
                    Path(os.readlink(node_modules / ".pnpm")).is_absolute()
                )

            scene_one_config = (
                scenes_dir / "scene-001" / "remotion" / "scene-config.ts"
            ).read_text(encoding="utf-8")
            scene_two_config = (
                scenes_dir / "scene-002" / "remotion" / "scene-config.ts"
            ).read_text(encoding="utf-8")
            transition_config = (
                transitions_dir / "transition-001" / "remotion" / "transition-config.ts"
            ).read_text(encoding="utf-8")
            transition_prompt = (
                transitions_dir / "transition-001" / "transition-prompt.md"
            ).read_text(encoding="utf-8")
            self.assertIn('"top_left"', scene_one_config)
            self.assertIn('"top_right"', scene_two_config)
            self.assertIn("BACKGROUND_WIDTH = 1480", transition_config)
            self.assertIn("BACKGROUND_HEIGHT = 1840", transition_config)
            self.assertIn("FOREGROUND_TRAVEL = 1200", transition_config)
            self.assertIn(
                'TRANSITION_TYPE: "parallax" | "custom" = "custom"',
                transition_config,
            )
            self.assertIn('VISUAL_THEME = "light"', transition_config)
            self.assertIn('BACKGROUND_COLOR = "#eadeca"', transition_config)
            self.assertIn('"top_left"', transition_config)
            self.assertIn('"top_right"', transition_config)
            self.assertIn("依赖由脚手架预装", transition_prompt)
            self.assertIn("transition_type: custom", transition_prompt)
            self.assertNotIn("pnpm install", transition_prompt)
            self.assertTrue(
                (scenes_dir / "scene-001" / "design-system" / "light-fixture").is_dir()
            )
            self.assertFalse(
                (scenes_dir / "scene-001" / "design-system" / "dark-fixture").exists()
            )
            scene_prompt = (
                scenes_dir / "scene-001" / "claude-scene-prompt.md"
            ).read_text(encoding="utf-8")
            self.assertIn("visual_theme: light", scene_prompt)
            self.assertIn("拟物阴影、拼贴白边", scene_prompt)
            self.assertIn("主视觉坐标独立于 `background_anchor`", scene_prompt)
            self.assertIn('`column` 的水平居中用 `alignItems: "center"`', scene_prompt)
            self.assertIn("视觉复核总预算为 1 轮", scene_prompt)
            self.assertIn(
                "node scripts/remotion-cli.mjs still default", scene_prompt
            )
            self.assertIn("禁止使用 `npx remotion`", scene_prompt)
            self.assertIn("合成一张联系表，只调用一次 kimi-img-viewer", scene_prompt)
            self.assertIn("视觉复核最多触发 1 次集中修正", scene_prompt)
            self.assertIn("候选视频已通过技术校验", scene_prompt)
            self.assertIn("单轮视觉复核完成", scene_prompt)
            self.assertIn("阶段消息通过 `SendUserMessage` 实时转发给用户", scene_prompt)
            self.assertIn(
                "`status` 使用 `normal`",
                scene_prompt,
            )
            scene_runner = (
                scenes_dir / "scene-001" / "run-claude-ai.sh"
            ).read_text(encoding="utf-8")
            self.assertIn(
                "当前目录是本场景唯一的文件上下文；"
                "在当前目录内独立完成 `claude-scene-prompt.md`。",
                scene_runner,
            )
            self.assertIn("--brief", scene_runner)
            self.assertIn("CLAUDE_CODE_BRIEF=1", scene_runner)
            self.assertIn('.name=="SendUserMessage"', scene_runner)
            self.assertEqual(
                (
                    scenes_dir / "scene-001" / "public" / "img" / "lightbg.png"
                ).read_bytes(),
                background_path.read_bytes(),
            )

            document = read_scene_plan_document(plan_path)
            for scene in document["scenes"]:
                scene_dir = scenes_dir / scene["scene_id"]
                artifacts = scene_dir / "artifacts"
                artifacts.mkdir()
                handle_name = "exit" if scene["scene_id"] == "scene-001" else "entry"
                foreground = artifacts / f"{handle_name}-foreground.png"
                composite = artifacts / f"{handle_name}-composite.png"
                foreground.write_bytes(b"foreground")
                composite.write_bytes(b"composite")
                (scene_dir / scene["output_file"]).write_bytes(b"clip")
                manifest = {
                    "scene_id": scene["scene_id"],
                    "fps": 30,
                    "width": 1080,
                    "height": 1440,
                    "frame_range": scene["frame_range"],
                    "duration_in_frames": scene["duration_in_frames"],
                    "visual_theme": "light",
                    "background": scene["background"]["target"],
                    "background_width": 1480,
                    "background_height": 1840,
                    "background_color": "#eadeca",
                    "background_anchor": scene["background_anchor"],
                    "handles": {
                        handle_name: {
                            "foreground": f"artifacts/{foreground.name}",
                            "composite": f"artifacts/{composite.name}",
                        }
                    },
                }
                (artifacts / "scene-manifest.json").write_text(
                    json.dumps(manifest), encoding="utf-8"
                )

            self.run_command(
                [
                    sys.executable,
                    str(PROJECT_DIR / "stage-transition.py"),
                    str(plan_path),
                    "transition-001",
                    "--scenes-dir",
                    str(scenes_dir),
                    "--transitions-dir",
                    str(transitions_dir),
                ]
            )
            staged_input = transitions_dir / "transition-001" / "public" / "input"
            self.assertTrue((staged_input / "background.png").is_file())
            self.assertFalse((staged_input / "from-background.png").exists())
            self.assertFalse((staged_input / "to-background.png").exists())

    def test_empty_design_system_option_leaves_design_to_claude(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scenes_dir = root / "scenes"
            design_systems_dir = root / "design-systems"
            design_systems_dir.mkdir()
            (design_systems_dir / "weights.json").write_text(
                json.dumps({"__none__": {"weight": 100}}), encoding="utf-8"
            )
            (root / "transcription.srt").write_text(
                "1\n00:00:00,000 --> 00:00:02,000\n第一句\n", encoding="utf-8"
            )

            background_path = root / "resources" / "backgrounds" / "lightbg.png"
            background_path.parent.mkdir(parents=True)
            shutil.copy2(
                PROJECT_DIR / "resources" / "backgrounds" / "lightbg.png",
                background_path,
            )
            plan = {
                "fps": 30,
                "visual_theme": "light",
                "total_duration_seconds": "2.000",
                "background": {
                    "source": "resources/backgrounds/lightbg.png",
                    "target": "public/img/lightbg.png",
                    "width": 1480,
                    "height": 1840,
                },
                "scenes": [
                    {
                        "time_range_seconds": ["0.000", "2.000"],
                        "subtitle_text": "00:00:00,000 --> 00:00:02,000\n第一句",
                        "research_brief": "无额外补充",
                        "image_resources": [],
                    }
                ],
                "transitions": [],
            }
            plan_path = root / "scene-plan.json"
            plan_path.write_text(
                json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            self.run_command(
                [
                    sys.executable,
                    str(PROJECT_DIR / "prepare-scenes.py"),
                    str(PROJECT_DIR / "sceneFolder"),
                    str(scenes_dir),
                    str(design_systems_dir),
                    str(plan_path),
                ]
            )

            scene_dir = scenes_dir / "scene-001"
            self.assertFalse((scene_dir / "design-system").exists())
            frame = (scene_dir / "frame.md").read_text(encoding="utf-8")
            self.assertNotIn("Selected design system", frame)
            self.assertIn("otherwise define the visual language", frame)
            prompt = (scene_dir / "claude-scene-prompt.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("没有时，根据本场景内容自定视觉语言", prompt)


if __name__ == "__main__":
    unittest.main()
