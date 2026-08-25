import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.doctor import KNOWN_VENDOR_OVERRIDES, compare_vendor


class DoctorTests(unittest.TestCase):
    def test_approved_harness_overrides_are_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            upstream, vendor = root / "upstream", root / "vendor"
            upstream.mkdir()
            vendor.mkdir()
            for relative in KNOWN_VENDOR_OVERRIDES:
                source = upstream / relative
                installed = vendor / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                installed.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("source", encoding="utf-8")
                installed.write_text("approved override", encoding="utf-8")

            report = compare_vendor(upstream, vendor)

            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["unexpected_differences"], [])
            self.assertEqual(set(report["known_overrides"]), KNOWN_VENDOR_OVERRIDES)

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
