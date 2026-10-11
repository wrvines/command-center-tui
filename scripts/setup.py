#!/usr/bin/env python3
"""Install maintained dependencies and delegate reversible user integrations."""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
from cc import tool_env

CORE = ("zellij", "btop", "newsboat", "lazygit", "curl", "git")


def dependency_plan(env):
    missing = [name for name in CORE if not shutil.which(name, path=env["PATH"])]
    commands = []
    if missing:
        brew = shutil.which("brew", path=env["PATH"])
        if not brew:
            raise ValueError("Missing tools: " + ", ".join(missing) +
                             ". Install Homebrew from https://brew.sh (macOS/Linux/WSL 2), "
                             "or install these with your package manager and use --no-dependencies.")
        commands.append([brew, "install", *missing])
    return commands


def check_versions(env):
    executable = shutil.which("zellij", path=env["PATH"])
    if not executable:
        raise ValueError("Zellij is required; rerun without --no-dependencies or install Zellij 0.45.1+")
    result = subprocess.run([executable, "--version"], env=env, capture_output=True, text=True, timeout=10, check=True)
    version = re.search(r"(\d+)\.(\d+)\.(\d+)", result.stdout)
    if not version or tuple(map(int, version.groups())) < (0, 45, 1):
        raise ValueError("This configuration requires Zellij 0.45.1+. Upgrade Zellij with your package manager first.")


def main():
    if sys.version_info < (3, 9):
        raise ValueError("Python 3.9 or newer is required")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without installing packages or writing files")
    parser.add_argument("--no-dependencies", action="store_true", help="Use tools already installed by your package manager")
    parser.add_argument("--no-ghostty", action="store_true", help="Leave Ghostty configuration untouched")
    parser.add_argument("--with-ghostty", action="store_true", help="Install Ghostty's Homebrew cask on macOS if absent")
    args = parser.parse_args()
    if sys.platform not in ("darwin", "linux"):
        raise ValueError("Use install.ps1 with WSL 2 on Windows")
    if args.with_ghostty and (sys.platform != "darwin" or args.no_ghostty):
        raise ValueError("--with-ghostty requires macOS and cannot be combined with --no-ghostty")
    env = tool_env()
    commands = [] if args.no_dependencies else dependency_plan(env)
    if args.with_ghostty and not Path("/Applications/Ghostty.app").exists():
        brew = shutil.which("brew", path=env["PATH"])
        if not brew:
            raise ValueError("Homebrew is required for --with-ghostty: https://brew.sh")
        commands.append([brew, "install", "--cask", "ghostty"])
    # Preflight collisions/ownership before installing any packages.
    integration = [sys.executable, str(ROOT / "scripts/manage.py"), "install"]
    if args.no_ghostty:
        integration.append("--no-ghostty")
    subprocess.run(integration + ["--dry-run"], env=env, check=True)
    for command in commands:
        print("Dependencies: " + " ".join(command), flush=True)
        if not args.dry_run:
            subprocess.run(command, env=env, check=True)
    if args.dry_run:
        print("Dry run: no packages or user files changed.")
        return 0
    missing = [name for name in CORE if not shutil.which(name, path=env["PATH"])]
    if missing:
        raise ValueError("Missing required tools: " + ", ".join(missing))
    check_versions(env)
    subprocess.run([str(ROOT / "scripts/validate.sh")], env=env, check=True)
    subprocess.run(integration, env=env, check=True)
    print('Launch: command-center (or "$HOME/.local/bin/command-center" if it is not on PATH yet).')
    print("Starter workspace shortcut: command-center reset (equivalent to --session fresh-start; an existing session is reused).")
    if sys.platform == "linux" and not args.no_ghostty:
        print("Install Ghostty separately using https://ghostty.org/docs/install/binary, or use your existing terminal.")
    print("AI agents are optional; install and authenticate each one separately. See docs/install.md.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print("command-center install: " + str(error), file=sys.stderr)
        sys.exit(1)
