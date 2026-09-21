import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "agent-request-timeout-ui.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class AgentRequestTimeoutUiPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_timeout_setting_has_safe_user_range_and_default(self):
        for marker in (
            "QSpinBox",
            "setRange(15, 3600)",
            'requestTimeoutSeconds"), 600',
            'setSuffix(i18n(" s"))',
            'Request timeout',
        ):
            self.assertIn(marker, self.patch)

    def test_timeout_setting_persists_and_drives_agent(self):
        self.assertIn('setObjectName(QStringLiteral("agentRequestTimeoutSeconds"))', self.patch)
        self.assertIn('QSpinBox::valueChanged', self.patch)
        self.assertIn('setValue(QStringLiteral("requestTimeoutSeconds"), seconds)', self.patch)
        self.assertIn('const int requestTimeoutSeconds = qBound(15, settings.value(QStringLiteral("requestTimeoutSeconds"), 600).toInt(), 3600)', self.patch)
        self.assertIn("m_agent->setRequestTimeoutMs(requestTimeoutSeconds * 1000)", self.patch)

    def test_ui_patch_does_not_modify_crlf_header(self):
        self.assertNotIn("aiassistantwidget.h", self.patch)
        self.assertNotIn("m_requestTimeoutSeconds", self.patch)

    def test_ui_patch_is_last_and_copied_to_craft(self):
        entry = self.manifest["apply_chain"][-1]
        self.assertEqual(entry["name"], "agent-request-timeout-ui")
        self.assertEqual(entry["path"], "patches/agent-request-timeout-ui.patch")
        payloads = {item["source"]: item["destination"] for item in self.manifest["blueprint_payloads"]}
        self.assertEqual(payloads["patches/agent-request-timeout-ui.patch"], "craft/editaja/agent-request-timeout-ui.patch")
        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertTrue(chain.rstrip().endswith('("agent-request-timeout-ui.patch", 1)]'))


if __name__ == "__main__":
    unittest.main()
