# GitHub Actions

This repository intentionally keeps the workflow surface small.

| Workflow | Responsibility |
| --- | --- |
| `test-suite.yml` | Runs static validation, parallel component test groups, and contract/example smoke checks. |
| `validate-build.yml` | Validates the pinned build manifest, patch checksums, YAML, Python build helpers, and PowerShell syntax. |
| `build-windows.yml` | Orchestrates the reproducible Windows application build and package upload. Build logic lives in `scripts/windows/`. |

## Quality-gate model

`test-suite.yml` keeps one workflow but exposes failures by subsystem:

- AI Control
- Media Editorial
- Audio Speech
- Captions
- Visual Segmentation
- Documentary
- Static / Repository
- Contracts / Examples

This makes independent checks run in parallel while keeping the Actions page
small and readable.

Do not create one workflow per feature. Add feature tests under `tests/` and
place them in the appropriate matrix group. Add a dedicated workflow only when
a job genuinely needs a different operating system, permissions model, secret,
external service, or materially different runtime environment.

Windows build deduplication is handled by the `concurrency` block in
`build-windows.yml`.
