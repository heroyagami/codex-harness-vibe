import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.providers import ProviderUnavailable, is_retryable_model_failure, read_manual_critique


class ProviderTests(unittest.TestCase):
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
