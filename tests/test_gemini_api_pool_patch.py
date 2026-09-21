import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "gemini-api-pool.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class GeminiApiPoolPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_ui_is_gemini_only_and_accepts_up_to_100_keys(self):
        for marker in (
            "Gemini Developer API · automatic key rotation",
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            "geminiApiKeyPool",
            "apiKeys.size() > 100",
            'startsWith(QStringLiteral("gemini-"), Qt::CaseInsensitive)',
            'QStringLiteral("gemini-3.8-flash")',
            'settings.remove(QStringLiteral("apiUrl"))',
        ):
            self.assertIn(marker, self.patch)

    def test_keys_are_session_only_and_not_logged(self):
        self.assertIn("Keys stay in memory for this app session", self.patch)
        self.assertNotIn('settings.setValue(QStringLiteral("apiKey")', self.patch)
        self.assertNotIn("trace(requestApiKey", self.patch)
        self.assertNotIn("trace(m_apiKey", self.patch)

    def test_quota_and_invalid_key_rotation_are_bounded(self):
        for marker in (
            "status == 429",
            "resource_exhausted",
            "Retry-After",
            "p5GeminiCooldowns",
            "p5GeminiInvalidKeys",
            "p5GeminiRetrySameRound",
            "Switching automatically to Gemini key",
            "No Gemini API key is ready right now",
        ):
            self.assertIn(marker, self.patch)

    def test_patch_is_last_and_copied_to_craft(self):
        entry = self.manifest["apply_chain"][-1]
        self.assertEqual(entry["name"], "gemini-api-pool")
        self.assertEqual(entry["path"], "patches/gemini-api-pool.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {item["source"]: item["destination"] for item in self.manifest["blueprint_payloads"]}
        self.assertEqual(
            payloads["patches/gemini-api-pool.patch"],
            "craft/editaja/gemini-api-pool.patch",
        )

        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertTrue(chain.rstrip().endswith('("gemini-api-pool.patch", 1)]'))

    def test_patch_avoids_crlf_headers(self):
        self.assertNotIn("aiassistantwidget.h", self.patch)
        self.assertNotIn("openaicompatibleagent.h", self.patch)


if __name__ == "__main__":
    unittest.main()
