$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
foreach ($path in @("install.ps1", "uninstall.ps1", "scripts/wsl.ps1")) {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        (Join-Path $root $path), [ref]$tokens, [ref]$parseErrors) | Out-Null
    if ($parseErrors.Count) { throw "PowerShell parse errors in ${path}: $parseErrors" }
}
. "$PSScriptRoot/wsl.ps1"
$global:CommandCenterTestCalls = @()
$global:CommandCenterTestKernel = "6.6.0-microsoft-standard-WSL2"
function global:wsl.exe {
    $Arguments = @($args)
    $global:LASTEXITCODE = 0
    $global:CommandCenterTestCalls += ,@($Arguments)
    if ($Arguments -contains "uname") { return $global:CommandCenterTestKernel }
    if ($Arguments -contains "wslpath") { return "/mnt/c/Users/O'Brien/command center" }
    $global:CommandCenterTestCommand = ($input | Out-String).Trim()
}
try {
    & "$root/install.ps1" -Distro "Test Distro" -NoDependencies -DryRun
    $command = $global:CommandCenterTestCommand
    if ($command -notlike "*install.sh*--no-ghostty*--no-dependencies*--dry-run*") {
        throw "Install flags were lost: $command"
    }
    if ($command.Contains("cd -- '/mnt/c/Users/O'Brien")) { throw "Apostrophe in checkout path was not escaped" }
    if ($global:CommandCenterTestCalls[0][1] -ne "Test Distro") { throw "Wrong WSL distro" }
    & "$root/uninstall.ps1" -Distro "Test Distro" -DryRun
    if ($global:CommandCenterTestCommand -notlike "*uninstall.sh*--dry-run*") { throw "Uninstall arguments missing" }
    $global:CommandCenterTestKernel = "4.4.0-Microsoft"
    $rejected = $false
    try { & "$root/install.ps1" -DryRun } catch { $rejected = $_.Exception.Message -like "*WSL 2*" }
    if (-not $rejected) { throw "WSL 1 was not rejected" }
    Write-Host "PASS: PowerShell syntax, WSL distro selection, path escaping, option forwarding, and WSL 1 rejection"
} finally {
    Remove-Item Function:\wsl.exe
    Remove-Variable CommandCenterTest* -Scope Global
}
