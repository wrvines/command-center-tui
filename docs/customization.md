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

## Tool preferences

Editable local defaults are copied once into `~/.config/command-center/`. Changing the repository defaults does not overwrite those local files. The normal mapping is:

- `preferences.json`: weather location and cache seconds.
- `feeds`: one RSS URL per line, with optional tags and quoted `~Title` labels.
- `btop.conf`: colors, display boxes, and refresh rate; btop saves its own UI changes here.
- `btop-compact.conf`: separate small-pane presets; used by `command-center run btop --compact` or `command-center pane btop --compact`.
- `newsboat.conf`: feed refresh and Newsboat appearance.
- `lazygit.yml`: Git UI appearance and behavior.

The btop theme file is under `config/btop/themes/`. Zellij's theme and keyboard settings are under `config/zellij/config.kdl`. Restart a session to reliably apply startup-only Zellij changes. The Ghostty include changes padding; your original theme and font remain in the existing Ghostty config.

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
