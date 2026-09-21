import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "bounded-ai-ui-output.patch"


class BoundedAiUiOutputPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")

    def test_agent_trace_has_entry_and_history_bounds(self):
        self.assertIn("maxTraceChars = 32768", self.patch)
        self.assertIn("m_output->document()->setMaximumBlockCount(400)", self.patch)
        self.assertIn("m_localEditHistory->document()->setMaximumBlockCount(160)", self.patch)

    def test_large_trace_is_flattened_and_escaped_before_display(self):
        self.assertIn("QTextDocument prefixDocument", self.patch)
        self.assertIn("prefixDocument.setHtml(html.left(maxTraceChars))", self.patch)
        self.assertIn("plainPrefix.toHtmlEscaped()", self.patch)
        self.assertIn("Display truncated to keep the AI sidebar responsive.", self.patch)

    def test_local_history_caps_plain_text_before_html_escaping(self):
        self.assertIn("boundedUiPlainText(command.trimmed(), 2048).toHtmlEscaped()", self.patch)
        self.assertIn('boundedUiPlainText(result.value(QStringLiteral("message")).toString(), 4096).toHtmlEscaped()', self.patch)

    def test_model_tool_result_path_is_not_modified(self):
        self.assertNotIn("appendToolResult", self.patch)
        self.assertNotIn("m_messages", self.patch)
        self.assertNotIn("AgentToolRegistry", self.patch)


if __name__ == "__main__":
    unittest.main()
