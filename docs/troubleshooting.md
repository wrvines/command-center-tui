# Troubleshooting and rollback

## Command not found

Run `./install.sh` from this checkout, or use `install.ps1` for a Windows checkout bridged to WSL 2. The launcher links are placed at `~/.local/bin/command-center` and `~/.local/bin/ccenter` inside the runtime OS. The original Mac's existing `~/.zprofile` adds that directory to PATH. A new terminal window will load it; an older shell can launch the absolute path directly:

```sh
~/.local/bin/command-center
```

The installer refuses to overwrite a command-name collision. The project does not claim `cc`, which already names the macOS C compiler. Moving or deleting this checkout breaks the symlinks and include; reinstall from its new location as described in customization.

## Controls appear to do nothing

Check the status bar. In locked mode, application input goes to the focused program. Press Ctrl+g to unlock, then use the native mode shortcuts. Press Ctrl+g again or finish an action to return to the application. Enter in a navigation mode finishes navigation; another Enter starts a suspended tool.

Increase the window size if pane text is cramped. Fullscreen the focused pane with Ctrl+g, Ctrl+p, f. The setup does not depend on Option/Alt shortcuts or a Nerd Font.

## Session or tool problems

Run `command-center doctor`. Install missing core dependencies with `./install.sh`; the [installation guide](install.md) explains Homebrew and manual package-manager options. A missing optional tool leaves a usable shell. The launcher rejects nesting in Zellij or tmux; use `command-center pane TOOL` inside the workspace, or launch from a normal terminal shell.

Selecting `--layout` for an existing session reconnects without replacing its arrangement. Choose a new `--session` name to try a different layout. Zellij's native `zellij list-sessions` shows running and exited sessions. The command-center launcher supplies an explicit configuration directory so Zellij 0.45.1 can resolve its saved layout during resurrection without a global Zellij config.

If a saved working directory was moved or removed, restore that directory or edit the saved KDL `cwd` paths. Layout export preserves structure and commands, not process memory or AI conversation state. Resume Hermes by a specific session ID in the intended pane. Provider authentication and model access remain each agent's own configuration; the setup tests do not send AI prompts.

A session-list operation that exceeds ten seconds stops with an error rather than leaving the launcher hung. Diagnose it with Zellij's own session tools; do not delete all sessions as a repair step.

## Weather or feeds unavailable

Weather has bounded curl timeouts and uses a timestamped stale forecast when possible. The remote wttr.in service can fail independently of the workspace. Check `preferences.json`, connectivity, and `command-center weather --refresh`. The default location is 84121.

Newsboat's R command reloads feeds. Edit `~/.config/command-center/feeds` to replace unavailable feeds. Its cache and history are under `~/Library/Application Support/command-center/newsboat/`; do not remove them just to change feed appearance. Newsboat may create its empty default `~/.newsboat` startup directory even with explicit configuration/state arguments; this project does not install settings there.

On Linux/WSL, cache/history are under `$XDG_DATA_HOME/command-center/newsboat/` (default `~/.local/share/command-center/newsboat/`). Use the paths printed by `command-center doctor` when XDG settings are customized. Linux feed links use `xdg-open`; a WSL browser bridge can be set in your private Newsboat config.

## Ghostty configuration

Reload appearance using Cmd+Shift+, or open a new window. The existing theme remains GitHub Dark High Contrast; the managed include only adds padding. Ghostty's CLI emitted `SentryInitFailed` during the initial sandbox inspection, while its version/theme and include validation were usable. Native Ghostty UI automation was unavailable during validation; inspect final appearance in your own window.

## Safe uninstall

From this checkout:

```sh
./uninstall.sh --dry-run
./uninstall.sh
```

The manifest is `~/Library/Application Support/command-center/install-manifest.json`. Both original Ghostty files were backed up in a timestamped directory beneath `backups/`. The legacy file was never modified. A successful uninstall restores the modern file byte-for-byte and removes the two managed links. Packages, preferences, feeds, saved layouts, caches, and backups remain.

On Linux/WSL the manifest defaults to `~/.local/share/command-center/install-manifest.json`. A Linux installation restores whichever Ghostty file it integrated; `--no-ghostty` records only the launcher links. For a Windows checkout use `./uninstall.ps1 -Distro Ubuntu` with `-DryRun` to preview. See [platform paths and uninstall](install.md).

Rollback checks every managed target and backup before changing anything. If you edited the modern Ghostty file after installation, it refuses to replace that file. To preserve those later edits, review the manifest and remove just the block between `# BEGIN command-center (managed)` and `# END command-center (managed)` manually. Review the recorded launcher targets before removing their symlinks manually. Retain the manifest and backups as the ownership record; do not fake its checksums to force a restore.

If an installation was interrupted, inspect `install-manifest.json` and its recorded target paths before retrying. An `install.lock` directory prevents concurrent operations; remove a stale lock only after confirming no installer is running. The installer attempts rollback for ordinary failures and never automatically uninstalls packages.
