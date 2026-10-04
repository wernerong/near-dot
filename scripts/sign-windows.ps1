param([Parameter(Mandatory=$true)][string]$Artifact)
$ErrorActionPreference = 'Stop'
if (-not $env:NEAR_DOT_PFX_PATH -or -not $env:WINDOWS_SIGNING_PASSWORD) { throw 'Protected Authenticode signing material is required.' }
$tools = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe"
$tool = ($tools | Sort-Object FullName -Descending | Select-Object -First 1).FullName
if (-not $tool) { throw 'Windows SDK signtool was not found.' }
& $tool sign /fd SHA256 /tr https://timestamp.digicert.com /td SHA256 /f $env:NEAR_DOT_PFX_PATH /p $env:WINDOWS_SIGNING_PASSWORD $Artifact
if ($LASTEXITCODE -ne 0) { throw 'Authenticode signing failed.' }
& $tool verify /pa $Artifact
if ($LASTEXITCODE -ne 0) { throw 'Authenticode verification failed.' }
