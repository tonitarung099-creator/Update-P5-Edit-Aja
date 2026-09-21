import json
import unittest

from tests.build_contract import ROOT


REGISTRY_PATCH = ROOT / "patches" / "async-native-analysis-registry.patch"
CLEANUP_PATCH = ROOT / "patches" / "async-native-analysis-cleanup.patch"
SILENCE_PATCH = ROOT / "patches" / "async-native-silence.patch"
TRANSCRIPTION_PATCH = ROOT / "patches" / "async-native-transcription.patch"
CLIENTS_PATCH = ROOT / "patches" / "async-agent-clients.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class AsyncNativeAnalysisPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = REGISTRY_PATCH.read_text(encoding="utf-8")
        cls.cleanup = CLEANUP_PATCH.read_text(encoding="utf-8")
        cls.silence = SILENCE_PATCH.read_text(encoding="utf-8")
        cls.transcription = TRANSCRIPTION_PATCH.read_text(encoding="utf-8")
        cls.clients = CLIENTS_PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_slow_native_tools_use_async_registry(self):
        for marker in (
            "NativeAsyncToolExecutor",
            "registerAsyncNativeTool",
            "kdenlive_detect_silence",
            "kdenlive_transcribe_media",
        ):
            self.assertIn(marker, self.registry)
        self.assertIn("AI Edit JSON cannot run asynchronous analysis tool", self.registry)
        self.assertIn("Asynchronous analysis tools must be called directly", self.registry)

    def test_old_blocking_waits_are_removed(self):
        removed = "\n".join(
            line[1:]
            for line in self.cleanup.splitlines()
            if line.startswith("-") and not line.startswith("---")
        )
        self.assertEqual(removed.count("waitForStarted("), 2)
        self.assertEqual(removed.count("waitForFinished("), 3)
        self.assertEqual(removed.count("waitForReadyRead("), 1)
        self.assertIn("QElapsedTimer", removed)

    def test_new_process_paths_are_signal_and_timer_driven(self):
        added = "\n".join(
            line[1:]
            for patch in (self.cleanup, self.silence, self.transcription)
            for line in patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        for marker in (
            "stopAgentOwnedProcess",
            "QProcess::started",
            "QProcess::errorOccurred",
            "QTimer::timeout",
            "editAjaAsyncCancelled",
            "editAjaAsyncCompleted",
            "FFmpeg silence detection timed out",
            "Whisper transcription timed out",
        ):
            self.assertIn(marker, added)
        self.assertNotIn("waitForStarted", added)
        self.assertNotIn("waitForFinished", added)
        self.assertNotIn("waitForReadyRead", added)
        self.assertNotIn("processEvents", added)

    def test_transcription_snapshots_timeline_mapping_before_process(self):
        self.assertIn("sourceIn = inOut.first", self.transcription)
        self.assertIn("sourceOut = inOut.second", self.transcription)
        self.assertIn("clipSpeed = qAbs(model->getClipSpeed(clipId))", self.transcription)
        finished_section = self.transcription.split("QProcess::finished", 1)[1]
        self.assertNotIn("model->", finished_section)

    def test_bundled_clients_await_async_jobs(self):
        for marker in (
            'jobs/status',
            '/jobs/{job_id}',
            'time.monotonic()',
            'time.sleep(0.1)',
        ):
            self.assertIn(marker, self.clients)
        self.assertIn('jobs/cancel', self.clients)
        self.assertIn('/jobs/{job_id}/cancel', self.clients)

    def test_patch_order_and_craft_payloads_match(self):
        expected = [
            "async-native-analysis-registry",
            "async-native-analysis-cleanup",
            "async-native-silence",
            "async-native-transcription",
            "async-agent-clients",
        ]
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        self.assertEqual(names[-5:], expected)
        self.assertLess(names.index("nonblocking-film-context-indexer"), names.index(expected[0]))

        payloads = {
            item["source"]: item["destination"]
            for item in self.manifest["blueprint_payloads"]
        }
        patch_names = [
            "async-native-analysis-registry.patch",
            "async-native-analysis-cleanup.patch",
            "async-native-silence.patch",
            "async-native-transcription.patch",
            "async-agent-clients.patch",
        ]
        for patch_name in patch_names:
            source = f"patches/{patch_name}"
            self.assertEqual(payloads[source], f"craft/editaja/{patch_name}")

        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        positions = [chain.index(f'("{patch_name}", 1)') for patch_name in patch_names]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(
            chain.index('("nonblocking-film-context-indexer.patch", 1)'),
            positions[0],
        )


if __name__ == "__main__":
    unittest.main()
