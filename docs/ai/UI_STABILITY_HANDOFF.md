# P5 UI stability audit and AI handoff

Audit date: 2026-09-21 UTC. User request: inspect UI errors/responsiveness, fix
proven problems, and preserve a plan another AI can execute without this chat.
This is the continuation entry point; read AGENTS.md and AI_WORKING_RULES.md first.
Do not describe this audit as a complete interactive Windows UI test.

## Verified baseline (refresh before changing anything)

- Repository: `tonitarung099-creator/Update-P5-Edit-Aja` (not Edit-Aja-Gemini).
- Current verified main before this UI-04 continuation: `76a03fcc4607cb01c75dd2b4bf64ec35dd2a9bcf`.
- Main quality run `35562239668` (#68): PASS.
- Latest exact-source Windows run: `35562333388` (#80), source
  `76a03fcc4607cb01c75dd2b4bf64ec35dd2a9bcf`, job `106217434464`: PASS.
- #80 completed Windows compile, packaging, installer/startup smoke and the existing
  functional editor smoke for the exact current main. It contains PR #40 request
  lifecycle, PR #41 async Film Context tools, and PR #42 nonblocking Film Context
  indexer startup.
- Existing functional smoke still does not execute real FFmpeg silence detection or
  Whisper transcription, does not measure rendering/responsiveness/DPI, and does
  not prove uninstall success. Those boundaries remain explicit.
- This branch changes the remaining MainWindow silence/transcription process paths;
  exact-source Windows compile/package and end-to-end analysis-tool behavior are
  NOT TESTED until PR/merged Windows verification.
- Open PRs at audit start: none. Other chats can modify this repo: refresh main,
  PRs and run lineage immediately before pushing/merging.

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
| UI-05 | P1 / NOT TESTED sizing and layout persistence | Toolbar has many minimum-width buttons plus 250px command box; sidebar min width 320, output min height 220, nested scroll/toolbox. `finishUiSetup` still reopens/redocks AI after every restore despite one-time migration comment. Clipping is a hypothesis until visually reproduced; forced reopening is confirmed code behavior. | `creator-workspace-filmora.patch`, `creator-layout-filmora.patch`, `creator-layout-reset.patch`, `ai-agent-sidebar.patch`, `ai-agent-toolbox.patch`. Capture real screenshots before changing geometry. Keep AI default on right; define migration separately from later user layout persistence. | Matrix below: reachable controls, no overlap, monitor/timeline usable, intended persistence after restart, Layout reset preserves project/undo and does not duplicate panels. |
| UI-06 | P1 / core implemented in current branch; verification pending | The agent now owns a single-shot per-model-turn request timer with a 600s default and a bounded programmatic setter. On expiry the active reply is detached before abort, no edit/tool call is replayed automatically, busy state is released, and the next request may start cleanly. The optional user-facing timeout control is intentionally deferred to a small follow-up so this core reliability fix does not depend on fragile sidebar-layout patch context. | `openaicompatibleagent.*`, patch `agent-request-timeout.patch`; Qt loopback fixture covers stalled response, stale callback safety, fresh retry and cancel-before-timeout. | AI Control + Source Reconstruction/Qt test must PASS, followed by exact-source Windows build. User-facing timeout setting remains PLANNED/NOT IMPLEMENTED in this PR. |
| UI-07 | P2 / implemented in current branch; verification pending | The AI trace and Local Edit history now have bounded document block counts. Very large individual trace/history entries are truncated only for display; oversized HTML is flattened to plain text and escaped before showing the truncation marker. Agent messages/tool payloads are unchanged. | `aiassistantwidget.cpp`, patch `bounded-ai-output.patch`; AI trace 600 blocks / 12k display chars per entry, Local Edit history 120 blocks with bounded command/message display. | Patch apply check PASS locally. AI Control + Source Reconstruction/full compile must still PASS. Runtime memory/responsiveness under stress and real Windows visuals remain NOT TESTED. |
| UI-08 | P1 / NOT TESTED data persistence and export | Existing smoke proves save file exists/size and original active path, not reopening edited contents; no render/decode assertions. | Extend packaged functional smoke in separate change: save, reopen in fresh process, compare timeline/subtitle semantics, short render, decode via packaged tools. | Edited clip positions/durations and subtitle text/timing survive reopening; render completes, nonempty output decodes with expected duration/audio/video. |
| UI-09 | P2 / OBSERVED uninstall warning | #75 uninstaller exit -1; test then removes directory manually. No proven cause yet. | Inspect pinned NSIS script/current-user mode and invoke syntax before changing installer. | Actual uninstall returns intended success, removes registry/files, reinstall works; keep separate from startup PASS. |
| UI-10 | P1 / COVERAGE GAP | Live panel open tool returns success but no screenshot, geometry, focus, DPI, keyboard or stress assertions. | Add Windows UI evidence capture to existing workflow/smoke, plus separate manual matrix; include exact source SHA/resolution/scaling in evidence. | Review actual screenshots, measure event-loop response; native tool success alone cannot satisfy UI acceptance. |

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
5. Preserve the active exact-source Windows verification for UI-04. Finish the
   current UI-06 timeout PR only after its Qt lifecycle/source gates are green, and
   do not merge it while an older Windows build still needs diagnosis. Then prioritize
   UI-10 real screenshot/heartbeat evidence, followed by UI-05 geometry/persistence
   and UI-08 reopen/export. Keep focused PRs.
6. Before merging: relevant tests, complete diff review, all quality gates green;
   after merging track exact-source Windows build separately. Preserve active builds.
7. Update this file with completed IDs, exact tests and unresolved risks. Do not mark
   this whole audit complete until the Windows matrix and data/export checks pass.

## Required handoff summary on every continuation

Record current main SHA/PR; last tested Windows SHA/run; observed failing step or
warning; changed files; tests actually executed; runtime/visual items NOT TESTED;
and one next executable task. Source or Qt-component PASS is not UI/release PASS.
No need to ask the owner to choose a threading framework or debug command.
