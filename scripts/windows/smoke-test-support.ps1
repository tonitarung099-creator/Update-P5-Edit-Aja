function Expand-EditAjaPortable {
    param(
        [Parameter(Mandatory = $true)][string]$PackageRoot,
        [Parameter(Mandatory = $true)][string]$DestinationRoot
    )

    if (-not (Test-Path -LiteralPath $PackageRoot -PathType Container)) {
        throw "Portable package directory not found: $PackageRoot"
    }

    $archives = @(
        Get-ChildItem -LiteralPath $PackageRoot -File -Filter '*.zip' |
            Where-Object { $_.Name -match '(?i)edit.?aja.*portable|portable.*edit.?aja' } |
            Sort-Object Length -Descending
    )
    if ($archives.Count -eq 0) {
        throw 'No Edit Aja portable ZIP was found in artifacts/windows.'
    }

    if (Test-Path -LiteralPath $DestinationRoot) {
        Remove-Item -LiteralPath $DestinationRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force $DestinationRoot | Out-Null

    $archive = $archives[0]
    Write-Host "Portable smoke archive: $($archive.FullName)"
    Expand-Archive -LiteralPath $archive.FullName -DestinationPath $DestinationRoot -Force

    $apps = @(
        Get-ChildItem -LiteralPath $DestinationRoot -Recurse -File -Filter 'kdenlive.exe' |
            Where-Object { $_.Directory.Name -eq 'bin' } |
            Sort-Object { $_.FullName.Length }
    )
    if ($apps.Count -eq 0) {
        throw 'Portable ZIP extracted successfully but bin\kdenlive.exe was not found.'
    }

    $app = $apps[0]
    $root = $app.Directory.Parent.FullName
    if (Get-ChildItem -LiteralPath $root -Recurse -File -Filter 'uninstall.exe' -ErrorAction SilentlyContinue | Select-Object -First 1) {
        throw 'Portable package unexpectedly contains uninstall.exe.'
    }

    return [pscustomobject]@{
        Archive = $archive.FullName
        Root = $root
        App = $app.FullName
    }
}

function Assert-SmokeProcessRunning {
    param(
        [Parameter(Mandatory = $true)][System.Diagnostics.Process]$Process,
        [Parameter(Mandatory = $true)][string]$Stage
    )
    $Process.Refresh()
    if ($Process.HasExited) {
        throw "Packaged application exited during $Stage with code $($Process.ExitCode)."
    }
}

function Stop-SmokeProcessTree {
    param([System.Diagnostics.Process]$Process)
    if ($null -eq $Process) { return }
    # Cleanup must not replace the original test failure if the process exits
    # between HasExited and taskkill. These processes belong to this CI test.
    $nativeErrorsWereFatal = $PSNativeCommandUseErrorActionPreference
    try {
        $Process.Refresh()
        if ($Process.HasExited) { return }
        $PSNativeCommandUseErrorActionPreference = $false
        & taskkill.exe /PID $Process.Id /T /F | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Smoke-test process cleanup returned code $LASTEXITCODE."
        }
        [void]$Process.WaitForExit(5000)
    }
    catch { Write-Warning "Could not finish smoke-test process cleanup: $($_.Exception.Message)" }
    finally { $PSNativeCommandUseErrorActionPreference = $nativeErrorsWereFatal }
}

function Export-SmokeDiagnostics {
    param(
        [Parameter(Mandatory = $true)][string]$Directory,
        [Parameter(Mandatory = $true)][string]$Stage,
        [Parameter(Mandatory = $true)][ValidateSet('PASS', 'FAIL')][string]$Status,
        [string[]]$LogPaths = @(),
        [string]$DiscoveryFile = ''
    )
    New-Item -ItemType Directory -Force $Directory | Out-Null
    $token = ''
    if ($DiscoveryFile -and (Test-Path -LiteralPath $DiscoveryFile -PathType Leaf)) {
        try {
            $discovery = Get-Content -LiteralPath $DiscoveryFile -Raw | ConvertFrom-Json
            if ($discovery.PSObject.Properties.Name -contains 'token') { $token = [string]$discovery.token }
        }
        catch {
            # Malformed discovery data could contain credentials: keep the
            # stage report, but do not export unredacted application logs.
            $LogPaths = @()
            Write-Warning 'Discovery data could not be parsed; raw logs were not exported.'
        }
    }
    foreach ($path in $LogPaths) {
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            # Get-Content -Raw can yield AutomationNull for a zero-byte file,
            # even through the string cast used here previously. ReadAllText
            # returns an actual empty string so token redaction remains safe.
            $content = [System.IO.File]::ReadAllText((Convert-Path -LiteralPath $path))
            if ($token) { $content = $content.Replace($token, '[REDACTED]') }
            $content = $content -replace '(?i)(Bearer\s+)[A-Za-z0-9._~-]+', '$1[REDACTED]'
            Set-Content -LiteralPath (Join-Path $Directory ([System.IO.Path]::GetFileName($path))) -Value $content -Encoding utf8
        }
    }
    # Never copy the authenticated bridge discovery file into the artifact.
    # workflow_run's GITHUB_SHA can differ from the explicitly checked-out build.
    $commit = (& git rev-parse HEAD).Trim()
    @{ stage = $Stage; status = $Status; run_id = $env:GITHUB_RUN_ID; commit = $commit } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Directory 'result.json') -Encoding utf8
}
