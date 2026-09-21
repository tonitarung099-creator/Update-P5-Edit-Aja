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

function Initialize-SmokeUiNative {
    if (-not ('P5SmokeUiNative' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class P5SmokeUiNative
{
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint flags);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr SendMessageTimeout(
        IntPtr hWnd,
        uint msg,
        UIntPtr wParam,
        IntPtr lParam,
        uint flags,
        uint timeout,
        out UIntPtr result
    );

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int command);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern uint GetDpiForWindow(IntPtr hWnd);
}
'@
    }
    Add-Type -AssemblyName System.Drawing
}

function Wait-SmokeMainWindow {
    param(
        [Parameter(Mandatory = $true)][System.Diagnostics.Process]$Process,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        Assert-SmokeProcessRunning -Process $Process -Stage 'ui_evidence'
        $Process.Refresh()
        if ($Process.MainWindowHandle -ne [IntPtr]::Zero) {
            try { [void]$Process.WaitForInputIdle(5000) } catch {}
            $Process.Refresh()
            if ($Process.MainWindowHandle -ne [IntPtr]::Zero) {
                return $Process.MainWindowHandle
            }
        }
        Start-Sleep -Milliseconds 250
    }

    throw "Packaged application did not expose a main window within $TimeoutSeconds seconds."
}

function Save-SmokeWindowScreenshot {
    param(
        [Parameter(Mandatory = $true)][System.Diagnostics.Process]$Process,
        [Parameter(Mandatory = $true)][string]$Path
    )

    Initialize-SmokeUiNative
    $handle = Wait-SmokeMainWindow -Process $Process
    $rect = New-Object 'P5SmokeUiNative+RECT'
    if (-not [P5SmokeUiNative]::GetWindowRect($handle, [ref]$rect)) {
        throw "Could not read packaged application window bounds. Win32=$([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
    }

    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
    if ($width -lt 200 -or $height -lt 120) {
        throw "Packaged application window bounds are implausible: $width x $height."
    }

    $directory = Split-Path -Parent $Path
    if ($directory) { New-Item -ItemType Directory -Force $directory | Out-Null }

    [void][P5SmokeUiNative]::ShowWindow($handle, 5)
    [void][P5SmokeUiNative]::SetForegroundWindow($handle)
    Start-Sleep -Milliseconds 500

    $bitmap = New-Object System.Drawing.Bitmap $width, $height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $captureMethod = 'PrintWindow'
    try {
        $hdc = $graphics.GetHdc()
        try {
            $printed = [P5SmokeUiNative]::PrintWindow($handle, $hdc, 2)
        }
        finally {
            $graphics.ReleaseHdc($hdc)
        }

        if (-not $printed) {
            $captureMethod = 'CopyFromScreen'
            $graphics.CopyFromScreen(
                $rect.Left,
                $rect.Top,
                0,
                0,
                (New-Object System.Drawing.Size $width, $height)
            )
        }

        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf) -or (Get-Item -LiteralPath $Path).Length -lt 1024) {
        throw "UI screenshot was not created correctly: $Path"
    }

    $dpi = [P5SmokeUiNative]::GetDpiForWindow($handle)
    if ($dpi -eq 0) { $dpi = 96 }

    return [pscustomobject]@{
        path = $Path
        width = $width
        height = $height
        dpi = [int]$dpi
        scale_percent = [Math]::Round(($dpi / 96.0) * 100)
        capture_method = $captureMethod
    }
}

function Measure-SmokeWindowHeartbeat {
    param(
        [Parameter(Mandatory = $true)][System.Diagnostics.Process]$Process,
        [int]$Samples = 8,
        [int]$TimeoutMilliseconds = 1500,
        [int]$SlowThresholdMilliseconds = 500
    )

    Initialize-SmokeUiNative
    $handle = Wait-SmokeMainWindow -Process $Process
    $latencies = @()
    $timeouts = 0

    for ($index = 0; $index -lt $Samples; $index++) {
        Assert-SmokeProcessRunning -Process $Process -Stage 'ui_evidence'
        $result = [UIntPtr]::Zero
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        $sent = [P5SmokeUiNative]::SendMessageTimeout(
            $handle,
            0,
            [UIntPtr]::Zero,
            [IntPtr]::Zero,
            2,
            [uint32]$TimeoutMilliseconds,
            [ref]$result
        )
        $timer.Stop()

        $elapsed = [Math]::Round($timer.Elapsed.TotalMilliseconds, 1)
        if ($sent -eq [IntPtr]::Zero) {
            $timeouts++
            $elapsed = $TimeoutMilliseconds
        }
        $latencies += $elapsed
        Start-Sleep -Milliseconds 100
    }

    $slowSamples = @($latencies | Where-Object { $_ -gt $SlowThresholdMilliseconds }).Count
    $average = if ($latencies.Count -gt 0) {
        [Math]::Round((($latencies | Measure-Object -Average).Average), 1)
    } else { 0 }
    $maximum = if ($latencies.Count -gt 0) {
        [Math]::Round((($latencies | Measure-Object -Maximum).Maximum), 1)
    } else { 0 }

    return [pscustomobject]@{
        scope = 'idle_after_ai_panel_open'
        samples_ms = $latencies
        average_ms = $average
        max_ms = $maximum
        timeout_count = $timeouts
        slow_threshold_ms = $SlowThresholdMilliseconds
        slow_sample_count = $slowSamples
        pass = ($timeouts -eq 0 -and $slowSamples -lt 2)
    }
}

