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

## Remaining boundary

Actions that open a modal dialog can be launched through the QAction bridge, but the contents of arbitrary dialogs are not automatically editable merely because the dialog was opened. Frequently used editing operations should continue to receive dedicated native tools with typed parameters so Gemini can perform them deterministically and verify the result.
