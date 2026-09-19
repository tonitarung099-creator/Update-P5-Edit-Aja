Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

. "$PSScriptRoot\craft-env.ps1"

[void](Enter-CraftEnvironment)

python "$PSScriptRoot\..\prepare_package_images.py" --craft-root $env:CRAFT_ROOT --package kde/kdemultimedia/editaja
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
