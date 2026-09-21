import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "nonblocking-film-context-indexer.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class NonblockingFilmContextIndexerPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_indexer_startup_is_signal_driven(self):
        added = "\n".join(
            line[1:]
            for line in self.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        self.assertIn("QProcess::errorOccurred", added)
        self.assertIn("QProcess::FailedToStart", added)
        self.assertIn("m_filmContextIndexer->errorString()", added)
        self.assertIn("m_filmContextBuildButton->setEnabled(true)", added)
        self.assertIn("m_filmContextVisualButton->setEnabled(true)", added)
        self.assertNotIn("waitForStarted", added)
        self.assertNotIn("waitForFinished", added)
        self.assertNotIn("processEvents", added)

    def test_both_previous_startup_waits_are_removed(self):
        removed = "\n".join(
            line[1:]
            for line in self.patch.splitlines()
            if line.startswith("-") and not line.startswith("---")
        )
        self.assertEqual(removed.count("waitForStarted(3000)"), 2)

    def test_patch_precedes_native_async_analysis_and_is_copied_to_craft(self):
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        entry = self.manifest["apply_chain"][names.index("nonblocking-film-context-indexer")]
        self.assertEqual(entry["name"], "nonblocking-film-context-indexer")
        self.assertEqual(entry["path"], "patches/nonblocking-film-context-indexer.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {
            item["source"]: item["destination"]
            for item in self.manifest["blueprint_payloads"]
        }
        self.assertEqual(
            payloads["patches/nonblocking-film-context-indexer.patch"],
            "craft/editaja/nonblocking-film-context-indexer.patch",
        )

        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertIn('("nonblocking-film-context-indexer.patch", 1)', chain)
        if '("async-native-analysis-registry.patch", 1)' in chain:
            self.assertLess(
                chain.index('("nonblocking-film-context-indexer.patch", 1)'),
                chain.index('("async-native-analysis-registry.patch", 1)'),
            )


if __name__ == "__main__":
    unittest.main()
