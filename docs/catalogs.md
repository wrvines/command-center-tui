# App menu and searchable catalogs

Inside the command center, press **Ctrl+g, then a** to open the floating app menu. Or run:

```sh
command-center apps
command-center catalogs
```

The app menu lists this setup's configured tools that are found on PATH, plus **Browse catalogs…**. It does not claim to detect every TUI installed on the machine. Choose a catalog, type to search its names/descriptions/categories, and use the arrows to move. The preview shows the selected tool's description and link as text. Press **Ctrl+P** to hide/show the preview, **Ctrl+R** to refresh the catalog, and **Esc** to go back or close the menu.

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

Interactive search uses fzf's fuzzy matching. `--query` initializes that search; with `--list` it performs a plain case-insensitive substring match. Queries filter locally and are not sent to the catalog providers. Indexes are fetched on demand and cached for 24 hours; nothing polls in the background. Download failures retain the last good cache and label it **STALE CACHE** with its timestamp. Invalid or empty downloads do not replace valid cached data.

## Launch a tool or install a package

For configured installed apps, **Enter** opens the action list with **Open in new tiled pane** selected first. Floating and **Use menu pane** are alternatives. A successful launch closes the menu. Configured launches retain this setup's Newsboat feeds, compact btop preferences, and other supported adapters.

**Use menu pane** means the pane hosting the menu. When the menu was opened as a floating panel, the tool uses that floating panel. To launch into an existing empty shell pane instead, run:

```sh
command-center apps --inline
# Or browse catalogs in that shell pane:
command-center catalogs --inline
```

Then select **Use menu pane**. This runs the app as a foreground command and returns to the parent shell when it exits. It never sends a launch command into another pane's running program. From an ordinary terminal outside Zellij, only the current-pane launch is available.

For unfamiliar listings, read the preview and project link first. The non-Homebrew catalogs offer **Search Homebrew for this name**; this is a search, not an assumed package mapping. Homebrew entries show their exact installation command. Select **Install with Homebrew…**, then choose the named package to confirm. Packages use Homebrew's normal directories and updates; authentication/setup remains with the tool. Installation does not automatically launch the result or add unknown executable names to the configured app menu. The menu only executes known launch adapters; it never treats downloaded catalog descriptions as commands.

Arbitrary app registration and a saved-setup picker remain future work. Existing `command-center save-layout NAME`, `--layout NAME --session NAME`, and session reattachment continue to work. See [workspace customization](customization.md).

## macOS, Linux, and Windows/WSL

The shared menu uses Python 3.9+, curl, and **fzf**. Installers now include fzf among the core dependencies. Existing installations can add it with `brew install fzf`, or use the Linux distribution's fzf package and `./install.sh --no-dependencies`.

On Windows, open the installed WSL 2 distro in Windows Terminal and run `~/.local/bin/command-center catalogs`. The same shortcut works inside that distro's command-center session. Homebrew package installation requires Homebrew inside WSL/Linux; a distro-managed setup can browse every catalog without using Homebrew installs. Opening project links uses macOS `open`, Linux `xdg-open`, or `wslview` when available.

New sessions receive the shortcut through the generated scoped Zellij config. For an older session, `command-center apps` works without a new keybinding; regenerating that session's scoped config or starting a new named session makes the shortcut available. No shell startup or global Zellij configuration is edited.

Catalog caches are under `~/Library/Caches/command-center/catalogs/` on macOS and `$XDG_CACHE_HOME/command-center/catalogs/` on Linux/WSL (default `~/.cache/command-center/catalogs/`). They contain public metadata only and are not tracked in Git. Removing those cache files forces fresh downloads next time. Uninstalling retains installed packages; removing a menu entry or closing a pane does not uninstall a tool.
