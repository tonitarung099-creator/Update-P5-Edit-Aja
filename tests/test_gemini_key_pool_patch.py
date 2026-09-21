import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "gemini-only-key-pool.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class GeminiKeyPoolPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_ui_is_gemini_only_and_multiline(self):
        additions = "\n".join(
            line[1:] for line in self.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        self.assertIn("Provider: Google Gemini only", additions)
        self.assertIn("geminiApiKeyPool", additions)
        self.assertIn("one key per line, maximum 100", additions)
        self.assertIn("gemini-2.5-flash", additions)
        self.assertNotIn('apiForm->addRow(i18n("Chat API URL")', additions)

    def test_primary_agent_copy_is_gemini_only(self):
        additions = "\n".join(
            line[1:] for line in self.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        self.assertIn("Built-in AI Agent uses Google Gemini only", additions)
        self.assertIn("up to 100 Gemini API keys", additions)
        self.assertNotIn("Connect an OpenAI-compatible API inside the editor", additions)

    def test_pool_is_bounded_and_rotates_on_quota(self):
        for marker in (
            "keys.size() >= 100",
            "httpStatus == 429",
            "resource_exhausted",
            'rawHeader("Retry-After")',
            "attemptedThisTurn",
            "cooldownUntilMs",
            "retryingApiKey",
            "switching automatically",
        ):
            self.assertIn(marker, self.patch)

    def test_invalid_keys_are_disabled_without_exposing_secrets(self):
        self.assertIn("disabledIndices", self.patch)
        self.assertIn("API_KEY_INVALID".lower(), self.patch.lower())
        self.assertNotIn("requestApiKey)", self.patch)
        self.assertNotIn("Q_EMIT trace(requestApiKey", self.patch)

    def test_gemini_patch_is_last_and_copied_to_craft(self):
        entry = self.manifest["apply_chain"][-1]
        self.assertEqual(entry["name"], "gemini-only-key-pool")
        self.assertEqual(entry["path"], "patches/gemini-only-key-pool.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {item["source"]: item["destination"] for item in self.manifest["blueprint_payloads"]}
        self.assertEqual(
            payloads["patches/gemini-only-key-pool.patch"],
            "craft/editaja/gemini-only-key-pool.patch",
        )
        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertTrue(chain.rstrip().endswith('("gemini-only-key-pool.patch", 1)]'))


if __name__ == "__main__":
    unittest.main()
