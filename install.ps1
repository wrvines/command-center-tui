[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu",
    [switch]$NoDependencies,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
. "$PSScriptRoot/scripts/wsl.ps1"
$options = @("--no-ghostty")
if ($NoDependencies) { $options += "--no-dependencies" }
if ($DryRun) { $options += "--dry-run" }
Invoke-CommandCenterWSL -Distro $Distro -Script "install.sh" -Options $options
