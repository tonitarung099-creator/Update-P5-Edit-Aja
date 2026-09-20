Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$packageRoot = Join-Path (Get-Location) 'artifacts/windows'
if (-not (Test-Path $packageRoot)) {
    throw "Windows package directory not found: $packageRoot"
}

$installers = @(
    Get-ChildItem $packageRoot -File -Filter '*.exe' |
        Where-Object { $_.Name -match 'edit.?aja' } |
        Sort-Object Length -Descending
)
if ($installers.Count -eq 0) {
    throw 'No Edit Aja NSIS installer was found in artifacts/windows.'
}

# Craft can emit companion package files. Prefer the largest matching EXE,
# which is the NSIS installer containing the application payload.
$installer = $installers[0]
$installRoot = Join-Path $env:RUNNER_TEMP 'editaja-packaged-app-smoke'
$stdout = Join-Path $env:RUNNER_TEMP 'editaja-version-stdout.txt'
$stderr = Join-Path $env:RUNNER_TEMP 'editaja-version-stderr.txt'

if (Test-Path $installRoot) {
    Remove-Item $installRoot -Recurse -Force
}
Remove-Item $stdout, $stderr -Force -ErrorAction SilentlyContinue

$appProcess = $null

function Stop-SmokeProcessTree {
    param([System.Diagnostics.Process]$Process)

    if ($null -eq $Process -or $Process.HasExited) {
        return
    }

    # Kdenlive can create helper processes. Kill the whole CI-only process tree.
    & taskkill.exe /PID $Process.Id /T /F | Out-Host
}

try {
    Write-Host "Smoke installer: $($installer.FullName)"
    Write-Host "Smoke install root: $installRoot"

    # The pinned Craft NSIS template enables MULTIUSER_INSTALLMODE_COMMANDLINE.
    # /CurrentUser avoids an elevation requirement in the hosted runner.
    # NSIS requires /D= to be the final argument and the path is intentionally
    # chosen without spaces so Start-Process cannot change its parsing.
    $install = Start-Process -FilePath $installer.FullName -ArgumentList @('/S', '/CurrentUser', "/D=$installRoot") -PassThru -Wait
    if ($install.ExitCode -ne 0) {
        throw "Silent installer exited with code $($install.ExitCode)."
    }

    $app = Join-Path $installRoot 'bin/kdenlive.exe'
    $uninstaller = Join-Path $installRoot 'uninstall.exe'
    if (-not (Test-Path $app -PathType Leaf)) {
        throw "Installed application executable not found: $app"
    }
    if (-not (Test-Path $uninstaller -PathType Leaf)) {
        throw "Installed uninstaller not found: $uninstaller"
    }

    Write-Host 'Installer PASS: packaged application files are present.'

    # --version initializes the packaged executable and its DLL search path, but
    # exits without requiring GUI interaction. Missing runtime DLLs surface here
    # as a non-zero process exit instead of being mistaken for packaging success.
    $version = Start-Process -FilePath $app -ArgumentList @('--version') -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

    if (-not $version.WaitForExit(30000)) {
        Stop-SmokeProcessTree -Process $version
        throw 'Packaged application --version did not exit within 30 seconds.'
    }

    $versionOut = if (Test-Path $stdout) { Get-Content $stdout -Raw } else { '' }
    $versionErr = if (Test-Path $stderr) { Get-Content $stderr -Raw } else { '' }
    if ($version.ExitCode -ne 0) {
        throw "Packaged application --version failed with code $($version.ExitCode).\nSTDOUT:\n$versionOut\nSTDERR:\n$versionErr"
    }
    Write-Host "Executable probe PASS. Output: $($versionOut.Trim())"

    # A successful version probe is not enough to prove GUI startup. Launch the
    # packaged application normally and require it to remain alive long enough
    # to rule out an immediate startup/runtime crash.
    $appProcess = Start-Process -FilePath $app -PassThru
    Start-Sleep -Seconds 15
    $appProcess.Refresh()
    if ($appProcess.HasExited) {
        throw "Packaged application exited during the 15-second startup smoke test with code $($appProcess.ExitCode)."
    }

    Write-Host 'Packaged-app startup smoke PASS: process remained alive for 15 seconds.'
}
finally {
    Stop-SmokeProcessTree -Process $appProcess

    $uninstaller = Join-Path $installRoot 'uninstall.exe'
    if (Test-Path $uninstaller -PathType Leaf) {
        Write-Host 'Running silent smoke-test uninstall.'
        $uninstall = Start-Process -FilePath $uninstaller -ArgumentList @('/S', "_?=$installRoot") -PassThru -Wait
        if ($uninstall.ExitCode -ne 0) {
            Write-Warning "Smoke-test uninstaller exited with code $($uninstall.ExitCode)."
        }
    }

    if (Test-Path $installRoot) {
        Remove-Item $installRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
