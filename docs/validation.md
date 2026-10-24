# Validation record

## Source update command — October 22, 2026

`command-center update` passed seven tests against disposable local bare Git remotes: fast-forward through an installed symlink from an unrelated directory (checkout path with spaces, active Zellij environment, private settings preserved), already-current checkout, tracked edits/untracked files, divergent history, detached HEAD/missing upstream, unreachable remote, and a source copy nested in another repository. No pull was performed against the development checkout or GitHub.

The full behavior suite ran 40 tests successfully, with two optional zsh tests skipped because zsh is absent. `git diff --check` passed. `scripts/validate.sh` passed its theme, Python, and Bash checks before stopping because Zellij is not installed on this host; native Zellij/Ghostty/Newsboat configuration and real terminal checks were not completed here.

## Optional unified theme — October 14, 2026

Verified locally on the original Apple Silicon Mac with **Ghostty 1.3.1** and **Zellij 0.45.1**, rechecked through their installed binaries. The existing baseline passed before implementation.

- `scripts/validate.sh` passes all **25 behavior tests**, Bash/zsh/Python syntax checks, six layout checks, and native Newsboat config/feed parsing. Theme regression tests verify that the opt-in launcher uses a separate scoped file, retains the resurrection config-dir, preserves the default runtime file and private monitor preferences, and rejects unknown theme names before writing runtime state.
- `python3 -B scripts/themes.py --check` verifies generated Ghostty/Zellij adapters against the centralized JSON without writing or installing them; the full validator runs this check too.
- Installed Zellij parses both `command-center` and `oh-my-pi` configurations for macOS and Linux through `setup --check`, including the theme's explicit UI component definitions. Linux checks here use Linux-rendered configuration with the Mac binary; they are not a Debian runtime test.
- Installed Ghostty accepts both the unchanged padding include and the complete `OhMyPi-DarkTerminal` adapter through `+validate-config --config-file=…` with exit status 0. A disposable malformed-color config returns nonzero. Some direct CLI runs emit `SentryInitFailed` from Ghostty; syntax-check success is distinguished by exit status. `+show-config` with custom arguments did not produce a usable resolved-color dump in this environment, so no visual or resolved-output claim is made from it.
- `git diff --check` passes. Standards and requirement reviews found no actionable issues.
- Live Ghostty `config` / `config.ghostty`, global Zellij `config.kdl`, and scoped baseline `platform.kdl` have identical SHA-256 hashes before and after this work. No installer, live theme selection, session reset, remote SSH command, or profile edit was performed. Existing application preferences were not migrated.

The user subsequently confirmed that the theme worked in the regular terminal and in a new themed command-center session. This is user-reported visual verification; the agent did not inspect a native Ghostty window. Color perception across displays, actual SSH/terminfo behavior on the Debian Lenovo, and existing-session theme reload remain untested. Review [activation and rollback](themes.md) before trying the theme. Full/compact btop and Lazygit still use their existing explicit palettes; future adapters and persistent switching are recorded in [the roadmap](roadmap.md).

Validated on October 11, 2026, on macOS 27.0.1 / Apple Silicon.

## Completed

- Core dependencies installed through Homebrew: Zellij 0.45.1, btop 1.4.7, Newsboat 2.45.0, and Lazygit 0.66.1.
- OpenCode 1.18.31, Pi 0.85.1, and Codex CLI 0.162.0-alpha.17.2 detected through their version commands. Existing Hermes launcher/source provenance inspected without reading credentials.
- Python/Bash syntax checks and native parsing of all six rendered KDL layouts, including paths with spaces and quotes.
- Ghostty include validation, preserving its original theme and shell startup.
- Newsboat configuration and feed list loaded through native OPML export without feed requests.
- Ten behavior tests: idempotent installation, exact rollback, retained local preferences, rollback refusal after later edits, executable-name collisions, new-session path escaping, live-session attachment without layout replacement, nesting rejection, saved-layout overwrite prevention, cached/stale weather handling, invalid-response rejection, and unset-location behavior. Some tests cover multiple related cases.
- A real 160×50 PTY session rendered all five tabs. Native keyboard split/input, movement, resizing, floating/tiled changes, optional-tool fallback, non-Git fallback, themed btop and Lazygit startup, workspace addition, native layout export, detach/reattach, and exited-session resurrection passed.
- Newsboat loaded two disposable local articles in its real terminal UI. Marking them read persisted across a fresh process using the scoped cache; the user's real articles were not modified by this check.
- Smoke sessions used unique names and were removed afterward. No agent was asked to perform a task and no AI prompts were sent.

