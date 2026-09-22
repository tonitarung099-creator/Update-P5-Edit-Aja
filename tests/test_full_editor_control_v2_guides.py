import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "full-editor-control-v2-guides.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class FullEditorControlV2GuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_four_native_guide_tools_are_registered_and_dispatched(self):
        for name in (
            "kdenlive_list_guides",
            "kdenlive_add_guide",
            "kdenlive_edit_guide",
            "kdenlive_delete_guide",
        ):
            self.assertGreaterEqual(self.patch.count(name), 2, name)

    def test_tools_use_native_project_guide_model_and_undoable_methods(self):
        for marker in (
            "model->getGuideModel()",
            "guideModel->getAllMarkers()",
            "guideModel->addMarker(",
            "guideModel->addRangeMarker(",
            "guideModel->editMarker(",
            "guideModel->removeMarker(",
        ):
            self.assertIn(marker, self.patch)

    def test_add_is_collision_safe_and_category_safe(self):
        self.assertIn("guideModel->hasMarker(position) && !overwrite", self.patch)
        self.assertIn("set overwrite=true to replace it", self.patch)
        self.assertIn("type != -1 && !pCore->markerTypes.contains(type)", self.patch)
        self.assertIn("Unknown guide category type", self.patch)

    def test_edit_never_moves_onto_an_existing_guide(self):
        self.assertIn("newPosition != position && guideModel->hasMarker(newPosition)", self.patch)
        self.assertIn("Another guide already exists at the new frame", self.patch)
        edit_registration = self.patch.split('QStringLiteral("kdenlive_edit_guide")', 1)[1].split('QStringLiteral("kdenlive_delete_guide")', 1)[0]
        self.assertNotIn('QStringLiteral("overwrite")', edit_registration)

    def test_list_reports_point_and_range_semantics(self):
        for marker in (
            'QStringLiteral("position_frame")',
            'QStringLiteral("position_seconds")',
            'QStringLiteral("has_range")',
            'QStringLiteral("duration_frames")',
            'QStringLiteral("duration_seconds")',
            'QStringLiteral("end_frame")',
            "guide.markerType()",
            "guide.comment()",
        ):
            self.assertIn(marker, self.patch)

    def test_patch_is_after_v1_and_copied_to_craft(self):
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        self.assertLess(names.index("full-editor-control-v1"), names.index("full-editor-control-v2-guides"))
        entry = next(entry for entry in self.manifest["apply_chain"] if entry["name"] == "full-editor-control-v2-guides")
        self.assertEqual(entry["path"], "patches/full-editor-control-v2-guides.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])
        payloads = {item["source"]: item["destination"] for item in self.manifest["blueprint_payloads"]}
        self.assertEqual(
            payloads["patches/full-editor-control-v2-guides.patch"],
            "craft/editaja/full-editor-control-v2-guides.patch",
        )
        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertLess(
            chain.index('("full-editor-control-v1.patch", 1)'),
            chain.index('("full-editor-control-v2-guides.patch", 1)'),
        )


if __name__ == "__main__":
    unittest.main()
