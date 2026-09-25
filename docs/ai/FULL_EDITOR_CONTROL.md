# Full Editor Control

The built-in Gemini AI Agent already has direct native editing tools for timeline edits, subtitles, effects, transforms, speed, volume, crop, transitions, titles, tracks, render/export, project save/checkpoints, transcription, silence detection and Film Context.

It also has a generic editor-action bridge:

- `kdenlive_list_actions` discovers registered editor `QAction` commands.
- `kdenlive_trigger_action` triggers a registered action by internal name.

## Full Editor Control v1

This layer makes generic action control safer and less ambiguous.

- Action discovery now exposes `enabled`, `visible`, `checkable`, `checked` and shortcut state.
- `kdenlive_get_action_state` reads one exact action by internal name.
- `kdenlive_set_action_checked` requests an explicit checked state instead of blindly toggling a checkbox/toggle action.
- If the action is already in the requested state, it is not triggered again.
- Disabled or non-checkable actions return explicit errors.
- After a state change, the result reports whether the requested state was reached.

This is intentionally native editor control. It does not automate mouse coordinates or depend on screen layout.

## Full Editor Control v2 — project guides

Gemini can work with project timeline guides/markers through typed native tools:

- `kdenlive_list_guides` reads point/range guides with frame/time, comment, category and duration.
- `kdenlive_add_guide` adds a point guide or duration-based range guide.
- `kdenlive_edit_guide` edits text/category/duration or moves a guide.
- `kdenlive_delete_guide` removes an exact guide.
- Guide categories are validated against Kdenlive's current marker categories.
- Adding onto an occupied frame is rejected by default; replacement requires explicit `overwrite=true`.
- Moving an existing guide onto another occupied frame is always rejected to protect Kdenlive's frame-to-guide mapping.
- Mutations use Kdenlive's `MarkerListModel`, retaining native undo/redo semantics.

## Full Editor Control v3 — track state

Gemini can now inspect and set exact timeline-track state without relying on blind toggle actions:

- `kdenlive_get_track_state` reads track position/type, custom name, lock state, active state and effect-stack state, plus only the type-relevant visibility field (`muted` for audio or `hidden` for video).
- `kdenlive_set_track_state` accepts explicit target values for name, lock, active state and effect-stack state.
- Audio tracks use the explicit `muted` field; video tracks use the explicit `hidden` field. Cross-type misuse is rejected.
- Toggle-backed editor behavior is only invoked when the current value differs from the requested value.
- Track rename, lock, mute/hide and effect-stack changes use Kdenlive's native model/controller paths; the response returns the final state plus `changed_fields`.

## Remaining boundary

Actions that open a modal dialog can be launched through the QAction bridge, but the contents of arbitrary dialogs are not automatically editable merely because the dialog was opened. Frequently used editing operations should continue to receive dedicated native tools with typed parameters so Gemini can perform them deterministically and verify the result.
