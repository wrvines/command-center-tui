# App menu and searchable catalogs

Inside the command center, press **Ctrl+g, then a** to open the floating app menu. Or run:

```sh
command-center apps
command-center catalogs
```

The app menu lists configured tools, saved launchers, and installed command names matched against cached terminal-tool catalogs. **Ctrl+R** rescans PATH, common installation folders, and your saved search folders. **Add to apps…** handles unmatched commands; each app also offers removal/uninstall actions. See [discovery, registration, search folders, and uninstall](app-discovery.md).

Choose **Browse catalogs…**, pick a catalog, type to search its names/descriptions/categories, and use the arrows to move. The preview shows the selected tool's description and link as text. Press **Ctrl+P** to hide/show the preview, **Ctrl+R** to refresh that catalog, and **Esc** to go back or close the menu.

**abtop (AI agents)** is a configured optional app. After installing `abtop` separately and making it available in the search folders, close and reopen the app menu to see it. It supports tiled, floating, and menu-pane launches, plus `command-center run abtop` and `command-center pane abtop`.

**Amp editor** is another configured optional app (`brew install amp`). It runs the `amp` terminal text editor, supports the same pane options, and appears after reopening the menu when installed. Use `command-center run amp -- file.txt` to edit a particular file in the current shell pane, or `command-center pane amp` for a new editor pane.

In a new premade workspace, press **Enter** in an unassigned pane to choose an app directly for that pane. This starter picker lists available apps, Shell, and Weather; it returns to a shell on cancel or app exit. `command-center apps --pick` opens the same picker in a shell. Use the regular app menu above for catalog browsing, registration, and uninstall actions.

## Available catalogs

