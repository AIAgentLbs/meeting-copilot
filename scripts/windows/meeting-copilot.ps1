$ErrorActionPreference='Stop'
$check=$args -contains '--check'
if(@($args|Where-Object {$_ -notin @('--check','--no-open','--refresh')}).Count){throw 'Usage: meeting-copilot.ps1 [--check|--no-open|--refresh]'}
$root=$PSScriptRoot
$capture=Join-Path $root 'capture\MeetingCopilotCapture.exe'
$python=Join-Path $root 'python\python.exe'
$pythonw=Join-Path $root 'python\pythonw.exe'
$server=Join-Path $root 'web\server.py'
$config=Join-Path $env:USERPROFILE '.config\meeting-copilot'
$data=Join-Path $env:USERPROFILE '.local\share\meeting-copilot'
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
function Stop-OtherVersions([string]$Root,[string]$UserHome){
    # MEETONTRACK-65: an update leaves the previous version's server and capture running.
    # Stop only our own processes from another versions\<v> folder. Keep a capture that owns a
    # recording marker (written before recording starts), and every capture when a marker is
    # unreadable or the live transcript says a recording is on. Same text in install.ps1 and
    # meeting-copilot.ps1: the installer may unpack a package whose launcher predates this.
    $versions=(Split-Path $Root -Parent).TrimEnd('\')+'\'
    $own=$Root.TrimEnd('\')+'\'
    $data=Join-Path $UserHome '.local\share\meeting-copilot'
    $roots=@((Join-Path $UserHome 'MeetOnTrack Recordings'),(Join-Path $UserHome 'Recordings'),(Join-Path $data 'recordings'))
    try {$chosen=[string](Get-Content (Join-Path $UserHome '.config\meeting-copilot\config.json') -Raw -Encoding UTF8|ConvertFrom-Json).recordings_dir; if($chosen){$roots+=$chosen}} catch {}
    $owners=@(); $keepCaptures=$false
    foreach($folder in @($roots|Where-Object {Test-Path -LiteralPath $_ -PathType Container}|ForEach-Object {Get-ChildItem -LiteralPath $_ -Directory -ErrorAction SilentlyContinue})){
        $marker=Join-Path $folder.FullName '.recording.json'
        if(Test-Path -LiteralPath $marker){try {$owners+=[int](Get-Content -LiteralPath $marker -Raw -Encoding UTF8|ConvertFrom-Json).pid} catch {$keepCaptures=$true}}
    }
    try {if((Get-Content (Join-Path $data 'meeting-copilot-live.json') -Raw -Encoding UTF8|ConvertFrom-Json).status -in @('recording','paused','loading','overloaded')){$keepCaptures=$true}} catch {}
    $old=@(Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe' OR Name='MeetingCopilotCapture.exe'" | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.StartsWith($versions,'OrdinalIgnoreCase') -and -not $_.ExecutablePath.StartsWith($own,'OrdinalIgnoreCase') -and
        -not ($_.Name -eq 'MeetingCopilotCapture.exe' -and ($keepCaptures -or $_.ProcessId -in $owners))})
    foreach($process in $old){Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue}
    if($old.Count){Wait-Process -Id $old.ProcessId -Timeout 10 -ErrorAction SilentlyContinue}
    if(@($old|Where-Object {$_.Name -ne 'MeetingCopilotCapture.exe'}).Count){
        for($i=0;$i -lt 40 -and @(Get-NetTCPConnection -LocalPort 43121 -State Listen -ErrorAction SilentlyContinue).Count;$i++){Start-Sleep -Milliseconds 250}
    }
}
$release=[string](Get-Content (Join-Path $root 'release.json') -Raw -Encoding UTF8 | ConvertFrom-Json).version
function Test-Ready {
    try {$h=Invoke-RestMethod 'http://127.0.0.1:43121/api/health' -TimeoutSec 2; return $h.service -eq 'meeting-copilot' -and [string]$h.version -eq $release} catch {return $false}
}
foreach($file in @($capture,$python,$server,"$config\config.json","$config\SESSION.md")){
    if(-not(Test-Path $file -PathType Leaf)){throw "Missing installation component: $file"}
}
$cmd=Get-Command codex.exe,codex.cmd -ErrorAction SilentlyContinue | Select-Object -First 1
$codexPath=$cmd.Source
if(-not $codexPath){
    $native=Get-ChildItem "$env:LOCALAPPDATA\MeetingCopilot\tools\node_modules" -Filter codex.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    $codexPath=$native.FullName
}
if($codexPath){
    $env:MEETING_COPILOT_CODEX=$codexPath
    $codexTools=Join-Path (Split-Path (Split-Path $codexPath)) 'codex-path'
    if(Test-Path "$codexTools\rg.exe"){$env:PATH="$codexTools;$env:PATH"}
} else {Write-Host 'AI is optional. Choose an AI tool and model once in Getting started; recording remains available.'}
if($args -contains '--refresh'){
    & $python "$root\refresh-repos.py" --config-root $config
    if($LASTEXITCODE -ne 0){throw 'Read-only repository inventory failed'}
    exit 0
}
if($check){
    & $python $server --self-test
    if($LASTEXITCODE -ne 0){throw 'Web self-test failed'}
    foreach($model in @('nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf','parakeet-tdt-0.6b-v3-Q8_0.gguf')){
        if(-not(Test-Path "$data\capture-data\models\$model")){throw "Missing speech model: $model"}
    }
    Write-Host '[OK] Capture, bundled Python and speech models. AI tool, model and account access are chosen and checked in Getting started.'
    exit 0
}
Stop-OtherVersions $root $env:USERPROFILE
if(-not(Get-Process MeetingCopilotCapture -ErrorAction SilentlyContinue)){Start-Process -FilePath $capture}
$ready=Test-Ready
if(-not $ready){
    Start-Process -FilePath $pythonw -ArgumentList @('-X','utf8',"`"$server`"",'--no-open') -WorkingDirectory $root
    for($i=0;$i -lt 40 -and -not $ready;$i++){Start-Sleep -Milliseconds 250; $ready=Test-Ready}
}
if(-not $ready){throw "MeetOnTrack $release web service did not start; port 43121 may be used by another program"}
if($args -notcontains '--no-open'){Start-Process 'http://127.0.0.1:43121'}
Write-Host 'MeetOnTrack: http://127.0.0.1:43121'
