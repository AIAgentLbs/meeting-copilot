param(
    [string]$PackagePath,
    [string]$ExpectedSha256 = '74b2c0deb0374eac4df854188f5744a1f5971b60fb0cd52b3413265335f2c828',
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'MeetingCopilot'),
    [string]$UserRoot = $env:USERPROFILE,
    [switch]$SkipModels,
    [switch]$NoLaunch,
    [switch]$NoShortcuts
)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$version='0.1.4-windows-beta.1'
$url='https://github.com/AIAgentLbs/meeting-copilot/releases/download/windows-v0.1.4/meeting-copilot-windows-v0.1.4-x64.zip'
$utf8=[Text.UTF8Encoding]::new($false)
$script:copilotDownloadPython=$null
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
        $settings=@{recordings_dir=(Join-Path $dataRoot 'recordings'); keep_audio=$true; system_audio='all'; start_at_login=$false; interface_language='auto'; auto_record=@{enabled=$true;min_duration_seconds=300}; transcription=@{enabled=$true;engine='local';local_engine='parakeet'}; live_transcription=@{enabled=$true}; summary=@{enabled=$false;backend='none'}; speaker_names=@{backend='none'}}
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
    if(-not $NoShortcuts){
        # Separate tools installation leaves a parallel user's Codex session untouched.
        $tools=Join-Path $InstallRoot 'tools'
        $native=Get-ChildItem "$tools\node_modules" -Filter codex.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
        if(-not $native){
            $npm=Get-Command npm.cmd -ErrorAction SilentlyContinue
            if($npm){
                & $npm.Source install --prefix $tools @openai/codex@0.160.1 --no-audit --no-fund
                if($LASTEXITCODE -ne 0){throw 'Could not install the compatible private Codex CLI'}
            }
        }
        $shell=New-Object -ComObject WScript.Shell
        $shortcut=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Programs')) 'Meeting Copilot.lnk'))
        $shortcut.TargetPath="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
        $shortcut.Arguments="-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$destination\meeting-copilot.ps1`""
        $shortcut.WorkingDirectory=$destination
        $shortcut.IconLocation="$destination\capture\MeetingCopilotCapture.exe"
        $shortcut.Save()
        $startup=Join-Path ([Environment]::GetFolderPath('Startup')) 'Meeting Copilot.lnk'
        Copy-Item (Join-Path ([Environment]::GetFolderPath('Programs')) 'Meeting Copilot.lnk') $startup -Force
    }
    Write-Host "Installed Meeting Copilot $version. Recordings/settings are outside the installation directory."
    if(-not $NoLaunch){& "$destination\meeting-copilot.ps1"}
} finally {Remove-Item -LiteralPath $temporary -Recurse -Force}
