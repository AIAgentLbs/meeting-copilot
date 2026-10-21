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
function Stop-OtherVersions([string]$Root){
    # MEETONTRACK-65: after an update the previous version's web server keeps port 43121, so the
    # new version never serves. Stop only our own Python from another versions\<v> folder and
    # wait for the port. Capture is never stopped here: no snapshot proves it idle while a
    # recording may start meanwhile. The single-instance recorder is replaced at next sign-in
    # (its Run value and the Startup shortcut name the new version). Same text in install.ps1
    # and meeting-copilot.ps1: the installer may unpack a package whose launcher predates this.
    $versions=(Split-Path $Root -Parent).TrimEnd('\')+'\'
    $own=$Root.TrimEnd('\')+'\'
    $old=@(Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.StartsWith($versions,'OrdinalIgnoreCase') -and -not $_.ExecutablePath.StartsWith($own,'OrdinalIgnoreCase')})
    foreach($process in $old){Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue}
    if($old.Count){
        Wait-Process -Id $old.ProcessId -Timeout 10 -ErrorAction SilentlyContinue
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
Stop-OtherVersions $root
if(-not(Get-Process MeetingCopilotCapture -ErrorAction SilentlyContinue)){Start-Process -FilePath $capture}
$ready=Test-Ready
if(-not $ready){
    Start-Process -FilePath $pythonw -ArgumentList @('-X','utf8',"`"$server`"",'--no-open') -WorkingDirectory $root
    for($i=0;$i -lt 40 -and -not $ready;$i++){Start-Sleep -Milliseconds 250; $ready=Test-Ready}
}
if(-not $ready){throw "MeetOnTrack $release web service did not start; port 43121 may be used by another program"}
if($args -notcontains '--no-open'){Start-Process 'http://127.0.0.1:43121'}
Write-Host 'MeetOnTrack: http://127.0.0.1:43121'
