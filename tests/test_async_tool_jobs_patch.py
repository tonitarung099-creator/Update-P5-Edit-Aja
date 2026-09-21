import json
import unittest

from tests.build_contract import ROOT


REGISTRY_PATCH = ROOT / "patches" / "async-tool-registry.patch"
IPC_PATCH = ROOT / "patches" / "async-tool-ipc.patch"
AGENT_PATCH = ROOT / "patches" / "async-agent-tool-wait.patch"
PROCESS_PATCH = ROOT / "patches" / "async-film-context-process.patch"
REGISTRATION_PATCH = ROOT / "patches" / "async-film-context-registration.patch"
MANIFEST = ROOT / "build" / "build-manifest.json"
BLUEPRINT = ROOT / "craft" / "editaja" / "editaja.py"


class AsyncToolJobsPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = REGISTRY_PATCH.read_text(encoding="utf-8")
        cls.ipc = IPC_PATCH.read_text(encoding="utf-8")
        cls.agent = AGENT_PATCH.read_text(encoding="utf-8")
        cls.process = PROCESS_PATCH.read_text(encoding="utf-8")
        cls.registration = REGISTRATION_PATCH.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.blueprint = BLUEPRINT.read_text(encoding="utf-8")

    def test_registry_has_bounded_async_job_contract(self):
        for marker in (
            "registerAsyncTool",
            "invokeOrStart",
            "jobStatus",
            "cancelJob",
            "jobFinished",
            "maxRetainedJobs = 128",
        ):
            self.assertIn(marker, self.registry)

    def test_ipc_exposes_same_job_contract(self):
        for marker in (
            'jobs/status',
            'jobs/cancel',
            '/v1/jobs/',
            'invokeOrStart',
        ):
            self.assertIn(marker, self.ipc)

    def test_agent_waits_and_cancels_async_jobs(self):
        for marker in (
            "m_toolJobId",
            "processNextToolCall",
            "jobFinished",
            "cancelJob(toolJobId)",
        ):
            self.assertIn(marker, self.agent)

    def test_film_context_process_path_is_event_driven(self):
        added = "\n".join(
            line[1:]
            for line in self.process.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        for marker in (
            "startFilmContextTool",
            "QTimer",
            "QProcess::started",
            "QProcess::errorOccurred",
            "taskkill",
            "stopOwnedProcessTree",
        ):
            self.assertIn(marker, added)
        self.assertNotIn("waitForFinished", added)
        self.assertNotIn("waitForStarted", added)
        self.assertNotIn("processEvents", added)

    def test_film_context_tools_use_async_registry(self):
        self.assertGreaterEqual(self.registration.count("registerAsyncTool"), 5)
        for name in (
            "movie_context_status",
            "movie_search",
            "movie_get_scene",
            "movie_get_context",
            "movie_get_keyframes",
        ):
            self.assertIn(name, self.registration)

    def test_patch_order_and_craft_payloads_match(self):
        expected = [
            "async-tool-registry",
            "async-tool-ipc",
            "async-agent-tool-wait",
            "async-film-context-process",
            "async-film-context-registration",
        ]
        names = [entry["name"] for entry in self.manifest["apply_chain"]]
        positions = [names.index(name) for name in expected]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(names.index("ai-agent-request-lifecycle"), positions[0])
        if "nonblocking-film-context-indexer" in names:
            self.assertLess(positions[-1], names.index("nonblocking-film-context-indexer"))

        payloads = {
            item["source"]: item["destination"]
            for item in self.manifest["blueprint_payloads"]
        }
        patch_names = [
            "async-tool-registry.patch",
            "async-tool-ipc.patch",
            "async-agent-tool-wait.patch",
            "async-film-context-process.patch",
            "async-film-context-registration.patch",
        ]
        for patch_name in patch_names:
            source = f"patches/{patch_name}"
            self.assertEqual(payloads[source], f"craft/editaja/{patch_name}")

        chain = self.blueprint.split('self.patchToApply["editaja"] = ', 1)[1].split("\n", 1)[0]
        positions = [chain.index(f'("{patch_name}", 1)') for patch_name in patch_names]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(
            chain.index('("ai-agent-request-lifecycle.patch", 1)'),
            positions[0],
        )


if __name__ == "__main__":
    unittest.main()
