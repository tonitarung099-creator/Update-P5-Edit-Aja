import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "full-editor-control-v1.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class FullEditorControlV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_action_catalog_exposes_runtime_state(self):
        self.assertIn('QStringLiteral("visible"), action->isVisible()', self.patch)
        self.assertIn('QStringLiteral("checked"), action->isChecked()', self.patch)

    def test_exact_action_state_tool_exists(self):
        self.assertIn('QStringLiteral("kdenlive_get_action_state")', self.patch)
        self.assertIn("Unknown editor action", self.patch)

    def test_checked_schema_does_not_depend_on_late_boolean_property(self):
        self.assertNotIn("booleanProperty", self.patch)
        self.assertIn(
            'QStringLiteral("checked"), QJsonObject{{QStringLiteral("type"), QStringLiteral("boolean")}}',
            self.patch,
        )

    def test_checked_action_setter_is_not_blind_toggle(self):
        self.assertIn('QStringLiteral("kdenlive_set_action_checked")', self.patch)
        self.assertIn("beforeChecked == desiredChecked", self.patch)
        self.assertIn('QStringLiteral("target_reached")', self.patch)
        self.assertIn("Editor action is not checkable", self.patch)
        self.assertIn("Editor action is currently disabled", self.patch)

    def test_patch_is_in_manifest_and_blueprint(self):
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        self.assertIn("full-editor-control-v1", names)
        entry = next(entry for entry in self.manifest["apply_chain"] if entry["name"] == "full-editor-control-v1")
        self.assertEqual(entry["path"], "patches/full-editor-control-v1.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {item["source"]: item["destination"] for item in self.manifest["blueprint_payloads"]}
        self.assertEqual(
            payloads["patches/full-editor-control-v1.patch"],
            "craft/editaja/full-editor-control-v1.patch",
        )
        self.assertIn('("full-editor-control-v1.patch", 1)', self.blueprint)


if __name__ == "__main__":
    unittest.main()
