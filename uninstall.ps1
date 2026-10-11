[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu",
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
. "$PSScriptRoot/scripts/wsl.ps1"
$options = @()
if ($DryRun) { $options += "--dry-run" }
Invoke-CommandCenterWSL -Distro $Distro -Script "uninstall.sh" -Options $options
