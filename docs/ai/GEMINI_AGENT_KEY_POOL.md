# P5 Gemini-only AI Agent key pool

This document is the continuation contract for the Gemini provider path.

## Product behavior

- P5 AI Agent is intentionally Gemini-only.
- The fixed chat endpoint is the Gemini Developer API OpenAI-compatible endpoint:
  `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`.
- The model field accepts only names beginning with `gemini-`; a stale non-Gemini
  saved model falls back to `gemini-3.8-flash`.
- The UI accepts at most 100 unique API keys in a masked password field.
- Keys are session-only. They are not written to QSettings and are never printed
  in trace output. Only a SHA-256 pool fingerprint is kept as auxiliary state.
- A key is considered ready when it is not known-invalid and its local cooldown
  has expired. Do not probe every key before a request; probing would spend quota.

## Automatic failover

For the active key:

- HTTP 429 is treated as quota/rate limiting.
- HTTP 400/403 is also treated as quota limiting when the response clearly
  contains RESOURCE_EXHAUSTED/quota/rate-limit evidence.
- HTTP 401 or explicit invalid-key/authentication text quarantines that key for
  the current application session.
- Retry-After or Gemini retry-delay hints are honored when available; otherwise
  the affected quota-limited key gets a bounded local cooldown.
- The same model turn is retried on the next ready key without consuming another
  autonomous-agent round.
- Generic network failures and request timeouts do not silently rotate keys.

## Quota boundary

Gemini API rate limits are project-scoped. Multiple API keys belonging to the
same Google Cloud project can share the same project quota. The pool must not
claim that 100 keys equal 100 times the quota. Rotation simply selects another
user-supplied key that still has usable quota.

## Verification

`tests/test_gemini_api_pool_patch.py` checks the repository/build contract.
The reconstructed Qt lifecycle test uses a local HTTP server: key A receives
HTTP 429/RESOURCE_EXHAUSTED and the production agent must retry with key B and
complete. CI uses no real Gemini credential.

Real Gemini cloud behavior and packaged Windows behavior remain separate
verification stages. Never mark them PASS from source/fixture tests alone.
