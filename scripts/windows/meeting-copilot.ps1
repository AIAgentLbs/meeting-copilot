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
if(-not(Get-Process MeetingCopilotCapture -ErrorAction SilentlyContinue)){Start-Process -FilePath $capture}
$ready=$false
try {$h=Invoke-RestMethod 'http://127.0.0.1:43121/api/health' -TimeoutSec 2; $ready=$h.service -eq 'meeting-copilot' -or $h.ok -eq $true} catch {}
if(-not $ready){
    Start-Process -FilePath $pythonw -ArgumentList @('-X','utf8',"`"$server`"",'--no-open') -WorkingDirectory $root
    for($i=0;$i -lt 40;$i++){
        Start-Sleep -Milliseconds 250
        try {Invoke-RestMethod 'http://127.0.0.1:43121/api/health' -TimeoutSec 1 | Out-Null; $ready=$true;break} catch {}
    }
}
if(-not $ready){throw 'MeetOnTrack web service did not start'}
if($args -notcontains '--no-open'){Start-Process 'http://127.0.0.1:43121'}
Write-Host 'MeetOnTrack: http://127.0.0.1:43121'
