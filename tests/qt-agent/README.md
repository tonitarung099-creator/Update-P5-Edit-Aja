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
invalid API JSON still reports failure and restores idle.

This does not compile the full AiAssistantWidget or validate screen geometry,
Windows DPI, native tool cancellation or event-loop responsiveness while a native
handler blocks. Follow `docs/ai/UI_STABILITY_HANDOFF.md` for those tests.
