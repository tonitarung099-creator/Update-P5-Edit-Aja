# Update P5 Edit Aja roadmap

`Update P5 Edit Aja` starts from the full Edit Aja Phase 5 baseline and develops the more experimental automation/AI-native feature set here, without changing the original Edit Aja repository.

## Phase 6 — AI Edit JSON

- [x] Deterministic JSON edit-script format.
- [x] Phase 5 REST discovery/auth client.
- [x] Live tool-catalog validation.
- [x] Cross-step `$ref` values.
- [x] Portable `$var` values and relative media paths.
- [x] Live `$track` and `$clip_at` selectors.
- [x] Automatic project checkpoint before apply.
- [x] Execution report and stop/continue-on-error modes.
- [x] Unit tests and CI.
- [ ] Native **Import AI Edit…** UI inside the editor.
- [ ] Visual change preview and per-step enable/disable UI.
- [ ] One-click import of JSON produced by ChatGPT.

## Phase 7 — Media intelligence

Planned as optional analysis backends feeding the same edit-script/native tool layer:

- scene/shot detection (PySceneDetect-style backend),
- silence/pause analysis and smart jump cuts,
- motion/activity analysis,
- filler-word and bad-take markers,
- pacing analysis,
- beat analysis.

## Phase 8 — Speech, captions and audio

- optional local whisper.cpp backend alongside existing speech recognition,
- word-level animated captions and reusable caption presets,
- speaker-aware transcript workflow,
- voice cleanup/noise suppression backend such as DeepFilterNet,
- loudness normalization and auto-ducking.

## Phase 9 — Visual intelligence

- object/face tracking,
- masks and subject isolation,
- background removal/blur,
- smart reframe for 16:9, 9:16 and 1:1,
- optional SAM 2-style segmentation backend.

GPU-heavy models should remain optional modules rather than mandatory editor dependencies.

## Phase 10 — Documentary/creator graphics

- B-roll placeholders and asset slots,
- map/timeline/chart graphics,
- quote/source cards and lower thirds,
- Ken Burns/photo motion presets,
- reusable documentary motion-graphics templates.

## Interchange and architecture

- Keep Kdenlive/MLT as the native editable timeline/rendering foundation.
- Keep the existing Phase 5 built-in AI Agent unchanged as one control path.
- AI Edit JSON is a second deterministic control path using the same native registry.
- Continue using OpenTimelineIO support where suitable for editorial interchange.
- External analysis/model integrations must be isolated behind adapters and reviewed for code/model licensing before distribution.
