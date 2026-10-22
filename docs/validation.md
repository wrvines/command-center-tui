# Validation record

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
