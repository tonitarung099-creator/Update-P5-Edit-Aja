import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "creator-workspace-filmora.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class CreatorWorkspaceFilmoraPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_workspace_uses_category_buttons_with_text_under_icons(self):
        self.assertIn("Qt::ToolButtonTextUnderIcon", self.patch)
        self.assertIn("QSize(72, 54)", self.patch)
        self.assertIn("bar->addSeparator();", self.patch)

    def test_ai_agent_is_visually_prominent_without_changing_behavior(self):
        self.assertIn('creatorAiAgentButton', self.patch)
        self.assertIn('Open the main AI Agent controls in the right sidebar.', self.patch)
        self.assertIn('m_aiAssistantDock->open();', self.patch)
        self.assertIn('m_aiAssistantDock->setAsCurrentTab();', self.patch)
        self.assertIn('QToolButton#creatorAiAgentButton', self.patch)

    def test_quick_edit_and_export_keep_existing_actions(self):
        self.assertIn('Quick Edit: potong 5', self.patch)
        self.assertIn('creatorLocalEditPreview', self.patch)
        self.assertIn('creatorLocalEditRun', self.patch)
        self.assertIn('creatorExportButton', self.patch)
        self.assertIn('project_render', self.patch)

    def test_patch_is_ui_only(self):
        self.assertIn('--- a/src/mainwindow.cpp', self.patch)
        self.assertIn('+++ b/src/mainwindow.cpp', self.patch)
        self.assertNotIn('src/aiassistant/', self.patch)
        self.assertNotIn('kdenlive_cut_clip', self.patch)
        self.assertNotIn('kdenlive_save_project', self.patch)

    def test_polish_patch_is_last_and_copied_to_craft(self):
        entry = self.manifest["apply_chain"][-1]
        self.assertEqual(entry["name"], "creator-workspace-filmora")
        self.assertEqual(entry["path"], "patches/creator-workspace-filmora.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {
            item["source"]: item["destination"]
            for item in self.manifest["blueprint_payloads"]
        }
        self.assertEqual(
            payloads["patches/creator-workspace-filmora.patch"],
            "craft/editaja/creator-workspace-filmora.patch",
        )

        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertTrue(chain.rstrip().endswith('("creator-workspace-filmora.patch", 1)]'))


if __name__ == "__main__":
    unittest.main()
