# Windows build scripts

The Windows workflow is intentionally thin. Each failure domain lives in one
script so fixes can be isolated and reviewed without editing a large YAML file.

| Script | Responsibility |
| --- | --- |
| `reconstruct-source.ps1` | Clone pinned Kdenlive source, apply the patch chain, brand it, verify required P5 features, and archive corresponding source. |
| `bootstrap-craft.ps1` | Download the pinned Craft bootstrap, select MinGW, bootstrap Craft, and apply stable Craft settings. |
| `patch-gettext.ps1` | Apply the MinGW/libxml2 compatibility hotfix to Craft's gettext blueprint. |
| `install-blueprint.ps1` | Copy the prepared Edit Aja Craft blueprint into Craft's KDE blueprint tree. |
| `invoke-craft.ps1` | Run one explicit Craft phase: dependencies, application build, packager install, or package creation. |
| `collect-package.ps1` | Find the produced Windows package and copy runnable artifacts into `artifacts/windows`. |
| `craft-env.ps1` | Shared helper that imports Craft's environment safely. |

Pinned external revisions and patch hashes are stored in
`build/build-manifest.json`. Generated patch inputs are prepared by
`scripts/prepare_build_inputs.py`.

When a build fails, start with the failed GitHub Actions step and edit only the
script responsible for that step. Avoid putting build logic back into
`.github/workflows/build-windows.yml`.


## Packaging image compatibility

`prepare-package-images.ps1 -DependenciesOnly` checks dependency images before
compilation. The full check runs again after compilation, immediately before
Craft packaging, and also requires the application image. Craft's
Windows bootstrap may install toolchain images as `MinSizeRel` while the
application build uses `RelWithDebInfo`. The Craft packager requires an image
directory for every runtime/packaging dependency. Build #51's log confirms
`libs/runtime` installed the MinGW 14.2.0 DLLs in `image-MinSizeRel-14.2.0`,
then packaging looked for `image-RelWithDebInfo-14.2.0`.

The helper permits a temporary directory junction for `libs/runtime` and the
prebuilt MinGW `dev-utils/snoretoast` package, using an exact same-target release
image. SnoreToast must be a `BinaryPackageBase`; a source-built recipe is rejected. Debug images, other versions, missing
application images, and missing images of other dependencies fail explicitly.
It checks all required images before creating any junction. Package exclusions
are initialized in the blueprint constructor so preflight and Craft packaging
use the same dependency set.

Regression tests exercise the dependency traversal and failure paths. The
Windows quality gate also creates a real junction and checks file access,
existing-destination failure, and preservation of the source after removal.
This gate does not replace testing the final installer and application.

## Craft configuration discovery

Build #56 compiled successfully but the external packaging helper searched for
`D:\etc\CraftSettings.ini` instead of the configured installation. The pinned
CraftConfig implementation uses `craftRoot` (the Craft checkout directory) or
the invoked script's location to discover its settings. Neither `CRAFT_ROOT`
nor `KDEROOT` controls that lookup.

The helper validates the installation and sets `craftRoot` before importing
Craft modules. The Windows preflight quality gate now runs the real CLI against
the manifest-pinned Craft checkout, with an isolated configuration and a small
source-only blueprint. It checks external-script invocation, paths with spaces,
a stale locator, and missing settings without downloading the application
dependencies. This tests real Craft initialization, not a mocked configuration.

## Build #60: prebuilt SnoreToast image

Build #60 (`35456970019`) installed SnoreToast 0.7.0 from KDE's prebuilt
MSVC archive during bootstrap. Its post-install log identifies
`image-MinSizeRel-0.7.0`, while packaging requested
`image-RelWithDebInfo-0.7.0`. The pinned Craft configuration fix worked;
preflight stopped because the compatibility exception covered only MinGW's
runtime libraries. No package or application smoke test completed.

The MinGW SnoreToast blueprint copies one upstream binary archive for all
release build types. Reusing that exact-version image preserves its payload;
it does not change or recompile the executable. The guard still rejects Debug,
other versions, unrelated dependencies, and source-built SnoreToast.

The Windows integration test uses the actual pinned Craft dependency resolver,
a BinaryPackageBase fixture, and a real junction. It verifies the fixture
payload is readable, unchanged, and reusable on a second run. It does not claim
to run the actual SnoreToast executable or the final application.

Both the packager installation and dependency-image check now happen before
compiling Edit Aja. The early check skips only the root application image; the
mandatory post-compile check includes it. This catches missing packaging
inputs before spending time on another full application compile.
