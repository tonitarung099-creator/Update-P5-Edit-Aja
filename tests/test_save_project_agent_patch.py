import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "save-project-agent.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class NativeSaveProjectPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_new_target_does_not_use_overwrite_permission_as_existing_file_flag(self):
        self.assertIn("const bool outputExists = output.exists();", self.patch)
        self.assertIn("if (outputExists && !overwrite)", self.patch)
        self.assertIn(
            "saveFileAs(output.absoluteFilePath(), outputExists && overwrite, saveCopy)",
            self.patch,
        )
        added = "\n".join(
            line[1:] for line in self.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        self.assertNotIn(
            "saveFileAs(output.absoluteFilePath(), overwrite, saveCopy)",
            added,
        )

    def test_save_fix_is_last_source_patch(self):
        entry = self.manifest["apply_chain"][-1]
        self.assertEqual(entry["name"], "save-project-agent")
        self.assertEqual(entry["path"], "patches/save-project-agent.patch")
        self.assertTrue(entry["check"])

    def test_save_fix_is_copied_into_blueprint_and_applied_last(self):
        payloads = {
            item["source"]: item["destination"]
            for item in self.manifest["blueprint_payloads"]
        }
        self.assertEqual(
            payloads["patches/save-project-agent.patch"],
            "craft/editaja/save-project-agent.patch",
        )
        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertTrue(chain.rstrip().endswith('("save-project-agent.patch", 1)]'))


if __name__ == "__main__":
    unittest.main()
