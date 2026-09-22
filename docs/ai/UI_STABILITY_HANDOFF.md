# P5 UI stability audit and AI handoff

Audit date: 2026-09-21 UTC. User request: inspect UI errors/responsiveness, fix
proven problems, and preserve a plan another AI can execute without this chat.
This is the continuation entry point; read AGENTS.md and AI_WORKING_RULES.md first.
Do not describe this audit as a complete interactive Windows UI test.

## Verified baseline (refresh before changing anything)

- Repository: `tonitarung099-creator/Update-P5-Edit-Aja`.
- Current main after Full Editor Control v1: `490785b9860ad3786924e744727777b259e07114`.
- Main Quality Gates #146 (`35694254737`): PASS, including Source Reconstruction and Qt lifecycle compile/test.
- Windows Build #90 (`35689293215`, source `654cc26c23edaf258a8fd2821038381b6348183e`): PASS end to end through portable startup and functional smoke.
- Build #90 proved the corrected non-splash main-window selection and geometry persistence: before/after restart were both 1178x756 at 48,48 with zero deltas, title `input / HD 1080p 25 fps - Update P5 Edit Aja`.
- Build #90 also passed packaged AI Agent panel opening, screenshot capture, idle heartbeat, timeline split, subtitle add/readback and project save-copy.
- PR #60 Gemini-only UI copy cleanup is merged at `13986e68f01dd97094699c11fa8bd404aa400964`; main Quality Gates #144 PASS. Windows Build #91 for that exact UI is currently in progress.
- Full Editor Control v1 PR #63 is merged; Quality Gates #146 PASS. Windows Build #92 is queued behind #91.
- PR #64 extends the packaged functional smoke to fresh-process reopen, render/export and packaged FFmpeg decode. Its Quality Gates #147 PASS, but the new runtime smoke is NOT TESTED until a post-merge Windows build runs it.
- Other chats can modify this repo: refresh main, PRs and run lineage immediately before pushing/merging.

## Scope and limitations

Inspected reconstructed pinned C++ for AiAssistantWidget, OpenAiCompatibleAgent,
AgentToolRegistry, AgentIpcServer, MainWindow creator layout/native process calls,
patch chain, UI tests and actual #75 Windows job log. All current patches applied
locally without error. This Linux workspace has no running packaged Windows UI;
no screenshot, manual interaction, frame rate, or memory measurement has been
claimed. Static findings below distinguish code evidence from runtime hypotheses.
Do not replace the real UI with a mockup and report it as verification.

## Findings and implementation order

