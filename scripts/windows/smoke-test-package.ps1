Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
. "$PSScriptRoot\smoke-test-support.ps1"

$packageRoot = Join-Path (Get-Location) 'artifacts/windows'
$portableExtractRoot = Join-Path $env:RUNNER_TEMP 'editaja-portable-startup-smoke'
$stdout = Join-Path $env:RUNNER_TEMP 'editaja-version-stdout.txt'
$stderr = Join-Path $env:RUNNER_TEMP 'editaja-version-stderr.txt'
$appStdout = Join-Path $env:RUNNER_TEMP 'editaja-startup-stdout.txt'
$appStderr = Join-Path $env:RUNNER_TEMP 'editaja-startup-stderr.txt'
$diagnostics = Join-Path (Get-Location) 'artifacts/smoke/startup'

Remove-Item $stdout, $stderr, $appStdout, $appStderr -Force -ErrorAction SilentlyContinue

$stage = 'extract'
$status = 'FAIL'
$appProcess = $null

try {
    $portable = Expand-EditAjaPortable -PackageRoot $packageRoot -DestinationRoot $portableExtractRoot
    $app = $portable.App

    Write-Host "Portable root: $($portable.Root)"
    Write-Host "Portable executable: $app"

    # --version exercises the executable and packaged DLL search path without
    # requiring GUI interaction. Missing runtime DLLs fail here.
    $stage = 'version'
    $version = Start-Process -FilePath $app -ArgumentList @('--version') -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    if (-not $version.WaitForExit(30000)) {
        Stop-SmokeProcessTree -Process $version
        throw 'Portable application --version did not exit within 30 seconds.'
    }

    $versionOut = if (Test-Path $stdout) { Get-Content $stdout -Raw } else { '' }
    $versionErr = if (Test-Path $stderr) { Get-Content $stderr -Raw } else { '' }
    if ($version.ExitCode -ne 0) {
        throw "Portable application --version failed with code $($version.ExitCode).\nSTDOUT:\n$versionOut\nSTDERR:\n$versionErr"
    }
    Write-Host "Portable executable probe PASS. Output: $($versionOut.Trim())"

    # Launch directly from the extracted ZIP. No installer, registry key,
    # Start-menu shortcut or uninstall path is involved.
    $stage = 'startup'
    $appProcess = Start-Process -FilePath $app -RedirectStandardOutput $appStdout -RedirectStandardError $appStderr -PassThru
    for ($second = 0; $second -lt 15; $second++) {
        Start-Sleep -Seconds 1
        Assert-SmokeProcessRunning -Process $appProcess -Stage $stage
    }

    $status = 'PASS'
    Write-Host 'PORTABLE STARTUP SMOKE PASS: extracted ZIP launched directly and remained alive for 15 seconds.'
}
finally {
    Stop-SmokeProcessTree -Process $appProcess
    try {
        Export-SmokeDiagnostics -Directory $diagnostics -Stage $stage -Status $status -LogPaths @($stdout, $stderr, $appStdout, $appStderr) -DiscoveryFile (Join-Path $env:TEMP 'kdenlive-open-agent.json')
    }
    catch { Write-Warning "Could not save smoke diagnostics: $($_.Exception.Message)" }

    if (Test-Path -LiteralPath $portableExtractRoot) {
        Remove-Item -LiteralPath $portableExtractRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
