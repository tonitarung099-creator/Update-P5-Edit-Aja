# Update P5 Edit Aja

**Update P5 Edit Aja** is the experimental, expanded version of the Edit Aja video editor. It starts from the complete Edit Aja Phase 5 baseline built on Kdenlive/MLT, while the original `Edit-Aja` repository can remain stable.

The project is designed around three editing paths that share the same native timeline foundation:

1. normal manual editing,
2. the existing Phase 5 built-in AI Agent / MCP / REST control layer, and
3. deterministic **AI Edit JSON** files created outside the editor (for example by ChatGPT) and applied to the editable timeline.

## Current baseline

The repository retains the complete Phase 1–5 Edit Aja work:

- built-in OpenAI-compatible API agent,
- MCP and localhost REST/JSON bridges,
- shared native `kdenlive_*` editing tool registry,
- project/timeline/media/effect/subtitle/render tools,
- local transcription and silence/jump-cut primitives,
- Edit Aja branding and Windows packaging workflow.

The internal `kdenlive_*` names intentionally remain for Phase 5 API compatibility.

## Phase 6: AI Edit JSON

The first Update P5 feature is implemented both as developer tooling under `tools/ai_edit/` / `ai-edit/` and as a native editor UI applied by the Phase 6 source patch.

A JSON edit file can call the existing Phase 5 registry directly, reference values returned by earlier steps, resolve a live track, or find the clip covering a timeline time. This means an external AI can make editing decisions while Update P5 Edit Aja remains the deterministic executor.

```text
MP4 + editing request
        ↓
      ChatGPT
        ↓
update-p5-ai-edit JSON
        ↓
AI Edit runner
        ↓
Phase 5 localhost REST bridge
        ↓
shared native tool registry
        ↓
editable Kdenlive/MLT timeline
```

Validate an edit file:

```text
python tools/ai_edit/update_p5_ai_edit.py validate ai-edit/examples/documentary-basic.json
```

Inside the application, use the **AI Edit JSON** button in the Creator Workspace (or the AI Assistant panel) to choose a JSON file, preview/validate it, and apply it directly to the editable timeline. Missing asset variables can be resolved with native file pickers.

For developer/automation use, with Update P5 Edit Aja running and the AI Agent panel opened, inspect the live catalog or apply a plan from the command line:

```text
python tools/ai_edit/update_p5_ai_edit.py catalog
python tools/ai_edit/update_p5_ai_edit.py apply my-edit.json
```

The runner creates a project checkpoint before applying edits by default. See `ai-edit/FORMAT.md` for the format, references, variables and selectors.

## New intelligence engines

Update P5 now includes feature engines outside the original Phase 5 AI Agent:

- **Media Intelligence** — FFprobe metadata, silence detection, scene/shot detection, black-frame detection, loudness measurement, pacing analysis, and smart jump-cut JSON generation.
- **Caption Intelligence** — SRT/transcript ingestion, phrase captions, word-by-word captions, timing resegmentation, case transforms, and direct native subtitle-batch JSON generation.
- **Audio Intelligence** — LUFS/true-peak measurement, safety-bounded gain recommendations, native clip-volume normalization, and optional native audio fades.

These engines intentionally feed the same Phase 6 AI Edit/native tool layer rather than introducing another AI agent.

## Roadmap

See `ROADMAP.md`. Planned areas now move beyond the completed native AI Edit import UI into richer change previews, scene/media intelligence, advanced captions and audio cleanup, object tracking/masking/background removal, smart reframe, documentary graphics, and optional analysis/model backends.

## Upstream and license

Update P5 Edit Aja is based on Edit Aja and Kdenlive and preserves the GPL licensing and upstream copyright notices. The reproducible build remains pinned to upstream Kdenlive commit:

`c3d8a38c04470f6726b21485fc488f2cd2921654`

Upstream Kdenlive: https://github.com/KDE/kdenlive

Original baseline repository: https://github.com/tonitarung099-creator/Edit-Aja

This repository: https://github.com/tonitarung099-creator/Update-P5-Edit-Aja

Third-party engines/models added in later phases must receive a separate license/dependency review before they are bundled or distributed.
