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
| btop — full view | `command-center run btop` | `command-center pane btop` |
| btop — small pane | `command-center run btop --compact` | `command-center pane btop --compact` |
| Newsboat — configured feeds | `command-center run newsboat` | `command-center pane newsboat` |
| Weather | `command-center weather` | `command-center pane weather` |
| Lazygit | `lazygit` | `command-center pane lazygit` |
| Zellij | `zellij` | Already running in the command center |
| Yazi — optional, uninstalled | `yazi` | `command-center pane yazi` |
| lazydocker — optional, uninstalled | `lazydocker` | `command-center pane lazydocker` |

`command-center run TOOL` starts a tool in the **current terminal or empty shell pane**, using this setup's configuration. It opens no new panes. For Newsboat, this loads your BBC News, Hacker News, and GitHub Blog feeds and shared read-state. Plain `newsboat` reads a separate default feed list and can fail with "no URLs configured"; use `command-center run newsboat` for this setup. Plain `btop` likewise uses its own default preferences. Start Lazygit from a Git repository. lazydocker also requires a running Docker-compatible engine. Run standalone `zellij` from an ordinary terminal to avoid nesting multiplexers.

Newsboat permits one running instance per feed database. If it reports "an instance of Newsboat is already running", return to that pane or quit it with `q` before launching elsewhere. Both configured commands use the same read-state; they do not create independent readers.

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
| SYSTEM | Compact btop above two shell panes; switch views for CPU, memory/disks, network, and processes |
| AGENTS | Separate Hermes, OpenCode, Pi, and Codex CLI panes, all initially suspended |
| NEWS & WEATHER | BBC News, Hacker News, and GitHub Blog in Newsboat; weather for 84121 |
| OPERATIONS | Project logs, services, Git, and an optional container pane |

### What to run in DEV OUTPUT

DEV OUTPUT describes the middle-right shell's intended role in the starter DEV layout. It is an ordinary shell for watching your project's output while you work in another pane. Its visible title follows what it is running; it starts at a shell prompt, and you choose the command yourself.

| Use | Example |
| --- | --- |
| Development server | `npm run dev`, if your project defines a `dev` script |
| Tests in watch mode | Your project's test-watch command; for runners that support it, `npm test -- --watch` |
| Application logs | `tail -F /path/to/app.log` |
| Build output | Your project's build command, such as `npm run build` |

Run these from the appropriate project directory and use that project's documented commands. For a CLI coding-agent workflow, run OpenCode, Pi, or Codex in the main coding shell, then use the output shell to watch the app or tests the agent is changing. Press **Ctrl+C** to stop a running command. Leave this pane empty, rename it, or close it whenever you do not need it.

### Launch individual workspaces

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

## Automatic pane titles

Starter layouts and `command-center pane TOOL` use automatic titles instead of fixed labels such as GIT or DEV OUTPUT. Idle shells show `zsh` or `bash`; a command such as `npm run dev` changes the title to `npm`, then the title returns to the shell when it finishes. Tools can supply their own richer titles. Command arguments are not included by our hooks. Tab names such as DEV and SYSTEM stay visible.

This uses small shell hooks inside command-center shells, with no polling service or changes to your normal shell startup files. Zsh loads your original startup files, including a custom `ZDOTDIR`; Bash loads your `.bashrc`. Other shells retain their own title behavior. Bash preserves existing DEBUG traps; when one exists, arbitrary-command tracking is left to that integration. Application-provided titles still work.

Existing saved sessions retain their fixed labels and already-running shells. To enable automatic naming for an existing shell pane without rearranging it:

```sh
command-center run shell
```

That clears its fixed label and opens a shell with the title hooks. To clear fixed labels across an existing session, use `command-center titles --all`; it first saves a layout backup containing the previous arrangement and titles. Existing shells still need the command above to load the hooks. New sessions use the new defaults, for example `command-center --session auto-titles`.

You can keep a deliberate fixed label with `command-center pane shell --name "MY PANEL"`, or `zellij action rename-pane "MY PANEL"`. It overrides automatic titles. Return the focused pane to automatic titles with `command-center titles` or `zellij action rename-pane ""`; `undo-rename-pane` restores an earlier name and does not reliably clear an original layout label. See [Zellij title actions](https://zellij.dev/documentation/cli-actions#rename-pane) and [zsh hook functions](https://zsh.sourceforge.io/Doc/Release/Functions.html#Hook-Functions).

## Smaller screens and panels

Run these in an empty shell pane or an ordinary terminal:

```sh
command-center run newsboat          # Your configured feeds in this pane
command-center run btop --compact    # CPU view in this pane
```

Inside compact btop, press **p** / **Shift+p** to cycle CPU → memory/disks → network → processes. Keys **1**, **2**, **3**, **4** toggle those individual sections. Keep Zellij in locked mode so the keys reach btop. The compact configuration retains the palette and two-second refresh, with fewer graphs; it has its own editable `~/.config/command-center/btop-compact.conf` and preserves your full-view `btop.conf`.

Native btop was tested at 60 columns with CPU at 8 rows, memory/disks at 10 rows, network at 6 rows, and processes at 16 rows. These are usable test sizes, not a promise that every combination fits. A full view still needs more room. Enlarge or fullscreen a pane before choosing a view that needs more height. Btop cannot scale all its sections below their native minimum sizes. See [btop's native controls](https://github.com/aristocratos/btop).

New SYSTEM tabs give the compact monitor 60% of the height, with two side-by-side shells underneath. Existing saved sessions keep your arrangement. To try the new template without replacing it, run this from a command-center shell:

```sh
command-center add-workspace system
# Or add just a compact monitor to your current tab:
command-center pane btop --compact --floating
```

Use Zellij's resize/fullscreen controls below as needed. You can also shrink Ghostty's font with its normal font-size controls to fit more terminal cells. Layout percentages divide the available cells; they do not shrink an application's text.

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
| `btop-compact.conf` | Separate small-pane monitor presets and fewer graphs |
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
config/shell/        scoped automatic-title integration for zsh and bash
config/btop/         default config and theme
config/newsboat/     default config and feed list
config/lazygit/      default Git UI config
scripts/             reversible installer, validation, real-session smoke test
tests/               ownership, persistence-decision, and weather failure checks
docs/                usage, customization, troubleshooting, and validation
```

Useful upstream references: [Ghostty configuration](https://ghostty.org/docs/config), [Zellij layouts](https://zellij.dev/documentation/creating-a-layout.html), [Zellij CLI actions](https://zellij.dev/documentation/cli-actions.html), [session resurrection](https://zellij.dev/documentation/session-resurrection.html), [Hermes CLI](https://hermes-agent.nousresearch.com/docs/user-guide/cli/), [Newsboat](https://newsboat.org/), and [wttr.in](https://github.com/chubin/wttr.in).
