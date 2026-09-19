param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('install-deps', 'build', 'install-packager', 'package')]
    [string]$Mode
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

. "$PSScriptRoot\craft-env.ps1"

if (-not $env:CRAFT_BUILD_TYPE) {
    $env:CRAFT_BUILD_TYPE = 'RelWithDebInfo'
}

$craft = Enter-CraftEnvironment
$package = 'kde/kdemultimedia/editaja'

switch ($Mode) {
    'install-deps' {
        $arguments = @('--ci-mode', '--buildtype', $env:CRAFT_BUILD_TYPE, '--use-cache', '--install-deps', $package)
    }
    'build' {
        # Dependencies may use KDE's binary cache, but the modified application
        # itself must always be compiled from our prepared source.
        $arguments = @('--ci-mode', '--buildtype', $env:CRAFT_BUILD_TYPE, '--no-cache', $package)
    }
    'install-packager' {
        $arguments = @('--ci-mode', '--buildtype', $env:CRAFT_BUILD_TYPE, '--use-cache', '--update', 'nsis')
    }
    'package' {
        $arguments = @('--ci-mode', '--buildtype', $env:CRAFT_BUILD_TYPE, '--package', $package)
    }
}

Write-Host "Craft mode: $Mode"
python $craft @arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
