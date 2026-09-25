import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "gemini-ui-copy.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class GeminiUiCopyPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_primary_panel_is_explicitly_gemini_only(self):
        additions = "\n".join(
            line[1:] for line in self.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        self.assertIn("AI Agent bawaan menggunakan Google Gemini", additions)
        self.assertIn("hingga 100 API key Gemini", additions)
        self.assertNotIn("OpenAI-compatible API", additions)

    def test_redundant_group_title_is_cleared(self):
        self.assertIn("+    agentGroup->setTitle(QString());", self.patch)
        self.assertIn("+    description->setText(i18n(\"AI Agent bawaan menggunakan Google Gemini.", self.patch)
        additions = "\n".join(
            line[1:] for line in self.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        self.assertNotIn("AI Agent — Main Control", additions)

    def test_patch_is_after_gemini_pool_and_before_later_extensions(self):
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        gemini_index = names.index("gemini-only-key-pool")
        ui_index = names.index("gemini-ui-copy")
        self.assertLess(gemini_index, ui_index)
        if "full-editor-control-v1" in names:
            self.assertLess(ui_index, names.index("full-editor-control-v1"))

        entry = self.manifest["apply_chain"][ui_index]
        self.assertEqual(entry["path"], "patches/gemini-ui-copy.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {item["source"]: item["destination"] for item in self.manifest["blueprint_payloads"]}
        self.assertEqual(
            payloads["patches/gemini-ui-copy.patch"],
            "craft/editaja/gemini-ui-copy.patch",
        )
        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertIn('("gemini-ui-copy.patch", 1)', chain)
        if "full-editor-control-v1" in names:
            self.assertLess(
                chain.index('("gemini-ui-copy.patch", 1)'),
                chain.index('("full-editor-control-v1.patch", 1)'),
            )


if __name__ == "__main__":
    unittest.main()
