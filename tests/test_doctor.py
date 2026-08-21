import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.doctor import compare_vendor


class DoctorTests(unittest.TestCase):
    def test_unknown_vendor_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            upstream, vendor = root / "upstream", root / "vendor"
            upstream.mkdir()
            vendor.mkdir()
            (upstream / "a.txt").write_text("source", encoding="utf-8")
            (vendor / "a.txt").write_text("changed", encoding="utf-8")
            report = compare_vendor(upstream, vendor)
            self.assertEqual(report["status"], "rejected")
            self.assertEqual(report["unexpected_differences"], ["a.txt"])


if __name__ == "__main__":
    unittest.main()
