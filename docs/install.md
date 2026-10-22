# Install, update, and uninstall

Clone the repository into a permanent location. The launcher links and Ghostty include refer to that checkout, so keep it there after installation. The installers never auto-launch the command center when a terminal opens.

## Supported platforms

| Platform | Entry points | Runtime and prerequisites |
| --- | --- | --- |
| macOS | `install.sh`, `uninstall.sh` | Python 3.9+, Homebrew for automatic core dependencies, Ghostty or another terminal |
| Linux | `install.sh`, `uninstall.sh` | Python 3.9+, Bash, Homebrew for automatic core dependencies, Ghostty or another terminal |
| Windows | `install.ps1`, `uninstall.ps1` | Initialized WSL 2 Linux distro, its Python 3.9+ and Homebrew; use Windows Terminal |

Windows support runs the command center inside WSL 2. Although Zellij now has a native Windows build, this project's Bash helpers, Newsboat, and monitor integration use the Linux tool stack. Ghostty currently supports macOS and Linux. Windows PowerShell entry points bridge to the same Linux installer; they do not install/unregister distributions, change Windows PATH, or configure a Windows terminal automatically.

## macOS and Linux

Install [Homebrew](https://brew.sh) first if you want automatic dependency installation. On Linux/WSL, follow its [prerequisites and shell setup](https://docs.brew.sh/Homebrew-on-Linux). Python must already be available as `python3`; install it with your package manager if needed. Then:

```sh
git clone https://github.com/wrvines/command-center-tui.git
cd command-center-tui
./install.sh --dry-run
./install.sh
command-center
```

`install.sh` preflights ownership, installs missing Zellij/btop/Newsboat/Lazygit/curl/Git/fzf with Homebrew, checks Zellij is at least 0.45.1, validates configurations and fixture tests, then installs launcher links and a backed-up Ghostty include. Repeated installation preserves existing preferences and checks ownership. Existing outdated tools are not silently upgraded; update them with their package manager if version validation fails. Packages installed before a later validation failure remain installed; user integrations are applied only after validation passes.

Fzf powers the searchable app/catalog picker. After updating an existing installation, rerun the installer to add it if missing, or install it with your Linux package manager when using `--no-dependencies`. Run `command-center catalogs` on macOS/Linux, or `~/.local/bin/command-center catalogs` inside the installed WSL distro. See [catalog usage](catalogs.md) for source selection, caching, and Terminal Trove's recent-feed fallback.

If your distribution already provides the core tools, including a sufficiently recent Zellij:

```sh
./install.sh --no-dependencies
```

For another terminal, or a headless Linux host:

```sh
./install.sh --no-ghostty
```

For the MacBook Air → SSH → Debian Lenovo setup, Ghostty stays on the Mac. On Debian with compatible tools already installed, combine `--no-dependencies --no-ghostty` (review with `--dry-run` first). Install terminal capability metadata only if the remote host lacks the advertised terminfo entry. See [unified theme installation](themes.md#debian-lenovo-over-ssh) for the `oh-my-pi` Zellij selector, Mac Ghostty activation, and remote checks. The main installer does not activate the optional theme or replace private app colors.

For a fresh Mac that also needs Ghostty:

```sh
./install.sh --with-ghostty
```

On Linux, install Ghostty separately using its [distribution packages](https://ghostty.org/docs/install/binary). The installer preserves the terminal's existing theme and startup behavior; on a new machine, select a Ghostty theme yourself if desired.

If `command-center` is not on PATH, run `"$HOME/.local/bin/command-center"`, or add the directory to the current shell:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Make that PATH setting persistent using your shell's normal startup file if desired. The installer leaves shell startup files unchanged.

## Windows / WSL 2

First initialize WSL 2. From administrator PowerShell if WSL is not installed:

```powershell
wsl --install -d Ubuntu
```

Restart if requested, open Ubuntu, finish its user setup, and install Python, Git, curl and Homebrew **inside that distro** following [Microsoft's WSL instructions](https://learn.microsoft.com/en-us/windows/wsl/install) and the Homebrew Linux guide above. `wsl --list --verbose` should show version 2.

For best filesystem performance, clone into the Linux home from Ubuntu in Windows Terminal and use the Linux entry points:

```sh
git clone https://github.com/wrvines/command-center-tui.git
cd command-center-tui
./install.sh --no-ghostty
~/.local/bin/command-center
```

Alternatively, clone with Git for Windows and run the PowerShell entry points from that checkout (PowerShell 7 recommended):

```powershell
git clone https://github.com/wrvines/command-center-tui.git
cd command-center-tui
./install.ps1 -Distro Ubuntu -DryRun
./install.ps1 -Distro Ubuntu
```

Use `-NoDependencies` when the tools are already installed in WSL. If execution policy blocks a local script, run it with a process-only policy, for example `pwsh -NoProfile -ExecutionPolicy Bypass -File ./install.ps1 -Distro Ubuntu`. This does not persist a policy change.

Open the same distro in Windows Terminal and run `~/.local/bin/command-center`. It does not automatically launch from a normal Windows PowerShell prompt. Install and authenticate Hermes/OpenCode/Pi/Codex inside WSL separately; native Windows installations are not reused automatically. Newsboat's Linux browser setting uses `xdg-open`; configure a WSL browser bridge such as `wslview` in your local `newsboat.conf` if needed. Clipboard copying uses `clip.exe` when available, otherwise Zellij's terminal clipboard protocol.

## Paths and ownership

| Purpose | macOS | Linux / WSL |
| --- | --- | --- |
| Launcher links | `~/.local/bin/command-center`, `ccenter` | Same, inside Linux |
| Editable preferences | `~/.config/command-center/` | `$XDG_CONFIG_HOME/command-center/`, default `~/.config/command-center/` |
| State, backups, manifest | `~/Library/Application Support/command-center/` | `$XDG_DATA_HOME/command-center/`, default `~/.local/share/command-center/` |
| Weather cache | `~/Library/Caches/command-center/` | `$XDG_CACHE_HOME/command-center/`, default `~/.cache/command-center/` |
| Ghostty include target | Existing modern Application Support config | Existing `config.ghostty` or `config` under `$XDG_CONFIG_HOME/ghostty/` |

macOS also honors an absolute `XDG_CONFIG_HOME` for the project preferences. Linux runtime configuration follows the user's shell, removes macOS-only clipboard commands, and is generated under the scoped Zellij directory. WSL skips Ghostty configuration. Keep XDG settings consistent between installation, use, and uninstallation.

## Reset the workspace session

The same Python launcher provides `reset` on every supported platform. Run it from an ordinary terminal after detaching from Zellij:

| Platform | Command |
| --- | --- |
| macOS or Linux | `command-center reset` |
| Windows: open the installed WSL 2 distro in Windows Terminal | `~/.local/bin/command-center reset` |

If the launcher directory is on PATH, `command-center reset` also works inside WSL. This is equivalent to `command-center --session fresh-start`: it creates the starter five-tab arrangement when that session does not exist, otherwise reconnects to or restores its saved arrangement. It preserves other sessions, saved layouts, tool preferences, feeds, and authentication. It does not reset macOS/Windows window positions or restore tool factory settings. Use another unused session name for an untouched starter arrangement again.

For stock Zellij separately, detach and run `zellij --config /dev/null` on macOS, Linux, or inside WSL. Quit that stock session with Ctrl+q, then run `command-center` (or its full launcher path) to return. See the [README quick reference](../README.md#quick-reference-leave-restore-and-refresh).

## Optional tools

AI agents, Neovim, Yazi, lazydocker, and a container engine are not installed automatically. The required workspaces still open, and missing tools leave helpful shells. See [OpenCode v2](https://opencode.ai/v2/docs), [Hermes](https://hermes-agent.nousresearch.com/docs/), and the respective tool documentation for installation/authentication. On this Mac the four coding agents already exist. New installations need their own accounts/settings; none are committed to the repository.

## Update from GitHub

For a checkout on macOS, Linux, or inside WSL:

```sh
command-center update
# Or: ccenter update
```

Run this from any directory, including a command-center shell pane. It locates the permanent source checkout through the installed launcher link and pulls that branch's configured upstream using `git pull --no-rebase --ff-only`. Git must be installed and able to reach/authenticate with the remote. It refuses tracked edits, staged changes, untracked files, detached HEAD, missing upstream, and divergent history. Commit/stash local work or move untracked files yourself before retrying; the updater does not discard work or create merge commits.

This updates source only, without installing packages or changing private settings. Launcher links immediately use the new source. To validate and refresh installation integrations, run from the permanent checkout:

```sh
./install.sh --no-dependencies
```

The installer includes validation. On an older installation that does not yet recognize `update`, bootstrap with `git pull --ff-only` from the checkout. Windows users run `~/.local/bin/command-center update` inside the installed WSL distro if the launcher is not on PATH. For a Git for Windows checkout, use the PowerShell workflow below instead.

Changes to tracked layouts apply to new sessions. Existing sessions keep their arrangement; private preferences are never overwritten. Keep local code changes on a branch or commit them before pulling. Avoid moving or deleting the checkout while installed; uninstall first if you need to relocate it.

For a Git for Windows checkout, update from PowerShell with the same WSL distro used during installation:

```powershell
git pull --ff-only
./install.ps1 -Distro Ubuntu -NoDependencies
```

The wrapper runs the shared Linux validation and installer. After updating, open that distro in Windows Terminal and run `~/.local/bin/command-center reset`. The macOS/Linux launcher links refer to the checkout, so `reset` is available from the updated source without a separate platform-specific implementation. A rerun of the installer preserves ownership checks and existing preferences.

## Uninstall

From the original checkout on macOS/Linux:

```sh
./uninstall.sh --dry-run
./uninstall.sh
```

For an installation made through the PowerShell wrapper:

```powershell
./uninstall.ps1 -Distro Ubuntu -DryRun
./uninstall.ps1 -Distro Ubuntu
```

Use the Linux uninstaller inside WSL for a Linux-home checkout. Uninstall removes owned launcher links and restores Ghostty's original bytes if it was integrated. It preserves installed packages, AI authentication, preferences, feed read-state, weather cache, sessions, saved layouts, and backups. It does not stop running sessions; detach or end those separately. Later edits to managed files cause uninstall to stop before making changes; preserve those edits and follow [troubleshooting](troubleshooting.md). Homebrew, WSL, and Windows Terminal are never removed.

The original `scripts/install.sh` and `scripts/uninstall.sh` remain available as integration-only entry points for existing installations and advanced testing.
