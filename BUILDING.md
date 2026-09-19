# Building Update P5 Edit Aja

The GitHub Actions workflow is the reference reproducible Windows build for
Update P5 Edit Aja. Build logic is deliberately split into small scripts so a
failure can be isolated without repeatedly editing one large workflow file.

## Source and version contract

The single build manifest is `build/build-manifest.json`. It records:

- the exact Kdenlive commit used as the upstream source,
- the exact KDE Craft revision used for Windows builds,
- every compressed P5 patch source and SHA-256,
- the patch application order and strip depth,
- payloads copied into the Craft blueprint.

Do not update a revision or checksum only in the workflow. Update the manifest
and let the validation tests catch any mismatch.

## Build chain

1. `scripts/prepare_build_inputs.py` reconstructs the generated patch files,
   verifies every SHA-256, and stages the Craft blueprint payloads.
2. `scripts/windows/reconstruct-source.ps1` clones the pinned Kdenlive commit,
   applies Phase 5, build fixes, Phase 6, Phase 12, Phase 13, Phase 14 and
   Phase 15 in the manifest order, applies branding, and runs
   `scripts/verify_p5_source.py`.
3. The verified corresponding source is archived independently as
   `artifacts/Update-P5-Edit-Aja-Source.zip`.
4. `scripts/windows/bootstrap-craft.ps1` downloads the bootstrap script from
   the pinned Craft revision, selects MinGW x64, and runs
   `scripts/configure_craft.py`. Craft uses `Z:/` as the short-path drive,
   the binary cache, and `RelWithDebInfo`.
5. `scripts/windows/patch-gettext.ps1` applies the isolated MinGW/libxml2
   gettext compatibility fix.
6. `scripts/windows/install-blueprint.ps1` installs the prepared Edit Aja
   blueprint.
7. `scripts/windows/invoke-craft.ps1` runs four explicit phases:
   `install-deps`, `build`, `install-packager`, and `package`.
   Dependencies may use KDE's binary cache; the modified Edit Aja application
   is always built with `--no-cache`.
8. `scripts/windows/collect-package.ps1` collects the runnable Windows package
   into `artifacts/windows`, with a fallback search if Craft changes its
   package destination query.
9. GitHub Actions uploads `Update-P5-Edit-Aja-Windows-x64` only after
   successful packaging. Verified source is uploaded separately even if a later
   compile or packaging stage fails.

## Debugging rule

Use the failed Actions step as the boundary of the problem:

- source/patch failure -> manifest, `prepare_build_inputs.py`, or
  `reconstruct-source.ps1`;
- Craft bootstrap/configuration failure -> `bootstrap-craft.ps1`;
- gettext/libxml2 failure -> `patch-gettext.ps1` or its Python patcher;
- dependency/build/package failure -> `invoke-craft.ps1` plus the exact Craft
  log for that mode;
- artifact discovery failure -> `collect-package.ps1`.

Avoid adding temporary repair logic directly to
`.github/workflows/build-windows.yml`. Put it in the owning script and add a
validation test when possible.

## Validation before long Windows builds

`Validate Build Configuration` checks the build before the expensive Windows
job:

- Python helper syntax,
- Craft configuration tests,
- manifest revision consistency,
- all compressed patch SHA-256 values,
- Kdenlive blueprint/manifest commit agreement,
- YAML parsing,
- inline workflow PowerShell syntax,
- every `scripts/windows/*.ps1` syntax.

Update P5 Edit Aja deliberately keeps several Kdenlive internal names and the
`.kdenlive` project extension for compatibility with existing projects,
effects, translations, QML modules, and the Phase 5 MCP/API namespace.
