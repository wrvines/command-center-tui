#!/usr/bin/env python3
"""Validate configurations and behavior without changing the user's setup."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
from cc import render_layout, zellij_config_content


def run(command, **kwargs):
    result = subprocess.run(command, capture_output=True, text=True, **kwargs)
    if result.returncode or "Failed to parse" in result.stdout + result.stderr:
        raise RuntimeError("Validation failed:\n" + result.stdout + result.stderr)
    return result


def main():
    run([sys.executable, "-B", str(ROOT / "scripts/themes.py"), "--check"])
    for folder in (ROOT / "bin", ROOT / "lib", ROOT / "scripts", ROOT / "tests"):
        for source in folder.iterdir():
            if source.is_file() and (source.suffix == ".py" or source.name in ("command-center", "cc-weather")):
                compile(source.read_text(), str(source), "exec")
    for shell in [ROOT / "bin/cc-panel", ROOT / "bin/cc-shell", ROOT / "config/shell/bashrc",
                  *ROOT.glob("*.sh"), *(ROOT / "scripts").glob("*.sh")]:
        run(["bash", "-n", str(shell)])
    if shutil.which("zsh"):
        for shell in (ROOT / "config/shell/titles.zsh", ROOT / "config/shell/zsh/.zshenv"):
            run(["zsh", "-n", str(shell)])
    with tempfile.TemporaryDirectory(prefix="cc-platform-") as temp:
        for system in ("darwin", "linux"):
            for theme in ("command-center", "oh-my-pi"):
                platform_config = Path(temp) / (system + "-" + theme + ".kdl")
                platform_config.write_text(zellij_config_content(system, theme))
                run(["zellij", "--config", str(platform_config), "setup", "--check"])
                print("Platform config valid: " + system + " / " + theme)
    config = ROOT / "config/zellij/config.kdl"
    for source in sorted((ROOT / "config/zellij/layouts").glob("*.kdl")):
        run(["zellij", "--config", str(config), "--layout-string",
             render_layout(source.stem, Path('/private/tmp/project with spaces and "quotes"')),
             "setup", "--check"])
        print("Layout valid: " + source.stem)
    ghostty = shutil.which("ghostty")
    if not ghostty and Path("/Applications/Ghostty.app/Contents/MacOS/ghostty").exists():
        ghostty = "/Applications/Ghostty.app/Contents/MacOS/ghostty"
    if ghostty:
        for source in ("config/ghostty/command-center.ghostty", "config/ghostty/themes/OhMyPi-DarkTerminal"):
            run([ghostty, "+validate-config", "--config-file=" + str(ROOT / source)])
            print("Ghostty config valid: " + source)
    else:
        print("Ghostty checks skipped: not installed on this host (normal for remote Debian)")
    # Export to OPML loads Newsboat's config/feed list but performs no feed requests.
    with tempfile.TemporaryDirectory(prefix="cc-newsboat-") as temp:
        run(["newsboat", "-C", str(ROOT / "config/newsboat/config"), "-u",
             str(ROOT / "config/newsboat/urls.example"), "-c", temp + "/cache.db", "-e"])
    print("Newsboat config and feeds valid")
    tests = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"], cwd=ROOT)
    return tests.returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
