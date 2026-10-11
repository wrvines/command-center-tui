# Personal Terminal Command Center

A customizable terminal workspace built from Ghostty, Zellij, and existing CLI tools. Ghostty opens to your normal zsh shell. Type `command-center` when you want the full workspace; `ccenter` is its short equivalent.

The implementation uses small Python standard-library and Bash integration scripts. It has no custom TUI, web server, background daemon, or editor dependency. Neovim is not installed or required.

## Install from GitHub

macOS and Linux use the same installer. Python 3.9+ and Git are prerequisites; install [Homebrew](https://brew.sh) first for automatic core-tool installation.

```sh
git clone https://github.com/wrvines/command-center-tui.git
cd command-center-tui
./install.sh --dry-run
./install.sh
command-center
```

Use `./install.sh --no-dependencies` if the tools are already installed, `--no-ghostty` to keep terminal settings untouched, or `--with-ghostty` to install Ghostty on a fresh Mac. Keep the checkout in place: the launcher links refer to it. Add `~/.local/bin` to PATH if needed.

Windows runs this setup inside **WSL 2** using Windows Terminal. After initializing your Linux distro and installing its Python/Homebrew prerequisites, a Git for Windows checkout supports:

```powershell
./install.ps1 -Distro Ubuntu -DryRun
./install.ps1 -Distro Ubuntu
```

Then open Ubuntu in Windows Terminal and run `~/.local/bin/command-center`. You can also clone directly into the WSL home and use `./install.sh --no-ghostty`. See the [platform installation guide](docs/install.md) for prerequisites, Windows execution-policy options, updates, and uninstall behavior. AI tools are installed/authenticated separately on new machines.

Uninstall from the same checkout:

```sh
./uninstall.sh --dry-run
./uninstall.sh
```

On Windows, use `./uninstall.ps1 -Distro Ubuntu -DryRun`, then omit `-DryRun`. Uninstall retains packages, preferences, saved layouts, sessions, and backups.

## Start using it

Installed and activated on the original Mac on October 11, 2026. After installation, run these from Ghostty or your platform's terminal:

```sh
command-center
# Short equivalent:
ccenter

# Start a separate workspace for a project:
command-center --project "/path/to/my project" --session my-project

# Launch only the agents workspace in its own named session:
command-center --workspace agents
```

An existing named session keeps its directories and arrangement when you reconnect. `--project`, `--workspace`, and `--layout` choose initial settings for a new session; they do not reset a live one. The launcher restores exited sessions through Zellij's native resurrection.

Panels for agents, monitoring, news, weather, and Git wait for Enter before starting. Your ordinary shell panels are immediately usable. Multiple normal Ghostty windows can remain open alongside the command center.

## Tool launch commands

Open Ghostty normally and type any standalone command below. New-panel commands run from a shell pane **inside the command center** and load this setup's tool configurations.

| Tool | Start in a normal terminal | Open a new command-center panel |
| --- | --- | --- |
| Hermes | `hermes chat` | `command-center pane hermes` |
| OpenCode v2 | `opencode` | `command-center pane opencode` |
| Pi | `pi` | `command-center pane pi` |
| Codex CLI | `codex` | `command-center pane codex` |
| btop | `btop` | `command-center pane btop` |
| Newsboat | `newsboat` | `command-center pane newsboat` |
| Weather | `command-center weather` | `command-center pane weather` |
| Lazygit | `lazygit` | `command-center pane lazygit` |
| Zellij | `zellij` | Already running in the command center |
| Yazi — optional, uninstalled | `yazi` | `command-center pane yazi` |
| lazydocker — optional, uninstalled | `lazydocker` | `command-center pane lazydocker` |

Plain `newsboat` uses its default settings; the panel command loads your BBC News, Hacker News, and GitHub Blog feeds and scoped read-state. Start Lazygit from a Git repository. lazydocker also requires a running Docker-compatible engine. Run standalone `zellij` from an ordinary terminal to avoid nesting multiplexers.

Choose the placement of a new panel:

```sh
command-center pane opencode --floating
command-center pane hermes --direction right
command-center pane codex --direction down
```

Repeat an agent's panel command to open another independent session. New-panel commands start the tool immediately; in the starter layouts, focus a suspended panel and press **Enter** to launch it.

Useful commands from your ordinary terminal or a command-center shell:

```sh
command-center weather --refresh   # Refresh the 84121 forecast
command-center doctor              # Check the installation
```

From a shell pane inside the command center:

```sh
command-center save-layout my-desk # Save your arrangement
command-center detach             # Return to your ordinary terminal
```

## Workspaces

| Tab | Starting arrangement |
| --- | --- |
| DEV | Large coding shell; Git, development output, and another shell on the right |
| SYSTEM | btop for CPU, memory, processes, disks, and network; diagnostics shell below |
| AGENTS | Separate Hermes, OpenCode, Pi, and Codex CLI panes, all initially suspended |
| NEWS & WEATHER | BBC News, Hacker News, and GitHub Blog in Newsboat; weather for 84121 |
| OPERATIONS | Project logs, services, Git, and an optional container pane |

Start just one workspace from your normal Ghostty terminal:

```sh
command-center --workspace dev
command-center --workspace system
command-center --workspace agents
command-center --workspace news-weather
command-center --workspace operations
```

Each workspace gets its own default session name. Repeating a command reconnects to that workspace's existing session.

These are starting arrangements. Add, close, move, resize, or float panels freely. Automatic rearrangement is disabled. Logs and services open to shells so you can choose your own project commands; no builds or services start automatically.

On the original Mac, the existing **GitHub Dark High Contrast** theme remains in Ghostty. Zellij, btop, and Lazygit use a matching palette, and Newsboat uses terminal colors. The managed Ghostty include adds modest padding and does not change the startup command, font, or theme. Fresh machines retain their own terminal theme.

## Essential controls

Start in locked mode: shortcuts go to the application in the focused pane. Press **Ctrl+g** to unlock Zellij's controls. Keys below are sequential, not held together across steps.

| Action | Keys |
| --- | --- |
| Select tab 1–5 | Ctrl+g, then 1–5 |
| Split right / below | Ctrl+g, Ctrl+p, then r / d |
| Focus another pane | Ctrl+g, Ctrl+p, arrows; Enter to return to the application |
| Resize panes | Ctrl+g, Ctrl+n, arrows or + / -; Enter when finished |
| Move a pane | Ctrl+g, Ctrl+h, arrows; Enter when finished |
| Make the focused pane floating / tiled | Ctrl+g, Ctrl+p, e |
| Show / hide floating panels | Ctrl+g, Ctrl+p, w |
| Fullscreen the focused pane | Ctrl+g, Ctrl+p, f |
| Close the focused pane | Ctrl+g, Ctrl+p, x |
| Add a tab | Ctrl+g, Ctrl+t, n |
| Detach to the ordinary terminal | Ctrl+g, d |

Single-action pane shortcuts return to locked mode. Closing a pane ends its program; detaching keeps programs running. The normal-mode status hints show Zellij's native mode shortcuts. See [everyday usage](docs/usage.md) for more detail.

## Customize while working

From a shell pane inside the command center:

```sh
command-center pane codex --floating
command-center pane opencode --direction right
command-center pane pi --direction down
command-center pane hermes --direction right
command-center pane btop --floating
command-center add-workspace system
command-center save-layout my-desk
command-center layouts
```

Run any other CLI tool in a regular shell pane. The `pane` convenience command supports the tools listed by `command-center pane --help`; new tools do not require that shortcut to work.

Saved layouts are native KDL files. Use one for a new session:

```sh
command-center --layout my-desk --session my-desk
```

Saving refuses to overwrite an existing saved layout. Choose a new name or edit the existing file. Saved snapshots retain captured working directories; see [customization](docs/customization.md) to reuse them with a different project.

## Installation and configuration

Core dependencies were installed with Homebrew on October 11, 2026:

| Tool | Verified version |
| --- | --- |
| Ghostty | 1.3.1, existing installation |
| Zellij | 0.45.1 |
| btop | 1.4.7 |
| Newsboat | 2.45.0 |
| Lazygit | 0.66.1 |
| OpenCode | 2.0.26, upgraded through Homebrew |
| Pi | 0.85.1, existing installation |
| Codex CLI | 0.162.0-alpha.17.2, existing installation |
| Python | 3.9.6 from installed macOS Command Line Tools |

Hermes uses your existing `~/.local/bin/hermes` launcher and authentication. Its inspected checkout identifies as `v0.21.6+canary.20261010T070026Z-142-g66605471e9f`; that is source provenance rather than a verified CLI banner. Provider settings and credentials are untouched. No AI prompts are sent by the installer or tests.

OpenCode was upgraded from 1.18.31 through 1.19.0 using its official `opencode upgrade --major --method brew` migration on October 11, 2026. Its Homebrew package is now `anomalyco/tap/opencode-v2`, while the command remains `opencode`. Future updates use `brew upgrade anomalyco/tap/opencode-v2`; the existing panel helper already launches this binary.

For a fresh installation:

```sh
./install.sh --dry-run
./install.sh
command-center doctor
```

Keep this checkout in place: launcher links and the Ghostty include refer to it. Installation is idempotent and backs up both existing Ghostty configuration files. `~/.zprofile` already includes `~/.local/bin` on this Mac; no shell startup file is edited. The short command is `ccenter`, avoiding the existing macOS `cc` compiler command.

Local editable settings live under `~/.config/command-center/`:

| File | Purpose |
| --- | --- |
| `preferences.json` | Weather location and cache lifetime |
| `feeds` | RSS feed URLs and labels |
| `newsboat.conf` | Newsboat appearance and refresh settings |
| `btop.conf` | Monitor appearance and two-second refresh |
| `lazygit.yml` | Git UI appearance; automatic fetch disabled |

Saved layouts, Newsboat read-state, Lazygit state, backups, and the installation manifest live under `~/Library/Application Support/command-center/`. Weather uses `~/Library/Caches/command-center/`. Zellij retains its own native session metadata. `COMMAND_CENTER_HOME=/some/path` redirects this project's configuration/data/cache for isolated testing; it does not redirect other tools globally.

On Linux and WSL, state defaults to `~/.local/share/command-center/` and cache to `~/.cache/command-center/`, honoring XDG paths. See the [platform path table](docs/install.md#paths-and-ownership).

Yazi and lazydocker are optional and currently absent. Container use also needs a Docker-compatible CLI and engine; neither is configured by this setup. Missing optional tools leave a useful shell. Adding or removing panels never installs or uninstalls packages.

## Maintenance and rollback

```sh
command-center doctor
scripts/validate.sh
# Optional real terminal smoke check; creates and removes its own test session:
python3 -u -B scripts/smoke.py

scripts/uninstall.sh --dry-run
scripts/uninstall.sh
```

Rollback restores the original modern Ghostty config and removes only the two managed launcher links. It keeps packages, preferences, saved layouts, tool state, and backups. If a managed file has been edited since installation, rollback stops before making changes; see [troubleshooting](docs/troubleshooting.md).

The README and [agent guide](agent.md) describe the current implementation. [Validation results](docs/validation.md) distinguish automated checks from remaining visual and provider checks. The [initial inspection](docs/inspection.md) is retained as a historical record.

## Source layout

```text
bin/                 launch, panel, and weather helpers
lib/                 shared path, preference, and layout rendering helpers
config/ghostty/      small managed include
config/zellij/       keyboard/theme config and six reusable KDL layouts
config/btop/         default config and theme
config/newsboat/     default config and feed list
config/lazygit/      default Git UI config
scripts/             reversible installer, validation, real-session smoke test
tests/               ownership, persistence-decision, and weather failure checks
docs/                usage, customization, troubleshooting, and validation
```

Useful upstream references: [Ghostty configuration](https://ghostty.org/docs/config), [Zellij layouts](https://zellij.dev/documentation/creating-a-layout.html), [Zellij CLI actions](https://zellij.dev/documentation/cli-actions.html), [session resurrection](https://zellij.dev/documentation/session-resurrection.html), [Hermes CLI](https://hermes-agent.nousresearch.com/docs/user-guide/cli/), [Newsboat](https://newsboat.org/), and [wttr.in](https://github.com/chubin/wttr.in).
