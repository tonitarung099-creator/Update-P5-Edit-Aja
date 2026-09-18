import base64
import bz2
import hashlib
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCH_FILE = ROOT / "patches" / "phase14-local-edit-preview-history.patch.bz2.b64"
EXPECTED_SHA256 = "864aa6d7aeee21a965df407c1be2b9da7dde744cc065eccb698d7e5fdca7c248"


class LocalEditPreviewHistoryPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = bz2.decompress(base64.b64decode(PATCH_FILE.read_text(encoding="ascii")))
        cls.patch = raw.decode("utf-8")
        cls.digest = hashlib.sha256(raw).hexdigest()

    def test_checksum(self):
        self.assertEqual(self.digest, EXPECTED_SHA256)

    def test_preview_and_apply_are_separate(self):
        self.assertIn("previewLocalEditCommand", self.patch)
        self.assertIn("handleLocalEditCommand(const QString &command, bool previewOnly)", self.patch)
        self.assertIn("return handleLocalEditCommand(command, true)", self.patch)
        self.assertIn("handleLocalEditCommand(command, false)", self.patch)
        self.assertIn("if (previewOnly)", self.patch)

    def test_creator_toolbar_enter_is_preview(self):
        self.assertIn("creatorLocalEditPreview", self.patch)
        self.assertIn('localEditPreview->setText(i18n("Preview"))', self.patch)
        self.assertIn('localEditRun->setText(i18n("Apply"))', self.patch)
        self.assertIn("QLineEdit::returnPressed, this, previewLocalEditCommand", self.patch)

    def test_preview_summarizes_real_work(self):
        self.assertIn("Dipahami: potong", self.patch)
        self.assertIn("Dipahami: hapus detected Scene", self.patch)
        self.assertIn("Dipahami: zoom smooth", self.patch)
        self.assertIn("affected_count", self.patch)
        self.assertIn("one_undo", self.patch)
        self.assertIn("lowest_end_scale_percent", self.patch)

    def test_history_is_session_visible_and_shared(self):
        self.assertIn("Local Edit History", self.patch)
        self.assertIn("appendLocalEditHistory", self.patch)
        self.assertIn("QDateTime::currentDateTime", self.patch)
        self.assertIn("localEditHistory", self.patch)
        self.assertIn("Clear", self.patch)

    def test_ai_mcp_preview_does_not_send_or_prepare(self):
        self.assertIn("if (!previewOnly)", self.patch)
        self.assertIn("nothing has been sent", self.patch)
        self.assertIn("prepareAgentPrompt(original)", self.patch)

    def test_build_chain_contains_phase14(self):
        blueprint = (ROOT / "craft" / "editaja" / "editaja.py").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "build-windows.yml").read_text(encoding="utf-8")
        self.assertIn('("phase14.patch", 1)', blueprint)
        self.assertIn("PHASE14_SHA256", workflow)
        self.assertIn("phase14-local-edit-preview-history.patch.bz2.b64", workflow)
        self.assertIn("craft/editaja/phase14.patch", workflow)
        self.assertIn("Local Edit History", workflow)
        self.assertIn("creatorLocalEditPreview", workflow)


if __name__ == "__main__":
    unittest.main()