The real-session check exposed Zellij 0.45.1's need for an explicit configuration directory when resolving an absolute cached layout on a Mac without a global Zellij config. The launcher now supplies its own scoped directory while keeping the actual configuration repository-local. Native restoration subsequently passed with all tabs and suspended commands.

## Resource observations

One short PTY check measured CPU-time deltas over two seconds for the Zellij client/server and their child processes:

| State | CPU, relative to one core | Summed RSS | Process count |
| --- | --- | --- | --- |
| Agents and monitors suspended | 0.5% | 124.4 MiB | 6 |
| btop active, agents suspended | 1.0% | 101.1 MiB | 8 |

These are short observations, not a benchmark or memory guarantee. RSS sums may count shared pages repeatedly; initialization, compilation, and reclamation affect the samples, so the lower second RSS value does not imply btop saves memory. A Ghostty window and active coding agents add their own resource usage. Hidden running panels continue consuming resources; suspension and modest refresh rates are the primary controls.

## Practical limits

Native Ghostty UI access was denied by the computer-use tool. Ghostty's actual window rendering, font appearance, and macOS shortcut delivery still need visual confirmation by the user. The terminal controls and layouts were exercised in a real PTY rather than in Ghostty's window.

Provider authentication, paid model responses, and simultaneous Hermes conversation-ID creation were not exercised. Fresh Hermes panes invoke `hermes chat` without shared resume arguments; each tool keeps its own conversation persistence. Yazi, lazydocker, and a container engine remain optional and uninstalled. No service/build/log stream was started for testing.

## Live connectivity and activation

Weather for postal code 84121 fetched successfully from wttr.in and was cached locally. Newsboat fetched BBC News, Hacker News, and GitHub Blog; the scoped database contained 58 articles (28 BBC, 20 Hacker News, 10 GitHub Blog) at the check. Remote service availability is independent of configuration validity.

The installer activated `command-center` and `ccenter` under `~/.local/bin`, seeded private editable preferences, and appended its owned include to the existing modern Ghostty configuration. A repeat installation made no changes. The installed launcher passed `doctor`, and rollback's dry-run passed its ownership checks. Actual rollback was tested only against isolated fixtures.

Both original Ghostty configuration backups matched the inspection hashes:

