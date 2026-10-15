# Unified terminal theme

`oh-my-pi` is an opt-in command-center palette inspired by [Oh My Pi's dark-terminal](https://github.com/can1357/oh-my-pi/blob/main/packages/tui/src/theme/defaults/dark-terminal.json). The user's nine colors below are authoritative. This is an adaptation, not a copy of every upstream color: upstream has additional message backgrounds and a different ANSI palette.

Ghostty renders the colors on the MacBook Air, including output arriving over SSH from the Debian Lenovo. Zellij and individual applications can draw their own UI colors, so each needs a matching adapter. SSH does not synchronize application themes. Debian does **not** need Ghostty installed.

## Source and adapters

| Role | Hex | Use |
| --- | --- | --- |
| Background | `#050505` | Terminal and ordinary UI background |
| Foreground | `#cccccc` | Ordinary text |
| Primary | `#00ff00` | Cursor, active tab, focused frame, success |
| Secondary | `#00aaff` | Secondary emphasis, headings and links |
| Cyan | `#00ffcc` | Highlights and frame control mode |
| Error | `#ff0000` | Failures and removed content |
| Warning | `#ffff00` | Warnings and changed content |
| Muted | `#666666` | Dim text and ANSI bright black |
| Border | `#333333` | Inactive frames and selection background |

- `config/themes/oh-my-pi.json` is the reusable source of truth, with semantic roles and a 16-slot ANSI role mapping.
- `config/ghostty/themes/OhMyPi-DarkTerminal` is a complete Ghostty color-only theme, including cursor, selection, and all 16 ANSI slots.
- `config/zellij/themes/oh-my-pi.kdl` defines the `oh-my-pi` theme with explicit Zellij UI components, including focused/unfocused frames, tabs, lists, and exit codes.
- `scripts/themes.py` generates these adapters inside the checkout. It never installs or activates them.

ANSI slots 0–7 are background, error, primary, warning, secondary, secondary, cyan, foreground. Slots 8–15 repeat those roles with muted replacing background. Both magenta slots deliberately use secondary blue; bright colors reuse the supplied colors instead of inventing extra shades. Programs that depend on a separate magenta hue will therefore look different. The extended 256-color palette remains Ghostty's default; indexed colors above 15 are not recolored by this adapter.

After editing the JSON:

```sh
python3 -B scripts/themes.py
python3 -B scripts/themes.py --check
./scripts/validate.sh
```

Review and commit the source and generated adapters together. `--check` detects drift without writing. Existing defaults, tool preferences, layouts, shell startup, and installer ownership rules are preserved.

## Review and try on macOS

No live configuration was changed while implementing this feature. Review the adapters and these steps before running activation commands. Keep the checkout in its permanent location.

For a one-off Ghostty preview, run from the checkout on the Mac:

```sh
open -na /Applications/Ghostty.app --args --theme="$PWD/config/ghostty/themes/OhMyPi-DarkTerminal"
```

This opens a separate Ghostty instance without editing configuration. Existing explicit `background`, `foreground`, `palette`, cursor, or selection settings override theme values, so inspect those if a color differs. A user-configured opacity below 1 also changes the perceived background. Close the preview instance to end this trial.

In an ordinary terminal, outside any multiplexer, start a **previously unused** command-center session:

```sh
command-center --theme oh-my-pi --session theme-preview
# Or, before installing the launcher links:
./bin/command-center --theme oh-my-pi --workspace system --session theme-system
```

Put global flags before subcommands, e.g. `command-center --theme oh-my-pi doctor`. The selector writes only the project's generated `zellij/platform-oh-my-pi.kdl` when you invoke it. The existing `platform.kdl`, global Zellij configuration, and private tool preferences are untouched. The scoped config-dir used for session resurrection is retained.

An existing live or resurrected session retains its own configuration and arrangement; the flag is intended for new sessions. Reusing a session name is not a reliable theme switch. Detach with Ctrl+g → d to leave tools running. Omitting `--theme` (or using `--theme command-center`) retains the original palette for new sessions. `command-center reset` still reuses `fresh-start`; it is not a theme reset.

### Make Ghostty persistent after review

Use an absolute theme path to the checkout. [Ghostty accepts absolute theme paths](https://ghostty.org/docs/features/theme); this avoids installing another theme copy or a competing config in `~/.config/ghostty/`.

On this Mac, both `~/Library/Application Support/com.mitchellh.ghostty/config` and `config.ghostty` exist. Back up both to a new, uniquely named backup directory before editing. Inspect any XDG config and included files too, if present. Keep the legacy file, padding include, fonts, keybindings, and startup command intact.

**If command-center is already installed with Ghostty integration, first run `./uninstall.sh --dry-run` and review its plan, then `./uninstall.sh`.** This ends ownership of the exact installed config bytes before a manual edit. Uninstall leaves packages, sessions and preferences in place. If it detects later edits, stop and reconcile them using [troubleshooting](troubleshooting.md); do not bypass the manifest check. Do not edit a managed file and then expect the old manifest to accept it.

In the existing active modern config, replace only the existing theme selection (record its exact previous value, currently `GitHub Dark High Contrast` on the original Mac):

```ini
theme = /Users/williamvines/Documents/ChatGPT/command-center/config/ghostty/themes/OhMyPi-DarkTerminal
```

Use your actual absolute checkout path on another Mac; do not paste the original Mac's path there. Inspect explicit color overrides before removing or changing any of them. Validate before reloading:

```sh
/Applications/Ghostty.app/Contents/MacOS/ghostty +validate-config \
  --config-file="$HOME/Library/Application Support/com.mitchellh.ghostty/config.ghostty"
./install.sh --no-dependencies --dry-run
./install.sh --no-dependencies
```

The reviewed reinstall records the new baseline and restores launcher links and the padding include. Reload Ghostty configuration with its **Reload Configuration** action, or open a new window if needed. Other terminals and explicitly themed applications retain their own settings. Do not put a theme setting into `config/ghostty/command-center.ghostty`; that shared include remains padding-only.

For rollback, uninstall the managed integration through its ordinary checks, restore just the recorded prior theme selection, validate, then reinstall and reload. If other settings changed since your backup, merge only the theme change; do not overwrite the whole file. The installer does not own the manual theme selection and will not revert it automatically. Reattaching to an existing themed session does not revert its appearance; use a new session with the default selector.

## Debian Lenovo over SSH

Run Ghostty on the **Mac**. On Debian, use existing distro-managed tools or install the prerequisites described in [installation](install.md); confirm `python3`, Git, curl, btop, Newsboat, Lazygit and **Zellij 0.45.1+** are available. Older Debian Zellij packages may need a separate upgrade. No dependency or SSH setting is changed automatically by the theme feature.

If you want command-center on the Lenovo, clone into a permanent directory **there**, then review and run:

```sh
./install.sh --no-dependencies --no-ghostty --dry-run
./install.sh --no-dependencies --no-ghostty
zellij --version
./scripts/validate.sh
command-center --theme oh-my-pi --session lenovo-themed
```

The validator reports Ghostty checks skipped when Ghostty is absent, which is expected on this host. macOS/Linux config variants were parsed locally on the Mac; actual Debian execution and display still require testing on the Lenovo. Run the command above from a direct SSH shell outside Zellij/tmux to avoid nesting multiplexers. Alternatively keep Zellij on the Mac and run SSH inside a pane; then remote apps inherit that pane's terminal environment and only remote app adapters/terminfo need attention.

Check the terminal advertised by the actual connection on Debian:

```sh
printf 'TERM=%s COLORTERM=%s\n' "$TERM" "${COLORTERM-}"
infocmp -x "$TERM" >/dev/null
tput colors
```

Direct Ghostty SSH normally advertises `xterm-ghostty`; inside Zellij the advertised terminal can differ. Do not globally hardcode `TERM` in shell startup files. `tput colors` reporting 256 does not by itself disprove truecolor support.

If Debian lacks `xterm-ghostty`, install only its terminfo entry for your account. From a **direct ordinary Ghostty shell on the Mac**, after reviewing the destination, use the [Ghostty terminfo method](https://ghostty.org/docs/help/terminfo) with an explicit user directory:

```sh
infocmp -x xterm-ghostty | ssh user@lenovo 'tic -x -o "$HOME/.terminfo" -'
ssh user@lenovo 'infocmp -x xterm-ghostty >/dev/null'
```

Replace `user@lenovo` with your SSH destination. Inspect/back up any existing entry first; run this only if it is missing. Debian's `ncurses-bin` supplies `infocmp`, `tic`, and `tput`. This transfers terminal capability metadata, not colors. If the local lookup fails, inspect Ghostty's bundled terminfo at `/Applications/Ghostty.app/Contents/Resources/terminfo/` with `infocmp -A` rather than installing Ghostty remotely. If SSH starts inside Zellij and Debian lacks the advertised entry, transfer that exact entry instead; do not relabel it as `xterm-ghostty`.

For applications that explicitly require `COLORTERM`, test `COLORTERM=truecolor my-tui` for that invocation after checking that the terminal chain supports it. No global export, `sshd` change, or remote profile rewrite is needed just to select this theme. Apps emitting their own RGB values still need their own palette adapters; neither `TERM` nor `COLORTERM` selects an application theme.

## Extend to other TUI applications

Prefer terminal default foreground/background and the shared 16 ANSI slots when an application supports them. For apps that require explicit RGB, add an adapter in `scripts/themes.py` that maps semantic roles to the app's native keys and write the generated default under `config/<app>/`. Avoid embedding a second palette in layouts or scripts.

For example, a future adapter can map `primary` to selected borders and success, `secondary` to links, `error` to removed diff lines, `warning` to changed lines, and `muted` to comments. Use foreground on border gray for selected text, or background on primary green for active tabs. Muted text is for secondary information; do not use the border color for ordinary text.

Validate with that application's **installed version**, then review a temporary preview. Copy or include into private application settings only after backing them up and comparing with the existing file; use a separate profile if supported. Preserve credentials, keybindings, behavioral preferences, and app-written state. Add automated adapter-drift checks to `scripts/validate.py` and test readable focus, selection, warnings, errors, and diffs in both small panes and larger windows.

Current btop, compact btop, Lazygit and Newsboat settings are intentionally preserved. The new Zellij selector does not silently migrate them. Newsboat uses terminal colors where configured; btop/Lazygit have explicit existing colors that require separate reviewed adapters to fully match. Future adapters and persistent theme selection are tracked in the [roadmap](roadmap.md).

For standalone Zellij outside this launcher, [Zellij supports theme files in its config-dir's `themes/` directory](https://zellij.dev/documentation/themes.html). After backing up and reviewing collisions, place the generated `oh-my-pi.kdl` there and select `theme "oh-my-pi"` in that Zellij configuration. Do not replace the entire global config. Command-center already embeds the adapter in its scoped generated config; it needs no global theme install.
