param([Parameter(Mandatory)][string]$Installer)
$ErrorActionPreference='Stop'
$temp=Join-Path ([IO.Path]::GetTempPath()) ('copilot-installer-fixture-'+[guid]::NewGuid())
New-Item -ItemType Directory "$temp\package\capture","$temp\package\python","$temp\package\web" -Force | Out-Null
try {
    Set-Content "$temp\package\release.json" '{"version":"fixture"}'
    Set-Content "$temp\package\capture\MeetingCopilotCapture.exe" 'synthetic binary fixture'
    Set-Content "$temp\package\python\python.exe" 'synthetic binary fixture'
    Set-Content "$temp\package\meeting-copilot.ps1" 'exit 0'
    Set-Content "$temp\package\web\server.py" '# synthetic fixture'
    Set-Content "$temp\package\SESSION.md" '# synthetic policy'
    Compress-Archive "$temp\package\*" "$temp\package.zip"
    $hash=(Get-FileHash "$temp\package.zip" -Algorithm SHA256).Hash
    & $Installer -PackagePath "$temp\package.zip" -ExpectedSha256 $hash -InstallRoot "$temp\installed" -UserRoot "$temp\user" -SkipModels -NoLaunch -NoShortcuts
    if(-not(Test-Path "$temp\installed\versions\fixture\capture\MeetingCopilotCapture.exe")){throw 'Ready-to-run capture not installed'}
    Set-Content "$temp\user\.config\meeting-copilot\config.json" '{"preserve":"fixture","analytics":true}'
    $retiredRoot="$temp\user\.local\share\meeting-copilot\capture-data"
    New-Item -ItemType Directory $retiredRoot -Force|Out-Null
    Set-Content "$retiredRoot\analytics.json" '{"synthetic":"identity"}'
    Set-Content "$retiredRoot\analytics-pending.json" '[{"synthetic":"event"}]'
    & $Installer -PackagePath "$temp\package.zip" -ExpectedSha256 $hash -InstallRoot "$temp\installed" -UserRoot "$temp\user" -SkipModels -NoLaunch -NoShortcuts
    if((Get-Content "$temp\user\.config\meeting-copilot\config.json" -Raw) -notmatch 'preserve'){throw 'Existing user settings overwritten'}
    if((Get-Content "$temp\user\.config\meeting-copilot\config.json" -Raw) -match 'analytics'){throw 'Retired usage setting was preserved'}
    if((Test-Path "$retiredRoot\analytics.json") -or (Test-Path "$retiredRoot\analytics-pending.json")){throw 'Retired usage state was preserved'}
    $rejected=$false
    try { & $Installer -PackagePath "$temp\package.zip" -ExpectedSha256 ('0'*64) -InstallRoot "$temp\bad" -UserRoot "$temp\user" -SkipModels -NoLaunch -NoShortcuts } catch {$rejected=$true}
    if(-not $rejected -or (Test-Path "$temp\bad\current.json")){throw 'Bad checksum was accepted'}
    Write-Output 'Windows installer tests: 5 passed (install, preserve settings, remove retired setting/state, reject checksum)'
} finally {Remove-Item -LiteralPath $temp -Recurse -Force}