| Original file | SHA-256 |
| --- | --- |
| `config` | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` |
| `config.ghostty` | `a7ede47f1c57425eba8e046608a71af581b410a88a0572ba6475096f33cb7bc3` |

The legacy configuration and shell startup files were not changed. Backups and the ownership manifest remain under `~/Library/Application Support/command-center/`.

## OpenCode v2 update

On October 11, 2026, the user's requested upgrade migrated Homebrew OpenCode 1.18.31 through 1.19.0, then ran the official `opencode upgrade --major --method brew` command. The resulting package is `anomalyco/tap/opencode-v2` 2.0.26. `/opt/homebrew/bin/opencode` resolves to that package's binary. Both `opencode --version` and `bin/cc-panel opencode --version` returned `opencode v2.0.26`. These checks sent no model prompts; provider responses and v1 conversation migration were not tested. V2 writes its normal local log even for the version command, so that check required running outside the agent filesystem sandbox.

## Portable installer update

The macOS/Linux entry points are now `install.sh` and `uninstall.sh`. Windows uses `install.ps1` and `uninstall.ps1` with WSL 2; native Windows runtime integration is not implemented. Documentation covers Homebrew/Python prerequisites, existing distro packages, private paths, clone/pull usage, optional agents, and retained state on uninstall.

Local checks passed for both rendered macOS/Linux configurations, all six layouts, all Bash entry points, and 17 Python behavior tests. The new cases cover XDG paths, removal of macOS-only runtime settings on Linux, missing dependency planning, Linux config restoration/removal, and the no-Ghostty WSL path. macOS installer/uninstaller previews passed against the existing v1 ownership manifest, and the complete real macOS PTY smoke check passed again after making the helpers portable.

PowerShell 7.6.6 was downloaded only into a temporary test directory from the official release; its SHA-256 matched the GitHub asset digest. Actual PowerShell parsing and a simulated `wsl.exe` transport test passed for distro selection, apostrophes/spaces in checkout paths, installation/uninstallation flag forwarding, and WSL 1 rejection. This test did not run a Windows kernel or initialize a real WSL distro. A GitHub workflow exercises Linux/macOS configuration and real-session tests plus Windows PowerShell transport tests after publication; workflow results must be checked separately before claiming those hosts passed.

The first [GitHub validation run](https://github.com/wrvines/command-center-tui/actions/runs/38170927586) passed for implementation commit `0d91c8123e258b1af107e56b23b94cdd88742022`: macOS and Ubuntu installed the core tools, passed configuration/behavior validation, and passed the real PTY smoke test. The Windows runner passed actual PowerShell parsing and the simulated WSL bridge checks. A full installation into a real WSL distro and native Ghostty window rendering remain manual checks. The subsequent documentation-only commit records these results without repeating CI.

## Small-screen and current-pane update

On October 11, 2026, plain `newsboat` reproduced the missing-default-URL error, while the configured panel successfully read the three command-center feeds. The new `command-center run newsboat` uses that same scoped configuration/cache in the current terminal. A later check encountered the user's active Newsboat cache lock; the instance was left running. Concurrent readers of that database are not supported.

The compact btop profile is separate from existing full-view preferences. Native terminal checks passed for CPU at 60×8, memory/disks at 60×10, network at 60×6, and processes at 60×16. Newsboat's current-terminal runner loaded a disposable local feed at 40×10. All checks used private temporary state, with no AI requests or changes to the user's article read-state.

Both platform configurations, all six layouts, shell/Python syntax, and 19 behavior tests passed. The real-session smoke check passed again, including the new compact SYSTEM monitor above two lower shell panes at 100×30, layout export, attachment, and resurrection. Full-view btop still has its native minimum-size constraints; changing graphs does not remove those constraints. Existing saved sessions retain their layout; adding a new SYSTEM workspace applies the revised template.

The new compact profile was seeded into the original Mac's private preferences without replacing `btop.conf`, feeds, or existing configuration. README and agent guidance document the configured current-pane launch, compact presets, and cache-lock behavior. Native Ghostty visual inspection remains untested.

## Automatic pane title update

On October 11, 2026, a disposable native Zellij session showed that an unnamed pane retained `Pane #1` while `sleep` ran, even though Zellij's process metadata detected it. Preset pane names also override application titles. Built-in layouts and new-pane defaults now omit fixed names, and small scoped zsh/bash hooks supply command titles through native terminal escape sequences. Explicit manual names still override those titles.

The real-session check passed with both zsh 5.9 and macOS Bash 3.2: idle shell title, command title during `sleep`, reset after completion, manual override, and clearing the fixed name. Native session attachment/resurrection, all five tabs, compact SYSTEM at 100×30, Git and Newsboat UI checks, and pane actions passed. Original `ZDOTDIR` redirection/startup order, existing Bash DEBUG/PROMPT_COMMAND integration, command-argument omission without evaluation, and backup/plugin exclusion when clearing all labels are covered by the behavior suite (23 tests).

The title wrapper uses original shell startup files without editing them. Mac/Linux now render their scoped shell path into the private `zellij/platform.kdl`. Existing running shells need an explicit `command-center run shell` to load the hooks; saved layouts retain fixed names until deliberately cleared. Native Ghostty visual inspection and non-zsh/bash shell integration remain outside these checks.

## Reproduce small-screen checks

```sh
python3 -u -B scripts/small-screen-smoke.py
```

## Reproduce full validation

```sh
scripts/validate.sh
python3 -u -B scripts/smoke.py
command-center doctor
```

The smoke test creates only its own disposable session. It may need permission to create Zellij IPC/cache state and inspect process resource usage when run from a restricted agent sandbox. Validation tests use temporary directories and do not change the user's installation.

## Reset shortcut validation

On October 11, 2026, `command-center reset` was verified through the existing isolated PTY launcher fixture to produce the same launch arguments as `command-center --session fresh-start`, include all five starter tabs for a new session, reattach without adding tabs when `fresh-start` exists, and reject nested launches before contacting Zellij. No personal sessions were started or stopped during this check. `scripts/validate.sh` also passed all 23 existing tests and native macOS/Linux configuration, six layout, Ghostty include, and Newsboat configuration checks.

## Catalog milestone — October 21, 2026

Installed fzf 0.74.5 with Homebrew. `scripts/validate.sh` passed 33 tests, both themes' generated macOS/Linux configurations, all six layouts, Ghostty configuration parsing, and Newsboat configuration/feed parsing. Eight catalog tests cover the four source formats, recent-feed labeling, control/URL sanitization, invalid formula names, last-good-cache fallback including malformed/oversized CSV, fzf startup-hook isolation, preserved searches through details/refresh, explicit package installation arguments, and headless listing. No sample package was installed by the tests.

