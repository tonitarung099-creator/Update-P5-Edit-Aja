import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "ai-agent-toolbox.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class AiAgentToolboxPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_supporting_tools_move_into_compact_toolbox(self):
        self.assertIn("#include <QToolBox>", self.patch)
        self.assertIn('aiAssistantToolbox', self.patch)
        self.assertIn('toolBox->addItem(localEditGroup, i18n("Quick Edit"))', self.patch)
        self.assertIn('toolBox->addItem(filmGroup, i18n("Film Context"))', self.patch)
        self.assertIn('toolBox->addItem(apiGroup, i18n("API"))', self.patch)
        self.assertIn('toolBox->addItem(mcpGroup, i18n("MCP"))', self.patch)
        self.assertIn('toolBox->addItem(aiEditGroup, i18n("AI Edit"))', self.patch)
        self.assertIn("background: #0f1724", self.patch)
        self.assertIn("border-color: #536dfe", self.patch)
        self.assertIn("font-size: 11px", self.patch)

    def test_agent_main_control_remains_outside_toolbox(self):
        self.assertNotIn('toolBox->addItem(agentGroup', self.patch)
        self.assertNotIn('layout->addWidget(agentGroup);', "\n".join(
            line[1:] for line in self.patch.splitlines()
            if line.startswith("-") and not line.startswith("---")
        ))

    def test_toolbox_defaults_to_quick_edit_and_keeps_existing_groups(self):
        self.assertIn("toolBox->setCurrentIndex(0);", self.patch)
        self.assertNotIn("delete localEditGroup", self.patch)
        self.assertNotIn("delete filmGroup", self.patch)
        self.assertNotIn("delete apiGroup", self.patch)

    def test_patch_is_ui_only(self):
        self.assertIn("--- a/src/aiassistant/aiassistantwidget.cpp", self.patch)
        self.assertIn("+++ b/src/aiassistant/aiassistantwidget.cpp", self.patch)
        self.assertNotIn("src/mainwindow.cpp", self.patch)
        self.assertNotIn("kdenlive_cut_clip", self.patch)
        self.assertNotIn("kdenlive_save_project", self.patch)

    def test_toolbox_patch_precedes_creator_layout_and_is_copied_to_craft(self):
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        toolbox_index = names.index("ai-agent-toolbox")
        layout_index = names.index("creator-layout-filmora")
        self.assertLess(toolbox_index, layout_index)

        entry = self.manifest["apply_chain"][toolbox_index]
        self.assertEqual(entry["path"], "patches/ai-agent-toolbox.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {
            item["source"]: item["destination"]
            for item in self.manifest["blueprint_payloads"]
        }
        self.assertEqual(
            payloads["patches/ai-agent-toolbox.patch"],
            "craft/editaja/ai-agent-toolbox.patch",
        )

        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertIn('("ai-agent-toolbox.patch", 1)', chain)
        self.assertIn('("creator-layout-filmora.patch", 1)', chain)
        self.assertLess(
            chain.index('("ai-agent-toolbox.patch", 1)'),
            chain.index('("creator-layout-filmora.patch", 1)'),
        )


if __name__ == "__main__":
    unittest.main()
