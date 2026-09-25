import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "creator-layout-filmora.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class CreatorLayoutFilmoraPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_layout_migrates_only_once(self):
        self.assertIn("#include <QSettings>", self.patch)
        self.assertIn('editaja/creatorLayoutVersion', self.patch)
        self.assertIn("savedCreatorLayoutVersion < creatorLayoutVersion", self.patch)
        self.assertIn("constexpr int creatorLayoutVersion = 2", self.patch)
        self.assertIn(
            'editAjaSettings.setValue(QStringLiteral("editaja/creatorLayoutVersion"), creatorLayoutVersion);',
            self.patch,
        )

    def test_creator_layout_has_media_viewer_ai_and_timeline_structure(self):
        self.assertIn("dockWindowSize.width() * 22 / 100", self.patch)
        self.assertIn("dockWindowSize.width() * 28 / 100", self.patch)
        self.assertIn("dockWindowSize.height() * 45 / 100", self.patch)
        self.assertIn(
            "mainDockWindow->addDockWidget(m_projectBinDock, KDDockWidgets::Location_OnLeft, m_projectMonitorDock, binSize);",
            self.patch,
        )
        self.assertIn(
            "mainDockWindow->addDockWidget(m_effectStackDock, KDDockWidgets::Location_OnRight, m_projectMonitorDock, sidebarSize);",
            self.patch,
        )
        self.assertIn(
            "mainDockWindow->addDockWidget(m_timelineDock, KDDockWidgets::Location_OnBottom, nullptr, timelineSize);",
            self.patch,
        )

    def test_secondary_panels_do_not_crowd_default_layout(self):
        self.assertIn("m_clipMonitorDock->close();", self.patch)
        self.assertIn("m_mixerDock->close();", self.patch)
        self.assertIn("m_projectMonitorDock->open();", self.patch)
        self.assertIn("m_projectMonitorDock->setAsCurrentTab();", self.patch)

    def test_patch_preserves_native_editing_behavior(self):
        self.assertIn("--- a/src/mainwindow.cpp", self.patch)
        self.assertNotIn("kdenlive_cut_clip", self.patch)
        self.assertNotIn("kdenlive_save_project", self.patch)
        self.assertNotIn("configureEditorAccess", self.patch)

    def test_layout_patch_precedes_reset_patch_and_is_copied_to_craft(self):
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        layout_index = names.index("creator-layout-filmora")
        reset_index = names.index("creator-layout-reset")
        self.assertLess(layout_index, reset_index)

        entry = self.manifest["apply_chain"][layout_index]
        self.assertEqual(entry["path"], "patches/creator-layout-filmora.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {
            item["source"]: item["destination"]
            for item in self.manifest["blueprint_payloads"]
        }
        self.assertEqual(
            payloads["patches/creator-layout-filmora.patch"],
            "craft/editaja/creator-layout-filmora.patch",
        )

        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertIn('("creator-layout-filmora.patch", 1)', chain)
        self.assertIn('("creator-layout-reset.patch", 1)', chain)
        self.assertLess(
            chain.index('("creator-layout-filmora.patch", 1)'),
            chain.index('("creator-layout-reset.patch", 1)'),
        )


if __name__ == "__main__":
    unittest.main()