Live downloads through the implemented curl adapter produced 718 Awesome TUIs entries, 2,206 Awesome CLI/TUI Apps entries, and 8,664 Homebrew/core formulae. Terminal Trove's full HTML index returned a Cloudflare browser challenge; its published Atom feed returned 50 recent tools. The latter is explicitly labeled **recent feed (full index unavailable)**. These counts record this check, not fixed catalog sizes.

The disposable native Zellij/fzf PTY smoke test passed the Ctrl-g/a floating menu, all four source choices, cached search and text preview, default tiled launch, floating launch, menu-pane replacement/exit, and Esc cancellation while preserving the underlying shell. It also passed the existing split/resize/move/title controls, btop/Lazygit/Newsboat checks, save/reattach/resurrection, and detach. No AI prompts were sent. This is terminal validation, not a visual inspection of a live Ghostty window. Native Linux and Windows/WSL runtime checks were not executed on this Mac; the shared code's Linux configs/fixtures passed and CI includes fzf on macOS/Ubuntu.

After review, the existing private baseline and optional-theme Zellij configs were compared with generated output: only the requested app-menu shortcut was added. Verified public indexes were cached privately for first use. Ghostty configuration hashes remained unchanged. No existing sessions were restarted and no tool preferences, feeds, credentials, or saved layouts were reset. Standards/spec review findings about malformed CSV and lost search queries were fixed and rechecked.

## Homebrew package-name search — October 22, 2026

The catalog action **Search Homebrew for this name** now uses a case-insensitive substring search limited to package names. General catalog browsing retains fuzzy matching across names and descriptions. The package-name prompt explains how to return to project installation instructions when no name matches.

With the installed fzf 0.74.5 and the existing 8,666-entry Homebrew/core cache, the original `abtop` query reproduced the screenshot's 611 unrelated matches; the corrected package-name search returned zero. The `btop` query returned only the `btop` package instead of 1,220 fuzzy matches. This checks the cached core catalog, not custom taps or all installation methods.

`scripts/validate.sh` passed all 43 behavior tests, generated configurations for both platforms/themes, all six layouts, and Ghostty/Newsboat configuration checks. Three new regressions cover real fzf matching without an interactive terminal, the catalog-to-Homebrew handoff, and retaining name-search mode and guidance after refresh. No package was installed. Native Ghostty window interaction remains a manual check.

## Optional abtop launcher — October 22, 2026

Added a reviewed optional `abtop` adapter to the installed-app menu, catalog launch detection, `command-center run` / `pane`, and the optional-tool doctor report. The menu shows **abtop (AI agents)** only when the executable is found on the effective PATH. It supports the existing tiled, floating, and current-menu-pane actions. Installation remains separate; this change does not add generic app registration or run abtop setup hooks.

`scripts/validate.sh` passed all 45 behavior tests and the existing platform/layout/Ghostty/Newsboat configuration checks. New regressions cover installed/missing abtop menu detection, catalog recognition, current-pane argument and exit-status forwarding, and tiled/floating pane commands using a disposable Zellij fixture. A separate invocation of the installed executable through the configured runner returned `abtop 0.5.5` with status 0 using temporary Command Center state. No live agent-monitoring session or native Ghostty window was opened for validation.

## Optional Amp editor launcher — October 22, 2026

Added the installed Homebrew `amp` terminal text editor as **Amp editor** in the configured-app menu and optional doctor report, with the existing `run`, tiled-pane, floating-pane, and menu-pane launch paths. This is the jmacdonald/amp editor from Homebrew formula `amp` (local installed version 0.7.1). No package installation or generic app registration was added.

`scripts/validate.sh` passed all 45 behavior tests and the existing configuration checks. The optional-app regressions now cover both abtop and Amp for installed/missing menu detection, catalog recognition, run argument/exit-status forwarding, and tiled/floating pane commands. Amp's case verifies forwarding a filename containing spaces. A real PTY smoke test launched the installed Amp through the configured runner, inserted text, saved a temporary file with spaces in its name, and quit with status 0. Command Center state and edited files were temporary; no live Zellij session or native Ghostty window was used for this check.

## Installed-app discovery and removal — October 22, 2026

