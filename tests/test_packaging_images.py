import tempfile
import unittest
from pathlib import Path

from scripts.prepare_package_images import compatible_image_candidates


class PackagingImageTests(unittest.TestCase):
    def test_prefers_minsizerel_compatible_image_for_same_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "image-MinSizeRel-14.2.0").mkdir()
            (root / "image-Release-14.2.0").mkdir()
            candidates = compatible_image_candidates(
                root, "image-RelWithDebInfo-14.2.0"
            )
            self.assertEqual(
                [path.name for path in candidates],
                ["image-MinSizeRel-14.2.0", "image-Release-14.2.0"],
            )

    def test_ignores_debug_symbols_and_other_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "image-MinSizeRel-14.2.0-dbg").mkdir()
            (root / "image-MinSizeRel-13.2.0").mkdir()
            self.assertEqual(
                compatible_image_candidates(root, "image-RelWithDebInfo-14.2.0"),
                [],
            )


if __name__ == "__main__":
    unittest.main()
