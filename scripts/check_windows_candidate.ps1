param([Parameter(Mandatory)][string]$PackagePath,[Parameter(Mandatory)][string]$ExpectedSha256,[Parameter(Mandatory)][string]$Installer)
$ErrorActionPreference='Stop'
$candidateRoot=Join-Path ([IO.Path]::GetTempPath()) ('meetontrack-candidate-'+[guid]::NewGuid())
New-Item -ItemType Directory $candidateRoot | Out-Null
try {
    if((Get-FileHash $PackagePath -Algorithm SHA256).Hash -ne $ExpectedSha256){throw 'Candidate checksum mismatch'}
    foreach($script in @($Installer,(Join-Path $PSScriptRoot 'windows/meeting-copilot.ps1'),(Join-Path $PSScriptRoot 'windows/package.ps1'))){
        $tokens=$null; $syntaxErrors=$null
        [Management.Automation.Language.Parser]::ParseFile($script,[ref]$tokens,[ref]$syntaxErrors) | Out-Null
        if($syntaxErrors.Count){throw "PowerShell syntax failed: $script"}
    }
    & (Join-Path $PSScriptRoot 'test_windows_installer.ps1') -Installer $Installer
    $install=Join-Path $candidateRoot 'installed'
    $user=Join-Path $candidateRoot 'user'
    & $Installer -PackagePath $PackagePath -ExpectedSha256 $ExpectedSha256 -InstallRoot $install -UserRoot $user -SkipModels -NoLaunch -NoShortcuts
    $current=Get-Content "$install/current.json" -Raw | ConvertFrom-Json
    $manifest=Get-Content "$($current.directory)/release.json" -Raw | ConvertFrom-Json
    foreach($entry in $manifest.sha256.PSObject.Properties){
        $file=Join-Path $current.directory $entry.Name
        if((Get-FileHash $file -Algorithm SHA256).Hash -ne $entry.Value){throw "Payload checksum mismatch: $($entry.Name)"}
    }
    if((Get-Item "$($current.directory)/capture/MeetingCopilotCapture.exe").VersionInfo.ProductName -ne 'MeetOnTrack Capture'){throw 'Wrong native product identity'}
    & "$($current.directory)/python/python.exe" "$($current.directory)/web/server.py" --self-test
    if($LASTEXITCODE -ne 0){throw 'Installed server self-test failed'}
    $records=Join-Path $user '.local/share/meeting-copilot/recordings'
    New-Item -ItemType Directory $records -Force | Out-Null
    [IO.File]::WriteAllText("$records/synthetic-keep.txt",'synthetic recording preservation check')
    & $Installer -PackagePath $PackagePath -ExpectedSha256 $ExpectedSha256 -InstallRoot $install -UserRoot $user -SkipModels -NoLaunch -NoShortcuts
    if((Get-Content "$records/synthetic-keep.txt" -Raw) -ne 'synthetic recording preservation check'){throw 'Recordings not preserved'}
    $fileCount=@($manifest.sha256.PSObject.Properties).Count
    Write-Host "PASS: exact Windows candidate $($manifest.version); $fileCount file hashes; install/reinstall, product identity, embedded server, syntax and installer regressions. No hardware recording test."
} finally {Remove-Item -LiteralPath $candidateRoot -Recurse -Force}
