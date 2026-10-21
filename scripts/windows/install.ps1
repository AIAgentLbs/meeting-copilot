param(
    [string]$PackagePath,
    [string]$ExpectedSha256 = '6618f0239155a6e5d46fb2e6a29c28ee48a809e9aa9edce6ad943ec90c648e0b',
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'MeetingCopilot'),
    [string]$UserRoot = $env:USERPROFILE,
    [switch]$SkipModels,
    [switch]$NoLaunch,
    [switch]$NoShortcuts
)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$version='0.1.12-windows-beta.1'
$url='https://github.com/AIAgentLbs/meetontrack/releases/download/windows-v0.1.12/meeting-copilot-windows-v0.1.12-x64.zip'
$utf8=[Text.UTF8Encoding]::new($false)
$script:copilotDownloadPython=$null
function Test-OwnRunValue([string]$Value,[string]$VersionsRoot){
    # Recorders before MEETONTRACK-88 registered themselves at sign-in (HKCU Run) with their own
    # versioned path, which outlives updates and races the Startup shortcut that owns sign-in.
    return $Value -match '^\s*"([^"]+)"' -and $Matches[1].StartsWith($VersionsRoot.TrimEnd('\')+'\','OrdinalIgnoreCase')
}
function Stop-OtherVersions([string]$Root,[int]$Port=43121){
    # MEETONTRACK-65: after an update the previous version's web server keeps the port, so the
    # new version never serves. Stop only the process listening on it, and only when it is our
    # own Python from another versions\<v> folder; other jobs on that Python are left alone.
    # A capture is never stopped (MEETONTRACK-88): an old one is asked to quit once idle, so a
    # recording in progress finishes first, and a hidden waiter starts this version's capture
    # after it has quit. A capture too old for that command answers no and is replaced at next
    # sign-in by the Startup shortcut. Same text in install.ps1 and meeting-copilot.ps1: the
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
    if(-not $oldCapture.Count -or -not(Test-Path $capture -PathType Leaf)){return}
    $asked=Start-Process $capture -ArgumentList 'record','quit-when-idle' -WindowStyle Hidden -Wait -PassThru
    if($asked.ExitCode -ne 0){return}
    $waiter="Wait-Process -Id $($oldCapture.ProcessId -join ','); if(-not @(Get-CimInstance Win32_Process -Filter `"Name='MeetingCopilotCapture.exe' AND SessionId=$session`" | Where-Object {`$_.CommandLine -notmatch '--live-worker'}).Count){Start-Process -FilePath '$($capture -replace "'","''")' -ArgumentList '--background'}"
    Start-Process "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -WindowStyle Hidden -ArgumentList '-NoProfile','-EncodedCommand',([Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($waiter)))
}
function Download-VerifiedInput([string]$Url,[string]$Target){
    if($script:copilotDownloadPython){
        $code="import sys,urllib.request,shutil; r=urllib.request.urlopen(sys.argv[1],timeout=60); f=open(sys.argv[2],'wb'); shutil.copyfileobj(r,f); f.close(); r.close()"
        & $script:copilotDownloadPython -c $code $Url $Target
        if($LASTEXITCODE -eq 0){return}
    }
    $curl=Get-Command curl.exe -ErrorAction SilentlyContinue
    if($curl){
        & $curl.Source --fail --location --retry 3 --retry-delay 2 --connect-timeout 30 --silent --show-error --output $Target $Url
        if($LASTEXITCODE -ne 0){throw 'Download failed after bounded retries'}
    } else {Invoke-WebRequest -UseBasicParsing $Url -OutFile $Target}
}
if([Environment]::Is64BitOperatingSystem -ne $true){throw 'Windows x64 is required'}
if([int](Get-CimInstance Win32_OperatingSystem).BuildNumber -lt 26100){throw 'Windows 11 24H2 or newer is required'}
$configRoot=Join-Path $UserRoot '.config\meeting-copilot'
$dataRoot=Join-Path $UserRoot '.local\share\meeting-copilot'
$live=Join-Path $dataRoot 'meeting-copilot-live.json'
if(Test-Path $live){
    $state=Get-Content $live -Raw -Encoding UTF8 | ConvertFrom-Json
    if($state.status -in @('recording','paused','loading','overloaded')){throw 'Finish the active meeting and close Capture before updating'}
}
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('meeting-copilot-install-'+[guid]::NewGuid())
New-Item -ItemType Directory -Force $temporary | Out-Null
try {
    if(-not $PackagePath){
        $PackagePath=Join-Path $temporary 'package.zip'
        Write-Host 'Downloading the ready-to-run Windows package (no compiler required)...'
        Download-VerifiedInput $url $PackagePath
    }
    if($ExpectedSha256 -notmatch '^[a-fA-F0-9]{64}$'){throw 'The published package checksum is not configured'}
    if((Get-FileHash $PackagePath -Algorithm SHA256).Hash -ne $ExpectedSha256){throw 'Package SHA-256 mismatch. Nothing installed'}
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive=[IO.Compression.ZipFile]::OpenRead($PackagePath)
    try {
        foreach($entry in $archive.Entries){
            if($entry.FullName -match '(^[/\\]|(^|[/\\])\.\.([/\\]|$)|:)'){throw 'Unsafe archive path'}
        }
    } finally {$archive.Dispose()}
    Expand-Archive -LiteralPath $PackagePath -DestinationPath "$temporary\payload"
    foreach($required in @('release.json','capture\MeetingCopilotCapture.exe','python\python.exe','web\server.py','meeting-copilot.ps1','SESSION.md')){
        if(-not(Test-Path (Join-Path "$temporary\payload" $required) -PathType Leaf)){throw "Incomplete package: $required"}
    }
    $manifest=Get-Content "$temporary\payload\release.json" -Raw -Encoding UTF8 | ConvertFrom-Json
    $version=[string]$manifest.version
    if($version -notmatch '^[a-zA-Z0-9.-]+$'){throw 'Invalid package version'}
    $destination=Join-Path $InstallRoot "versions\$version"
    New-Item -ItemType Directory -Force $destination,$configRoot,$dataRoot | Out-Null
    Copy-Item "$temporary\payload\*" $destination -Recurse -Force
    $script:copilotDownloadPython=Join-Path $destination 'python\python.exe'
    if(-not(Test-Path "$configRoot\config.json")){
        $settings=@{recordings_dir=(Join-Path $dataRoot 'recordings'); keep_audio=$true; system_audio='all'; interface_language='auto'; auto_record=@{enabled=$true;min_duration_seconds=300}; transcription=@{enabled=$true;engine='local';local_engine='parakeet'}; live_transcription=@{enabled=$true}; summary=@{enabled=$false;backend='none'}; speaker_names=@{backend='none'}}
        [IO.File]::WriteAllText("$configRoot\config.json",($settings|ConvertTo-Json -Depth 8),$utf8)
    }
    if(Test-Path "$configRoot\SESSION.md"){
        if((Get-FileHash "$configRoot\SESSION.md").Hash -ne (Get-FileHash "$destination\SESSION.md").Hash){
            Copy-Item "$configRoot\SESSION.md" "$configRoot\SESSION.md.before-windows-install" -Force
        }
    }
    Copy-Item "$destination\SESSION.md" "$configRoot\SESSION.md" -Force
    foreach($name in @('repos.json','active-repos.json')){
        if(-not(Test-Path "$configRoot\$name")){[IO.File]::WriteAllText("$configRoot\$name",'{"repositories":[]}',$utf8)}
    }
    # One-time removal of retired telemetry state; preserve every other setting.
    $settingsFile=Join-Path $configRoot 'config.json'
    $existing=Get-Content $settingsFile -Raw -Encoding UTF8|ConvertFrom-Json
    if($existing.PSObject.Properties.Name -contains 'analytics'){
        $existing.PSObject.Properties.Remove('analytics')
        [IO.File]::WriteAllText("$settingsFile.statistics-removal.tmp",($existing|ConvertTo-Json -Depth 100),$utf8)
        Move-Item -LiteralPath "$settingsFile.statistics-removal.tmp" -Destination $settingsFile -Force
    }
    foreach($folder in @($configRoot,(Join-Path $dataRoot 'capture-data'))){
        foreach($name in @('analytics.json','analytics-pending.json')){
            $retired=Join-Path $folder $name
            if(Test-Path $retired -PathType Leaf){Remove-Item -LiteralPath $retired}
        }
    }
    if(-not $SkipModels){
        $modelRoot=Join-Path $dataRoot 'capture-data\models'
        New-Item -ItemType Directory -Force $modelRoot | Out-Null
        foreach($model in @(
            @{name='nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf';url='https://huggingface.co/handy-computer/nemotron-3.5-asr-streaming-0.6b-gguf/resolve/main/nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf';hash='b94545b313b3223fda7b2857a52681da813935c2127643d1e9ff0c23d988089c'},
            @{name='parakeet-tdt-0.6b-v3-Q8_0.gguf';url='https://huggingface.co/handy-computer/parakeet-tdt-0.6b-v3-gguf/resolve/main/parakeet-tdt-0.6b-v3-Q8_0.gguf';hash='5859f77944efcd8eafa23a6350731960b2b55b2203df51f319665c807d802cc7'}
        )){
            $target=Join-Path $modelRoot $model.name
            if((Test-Path $target) -and (Get-FileHash $target -Algorithm SHA256).Hash -eq $model.hash){continue}
            Write-Host ("Downloading and verifying local speech model: "+$model.name)
            Download-VerifiedInput $model.url "$target.download"
            if((Get-FileHash "$target.download" -Algorithm SHA256).Hash -ne $model.hash){throw 'Speech model checksum mismatch'}
            Move-Item "$target.download" $target -Force
        }
    }
    [IO.File]::WriteAllText("$InstallRoot\current.json",(@{version=$version;directory=$destination}|ConvertTo-Json),$utf8)
    Stop-OtherVersions $destination
    if(-not $NoShortcuts){
        # AI is optional; never pin/install an obsolete CLI or change an existing
        # user's auth. The first-run assistant offers installation and a live check.
        $shell=New-Object -ComObject WScript.Shell
        $shortcut=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Programs')) 'MeetOnTrack.lnk'))
        $shortcut.TargetPath="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
        $shortcut.Arguments="-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$destination\meeting-copilot.ps1`""
        $shortcut.WorkingDirectory=$destination
        $shortcut.IconLocation="$destination\capture\MeetingCopilotCapture.exe"
        $shortcut.Save()
        $startup=Join-Path ([Environment]::GetFolderPath('Startup')) 'MeetOnTrack.lnk'
        $run='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
        $registered=(Get-ItemProperty $run -ErrorAction SilentlyContinue).MeetingCopilotCapture
        if($registered -and (Test-OwnRunValue $registered (Join-Path $InstallRoot 'versions'))){Remove-ItemProperty $run MeetingCopilotCapture}
        Copy-Item (Join-Path ([Environment]::GetFolderPath('Programs')) 'MeetOnTrack.lnk') $startup -Force
        foreach($folder in @([Environment]::GetFolderPath('Programs'),[Environment]::GetFolderPath('Startup'))){
            $legacy=Join-Path $folder 'Meeting Copilot.lnk'
            if(Test-Path $legacy){
                $old=$shell.CreateShortcut($legacy)
                if($old.Arguments.Contains($InstallRoot) -and $old.Arguments.Contains('meeting-copilot.ps1')){Remove-Item -LiteralPath $legacy}
            }
        }
    }
    Write-Host "Installed MeetOnTrack $version. Recordings/settings are outside the installation directory."
    if(-not $NoLaunch){& "$destination\meeting-copilot.ps1"}
} finally {Remove-Item -LiteralPath $temporary -Recurse -Force}
