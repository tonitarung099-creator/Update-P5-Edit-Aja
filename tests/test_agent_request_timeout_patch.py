import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "agent-request-timeout.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class AgentRequestTimeoutPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_timeout_is_bounded_and_programmatically_configurable(self):
        for marker in (
            "setRequestTimeoutMs",
            "m_requestTimeoutMs{600000}",
            "m_requestTimer->setSingleShot(true)",
            "m_requestTimer->start(m_requestTimeoutMs)",
            "handleRequestTimeout",
        ):
            self.assertIn(marker, self.patch)

    def test_timeout_detaches_before_abort_and_does_not_retry(self):
        timeout_section = self.patch.split("void OpenAiCompatibleAgent::handleRequestTimeout()", 1)[1]
        timeout_section = timeout_section.split("void OpenAiCompatibleAgent::fail", 1)[0]
        self.assertLess(timeout_section.index("m_reply.clear();"), timeout_section.index("reply->abort();"))
        self.assertIn("fail(QStringLiteral", timeout_section)
        self.assertNotIn("sendTurn();", timeout_section)
        self.assertNotIn("m_network->post", timeout_section)

    def test_cancel_and_failure_stop_request_timer(self):
        self.assertGreaterEqual(self.patch.count("m_requestTimer->stop();"), 3)
        self.assertIn("API request timed out after %1 seconds", self.patch)

    def test_patch_precedes_bounded_output_and_is_copied_to_craft(self):
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        timeout_index = names.index("agent-request-timeout")
        entry = self.manifest["apply_chain"][timeout_index]
        self.assertEqual(entry["name"], "agent-request-timeout")
        self.assertEqual(entry["path"], "patches/agent-request-timeout.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {
            item["source"]: item["destination"]
            for item in self.manifest["blueprint_payloads"]
        }
        self.assertEqual(
            payloads["patches/agent-request-timeout.patch"],
            "craft/editaja/agent-request-timeout.patch",
        )

        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertIn('("agent-request-timeout.patch", 1)', chain)
        if '("bounded-ai-output.patch", 1)' in chain:
            self.assertLess(
                chain.index('("agent-request-timeout.patch", 1)'),
                chain.index('("bounded-ai-output.patch", 1)'),
            )


if __name__ == "__main__":
    unittest.main()
