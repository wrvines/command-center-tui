#!/usr/bin/env python3
"""Exercise a disposable real Zellij session through a PTY; never start AI requests."""
import fcntl
import json
import os
import pty
import select
import shlex
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
from cc import zellij_config_content
SESSION = "cc-smoke-" + str(os.getpid())


def main():
    with tempfile.TemporaryDirectory(prefix="cc-real-session-") as temp:
        base = Path(temp)
        CONFIG = base / "runtime-config.kdl"
        CONFIG.write_text(zellij_config_content())
        project = base / 'project with spaces and "quotes"'
        project.mkdir()
        home = base / "home"
        home.mkdir()
        # The default-title checks must not inherit a runner/user's title-setting
        # prompt. Startup-file preservation has separate focused behavior tests.
        env = dict(os.environ, HOME=str(home), COMMAND_CENTER_HOME=str(base / "state"), TERM="xterm-256color")
        env.pop("ZDOTDIR", None)
        env.pop("ZELLIJ", None)
        env.pop("TMUX", None)
        children = []

        def action(*args):
            result = subprocess.run(["zellij", "--config", str(CONFIG), "--session", SESSION, "action", *args],
                                    env=env, capture_output=True, text=True, timeout=10)
            # This boolean query uses nonzero status for false (2 on this installed build).
            false_query = (args == ("are-floating-panes-visible",) and result.returncode in (1, 2)
                           and (result.stdout or result.stderr).strip() == "false")
            if result.returncode and not false_query:
                raise RuntimeError(f"Zellij action {args!r} failed ({result.returncode}): " +
                                   (result.stderr or result.stdout or "no diagnostic"))
            return "false" if false_query else result.stdout

        def start(*extra):
            for old_process, _, old_thread in children:
                if old_process.poll() is not None:
                    old_thread.join(timeout=1)
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 160, 0, 0))
            def control_terminal():
                os.setsid()
                fcntl.ioctl(0, termios.TIOCSCTTY, 0)
            process = subprocess.Popen([str(ROOT / "bin/command-center"), "--session", SESSION,
                                        "--project", str(project), *extra],
                                       env=env, stdin=slave, stdout=slave, stderr=slave,
                                       preexec_fn=control_terminal)
            os.close(slave)
            transcript = bytearray()
            def drain():
                while True:
                    try:
                        ready, _, _ = select.select([master], [], [], 0.2)
                        if ready:
                            chunk = os.read(master, 65536)
                            if not chunk:
                                return
                            transcript.extend(chunk)
                        elif process.poll() is not None:
                            return
                    except OSError:
                        return
            thread = threading.Thread(target=drain, daemon=True)
            thread.start()
            children.append((process, master, thread))
            for _ in range(75):
                time.sleep(0.2)
                if process.poll() is not None:
                    raise RuntimeError("Terminal exited early: " + transcript.decode(errors="replace")[-2000:])
                try:
                    if "DEV" in action("query-tab-names") and (b"INTERFACE LOCKED" in transcript or b"UNLOCK" in transcript):
                        return process, master
                except (RuntimeError, subprocess.TimeoutExpired):
                    pass
            import re
            screen = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", transcript.decode(errors="replace"))
            listing = subprocess.run(["zellij", "list-sessions", "--no-formatting", "--short"], env=env, capture_output=True, text=True)
            raise RuntimeError("Session did not become ready. Sessions: " + listing.stdout + " Terminal: " + screen[-2500:])

        def wait_for(test, description):
            for _ in range(30):
                try:
                    if test():
                        return
                except json.JSONDecodeError as error:
                    # Zellij can briefly return no metadata during pane replacement.
                    # Retry an empty response within this wait's existing limit;
                    # malformed nonempty JSON must still fail immediately.
                    if error.doc.strip():
                        raise
                time.sleep(0.1)
            raise RuntimeError("Failed: " + description + "\n" + action("dump-screen"))

        def launcher(*args):
            inside = dict(env, ZELLIJ="1", ZELLIJ_SESSION_NAME=SESSION)
            panes = json.loads(action("list-panes", "--json", "--all"))
            focused = next((pane for pane in panes if pane.get("is_focused") and not pane.get("is_plugin")), None)
            if focused:
                inside["ZELLIJ_PANE_ID"] = str(focused["id"])
            result = subprocess.run([str(ROOT / "bin/command-center"), *args], env=inside,
                                    capture_output=True, text=True, timeout=15)
            if result.returncode:
                raise RuntimeError(result.stderr or result.stdout)
            return result.stdout

        def resources(client_pid, label):
            def snapshot():
                listing = subprocess.check_output(["ps", "-axo", "pid=,ppid=,time=,rss=,command="], text=True)
                rows = {}
                for line in listing.splitlines():
                    fields = line.split(None, 4)
                    if len(fields) == 5:
                        pid, parent, cpu, rss, command = fields
                        parts = cpu.split(":")
                        seconds = sum(float(value) * 60 ** i for i, value in enumerate(reversed(parts)))
                        rows[int(pid)] = (int(parent), seconds, int(rss), command)
                selected = {client_pid}
                selected.update(pid for pid, row in rows.items() if "--server" in row[3] and SESSION in row[3])
                while True:
                    expanded = selected | {pid for pid, row in rows.items() if row[0] in selected}
                    if expanded == selected:
                        break
                    selected = expanded
                return {pid: rows[pid] for pid in selected if pid in rows}
            first = snapshot()
            stamp = time.monotonic()
            time.sleep(2)
            second = snapshot()
            seconds = sum(max(0, row[1] - first[pid][1]) for pid, row in second.items() if pid in first)
            cpu = seconds / (time.monotonic() - stamp) * 100
            rss = sum(row[2] for row in second.values()) / 1024
            print(f"MEASURE {label}: {cpu:.1f}% of one CPU core over 2s; {rss:.1f} MiB summed RSS; {len(second)} processes")

        try:
            process, master = start()
            names = action("query-tab-names")
            for name in ("DEV", "SYSTEM", "AGENTS", "NEWS & WEATHER", "OPERATIONS"):
                assert name in names, names
            print("PASS: all five tabs render in a 160×50 terminal")
            wait_for(lambda: bool(json.loads(action("list-panes", "--json", "--all"))), "pane metadata ready")
            # Real fzf and native shortcut, using only local catalog fixtures.
            from cc_catalogs import load_catalog
            load_catalog('awesome-tuis', cache_dir=base / 'state/cache/catalogs',
                         fetch=lambda url: '## Dashboards\n'
                                           '- [btop](https://github.com/aristocratos/btop) Resource monitor\n'
                                           '- [cc-discovery-demo](https://example.com/demo) Local smoke fixture\n')
            from cc_apps import Registry
            registry = Registry(config_dir=base / 'state/config', cache_dir=base / 'state/cache')
            app_folder = base / 'manual apps'
            app_folder.mkdir()
            demo = app_folder / 'cc-discovery-demo'
            demo.write_text('#!/bin/sh\nprintf "CC_DISCOVERY_DEMO_READY\\n"\nread -r answer\n')
            demo.chmod(0o755)
            registry.add_folder(app_folder)
            original_count = len(json.loads(action("list-panes", "--json", "--all")))
            os.write(master, b"\r")
            wait_for(lambda: "Choose an app" in action("dump-screen"), "Enter opens starter picker")
            os.write(master, b"cc-discovery-demo")
            time.sleep(0.2)
            os.write(master, b"\r")
            wait_for(lambda: "CC_DISCOVERY_DEMO_READY" in action("dump-screen"), "starter launches in place")
            assert len(json.loads(action("list-panes", "--json", "--all"))) == original_count
            action("write-chars", "\n")
            time.sleep(0.5)
            action("write-chars", "printf 'CC_STARTER_%s\\n' SHELL_READY\n")
            wait_for(lambda: "CC_STARTER_SHELL_READY" in action("dump-screen"), "app exit returns to shell")
            print("PASS: Enter opens a starter picker, selection fills its pane, app exit returns to shell")
            origin_app = app_folder / 'cc-origin-demo'
            origin_app.write_text('#!/bin/sh\nprintf "CC_ORIGIN_APP_READY\\n"\nread -r answer\nexit 7\n')
            origin_app.chmod(0o755)
            registry.register('cc-origin-demo', [str(origin_app)])
            origin_id = next(pane['id'] for pane in json.loads(action('list-panes', '--json', '--all'))
                             if pane.get('is_focused') and not pane.get('is_plugin'))
            action('write-chars', shlex.quote(str(ROOT / 'bin/command-center')) + ' apps\n')
            wait_for(lambda: 'Installed and saved apps' in action('dump-screen'), 'typed apps floating menu')
            os.write(master, b'cc-origin-demo')
            time.sleep(0.2)
            os.write(master, b'\r')
            wait_for(lambda: 'Open in current pane' in action('dump-screen'), 'current pane option')
            assert 'Use menu pane' not in action('dump-screen')
            os.write(master, b'Open in current pane')
            time.sleep(0.2)
            os.write(master, b'\r')
            wait_for(lambda: 'CC_ORIGIN_APP_READY' in action('dump-screen'), 'original terminal app')
            origin_panes = json.loads(action('list-panes', '--json', '--all'))
            assert len(origin_panes) == original_count
            assert next(pane['id'] for pane in origin_panes if pane.get('is_focused')) == origin_id
            assert action('are-floating-panes-visible').strip() == 'false'
            action('write-chars', '\n')
            time.sleep(0.5)
            action('write-chars', 'printf "CC_ORIGIN_STATUS_%s\\n" "$?"\n')
            wait_for(lambda: 'CC_ORIGIN_STATUS_7' in action('dump-screen'), 'original shell and exit status')
            action('write-chars', shlex.quote(str(ROOT / 'bin/command-center')) + ' apps\n')
            wait_for(lambda: 'Installed and saved apps' in action('dump-screen'), 'typed apps cancel menu')
            os.write(master, b'\x1b')
            time.sleep(0.5)
            action('write-chars', 'printf "CC_ORIGIN_CANCEL_%s\\n" "$?"\n')
            wait_for(lambda: 'CC_ORIGIN_CANCEL_0' in action('dump-screen'), 'cancel returns to original shell')
            print('PASS: typed apps launches in its original pane, preserves shell/exit status, and cancels cleanly')
            demo.write_text('#!/bin/sh\nprintf "CC_CATALOG_CURRENT_READY\\n"\nread -r answer\n')
            action('write-chars', shlex.quote(str(ROOT / 'bin/command-center')) + ' apps\n')
            wait_for(lambda: 'Installed and saved apps' in action('dump-screen'), 'typed apps catalog route')
            os.write(master, b'Browse catalogs')
            time.sleep(0.2)
            os.write(master, b'\r')
            wait_for(lambda: 'Choose catalog' in action('dump-screen'), 'origin catalog source picker')
            os.write(master, b'Awesome TUIs')
            time.sleep(0.2)
            os.write(master, b'\r')
            wait_for(lambda: 'full index' in action('dump-screen'), 'origin cached catalog')
            os.write(master, b'cc-discovery-demo')
            time.sleep(0.2)
            os.write(master, b'\r')
            wait_for(lambda: 'Open in current pane' in action('dump-screen'), 'catalog current pane action')
            os.write(master, b'Open in current pane')
            time.sleep(0.2)
            os.write(master, b'\r')
            wait_for(lambda: 'CC_CATALOG_CURRENT_READY' in action('dump-screen'), 'catalog launches in original pane')
            catalog_panes = json.loads(action('list-panes', '--json', '--all'))
            assert len(catalog_panes) == original_count
            assert next(pane['id'] for pane in catalog_panes if pane.get('is_focused')) == origin_id
            assert action('are-floating-panes-visible').strip() == 'false'
            action('write-chars', '\n')
            time.sleep(0.5)
            action('write-chars', "printf 'CC_CATALOG_%s\\n' SHELL_READY\n")
            wait_for(lambda: 'CC_CATALOG_SHELL_READY' in action('dump-screen'), 'catalog app returns to shell')
            demo.write_text('#!/bin/sh\nprintf "CC_DISCOVERY_DEMO_READY\\n"\nread -r answer\n')
            print('PASS: catalog current-pane selection also returns to the original terminal')
            shortcut_app = app_folder / 'cc-shortcut-demo'
            shortcut_app.write_text('#!/bin/sh\nprintf "CC_SHORTCUT_APP_READY\\n"\nread -r answer\n')
            shortcut_app.chmod(0o755)
            registry.register('cc-shortcut-demo', [str(shortcut_app)])
            action('write-chars', "CC_PANE_KEEP=preserved; printf 'CC_PANE_%s\\n' PREPARED\n")
            wait_for(lambda: 'CC_PANE_PREPARED' in action('dump-screen'), 'workspace shell state prepared')
            source_pane = next(pane for pane in json.loads(action('list-panes', '--json', '--all'))
                               if pane['id'] == origin_id and not pane.get('is_plugin'))
            os.write(master, b'\x07a')
            wait_for(lambda: 'Installed and saved apps' in action('dump-screen'), 'shortcut floating menu route')
            os.write(master, b'cc-shortcut-demo')
            time.sleep(0.2)
            os.write(master, b'\r')
            wait_for(lambda: 'Open in current pane' in action('dump-screen'), 'shortcut workspace action')
            assert 'Use menu pane' not in action('dump-screen')
            os.write(master, b'Open in current pane')
            time.sleep(0.2)
            os.write(master, b'\r')
            wait_for(lambda: 'CC_SHORTCUT_APP_READY' in action('dump-screen'), 'shortcut app uses workspace pane')
            assert action('are-floating-panes-visible').strip() == 'false'
            shortcut_panes = json.loads(action('list-panes', '--json', '--all'))
            assert next(pane for pane in shortcut_panes if pane['id'] == origin_id and
                        not pane.get('is_plugin'))['is_suppressed']
            visible_app = next(pane for pane in shortcut_panes if pane.get('is_focused') and
                               not pane.get('is_suppressed') and not pane.get('is_plugin') and
                               pane['tab_id'] == source_pane['tab_id'])
            assert not visible_app['is_floating']
            for key in ('pane_x', 'pane_y', 'pane_rows', 'pane_columns'):
                assert visible_app[key] == source_pane[key], (key, visible_app[key], source_pane[key])
            action('write-chars', '\n')
            wait_for(lambda: any(pane['id'] == origin_id and not pane.get('is_plugin') and not pane.get('is_suppressed')
                                for pane in json.loads(action('list-panes', '--json', '--all'))), 'original shell restored')
            action('write-chars', "printf 'CC_PANE_RESTORED_%s\\n' \"$CC_PANE_KEEP\"\n")
            wait_for(lambda: 'CC_PANE_RESTORED_preserved' in action('dump-screen'), 'same shell state restored')
            print('PASS: shortcut current-pane launch replaces workspace view and restores the same live shell')
            os.write(master, b"\x07a")
            wait_for(lambda: "Installed and saved apps" in action("dump-screen"), "app picker shortcut")
            os.write(master, b"Browse catalogs")
            time.sleep(0.2)  # Let fzf apply its asynchronous query before accepting.
            os.write(master, b"\r")
            wait_for(lambda: "Choose catalog" in action("dump-screen"), "catalog source picker")
            catalog_screen = action("dump-screen")
            for name in ("Terminal Trove", "Awesome TUIs", "Awesome CLI/TUI Apps", "Homebrew Formulae"):
                assert name in catalog_screen, catalog_screen
            os.write(master, b"Awesome TUIs")
            time.sleep(0.2)
            os.write(master, b"\r")
            wait_for(lambda: "full index" in action("dump-screen"), "cached catalog results")
            os.write(master, b"btop")
            wait_for(lambda: "https://github.com/aristocratos/btop" in action("dump-screen"), "catalog text preview")
            os.write(master, b"\r")
            wait_for(lambda: "Open in new tiled pane" in action("dump-screen"), "installed app actions")
            os.write(master, b"\r")
            wait_for(lambda: "cpu" in action("dump-screen").lower(), "catalog launches configured btop")
            wait_for(lambda: len(json.loads(action("list-panes", "--json", "--all"))) == original_count + 1,
                     "temporary picker closes after launch")
            assert action("are-floating-panes-visible").strip() == "false", "Default app launch should be tiled"
            action("close-pane")
            os.write(master, b"\x07a")
            wait_for(lambda: "Installed and saved apps" in action("dump-screen"), "reopen app picker")
            os.write(master, b"\x1b")
            wait_for(lambda: len(json.loads(action("list-panes", "--json", "--all"))) == original_count,
                     "Esc closes picker without replacing the underlying shell")
            print("PASS: native app-menu shortcut, all four catalogs, cached fuzzy search/preview, tiled launch, Esc")
            for placement in ("Open floating",):
                launcher("apps")
                wait_for(lambda: "Installed and saved apps" in action("dump-screen"), "CLI floating picker")
                os.write(master, b"btop")
                time.sleep(0.2)
                os.write(master, b"\r")
                wait_for(lambda: "Open in new tiled pane" in action("dump-screen"), "app placement menu")
                os.write(master, placement.encode())
                time.sleep(0.2)
                os.write(master, b"\r")
                wait_for(lambda: "cpu" in action("dump-screen").lower(), placement)
                assert action("are-floating-panes-visible").strip() == "true"
                action("close-pane")
                wait_for(lambda: len(json.loads(action("list-panes", "--json", "--all"))) == original_count,
                         "alternative launch returns to original shell")
            print("PASS: floating app launch preserves the underlying shell")
            launcher('apps')
            wait_for(lambda: 'Installed and saved apps' in action('dump-screen'), 'discovered app picker')
            os.write(master, b'cc-discovery-demo')
            time.sleep(0.2)
            os.write(master, b'\r')
            wait_for(lambda: 'Open in new tiled pane' in action('dump-screen'), 'discovered app actions')
            os.write(master, b'\r')
            wait_for(lambda: 'CC_DISCOVERY_DEMO_READY' in action('dump-screen'), 'discovered app launches from saved folder')
            assert 'cc-discovery-demo' in registry.settings()['apps'], 'pane launch should save the discovered command'
            action('close-pane')
            launcher('apps')
            wait_for(lambda: 'Installed and saved apps' in action('dump-screen'), 'remove app picker')
            os.write(master, b'cc-discovery-demo')
            time.sleep(0.2)
            os.write(master, b'\r')
            wait_for(lambda: 'Remove from apps' in action('dump-screen'), 'remove action')
            os.write(master, b'Remove from apps')
            time.sleep(0.2)
            os.write(master, b'\r')
            wait_for(lambda: 'cc-discovery-demo' in registry.settings()['hidden'], 'app remains hidden after rescan')
            os.write(master, b'\x1b')
            wait_for(lambda: len(json.loads(action('list-panes', '--json', '--all'))) == original_count, 'remove picker closes')
            assert demo.exists(), 'removing a launcher must retain the executable'
            registry.restore('cc-discovery-demo')
            print('PASS: cached app discovery, saved search folder, dynamic pane launch, persistent removal, restore')
            resources(process.pid, "agents and monitors suspended")
            initial_layout = action("dump-layout")
            os.write(master, b"\x07\x10r")  # Ctrl-g, Ctrl-p, r: split right, return to Locked.
            wait_for(lambda: action("dump-layout") != initial_layout, "keyboard split")
            os.write(master, b"printf 'CC_SMOKE_OK\\n'\r")
            wait_for(lambda: "CC_SMOKE_OK" in action("dump-screen"), "shell input after keyboard split")
            print("PASS: locked-mode input, leader shortcut, keyboard split")
            def focused_title():
                return next(pane["title"] for pane in json.loads(action("list-panes", "--json", "--all"))
                            if pane.get("is_focused") and not pane.get("is_plugin"))
            shell_name = Path(env.get("SHELL", "/bin/bash")).name
            if shell_name in ("zsh", "bash"):
                wait_for(lambda: focused_title() == shell_name, "idle shell title")
                os.write(master, b"sleep 2\r")
                wait_for(lambda: focused_title() == "sleep", "running command title")
                wait_for(lambda: focused_title() == shell_name, "title returns to shell")
                action("rename-pane", "MY PANEL")
                os.write(master, b"sleep 1\r")
                time.sleep(0.2)
                assert focused_title() == "MY PANEL", "manual title should override automatic title"
                time.sleep(1)
                launcher("titles")
                wait_for(lambda: focused_title() == shell_name, "clear fixed title")
                action("rename-pane", "BACKUP TITLE")
                launcher("titles", "--all")
                backups = list((base / "state/data/layouts").glob("before-auto-titles-*.kdl"))
                assert len(backups) == 1 and "BACKUP TITLE" in backups[0].read_text()
                wait_for(lambda: focused_title() == shell_name, "clear all fixed titles")
                print("PASS: automatic command titles, idle reset, manual override, fixed-title clearing")
            action("resize", "increase", "left")
            action("move-pane", "left")
            action("toggle-pane-embed-or-floating")
            assert action("are-floating-panes-visible").strip() == "true"
            action("toggle-pane-embed-or-floating")
            print("PASS: resize, movement, tiled/floating transitions")
            launcher("pane", "yazi", "--floating", "--cwd", str(project))
            wait_for(lambda: "not installed" in action("dump-screen"), "missing optional tool fallback")
            action("close-pane")
            launcher("pane", "lazygit", "--floating", "--cwd", str(project))
            wait_for(lambda: "not a Git repository" in action("dump-screen"), "non-Git directory fallback")
            action("close-pane")
            launcher("pane", "btop", "--floating", "--cwd", str(project))
            time.sleep(1)
            screen = action("dump-screen")
            if "ERROR" in screen or "error:" in screen.lower():
                raise RuntimeError(screen)
            assert "btop" in action("list-panes", "--json", "--command"), "btop process did not start"
            resources(process.pid, "btop active, agents suspended")
            action("close-pane")
            print("PASS: btop runs with the project theme; optional/non-Git fallbacks leave a shell")
            subprocess.run(["git", "init", "--quiet", str(project)], check=True, capture_output=True)
            launcher("pane", "lazygit", "--floating", "--cwd", str(project))
            wait_for(lambda: "status" in action("dump-screen").lower(), "Lazygit UI startup with custom config")
            assert "error:" not in action("dump-screen").lower()
            action("close-pane")
            print("PASS: Lazygit UI starts with local configuration in a disposable repository")
            state = base / "state"
            # Test Newsboat with an entirely local RSS file, not the user's feed database.
            rss = base / "sample.xml"
            rss.write_text('<rss version="2.0"><channel><title>CC Test Feed</title><link>https://example.com</link><description>Local test</description>'
                           '<item><title>Item one</title><guid>cc-one</guid><link>https://example.com/one</link></item>'
                           '<item><title>Item two</title><guid>cc-two</guid><link>https://example.com/two</link></item></channel></rss>')
            (state / "config/feeds").write_text(rss.as_uri() + "\n")
            newsconf = state / "config/newsboat.conf"
            newsconf.write_text(newsconf.read_text().replace("refresh-on-startup yes", "refresh-on-startup no"))
            newsenv = dict(env, CC_ROOT=str(ROOT), CC_CONFIG=str(state / "config"), CC_DATA=str(state / "data"))
            panel = [str(ROOT / "bin/cc-panel"), "newsboat"]
            subprocess.run(panel + ["-x", "reload"], env=newsenv, check=True, capture_output=True)
            unread = subprocess.check_output(panel + ["-x", "print-unread"], env=newsenv, text=True).strip()
            assert unread.startswith("2"), unread
            launcher("pane", "newsboat", "--floating", "--cwd", str(project))
            wait_for(lambda: "CC Test Feed" in action("dump-screen"), "Newsboat local feed UI")
            action("write-chars", "C")  # Newsboat: mark all feeds read.
            time.sleep(0.1)
            action("write-chars", "y")  # Confirm only the disposable local test feed.
            time.sleep(0.3)
            action("write-chars", "q")
            time.sleep(0.3)
            action("close-pane")
            unread = subprocess.check_output(panel + ["-x", "print-unread"], env=newsenv, text=True).strip()
            assert unread.startswith("0"), unread
            print("PASS: Newsboat UI loads local articles and read-state persists across processes")
            launcher("add-workspace", "system", "--cwd", str(project))
            assert action("query-tab-names").count("SYSTEM") == 2
            fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
            action("write-chars", "\n")
            wait_for(lambda: "Choose an app" in action("dump-screen"), "SYSTEM starter picker")
            action("write-chars", "btop")
            time.sleep(0.2)
            action("write-chars", "\r")
            wait_for(lambda: "cpu" in action("dump-screen").lower(), "compact SYSTEM monitor")
            screen = action("dump-screen")
            assert "Terminal size too small" not in screen, screen
            panes = json.loads(action("list-panes", "--json", "--all"))
            new_tab_position = max(pane["tab_position"] for pane in panes)
            terminals = [pane for pane in panes if pane["tab_position"] == new_tab_position and not pane.get("is_plugin")]
            assert len(terminals) == 3, [(pane["title"], pane["tab_position"]) for pane in terminals]
            action("focus-next-pane")
            action("write-chars", "\n")
            wait_for(lambda: "Choose an app" in action("dump-screen"), "lower SYSTEM starter picker")
            os.write(master, b"\x1b")
            time.sleep(0.5)
            action("write-chars", "printf 'CC_CANCEL_%s\\n' SHELL_READY\n")
            wait_for(lambda: "CC_CANCEL_SHELL_READY" in action("dump-screen"), "cancel returns to shell")
            print("PASS: SYSTEM picker fills its pane with compact btop; cancel opens a shell at 100×30")
            action("close-tab")
            fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 160, 0, 0))
            launcher("save-layout", "smoke-saved")
            saved = base / "state/data/layouts/smoke-saved.kdl"
            assert saved.is_file()
            check = subprocess.run(["zellij", "--config", str(CONFIG), "--layout", str(saved), "setup", "--check"],
                                   env=env, capture_output=True, text=True)
            assert check.returncode == 0, check.stderr
            action("save-session")
            before = action("dump-layout")
            launcher("detach")
            process.wait(timeout=10)
            process, master = start("--layout", "system")
            assert action("query-tab-names") == names
            assert action("dump-layout") == before
            print("PASS: saved layout parses; live reattachment preserves changes and adds no tabs")
            action("save-session")
            subprocess.run(["zellij", "kill-session", SESSION], env=env, check=True, capture_output=True)
            process.wait(timeout=10)
            process, master = start("--layout", "dev")
            assert action("query-tab-names") == names
            # No force-run flag is used; commands return behind Enter banners.
            resurrected = action("dump-layout")
            assert "start_suspended=true" in resurrected or "start_suspended true" in resurrected
            print("PASS: exited session resurrects with all tabs and suspended commands")
            os.write(master, b"\x07d")
            process.wait(timeout=10)
            print("PASS: keyboard detach returns the terminal after resurrection")
        finally:
            # This is the uniquely named session created by this script, never a user's session.
            subprocess.run(["zellij", "delete-session", "--force", SESSION], env=env, capture_output=True, timeout=10)
            for process, master, thread in children:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
                thread.join(timeout=1)
                os.close(master)


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print("Smoke test failed: " + str(error), file=sys.stderr)
        sys.exit(1)
