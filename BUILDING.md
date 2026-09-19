# Building Update P5 Edit Aja

The GitHub Actions workflow is the reference reproducible Windows build for Update P5 Edit Aja.

Build chain:

1. Clone Kdenlive at `c3d8a38c04470f6726b21485fc488f2cd2921654`.
2. Concatenate `patches/phase5.patch.bz2.b64.*`, decode/decompress it, verify SHA-256 `682be7bcb5afd875eb5f347ecd8f644be5fa1273e175c027ddd1d67491ac9a65`, and apply the Phase 5 patch with depth 2.
3. Apply `patches/build-fixes.patch`, then decode `patches/phase6-ai-edit-json.patch.bz2.b64`, verify SHA-256 `975a7c253f125fc5350aec2f835c2eeed0d7c3b2a3cfe5766810d12244985f37`, and apply the native Phase 6 AI Edit JSON UI patch with depth 1.
4. Decode, verify and apply the Phase 12, 13, 14 and 15 patches in that order,
   using the checksums in the Windows workflow. Copy the Film Context backend
   into `data/scripts/filmcontext/film_context.py`.
5. Run `scripts/apply_branding.py`.
6. Bootstrap MinGW Craft and run `scripts/configure_craft.py` against its settings.
   This sets the Qt short-path drive to `Z:/`, enables the binary cache, and
   selects `RelWithDebInfo`. The script preserves unrelated configuration values.
7. Install dependencies from KDE's binary cache, build the modified application
   without using an application cache, install NSIS, then package with Craft.
8. Upload `Update-P5-Edit-Aja-Windows-x64` only after successful packaging.
   Verified corresponding source is uploaded separately as `Update-P5-Edit-Aja-Source`,
   even if compilation fails. A source ZIP is not a runnable Windows application.

The separate Validate Build Configuration workflow checks YAML and PowerShell
syntax and tests settings updates, so malformed build-file edits are reported
even when GitHub cannot start the Windows workflow. Native command failures stop
source reconstruction immediately. The build-fixes patch includes the
ProfileModel reference correction required by the shared Phase 5 source.

Update P5 Edit Aja deliberately keeps several Kdenlive internal names and file extensions
for compatibility with existing projects, effects, translations, QML modules,
and the Phase 5 MCP/API namespace.
