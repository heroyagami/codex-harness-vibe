import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.facts import audit_sources, numeric_facts
from legal_auto_motion.timing import audit_timing


class FactAuditTests(unittest.TestCase):
    def test_currency_spoken_variant_is_normalized(self):
        self.assertEqual(numeric_facts("5180块"), {(5180.0, "元")})

    def test_rejects_invented_percentage_case_number_and_ruling(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder) / "scene-003"
            authored = scene / "scenes"
            authored.mkdir(parents=True)
            (authored / "DefaultScene.tsx").write_text(
                """export const x = <div>减少赔付 50%</div>;
                const fake = '(2025) 京民终 0117号';
                const ruling = '驳回上诉，维持原判';""",
                encoding="utf-8",
            )
            contract = {
                "narration": "就因为他献过血，撞他的人反而想少赔钱",
                "approved_copy": ["献过血", "少赔钱"],
            }
            reasons = [item.reason for item in audit_sources(scene, contract)]
            self.assertTrue(any("屏幕中文" in reason for reason in reasons))
            self.assertTrue(any("50%" in reason for reason in reasons))
            self.assertTrue(any("案号" in reason for reason in reasons))

    def test_accepts_approved_short_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder) / "scene-008"
            authored = scene / "scenes"
            authored.mkdir(parents=True)
            (authored / "DefaultScene.tsx").write_text(
                "export const x = <><div>医疗费 8万8千多</div><div>用血费 5180元</div></>;",
                encoding="utf-8",
            )
            contract = {
                "narration": "医药费花了8万8千多，这里头有5180块是输血的钱",
                "approved_copy": ["医疗费 8万8千多", "用血费 5180元"],
            }
            self.assertEqual(audit_sources(scene, contract), [])

    def test_accepts_same_date_with_different_separators(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder) / "scene-004"
            authored = scene / "scenes"
            authored.mkdir(parents=True)
            (authored / "DefaultScene.tsx").write_text(
                "export const x = <div>2018.01.04</div>;",
                encoding="utf-8",
            )
            contract = {
                "narration": "把时间拨回2018年1月4日",
                "approved_copy": ["2018年1月4日"],
            }
            self.assertEqual(audit_sources(scene, contract), [])


class TimingAuditTests(unittest.TestCase):
    def test_rejects_global_frames_outside_local_duration(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder)
            (scene / "scenes").mkdir()
            (scene / "scene-metadata.json").write_text(
                '{"duration_in_frames": 180}', encoding="utf-8"
            )
            (scene / "scenes" / "DefaultScene.tsx").write_text(
                "const BEAT = {enter: 320, verdictIn: 468, exit: 500};",
                encoding="utf-8",
            )
            self.assertGreaterEqual(len(audit_timing(scene)), 3)


if __name__ == "__main__":
    unittest.main()
