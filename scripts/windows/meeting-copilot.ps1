$ErrorActionPreference='Stop'
$check=$args -contains '--check'
if(@($args|Where-Object {$_ -notin @('--check','--no-open')}).Count){throw 'Usage: meeting-copilot.ps1 [--check|--no-open]'}
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
$native=Get-ChildItem "$env:LOCALAPPDATA\MeetingCopilot\tools\node_modules" -Filter codex.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if($native){$codexPath=$native.FullName}else{$cmd=Get-Command codex.exe,codex.cmd -ErrorAction SilentlyContinue | Select-Object -First 1;$codexPath=$cmd.Source}
if(-not $codexPath){throw 'Codex CLI is required. Install/sign in to Codex, then open Meeting Copilot again'}
$env:MEETING_COPILOT_CODEX=$codexPath
$info=[Diagnostics.ProcessStartInfo]::new()
$info.FileName=if($codexPath.EndsWith('.cmd')){"$env:SystemRoot\System32\cmd.exe"}else{$codexPath}
$info.Arguments=if($codexPath.EndsWith('.cmd')){"/d /s /c `"`"$codexPath`" login status`""}else{'login status'}
$info.UseShellExecute=$false
$info.RedirectStandardOutput=$true
$info.RedirectStandardError=$true
$info.CreateNoWindow=$true
$auth=[Diagnostics.Process]::Start($info)
$out=$auth.StandardOutput.ReadToEndAsync();$err=$auth.StandardError.ReadToEndAsync()
if(-not $auth.WaitForExit(15000)){$auth.Kill();throw 'Codex login check timed out'}
if($auth.ExitCode -ne 0){throw 'Codex needs sign-in. Run codex login, then open Meeting Copilot again'}
& $python "$root\refresh-repos.py" --config-root $config
if($LASTEXITCODE -ne 0){throw 'Read-only repository inventory failed'}
if($check){
    & $python $server --self-test
    if($LASTEXITCODE -ne 0){throw 'Web self-test failed'}
    foreach($model in @('nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf','parakeet-tdt-0.6b-v3-Q8_0.gguf')){
        if(-not(Test-Path "$data\capture-data\models\$model")){throw "Missing speech model: $model"}
    }
    Write-Host '[OK] Capture, bundled Python, speech models, read-only repository manifest and Codex login. Model: gpt-6.1-sol'
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
if(-not $ready){throw 'Meeting Copilot web service did not start'}
if($args -notcontains '--no-open'){Start-Process 'http://127.0.0.1:43121'}
Write-Host 'Meeting Copilot: http://127.0.0.1:43121'