Implemented host-local discovery from effective PATH, common user installation folders, and saved folders. Non-Homebrew cached catalog names match actual executable filenames; scans neither run candidates nor download indexes. A private argv registry supports custom labels/arguments, missing-app reporting, explicit replacement, persistent hide/restore, and saved uninstall commands. Homebrew post-install registration auto-selects an unambiguous executable or offers a picker. The app menu and CLI share the registry; built-in adapters retain their private configurations. Multi-host agent aggregation was recorded as a later roadmap investigation.

`scripts/validate.sh` passed all 64 behavior tests, generated macOS/Linux configurations for both themes, six layouts, and Ghostty/Newsboat parsing. New checks cover local/catalog discovery, common/custom folders, PATH precedence, nonrecursive scans, atomic registry preservation, missing executables, saved argv and replacement, hidden-state persistence, canonical app keys, successful/canceled/failed Homebrew uninstall, literal manual uninstall arguments, discovered executable pinning before saving uninstall recipes, and macOS system-command filtering while preserving Linux package discovery. Disposable update-test repositories now include the registry module.

The real Zellij/fzf PTY smoke test passed all existing session checks plus cached automatic discovery of a fixture in a saved folder, dynamic tiled launch and launcher persistence, app-menu removal that retains the executable, and restoration. Tiled/floating/menu-pane launches, native shortcuts, configured btop/Lazygit/Newsboat, titles, save/reattach, suspended resurrection, and detach also passed. The restricted runner could not create the initial test session; the disposable test passed with access to local IPC/process information. No user session was restarted and no real package was installed or uninstalled by these checks. Native Linux/WSL runtime behavior and live Ghostty window rendering were not tested here.

A read-only scan against the existing Mac catalog cache initially found 12 names in roughly 0.14 seconds. That exposed a collision between Apple's `/usr/bin/vis` utility and the cataloged Vis editor. Automatic macOS matching now excludes protected system-command folders; the final scan found 11 apps, including Astroterm through catalog matching. Linux/WSL system folders remain eligible for distribution-installed apps. These are local observations, not benchmarks or guarantees that every installed command can be classified as a TUI. Independent standards/spec reviews were completed; findings about hidden state, old-server PATH, replacement uninstall recipes, and canonical keys were corrected and regression-tested.

## Unassigned starter panes — October 22, 2026

All six premade templates preserve their geometry and tab names while every terminal pane starts suspended with an app picker. Enter opens the picker; available apps launch in that same pane. Shell and Weather use the configured helpers. Canceling the picker, a picker error, or an app exiting returns to the scoped shell. The normal app menu retains management/catalog actions. Existing sessions and saved layouts remain authoritative.

`scripts/validate.sh` passed all 69 behavior tests, both platform/theme configurations, all six native layout checks, and Ghostty/Newsboat parsing. New regressions cover every template leaf waiting for the picker, direct app selection, available-only choices, configured Shell/Weather arguments, cancellation, and shell fallback even after a picker failure. The real Zellij/fzf PTY smoke passed Enter-to-picker, discovered-app launch in place with unchanged pane count, app-exit shell fallback, SYSTEM btop selection and cancel-to-shell at 100×30, and all existing management, title, pane, save, reattach, resurrection, and detach checks. Independent standards and spec reviews passed after restricting starter choices to available apps and Shell/Weather. Tests used a disposable session; existing user sessions were untouched. Native Ghostty window rendering and native Linux/WSL runtime remain untested here.

## Launch in the invoking terminal — October 23, 2026

Typed interactive `command-center apps` now keeps its calling process waiting while the native floating menu is open. Installed/saved app actions offer **Open in original terminal pane**: the picker returns only an app ID, closes, and the waiting process resolves and launches the app in its own terminal after cleaning up the private temporary directory. No command is injected into another pane. Keyboard shortcuts, noninteractive spawning, inline pickers, and other launch placements retain their existing behavior.

`scripts/validate.sh` passed all 74 behavior tests, both platform/theme configurations, all six layouts, and Ghostty/Newsboat parsing. New tests cover the app-ID return path, no original-pane action in shortcut menus, launch/exit-status forwarding in the invoking PTY, cancellation, temporary-directory cleanup, and rejection of malformed or shell-syntax selections. The full real Zellij/fzf PTY smoke passed a typed `apps` command, selection of the original-terminal action, an unchanged focused pane ID and total pane count after the menu closed, app exit status 7 returning to the original shell, and canceled-menu status 0. All prior pane, catalog, discovery/removal, title, configured-tool, save, reattach, resurrection, and detach checks passed. No user session or real package was changed by verification. Native Linux/WSL runtime and a native Ghostty window remain untested here.

