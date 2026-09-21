#!/usr/bin/env python3
"""Verify that the reconstructed P5 source contains every required integration."""

import argparse
import re
from pathlib import Path


TEXT_CHECKS = [
    ("src/aiassistant/aiassistantwidget.cpp", r"void AiAssistantWidget::runAgent\(\)\s*\{(?:\s*//[^\n]*\n)*\s*if \(!m_runButton->isEnabled\(\)\)", "Agent duplicate UI activation guard"),
    ("src/aiassistant/aiassistantwidget.cpp", r"m_prompt->setEnabled\(!busy\)", "Agent prompt follows busy state"),
    ("src/aiassistant/openaicompatibleagent.cpp", r"if \(m_reply != reply\)", "Ignore detached agent reply completion"),
    ("src/main.cpp", r'i18n\("Update P5 Edit Aja"\)', "Update P5 Edit Aja branding"),
    ("src/aiassistant/aiassistantwidget.cpp", r"AI Edit JSON", "Phase 6 AI Edit JSON UI"),
    ("src/aiassistant/aiassistantwidget.cpp", r"Local Edit.*Lightweight", "Phase 12 Local Edit UI"),
    ("src/mainwindow.cpp", r"kdenlive_set_transform_keyframes", "Phase 12 native Transform keyframe tool"),
    ("src/mainwindow.cpp", r"keyframes->removeAllKeyframes\(\)", "Keyframe API compatibility fix"),
    ("src/mainwindow.cpp", r"keyframes->updateKeyframe\(", "Public keyframe value update path"),
    ("src/mainwindow.cpp", r"kdenlive_get_scene_map", "Phase 13 Scene Detection map tool"),
    ("src/aiassistant/aiassistantwidget.cpp", r"beginMacro.*Local Edit: Zoom snapshots", "Phase 13 Local Edit single-undo grouping"),
    ("src/aiassistant/aiassistantwidget.cpp", r"Local Edit History", "Phase 14 Local Edit History UI"),
    ("src/mainwindow.cpp", r"creatorLocalEditPreview", "Phase 14 Creator Workspace preview control"),
    ("src/aiassistant/aiassistantwidget.cpp", r"Film Context", "Phase 15 Film Context optional UI"),
    ("src/aiassistant/aiassistantwidget.cpp", r"movie_search", "Phase 15 Film Context agent tools"),
    ("src/aiassistant/aiassistantwidget.cpp", r"Build Visual Index \(Optional\)", "Phase 15 optional visual index UI"),
    ("src/aiassistant/openaicompatibleagent.cpp", r"agent_image_paths", "Phase 15 multi-keyframe vision handoff"),
    ("src/mainwindow.cpp", r"const bool outputExists = output\.exists\(\);", "Native save target existence check"),
    ("src/mainwindow.cpp", r"saveFileAs\(output\.absoluteFilePath\(\), outputExists && overwrite, saveCopy\)", "Native save overwrite semantics"),
    ("src/mainwindow.cpp", r'm_aiAssistantDock = addDock\(i18n\("AI Agent"\)', "AI Agent right-sidebar dock"),
    ("src/mainwindow.cpp", r"Keep AI Agent as the primary right sidebar", "AI Agent post-layout docking"),
    ("src/aiassistant/aiassistantwidget.cpp", r"aiAssistantScrollArea", "Scrollable AI Agent sidebar"),
    ("src/aiassistant/aiassistantwidget.cpp", r"AI Agent — Main Control", "AI Agent primary command surface"),
    ("src/mainwindow.cpp", r"creatorAiAgentButton", "Filmora-style primary AI Agent workspace button"),
    ("src/mainwindow.cpp", r"Qt::ToolButtonTextUnderIcon", "Filmora-style Creator Workspace category layout"),
    ("src/mainwindow.cpp", r"Quick Edit: potong 5", "Creator Workspace Quick Edit command surface"),
    ("src/aiassistant/aiassistantwidget.cpp", r"aiAssistantToolbox", "Compact AI Agent supporting-tool toolbox"),
    ("src/aiassistant/aiassistantwidget.cpp", r"toolBox->addItem\(localEditGroup, i18n\(\"Quick Edit\"\)\)", "AI Agent Quick Edit toolbox page"),
    ("src/mainwindow.cpp", r"editaja/creatorLayoutVersion", "One-time creator layout migration state"),
    ("src/mainwindow.cpp", r"Location_OnLeft, m_projectMonitorDock", "Creator layout media-left docking"),
    ("src/mainwindow.cpp", r"Location_OnRight, m_projectMonitorDock", "Creator layout AI/properties-right docking"),
    ("src/mainwindow.cpp", r"Location_OnBottom, nullptr, timelineSize", "Creator layout full-width bottom timeline"),
    ("src/mainwindow.cpp", r"void MainWindow::applyCreatorLayout\(\)", "Reusable Creator Layout restore action"),
    ("src/mainwindow.cpp", r"creatorLayoutButton", "Creator Workspace Layout restore button"),
    ("src/aiassistant/agenttoolregistry.cpp", r"registerAsyncTool", "Shared async tool registration"),
    ("src/aiassistant/agenttoolregistry.cpp", r"invokeOrStart", "Shared async tool job start"),
    ("src/aiassistant/agentipcserver.cpp", r"/v1/jobs/", "REST async tool job status/cancel endpoints"),
    ("src/aiassistant/openaicompatibleagent.cpp", r"processNextToolCall", "AI Agent async tool continuation"),
    ("src/aiassistant/openaicompatibleagent.cpp", r"cancelJob\(toolJobId\)", "AI Agent async tool cancellation"),
    ("src/aiassistant/aiassistantwidget.cpp", r"startFilmContextTool", "Event-driven Film Context process path"),
    ("src/aiassistant/aiassistantwidget.cpp", r"QProcess::started", "Film Context process started signal"),
    ("src/aiassistant/aiassistantwidget.cpp", r"registerAsyncTool\(\s*QStringLiteral\(\"movie_search\"\)", "Film Context tools registered asynchronously"),
    ("src/aiassistant/aiassistantwidget.cpp", r"m_filmContextIndexer, &QProcess::errorOccurred", "Nonblocking Film Context indexer startup error path"),
    ("src/aiassistant/aiassistantwidget.h", r"NativeAsyncToolExecutor", "Async native editor executor contract"),
    ("src/aiassistant/aiassistantwidget.cpp", r"registerAsyncNativeTool", "Async native tool registration bridge"),
    ("src/aiassistant/aiassistantwidget.cpp", r"registerAsyncNativeTool\(\s*QStringLiteral\(\"kdenlive_detect_silence\"\)", "Silence detection registered asynchronously"),
    ("src/aiassistant/aiassistantwidget.cpp", r"registerAsyncNativeTool\(\s*QStringLiteral\(\"kdenlive_transcribe_media\"\)", "Transcription registered asynchronously"),
    ("src/mainwindow.cpp", r"stopAgentOwnedProcess", "Owned analysis process-tree cancellation"),
    ("src/mainwindow.cpp", r"FFmpeg silence detection timed out", "Async silence deadline handling"),
    ("src/mainwindow.cpp", r"Whisper transcription timed out", "Async transcription deadline handling"),
    ("tools/mcp/kdenlive_mcp_server.py", r"jobs/status", "MCP async job polling"),
    ("tools/api/kdenlive_agent_api_example.py", r"/jobs/\{job_id\}", "REST example async job polling"),
    ("src/aiassistant/openaicompatibleagent.cpp", r"handleRequestTimeout", "Bounded API request timeout handler"),
    ("src/aiassistant/openaicompatibleagent.cpp", r"m_requestTimer->start\(m_requestTimeoutMs\)", "Per-turn API timeout start"),
    ("src/aiassistant/aiassistantwidget.cpp", r"requestTimeoutSeconds", "User-facing API request timeout setting"),
]


