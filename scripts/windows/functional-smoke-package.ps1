Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
. "$PSScriptRoot\smoke-test-support.ps1"

$packageRoot = Join-Path (Get-Location) 'artifacts/windows'
$fixtureSource = Join-Path (Get-Location) 'corresponding-source/tests/dataset/av.kdenlive'
if (-not (Test-Path $packageRoot)) {
    throw "Windows package directory not found: $packageRoot"
}
if (-not (Test-Path $fixtureSource -PathType Leaf)) {
    throw "Functional smoke project fixture not found: $fixtureSource"
}

$portableExtractRoot = Join-Path $env:RUNNER_TEMP 'editaja-functional-smoke-portable'
$workRoot = Join-Path $env:RUNNER_TEMP 'editaja-functional-smoke'
$projectPath = Join-Path $workRoot 'input.kdenlive'
$savedProjectPath = Join-Path $workRoot 'saved-copy.kdenlive'
$discoveryPath = Join-Path $env:TEMP 'kdenlive-open-agent.json'

$diagnostics = Join-Path (Get-Location) 'artifacts/smoke/functional'
$uiEvidenceDir = Join-Path $diagnostics 'ui'
$appStdout = Join-Path $env:RUNNER_TEMP 'editaja-functional-stdout.txt'
$appStderr = Join-Path $env:RUNNER_TEMP 'editaja-functional-stderr.txt'
$stage = 'extract'
$status = 'FAIL'
Remove-Item $appStdout, $appStderr -Force -ErrorAction SilentlyContinue

$appProcess = $null

function Invoke-AgentGet {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Token
    )
    return Invoke-RestMethod -Method Get -Uri $Url -Headers @{ Authorization = "Bearer $Token" } -TimeoutSec 20
}

function Invoke-AgentTool {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [Parameter(Mandatory = $true)][string]$Token,
        [Parameter(Mandatory = $true)][string]$Name,
        [hashtable]$Arguments = @{},
        [int]$TimeoutSeconds = 30
    )

    $body = @{ name = $Name; arguments = $Arguments } | ConvertTo-Json -Depth 20 -Compress
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    Write-Host "Native tool call: $Name (timeout ${TimeoutSeconds}s)"
    try {
        $response = Invoke-RestMethod -Method Post -Uri "$BaseUrl/tools/call" -Headers @{ Authorization = "Bearer $Token" } -ContentType 'application/json' -Body $body -TimeoutSec $TimeoutSeconds
    }
    catch {
        $timer.Stop()
        throw "Native tool '$Name' HTTP call failed after $([Math]::Round($timer.Elapsed.TotalSeconds, 1))s: $($_.Exception.Message)"
    }
    $timer.Stop()
    Write-Host "Native tool call complete: $Name in $([Math]::Round($timer.Elapsed.TotalSeconds, 1))s."

    if (-not $response.ok) {
        throw "REST wrapper rejected tool '$Name': $($response | ConvertTo-Json -Depth 20 -Compress)"
    }

    $result = $response.result
    if ($null -eq $result) {
        throw "Tool '$Name' returned no result."
    }

    if (($result.PSObject.Properties.Name -contains 'ok') -and -not $result.ok) {
        throw "Tool '$Name' failed: $($result | ConvertTo-Json -Depth 20 -Compress)"
    }

    return $result
}

