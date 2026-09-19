"""Run the real preflight CLI against the manifest-pinned Craft checkout.

P5_CRAFT_TEST_SOURCE must name a local checkout of that exact revision. The
fixture has a source-only blueprint, so no toolchain download/build is needed.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CraftPreflightIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.environ["P5_CRAFT_TEST_SOURCE"]).resolve()
        expected = json.loads((ROOT / "build/build-manifest.json").read_text())["craft"]["revision"]
        actual = subprocess.check_output(
            ["git", "-C", str(cls.source), "rev-parse", "HEAD"], text=True
        ).strip()
        if actual != expected:
            raise RuntimeError(f"Craft fixture revision mismatch: {actual} != {expected}")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "installation with spaces"
        shutil.copytree(
            self.source, self.root / "craft",
            ignore=shutil.ignore_patterns(".git", "__pycache__"),
        )
        (self.root / "etc").mkdir()
        abi = "windows-gcc-x86_64" if os.name == "nt" else "linux-gcc-x86_64"
        (self.root / "etc/CraftSettings.ini").write_text(
            f"[Version]\nConfigVersion=6\n[General]\nABI={abi}\n"
            "[Compile]\nBuildType=RelWithDebInfo\n", encoding="utf-8",
        )
        blueprint = self.root / "etc/blueprints/locations/fixture/probe"
        blueprint.mkdir(parents=True)
        (blueprint.parent / "info.ini").write_text("[General]\n", encoding="utf-8")
        (blueprint / "probe.py").write_text(
            "import info\n"
            "from Package.SourceOnlyPackageBase import SourceOnlyPackageBase\n"
            "class subinfo(info.infoclass):\n"
            "    def setTargets(self):\n"
            "        self.targets['1.0'] = ''\n"
            "        self.defaultTarget = '1.0'\n"
            "    def setDependencies(self):\n"
            "        pass\n"
            "class Package(SourceOnlyPackageBase):\n"
            "    pass\n", encoding="utf-8",
        )
        self.env = os.environ.copy()
        for key in ("craftRoot", "CRAFT_TEST", "CRAFT_TEST_ABI", "CRAFT_FORCE_RESET"):
            self.env.pop(key, None)
        # Match invocation after Enter-CraftEnvironment has already run.
        self.env["KDEROOT"] = str(self.root)
        self.env["CRAFT_ROOT"] = str(self.root)

    def run_helper(self, package="probe"):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/prepare_package_images.py"),
             "--craft-root", str(self.root), "--package", package],
            cwd=ROOT, env=self.env, text=True, capture_output=True, timeout=30,
        )

    def test_external_script_locates_real_craft_configuration(self):
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Packaging image preparation complete", result.stdout)
        self.assertNotIn("Could not find config", result.stderr)

    def test_explicit_installation_overrides_stale_craft_locator(self):
        self.env["craftRoot"] = str(self.root / "wrong-checkout")
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_configuration_fails_before_craft_initialization(self):
        (self.root / "etc/CraftSettings.ini").unlink()
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Craft settings not found", result.stderr)
        self.assertNotIn("Your configuration is outdated", result.stderr)


if __name__ == "__main__":
    unittest.main()
