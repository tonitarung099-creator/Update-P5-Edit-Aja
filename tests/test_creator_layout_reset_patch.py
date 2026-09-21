import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "creator-layout-reset.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class CreatorLayoutResetPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_layout_logic_is_reusable_from_toolbar_and_startup(self):
        self.assertIn("void MainWindow::applyCreatorLayout()", self.patch)
        self.assertIn("applyCreatorLayout();", self.patch)
        self.assertIn("savedCreatorLayoutVersion < creatorLayoutVersion", self.patch)
        self.assertIn('addWorkspaceButton(i18n("Layout")', self.patch)
        self.assertIn('creatorLayoutButton', self.patch)

    def test_restore_keeps_ai_agent_as_right_sidebar(self):
        self.assertIn(
            "mainDockWindow->addDockWidget(m_effectStackDock, KDDockWidgets::Location_OnRight, m_projectMonitorDock, sidebarSize);",
            self.patch,
        )
        self.assertIn("m_effectStackDock->addDockWidgetAsTab(m_aiAssistantDock);", self.patch)
        self.assertIn("m_aiAssistantDock->open();", self.patch)
        self.assertIn("m_aiAssistantDock->setAsCurrentTab();", self.patch)

    def test_restore_changes_only_panel_arrangement(self):
        self.assertNotIn("kdenlive_cut_clip", self.patch)
        self.assertNotIn("kdenlive_save_project", self.patch)
        self.assertNotIn("configureEditorAccess", self.patch)
        self.assertNotIn("saveFileAs(", self.patch)

    def test_layout_reset_patch_is_last_and_copied_to_craft(self):
        entry = self.manifest["apply_chain"][-1]
        self.assertEqual(entry["name"], "creator-layout-reset")
        self.assertEqual(entry["path"], "patches/creator-layout-reset.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {
            item["source"]: item["destination"]
            for item in self.manifest["blueprint_payloads"]
        }
        self.assertEqual(
            payloads["patches/creator-layout-reset.patch"],
            "craft/editaja/creator-layout-reset.patch",
        )

        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertTrue(chain.rstrip().endswith('("creator-layout-reset.patch", 1)]'))


if __name__ == "__main__":
    unittest.main()
