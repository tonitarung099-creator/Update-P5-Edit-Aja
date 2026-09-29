import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "bounded-ai-output.patch"
SIDEBAR_PATCH = ROOT / "patches" / "ai-agent-sidebar.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class BoundedAiOutputPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.sidebar_patch = SIDEBAR_PATCH.read_text(encoding="utf-8")
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

    def test_bounded_patch_context_matches_modern_sidebar(self):
        sidebar_additions = "\n".join(
            line[1:]
            for line in self.sidebar_patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        bounded_context = "\n".join(
            line[1:] if line.startswith(("+", "-")) else line
            for line in self.patch.splitlines()
            if not line.startswith(("+++", "---", "@@"))
        )
        for line in (
            "m_output->setMinimumHeight(200);",
            'm_output->setPlaceholderText(i18n("Aktivitas dan hasil AI Agent akan muncul di sini."));',
        ):
            self.assertIn(line, sidebar_additions)
            self.assertIn(line, bounded_context)

        self.assertNotIn("m_output->setMinimumHeight(220);", bounded_context)
        self.assertNotIn("Agent tool calls and results will appear here.", bounded_context)

    def test_only_sidebar_display_path_is_changed(self):
        self.assertIn("--- a/src/aiassistant/aiassistantwidget.cpp", self.patch)
        self.assertNotIn("openaicompatibleagent.cpp", self.patch)
        self.assertNotIn("m_messages", self.patch)
        self.assertNotIn("toolCatalog", self.patch)
        self.assertNotIn("invokeOrStart", self.patch)

    def test_patch_precedes_gemini_pool_and_is_copied_to_craft(self):
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        bounded_index = names.index("bounded-ai-output")
        self.assertLess(names.index("ai-agent-sidebar"), bounded_index)
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
        self.assertIn('("bounded-ai-output.patch", 1)', chain)
        self.assertLess(
            chain.index('("ai-agent-sidebar.patch", 1)'),
            chain.index('("bounded-ai-output.patch", 1)'),
        )
        if "gemini-only-key-pool" in names:
            self.assertLess(bounded_index, names.index("gemini-only-key-pool"))
            self.assertLess(
                chain.index('("bounded-ai-output.patch", 1)'),
                chain.index('("gemini-only-key-pool.patch", 1)'),
            )

    def test_post_sidebar_patch_chain_order_is_stable(self):
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        expected = [
            "bounded-ai-output",
            "gemini-only-key-pool",
            "gemini-ui-copy",
            "full-editor-control-v1",
            "full-editor-control-v2-guides",
        ]
        for name in expected:
            self.assertIn(name, names)
        for before, after in zip(expected, expected[1:]):
            self.assertLess(names.index(before), names.index(after))

        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        expected_patch_names = [
            "bounded-ai-output.patch",
            "gemini-only-key-pool.patch",
            "gemini-ui-copy.patch",
            "full-editor-control-v1.patch",
            "full-editor-control-v2-guides.patch",
        ]
        for patch_name in expected_patch_names:
            self.assertIn(f'(\"{patch_name}\", 1)', chain)
        for before, after in zip(expected_patch_names, expected_patch_names[1:]):
            self.assertLess(chain.index(f'(\"{before}\", 1)'), chain.index(f'(\"{after}\", 1)'))


if __name__ == "__main__":
    unittest.main()
