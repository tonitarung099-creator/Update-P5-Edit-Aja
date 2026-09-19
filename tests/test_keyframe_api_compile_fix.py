import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "keyframe-api-compile-fix.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class KeyframeApiCompileFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_uses_public_keyframe_model_list_api(self):
        self.assertIn("keyframes->removeAllKeyframes()", self.patch)
        self.assertIn("keyframes->addKeyframe(position, type)", self.patch)
        self.assertIn("keyframes->updateKeyframe(position, QVariant(value)", self.patch)

    def test_does_not_call_protected_keyframe_model_mutators(self):
        added = "\n".join(
            line[1:] for line in self.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        self.assertNotIn("rectModel->removeAllKeyframes()", added)
        self.assertNotIn("rectModel->addKeyframe(", added)

    def test_fix_is_last_source_patch(self):
        self.assertEqual(
            self.manifest["apply_chain"][-1]["name"],
            "keyframe-api-compile-fix",
        )
        self.assertEqual(
            self.manifest["apply_chain"][-1]["path"],
            "patches/keyframe-api-compile-fix.patch",
        )
        self.assertTrue(self.manifest["apply_chain"][-1]["check"])
        self.assertTrue(self.manifest["apply_chain"][-1]["ignore_space_change"])

    def test_craft_blueprint_applies_same_fix_last(self):
        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertIn('("keyframe-api-compile-fix.patch", 1)', chain)
        self.assertTrue(chain.rstrip().endswith('("keyframe-api-compile-fix.patch", 1)]'))


if __name__ == "__main__":
    unittest.main()
