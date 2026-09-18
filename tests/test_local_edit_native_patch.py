import base64
import bz2
import hashlib
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCH_FILE = ROOT / "patches" / "phase12-local-edit-native.patch.bz2.b64"
EXPECTED_SHA256 = "d8729f8d3cbe09e7818d5d5a4ab8cc690a45ac9f6982fdf98d0ded6732665652"


class LocalEditNativePatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        encoded = PATCH_FILE.read_text(encoding="ascii")
        cls.patch = bz2.decompress(base64.b64decode(encoded)).decode("utf-8")
        cls.digest = hashlib.sha256(cls.patch.encode("utf-8")).hexdigest()

    def test_patch_checksum(self):
        self.assertEqual(self.digest, EXPECTED_SHA256)

    def test_patch_only_targets_expected_native_sources(self):
        plus_paths = [
            line[4:].split("\t", 1)[0].split(" ", 1)[0]
            for line in self.patch.splitlines()
            if line.startswith("+++ ")
        ]
        self.assertEqual(
            plus_paths,
            [
                "editaja_phase12/src/aiassistant/aiassistantwidget.cpp",
                "editaja_phase12/src/aiassistant/aiassistantwidget.h",
                "editaja_phase12/src/mainwindow.cpp",
            ],
        )

    def test_command_bar_contract(self):
        self.assertIn("creatorLocalEditInput", self.patch)
        self.assertIn("Local Edit — Lightweight", self.patch)
        self.assertIn("executeLocalEditCommand", self.patch)
        self.assertIn("ptong 5", self.patch)
        self.assertIn("hpus sceen 73", self.patch)

    def test_native_transform_keyframe_contract(self):
        self.assertIn("kdenlive_set_transform_keyframes", self.patch)
        self.assertIn("KeyframeType::CurveSmooth", self.patch)
        self.assertIn("target_duration_seconds", self.patch)
        self.assertIn("hold_after_target", self.patch)
        self.assertIn("actualSeconds / referenceSeconds", self.patch)
        self.assertIn("startScale + (targetScale - startScale) * progress", self.patch)

    def test_build_pipeline_applies_phase12(self):
        blueprint = (ROOT / "craft" / "editaja" / "editaja.py").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "build-windows.yml").read_text(encoding="utf-8")
        self.assertIn('("phase12.patch", 1)', blueprint)
        self.assertIn("PHASE12_SHA256", workflow)
        self.assertIn("phase12-local-edit-native.patch.bz2.b64", workflow)
        self.assertIn("craft/editaja/phase12.patch", workflow)
        self.assertIn("kdenlive_set_transform_keyframes", workflow)


if __name__ == "__main__":
    unittest.main()
