from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = ROOT / "scripts" / "windows" / "smoke-test-support.ps1"
FUNCTIONAL = ROOT / "scripts" / "windows" / "functional-smoke-package.ps1"


class BuildUiPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.support = SUPPORT.read_text(encoding="utf-8")
        cls.functional = FUNCTIONAL.read_text(encoding="utf-8")

    def test_native_helpers_support_geometry_and_graceful_close(self):
        for marker in (
            "MoveWindow(",
            "function Get-SmokeWindowBounds",
            "function Set-SmokeWindowBounds",
            "function Close-SmokeWindowGracefully",
            "0x0010",
            "WM_CLOSE",
            "FindBestTopLevelWindow",
            "EnumWindows(",
            "GetWindowTextLength",
            "largest_visible_titled_top_level_window",
        ):
            self.assertIn(marker, self.support)

    def test_functional_smoke_restarts_before_editing(self):
        persistence = self.functional.index("$stage = 'window_persistence'")
        project_load = self.functional.index("$stage = 'project_load'")
        timeline_edit = self.functional.index("$stage = 'timeline_split'")
        self.assertLess(persistence, project_load)
        self.assertLess(project_load, timeline_edit)
        self.assertIn("Close-SmokeWindowGracefully -Process $appProcess", self.functional)
        self.assertIn("Start-Process -FilePath $app", self.functional)
        self.assertIn("window-persistence.json", self.functional)
        restart_bridge = self.functional.index("$discovery = Wait-AgentBridge -DiscoveryFile $discoveryPath", persistence)
        reopened_project = self.functional.index("$project = Wait-ProjectLoaded", restart_bridge)
        after_bounds = self.functional.index("$boundsAfterRestart = Get-SmokeWindowBounds", reopened_project)
        self.assertLess(restart_bridge, reopened_project)
        self.assertLess(reopened_project, after_bounds)

    def test_persistence_is_measured_with_bounded_tolerance(self):
        for marker in (
            "$sizeTolerance = 48",
            "$positionTolerance = 96",
            "delta = [ordered]@{",
            "$windowPersistence.pass",
            "window-before-restart.png",
            "window-after-restart.png",
        ):
            self.assertIn(marker, self.functional)


if __name__ == "__main__":
    unittest.main()
