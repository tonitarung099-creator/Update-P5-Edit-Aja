from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FUNCTIONAL = ROOT / "scripts" / "windows" / "functional-smoke-package.ps1"


class BuildRenderRoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.functional = FUNCTIONAL.read_text(encoding="utf-8")

    def test_fresh_reopen_does_not_trigger_original_project_save_prompt(self):
        start = self.functional.index("$stage = 'fresh_reopen_saved_copy'")
        end = self.functional.index("$stage = 'render_export'")
        fresh_reopen = self.functional[start:end]
        self.assertIn("Stop-SmokeProcessTree -Process $appProcess", fresh_reopen)
        self.assertIn("$appProcess.HasExited", fresh_reopen)
        self.assertNotIn("Close-SmokeWindowGracefully -Process $appProcess", fresh_reopen)
        self.assertIn("save_copy intentionally leaves the original project marked modified", fresh_reopen)

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

    def test_empty_decode_stderr_is_normalized_before_trim(self):
        self.assertIn("[string](Get-Content $decodeStderr -Raw)", self.functional)
        self.assertIn("if ($null -eq $stderr)", self.functional)
        self.assertIn("$stderr = ''", self.functional)
        self.assertIn("decode_stderr = $stderr.Trim()", self.functional)

    def test_full_editor_action_state_is_exercised_and_restored(self):
        self.assertIn("'kdenlive_get_action_state'", self.functional)
        self.assertIn("'kdenlive_set_action_checked'", self.functional)
        self.assertIn("$stage = 'full_editor_action_state'", self.functional)
        self.assertIn("$testActionName = 'audiomixer_button'", self.functional)
        self.assertIn("$targetChecked = -not $originalChecked", self.functional)
        self.assertIn("Wait-ActionCheckedState", self.functional)
        self.assertIn("-ExpectedChecked $targetChecked", self.functional)
        self.assertIn("-ExpectedChecked $originalChecked", self.functional)
        self.assertIn("full-editor-action-state.json", self.functional)
        self.assertIn("Full Editor Control action-state PASS", self.functional)

    def test_render_evidence_is_persisted(self):
        self.assertIn("render-evidence.json", self.functional)
        self.assertIn("render_request = $renderRequest", self.functional)
        self.assertIn("render_status = $renderFinished.status", self.functional)
        self.assertIn("decode = $decodeEvidence", self.functional)
        self.assertIn("project save-copy, fresh-process reopen, render/export, and packaged-media decode", self.functional)


if __name__ == "__main__":
    unittest.main()