function Wait-AgentBridge {
    param(
        [Parameter(Mandatory = $true)][string]$DiscoveryFile,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = $null

    while ((Get-Date) -lt $deadline) {
        Assert-SmokeProcessRunning -Process $appProcess -Stage $stage
        if (Test-Path $DiscoveryFile -PathType Leaf) {
            try {
                $discovery = Get-Content $DiscoveryFile -Raw | ConvertFrom-Json
                if ($discovery.rest_base_url -and $discovery.token) {
                    $ping = Invoke-AgentGet -Url "$($discovery.rest_base_url)/ping" -Token $discovery.token
                    if ($ping.ok -and $ping.result -eq 'pong') {
                        return $discovery
                    }
                }
            }
            catch {
                $lastError = $_
            }
        }
        Start-Sleep -Milliseconds 500
    }

    if ($lastError) {
        throw "AI/REST bridge did not become ready within $TimeoutSeconds seconds. Last error: $lastError"
    }
    throw "AI/REST bridge discovery file did not become ready within $TimeoutSeconds seconds: $DiscoveryFile"
}

function Wait-ProjectLoaded {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [Parameter(Mandatory = $true)][string]$Token,
        [Parameter(Mandatory = $true)][string]$ExpectedPath,
        [int]$TimeoutSeconds = 60
    )

    $expected = [System.IO.Path]::GetFullPath($ExpectedPath)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $last = $null

    while ((Get-Date) -lt $deadline) {
        Assert-SmokeProcessRunning -Process $appProcess -Stage $stage
        try {
            $last = Invoke-AgentTool -BaseUrl $BaseUrl -Token $Token -Name 'kdenlive_get_project_info'
            if ($last.path) {
                $actual = [System.IO.Path]::GetFullPath("$($last.path)")
                if ($actual.Equals($expected, [System.StringComparison]::OrdinalIgnoreCase) -and [int]$last.duration_frames -gt 0) {
                    return $last
                }
            }
        }
        catch {
            $last = $_
        }
        Start-Sleep -Milliseconds 750
    }

    throw "Project did not become ready in the native tool registry. Last state: $($last | Out-String)"
}

