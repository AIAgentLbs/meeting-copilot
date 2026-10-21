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
function Stop-OtherVersions([string]$Root,[int]$Port=43121,[switch]$KeepCapture){
    # MEETONTRACK-65: after an update the previous version's web server keeps the port, so the
    # new version never serves. Stop only the process listening on it, and only when it is our
    # own Python from another versions\<v> folder; other jobs on that Python are left alone.
    # A capture is never stopped (MEETONTRACK-88): an old one is asked to quit once idle, so a
    # recording in progress finishes first, and a hidden waiter starts this version's capture
    # after it has quit: the version current.json names then, so a later update wins. A capture
    # too old for that command answers no and is replaced at next sign-in by the Startup
    # shortcut. -KeepCapture (install without launch) leaves the capture alone. Same text in install.ps1 and meeting-copilot.ps1: the
    # installer may unpack a package whose launcher predates this.
    $versions=(Split-Path $Root -Parent).TrimEnd('\')+'\'
    $own=$Root.TrimEnd('\')+'\'
    $listeners=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).OwningProcess
    $old=@(Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" | Where-Object {
        $_.ProcessId -in $listeners -and $_.ExecutablePath -and $_.ExecutablePath.StartsWith($versions,'OrdinalIgnoreCase') -and -not $_.ExecutablePath.StartsWith($own,'OrdinalIgnoreCase')})
    foreach($process in $old){Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue}
    if($old.Count){
        Wait-Process -Id $old.ProcessId -Timeout 10 -ErrorAction SilentlyContinue
        for($i=0;$i -lt 40 -and @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).Count;$i++){Start-Sleep -Milliseconds 250}
    }
    $capture=Join-Path $Root 'capture\MeetingCopilotCapture.exe'
    $session=(Get-Process -Id $PID).SessionId  # one capture per sign-in session
    $oldCapture=@(Get-CimInstance Win32_Process -Filter "Name='MeetingCopilotCapture.exe' AND SessionId=$session" | Where-Object {
        $_.CommandLine -notmatch '--live-worker' -and $_.ExecutablePath -and $_.ExecutablePath.StartsWith($versions,'OrdinalIgnoreCase') -and -not $_.ExecutablePath.StartsWith($own,'OrdinalIgnoreCase')})
    if($KeepCapture -or -not $oldCapture.Count -or -not(Test-Path $capture -PathType Leaf)){return}
    $asked=Start-Process $capture -ArgumentList 'record','quit-when-idle' -WindowStyle Hidden -Wait -PassThru
    if($asked.ExitCode -ne 0){return}
    $current=Join-Path (Split-Path $versions -Parent) 'current.json'
    $waiter="Wait-Process -Id $($oldCapture.ProcessId -join ','); `$c=try{(Get-Content -ErrorAction Stop -LiteralPath '$($current -replace "'","''")' -Raw | ConvertFrom-Json).directory+'\capture\MeetingCopilotCapture.exe'}catch{'$($capture -replace "'","''")'}; if((Test-Path -LiteralPath `$c) -and -not @(Get-CimInstance Win32_Process -Filter `"Name='MeetingCopilotCapture.exe' AND SessionId=$session`" | Where-Object {`$_.CommandLine -notmatch '--live-worker'}).Count){Start-Process -FilePath `$c -ArgumentList '--background'}"
    Start-Process "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -WindowStyle Hidden -ArgumentList '-NoProfile','-EncodedCommand',([Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($waiter)))
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
