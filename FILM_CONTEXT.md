# Film Context

Film Context is an optional local capability for **Update P5 Edit Aja**. It gives an AI agent a small searchable memory of a movie so the agent does not need to inspect or upload the full movie on every request.

It is deliberately separate from **AI Edit JSON**:

- Film Context answers: *what is in the source movie and where is it?*
- AI Edit JSON answers: *what timeline edits should Edit Aja execute?*

Film Context itself never edits the timeline.

## Design goals

1. Local-first. Building/searching the base index uses no API.
2. Optional. Edit Aja must remain usable when Film Context is disabled or absent.
3. Text-first escalation. Return timestamps/dialogue first; generate images only for a few requested candidates.
4. Reusable cache. Index a movie once and reuse it in later projects.
5. Small model context. AI providers receive compact JSON results instead of a whole-film dump.
6. Stable tool protocol. Gemini, OpenAI-compatible agents, MCP adapters, or future local agents can use the same movie tools.

## Current Phase 15 core

The base implementation is dependency-light:

- FFmpeg scene-change detection
- FFprobe duration lookup
- optional SRT parsing
- SQLite scene/subtitle database
- local BM25 ranking over dialogue + local scene notes
- optional continuity bias with \`near_scene\`
- neighboring scene context
- on-demand keyframe extraction and cache
- JSON tool-call adapter

No third-party Python package is required by the core.

## Build an index

\`\`\`bash
python tools/film_context/film_context.py index movie.mp4 \
  --srt movie.srt \
  --index-dir .film-context/movie
\`\`\`

The output directory contains:

\`\`\`text
.film-context/movie/
  manifest.json
  movie.db
  keyframes/        # created only when keyframes are requested
\`\`\`

The initial index deliberately does **not** render every scene to images.

## Search locally

\`\`\`bash
python tools/film_context/film_context.py search \
  "John kembali ke rumah" \
  --index-dir .film-context/movie \
  --top-k 5
\`\`\`

The result is compact JSON with scene ids, source timestamps, scores and a short dialogue/notes excerpt.

For story continuity:

\`\`\`bash
python tools/film_context/film_context.py search \
  "mencari ayahnya" \
  --index-dir .film-context/movie \
  --near-scene 214
\`\`\`

This keeps semantic text matching dominant while adding a small proximity preference.

## Read one candidate and its neighbors

\`\`\`bash
python tools/film_context/film_context.py scene 214 \
  --index-dir .film-context/movie

python tools/film_context/film_context.py context 214 \
  --index-dir .film-context/movie \
  --radius 2
\`\`\`

This is the intended AI flow:

\`\`\`text
movie_search(query)
       ↓
small Top-K list
       ↓
movie_get_context(best candidate)
       ↓
still ambiguous?
       ↓
movie_get_keyframes([candidate ids])
\`\`\`

Only the final step generates image files.

## On-demand keyframes

\`\`\`bash
python tools/film_context/film_context.py keyframes 214 216 \
  --index-dir .film-context/movie \
  --count 2
\`\`\`

Film Context chooses times inside each scene rather than exact cut boundaries, reducing accidental transition/black frames. A maximum of a few frames per requested scene is intended.

## Stable AI tool protocol

\`\`\`bash
python tools/film_context/film_context.py tool-catalog
\`\`\`

Phase 15 exposes these names:

- \`movie_context_status\`
- \`movie_search\`
- \`movie_get_scene\`
- \`movie_get_context\`
- \`movie_get_keyframes\`

Example:

\`\`\`bash
python tools/film_context/film_context.py tool-call movie_search \
  --index-dir .film-context/movie \
  --arguments '{"query":"John pulang ke rumah","top_k":3}'
\`\`\`

Every core response records \`api_used: false\` when relevant. An adapter may later decide whether to send only those compact results to Gemini or another provider.

## Scene notes / future local intelligence

The \`notes\` column is intentionally part of the index now:

\`\`\`bash
python tools/film_context/film_context.py annotate 214 \
  "John enters the house and finds his father missing" \
  --index-dir .film-context/movie
\`\`\`

Later optional local semantic/vision engines can populate these notes or add vector indexes without changing the public tool names. No heavy vision model is bundled in Phase 15.

## Privacy and API budget

The intended escalation policy is:

\`\`\`text
LEVEL 0  Local search only
LEVEL 1  Compact timestamps/dialogue JSON
LEVEL 2  Neighbor scene context
LEVEL 3  A few candidate keyframes
LEVEL 4  Short clip only if a future adapter explicitly needs motion
\`\`\`

The entire source movie is never required as an API prompt.

## Next native integration

The core is intentionally merged before the UI bridge. The next integration layer will:

- add an optional Film Context section in the existing AI Assistant,
- select/build an index without creating a new editor/workspace,
- register the five Film Context tools with the existing agent registry,
- keep the plugin disabled by default,
- keep ChatGPT/AI Edit JSON unchanged,
- hand final edit decisions to the existing native timeline tools.
