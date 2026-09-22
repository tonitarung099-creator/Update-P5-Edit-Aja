from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FUNCTIONAL = ROOT / "scripts" / "windows" / "functional-smoke-package.ps1"


class BuildRenderRoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.functional = FUNCTIONAL.read_text(encoding="utf-8")

    def test_saved_copy_is_reopened_in_a_fresh_process_before_render(self):
        save_copy = self.functional.index("$stage = 'save_copy'")
        fresh_reopen = self.functional.index("$stage = 'fresh_reopen_saved_copy'")
        render_export = self.functional.index("$stage = 'render_export'")
        render_decode = self.functional.index("$stage = 'render_decode'")

        self.assertLess(save_copy, fresh_reopen)
        self.assertLess(fresh_reopen, render_export)
        self.assertLess(render_export, render_decode)
        self.assertIn("Close-SmokeWindowGracefully -Process $appProcess", self.functional)
        self.assertIn("Wait-ProjectLoaded -BaseUrl $baseUrl -Token $token -ExpectedPath $savedProjectPath", self.functional)

    def test_reopen_verifies_native_edits_survived(self):
        self.assertIn("$reopenedClipCount -ne $clipCountAfter", self.functional)
        self.assertIn("$reopenedMatchingSubtitle.Count -ne 1", self.functional)
        self.assertIn("Fresh-process reopen PASS", self.functional)

    def test_render_is_native_and_bounded(self):
        self.assertIn("-Name 'kdenlive_render'", self.functional)
        self.assertIn("preset = 'MP4-H264/AAC'", self.functional)
        self.assertIn("start_seconds = 0.0", self.functional)
        self.assertIn("end_seconds = 2.5", self.functional)
        self.assertIn("embed_subtitles = $true", self.functional)
        self.assertIn("Wait-RenderFinished", self.functional)
        self.assertIn("TimeoutSeconds = 240", self.functional)
        for terminal in ("finished", "failed", "aborted"):
            self.assertIn(terminal, self.functional)

    def test_decode_uses_binary_from_portable_tree(self):
        self.assertIn("Test-PackagedRenderedMedia", self.functional)
        self.assertIn("-LiteralPath $PortableRoot -Recurse -File -Filter 'ffmpeg.exe'", self.functional)
        self.assertIn("Portable package does not contain ffmpeg.exe", self.functional)
        self.assertIn("'-f', 'null'", self.functional)
        self.assertIn("'NUL'", self.functional)
        self.assertNotIn("Get-Command ffmpeg", self.functional)

    def test_render_evidence_is_persisted(self):
        self.assertIn("render-evidence.json", self.functional)
        self.assertIn("render_request = $renderRequest", self.functional)
        self.assertIn("render_status = $renderFinished.status", self.functional)
        self.assertIn("decode = $decodeEvidence", self.functional)
        self.assertIn("project save-copy, fresh-process reopen, render/export, and packaged-media decode", self.functional)


if __name__ == "__main__":
    unittest.main()
