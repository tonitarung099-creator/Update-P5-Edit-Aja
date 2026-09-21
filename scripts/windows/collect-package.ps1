Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\craft-env.ps1"

if (-not $env:CRAFT_BUILD_TYPE) {
    $env:CRAFT_BUILD_TYPE = 'RelWithDebInfo'
}

$artifactRoot = Join-Path (Get-Location) 'artifacts/windows'
New-Item -ItemType Directory -Force $artifactRoot | Out-Null
Get-ChildItem $artifactRoot -File -ErrorAction SilentlyContinue | Remove-Item -Force

$craft = Enter-CraftEnvironment

# PortablePackager writes into Craft's normal package destination. Query it
# first, then fall back to CraftRoot only if Craft changes this helper.
$previousNativePreference = $PSNativeCommandUseErrorActionPreference
$PSNativeCommandUseErrorActionPreference = $false
$packageDirOutput = & python $craft --ci-mode --buildtype $env:CRAFT_BUILD_TYPE -q --get 'packageDestinationDir()' virtual/base 2>$null
$queryExitCode = $LASTEXITCODE
$PSNativeCommandUseErrorActionPreference = $previousNativePreference

$searchRoots = @()
if ($queryExitCode -eq 0 -and $packageDirOutput) {
    $packageDir = "$($packageDirOutput | Select-Object -Last 1)".Trim()
    if ($packageDir -and (Test-Path $packageDir)) {
        Write-Host "Craft package directory: $packageDir"
        $searchRoots += $packageDir
    }
}
if (Test-Path $env:CRAFT_ROOT) {
    $searchRoots += $env:CRAFT_ROOT
}

$portable = $null
foreach ($root in ($searchRoots | Select-Object -Unique)) {
    $portable = Get-ChildItem $root -Recurse -File -Filter '*.zip' -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match 'edit.?aja' -and
            $_.Name -notmatch '(?i)(-src|-logs|-dbg)'
        } |
        Sort-Object Length -Descending |
        Select-Object -First 1
    if ($portable) { break }
}

if (-not $portable) {
    throw 'No portable Edit Aja ZIP was produced by Craft.'
}

$portableName = 'Update-P5-Edit-Aja-Portable-Windows-x64.zip'
$destination = Join-Path $artifactRoot $portableName
Copy-Item $portable.FullName $destination -Force

$hash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $portableName" | Set-Content -LiteralPath "$destination.sha256" -Encoding ascii

Write-Host "Portable source: $($portable.FullName)"
Write-Host "Portable artifact: $destination"
Write-Host "SHA-256: $hash"
Get-ChildItem $artifactRoot -File | Format-Table Name, Length

if (Get-ChildItem $artifactRoot -File -Filter '*.exe' -ErrorAction SilentlyContinue) {
    throw 'Portable artifact directory unexpectedly contains an installer EXE.'
}

$global:LASTEXITCODE = 0
