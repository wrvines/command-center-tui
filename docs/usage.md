# Everyday use

Open Ghostty normally. It runs your ordinary zsh shell. Launch individual coding agents there whenever you want, or type `command-center` (short form: `ccenter`) to enter the workspace.

## First launch

DEV is selected first. The large pane is a shell in the directory from which you launched. Run your coding agent or project command there. To select AGENTS, press Ctrl+g, then 3. Its four panes are initially suspended: focus one and press Enter to start its tool.

The AGENTS tab is a convenient starter layout, not a limit of four agents. Open additional Hermes, OpenCode, Pi, or Codex panes using the commands below, or split a normal shell and run any CLI yourself. Every `hermes chat` invocation starts fresh; resuming an existing conversation is an explicit action.

## Keyboard controls

Ctrl+g toggles application input (locked mode) and Zellij controls (normal mode). The status bar identifies the current mode. Starting from locked mode:

| Purpose | Sequence |
| --- | --- |
| Open the searchable app / catalog menu | Ctrl+g, a |
| Select the five starter tabs | Ctrl+g, then 1, 2, 3, 4, or 5 |
| Focus a different panel | Ctrl+g, Ctrl+p, arrow keys, Enter |
| Split right | Ctrl+g, Ctrl+p, r |
| Split below | Ctrl+g, Ctrl+p, d |
| Add a pane automatically | Ctrl+g, Ctrl+p, n |
| Close a pane | Ctrl+g, Ctrl+p, x |
| Float or tile the focused pane | Ctrl+g, Ctrl+p, e |
| Toggle floating panels | Ctrl+g, Ctrl+p, w |
| Toggle pane fullscreen | Ctrl+g, Ctrl+p, f |
| Resize | Ctrl+g, Ctrl+n, arrows or + / -, Enter |
| Move | Ctrl+g, Ctrl+h, arrows, Enter |
| New tab | Ctrl+g, Ctrl+t, n |
| Rename a tab | Ctrl+g, Ctrl+t, r, type the name, Enter |
| Rename a pane | Ctrl+g, Ctrl+p, c, type the name, Enter |
| Scroll output | Ctrl+g, Ctrl+s, arrows or PageUp/PageDown, Enter |
| Open native session manager | Ctrl+g, Ctrl+o, w; Ctrl+g to relock after closing it |
| Return to your normal terminal | Ctrl+g, d |

Enter finishes navigation and returns to locked mode. If the newly selected tool is suspended, press Enter again to start it. You can also select panes with the mouse. Hold Shift to bypass Zellij mouse handling for terminal selection when needed; copied Zellij selections use macOS `pbcopy`.

Linux uses Zellij's terminal clipboard protocol; WSL uses `clip.exe` when available. The same launcher and controls work inside a WSL 2 distro opened in Windows Terminal. See [platform installation](install.md).

The stock Ctrl-mode shortcuts remain available. Single-action pane shortcuts such as split, close, fullscreen, and float return to locked mode automatically. Closing a panel ends its process. Detaching leaves the whole session running; opening a fresh Ghostty window still gives you an ordinary terminal.

## Add panels and workspaces

Use `command-center apps` for the floating installed-app menu or `command-center catalogs` to choose between Terminal Trove, Awesome TUIs, Awesome CLI/TUI Apps, and Homebrew. Type to search within the selected catalog. Ctrl+R refreshes, Ctrl+P toggles the text preview, and Esc goes back. New tiled panes are the default for configured app launches, with floating/current-menu-pane options. `--inline` runs the picker in an existing shell pane. See [catalog usage](catalogs.md), including the limited recent-feed fallback if Terminal Trove blocks its full index.

Run these inside a shell pane:

```sh
command-center pane codex --floating
command-center pane pi --direction right
command-center pane opencode --direction down
command-center pane hermes --direction right
command-center pane lazygit --floating
command-center pane weather --floating
command-center add-workspace system
command-center add-workspace news-weather --cwd "/path/to/project"
```

`pane` starts the requested tool immediately because the command is your explicit choice. Template panes start suspended. Any program can run in a normal shell pane; convenient tool shortcuts do not limit customization.

Lazygit uses the current directory unless `--cwd` is supplied. A directory outside Git leaves a helpful shell. Optional Yazi or lazydocker panes also fall back to a shell when unavailable. Container tools never start an engine for you.

## Save and return

```sh
command-center save-layout my-desk
command-center layouts
```

Detach with Ctrl+g, d, then run `command-center` again to reconnect. A named session keeps its live changes even if you request a different starting layout. For a separate session:

```sh
command-center --session work --project "/path/to/work"
command-center --layout my-desk --session my-desk
command-center --workspace system
command-center reset
```

`command-center reset` is equivalent to `command-center --session fresh-start`. Run it from an ordinary terminal after detaching. It creates the starter five-tab arrangement if that session does not exist; otherwise it reconnects to or restores `fresh-start` with its saved arrangement. It preserves other sessions and tool settings. Use another unused session name when you want an untouched starter arrangement again.

This works on macOS, Linux, and inside Windows/WSL 2. In Windows Terminal, open the installed Linux distro and use `~/.local/bin/command-center reset` if the launcher directory is not on PATH. Reset is not a native PowerShell command. See [platform installation and updates](install.md).

After a reboot or session exit, the launcher uses Zellij's saved metadata to reconstruct panes and tabs. Suspended commands wait for Enter. Tool process memory and running jobs do not survive reboot. Saved layouts keep their captured directories and command structure.

Hermes conversation history is separate. Resume a particular conversation using its session ID, for example `hermes --resume SESSION_ID` in an appropriate shell pane. Do not use a shared “latest” resume command for all agents. Keep editing agents in separate Git worktrees when their tasks overlap.

## News, weather, and operations

Newsboat refreshes the selected feeds when you start its panel, with 15-second per-download timeouts. Shift+R refreshes all feeds; r refreshes the selected feed. Enter opens a feed or article, q returns, and ? shows Newsboat's help. Article read-state lives in the command-center data directory and is retained across launches.

The weather panel displays an on-demand forecast and leaves a shell below it. Weather uses postal code 84121, caches for 30 minutes, and has a 15-second curl request limit. Refresh with:

```sh
command-center weather --refresh
```

A failed request shows an older forecast with a STALE label if available. No timer or daemon keeps fetching while the panel is hidden. Change the location in `~/.config/command-center/preferences.json`.

OPERATIONS leaves service and log selection to you. Use `tail -F` for your own log, `brew services list` for Homebrew service inspection, or your project's usual commands. The layout does not guess a build command or start containers/services.