| ID | Priority / state | Evidence and impact | Owning files / next action | Acceptance evidence |
| --- | --- | --- | --- | --- |
| UI-01 | P1 / merged; packaged baseline PASS | `setBusy` disables Run but leaves prompt enabled; Return calls `runAgent`, clears output and runs checkpoint before backend rejects duplicate. Backend rejection also emits busy=false while original request is live. | `aiassistantwidget.cpp` runAgent/setBusy; `openaicompatibleagent.cpp` run. Guard before side effects, disable prompt while busy, reject duplicate without changing active busy state. | Delayed local API fixture: duplicate start produces one HTTP request, no false idle event; UI Return while busy does not clear trace or create a second checkpoint. |
| UI-02 | P1 / merged; packaged baseline PASS | Cancel calls abort before detaching current reply; finished callback processes even stale replies. Cancellation can emit API failure and old replies can alter later state. | `openaicompatibleagent.cpp` cancel/sendTurn. Detach first, ignore completions that no longer own active reply, preserve deferred deletion. | Qt component test cancel, cancel twice, immediately start new request: no cancellation API error or old completion; new request finishes and busy transitions correctly. |
| UI-03 | P0 / merged; packaged baseline PASS | The synchronous Film Context tool path is replaced by bounded async jobs. Native timeline tools remain synchronous on the GUI thread; process-backed Film Context uses signal/timer-driven `QProcess`, shared job IDs, status/cancel for REST/MCP, and Agent continuation without a nested event loop. | `agenttoolregistry.*`, `agentipcserver.cpp`, `openaicompatibleagent.*`, `aiassistantwidget.*`; patches `async-*`. Qt regression uses a delayed local async fixture and cancel/restart path. | Patch-chain application PASS locally. PR gates must compile the reconstructed production registry/agent and prove heartbeat/cancel behavior. Exact-source packaged Windows behavior remains NOT TESTED until the post-merge build. |
| UI-04 | P1 / remainder implemented in current branch; verification pending | Film Context index startup is already merged. This branch converts `kdenlive_detect_silence` and `kdenlive_transcribe_media` to shared async jobs: media/timeline metadata is snapshotted on the GUI thread, external FFmpeg/Whisper runs signal/timer-driven, and completion uses only captured values. No QWidget/MLT mutation is moved to a worker thread. | `aiassistantwidget.*`, `mainwindow.cpp`, bundled MCP/REST clients; patches `async-native-*` / `async-agent-clients`. AI Edit JSON and sequence runner explicitly reject async analysis steps so deterministic editing semantics are preserved. | Patch-chain application against exact Build #80 source PASS locally. PR source/contract gates and full Windows compile/package are required. Existing packaged smoke does not run real Whisper/FFmpeg analysis, so those end-to-end paths remain NOT TESTED even after a green generic smoke unless dedicated coverage is added. |
| UI-05 | P1 / VERIFIED on packaged Windows Build #90 | Build #90 selected the real non-splash Edit Aja main window before and after normal restart. Geometry was 1178x756 at 48,48 both times; all deltas were zero and the editor title remained correct. | Keep current selection rules and tolerances. Do not weaken acceptance. Future DPI/layout matrix remains separate. | Build #90 `window-persistence.json` PASS plus before/after screenshots. |
| UI-06 | P1 / core + user-facing setting merged; exact post-merge Windows verification pending | The agent now owns a single-shot per-model-turn request timer with a 600s default and a bounded programmatic setter. On expiry the active reply is detached before abort, no edit/tool call is replayed automatically, busy state is released, and the next request may start cleanly. The user-facing Request timeout control is now integrated in the API toolbox, persists in settings, and applies its bounded value before each agent run. | `openaicompatibleagent.*`, patch `agent-request-timeout.patch`; Qt loopback fixture covers stalled response, stale callback safety, fresh retry and cancel-before-timeout. | AI Control + Source Reconstruction/Qt test must PASS, followed by exact-source Windows build. User-facing timeout setting is merged; exact post-merge packaged Windows verification remains separate. |
| UI-07 | P2 / implemented in current branch; verification pending | The AI trace and Local Edit history now have bounded document block counts. Very large individual trace/history entries are truncated only for display; oversized HTML is flattened to plain text and escaped before showing the truncation marker. Agent messages/tool payloads are unchanged. | `aiassistantwidget.cpp`, patch `bounded-ai-output.patch`; AI trace 600 blocks / 12k display chars per entry, Local Edit history 120 blocks with bounded command/message display. | AI Control + Source Reconstruction/full compile must PASS. Runtime memory/responsiveness under stress and real Windows visuals remain NOT TESTED. |
| UI-08 | P1 / implemented in PR #64; runtime proof pending | Existing smoke already proved save-copy. PR #64 adds fresh-process reopen of the saved copy, rechecks clip count and subtitle, renders a bounded MP4 range, waits for native render `finished`, then decodes the output with `ffmpeg.exe` from the portable tree and writes `render-evidence.json`. | `scripts/windows/functional-smoke-package.ps1`, `tests/test_build_render_roundtrip.py`, Windows docs. | Quality Gates #147 PASS. Exact post-merge Windows functional smoke must still PASS before marking runtime verified. |
| UI-09 | N/A / retired by portable-only delivery | Earlier installer builds showed an uninstall warning, but Windows delivery is now portable ZIP only. There is no installer or uninstaller in the current product path. | Keep portable smoke asserting no `uninstall.exe` is present and run the app directly from the extracted ZIP. | Portable ZIP startup + functional smoke PASS; installer/uninstall behavior is no longer a release criterion. |
| UI-10 | P1 / packaged screenshot + heartbeat VERIFIED; broader matrix remains | Build #90 captured `ai-agent-window.png`, DPI/scale metadata and WM_NULL heartbeat from the packaged editor after opening AI Agent. Heartbeat passed and restart screenshots proved the actual editor window was selected, not splash/internal Qt windows. | Preserve automated screenshot/heartbeat evidence; continue manual DPI/focus/keyboard/stress matrix separately. | Build #90 UI evidence PASS; full multi-DPI/manual interaction matrix remains NOT TESTED. |

