# Agent guide: Personal Terminal Command Center

## Purpose and current stage

Maintain a macOS terminal command center built from existing tools: Ghostty, Zellij, btop, Newsboat, curl/wttr.in, Lazygit, and Hermes Agent, with coding-agent panes for OpenCode, Pi, and Codex CLI. Yazi and lazydocker are optional. Omit Neovim from the initial setup; no terminal editor is required. Build configuration and small integration scripts; do not build a new TUI, multiplexer, dashboard application, or orchestration service.

The implementation contains a working launcher, six rendered Zellij templates, tool configuration, bounded weather requests, a reversible installer, and focused validation. Core tools are installed. The README documents the supported commands; docs/validation.md records completed checks and practical limits. Keep those records current and distinguish terminal tests from native Ghostty window tests.

Platform entry points now support macOS and Linux with `install.sh` / `uninstall.sh`, and Windows through WSL 2 with `install.ps1` / `uninstall.ps1`. See docs/install.md. Homebrew installs missing core tools; `--no-dependencies` supports existing distro-managed tools. Python 3.9+, Git, and (for automatic dependencies) Homebrew are prerequisites. Keep native Windows support distinct from the WSL implementation. Preserve the macOS v1 ownership manifest format so existing installs remain reversible.

This lowercase `agent.md` is the requested human-readable maintenance guide. The root `AGENTS.md` points here for agent environments that discover the uppercase filename.

## Working context

- Project: `/Users/williamvines/Documents/ChatGPT/command-center`.
- macOS 27.0.1, Apple Silicon; shell `/bin/zsh`; Homebrew `/opt/homebrew`.
- Ghostty 1.3.1 already exists in `/Applications/Ghostty.app`.
- Ghostty theme: GitHub Dark High Contrast. Preserve it as the initial design baseline.
- Optional theme milestone (October 14, 2026): `config/themes/oh-my-pi.json` is the authoritative user palette inspired by Oh My Pi `dark-terminal`. Generate Ghostty `OhMyPi-DarkTerminal` and Zellij `oh-my-pi` with `scripts/themes.py`; keep generated files in sync. `--theme oh-my-pi` selects a separate scoped config for new sessions. Preserve the baseline, existing sessions and app preferences; do not activate Ghostty or modify live settings without user review. See `docs/themes.md` and `docs/roadmap.md` for decisions, activation/rollback, Debian terminfo and planned app adapters/theme switching.
- Existing Hermes command: `~/.local/bin/hermes`. Reuse its existing installation.
- Installed core versions: Zellij 0.45.1, btop 1.4.7, Newsboat 2.45.0, Lazygit 0.66.1.
- Existing coding agents: OpenCode 2.0.26, Pi 0.85.1, Codex CLI 0.162.0-alpha.17.2. OpenCode migrated through its official Homebrew major upgrader; maintain `anomalyco/tap/opencode-v2`, which provides the same `opencode` command.
- `~/.zprofile` already initializes Homebrew and puts `~/.local/bin` on PATH.
- tmux and Starship exist; preserve them and avoid nesting multiplexers.
- Reinspect relevant paths and CLI versions before further changes; the README snapshot can age.

## Required outcome

Provide DEV, SYSTEM, AGENTS, NEWS & WEATHER, and OPERATIONS workspaces. Use one named Zellij session with five tabs plus individually reusable layouts. Provide one launch command, convenient conflict-aware shortcuts, reversible configuration, and accurate installation and usage documentation.

Ghostty must open as a normal terminal with zsh. Never auto-start the command center from Ghostty or shell startup files. The user explicitly enters `command-center` to launch or reattach, and detaching returns them to their original shell. Keep ordinary terminal use available alongside command-center sessions.

Panel counts and arrangements belong to the user. Layouts are starting templates, not enforced structures. Support native additions, closures, movement, resizing, floating panes, and tab changes; disable automatic rearrangement initially. Preserve changes on reattachment. Export user layouts with native Zellij `dump-layout` and allow selection for new sessions without resetting live sessions.

`command-center reset` is the user's requested shortcut for `command-center --session fresh-start`. It follows the ordinary launch/attach path, reuses an existing `fresh-start` session, and preserves other sessions and tool preferences. Keep the distinction between this session shortcut and a destructive settings reset clear in the README.

