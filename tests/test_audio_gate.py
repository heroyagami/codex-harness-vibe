import unittest

from legal_auto_motion.audio_gate import classify_mix_levels, summarize_mix_classes


class AudioGateTests(unittest.TestCase):
    def test_classifies_masked_and_unmasked_effects(self):
        self.assertEqual(classify_mix_levels(effect_db=-25, voice_db=-50), "unmasked")
        self.assertEqual(classify_mix_levels(effect_db=-20, voice_db=-18), "audible")
        self.assertEqual(classify_mix_levels(effect_db=-38, voice_db=-18), "masked")

    def test_rejects_mix_when_most_effects_are_masked(self):
        report = summarize_mix_classes(["masked", "masked", "audible", "unmasked"], duration_seconds=60)
        self.assertEqual(report["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
