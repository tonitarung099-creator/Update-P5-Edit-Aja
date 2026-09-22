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
$renderOutputPath = Join-Path $workRoot 'render-smoke.mp4'
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


function Wait-ActionCheckedState {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [Parameter(Mandatory = $true)][string]$Token,
        [Parameter(Mandatory = $true)][string]$ActionName,
        [Parameter(Mandatory = $true)][bool]$ExpectedChecked,
        [int]$TimeoutSeconds = 5
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $last = $null
    while ((Get-Date) -lt $deadline) {
        $last = Invoke-AgentTool -BaseUrl $BaseUrl -Token $Token -Name 'kdenlive_get_action_state' -Arguments @{ action_name = $ActionName }
        if ([bool]$last.checked -eq $ExpectedChecked) {
            return $last
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Action '$ActionName' did not reach checked=$ExpectedChecked within $TimeoutSeconds seconds. Last state: $($last | ConvertTo-Json -Depth 10 -Compress)"
}

function Wait-RenderFinished {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [Parameter(Mandatory = $true)][string]$Token,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [int]$TimeoutSeconds = 240
    )

    $expectedLeaf = [System.IO.Path]::GetFileName($OutputPath)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $last = $null

    while ((Get-Date) -lt $deadline) {
        Assert-SmokeProcessRunning -Process $appProcess -Stage $stage
        $last = Invoke-AgentTool -BaseUrl $BaseUrl -Token $Token -Name 'kdenlive_render_status'
        $job = @($last.jobs | Where-Object {
            $_.output_file -and [System.IO.Path]::GetFileName("$($_.output_file)") -eq $expectedLeaf
        } | Select-Object -Last 1)

        if ($job.Count -gt 0) {
            $state = "$($job[0].status)"
            if ($state -eq 'finished') {
                return [pscustomobject]@{ status = $last; job = $job[0] }
            }
            if ($state -in @('failed', 'aborted')) {
                throw "Render job ended in state '$state': $($job[0] | ConvertTo-Json -Depth 10 -Compress)"
            }
        }
        Start-Sleep -Seconds 1
    }

    throw "Render did not finish within $TimeoutSeconds seconds. Last state: $($last | ConvertTo-Json -Depth 20 -Compress)"
}

function Test-PackagedRenderedMedia {
    param(
        [Parameter(Mandatory = $true)][string]$PortableRoot,
        [Parameter(Mandatory = $true)][string]$MediaPath
    )

    if (-not (Test-Path $MediaPath -PathType Leaf)) {
        throw "Rendered media was not created: $MediaPath"
    }
    $media = Get-Item $MediaPath
    if ($media.Length -lt 4096) {
        throw "Rendered media is unexpectedly small: $($media.Length) bytes"
    }

    $ffmpeg = Get-ChildItem -LiteralPath $PortableRoot -Recurse -File -Filter 'ffmpeg.exe' -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $ffmpeg) {
        throw "Portable package does not contain ffmpeg.exe, so rendered-media decode cannot be verified self-contained."
    }

    $decodeStdout = Join-Path $env:RUNNER_TEMP 'editaja-render-decode-stdout.txt'
    $decodeStderr = Join-Path $env:RUNNER_TEMP 'editaja-render-decode-stderr.txt'
    Remove-Item $decodeStdout, $decodeStderr -Force -ErrorAction SilentlyContinue

    $decode = Start-Process -FilePath $ffmpeg.FullName -ArgumentList @(
        '-hide_banner',
        '-loglevel', 'error',
        '-i', $MediaPath,
        '-map', '0:v:0?',
        '-map', '0:a:0?',
        '-f', 'null',
        'NUL'
    ) -RedirectStandardOutput $decodeStdout -RedirectStandardError $decodeStderr -PassThru -Wait

    $stderr = if (Test-Path $decodeStderr) { Get-Content $decodeStderr -Raw } else { '' }
    if ($decode.ExitCode -ne 0) {
        throw "Packaged FFmpeg could not decode rendered media (exit $($decode.ExitCode)): $stderr"
    }

    return [pscustomobject]@{
        decoder = $ffmpeg.FullName
        output_path = $media.FullName
        output_size_bytes = [int64]$media.Length
        decode_exit_code = [int]$decode.ExitCode
        decode_stderr = $stderr.Trim()
    }
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
        'kdenlive_open_panel',
        'kdenlive_get_action_state',
        'kdenlive_set_action_checked',
        'kdenlive_get_track_state',
        'kdenlive_set_track_state',
        'kdenlive_list_guides',
        'kdenlive_add_guide',
        'kdenlive_edit_guide',
        'kdenlive_delete_guide'
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

    $stage = 'full_editor_action_state'
    $testActionName = 'audiomixer_button'
    $actionBefore = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_get_action_state' -Arguments @{ action_name = $testActionName }
    if (-not [bool]$actionBefore.checkable) {
        throw "Full Editor Control smoke action is unexpectedly not checkable: $($actionBefore | ConvertTo-Json -Depth 10 -Compress)"
    }
    if (-not [bool]$actionBefore.enabled) {
        throw "Full Editor Control smoke action is unexpectedly disabled: $($actionBefore | ConvertTo-Json -Depth 10 -Compress)"
    }

    $originalChecked = [bool]$actionBefore.checked
    $targetChecked = -not $originalChecked
    $setAction = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_set_action_checked' -Arguments @{ action_name = $testActionName; checked = $targetChecked }
    $actionChanged = Wait-ActionCheckedState -BaseUrl $baseUrl -Token $token -ActionName $testActionName -ExpectedChecked $targetChecked

    [void](Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_set_action_checked' -Arguments @{ action_name = $testActionName; checked = $originalChecked })
    $actionRestored = Wait-ActionCheckedState -BaseUrl $baseUrl -Token $token -ActionName $testActionName -ExpectedChecked $originalChecked

    $actionEvidence = [ordered]@{
        action = $testActionName
        before = $actionBefore
        requested_checked = $targetChecked
        setter_result = $setAction
        changed_state = $actionChanged
        restored_state = $actionRestored
        pass = ([bool]$actionChanged.checked -eq $targetChecked -and [bool]$actionRestored.checked -eq $originalChecked)
    }
    New-Item -ItemType Directory -Force $diagnostics | Out-Null
    $actionEvidence | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath (Join-Path $diagnostics 'full-editor-action-state.json') -Encoding utf8
    if (-not $actionEvidence.pass) {
        throw "Full Editor Control action state round trip failed: $($actionEvidence | ConvertTo-Json -Depth 15 -Compress)"
    }
    Write-Host "Full Editor Control action-state PASS: $testActionName $originalChecked -> $targetChecked -> $originalChecked."

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

    # The REST bridge can become ready before the fully restored editor window
    # replaces transient startup/render windows. Wait for the reopened project
    # to be visible through the native registry before measuring geometry.
    $project = Wait-ProjectLoaded -BaseUrl $baseUrl -Token $token -ExpectedPath $projectPath
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
    Write-Host "Project load PASS after restart: $($project.path), duration=$($project.duration_frames) frames."

    $stage = 'full_editor_track_state'
    $trackTimeline = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_get_timeline_state' -Arguments @{ include_items = $false }
    $trackCandidates = @($trackTimeline.tracks)
    if ($trackCandidates.Count -lt 1) {
        throw "Functional smoke project has no timeline track for Full Editor Control track-state verification."
    }

    $trackId = [int]$trackCandidates[0].id
    $trackBefore = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_get_track_state' -Arguments @{ track_id = $trackId }
    $originalLocked = [bool]$trackBefore.locked
    $targetLocked = -not $originalLocked

    $trackSet = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_set_track_state' -Arguments @{
        track_id = $trackId
        locked = $targetLocked
    }
    $trackChanged = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_get_track_state' -Arguments @{ track_id = $trackId }
    if ([bool]$trackChanged.locked -ne $targetLocked) {
        throw "Track-state set/readback verification failed: $($trackChanged | ConvertTo-Json -Depth 12 -Compress)"
    }

    [void](Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_set_track_state' -Arguments @{
        track_id = $trackId
        locked = $originalLocked
    })
    $trackRestored = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_get_track_state' -Arguments @{ track_id = $trackId }
    if ([bool]$trackRestored.locked -ne $originalLocked) {
        throw "Track-state restore verification failed: $($trackRestored | ConvertTo-Json -Depth 12 -Compress)"
    }

    $trackStateEvidence = [ordered]@{
        track_id = $trackId
        before = $trackBefore
        requested_locked = $targetLocked
        setter_result = $trackSet
        changed_state = $trackChanged
        restored_state = $trackRestored
        pass = ([bool]$trackChanged.locked -eq $targetLocked -and [bool]$trackRestored.locked -eq $originalLocked)
    }
    New-Item -ItemType Directory -Force $diagnostics | Out-Null
    $trackStateEvidence | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath (Join-Path $diagnostics 'full-editor-track-state.json') -Encoding utf8
    Write-Host "Full Editor Control track-state PASS: track $trackId locked $originalLocked -> $targetLocked -> $originalLocked."

    $stage = 'full_editor_guides'
    $guidesBefore = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_list_guides'
    $occupiedGuideFrames = @{}
    foreach ($guide in @($guidesBefore.guides)) {
        $occupiedGuideFrames[[int]$guide.position_frame] = $true
    }

    $guideFrame = $null
    $editedGuideFrame = $null
    $guideSearchLimit = [Math]::Min(100, [Math]::Max(10, [int]$project.duration_frames - 20))
    for ($candidate = 5; $candidate -lt $guideSearchLimit; $candidate += 5) {
        $movedCandidate = $candidate + 2
        if (-not $occupiedGuideFrames.ContainsKey($candidate) -and -not $occupiedGuideFrames.ContainsKey($movedCandidate)) {
            $guideFrame = $candidate
            $editedGuideFrame = $movedCandidate
            break
        }
    }
    if ($null -eq $guideFrame -or $null -eq $editedGuideFrame) {
        throw "Could not find two free guide frames in the functional smoke project."
    }

    $guideComment = 'P5 functional smoke guide'
    $editedGuideComment = 'P5 functional smoke guide edited'
    $guideAdd = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_add_guide' -Arguments @{
        position_frame = [int]$guideFrame
        comment = $guideComment
    }

    $guidesAfterAdd = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_list_guides'
    $addedGuide = @($guidesAfterAdd.guides | Where-Object {
        [int]$_.position_frame -eq [int]$guideFrame -and $_.comment -eq $guideComment
    })
    if ($addedGuide.Count -ne 1 -or [bool]$addedGuide[0].has_range) {
        throw "Point guide add/list verification failed: $($guidesAfterAdd | ConvertTo-Json -Depth 20 -Compress)"
    }

    $guideEdit = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_edit_guide' -Arguments @{
        position_frame = [int]$guideFrame
        new_position_frame = [int]$editedGuideFrame
        comment = $editedGuideComment
        duration_frames = 10
    }

    $guidesAfterEdit = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_list_guides'
    $oldGuideStillPresent = @($guidesAfterEdit.guides | Where-Object { [int]$_.position_frame -eq [int]$guideFrame })
    $editedGuide = @($guidesAfterEdit.guides | Where-Object {
        [int]$_.position_frame -eq [int]$editedGuideFrame -and $_.comment -eq $editedGuideComment
    })
    if ($oldGuideStillPresent.Count -ne 0 -or $editedGuide.Count -ne 1 -or -not [bool]$editedGuide[0].has_range -or [int]$editedGuide[0].duration_frames -ne 10) {
        throw "Guide edit/move/range verification failed: $($guidesAfterEdit | ConvertTo-Json -Depth 20 -Compress)"
    }

    $guideDelete = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_delete_guide' -Arguments @{
        position_frame = [int]$editedGuideFrame
    }
    $guidesAfterDelete = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_list_guides'
    $deletedGuideStillPresent = @($guidesAfterDelete.guides | Where-Object {
        [int]$_.position_frame -eq [int]$editedGuideFrame -and $_.comment -eq $editedGuideComment
    })
    if ($deletedGuideStillPresent.Count -ne 0) {
        throw "Guide delete verification failed: $($guidesAfterDelete | ConvertTo-Json -Depth 20 -Compress)"
    }

    $guideEvidence = [ordered]@{
        selected_frame = [int]$guideFrame
        edited_frame = [int]$editedGuideFrame
        before = $guidesBefore
        add_result = $guideAdd
        after_add = $guidesAfterAdd
        edit_result = $guideEdit
        after_edit = $guidesAfterEdit
        delete_result = $guideDelete
        after_delete = $guidesAfterDelete
        pass = $true
    }
    New-Item -ItemType Directory -Force $diagnostics | Out-Null
    $guideEvidence | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $diagnostics 'full-editor-guides.json') -Encoding utf8
    Write-Host "Full Editor Control guide round-trip PASS: point@$guideFrame -> range@$editedGuideFrame -> deleted."

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

    $stage = 'fresh_reopen_saved_copy'
    # save_copy intentionally leaves the original project marked modified. A
    # normal WM_CLOSE would therefore open a save-changes dialog and invalidate
    # this headless persistence check. The copy has already been written and
    # verified above, so terminate only this disposable CI process before
    # reopening the saved copy in a fresh process. Geometry persistence was
    # already proven earlier through the normal graceful-close path.
    Stop-SmokeProcessTree -Process $appProcess
    $appProcess.Refresh()
    if (-not $appProcess.HasExited) {
        throw "Disposable editor process did not exit before fresh saved-copy reopen."
    }
    $appProcess = $null
    Remove-Item $discoveryPath -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 750

    $quotedSavedProject = '"' + $savedProjectPath + '"'
    $appProcess = Start-Process -FilePath $app -ArgumentList @($quotedSavedProject) -RedirectStandardOutput $appStdout -RedirectStandardError $appStderr -PassThru
    $discovery = Wait-AgentBridge -DiscoveryFile $discoveryPath
    $baseUrl = "$($discovery.rest_base_url)"
    $token = "$($discovery.token)"
    $savedProject = Wait-ProjectLoaded -BaseUrl $baseUrl -Token $token -ExpectedPath $savedProjectPath

    $reopenedTimeline = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_get_timeline_state' -Arguments @{ include_items = $true }
    $reopenedClipCount = @($reopenedTimeline.items | Where-Object { $_.kind -eq 'clip' }).Count
    if ($reopenedClipCount -ne $clipCountAfter) {
        throw "Fresh-process reopen did not preserve timeline edit count. Expected=$clipCountAfter Actual=$reopenedClipCount"
    }

    $reopenedSubtitles = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_list_subtitles'
    $reopenedMatchingSubtitle = @($reopenedSubtitles.subtitles | Where-Object { $_.text -eq $subtitleText })
    if ($reopenedMatchingSubtitle.Count -ne 1) {
        throw "Fresh-process reopen did not preserve the functional-smoke subtitle: $($reopenedSubtitles | ConvertTo-Json -Depth 20 -Compress)"
    }
    Write-Host "Fresh-process reopen PASS: clips=$reopenedClipCount subtitle='$subtitleText'."

    $stage = 'render_export'
    $renderRequest = Invoke-AgentTool -BaseUrl $baseUrl -Token $token -Name 'kdenlive_render' -Arguments @{
        output_path = $renderOutputPath
        preset = 'MP4-H264/AAC'
        start_seconds = 0.0
        end_seconds = 2.5
        embed_subtitles = $true
        use_proxy = $false
        two_pass = $false
        overwrite = $true
    } -TimeoutSeconds 60
    if (@($renderRequest.jobs).Count -lt 1) {
        throw "Render tool reported success but queued no jobs: $($renderRequest | ConvertTo-Json -Depth 20 -Compress)"
    }

    $renderFinished = Wait-RenderFinished -BaseUrl $baseUrl -Token $token -OutputPath $renderOutputPath -TimeoutSeconds 240

    $stage = 'render_decode'
    $decodeEvidence = Test-PackagedRenderedMedia -PortableRoot $portable.Root -MediaPath $renderOutputPath
    New-Item -ItemType Directory -Force $diagnostics | Out-Null
    $renderEvidence = [ordered]@{
        captured_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        saved_project_path = $savedProject.path
        reopened_clip_count = $reopenedClipCount
        subtitle_text = $subtitleText
        render_request = $renderRequest
        render_status = $renderFinished.status
        render_job = $renderFinished.job
        decode = $decodeEvidence
        pass = $true
    }
    $renderEvidence | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $diagnostics 'render-evidence.json') -Encoding utf8
    Write-Host "Render/decode PASS: $($decodeEvidence.output_path) ($($decodeEvidence.output_size_bytes) bytes)."

    $status = 'PASS'
    Write-Host 'FUNCTIONAL PORTABLE EDITOR SMOKE PASS: extracted ZIP, REST/native registry, AI Agent panel, deterministic QAction state control, deterministic track-state control, project guide round-trip, project load, timeline split, subtitle edit, project save-copy, fresh-process reopen, render/export, and packaged-media decode.'
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