try {
    foreach ($path in @($portableExtractRoot, $workRoot)) {
        if (Test-Path $path) {
            Remove-Item $path -Recurse -Force
        }
    }
    New-Item -ItemType Directory -Force $workRoot | Out-Null
    Copy-Item $fixtureSource $projectPath -Force
    Remove-Item $discoveryPath -Force -ErrorAction SilentlyContinue

    $portable = Expand-EditAjaPortable -PackageRoot $packageRoot -DestinationRoot $portableExtractRoot
    $app = $portable.App
    Write-Host "Functional smoke portable root: $($portable.Root)"
    Write-Host "Launching portable editor with functional project: $projectPath"
    $quotedProject = '"' + $projectPath + '"'
    $stage = 'launch'
    $appProcess = Start-Process -FilePath $app -ArgumentList @($quotedProject) -RedirectStandardOutput $appStdout -RedirectStandardError $appStderr -PassThru

    $stage = 'bridge'
    $discovery = Wait-AgentBridge -DiscoveryFile $discoveryPath
    $baseUrl = "$($discovery.rest_base_url)"
    $token = "$($discovery.token)"
    Write-Host "REST bridge PASS: $baseUrl"

    $stage = 'tool_catalog'
    $catalog = Invoke-AgentGet -Url "$baseUrl/tools" -Token $token
    $toolNames = @($catalog.tools | ForEach-Object { "$($_.name)" })
    $requiredTools = @(
        'kdenlive_get_project_info',
        'kdenlive_get_timeline_state',
        'kdenlive_cut_clip',
        'kdenlive_add_subtitle',
        'kdenlive_list_subtitles',
        'kdenlive_save_project',
        'kdenlive_list_panels',
        'kdenlive_open_panel'
    )
    foreach ($required in $requiredTools) {
        if ($toolNames -notcontains $required) {
            throw "Native tool catalog is missing required functional-smoke tool: $required"
        }
    }
    Write-Host "Native tool catalog PASS: $($requiredTools.Count) required tools are present."

    $stage = 'ai_panel'
    $panels = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_list_panels'
    $panelNames = @($panels.panels | ForEach-Object { "$_" })
    if ($panelNames -notcontains 'ai') {
        throw "AI Agent panel is missing from the packaged editor panel catalog: $($panels | ConvertTo-Json -Depth 20 -Compress)"
    }

    $openedPanel = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_open_panel' -Arguments @{ panel_name = 'ai' }
    if ("$($openedPanel.panel)" -ne 'ai') {
        throw "AI Agent panel open verification returned an unexpected result: $($openedPanel | ConvertTo-Json -Depth 20 -Compress)"
    }
    Write-Host 'AI Agent panel PASS: registered and openable through the live packaged editor.'


    $stage = 'ui_evidence'
    New-Item -ItemType Directory -Force $uiEvidenceDir | Out-Null
    $screenshot = Save-SmokeWindowScreenshot -Process $appProcess -Path (Join-Path $uiEvidenceDir 'ai-agent-window.png')
    $heartbeat = Measure-SmokeWindowHeartbeat -Process $appProcess
    $uiEvidence = [ordered]@{
        captured_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        scope = 'packaged portable editor with AI Agent panel open'
        screenshot = $screenshot
        heartbeat = $heartbeat
    }
    $uiEvidence | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $uiEvidenceDir 'ui-evidence.json') -Encoding utf8
    if (-not $heartbeat.pass) {
        throw "Packaged editor UI heartbeat did not meet the idle evidence threshold: $($heartbeat | ConvertTo-Json -Depth 8 -Compress)"
    }
    Write-Host "UI evidence PASS: screenshot=$($screenshot.width)x$($screenshot.height) dpi=$($screenshot.dpi), heartbeat avg=$($heartbeat.average_ms)ms max=$($heartbeat.max_ms)ms."

    $stage = 'window_persistence'
    $boundsBeforeClose = Set-SmokeWindowBounds -Process $appProcess -Left 48 -Top 48 -Width 940 -Height 680
    $beforeRestartScreenshot = Save-SmokeWindowScreenshot -Process $appProcess -Path (Join-Path $uiEvidenceDir 'window-before-restart.png')

    # Close before any timeline/subtitle mutation so no unsaved-project dialog
    # can invalidate the geometry persistence check.
    Close-SmokeWindowGracefully -Process $appProcess
    $appProcess = $null
    Remove-Item $discoveryPath -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 750

    $appProcess = Start-Process -FilePath $app -ArgumentList @($quotedProject) -RedirectStandardOutput $appStdout -RedirectStandardError $appStderr -PassThru
    $discovery = Wait-AgentBridge -DiscoveryFile $discoveryPath
    $baseUrl = "$($discovery.rest_base_url)"
    $token = "$($discovery.token)"

    $boundsAfterRestart = Get-SmokeWindowBounds -Process $appProcess
    $afterRestartScreenshot = Save-SmokeWindowScreenshot -Process $appProcess -Path (Join-Path $uiEvidenceDir 'window-after-restart.png')
    $sizeTolerance = 48
    $positionTolerance = 96
    $windowPersistence = [ordered]@{
        captured_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        scope = 'window_geometry_after_graceful_restart'
        before_close = $boundsBeforeClose
        after_restart = $boundsAfterRestart
        delta = [ordered]@{
            left = [Math]::Abs([int]$boundsAfterRestart.left - [int]$boundsBeforeClose.left)
            top = [Math]::Abs([int]$boundsAfterRestart.top - [int]$boundsBeforeClose.top)
            width = [Math]::Abs([int]$boundsAfterRestart.width - [int]$boundsBeforeClose.width)
            height = [Math]::Abs([int]$boundsAfterRestart.height - [int]$boundsBeforeClose.height)
        }
        tolerance = [ordered]@{
            position_px = $positionTolerance
            size_px = $sizeTolerance
        }
        screenshots = [ordered]@{
            before_restart = $beforeRestartScreenshot.path
            after_restart = $afterRestartScreenshot.path
        }
    }
    $windowPersistence.pass = (
        $windowPersistence.delta.left -le $positionTolerance -and
        $windowPersistence.delta.top -le $positionTolerance -and
        $windowPersistence.delta.width -le $sizeTolerance -and
        $windowPersistence.delta.height -le $sizeTolerance
    )
    $windowPersistence | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $uiEvidenceDir 'window-persistence.json') -Encoding utf8
    if (-not $windowPersistence.pass) {
        throw "Packaged editor window geometry was not restored after a normal restart: $($windowPersistence | ConvertTo-Json -Depth 10 -Compress)"
    }
    Write-Host "Window persistence PASS: before=$($boundsBeforeClose.width)x$($boundsBeforeClose.height)@$($boundsBeforeClose.left),$($boundsBeforeClose.top) after=$($boundsAfterRestart.width)x$($boundsAfterRestart.height)@$($boundsAfterRestart.left),$($boundsAfterRestart.top)."

    $stage = 'project_load'
    $project = Wait-ProjectLoaded -BaseUrl $baseUrl -Token $token -ExpectedPath $projectPath
    Write-Host "Project load PASS: $($project.path), duration=$($project.duration_frames) frames."

    $stage = 'timeline_split'
    $before = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_get_timeline_state' -Arguments @{ include_items = $true }
    $clipsBefore = @($before.items | Where-Object { $_.kind -eq 'clip' -and [int]$_.duration_frames -ge 4 })
    if ($clipsBefore.Count -eq 0) {
        throw "Functional smoke project has no editable timeline clips: $($before | ConvertTo-Json -Depth 20 -Compress)"
    }

    $clip = $clipsBefore | Sort-Object @{ Expression = { [int]$_.duration_frames }; Descending = $true } | Select-Object -First 1
    $cutFrame = [int]$clip.position_frame + [Math]::Floor([int]$clip.duration_frames / 2)
    if ($cutFrame -le [int]$clip.position_frame -or $cutFrame -ge [int]$clip.end_frame) {
        throw "Could not choose a valid cut frame for clip $($clip.id)."
    }

    [void](Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_cut_clip' -Arguments @{ clip_id = [int]$clip.id; position_frame = $cutFrame })

    $afterCut = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_get_timeline_state' -Arguments @{ include_items = $true }
    $clipCountBefore = @($before.items | Where-Object { $_.kind -eq 'clip' }).Count
    $clipCountAfter = @($afterCut.items | Where-Object { $_.kind -eq 'clip' }).Count
    if ($clipCountAfter -le $clipCountBefore) {
        throw "Timeline cut did not increase clip count. Before=$clipCountBefore After=$clipCountAfter"
    }
    Write-Host "Timeline split PASS: clips $clipCountBefore -> $clipCountAfter."

    $stage = 'subtitle_edit'
    $subtitleText = 'P5 functional smoke subtitle'
    [void](Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_add_subtitle' -Arguments @{ text = $subtitleText; start_seconds = 1.0; duration_seconds = 1.5; layer = 0 })

    $subtitles = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_list_subtitles'
    $matchingSubtitle = @($subtitles.subtitles | Where-Object { $_.text -eq $subtitleText })
    if ($matchingSubtitle.Count -ne 1) {
        throw "Subtitle add/list verification failed: $($subtitles | ConvertTo-Json -Depth 20 -Compress)"
    }
    Write-Host 'Subtitle native edit PASS.'

    $stage = 'save_copy'
    # Keep the save-specific timeout while checking that the requested file is
    # actually written. A longer timeout alone does not prove a successful save.
    [void](Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_save_project' -Arguments @{ path = $savedProjectPath; save_copy = $true; overwrite = $true } -TimeoutSeconds 120)
    if (-not (Test-Path $savedProjectPath -PathType Leaf)) {
        throw "Native save tool reported success but project copy was not created: $savedProjectPath"
    }
    if ((Get-Item $savedProjectPath).Length -lt 1024) {
        throw "Saved project copy is unexpectedly small: $((Get-Item $savedProjectPath).Length) bytes"
    }

    $projectAfterSave = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_get_project_info'
    $currentPath = [System.IO.Path]::GetFullPath("$($projectAfterSave.path)")
    $originalPath = [System.IO.Path]::GetFullPath($projectPath)
    if (-not $currentPath.Equals($originalPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "save_copy changed the active project path unexpectedly: $currentPath"
    }

    Write-Host "Project save-copy PASS: $savedProjectPath"
    $status = 'PASS'
    Write-Host 'FUNCTIONAL PORTABLE EDITOR SMOKE PASS: extracted ZIP, REST/native registry, AI Agent panel, project load, timeline split, subtitle edit, and project save-copy.'
}
finally {
    Stop-SmokeProcessTree -Process $appProcess
    try {
        Export-SmokeDiagnostics -Directory $diagnostics -Stage $stage -Status $status -LogPaths @($appStdout, $appStderr) -DiscoveryFile $discoveryPath
    }
    catch { Write-Warning "Could not save smoke diagnostics: $($_.Exception.Message)" }

    foreach ($root in @($portableExtractRoot, $workRoot)) {
        if ($root -and (Test-Path $root)) {
            Remove-Item $root -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    Remove-Item $discoveryPath -Force -ErrorAction SilentlyContinue
}
