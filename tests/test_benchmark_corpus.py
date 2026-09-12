import unittest
from pathlib import Path

from legal_auto_motion.benchmark_corpus import validate_corpus


class BenchmarkCorpusTests(unittest.TestCase):
    def test_corpus_v1_is_valid_and_diverse(self):
        root = Path(__file__).resolve().parents[1] / "benchmarks" / "corpus-v1"
        report = validate_corpus(root)
        self.assertEqual(report["status"], "valid")
        self.assertGreaterEqual(report["case_count"], 6)
        self.assertGreaterEqual(report["semantic_type_count"], 5)


if __name__ == "__main__":
    unittest.main()
