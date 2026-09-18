# Building Update P5 Edit Aja

The GitHub Actions workflow is the reference reproducible Windows build for Update P5 Edit Aja.

Build chain:

1. Clone Kdenlive at `c3d8a38c04470f6726b21485fc488f2cd2921654`.
2. Concatenate `patches/phase5.patch.bz2.b64.*`, decode/decompress it, verify SHA-256 `682be7bcb5afd875eb5f347ecd8f644be5fa1273e175c027ddd1d67491ac9a65`, and apply the Phase 5 patch with depth 2.
3. Apply `patches/build-fixes.patch`, then decode `patches/phase6-ai-edit-json.patch.bz2.b64`, verify SHA-256 `975a7c253f125fc5350aec2f835c2eeed0d7c3b2a3cfe5766810d12244985f37`, and apply the native Phase 6 AI Edit JSON UI patch with depth 1.
4. Run `scripts/apply_branding.py`.
5. Build/package with the custom `craft/editaja` KDE Craft blueprint.
6. Upload the installer/package and the exact corresponding-source archive.

Update P5 Edit Aja deliberately keeps several Kdenlive internal names and file extensions
for compatibility with existing projects, effects, translations, QML modules,
and the Phase 5 MCP/API namespace.
