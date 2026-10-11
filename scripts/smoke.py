#!/usr/bin/env python3
"""Exercise a disposable real Zellij session through a PTY; never start AI requests."""
import fcntl
import json
import os
import pty
import select
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
        env = dict(os.environ, COMMAND_CENTER_HOME=str(base / "state"), TERM="xterm-256color")
        env.pop("ZELLIJ", None)
        env.pop("TMUX", None)
        children = []

        def action(*args):
            result = subprocess.run(["zellij", "--config", str(CONFIG), "--session", SESSION, "action", *args],
                                    env=env, capture_output=True, text=True, timeout=10)
            if result.returncode:
                raise RuntimeError(result.stderr or result.stdout or "Zellij action failed")
            return result.stdout

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
                if test():
                    return
                time.sleep(0.1)
            raise RuntimeError("Failed: " + description)

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
            resources(process.pid, "agents and monitors suspended")
            initial_layout = action("dump-layout")
            os.write(master, b"\x07\x10r")  # Ctrl-g, Ctrl-p, r: split right, return to Locked.
            wait_for(lambda: action("dump-layout") != initial_layout, "keyboard split")
            os.write(master, b"printf 'CC_SMOKE_OK\\n'\r")
            wait_for(lambda: "CC_SMOKE_OK" in action("dump-screen"), "shell input after keyboard split")
            print("PASS: locked-mode input, leader shortcut, keyboard split")
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
            action("close-tab")
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
