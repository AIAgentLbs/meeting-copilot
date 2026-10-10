param(
    [string]$PackagePath,
    [string]$ExpectedSha256 = '05f7b492c6bfd9fc7fc068f2700db3c0de3c4e2686a8c2906adcf245aa63f8c4',
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'MeetingCopilot'),
    [string]$UserRoot = $env:USERPROFILE,
    [switch]$SkipModels,
    [switch]$NoLaunch,
    [switch]$NoShortcuts
)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$version='0.1.0-windows-beta.1'
$url='https://github.com/AIAgentLbs/meeting-copilot/releases/download/windows-v0.1.0/meeting-copilot-windows-x64.zip'
$utf8=[Text.UTF8Encoding]::new($false)
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
        Invoke-WebRequest -UseBasicParsing $url -OutFile $PackagePath
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
    if(-not(Test-Path "$configRoot\config.json")){
        $settings=@{recordings_dir=(Join-Path $dataRoot 'recordings'); keep_audio=$true; analytics=$false; system_audio='all'; start_at_login=$false; interface_language='auto'; auto_record=@{enabled=$true;min_duration_seconds=300}; transcription=@{enabled=$true;engine='local';local_engine='parakeet'}; live_transcription=@{enabled=$true}; summary=@{enabled=$false;backend='none'}; speaker_names=@{backend='none'}}
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
            Invoke-WebRequest -UseBasicParsing $model.url -OutFile "$target.download"
            if((Get-FileHash "$target.download" -Algorithm SHA256).Hash -ne $model.hash){throw 'Speech model checksum mismatch'}
            Move-Item "$target.download" $target -Force
        }
    }
    [IO.File]::WriteAllText("$InstallRoot\current.json",(@{version=$version;directory=$destination}|ConvertTo-Json),$utf8)
    if(-not $NoShortcuts){
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
