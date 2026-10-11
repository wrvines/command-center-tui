# Validation record

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

## Reproduce

```sh
scripts/validate.sh
python3 -u -B scripts/smoke.py
command-center doctor
```

The smoke test creates only its own disposable session. It may need permission to create Zellij IPC/cache state and inspect process resource usage when run from a restricted agent sandbox. Validation tests use temporary directories and do not change the user's installation.
