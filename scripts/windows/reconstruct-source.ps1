Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$manifest = Get-Content 'build/build-manifest.json' -Raw | ConvertFrom-Json
$sourceRoot = 'corresponding-source'

if (Test-Path $sourceRoot) {
    Remove-Item -Recurse -Force $sourceRoot
}

git init $sourceRoot
git -C $sourceRoot remote add origin $manifest.upstream.repository
git -C $sourceRoot fetch --depth 1 origin $manifest.upstream.commit
git -C $sourceRoot checkout --detach FETCH_HEAD

foreach ($entry in $manifest.apply_chain) {
    $patchPath = (Resolve-Path $entry.path).Path
    $strip = [int]$entry.strip

    if ($entry.PSObject.Properties.Name -contains 'check' -and $entry.check) {
        git -C $sourceRoot apply --check "-p$strip" $patchPath
    }

    $arguments = @('-C', $sourceRoot, 'apply')
    if ($entry.PSObject.Properties.Name -contains 'ignore_space_change' -and $entry.ignore_space_change) {
        $arguments += '--ignore-space-change'
    }
    $arguments += "-p$strip"
    $arguments += $patchPath

    Write-Host "Applying $($entry.name): $($entry.path)"
    git @arguments
}

$filmContextDir = Join-Path $sourceRoot 'data\scripts\filmcontext'
New-Item -ItemType Directory -Force $filmContextDir | Out-Null
Copy-Item 'tools/film_context/film_context.py' (Join-Path $filmContextDir 'film_context.py') -Force

python scripts/apply_branding.py $sourceRoot --assets branding
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python scripts/verify_p5_source.py $sourceRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

New-Item -ItemType Directory -Force artifacts | Out-Null
Remove-Item -Recurse -Force (Join-Path $sourceRoot '.git')

$archive = 'artifacts/Update-P5-Edit-Aja-Source.zip'
if (Test-Path $archive) {
    Remove-Item -Force $archive
}
Compress-Archive -Path "$sourceRoot/*" -DestinationPath $archive -CompressionLevel Optimal

Write-Host "Verified corresponding source archive: $archive"
