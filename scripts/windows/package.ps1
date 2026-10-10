param([Parameter(Mandatory)][string]$BuildRoot,[Parameter(Mandatory)][string]$PayloadRoot,[Parameter(Mandatory)][string]$CopilotRevision,[Parameter(Mandatory)][string]$CaptureRevision)
$ErrorActionPreference='Stop'
$stage=Join-Path $BuildRoot 'package-v0.1.1'
if(Test-Path $stage){throw 'Use a fresh package staging directory'}
New-Item -ItemType Directory "$stage\capture","$stage\python","$stage\web" -Force | Out-Null
Copy-Item "$BuildRoot\capture\*" "$stage\capture" -Recurse
foreach($component in @('local-runtime','live-runtime','Licenses')){
    Copy-Item "$BuildRoot\upstream-runtime\current\$component" "$stage\capture\$component" -Recurse -Force
}
if((Get-FileHash "$BuildRoot\python.zip" -Algorithm SHA256).Hash -ne 'f6cca216a359be84797cabb54149ce5e062afB16cc7567eb7fc51cacb2d86b65'){throw 'Embedded Python checksum mismatch'}
Expand-Archive "$BuildRoot\python.zip" "$stage\python"
[IO.File]::WriteAllText("$stage\python\python313._pth","python313.zip`n.`n../web`nimport site`n",[Text.UTF8Encoding]::new($false))
Copy-Item "$PayloadRoot\copilot\web\*" "$stage\web" -Recurse
Get-ChildItem "$stage\web" -Directory -Filter '__pycache__' -Recurse | Remove-Item -Recurse -Force
Copy-Item "$PayloadRoot\scripts\windows\meeting-copilot.ps1","$PayloadRoot\scripts\windows\refresh-repos.py" $stage
Copy-Item "$PayloadRoot\copilot\config\SESSION.md" "$stage\SESSION.md"
Copy-Item "$PayloadRoot\LICENSE" "$stage\LICENSE"
Copy-Item "$BuildRoot\source\LICENSE" "$stage\capture\AMANU-LICENSE"
$files=[ordered]@{}
foreach($file in Get-ChildItem $stage -Recurse -File){
    $relative=$file.FullName.Substring($stage.Length+1).Replace('\','/')
    if($file.Name -in @('repos.json','active-repos.json','config.json','report.json','meeting.json','delivery.json') -or $file.Extension -in @('.wav','.caf','.log','.gguf')){throw "Private/runtime data cannot enter package: $relative"}
    $files[$relative]=(Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLower()
}
$manifest=@{version='0.1.1-windows-beta.1';architecture='x64';channel='technical-beta';signed=$false;source_revision=$CopilotRevision;capture_revision=$CaptureRevision;native_runtime_source='Amanu windows-v0.6.6 (checksum-pinned)';sha256=$files}
[IO.File]::WriteAllText("$stage\release.json",($manifest|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Compress-Archive "$stage\*" "$BuildRoot\meeting-copilot-windows-v0.1.1-x64.zip" -CompressionLevel Optimal
Get-FileHash "$BuildRoot\meeting-copilot-windows-v0.1.1-x64.zip" -Algorithm SHA256 | Select-Object Hash | ConvertTo-Json
