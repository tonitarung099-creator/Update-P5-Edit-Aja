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
- [x] Native **AI Edit JSON** import UI inside the editor.
- [ ] Rich visual change preview and per-step enable/disable UI (current preview validates and summarizes the plan).
- [x] One-click open/validate/apply flow for JSON produced by ChatGPT.

## Phase 7 — Media intelligence

Planned as optional analysis backends feeding the same edit-script/native tool layer:

- [x] scene/shot detection using FFmpeg scene scores (optional PySceneDetect backend can be added later),
- [x] silence/pause analysis and smart jump-cut JSON generation,
- [ ] motion/activity analysis,
- [x] filler-word, immediate-repeat and long-gap dialogue analysis,
- [ ] semantic bad-take detection/review,
- [x] pacing analysis from detected scene durations,
- [ ] beat analysis.
- [x] black-frame detection.
- [x] media metadata normalization with FFprobe.

## Phase 8 — Speech, captions and audio

- [x] optional local whisper.cpp backend alongside existing speech recognition,
- [x] phrase and word-level smart caption segmentation with reusable native subtitle styles,
- [ ] richer animated typography/caption presets,
- [ ] speaker-aware transcript workflow,
- [x] optional DeepFilterNet voice cleanup/noise suppression backend,
- [x] LUFS/true-peak analysis and native clip-gain normalization plans,
- [x] native fade-in/fade-out plan generation,
- [ ] auto-ducking.

## Phase 9 — Visual intelligence

- [x] normalized subject-track interchange format,
- [x] optional OpenCV face tracking backend,
- [ ] richer object tracking backend,
- [ ] masks and subject isolation,
- [ ] background removal/blur,
- [x] smart reframe planner for vertical, square, portrait and landscape outputs,
- [ ] optional SAM 2-style segmentation backend.

GPU-heavy models should remain optional modules rather than mandatory editor dependencies.

## Phase 10 — Documentary/creator graphics

- [x] B-roll insertion and placeholders/asset slots,
- [ ] map/timeline/chart graphics,
- [x] quote/source cards and lower thirds,
- [x] chapter cards,
- [x] editable Ken Burns/photo motion presets,
- [ ] reusable advanced documentary motion-graphics templates.

## Interchange and architecture

- Keep Kdenlive/MLT as the native editable timeline/rendering foundation.
- Keep the existing Phase 5 built-in AI Agent unchanged as one control path.
- AI Edit JSON is a second deterministic control path using the same native registry.
- Continue using OpenTimelineIO support where suitable for editorial interchange.
- External analysis/model integrations must be isolated behind adapters and reviewed for code/model licensing before distribution.
