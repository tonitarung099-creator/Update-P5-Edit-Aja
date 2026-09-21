# Gemini-only built-in AI Agent

This branch intentionally narrows the built-in P5 AI Agent to Google Gemini.

## User-facing behavior

- The API panel no longer exposes a provider/base-URL field.
- The model field accepts Gemini model IDs only (must start with `gemini-`).
- Default model: `gemini-2.5-flash`.
- API keys are pasted one per line.
- At most 100 unique non-empty keys are loaded.
- Keys remain in memory for the current application session and are not written to QSettings by this change.
- Key values are never emitted into the AI trace.

The fixed OpenAI-compatible Gemini endpoint is:

`https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`

## Rotation behavior

For a model turn, the agent starts with the current usable key.

- HTTP 429 / RESOURCE_EXHAUSTED / rate-limit responses mark that key attempted for the current turn.
- `Retry-After` is honored when it contains seconds; otherwise the key receives a 60-second cooldown.
- HTTP 401/403 or API-key-invalid responses disable that key for the current app session.
- If another key is usable, the exact same pending model turn is retried with the next key.
- Key rotation does not increment the agent tool-round counter and does not replay completed editor tools.
- If every configured key is unavailable, the agent stops with an explicit error.

This mechanism does not bypass Google project/account quota. Multiple keys can share the same quota boundary, so rotating keys is useful only when another configured key is actually eligible to serve the request.

## Verification

Repository contract tests verify the fixed Gemini UI/endpoint, 100-key cap, patch order, 429 handling, Retry-After cooldown and secret-safe trace behavior.

The real Qt lifecycle test uses a local HTTP fixture (no cloud key) to prove:

1. request 1 uses key #1;
2. the fixture returns HTTP 429 / RESOURCE_EXHAUSTED;
3. the agent emits a rotation trace and sends request 2 using key #2;
4. request 2 succeeds and the original agent run completes without a failure signal.

Full packaged Windows verification remains separate and must be run after this stacked PR reaches main.
