param([Parameter(Mandatory)][string]$Installer)
$ErrorActionPreference='Stop'
$temp=Join-Path ([IO.Path]::GetTempPath()) ('copilot-installer-fixture-'+[guid]::NewGuid())
New-Item -ItemType Directory "$temp\package\capture","$temp\package\python","$temp\package\web" -Force | Out-Null
$stand=@{}
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
    # MEETONTRACK-65: an update stops our previous version's server, nothing else: never a
    # capture (it may be recording), never another program, even when the package's own
    # launcher (here a stub) predates that step.
    $old="$temp\installed\versions\old"
    New-Item -ItemType Directory "$old\python","$old\capture","$temp\foreign" -Force | Out-Null
    foreach($path in @("$old\python\pythonw.exe","$old\capture\MeetingCopilotCapture.exe","$temp\foreign\pythonw.exe")){
        Copy-Item "$env:SystemRoot\System32\cmd.exe" $path
        $stand[$path]=Start-Process $path -ArgumentList '/c','ping -n 30 127.0.0.1 >nul' -WindowStyle Hidden -PassThru
    }
    & $Installer -PackagePath "$temp\package.zip" -ExpectedSha256 $hash -InstallRoot "$temp\installed" -UserRoot "$temp\user" -SkipModels -NoLaunch -NoShortcuts
    if(-not $stand["$old\python\pythonw.exe"].WaitForExit(5000)){throw 'Previous version server left running'}
    if($stand["$temp\foreign\pythonw.exe"].HasExited){throw 'A process outside the versions folder was stopped'}
    if($stand["$old\capture\MeetingCopilotCapture.exe"].HasExited){throw 'A capture was stopped'}
    $functions=foreach($script in @($Installer,(Join-Path $PSScriptRoot 'windows\meeting-copilot.ps1'))){
        [Management.Automation.Language.Parser]::ParseFile($script,[ref]$null,[ref]$null).Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Stop-OtherVersions'},$true).Extent.Text}
    if(-not $functions[0] -or $functions[0] -ne $functions[1]){throw 'Installer and launcher stop different processes'}
    # The login entry the recorder wrote for an old version now names the new capture.
    $ast=[Management.Automation.Language.Parser]::ParseFile($Installer,[ref]$null,[ref]$null)
    . ([scriptblock]::Create($ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Get-CaptureRunValue'},$true).Extent.Text))
    $new='C:\U\MeetingCopilot\versions\0.2.0\capture\MeetingCopilotCapture.exe'
    if((Get-CaptureRunValue '"C:\U\MeetingCopilot\versions\0.1.4\capture\MeetingCopilotCapture.exe" --background' 'C:\U\MeetingCopilot\versions' $new) -ne "`"$new`" --background"){throw 'Stale login entry not rewritten'}
    if($null -ne (Get-CaptureRunValue '"C:\Other\MeetingCopilotCapture.exe" --background' 'C:\U\MeetingCopilot\versions' $new)){throw 'Foreign login entry rewritten'}
    if($null -ne (Get-CaptureRunValue "`"$new`" --background" 'C:\U\MeetingCopilot\versions' $new)){throw 'Current login entry rewritten'}
    $rejected=$false
    try { & $Installer -PackagePath "$temp\package.zip" -ExpectedSha256 ('0'*64) -InstallRoot "$temp\bad" -UserRoot "$temp\user" -SkipModels -NoLaunch -NoShortcuts } catch {$rejected=$true}
    if(-not $rejected -or (Test-Path "$temp\bad\current.json")){throw 'Bad checksum was accepted'}
    Write-Output 'Windows installer tests: 10 passed (install, preserve settings, remove retired setting/state, stop previous server only, keep capture, same stop rule in launcher, rewrite stale login entry, reject checksum)'
} finally {
    foreach($process in $stand.Values){if(-not $process.HasExited){Stop-Process -Id $process.Id -Force; $process.WaitForExit(5000) | Out-Null}}
    Remove-Item -LiteralPath $temp -Recurse -Force
}