## Real Windows UI verification matrix

Use a disposable test project and a separate application profile. Do not reset the
owner's settings or overwrite original media. No real API key is required for the
first pass; use a local delayed/error HTTP fixture for network lifecycle tests.

1. Screens: 1366x768 at 100%, 1920x1080 at 100/125/150%, 2560x1440 at 200%; record
   physical resolution and Qt logical dimensions. Resize/maximize/restore.
2. AI: open/close/tab/floating/redock; scroll every toolbox page; keyboard Tab,
   Shift+Tab, Enter; buttons visible/reachable; long Indonesian text and paths.
3. Requests: idle/working/cancel/error/retry; Enter twice; delayed success, invalid
   JSON, 401, 429, 500, connection refused, disconnect, never-responding server.
   Confirm one accepted operation and one terminal result; no stale callbacks.
4. Layout: first launch, old saved profile, restart with custom layout, Layout reset
   repeated 10 times; compare dock count, geometry, active project, undo history.
5. Editor: real A/V clip import, playback/scrub, split/move/trim, undo/redo, subtitle,
   save/reopen/export. Observe CPU/memory and event-loop lag during AI/tool work.
6. Stress: 100 trace events plus very large single result, 20 panel switches,
   20 resize cycles, close app during pending request and subprocess operation.
7. Log every failure with screenshot/video, exact steps, SHA/build, OS/scaling,
   expected/actual, sanitized stderr and owner domain. Proposed response targets:
   visible busy feedback within 200ms, no repeated >500ms UI stalls during async
   waiting; record actual measurements, not PASS inferred from source.

## How another AI continues

1. Fetch current main/open PRs and main Actions runs. Read newest relevant failed
   step logs before making a diagnosis; an older green build does not verify new UI.
2. Read this document and inspect changes after its audited SHA. Preserve work from
   other chats and keep P5 separate from the Gemini fork.
3. Reconstruct with `python scripts/reconstruct_source.py --output corresponding-source`.
   Edit a new patch against the fully reconstructed tree, not compressed historical
   patches. Wire manifest apply_chain + blueprint_payloads + Craft chain + verifier.
4. For UI-01/02 run the standalone Qt test using the actual reconstructed agent and
   registry (instructions in tests/qt-agent/README.md). Existing source gate also
   compiles/runs it. It requires no API account and does not verify full editor UI.
5. Preserve active exact-source Windows verification. Build #91 is the packaged proof for the Gemini-only UI cleanup; Build #92 is the packaged proof for Full Editor Control v1. Keep PR #64 unmerged until the chosen baseline build completes cleanly, then merge it and require a new Windows build whose functional smoke reaches fresh reopen, native render finish and packaged FFmpeg decode. Keep focused PRs.
6. Before merging: relevant tests, complete diff review, all quality gates green;
   after merging track exact-source Windows build separately. Preserve active builds.
7. Update this file with completed IDs, exact tests and unresolved risks. Do not mark
   this whole audit complete until the Windows matrix and data/export checks pass.

## Required handoff summary on every continuation

Record current main SHA/PR; last tested Windows SHA/run; observed failing step or
warning; changed files; tests actually executed; runtime/visual items NOT TESTED;
and one next executable task. Source or Qt-component PASS is not UI/release PASS.
No need to ask the owner to choose a threading framework or debug command.
