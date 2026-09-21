# P5 UI stability audit and AI handoff

Audit date: 2026-09-21 UTC. User request: inspect UI errors/responsiveness, fix
proven problems, and preserve a plan another AI can execute without this chat.
This is the continuation entry point; read AGENTS.md and AI_WORKING_RULES.md first.
Do not describe this audit as a complete interactive Windows UI test.

## Verified baseline (refresh before changing anything)

- Repository: `tonitarung099-creator/Update-P5-Edit-Aja` (not Edit-Aja-Gemini).
- Audited main: `dfbc232861a7d9466214228e1ca8e4fcb92355a1`.
- Main quality run `35558927632` (#60): PASS.
- Latest completed Windows run inspected: `35522742493` (#75), source
  `8c70026cbe7df521ef8c57902ce9801dad2ab304`, job `106109527735`: PASS.
- #75 actual logs: installer/startup, live AI panel registration/open command,
  project load (500 frames), split (2 to 4 clips), subtitle add/list, save-copy PASS.
  These assertions do not measure rendering, responsiveness, DPI or visual layout.
- #75 still warns that both smoke uninstall invocations exited -1; uninstall PASS
  must not be inferred from the workflow conclusion.
- #76 `35558745152` on `1ff97e10092b4bb52853031387e3ec531bb0ca15`
  was active; #77 `35558960153` on audited main was pending at audit start.
  Neither is evidence that the latest layout has already worked in a packaged app.
- Main changes since #75: creator-layout migration and one-click layout restore.
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
| UI-01 | P1 / fix in this change; packaged verification pending | `setBusy` disables Run but leaves prompt enabled; Return calls `runAgent`, clears output and runs checkpoint before backend rejects duplicate. Backend rejection also emits busy=false while original request is live. | `aiassistantwidget.cpp` runAgent/setBusy; `openaicompatibleagent.cpp` run. Guard before side effects, disable prompt while busy, reject duplicate without changing active busy state. | Delayed local API fixture: duplicate start produces one HTTP request, no false idle event; UI Return while busy does not clear trace or create a second checkpoint. |
| UI-02 | P1 / fix in this change; packaged verification pending | Cancel calls abort before detaching current reply; finished callback processes even stale replies. Cancellation can emit API failure and old replies can alter later state. | `openaicompatibleagent.cpp` cancel/sendTurn. Detach first, ignore completions that no longer own active reply, preserve deferred deletion. | Qt component test cancel, cancel twice, immediately start new request: no cancellation API error or old completion; new request finishes and busy transitions correctly. |
| UI-03 | P0 / fix in this change; packaged verification pending | The synchronous Film Context tool path is replaced by bounded async jobs. Native timeline tools remain synchronous on the GUI thread; process-backed Film Context uses signal/timer-driven `QProcess`, shared job IDs, status/cancel for REST/MCP, and Agent continuation without a nested event loop. | `agenttoolregistry.*`, `agentipcserver.cpp`, `openaicompatibleagent.*`, `aiassistantwidget.*`; patches `async-*`. Qt regression uses a delayed local async fixture and cancel/restart path. | Patch-chain application PASS locally. PR gates must compile the reconstructed production registry/agent and prove heartbeat/cancel behavior. Exact-source packaged Windows behavior remains NOT TESTED until the post-merge build. |
| UI-04 | P1 / CONFIRMED additional blocking paths | Film Context index buttons call waitForStarted(3000); MainWindow silence-detection path uses waitForFinished and transcription startup waits. | Audit these call sites with UI-03; async started/errorOccurred/finished, bounded progress, cancel controls; do not put QWidget/MLT editing operations on arbitrary worker threads. | Missing Python, slow startup, crashed FFmpeg, long media, cancel and application close each leave a usable UI and no orphan owned processes. |
| UI-05 | P1 / NOT TESTED sizing and layout persistence | Toolbar has many minimum-width buttons plus 250px command box; sidebar min width 320, output min height 220, nested scroll/toolbox. `finishUiSetup` still reopens/redocks AI after every restore despite one-time migration comment. Clipping is a hypothesis until visually reproduced; forced reopening is confirmed code behavior. | `creator-workspace-filmora.patch`, `creator-layout-filmora.patch`, `creator-layout-reset.patch`, `ai-agent-sidebar.patch`, `ai-agent-toolbox.patch`. Capture real screenshots before changing geometry. Keep AI default on right; define migration separately from later user layout persistence. | Matrix below: reachable controls, no overlap, monitor/timeline usable, intended persistence after restart, Layout reset preserves project/undo and does not duplicate panels. |
| UI-06 | P1 / CONFIRMED no explicit request timeout | `sendTurn` posts without a transfer/deadline timer; stalled API can leave busy state indefinitely until user cancel. | Add configurable bounded request policy with local stalled HTTP fixture; invalidate old reply before timeout abort. Never automatically replay editing tool calls. | Stalled connection releases busy state within configured bound; useful timeout message; subsequent run succeeds; normal long local model response is supported intentionally. |
| UI-07 | P2 / CONFIRMED unbounded UI output, slowdown not measured | `appendTrace` appends arbitrary JSON to QTextBrowser; no block/size cap. Local Edit history also appends. Large tool output/history can increase document layout/memory cost. | Bound UI display size and history, retain separate diagnostic evidence; escape plain text at trust boundary. Do not truncate actual tool result fed to model without a defined contract. | Large multiline and single-line outputs remain responsive, old UI entries evicted, plain text cannot become unintended markup; measure memory after sustained use. |
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
5. Prioritize UI-03 async process contract and UI-10 real screenshot/heartbeat
   evidence, then UI-05 geometry/persistence and UI-08 reopen/export. Keep focused PRs.
6. Before merging: relevant tests, complete diff review, all quality gates green;
   after merging track exact-source Windows build separately. Preserve active builds.
7. Update this file with completed IDs, exact tests and unresolved risks. Do not mark
   this whole audit complete until the Windows matrix and data/export checks pass.

## Required handoff summary on every continuation

Record current main SHA/PR; last tested Windows SHA/run; observed failing step or
warning; changed files; tests actually executed; runtime/visual items NOT TESTED;
and one next executable task. Source or Qt-component PASS is not UI/release PASS.
No need to ask the owner to choose a threading framework or debug command.
