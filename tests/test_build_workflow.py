"""Static queue/scheduling contracts; GitHub execution is verified separately."""

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class WindowsBuildSchedulingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.safe_load(
            (ROOT / ".github/workflows/build-windows.yml").read_text(encoding="utf-8")
        )
        cls.windows = cls.workflow["jobs"]["windows"]

    def test_unrelated_quality_runs_do_not_enter_windows_workflow(self):
        # PyYAML uses YAML 1.1, where unquoted `on` is a boolean key.
        triggers = self.workflow.get("on", self.workflow.get(True))
        trigger = triggers["workflow_run"]
        self.assertEqual(trigger["workflows"], ["P5 Quality Gates"])
        self.assertEqual(trigger["types"], ["completed"])
        self.assertEqual(trigger["branches"], ["main"])

    def test_ineligible_jobs_cannot_replace_a_queued_build(self):
        self.assertNotIn("concurrency", self.workflow)
        self.assertIn("concurrency", self.windows)
        condition = " ".join(self.windows["if"].split())
        self.assertEqual(
            condition,
            "github.event.workflow_run.conclusion == 'success' && "
            "github.event.workflow_run.head_branch == 'main'",
        )

    def test_new_builds_preserve_the_active_windows_job(self):
        queue = self.windows["concurrency"]
        self.assertEqual(queue["group"], "update-p5-edit-aja-windows")
        self.assertIs(queue["cancel-in-progress"], False)

    def test_build_uses_the_commit_that_passed_quality_gates(self):
        checkout = self.windows["steps"][0]
        self.assertTrue(checkout["uses"].startswith("actions/checkout@"))
        self.assertEqual(
            checkout["with"]["ref"], "${{ github.event.workflow_run.head_sha }}"
        )


if __name__ == "__main__":
    unittest.main()
