#!/usr/bin/env python3
"""Manifest-based install/rollback of owned launcher and terminal integrations."""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
from cc import platform_paths, seed_defaults
BEGIN = "# BEGIN command-center (managed)"
END = "# END command-center (managed)"


def checksum(content):
    return hashlib.sha256(content).hexdigest()


def write_atomic(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.chmod(mode)
    temporary.replace(path)


def matches(entry):
    path = Path(entry["path"])
    if entry["kind"] == "link":
        return path.is_symlink() and os.readlink(path) == entry["target"]
    return (path.is_file() and not path.is_symlink()
            and checksum(path.read_bytes()) == entry["installed_sha256"])


def present(entry):
    path = Path(entry["path"])
    return path.exists() or path.is_symlink()


def load_manifest(manifest):
    """Read and validate the ownership record before trusting any recorded path."""
    try:
        record = json.loads(manifest.read_text())
    except (OSError, ValueError) as error:
        raise ValueError("Cannot read installation manifest " + str(manifest) + ": " + str(error)) from error
    if (not isinstance(record, dict) or not isinstance(record.get("root"), str)
            or not isinstance(record.get("entries"), list)
            or not isinstance(record.get("installed_at"), str)
            or not re.fullmatch(r"[0-9]{8}-[0-9]{6}-[0-9]{6}", record["installed_at"])):
        raise ValueError("Invalid installation manifest: " + str(manifest))
    for entry in record["entries"]:
        if (not isinstance(entry, dict) or entry.get("kind") not in ("link", "file")
                or not isinstance(entry.get("path"), str)):
            raise ValueError("Invalid installation manifest entry: " + str(manifest))
        if entry["kind"] == "link":
            if not isinstance(entry.get("target"), str):
                raise ValueError("Invalid installation manifest link: " + str(manifest))
        else:
            if not isinstance(entry.get("existed"), bool) or not isinstance(entry.get("mode"), int):
                raise ValueError("Invalid installation manifest entry: " + str(manifest))
            for key in ("original_sha256", "installed_sha256"):
                if not isinstance(entry.get(key), str):
                    raise ValueError("Invalid installation manifest entry: " + str(manifest))
            if entry["existed"] and not isinstance(entry.get("backup"), str):
                raise ValueError("Invalid installation manifest backup: " + str(manifest))
    return record


def install(home, data, manifest, dry_run, system=None, no_ghostty=False, config=None):
    system = system or sys.platform
    config = config or platform_paths(home, system, {})[0]
    if manifest.exists():
        record = load_manifest(manifest)
        if record["root"] != str(ROOT):
            raise ValueError("An installation from another checkout owns these integrations")
        unmatched = [entry for entry in record["entries"] if not matches(entry)]
        if unmatched and all(not present(entry) for entry in unmatched):
            # The previous install stopped before creating these entries. Undo the entries
            # it did create so this run starts from the recorded original state.
            if dry_run:
                print("An interrupted installation would be recovered before installing.")
                return
            for entry in reversed(record["entries"]):
                if matches(entry):
                    restore(entry)
            manifest.unlink()
            print("Recovered from an interrupted installation; installing again.")
        elif unmatched:
            raise ValueError("Managed files have changed since installation. Preserve your edits; inspect " + str(manifest))
        else:
            print("Already installed; Ghostty still starts a normal shell.")
            return
    ghostty = (home / "Library/Application Support/com.mitchellh.ghostty" if system == "darwin"
               else config.parent / "ghostty")
    # Linux installations commonly use config; honor an existing config.ghostty.
    modern = ghostty / ("config.ghostty" if system == "darwin" or (ghostty / "config.ghostty").exists() else "config")
    legacy = ghostty / ("config" if modern.name == "config.ghostty" else "config.ghostty")
    if not no_ghostty and (modern.is_symlink() or legacy.is_symlink()):
        raise ValueError("Ghostty config is a symlink; add the include manually rather than replacing its ownership")
    original = modern.read_bytes() if not no_ghostty and modern.exists() else b""
    if BEGIN.encode() in original or END.encode() in original:
        raise ValueError("Found an existing managed block without a manifest; inspect it before installing")
    block = (BEGIN + "\nconfig-file = " + str(ROOT / "config/ghostty/command-center.ghostty") + "\n" + END + "\n").encode()
    updated = original + (b"\n" if original and not original.endswith(b"\n") else b"") + block
    entries = []
    for name in ("command-center", "ccenter"):
        target = home / ".local/bin" / name
        if target.exists() or target.is_symlink():
            raise ValueError("Will not overwrite existing command: " + str(target))
        # Do not shadow an unrelated command already on PATH.
        found = shutil.which(name)
        if home == Path.home().resolve() and found and Path(found) != target:
            raise ValueError("Command name is already in use on PATH: " + name)
        entries.append({"kind": "link", "path": str(target), "target": str(ROOT / "bin/command-center")})
    if not no_ghostty:
        entries.append({"kind": "file", "path": str(modern), "existed": modern.exists(),
                    "original_sha256": checksum(original), "installed_sha256": checksum(updated),
                    "mode": stat.S_IMODE(modern.stat().st_mode) if modern.exists() else 0o600})
    for entry in entries:
        print("Add launcher link: " + entry["path"] if entry["kind"] == "link" else "Append Ghostty include: " + entry["path"])
    print("Back up managed terminal settings; seed editable preferences and feeds; leave shell startup unchanged.")
    if dry_run:
        return
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = data / "backups" / stamp
    backup.mkdir(parents=True, mode=0o700)
    backups = []
    for path in (() if no_ghostty else (modern, legacy)):
        if path.exists():
            saved = backup / path.name
            shutil.copy2(path, saved)
            backups.append({"path": str(path), "backup": str(saved), "sha256": checksum(path.read_bytes())})
            if path == modern:
                entries[-1]["backup"] = str(saved)
    record = {"version": 1, "root": str(ROOT), "entries": entries, "backups": backups,
              "installed_at": stamp}
    # Store expected ownership before changing anything, so interrupted installs can be inspected.
    write_atomic(manifest, json.dumps(record, indent=2).encode() + b"\n")
    try:
        for entry in entries:
            path = Path(entry["path"])
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if entry["kind"] == "link":
                path.symlink_to(entry["target"])
            else:
                if (path.read_bytes() if path.exists() else b"") != original:
                    raise ValueError("Ghostty config changed during installation; stopping")
                write_atomic(path, updated, entry["mode"])
        # Seed local settings without replacing existing customization.
        seed_defaults(config, system)
    except Exception:
        # Undo only entries that still match exactly what this operation wrote.
        for entry in reversed(entries):
            if matches(entry):
                restore(entry)
        manifest.unlink()
        raise
    print("Installed. In your terminal, run: command-center (or ccenter)")
    if not no_ghostty:
        print("Open a new Ghostty window to load the appearance include.")
    if str(home / ".local/bin") not in os.environ.get("PATH", "").split(os.pathsep):
        print('Add launchers to this shell with: export PATH="$HOME/.local/bin:$PATH"')
    print("Backup manifest: " + str(manifest))


def restore(entry):
    path = Path(entry["path"])
    if entry["kind"] == "file" and entry["existed"]:
        saved = Path(entry["backup"])
        content = saved.read_bytes()
        if checksum(content) != entry["original_sha256"]:
            raise ValueError("Backup checksum mismatch: " + str(saved))
        write_atomic(path, content, entry["mode"])
    else:
        path.unlink()


def uninstall(manifest, dry_run):
    if not manifest.exists():
        print("No managed installation found.")
        return
    record = load_manifest(manifest)
    if record["root"] != str(ROOT):
        raise ValueError("Run uninstall from the checkout named in the installation manifest")
    # Validate all entries and backups before making even the first change.
    for entry in record["entries"]:
        if not matches(entry):
            raise ValueError("Refusing to overwrite a later edit: " + entry["path"] + ". See docs/troubleshooting.md.")
        if entry["kind"] == "file" and entry["existed"]:
            if checksum(Path(entry["backup"]).read_bytes()) != entry["original_sha256"]:
                raise ValueError("Backup checksum mismatch; leaving installation unchanged")
        print("Undo managed integration: " + entry["path"])
    if dry_run:
        return
    for entry in reversed(record["entries"]):
        restore(entry)
    archive = manifest.parent / ("uninstalled-" + record["installed_at"] + ".json")
    manifest.replace(archive)
    print("Removed launcher links and restored Ghostty config. Packages, preferences, sessions, and backups retained.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--home", type=Path, default=Path.home(), help="Installation home; useful for isolated rollback tests")
    parser.add_argument("--no-ghostty", action="store_true", help="Install launchers without changing Ghostty")
    parser.add_argument("--platform", choices=("darwin", "linux"), default=sys.platform, help=argparse.SUPPRESS)
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    config, data, _ = platform_paths(home, args.platform, os.environ if home == Path.home().resolve() else {})
    manifest = data / "install-manifest.json"
    if args.dry_run:
        (install(home, data, manifest, True, args.platform, args.no_ghostty, config) if args.action == "install" else uninstall(manifest, True))
        return
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = data / "install.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError("Another install operation is active (or was interrupted): " + str(lock))
    try:
        if args.action == "install":
            install(home, data, manifest, False, args.platform, args.no_ghostty, config)
        else:
            uninstall(manifest, False)
    finally:
        lock.rmdir()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print("command-center setup: " + str(error), file=sys.stderr)
        sys.exit(1)
