import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "bounded-ai-output.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class BoundedAiOutputPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_trace_and_history_have_hard_display_bounds(self):
        for marker in (
            "boundedDisplayHtml",
            "boundedPlainDisplayText",
            "setMaximumBlockCount(600)",
            "setMaximumBlockCount(120)",
            "boundedDisplayHtml(text, 12000)",
            "boundedPlainDisplayText(command, 800)",
            'boundedPlainDisplayText(result.value(QStringLiteral("message")).toString(), 2400)',
        ):
            self.assertIn(marker, self.patch)

    def test_large_html_is_flattened_before_truncated_display(self):
        self.assertIn("QTextDocument document;", self.patch)
        self.assertIn("document.setHtml(html);", self.patch)
        self.assertIn("document.toPlainText()", self.patch)
        self.assertIn("toHtmlEscaped()", self.patch)
        self.assertIn("full tool data is preserved for the agent", self.patch)

    def test_only_sidebar_display_path_is_changed(self):
        self.assertIn("--- a/src/aiassistant/aiassistantwidget.cpp", self.patch)
        self.assertNotIn("openaicompatibleagent.cpp", self.patch)
        self.assertNotIn("m_messages", self.patch)
        self.assertNotIn("toolCatalog", self.patch)
        self.assertNotIn("invokeOrStart", self.patch)

    def test_patch_precedes_gemini_pool_and_is_copied_to_craft(self):
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        bounded_index = names.index("bounded-ai-output")
        entry = self.manifest["apply_chain"][bounded_index]
        self.assertEqual(entry["name"], "bounded-ai-output")
        self.assertEqual(entry["path"], "patches/bounded-ai-output.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {
            item["source"]: item["destination"]
            for item in self.manifest["blueprint_payloads"]
        }
        self.assertEqual(
            payloads["patches/bounded-ai-output.patch"],
            "craft/editaja/bounded-ai-output.patch",
        )

        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertTrue(chain.rstrip().endswith('("bounded-ai-output.patch", 1)]'))


if __name__ == "__main__":
    unittest.main()
