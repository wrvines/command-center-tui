"""Host-local app discovery and saved argv launchers; scanning never runs candidates."""
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from cc import paths, tool_env

BUILTINS = {
    'hermes': 'Hermes Agent', 'opencode': 'OpenCode', 'pi': 'Pi', 'codex': 'Codex CLI',
    'btop': 'btop (compact)', 'abtop': 'abtop (AI agents)', 'newsboat': 'Newsboat',
    'lazygit': 'Lazygit', 'yazi': 'Yazi', 'lazydocker': 'Lazydocker', 'amp': 'Amp editor',
}
PANEL_TOOLS = ('shell', *BUILTINS, 'weather', 'logs', 'services')
APP_ID = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9+_.@-]{0,127}\Z')
FORMULA = re.compile(r'[a-z0-9][a-z0-9+_.@-]{0,199}\Z')
AUTO_EXCLUDE = {'tmux', 'zellij', 'screen', 'command-center', 'ccenter'}


def app_id(value):
    if not isinstance(value, str) or not APP_ID.fullmatch(value):
        raise ValueError('App names must start with a letter or number and contain no spaces or shell syntax')
    return value.casefold()


def executable(path):
    return Path(path).is_file() and os.access(path, os.X_OK)


class Registry:
    def __init__(self, config_dir=None, cache_dir=None, home=None, environ=None, system=None):
        config, _, cache = paths()
        self.file = Path(config_dir or config) / 'apps.json'
        self.cache = Path(cache_dir or cache) / 'catalogs'
        self.home = Path(home or Path.home())
        self.env = dict(tool_env() if environ is None else environ)
        self.system = system or sys.platform

    def settings(self):
        try:
            if self.file.stat().st_size > 1024 * 1024:
                raise ValueError('registry exceeds 1 MiB')
            data = json.loads(self.file.read_text())
            if not isinstance(data, dict) or data.get('schema') != 1:
                raise ValueError('unsupported registry schema')
            if not isinstance(data.get('apps'), dict) or not isinstance(data.get('folders'), list) or not isinstance(data.get('hidden'), list):
                raise ValueError('invalid registry fields')
            data.setdefault('uninstall', {})
            if not isinstance(data['uninstall'], dict):
                raise ValueError('invalid uninstall commands')
            for key, app in data['apps'].items():
                if app_id(key) != key or key in PANEL_TOOLS or not isinstance(app, dict):
                    raise ValueError('invalid saved app name')
                argv = app.get('argv')
                if (not isinstance(argv, list) or not argv or len(argv) > 256 or
                        any(not isinstance(arg, str) or '\0' in arg for arg in argv) or not Path(argv[0]).is_absolute()):
                    raise ValueError('invalid saved argument list')
                name = app.get('name')
                if not isinstance(name, str) or not name or len(name) > 160 or not name.isprintable():
                    raise ValueError('invalid display name')
            for key, argv in data['uninstall'].items():
                app_id(key)
                if (not isinstance(argv, list) or not argv or len(argv) > 256 or
                        any(not isinstance(arg, str) or '\0' in arg for arg in argv) or not Path(argv[0]).is_absolute()):
                    raise ValueError('invalid uninstall argument list')
            if any(not isinstance(folder, str) or not Path(folder).is_absolute() or '\0' in folder for folder in data['folders']):
                raise ValueError('invalid search folder')
            for key in data['hidden']:
                app_id(key)
            return data
        except FileNotFoundError:
            return dict(schema=1, apps={}, folders=[], hidden=[], uninstall={})
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise ValueError('Cannot read ' + str(self.file) + ': ' + str(error)) from error

    def _update(self, change):
        if self.file.is_symlink():
            raise ValueError('Refusing to replace a symlinked app registry: ' + str(self.file))
        self.file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = os.open(str(self.file) + '.lock', os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(lock, 'a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            data = self.settings()
            change(data)
            payload = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
            if len(payload.encode('utf-8')) > 1024 * 1024:
                raise ValueError('App registry exceeds 1 MiB; existing settings were retained')
            with tempfile.NamedTemporaryFile(mode='w', dir=self.file.parent, delete=False, encoding='utf-8') as output:
                temporary = Path(output.name)
                output.write(payload)
            try:
                temporary.replace(self.file)
            finally:
                temporary.unlink(missing_ok=True)

    def directories(self):
        folders = self.env.get('PATH', '').split(os.pathsep)
        folders += [str(self.home / name) for name in ('.local/bin', '.cargo/bin', 'go/bin')]
        folders += self.settings()['folders']
        result = []
        for folder in folders:
            # Empty/relative PATH entries must not turn a project directory into app inventory.
            if not folder or not Path(folder).is_absolute():
                continue
            path = Path(folder).expanduser().resolve()
            if path not in result:
                result.append(path)
        return result

    def environment(self):
        return dict(self.env, PATH=os.pathsep.join(str(path) for path in self.directories()))

    def executables(self):
        result = {}
        for folder in self.directories():
            try:
                with os.scandir(folder) as entries:
                    for index, item in enumerate(entries):
                        if index >= 20000:
                            break
                        if APP_ID.fullmatch(item.name) and item.is_file() and os.access(item.path, os.X_OK):
                            result.setdefault(item.name.casefold(), str(folder / item.name))
            except (OSError, ValueError):
                continue
        return result

    def _catalog_names(self):
        names = set()
        # Homebrew's general catalog contains libraries/helpers; it is not a TUI allowlist.
        for source in ('terminal-trove', 'awesome-tuis', 'awesome-cli'):
            try:
                target = self.cache / (source + '.json')
                if target.stat().st_size > 64 * 1024 * 1024:
                    continue
                data = json.loads(target.read_text())
                if data.get('schema') != 1 or data.get('source') != source:
                    continue
                for row in data['entries']:
                    name = row.get('name') if isinstance(row, dict) else None
                    if isinstance(name, str) and APP_ID.fullmatch(name):
                        names.add(name.casefold())
            except (OSError, ValueError, TypeError, KeyError, AttributeError):
                continue
        return names

    def applications(self, include_hidden=False):
        data = self.settings()
        env = self.environment()
        found = self.executables()
        apps = {}
        for tool, name in BUILTINS.items():
            path = shutil.which(tool, path=env['PATH'])
            if path:
                apps[tool] = dict(tool=tool, name=name, argv=[path], builtin=True, available=True,
                                  description='Configured app · ' + path)
        for tool in sorted(self._catalog_names() & found.keys()):
            system_command = self.system == 'darwin' and Path(found[tool]).parent in (
                Path('/usr/bin'), Path('/bin'), Path('/usr/sbin'), Path('/sbin'))
            if tool not in PANEL_TOOLS and tool not in AUTO_EXCLUDE and not system_command:
                apps[tool] = dict(tool=tool, name=tool, argv=[found[tool]], builtin=False, available=True,
                                  description='Discovered from catalog · ' + found[tool])
        for tool, app in data['apps'].items():
            available = executable(app['argv'][0])
            apps[tool] = dict(app, tool=tool, builtin=False, available=available,
                              description=('Saved app · ' if available else 'Unavailable · ') + app['argv'][0])
        return sorted((app for key, app in apps.items() if include_hidden or key not in data['hidden']),
                      key=lambda app: app['name'].casefold())

    def resolve(self, tool):
        key = app_id(tool)
        for app in self.applications(include_hidden=True):
            if app['tool'] == key:
                if not app['available']:
                    raise ValueError(app['name'] + ' is not available at ' + app['argv'][0])
                return app
        raise ValueError('Unknown installed app: ' + key + '. Use command-center apps to add its launcher.')

    def register(self, tool, argv, name=None, replace=False, show=True):
        key = app_id(tool)
        if key in PANEL_TOOLS:
            raise ValueError(key + ' already has a configured launcher')
        command = self._command(argv)
        label = name or tool
        if not isinstance(label, str) or not label or len(label) > 160 or not label.isprintable():
            raise ValueError('Display names must be printable text under 161 characters')
        app = dict(name=label, argv=command)
        def change(data):
            changed = key in data['apps'] and data['apps'][key]['argv'] != app['argv']
            if changed and not replace:
                raise ValueError('A different launcher is already saved as ' + key + '. Choose a different name or use apps add --replace.')
            if changed:
                data['uninstall'].pop(key, None)
            data['apps'][key] = app
            if show:
                data['hidden'] = [item for item in data['hidden'] if item != key]
        self._update(change)
        return key

    def _command(self, argv):
        if not isinstance(argv, list) or not argv or len(argv) > 256 or any(not isinstance(arg, str) or '\0' in arg for arg in argv):
            raise ValueError('Provide an executable and optional arguments')
        command = Path(argv[0]).expanduser()
        path = os.path.abspath(command) if '/' in argv[0] else self.executables().get(argv[0].casefold())
        if not path or not executable(path):
            raise ValueError('Executable not found: ' + argv[0])
        return [path, *argv[1:]]

    def set_uninstall(self, tool, argv):
        key = app_id(tool)
        app = self.resolve(key)
        command = self._command(argv)
        def change(data):
            if not app['builtin']:
                previous = data['apps'].get(key)
                if previous and previous['argv'] != app['argv']:
                    raise ValueError('The app launcher changed; review it before saving an uninstall command')
                data['apps'][key] = dict(name=app['name'], argv=app['argv'])
            data['uninstall'][key] = command
        self._update(change)

    def remove(self, tool):
        key = app_id(tool)
        def change(data):
            if key not in data['hidden']:
                data['hidden'].append(key)
        self._update(change)

    def restore(self, tool):
        key = app_id(tool)
        self._update(lambda data: data.update(hidden=[item for item in data['hidden'] if item != key]))

    def add_folder(self, folder):
        path = Path(folder).expanduser().resolve()
        if not path.is_dir():
            raise ValueError('Search folder does not exist: ' + str(path))
        def change(data):
            if str(path) not in data['folders']:
                data['folders'].append(str(path))
        self._update(change)

    def remove_folder(self, folder):
        path = str(Path(folder).expanduser().resolve())
        self._update(lambda data: data.update(folders=[item for item in data['folders'] if item != path]))

    def _brew(self, arguments):
        env = dict(self.environment(), HOMEBREW_NO_AUTO_UPDATE='1')
        brew = shutil.which('brew', path=env['PATH'])
        if not brew:
            return None
        result = subprocess.run([brew, *arguments], env=env, capture_output=True, text=True, timeout=15)
        return result.stdout.strip() if result.returncode == 0 and isinstance(result.stdout, str) else None

    def formula_commands(self, formula):
        if not FORMULA.fullmatch(formula):
            raise ValueError('Invalid Homebrew formula name')
        prefix = self._brew(['--prefix', formula])
        if not prefix or not Path(prefix).is_absolute():
            return []
        folder = Path(prefix) / 'bin'
        try:
            return sorted(str(path) for path in folder.iterdir() if APP_ID.fullmatch(path.name) and executable(path))
        except OSError:
            return []

    def homebrew_formula(self, app):
        cellar = self._brew(['--cellar'])
        if not cellar or not Path(cellar).is_absolute():
            return None
        try:
            relative = Path(app['argv'][0]).resolve().relative_to(Path(cellar).resolve())
            formula = relative.parts[0]
            if len(relative.parts) >= 3 and FORMULA.fullmatch(formula):
                return formula
        except (ValueError, OSError):
            pass
        return None
