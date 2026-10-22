# Shared WSL 2 bridge. Does not install/remove a distro or change Windows PATH.
$script:CommandCenterCheckout = Split-Path $PSScriptRoot -Parent
function ConvertTo-BashLiteral([string]$Value) {
    $escapedQuote = "'" + [char]34 + "'" + [char]34 + "'"
    return "'" + $Value.Replace("'", $escapedQuote) + "'"
}

function Invoke-CommandCenterWSL {
    param([string]$Distro, [string]$Script, [string[]]$Options)
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        throw "WSL 2 is required. In an administrator PowerShell, run: wsl --install -d Ubuntu. Restart if requested, initialize Ubuntu, and install Homebrew from https://brew.sh."
    }
    $version = & wsl.exe -d $Distro -- uname -r
    if ($LASTEXITCODE -ne 0 -or "$version" -notmatch '(?i)wsl2') {
        throw "Initialize a WSL 2 distro first. Inspect wsl --list --verbose; convert if needed with wsl --set-version $Distro 2."
    }
    $linuxPath = & wsl.exe -d $Distro -- wslpath -a -u $script:CommandCenterCheckout
    if ($LASTEXITCODE -ne 0) { throw "Could not map the checkout into WSL." }
    $quotedOptions = @($Options | ForEach-Object { ConvertTo-BashLiteral $_ }) -join ' '
    $command = "cd -- $(ConvertTo-BashLiteral ($linuxPath.Trim())) && bash ./$(ConvertTo-BashLiteral $Script) $quotedOptions"
    # Send the command on stdin to avoid Windows' nested native-argument quoting.
    $previousEncoding = $OutputEncoding
    try {
        $OutputEncoding = New-Object System.Text.UTF8Encoding $false
        ($command + "`n") | & wsl.exe -d $Distro -- bash -l -s
        if ($LASTEXITCODE -ne 0) { throw "Command-center $Script failed (exit $LASTEXITCODE)." }
    } finally {
        $OutputEncoding = $previousEncoding
    }
    if ($Script -eq "install.sh" -and $Options -notcontains "--dry-run") {
        Write-Host "Installed inside $Distro. Open that distro in Windows Terminal and run: ~/.local/bin/command-center"
        Write-Host "Starter workspace shortcut inside ${Distro}: ~/.local/bin/command-center reset (reuses fresh-start if it exists)."
        Write-Host "App/catalog search inside ${Distro}: ~/.local/bin/command-center catalogs; inside Zellij use Ctrl-g, then a."
    }
}
