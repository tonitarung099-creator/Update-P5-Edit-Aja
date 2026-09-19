# Tests

Tests are grouped by product responsibility rather than by GitHub workflow.

The single `.github/workflows/test-suite.yml` workflow runs independent
component groups in parallel so a failure is easy to locate without creating
dozens of workflow files.

Build-specific tests (`test_build*.py`) are owned by
`.github/workflows/validate-build.yml`.

## Adding a test

1. Put the test in `tests/` with a descriptive `test_*.py` name.
2. Add it to the appropriate component group in `test-suite.yml`.
3. If the test protects build configuration, use the `test_build*.py`
   convention so build validation discovers it.
4. Keep tests deterministic and offline whenever possible.
5. When fixing a bug, add a regression test in the owning subsystem if
   practical.

See `docs/QUALITY_GATES.md` for the full gate order.