This shortcut is shared by macOS, Linux, and Windows/WSL 2 through the same launcher. Windows users run it inside their installed Linux distro, using `~/.local/bin/command-center reset` when needed. Keep installer completion messages and platform update instructions consistent; do not imply native PowerShell runtime support.

`command-center update` (also `ccenter update`) pulls the launcher's permanent checkout from any working directory using its configured branch upstream and a fast-forward-only pull. Require a clean tree including untracked files, an attached branch, and an upstream; never auto-stash, merge, or rebase local work. This is a source-only update. Preserve private settings and sessions; integration refresh/validation remains an explicit `./install.sh --no-dependencies` from the checkout. Test against disposable local remotes rather than pulling into the working source tree.

Keep expensive commands suspended until the user starts them. Hidden panes can still consume resources. Use native Zellij facilities for floating panels, navigation, layout export, and resurrection. Keep bundled plugins and locked mode to pass coding-agent shortcuts through. DEV prioritizes coding-agent and shell panes rather than an editor. Do not alter provider settings or authentication. Zellij 0.45.1 requires the explicit scoped config-dir supplied by the launcher to restore cached layouts on this Mac; preserve that alongside the explicit config file.

## Configuration ownership

Inspect before writing. Existing user files are authoritative. Ghostty currently has both `config` and `config.ghostty` under `~/Library/Application Support/com.mitchellh.ghostty/`; preserve both. Prefer one managed include in the existing modern file, backed up first. Do not install a second competing theme file into another default search location.

Keep source configuration in this repository and prefer explicit configuration arguments from the launcher. Do not replace the global Zellij configuration or globally redirect XDG paths. Separate tracked defaults from private preferences, RSS URLs, caches, read-state, backups, and runtime metadata.

Linux/WSL uses XDG config/data/cache directories and the user's shell; render a scoped platform config without `/bin/zsh` or `pbcopy`. WSL skips Ghostty integration and uses `clip.exe` when available. PowerShell wrappers must escape checkout paths, forward errors, and never install/remove WSL distributions or persist execution-policy changes. Publish only source/default configuration; exclude logs, caches, databases, auth, and backups.

Make installation idempotent. Record prior file existence, backups, managed edits, and installed checksums in a local manifest. Never overwrite an existing executable or symlink without inspecting ownership. Rollback removes only this project's changes; detect later user edits and stop rather than overwrite them. Preserve user-installed packages.

## Hermes and operations

Start each Hermes pane as a distinct conversation. Never use `--continue` or `--resume latest` across all panes. Resume by a specific session ID. Existing Hermes authentication and settings can be shared; separate panes do not isolate memory, files, or credentials. Use distinct Git worktrees when agents will edit concurrently.

Do not read, copy, log, or commit Hermes `.env`, authentication files, provider secrets, or conversation databases. Do not change the Hermes gateway, model, or provider to make pane integration work. Check local CLI/source support before relying on online documentation for this installed canary build.

Keep container panels optional until a CLI and reachable engine exist. Use macOS-native diagnostics where needed. Project builds, services, log streams, and Docker contexts must be explicit choices rather than guessed startup commands. Avoid privileged monitoring as a default.

## Performance and failure behavior

The October 21 catalog milestone uses `lib/cc_catalogs.py` and fzf through `command-center apps` / `catalogs`. Ctrl-g, a opens a native floating menu; the generated scoped config replaces the quoted `{{CC_LAUNCHER}}` placeholder with the checkout's launcher path. Keep macOS/Linux/WSL on the shared implementation. Fzf is a core installer dependency, with no global shell integration.

