# Historical inspection and proposal

This document records the initial inspection. Installation status and usage are maintained in the current README.

# Personal macOS Command Center

A personal terminal workspace assembled from Ghostty, Zellij, and existing terminal tools. Configuration files and small launcher scripts provide the integration; each tool remains independently usable and upgradable.

**Status: environment inspection and implementation proposal, October 11, 2026.** The command center is not installed yet. Only this README and `agent.md` have been added to the project. Commands and files described as planned below are the implementation contract, not working entry points.

## Environment inspected

| Component | Observed state | Proposed action |
| --- | --- | --- |
| macOS | 27.0.1, build 26A434, Apple Silicon (`arm64`) | Use native Homebrew packages |
| Shell | `/bin/zsh` | Preserve startup files |
| Homebrew | 7.0.4, `/opt/homebrew/bin/brew` | Install missing core tools |
| Ghostty | 1.3.1 in `/Applications/Ghostty.app` | Preserve and extend its existing appearance |
| Zellij | Not on PATH; not installed through Homebrew | Install; inspected Homebrew candidate: 0.45.1 |
| btop | Not on PATH; not installed through Homebrew | Install; candidate: 1.4.7 |
| Newsboat | Not on PATH; not installed through Homebrew | Install; candidate: 2.45 |
| Lazygit | Not on PATH; not installed through Homebrew | Install; candidate: 0.66.1 |
| Hermes | Existing launcher at `~/.local/bin/hermes` | Reuse existing installation and authentication |
| OpenCode | Homebrew inventory: 1.18.31 | Support as a coding-agent pane |
| Pi, Codex CLI | Not checked in initial inspection | Check command availability before integration |
| Yazi, lazydocker | Not on PATH; not installed through Homebrew | Optional additions |
| Neovim | Not on PATH; not installed through Homebrew | Omit from the initial setup; no editor dependency |
| Docker | CLI not on PATH | Keep container panels optional; requires an engine too |
| curl | `/usr/bin/curl` | Use for wttr.in; no weather daemon |
| Git | 2.54.0 (Apple Git-157) | Reuse |
| tmux | Homebrew 3.7c | Preserve; launch Zellij directly from Ghostty |
| Starship | Homebrew 1.26.0 | Optional prompt integration after workspace validation |
| Project repository | Empty repository on `main`, no commits | Keep configuration and documentation here |

Homebrew candidate versions are a dated snapshot, not version pins. All four inspected core formulae offered Apple Silicon bottles for this macOS release. The local Hermes checkout describes itself as `v0.21.6+canary.20261010T070026Z-142-g66605471e9f`; this is source provenance, not a verified CLI version banner. Its wrapper targets `~/.hermes/hermes-agent/.hermes/bin/hermes`.

The inspection used command discovery, Homebrew inventory and package metadata, local source metadata, and Ghostty's version and effective configuration output. Homebrew needed an approved metadata refresh after the sandbox blocked its initial lookup. No packages were installed or upgraded.

### Existing configuration

Ghostty's macOS configuration directory contains:

- `~/Library/Application Support/com.mitchellh.ghostty/config`: a blank line.
- `~/Library/Application Support/com.mitchellh.ghostty/config.ghostty`: `theme = GitHub Dark High Contrast`.

Ghostty's effective configuration confirms that theme, background `#0a0c10`, and foreground `#f0f3f6`. Its inspection command also emitted `SentryInitFailed`; interactive rendering has not been tested, so this is recorded without attributing a cause.

