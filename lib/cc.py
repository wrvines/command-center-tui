"""Small, standard-library helpers for launch/configuration; no background service."""
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def platform_paths(home=None, system=None, environ=None):
    home = Path(home or Path.home())
    system = system or sys.platform
    env = os.environ if environ is None else environ
    def xdg(name, fallback):
        value = env.get(name, "")
        return Path(value) if value and Path(value).is_absolute() else home / fallback
    config = xdg("XDG_CONFIG_HOME", ".config") / "command-center"
    if system == "darwin":
        return config, home / "Library/Application Support/command-center", home / "Library/Caches/command-center"
    if system == "linux":
        return config, xdg("XDG_DATA_HOME", ".local/share") / "command-center", xdg("XDG_CACHE_HOME", ".cache") / "command-center"
    raise ValueError("Use install.ps1 with a WSL 2 Linux distribution on Windows")


def paths():
    override = os.environ.get("COMMAND_CENTER_HOME")
    if override:
        base = Path(override).expanduser().resolve()
        return base / "config", base / "data", base / "cache"
    return platform_paths()


def seed_defaults(config, system=None):
    system = system or sys.platform
    config.mkdir(parents=True, exist_ok=True, mode=0o700)
    for source, name in (
        ("config/preferences.json", "preferences.json"),
        ("config/newsboat/urls.example", "feeds"),
        ("config/newsboat/config", "newsboat.conf"),
        ("config/btop/btop.conf", "btop.conf"),
        ("config/btop/btop-compact.conf", "btop-compact.conf"),
        ("config/lazygit/config.yml", "lazygit.yml"),
    ):
        content = (ROOT / source).read_bytes()
        if name == "newsboat.conf" and system == "linux":
            content = content.replace(b'browser "open %u"', b'browser "xdg-open %u"')
        try:
            with (config / name).open("xb") as handle:
                handle.write(content)
            (config / name).chmod(0o600)
        except FileExistsError:
            pass


def seed():
    config, data, cache = paths()
    for directory in (config, config / "zellij", data, cache, data / "layouts", data / "newsboat"):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    seed_defaults(config)
    return config, data, cache


def zellij_config_content(system=None, theme="command-center"):
    if theme not in ("command-center", "oh-my-pi"):
        raise ValueError("Unknown command-center theme: " + theme)
    source = ROOT / "config/zellij/config.kdl"
    content = source.read_text().replace('default_shell "/bin/zsh"',
                                         'default_shell ' + json.dumps(str(ROOT / "bin/cc-shell")))
    content = content.replace('"{{CC_LAUNCHER}}"', json.dumps(str(ROOT / "bin/command-center")))
    if theme == "oh-my-pi":
        content = content.replace('theme "command-center"', 'theme "oh-my-pi"')
        content += "\n" + (ROOT / "config/zellij/themes/oh-my-pi.kdl").read_text()
    if (system or sys.platform) == "darwin":
        return content
    # Native OSC 52 clipboard support is the portable fallback.
    content = content.replace('copy_command "pbcopy"\n', '')
    if shutil.which("clip.exe", path=tool_env()["PATH"]):
        content += '\ncopy_command "clip.exe"\n'
    return content


def zellij_config(theme="command-center"):
    content = zellij_config_content(theme=theme)
    config, _, _ = paths()
    filename = "platform.kdl" if theme == "command-center" else "platform-oh-my-pi.kdl"
    target = config / "zellij" / filename
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not target.exists() or target.read_text() != content:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", dir=target.parent, delete=False) as handle:
            handle.write(content)
            temporary = Path(handle.name)
        temporary.replace(target)
    return target


def preferences():
    config, _, _ = paths()
    target = config / "preferences.json"
    source = target if target.exists() else ROOT / "config/preferences.json"
    values = json.loads(source.read_text())
    if not isinstance(values, dict):
        raise ValueError("preferences.json must contain a JSON object")
    return values


def valid_name(name):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name):
        raise ValueError("Use a name of 1–64 letters, numbers, underscores, or hyphens")
    return name


def layout_source(name):
    valid_name(name)
    _, data, _ = paths()
    custom = data / "layouts" / (name + ".kdl")
    builtin = ROOT / "config/zellij/layouts" / (name + ".kdl")
    if custom.is_file():
        return custom
    if builtin.is_file():
        return builtin
    raise ValueError("Unknown layout: " + name)


def render_layout(name, project):
    content = layout_source(name).read_text()
    # Replace complete quoted placeholders with properly escaped KDL strings.
    for key, value in (("CC_PANEL", ROOT / "bin/cc-panel"), ("PROJECT", project)):
        content = content.replace('"{{' + key + '}}"', json.dumps(str(value)))
    if "{{" in content:
        raise ValueError("Unresolved layout placeholder")
    return content


def tool_env():
    config, data, cache = paths()
    env = os.environ.copy()
    env.update(CC_ROOT=str(ROOT), CC_CONFIG=str(config), CC_DATA=str(data),
               CC_CACHE=str(cache))
    extra = ("/opt/homebrew/bin", "/usr/local/bin", "/home/linuxbrew/.linuxbrew/bin",
             str(Path.home() / ".linuxbrew/bin"), str(Path.home() / ".local/bin"))
    env["PATH"] = env.get("PATH", "") + os.pathsep + os.pathsep.join(extra)
    return env
