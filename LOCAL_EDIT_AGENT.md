# Local Edit Agent

Local Edit Agent is the lightweight, offline-first natural-language command path for Update P5 Edit Aja.

It is intentionally **not** a second large AI model. Simple editing language is handled deterministically on the user's laptop:

\`\`\`text
user words
  -> typo/alias normalizer
  -> local command parser
  -> timeline context
  -> math engine
  -> native tool hint / native adapter
  -> editable timeline
\`\`\`

Only requests that genuinely need semantic judgement or an external service are routed to the existing API/MCP AI path.

## Routing

The interpreter returns one of four routes:

- \`local\` — lightweight parser/math/context only.
- \`local_tool\` — specialized installed local engine such as whisper.cpp, DeepFilterNet, Demucs, SAM 2, or Media Intelligence.
- \`ai\` — semantic/editorial reasoning should go to the configured API AI agent.
- \`mcp\` — external search/assets/actions should go through an MCP-capable agent/tool.

## Typo-tolerant commands

Examples that remain local:

\`\`\`text
ptong 5
potong menit 5
hpus sceen 73
split disini
semua snapshpt zom 100 ke 111 5 dtk
\`\`\`

\`ptong 5\` is normalized to \`potong 5\`. By user convention a bare number after split/cut is treated as minutes, but is marked \`needs_confirmation=true\` so the UI can show:

\`\`\`text
Dipahami sebagai: Potong di 05:00
[ Jalankan ] [ Ubah ]
\`\`\`

Explicit \`potong menit 5\` is high-confidence and does not require that clarification.

## Timeline context

The parser can receive a small JSON context object, for example:

\`\`\`json
{
  "playhead_seconds": 123.4,
  "selected_clip_id": 42,
  "selected_clip_duration": 4.5,
  "scenes": {
    "73": {"start": 501.4, "end": 507.9}
  },
  "snapshots": [
    {"id": 1001, "duration": 4.5},
    {"id": 1002, "duration": 8.0}
  ]
}
\`\`\`

This lets phrases such as \`split disini\`, \`hapus scene 73\`, and \`zoom snapshot ini\` resolve without an LLM.

## Zoom math

For:

\`\`\`text
semua snapshot zoom 100 ke 111 5 detik
\`\`\`

the reference motion is 100% at time 0 and 111% at 5 seconds.

For a snapshot that is only 4.5 seconds:

\`\`\`text
100 + (111 - 100) * (4.5 / 5) = 109.9%
\`\`\`

So its generated animation ends at 109.9%. A snapshot longer than 5 seconds reaches 111% at 5 seconds, then holds 111% for the rest of the clip. Snapshot/photo animation defaults to smooth easing.

The interpreter emits explicit keyframe math as portable command IR. The current native registry has static transform plus generic effect-keyframe primitives; a dedicated transform-keyframe adapter is the intended final executor for parameter-specific smooth scale animation.

## CLI

\`\`\`bash
python tools/local_edit_agent/local_edit_agent.py ptong 5 --pretty
python tools/local_edit_agent/local_edit_agent.py "hpus sceen 73" --context timeline-context.json --pretty
python tools/local_edit_agent/local_edit_agent.py "semua snapshpt zom 100 ke 111 5 dtk" --context timeline-context.json --pretty
\`\`\`

No third-party Python package is required for the normal parser.

## Safety/UX rule

High-confidence deterministic commands may be configured for direct execution. Ambiguous or destructive commands should show the normalized interpretation first. Unknown language never guesses a native edit: it routes to the configured AI/MCP path instead.