Both filenames must be preserved. Current Ghostty documentation lists both modern and legacy filenames and their loading order. Future activation should add a managed include to the existing modern file, after backing up both files, instead of creating a competing configuration in another directory. See [Ghostty configuration](https://ghostty.org/docs/config).

`~/.zprofile` already initializes Homebrew and adds `~/.local/bin` to PATH. `~/.zshrc` is effectively empty. No tool configuration directories were found at the inspected default locations for Zellij, btop, Newsboat, or Lazygit. Font selection remains open; the inspected user and shared font directories did not reveal a custom terminal font. Do not require a Nerd Font for basic operation.

Hermes credentials, provider configuration, conversation databases, and private session contents were not read.

## Proposed architecture

Ghostty should always open to its normal zsh shell. Start the command center explicitly by typing `command-center`; do not auto-start Zellij from Ghostty configuration or shell startup files. Ordinary terminal windows and command-center windows can coexist.

The launcher enters one named Zellij session, `command-center`, initially containing five tabs. Zellij owns tab, pane, floating panel, resize, and session behavior. Use its bundled tab/status plugins initially. Avoid another multiplexer layer, custom dashboard, web server, or background service.

| Workspace | Initial pane arrangement | Startup behavior |
| --- | --- | --- |
| DEV | Large coding-agent/shell left; Git and development-output shells stacked right | Interactive shells immediately; OpenCode, Pi, Codex CLI, or Lazygit on demand |
| SYSTEM | Large btop pane; small diagnostics shell | btop on Enter, with a proposed two-second refresh |
| AGENTS | Starter panes for independent agents; number and tools are user-adjustable | Hermes, OpenCode, Pi, or Codex CLI on demand |
| NEWS & WEATHER | Newsboat left; forecast right | Fetch on demand; weather cached for 30 minutes |
| OPERATIONS | Logs left; Git, containers, and services on the right | Shells first; tools and selected log streams on demand |

These are independently reusable tab layouts as well as one combined layout. Project directories are supplied by the launcher rather than hardcoded to a particular repository. Operations commands are selected for the project; do not guess a build command, log file, service, or Docker context.

Neovim is unnecessary for this design. Coding agents run in ordinary terminal panes. Manual file editing can use whichever editor the user already prefers; do not require or auto-install an editor.

Zellij layouts support split panes, floating panes, reusable templates, and `start_suspended`, which waits for Enter before launching a command. Use those existing features to keep expensive panels idle until needed. Hiding an already running tab does not stop its processes. See [Zellij layouts](https://zellij.dev/documentation/creating-a-layout.html).

### User-controlled panel arrangement

The supplied layouts are starting arrangements. The user can add or close panes, change the panel count, split horizontally or vertically, move and resize panes, switch a pane between tiled and floating, and add or remove tabs. A small window will limit how many panes are comfortable to use.

Keep manual arrangements stable: initially disable automatic layout rearrangement and preserve user changes when reattaching. Provide `command-center save-layout NAME` to export the current arrangement using Zellij's native `dump-layout` action, and a planned `--layout NAME` option to select a saved template for a new session. Choosing a template must not overwrite an already running session. See [Zellij CLI actions](https://zellij.dev/documentation/cli-actions.html).

### Appearance and keyboard navigation

Keep Ghostty's GitHub Dark High Contrast theme. Derive matching tool colors, pane borders, and selection accents from it. Start with readable text labels, modest padding, and no transparency. Custom fonts and prompt decoration can follow after the core setup works.

Start Zellij in locked mode so coding-agent and Hermes shortcuts reach their applications. Use Zellij's native lock/unlock and pane, tab, resize, scroll, and session modes; document the installed version's actual bindings after testing. Keep its status hints visible during onboarding. Validate Option/Alt handling in Ghostty before adding Alt shortcuts. Floating panels should use native Zellij actions.

### Sessions and Hermes independence

The launcher should attach to a live named session, restore an exited one, or create it from the combined layout when absent. Reject accidental nesting inside Zellij. Reattaching to a live session keeps its processes running.

Zellij resurrection saves layout and command metadata; it does not preserve process memory after exit or reboot. Restored commands normally wait for Enter. Retain that behavior. Keep session serialization enabled and full scrollback serialization off initially to limit disk activity. See [session resurrection](https://zellij.dev/documentation/session-resurrection.html).

Each Hermes pane should start a fresh `hermes chat`, without a shared `--continue` or `--resume latest`. They share existing provider settings, authentication, and potentially persistent memory; separate conversations are not filesystem or configuration isolation. Record each conversation's specific ID when resumption is needed, and use `hermes --resume <session_id>` in that pane. Hermes saves conversations separately from Zellij workspace metadata. Confirm syntax against the installed build before integration. See [Hermes CLI](https://hermes-agent.nousresearch.com/docs/user-guide/cli/) and [Hermes sessions](https://hermes-agent.nousresearch.com/docs/user-guide/sessions/).

When multiple agents edit the same repository, give them distinct Git worktrees. Do not configure separate Hermes homes or duplicate credentials as a default.

## Proposed repository structure

Only `README.md` and `agent.md` currently exist. The remaining files below are planned:

```text
command-center/
  README.md
  agent.md
  Brewfile                     # Missing core packages; optional tools separate
  bin/
    command-center             # Launch, attach, restore, doctor, save-layout
    cc-weather                 # Bounded curl request and cached forecast
    cc-panel                   # Small tool availability / shell fallback wrapper
  config/
    ghostty/command-center.ghostty
    zellij/config.kdl
    zellij/layouts/
      command-center.kdl
      dev.kdl
      system.kdl
      agents.kdl
      news-weather.kdl
      operations.kdl
    btop/btop.conf
    newsboat/config
    newsboat/urls.example
    lazygit/config.yml
    command-center.env.example # Non-secret location and project preferences
  scripts/
    install.sh                 # Preview, backups, idempotent activation
    uninstall.sh               # Undo managed integrations from a manifest
    validate.sh                # CLI/config checks and isolated smoke checks
  docs/
    usage.md
    customization.md
    troubleshooting.md
```

Keep generated layout snapshots, private feeds, local preferences, backups, weather cache, Newsboat state, and installation manifests outside tracked source. Choose explicit per-tool configuration arguments where available. Do not globally replace `XDG_CONFIG_HOME`, the user's Zellij config, or unrelated tool settings.

## Planned installation and reversibility

The dependency installation step will be:

```sh
brew install zellij btop newsboat lazygit
```

It has not been run. Ghostty, Hermes, and OpenCode are already installed. Check Pi and Codex CLI availability before integration and preserve existing authentication. wttr.in needs curl and network access rather than a Homebrew package. Optional Yazi and lazydocker remain a separate installation choice. Neovim is excluded from the initial setup. Lazydocker also needs a reachable container engine; installing its CLI alone is insufficient.

The installer should preview every intended integration, then back up each existing file before writing. Use a timestamped manifest recording target paths, whether they existed, backup paths, and installed content checksums. Add only a marked Ghostty include and the launcher shortcut needed for this project. Existing PATH setup already supports a `~/.local/bin/command-center` link; do not overwrite a name collision.

Keep the core Zellij configuration repository-local and pass it explicitly from the launcher. Store Newsboat read-state separately from its configuration. The uninstall script should remove only matching managed changes and restore backups, refusing to overwrite edits made since installation. Package removal is a separate choice; do not uninstall existing or shared dependencies automatically.

## Planned everyday usage

Open Ghostty and use its normal shell for any terminal work, including launching a coding agent directly. Enter `command-center` only when the full workspace is wanted. Detaching should return to that original shell while the Zellij session keeps running; run `command-center` again to reattach. A short `cc` alias may be added only if the name is free.

The launcher will provide `--project /path/to/repo`, `--workspace dev|system|agents|news-weather|operations`, `--session NAME`, `--layout NAME`, `doctor`, and `save-layout NAME`. These interfaces are proposed and are not available yet.

Use native Zellij modes to open, close, move, resize, or float panes. Detach when preserving live work; attach with the launcher to return. After reboot, restore the workspace, start selected commands with Enter, and resume Hermes conversations by specific ID. Saved layout files are structural templates, while tool-specific data remains owned by each tool.

For weather, require an explicit configurable location rather than inferring a city from timezone. Use HTTPS, a connection timeout and total timeout, and a stale-cache fallback with a visible timestamp. Refresh only on demand or at a low frequency. Choose RSS feeds before enabling automated reloads. btop covers CPU, memory, processes, disks, and network; validate the metrics available on this Mac. See [btop](https://github.com/aristocratos/btop), [Newsboat](https://newsboat.org/), and [wttr.in](https://github.com/chubin/wttr.in).

## Implementation sequence and validation

1. Install the four missing core tools and record their actual CLI versions.
2. Build the repository-local Zellij config and DEV layout first; verify shell input, appearance, splits, floating panes, resizing, and detach/attach in Ghostty.
3. Add the other four tabs and individual workspace layouts. Test fallback shells for missing optional tools and non-Git directories.
4. Integrate independent Hermes panes, RSS, bounded weather requests, and project-specific operations commands.
5. Add the launcher and installer, exercise repeated installation and rollback, and finish the actual shortcut/usage guide.

Before marking the setup ready, validate configuration using the installed tools' supported checks, perform an interactive Ghostty smoke test, and test live reattachment and exited-session resurrection separately. Test launcher paths containing spaces, launching from another directory, missing dependencies, and nested Zellij detection. Verify weather timeout/cache behavior and Newsboat read-state persistence. Confirm Hermes panes get different conversation IDs and can resume individually.

Measure idle CPU and memory with expensive panels suspended, then with btop and one Hermes pane active. Record observations rather than promise a fixed overhead. Confirm original Ghostty configuration can be restored without losing user edits. Do not start container services, builds, or log streams merely to validate layout syntax.

**Completed validation:** installed-tool inventory, core Homebrew candidate metadata, Ghostty version/theme inspection, Hermes source provenance, and preservation hashes. **Pending:** installation, layout parsing, launcher tests, interactive use, persistence, performance measurement, and rollback execution.

Original Ghostty SHA-256 hashes for preservation checks:

```text
config          01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b
config.ghostty  a7ede47f1c57425eba8e046608a71af581b410a88a0572ba6475096f33cb7bc3
```