## Current-pane selection targets the invoking terminal — October 23, 2026

The typed app menu previously offered both Use menu pane and Open in original terminal pane. Choosing the former replaced the floating picker, and catalog browsing also lost the original-terminal context. The typed menu now presents a single **Open in current pane** action that returns the selected app ID to its waiting caller. Catalog browsing and nested Homebrew searches preserve this target. Shortcut/standalone menus retain their explicit Use menu pane action because they have no waiting caller. No commands are injected into another pane.

`scripts/validate.sh` passed all 76 behavior tests, platform/theme rendering, six layouts, and Ghostty/Newsboat parsing. The regression first reproduced the old current-pane execution inside the floating menu, then passed after routing it to the caller. Additional tests exercise the complete app-menu → catalog → current-pane return path and retention of the target during Homebrew handoff. The full real Zellij/fzf PTY smoke confirmed current-pane selection from both the app list and catalog launches in the same originating pane ID, closes the floating picker, and preserves the total pane count. Shell return/exit status, cancellation, other launch placements, shortcuts, discovery/removal, titles, configured tools, save/reattach, resurrection, and detach also passed. Independent standards and spec reviews reported no findings. No live user session was modified by these checks; native Linux/WSL runtime and native Ghostty window rendering remain untested here.

## Live floating-menu route — October 23, 2026

A repeated live report exposed a path missing from the prior current-pane test: the actual Astroterm pane had been launched by the checkout's `command-center apps --inline` floating menu, without the waiting caller's return-selection flag. Read-only pane metadata identified that route; the running app was left untouched. The launcher now recognizes its owned floating app menus, identifies the focused live workspace terminal in the same tab, and uses native temporary in-place replacement after target validation. The app uses the original pane's space/directory and restores its prior shell/app on exit. Explicit inline pickers inside ordinary floating shells retain their own pane. Plugin and terminal pane IDs are kept distinct.

`scripts/validate.sh` passed all 82 behavior tests, both platform/theme configurations, six layouts, and Ghostty/Newsboat parsing. New regressions reproduce the floating inline menu route, locate the same-tab workspace terminal while excluding plugin IDs and unavailable/ambiguous targets, preserve an explicit inline picker in a floating shell, handle suspended starters with no process cwd, validate native temporary replacement flags, and refuse a missing target without creating a pane. The full real Zellij/fzf PTY smoke passed the exact shortcut-created floating menu, current-pane selection into the underlying workspace, matching pane geometry, no floating app view, and restoration of the original live shell with its shell variable intact. Typed-command returns, catalog routes, other app placements, discovery/removal, titles, configured tools, save/reattach, resurrection, and detach also passed. Independent standards and spec reviews reported no findings. No live user pane was moved or closed, and the running Astroterm instance was left untouched. Native Linux/WSL runtime and native Ghostty window rendering remain untested here.


## Consolidated hardening review — October 23, 2026

PR #1 supplies bounded HTTPS downloads that ignore curl startup settings, terminal-text sanitization, XML declaration rejection, valid KDL string escaping for Unicode paths, registry symlink refusal, and restricted temporary app-selection files. The consolidated implementation adds PR #2's shared text sanitizer, private Newsboat state directory, malformed weather/pane-data errors, ownership-manifest validation, and pinned CI inputs. The Homebrew installer digest was independently verified without executing it.

Two reviewed regressions are corrected: cached catalog reads stop at the size limit plus one byte, and launcher-only installs do not reject paths for unused Ghostty integration. Automatic interrupted-install recovery is excluded: missing or modified managed files still stop installation while preserving the ownership manifest and original backups. Regression checks cover missing-file preservation and exact subsequent rollback, malformed manifests, bounded oversized caches, launcher-only paths, and overflowing weather cache lifetimes.

The consolidated source passed all 97 behavior tests, native parsing of both platform/theme configurations and all six layouts, Ghostty/Newsboat parsing, the small-terminal tool checks, and the full real Zellij/fzf PTY smoke test on this Mac. These checks used disposable state and sessions; no live user configuration, pane, or installed package was changed. Independent standards and spec reviews were completed. Native Linux/WSL runtime and native Ghostty window rendering were not tested locally. Earlier GitHub runs on both PRs and the existing main branch had terminal-smoke failures; those existing CI failures are tracked separately from the passing local checks.
