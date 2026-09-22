import json
import unittest

from tests.build_contract import ROOT


PATCH = ROOT / "patches" / "full-editor-control-v3-track-state.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class FullEditorControlV3TrackStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_exact_track_state_tools_are_registered_and_dispatched(self):
        for name in ("kdenlive_get_track_state", "kdenlive_set_track_state"):
            self.assertGreaterEqual(self.patch.count(name), 2, name)

    def test_readback_reports_native_track_state(self):
        for marker in (
            "model->getTrackPosition(trackId)",
            "track->isAudioTrack()",
            "track->isLocked()",
            "track->isTimelineActive()",
            "track->isHidden()",
            "track->isMute()",
            "track->stackEnabled()",
        ):
            self.assertIn(marker, self.patch)

    def test_setter_uses_explicit_target_state_instead_of_blind_toggles(self):
        for marker in (
            "isTimelineActive() != desired",
            "stackEnabled() != desired",
            "isMute() != desired",
            "isHidden() != desired",
            "isLocked() != desired",
        ):
            self.assertIn(marker, self.patch)
        self.assertIn("controller->switchTrackActive(trackId)", self.patch)
        self.assertIn("controller->hideTrack(trackId, desired, false)", self.patch)
        self.assertIn("model->setTrackLockedState(trackId, desired)", self.patch)

    def test_track_type_specific_visibility_is_guarded(self):
        self.assertIn("hidden is only valid for video tracks; use muted for audio tracks", self.patch)
        self.assertIn("muted is only valid for audio tracks; use hidden for video tracks", self.patch)

    def test_mutations_use_native_editor_paths(self):
        for marker in (
            "model->setTrackName(trackId, desired)",
            "model->setTrackStackEnabled(trackId, desired)",
            "model->setTrackLockedState(trackId, desired)",
            "controller->hideTrack(trackId, desired, false)",
        ):
            self.assertIn(marker, self.patch)
        self.assertIn("At least one track state field is required", self.patch)
        self.assertIn('QStringLiteral("changed_fields")', self.patch)

    def test_patch_is_after_v2_and_copied_to_craft(self):
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        self.assertLess(names.index("full-editor-control-v2-guides"), names.index("full-editor-control-v3-track-state"))
        entry = next(entry for entry in self.manifest["apply_chain"] if entry["name"] == "full-editor-control-v3-track-state")
        self.assertEqual(entry["path"], "patches/full-editor-control-v3-track-state.patch")
        self.assertTrue(entry["check"])
        self.assertTrue(entry["ignore_space_change"])

        payloads = {item["source"]: item["destination"] for item in self.manifest["blueprint_payloads"]}
        self.assertEqual(
            payloads["patches/full-editor-control-v3-track-state.patch"],
            "craft/editaja/full-editor-control-v3-track-state.patch",
        )

        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        self.assertLess(
            chain.index('("full-editor-control-v2-guides.patch", 1)'),
            chain.index('("full-editor-control-v3-track-state.patch", 1)'),
        )


if __name__ == "__main__":
    unittest.main()
