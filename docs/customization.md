# Customize the workspace

The command center is configuration around existing tools. A new tool can run immediately in any shell panel. Use Zellij's split controls to add a panel, run the command, then save your layout if you like the arrangement. Removing a panel does not remove the installed tool.

## Layouts

Source templates are in `config/zellij/layouts/`. `command-center.kdl` contains all five tabs; the other five files launch individual workspaces. Panes use percentages so layouts adapt to different window sizes. No maximum pane count is imposed by the launcher; available terminal space limits useful panel sizes.

The launcher renders the quoted `{{PROJECT}}` and `{{CC_PANEL}}` placeholders with safely escaped absolute paths. Launch built-in templates through `command-center` or `command-center add-workspace`; the raw files are not meant to run directly through `zellij --layout` before rendering.

Your exported arrangements are stored under `~/Library/Application Support/command-center/layouts/`. Their names take precedence over matching built-in names. `save-layout` refuses to replace an existing saved file. Save under a different name or edit the KDL file yourself.

On Linux/WSL, layouts default to `~/.local/share/command-center/layouts/`, honoring `XDG_DATA_HOME`. `command-center doctor` prints the active paths. See [platform installation](install.md).

Native exports capture absolute working directories. To reuse one with a different project, edit its `cwd` entries, or replace quoted directory values with the quoted `{{PROJECT}}` placeholder where appropriate. Keep commands you want to start on demand marked `start_suspended true`. New-session flags never reset an existing session; use a different `--session` name to try a template.

For a custom tool, add a native pane node to a layout, for example:

```kdl
pane name="MY TOOL" command="my-tool" start_suspended=true {
    args "--some-option"
}
```

Use a `command` plus separate `args` for executable arguments. No shell evaluation is performed by the launcher. If shell syntax is necessary, choose it explicitly with a shell command and review the script as ordinary code. Validate changes with `scripts/validate.sh`; saved custom layouts can be checked with `zellij --config config/zellij/config.kdl --layout "/absolute/path/to/layout.kdl" setup --check`.

## Pane titles

Built-in templates have no fixed pane names. `bin/cc-shell` supplies scoped zsh/bash title hooks to new shell panes, including native keyboard splits. Idle titles show the shell; running commands show their first command name, without arguments. Apps may replace that title themselves. Pipelines, shell functions, and wrappers are labeled by the command entered, rather than by polling every descendant process.

Zsh's temporary startup shim immediately restores the original `ZDOTDIR` and sources the original `.zshenv`; subsequent profile/rc/login files load normally. It installs additive `precmd`/`preexec` hooks at the first prompt. Bash uses a private rc file that sources your `.bashrc`, retains `PROMPT_COMMAND`, and adds command tracking only if no DEBUG trap exists. Neither edits global startup files. Other shells are passed through with their own title integration.

For an existing shell, `command-center run shell` clears its fixed name and starts the scoped shell. To retain a fixed title, use `command-center pane TOOL --name "NAME"` or native `zellij action rename-pane "NAME"`. To clear it, use `command-center titles` or `zellij action rename-pane ""`. Clearing all terminal names with `command-center titles --all` first backs up the current native layout into the private saved-layout directory. It does not replace saved layouts or restart commands; existing shell processes still need the scoped shell command to load new hooks.

Removing the title integration is reversible: use an ordinary shell or revert the repository update. Normal terminals remain unaffected. New-session configuration is rendered into the private `zellij/platform.kdl` on both macOS and Linux so the scoped shell path remains correct after cloning elsewhere. Raw repository config is a source template; use the launcher for the complete integration.

## Tool preferences

Editable local defaults are copied once into `~/.config/command-center/`. Changing the repository defaults does not overwrite those local files. The normal mapping is:

- `preferences.json`: weather location and cache seconds.
- `feeds`: one RSS URL per line, with optional tags and quoted `~Title` labels.
- `btop.conf`: colors, display boxes, and refresh rate; btop saves its own UI changes here.
- `btop-compact.conf`: separate small-pane presets; used by `command-center run btop --compact` or `command-center pane btop --compact`.
- `newsboat.conf`: feed refresh and Newsboat appearance.
- `lazygit.yml`: Git UI appearance and behavior.

The btop theme file is under `config/btop/themes/`. Zellij's baseline theme and keyboard settings are under `config/zellij/config.kdl`. Use a new session to reliably apply startup-only Zellij changes. The Ghostty include changes padding; your original theme and font remain in the existing Ghostty config.

## Shared theme and future profiles

`config/themes/oh-my-pi.json` defines the opt-in nine-color palette; `python3 -B scripts/themes.py` renders the Ghostty `OhMyPi-DarkTerminal` and Zellij `oh-my-pi` adapters. `command-center --theme oh-my-pi --session NEW_NAME` uses a separate scoped Zellij config and preserves the default palette. This selector does not change terminal settings or existing application preferences.

See [themes](themes.md) for review-first activation on macOS, Debian/SSH terminal capabilities, rollback, and adding app adapters. [The roadmap](roadmap.md) connects this palette to future theme switching, workspace profiles, the application launcher, and multiple-monitor customization. Persistent selection and automatic switching across apps are planned, not implemented.

Keep credentials in each tool's existing authentication mechanism. Do not put API keys in layouts, launcher arguments, tracked preferences, or feed examples. Coding agents retain their own model choices and authentication.

For small panes, compact btop starts with CPU only. Press `p` or `Shift+p` inside btop to switch to memory/disks, network, or processes. The full-view default preset is excluded from this compact cycle. Toggle individual sections with `1`–`4` if the pane has enough room. Process view needs more height than CPU/network; enlarge or fullscreen the pane when needed. Start a specific view with `command-center run btop --compact --preset 2` (memory/disks), `--preset 3` (network), or `--preset 4` (processes). Ordinary `command-center run btop` retains the original full configuration.

To launch configured tools in the current shell pane, use `command-center run TOOL`; trailing arguments go directly to that tool. This does not require Zellij. In particular, use `command-center run newsboat`: plain `newsboat` reads its own separate default configuration/feed file, which may be empty. The configured runner and new-pane launcher share the same feeds and read-state. Shell startup files and global tool settings are preserved.

## Agent and optional-tool choices

The starter AGENTS tab includes Hermes, OpenCode, Pi, and Codex CLI. Rename, remove, or duplicate any pane. Multiple Hermes panes start separate conversations while sharing your existing provider configuration and potentially persistent memory. Distinct panes do not isolate files or shared settings; use separate Git worktrees for concurrent edits.

Optional tools can be installed separately:

```sh
brew install yazi
brew install lazydocker
```

Lazydocker additionally needs an installed CLI and running Docker-compatible engine. Configure that separately when you want container work. Neovim is not part of this setup; use your preferred editor whenever manual editing is needed.

## Moving the checkout

The installation manifest, launcher links, Ghostty include, and saved command paths refer to this checkout's absolute location. Uninstall before moving it, then install from the new location. Existing exported layouts containing the old command path need that path updated too. Personal preferences and read-state are retained by uninstall.
