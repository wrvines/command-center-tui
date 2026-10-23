# Installed apps, saved launchers, and removal

Open `command-center apps` (or Ctrl+g, then a). Installed apps from cached terminal-tool catalogs now appear alongside built-in launchers and your saved apps. Press **Ctrl+R** to rescan, or close and reopen the menu after an external installation. No installed program is run during discovery.

## Where discovery searches

The app menu scans absolute directories in its effective `PATH`, then `~/.local/bin`, `~/.cargo/bin`, `~/go/bin`, and folders you have saved. It checks only files directly in those folders. Symlinked executables are supported; duplicate command names follow search-path order. Use **Search folders… → Add search folder…** for an unusual installation location. Select a saved folder again to remove it from the search list.

Names are matched against locally cached Terminal Trove, Awesome TUIs, and Awesome CLI/TUI Apps catalogs. Browsing a catalog populates its cache; **Refresh discovery catalogs…** downloads those three sources explicitly. Ordinary app rescans are offline. The Homebrew catalog is not used as an app allowlist because it includes libraries and helper utilities. Terminal Trove's recent-feed fallback limits what can be matched from that source. Known multiplexer commands are excluded from automatic discovery to avoid accidental nesting.

Catalog names can differ from executable names. Catalogs also include CLI utilities, so recognition does not guarantee an interactive TUI. On macOS, automatic matching skips protected system-command folders (`/usr/bin`, `/bin`, `/usr/sbin`, `/sbin`) to avoid collisions such as Apple's `vis` utility versus the Vis editor. Linux/WSL keeps those folders eligible because distribution packages install terminal apps there. **Add to apps…** lists installed commands, including ones that could not be matched automatically. Choose one and optionally save arguments and a display name, or select **Enter a command or executable path…** for an app elsewhere. Quote paths containing spaces. Commands and arguments are saved separately; shell operators are not interpreted.

## Homebrew installation

After a confirmed Homebrew install from a catalog, Command Center inspects that formula's `bin` directory. It adds the command automatically when its name matches the package name or the package has only one executable. Otherwise, it asks which command to add. You can skip that choice and use **Add to apps…** later. Existing built-in launchers retain their configured feeds/preferences. Installing a library with no executable does not create an app entry.

The next app-menu view includes the new registration. Installation does not automatically launch the app. Packages installed with `brew install` outside Command Center are handled like other external installations: cached catalog matching or a one-time saved registration.

## Saved app launchers

Saved and discovered apps offer tiled, floating, and current-pane launches. The floating app-menu shortcut targets the workspace pane behind its menu and restores the previous shell/app when the selected app exits. When you type `command-center apps` interactively inside Zellij, they also offer **Open in current pane** to run in the shell pane that opened the menu. A discovered command is saved when opened in a new pane so its executable and arguments remain available to saved layouts. Built-in adapters continue to load their existing private settings. Missing saved executables are labeled **Unavailable** and remain removable; another command is not silently substituted.

The CLI supports the same registry:

```sh
command-center apps --list
command-center apps folders
command-center apps add-folder "$HOME/Applications/terminal-tools"
command-center apps remove-folder "$HOME/Applications/terminal-tools"
command-center apps add my-tool -- /absolute/path/to/tool --option "value with spaces"
command-center run my-tool -- additional-argument
command-center pane my-tool --floating
```

`apps add` can also resolve a command name in the search folders. Replacing an existing registration with different arguments requires `apps add --replace NAME -- COMMAND ...`, or an explicit replacement selection in the menu. Changing a launch command clears its previous manual uninstall recipe so a replacement app cannot inherit an unrelated removal command. App names used by built-in adapters cannot be overwritten. A saved executable uses its absolute installation path; Homebrew symlink paths remain usable after normal package updates.

## Remove, restore, or uninstall

Select an app to see these actions:

- **Remove from apps (keep installed files)** hides its launcher. It stays hidden through rescans and restarts. **Restore hidden apps…** shows it again, with saved arguments intact.
- **Uninstall…** identifies Homebrew ownership from the executable's location in Homebrew's Cellar. It displays the exact package and `brew uninstall --formula PACKAGE` command before a separate confirmation. Package dependencies are not forcibly removed. A failed uninstall keeps the launcher.
- **Set uninstall command…** saves an optional uninstall command for a manual installation, such as its package manager's uninstall command. **Uninstall…** then displays that saved command before confirmation. Command Center does not guess a deletion command or extract executable recipes from webpages.

For a manual install without a saved uninstall command, the menu shows the executable location and directs you to the original installer/package manager. Removing the launcher remains available. Uninstall commands may have their own effects on app data; Command Center itself retains its preferences, saved layouts, and registry.

```sh
command-center apps remove my-tool
command-center apps restore my-tool
command-center apps set-uninstall my-tool -- /absolute/path/to/package-manager uninstall PACKAGE
command-center apps uninstall my-tool
```

The registry is private: `~/.config/command-center/apps.json` on macOS; `$XDG_CONFIG_HOME/command-center/apps.json` on Linux/WSL (default `~/.config/command-center/apps.json`). `COMMAND_CENTER_HOME` redirects it to `config/apps.json` for isolated checks. Updates are atomic, file permissions are private, and invalid settings are reported without being overwritten. Normal app scans do not edit shell startup files or install packages.

## Local and remote hosts

Discovery, registrations, and uninstall commands belong to the machine running Command Center. An SSH connection does not share installed programs or their registry. Install an app on the server when it needs access to server processes or local session files. For example, remote agent monitoring needs a remote abtop instance. Multi-host aggregation is a separate roadmap item.