Preserve separate Terminal Trove, Awesome TUIs, Awesome CLI/TUI Apps, and Homebrew sources. Fetch only on demand with time/size limits and keep last-good private caches. Terminal Trove's full index can require a browser challenge; its official new-tools feed is a limited fallback and must be labeled recent rather than full. Never bypass that challenge or substitute another source under its name. Sanitize terminal output and URLs; treat downloaded text solely as data, never a shell command or installation recipe. Ignore fzf startup execution hooks for this picker. Fixed adapters retain their private configurations; user-approved discovery/registrations now also support local executable argv launchers through `lib/cc_apps.py`. Scans inspect PATH, common user bins, and saved folders without executing candidates, recursively searching disks, or fetching network data. Match names from cached terminal catalogs; never classify all Homebrew formulae as apps. Keep registrations/search folders/hide state/private uninstall argv in private `apps.json`, with atomic writes and argument arrays. Homebrew installs register an unambiguous command or offer a picker after successful installation. Removal hides launchers; uninstall requires a named Homebrew package or an explicitly saved manual argv and separate confirmation. Do not guess manual deletion commands or force dependency removal. For a typed interactive `command-center apps`, current-pane means the terminal where the user typed the command. Owned floating app menus, including the shortcut's `apps --inline` route, identify the unique focused live nonfloating terminal in the same tab and use that workspace pane's space. Plugin IDs are a separate namespace; never treat them as terminal targets. Preserve the target directory and reject missing/ambiguous targets. An explicitly inline picker typed in an ordinary floating shell keeps its own terminal; standalone catalogs retain their explicit Use menu pane behavior. For an interactive typed `command-center apps`, the invoking process waits for its floating picker using native `new-pane --blocking`. The picker can return an app ID through a private temporary response file; only the waiting process launches it in its own terminal, after cleaning up the file. Offer this as Open in current pane, without a separate menu-pane replacement action in that flow. Propagate the waiting-terminal context through catalog browsing and Homebrew searches so current-pane always returns the app ID to that caller. For owned floating menus without a waiting caller, `pane --in-place ID` revalidates the target and uses native `new-pane --in-place --pane-id ID --close-on-exit`, preserving the previous shell/app and restoring it on exit. Never use `--close-replaced-pane`. Recognize the actual recorded menu command rather than treating every floating shell as a launcher menu. Never inject commands into another running pane. A saved-profile picker and multi-host aggregation remain planned; see docs/app-discovery.md and docs/roadmap.md.

Pane titles now follow the running shell/application by default. Keep fixed names out of built-in pane nodes and out of the default `pane` command, while retaining tab names. `--name` remains an explicit fixed-name override. The scoped `cc-shell` wrapper installs zsh/bash hooks without editing global startup files; respect user `ZDOTDIR`, existing startup order, PROMPT_COMMAND, DEBUG traps, and manual pane names. Both platforms render the actual scoped-shell config into private `zellij/platform.kdl`. `command-center titles --all` backs up the current layout before clearing fixed names; do not inject commands into running user panes to reload their shell hooks. Existing shells can explicitly use `command-center run shell`.

`command-center run TOOL` launches configured tools in the current terminal, including an empty Zellij shell pane. It forwards arguments and exit status without spawning a multiplexer. Plain `newsboat` uses its separate global feed list; document the configured runner to avoid the empty-URL failure. Keep full btop preferences intact. Small-pane btop uses `btop-compact.conf`, independent native presets, and `--compact` through the helper/runner/pane command. All six built-in templates now start every terminal pane suspended with `cc-panel apps`: Enter opens `apps --pick`, selecting an available app launches it in that pane, and cancel/app exit returns to the scoped shell. Shell and Weather are explicit picker choices. Preserve pane geometry/tab names and the normal floating app-management menu. Native splits remain ordinary shells. SYSTEM retains its large upper pane and two lower panes; choosing btop uses the compact monitor. Existing sessions and saved layouts remain authoritative.

Use the two-second btop refresh and 30-minute weather cache as adjustable starting values. Weather requests must have HTTPS, connection/total timeouts, and a timestamped stale-cache fallback. The user chose postal code 84121 and BBC News, Hacker News, and GitHub Blog feeds. Refresh feeds conservatively and only when configured. Local preferences are seeded once and not overwritten on reinstall.

Missing optional programs should leave a useful shell and actionable message. Required dependency failures should name the missing program and the installation step. Handle paths with spaces, launch from arbitrary directories, preserve exit status, and reject nested Zellij sessions. Avoid `eval` for user-supplied commands or layout values.

## Verification and documentation

Validate with the installed programs' supported configuration checks and focused smoke tests. Verify all five workspaces, native pane actions, shortcut delivery to applications, detach/attach, resurrection after exit, and separate Hermes conversation IDs. Test optional-tool absence, non-Git directories, weather failures, persistence, and installer rollback.

Distinguish live-session persistence from reconstruction after reboot: Zellij cannot restore process memory. Do not force-run resurrected commands. Measure idle resource usage and record results. Recheck Ghostty preservation hashes after changes.

Update `README.md` and actual usage documentation as each feature becomes usable. Explicitly label untested behavior, remaining dependencies, and limitations. Prefer primary tool documentation and local help/source; do not add dependencies solely for decoration.
