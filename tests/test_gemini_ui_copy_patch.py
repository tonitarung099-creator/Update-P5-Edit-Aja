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
        self.assertIn("Built-in AI Agent uses Google Gemini only", additions)
        self.assertIn("up to 100 Gemini API keys", additions)
        self.assertNotIn("OpenAI-compatible API", additions)

    def test_redundant_group_title_is_removed(self):
        self.assertIn("+    auto *agentGroup = new QGroupBox(this);", self.patch)
        additions = "\n".join(
            line[1:] for line in self.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        self.assertNotIn("AI Agent — Main Control", additions)

    def test_patch_is_after_gemini_pool_and_copied_to_craft(self):
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        self.assertEqual(names[-2:], ["gemini-only-key-pool", "gemini-ui-copy"])
        entry = self.manifest["apply_chain"][-1]
        self.assertEqual(entry["path"], "patches/gemini-ui-copy.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {item["source"]: item["destination"] for item in self.manifest["blueprint_payloads"]}
        self.assertEqual(
            payloads["patches/gemini-ui-copy.patch"],
            "craft/editaja/gemini-ui-copy.patch",
        )
        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertTrue(chain.rstrip().endswith('("gemini-ui-copy.patch", 1)]'))


if __name__ == "__main__":
    unittest.main()
