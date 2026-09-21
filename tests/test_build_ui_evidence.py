from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WindowsUiEvidenceContractTests(unittest.TestCase):
    def test_functional_smoke_captures_real_window_evidence(self):
        support = (ROOT / "scripts/windows/smoke-test-support.ps1").read_text(encoding="utf-8")
        functional = (ROOT / "scripts/windows/functional-smoke-package.ps1").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/build-windows.yml").read_text(encoding="utf-8")

        for marker in (
            "function Save-SmokeWindowScreenshot",
            "PrintWindow",
            "CopyFromScreen",
            "function Measure-SmokeWindowHeartbeat",
            "SendMessageTimeout",
            "slow_threshold_ms",
        ):
            self.assertIn(marker, support)

        self.assertIn("Save-SmokeWindowScreenshot -Process $appProcess", functional)
        self.assertIn("Measure-SmokeWindowHeartbeat -Process $appProcess", functional)
        self.assertIn("artifacts/smoke/functional", functional)
        self.assertIn("ui-evidence.json", functional)
        self.assertIn("ai-agent-window.png", functional)
        self.assertIn("Upload portable-app smoke diagnostics", workflow)
        self.assertIn("artifacts/smoke/**", workflow)


if __name__ == "__main__":
    unittest.main()
