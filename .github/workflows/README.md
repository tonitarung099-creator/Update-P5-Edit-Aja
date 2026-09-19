# GitHub Actions

This repository intentionally keeps the workflow surface small.

| Workflow | Responsibility |
| --- | --- |
| `test-suite.yml` | Runs the complete Python unit/integration suite and CLI smoke checks for all P5 tools. |
| `validate-build.yml` | Validates the pinned build manifest, patch checksums, YAML, Python build helpers, and PowerShell syntax. |
| `build-windows.yml` | Orchestrates the reproducible Windows application build and package upload. Build logic lives in `scripts/windows/`. |

## Rule

Do not create one workflow per feature. Add feature tests under `tests/` and let
`test-suite.yml` discover them. Add a dedicated workflow only when a job needs
a different operating system, permissions model, secret, external service, or a
materially different runtime environment. Windows build deduplication is handled directly by the `concurrency` block in `build-windows.yml`.
