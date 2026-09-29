import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "creator-layout-reset.patch"
FILMORA_PATCH = ROOT / "patches" / "creator-layout-filmora.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class CreatorLayoutResetPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.filmora_patch = FILMORA_PATCH.read_text(encoding="utf-8")
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
        self.assertIn("dockWindowSize.width() * 28 / 100", self.patch)
        self.assertIn('editaja/creatorLayoutVersion"), 2', self.patch)

    def test_restore_changes_only_panel_arrangement(self):
        self.assertNotIn("kdenlive_cut_clip", self.patch)
        self.assertNotIn("kdenlive_save_project", self.patch)
        self.assertNotIn("configureEditorAccess", self.patch)
        self.assertNotIn("saveFileAs(", self.patch)

    def test_reset_preimage_matches_layout_v2_from_previous_patch(self):
        filmora_additions = "\n".join(
            line[1:]
            for line in self.filmora_patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        reset_deletions = "\n".join(
            line[1:]
            for line in self.patch.splitlines()
            if line.startswith("-") and not line.startswith("---")
        )
        expected_v2_layout = (
            "const QSize timelineSize(0, qMax(270, dockWindowSize.height() * 45 / 100));",
            "const QSize binSize(qMax(270, dockWindowSize.width() * 22 / 100), qMax(320, dockWindowSize.height() * 53 / 100));",
            "const QSize sidebarSize(qMax(350, dockWindowSize.width() * 28 / 100), qMax(320, dockWindowSize.height() * 53 / 100));",
        )
        for line in expected_v2_layout:
            self.assertIn(line, filmora_additions)
            self.assertIn(line, reset_deletions)

        self.assertNotIn(
            "const QSize timelineSize(0, qMax(260, dockWindowSize.height() * 44 / 100));",
            reset_deletions,
        )
        self.assertNotIn(
            "const QSize sidebarSize(qMax(340, dockWindowSize.width() * 26 / 100), qMax(320, dockWindowSize.height() * 54 / 100));",
            reset_deletions,
        )

    def test_layout_reset_follows_layout_migration_and_is_copied_to_craft(self):
        names = [item["name"] for item in self.manifest["apply_chain"]]
        self.assertLess(names.index("creator-layout-filmora"), names.index("creator-layout-reset"))
        entry = self.manifest["apply_chain"][names.index("creator-layout-reset")]
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
        self.assertLess(chain.index('("creator-layout-filmora.patch", 1)'), chain.index('("creator-layout-reset.patch", 1)'))


if __name__ == "__main__":
    unittest.main()