| Source | CLI identifier | What is searched |
| --- | --- | --- |
| [Terminal Trove](https://terminaltrove.com/list/) | `terminal-trove` | Its full A–Z index where accessible; otherwise its published recent-tools feed |
| [Awesome TUIs](https://github.com/rothgar/awesome-tuis) | `awesome-tuis` | The community list's names, descriptions, categories, and project links |
| [Awesome CLI/TUI Apps](https://github.com/toolleeo/awesome-cli-apps-in-a-csv) | `awesome-cli` | The broader collection's structured CSV data |
| [Homebrew Formulae](https://formulae.brew.sh/) | `homebrew` | Homebrew/core package names and descriptions, including non-TUI programs and libraries |

Each source stays separate. Homebrew is a general package directory, not a guarantee that a package has an interactive interface. Catalog listings do not guarantee compatibility with the current OS; consult the project/formula page before installation.

Terminal Trove may require a browser challenge for its full index. In that case the menu uses its [published new-tools Atom feed](https://terminaltrove.com/new.xml), and prominently displays **recent feed (full index unavailable)**. This is a limited recent list, not the complete catalog. An existing full-index cache is retained instead of being replaced by a smaller feed. Source failures offer retry/back and an explicit browser option; browsing otherwise stays in the terminal.

## Search a particular source

```sh
command-center catalogs --source awesome-tuis
command-center catalogs --source awesome-cli --query calendar
command-center catalogs --source homebrew --query terminal
command-center catalogs --source terminal-trove --refresh
```

Noninteractive lists do not need fzf or Zellij:

```sh
command-center catalogs --list
command-center catalogs --source awesome-tuis --query monitor --list
```

Interactive catalog browsing uses fzf's fuzzy matching. **Search Homebrew for this name** instead matches the entered text only within package names, ignoring case; scattered letters and package descriptions do not produce matches. `--query` initializes ordinary catalog browsing; with `--list` it performs a plain case-insensitive substring match. Queries filter locally and are not sent to the catalog providers. Indexes are fetched on demand and cached for 24 hours; nothing polls in the background. Download failures retain the last good cache and label it **STALE CACHE** with its timestamp. Invalid or empty downloads do not replace valid cached data.

## Launch a tool or install a package

For configured installed apps, **Enter** opens the action list with **Open in new tiled pane** selected first. **Open floating** is an alternative. A typed `command-center apps` offers **Open in current pane** for the terminal where you typed the command; the app-menu shortcut offers the same choice for the workspace pane behind its floating menu. Standalone catalogs offer **Use menu pane** for the pane hosting that catalog menu. A successful launch closes the menu. Configured launches retain this setup's Newsboat feeds, compact btop preferences, and other supported adapters.

When you type `command-center apps` interactively inside Zellij, installed-app actions offer **Open in current pane**. It closes the floating menu and runs the selected app in the pane where you typed the command, preserving that working directory and returning to your shell when the app exits. The command waits while its menu is open; canceling returns to the shell without launching anything. This target is preserved when you browse catalogs from the app menu, including a Homebrew search reached from another catalog. The app menu does not offer a separate floating menu-pane replacement action when it has an original/workspace target; **Open floating** remains available.

Menus opened with **Ctrl+g → a**, or an owned floating app-menu pane, use the focused workspace pane in the same tab for **Open in current pane**. Zellij temporarily uses that pane's space, preserving its previous shell/app in the background; exiting the selected app restores it. A missing or ambiguous target is rejected rather than launching in the floating menu. No restart is needed after updating the launcher; close and reopen the menu to load the change.

**Use menu pane** means the pane hosting the menu. When the menu was opened as a floating panel, the tool uses that floating panel. To launch into an existing empty shell pane instead, run:

```sh
command-center apps --inline
# Or browse catalogs in that shell pane:
command-center catalogs --inline
```

Then select **Use menu pane**. This runs the app as a foreground command and returns to the parent shell when it exits. It never sends a launch command into another pane's running program. From an ordinary terminal outside Zellij, only the current-pane launch is available. An explicitly inline picker typed inside an ordinary floating shell also stays in that shell; it is not treated as a floating menu created by the launcher.

For unfamiliar listings, read the preview and project link first. The non-Homebrew catalogs offer **Search Homebrew for this name**; this is a search, not an assumed package mapping. The **Package name** prompt searches Homebrew/core package names. If there are no matches, edit the name or press **Esc**, then choose **Open project / formula page in browser** for installation instructions. Some apps require a different package name, a custom Homebrew tap, or another installation method. Homebrew entries show their exact installation command. Select **Install with Homebrew…**, then choose the named package to confirm. After installation, an unambiguous executable is registered automatically; a package containing several plausible commands offers a command picker. Packages use Homebrew's normal directories and updates; authentication/setup remains with the tool. Installation does not launch the app automatically. Catalog names are matched to actual installed files; downloaded descriptions are never interpreted as commands.

Saved app registration is available through **Add to apps…** and `command-center apps add`. A saved-setup picker remains future work. Existing `command-center save-layout NAME`, `--layout NAME --session NAME`, and session reattachment continue to work. See [workspace customization](customization.md).

## macOS, Linux, and Windows/WSL

The shared menu uses Python 3.9+, curl, and **fzf**. Installers now include fzf among the core dependencies. Existing installations can add it with `brew install fzf`, or use the Linux distribution's fzf package and `./install.sh --no-dependencies`.

On Windows, open the installed WSL 2 distro in Windows Terminal and run `~/.local/bin/command-center catalogs`. The same shortcut works inside that distro's command-center session. Homebrew package installation requires Homebrew inside WSL/Linux; a distro-managed setup can browse every catalog without using Homebrew installs. Opening project links uses macOS `open`, Linux `xdg-open`, or `wslview` when available.

New sessions receive the shortcut through the generated scoped Zellij config. For an older session, `command-center apps` works without a new keybinding; regenerating that session's scoped config or starting a new named session makes the shortcut available. No shell startup or global Zellij configuration is edited.

Catalog caches are under `~/Library/Caches/command-center/catalogs/` on macOS and `$XDG_CACHE_HOME/command-center/catalogs/` on Linux/WSL (default `~/.cache/command-center/catalogs/`). They contain public metadata only and are not tracked in Git. Removing those cache files forces fresh downloads next time. Uninstalling retains installed packages; removing a menu entry or closing a pane does not uninstall a tool.