# Creating subtitles must initialize the lazy model through the native UI path.
# Match within each dispatch branch so another tool's initializer cannot pass.
for tool in ("kdenlive_add_subtitle", "kdenlive_import_subtitles", "kdenlive_add_subtitle_batch"):
    TEXT_CHECKS.append((
        "src/mainwindow.cpp",
        rf'if \(toolName == QLatin1String\("{tool}"\)\) \{{\s*'
        r'//[^\n]*\n\s*showSubtitleTrack\(\);\s*const auto subtitles = model->getSubtitleModel\(\);',
        f"Native subtitle initialization for {tool}",
    ))

REQUIRED_FILES = [
    ("src/aiassistant/aiassistantwidget.cpp", "Phase 5 AI assistant source"),
    ("data/scripts/filmcontext/film_context.py", "Phase 15 local Film Context backend"),
    ("tools/mcp/kdenlive_mcp_server.py", "MCP bridge client"),
    ("tools/api/kdenlive_agent_api_example.py", "REST bridge example client"),
]


FORBIDDEN_PATTERNS = [
    ("src/mainwindow.cpp", r"waitForStarted|waitForFinished|waitForReadyRead", "Blocking QProcess wait remains in MainWindow AI tool bridge"),
]


def verify(root: Path) -> None:
    failures = []

    for relative, label in REQUIRED_FILES:
        if not (root / relative).is_file():
            failures.append(f"{label} is missing: {relative}")

    for relative, pattern, label in TEXT_CHECKS:
        path = root / relative
        if not path.is_file():
            failures.append(f"{label} cannot be checked because {relative} is missing")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not re.search(pattern, text, flags=re.MULTILINE):
            failures.append(f"{label} verification failed in {relative}")

    for relative, pattern, label in FORBIDDEN_PATTERNS:
        path = root / relative
        if not path.is_file():
            failures.append(f"{label} cannot be checked because {relative} is missing")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(pattern, text, flags=re.MULTILINE):
            failures.append(f"{label} in {relative}")

    if failures:
        raise SystemExit("\n".join(failures))

    print(f"Verified {len(TEXT_CHECKS)} source markers, {len(FORBIDDEN_PATTERNS)} forbidden-pattern rules and {len(REQUIRED_FILES)} required files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    verify(parser.parse_args().source_root.resolve())
