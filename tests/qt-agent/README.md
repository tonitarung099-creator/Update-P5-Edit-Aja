# Actual Qt agent lifecycle regression

This compiles the reconstructed production OpenAiCompatibleAgent and registry,
not a Python imitation. Requires CMake, a C++17 compiler and Qt6 Core/Network/Test
(`qt6-base-dev` on Ubuntu). It uses a loopback HTTP fixture, no API key or cloud.

```sh
python scripts/reconstruct_source.py --output corresponding-source
cmake -S tests/qt-agent -B build/qt-agent -DP5_SOURCE_DIR="$PWD/corresponding-source"
cmake --build build/qt-agent --parallel 2
ctest --test-dir build/qt-agent --output-on-failure
```

The existing Source / Reconstruction gate runs this suite after reconstruction.
Cases: duplicate Run preserves active busy state and sends one HTTP request;
Cancel/repeated Cancel/restart cannot report stale failure or completion; genuine
invalid API JSON still reports failure and restores idle; a stalled HTTP request
hits the configured deadline, restores idle, and a fresh request succeeds without
stale timeout output; Cancel stops the pending timeout; a Gemini-style 429 response
rotates from the first API key to the second without a cloud call; a delayed asynchronous tool
keeps a Qt heartbeat running before the follow-up API turn; cancelling that tool
prevents stale completion and a fresh request can finish normally.

This does not compile the full AiAssistantWidget or validate screen geometry,
Windows DPI, or the real Film Context process tree inside a packaged Windows app.
It does verify the production AgentToolRegistry/OpenAiCompatibleAgent async job
contract without a cloud API. Follow `docs/ai/UI_STABILITY_HANDOFF.md` for
packaged UI evidence.
