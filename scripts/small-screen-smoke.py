#!/usr/bin/env python3
"""Check native btop at small PTY sizes using disposable preferences."""
import fcntl
import os
import pty
import re
import select
import struct
import subprocess
import tempfile
import termios
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def terminal(command, env, rows, columns):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
    def control_terminal():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    process = subprocess.Popen(command, env=env, stdin=slave, stdout=slave,
                               stderr=slave, preexec_fn=control_terminal)
    os.close(slave)
    output = bytearray()
    try:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    output.extend(os.read(master, 65536))
                except OSError:
                    break
            if process.poll() is not None:
                break
        os.write(master, b"q")
        deadline = time.monotonic() + 5
        while process.poll() is None and time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    output.extend(os.read(master, 65536))
                except OSError:
                    break
        try:
            # EOF/EIO can precede child exit (for example during Newsboat cleanup).
            # Reap it within the remaining exit deadline before reporting failure.
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("Tool did not exit: " + output.decode(errors="replace")[-1500:]) from error
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        os.close(master)
    return process.returncode, re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output.decode(errors="replace"))


def main():
    with tempfile.TemporaryDirectory(prefix="cc-small-screen-") as temp:
        base = Path(temp)
        env = dict(os.environ, HOME=str(base), COMMAND_CENTER_HOME=str(base / "state"),
                   TERM="xterm-256color", LANG="en_US.UTF-8")
        for preset, label, rows, columns, marker in (
            (1, "CPU", 8, 60, "cpu"),
            (2, "memory/disks", 10, 60, "mem"),
            (3, "network", 6, 60, "net"),
            (4, "processes", 16, 60, "Pid"),
        ):
            code, screen = terminal([str(ROOT / "bin/command-center"), "run", "btop",
                                     "--compact", "--preset", str(preset)], env, rows, columns)
            if code or "Terminal size too small" in screen or "ERROR:" in screen or marker.lower() not in screen.lower():
                raise RuntimeError(f"{label} at {columns}×{rows} failed: {screen[-1200:]}")
            print(f"PASS: compact btop {label} renders at {columns}×{rows}")
        config = base / "state/config"
        rss = base / "sample.xml"
        rss.write_text('<rss version="2.0"><channel><title>Small Feed</title>'
                       '<link>https://example.com</link><description>Local test</description>'
                       '<item><title>Small article</title><guid>small-one</guid>'
                       '<link>https://example.com/one</link></item></channel></rss>')
        (config / "feeds").write_text(rss.as_uri() + '\n')
        newsconf = config / "newsboat.conf"
        newsconf.write_text(newsconf.read_text().replace("refresh-on-startup yes", "refresh-on-startup no"))
        command = [str(ROOT / "bin/command-center"), "run", "newsboat"]
        subprocess.run(command + ["-x", "reload"], env=env, check=True, capture_output=True)
        code, screen = terminal(command, env, 10, 40)
        if code or "Small Feed" not in screen or "ERROR:" in screen:
            raise RuntimeError("Newsboat at 40×10 failed: " + screen[-1200:])
        print("PASS: configured Newsboat loads a local feed in the current 40×10 terminal")


if __name__ == "__main__":
    main()
