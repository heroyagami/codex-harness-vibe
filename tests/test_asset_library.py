import tempfile
import unittest
from pathlib import Path

from legal_auto_motion.asset_library import AssetLibrary


class AssetLibraryTests(unittest.TestCase):
    def test_assets_are_deduplicated_selected_and_materialized(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "hospital.svg"
            source.write_text("<svg/>", encoding="utf-8")
            library = AssetLibrary(root / "library")
            first = library.add(source, tags=["医院", "医疗"], license_name="CC0")
            second = library.add(source, tags=["建筑"], license_name="CC0")
            self.assertEqual(first["asset_id"], second["asset_id"])
            selected = library.select("患者进入医院", limit=5)
            self.assertEqual(len(selected), 1)
            destination = root / "run" / "public" / "library"
            manifest = library.materialize(selected, destination)
            self.assertEqual(len(manifest), 1)
            self.assertTrue((destination / manifest[0]["filename"]).exists())


if __name__ == "__main__":
    unittest.main()
