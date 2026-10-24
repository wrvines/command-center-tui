"""Public discovery indexes and an fzf picker; catalog text is never executable."""
import csv
import html
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from cc import ROOT, paths, sanitize, tool_env
from cc_apps import BUILTINS, PANEL_TOOLS, Registry

SOURCES = {
    'terminal-trove': {
        'name': 'Terminal Trove', 'description': 'Terminal tools; full A–Z index or recent-tools feed',
        'url': 'https://terminaltrove.com/list/'},
    'awesome-tuis': {
        'name': 'Awesome TUIs', 'description': 'Community list of interactive terminal applications',
        'url': 'https://raw.githubusercontent.com/rothgar/awesome-tuis/main/README.md'},
    'awesome-cli': {
        'name': 'Awesome CLI/TUI Apps', 'description': 'Broader CLI/TUI collection with categories',
        'url': 'https://raw.githubusercontent.com/toolleeo/awesome-cli-apps-in-a-csv/master/data/apps.csv'},
    'homebrew': {
        'name': 'Homebrew Formulae', 'description': 'General package catalog, including non-TUI tools and libraries',
        'url': 'https://formulae.brew.sh/api/formula.json'},
}
MAX_BYTES = 64 * 1024 * 1024
TTL = 24 * 60 * 60
FORMULA = re.compile(r'[a-z0-9][a-z0-9+_.@-]{0,199}\Z')


def clean(value, limit=1200):
    # sanitize strips ANSI/OSC sequences and control/format characters; collapsing
    # the remaining whitespace also keeps each menu row on one line.
    return ' '.join(sanitize(html.unescape(str(value or ''))).split())[:limit]


def safe_url(value):
    if not isinstance(value, str) or any(ch.isspace() or unicodedata.category(ch)[0] == 'C' for ch in value):
        return ''
    try:
        parts = urlsplit(value)
        if parts.scheme in ('https', 'http') and parts.hostname and not parts.username and not parts.password:
            return value[:4096]
    except ValueError:
        pass
    return ''


def entry(name, description, category, url, formula=''):
    return dict(name=clean(name, 160), description=clean(description), category=clean(category, 160),
                url=safe_url(url), formula=formula if FORMULA.fullmatch(formula) else '')


class TroveIndex(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.item = None
        self.anchor = False

    def handle_starttag(self, tag, attrs):
        if tag == 'li':
            self.item = {'name': [], 'text': [], 'url': ''}
        elif tag == 'a' and self.item is not None and not self.item['url']:
            href = dict(attrs).get('href', '')
            if re.fullmatch(r'/[a-z0-9][a-z0-9-]*/', href):
                self.item['url'] = urljoin(SOURCES['terminal-trove']['url'], href)
                self.anchor = True

    def handle_data(self, data):
        if self.item is not None:
            self.item['text'].append(data)
            if self.anchor:
                self.item['name'].append(data)

    def handle_endtag(self, tag):
        if tag == 'a':
            self.anchor = False
        if tag == 'li' and self.item is not None:
            name = clean(''.join(self.item['name']))
            text = clean(''.join(self.item['text']))
            description = text[len(name):].lstrip(' -–—') if text.startswith(name) else ''
            if name and description and self.item['url']:
                self.rows.append(entry(name, description, 'Terminal tools', self.item['url']))
            self.item = None


def parse_catalog(source, body):
    rows = []
    if source == 'terminal-trove':
        parser = TroveIndex()
        parser.feed(body)
        rows = parser.rows
    elif source == 'awesome-tuis':
        category = 'TUI'
        for line in body.splitlines():
            heading = re.search(r'<h2>(.*?)</h2>', line) or re.match(r'^##\s+(.+)', line)
            if heading:
                category = clean(heading.group(1))
            match = re.match(r'^\s*[-*]\s+\[([^\]]+)\]\((https?://[^\s)]+)\)\s*(.*)', line)
            if match:
                rows.append(entry(match[1], match[3], category, match[2]))
    elif source == 'awesome-cli':
        reader = csv.DictReader(io.StringIO(body))
        if not {'name', 'category', 'description', 'homepage', 'git'}.issubset(reader.fieldnames or []):
            raise ValueError('CLI/TUI source has an unexpected CSV format')
        for row in reader:
            rows.append(entry(row['name'], row['description'], row['category'],
                              safe_url(row.get('homepage')) or row.get('git', '')))
    elif source == 'homebrew':
        data = json.loads(body)
        if not isinstance(data, list):
            raise ValueError('Homebrew source is not a package list')
        for row in data:
            if not isinstance(row, dict) or not isinstance(row.get('name'), str) or not FORMULA.fullmatch(row['name']):
                continue
            name = row['name']
            status = ' [disabled]' if row.get('disabled') else ' [deprecated]' if row.get('deprecated') else ''
            rows.append(entry(name, str(row.get('desc') or '') + status, 'Homebrew formula',
                              'https://formulae.brew.sh/formula/' + name, name))
    else:
        raise ValueError('Unknown catalog: ' + source)
    return normalize(rows)


def parse_feed(body):
    # Text from the network is data; a document type would redefine the language.
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)', body, re.IGNORECASE):
        raise ValueError('Feed document type declarations are not accepted')
    root = ET.fromstring(body)
    ns = '{http://www.w3.org/2005/Atom}'
    rows = []
    for item in root.findall(ns + 'entry'):
        link = next((node.get('href', '') for node in item.findall(ns + 'link')
                     if node.get('rel', 'alternate') == 'alternate'), '')
        description = item.findtext(ns + 'summary', '')
        description = re.sub(r'<[^>]*>', ' ', html.unescape(description))
        rows.append(entry(item.findtext(ns + 'title', ''), description, 'Recently added', link))
    return normalize(rows)


def normalize(rows):
    result = {}
    for row in rows:
        normalized = entry(row.get('name'), row.get('description'), row.get('category'),
                           row.get('url'), row.get('formula', ''))
        if normalized['name'] and normalized['url']:
            result[(normalized['name'].casefold(), normalized['url'])] = normalized
    if not result:
        raise ValueError('Catalog returned no tools; its format may have changed')
    return sorted(result.values(), key=lambda row: row['name'].casefold())


def fetch_text(url):
    with tempfile.TemporaryDirectory(prefix='cc-catalog-download-') as temp:
        target = Path(temp) / 'index'
        # --disable must be the first argument: ignore any user ~/.curlrc defaults.
        result = subprocess.run(['curl', '--disable', '--fail', '--silent', '--show-error', '--location',
                                 '--proto', '=https', '--proto-redir', '=https',
                                 '--connect-timeout', '8', '--max-time', '45', '--max-filesize', str(MAX_BYTES),
                                 '--output', str(target), url], env=tool_env(), capture_output=True,
                                text=True, timeout=50)
        if result.returncode:
            raise ValueError('Download failed: ' + clean(result.stderr, 300))
        if target.stat().st_size > MAX_BYTES:
            raise ValueError('Catalog exceeded the download size limit')
        return target.read_text(encoding='utf-8-sig')


def load_catalog(source, refresh=False, cache_dir=None, fetch=None):
    if source not in SOURCES:
        raise ValueError('Unknown catalog: ' + source)
    folder = Path(cache_dir) if cache_dir is not None else paths()[2] / 'catalogs'
    target = folder / (source + '.json')
    cached = None
    try:
        with target.open('rb') as handle:
            raw = handle.read(MAX_BYTES + 1)
        if len(raw) <= MAX_BYTES:
            candidate = json.loads(raw)
            if candidate['schema'] == 1 and candidate['source'] == source:
                candidate['entries'] = normalize(candidate['entries'])
                candidate['fetched_at'] = float(candidate['fetched_at'])
                candidate['coverage'] = clean(candidate['coverage'], 160)
                cached = candidate
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        pass
    if cached and not refresh and 0 <= time.time() - cached['fetched_at'] < TTL:
        return dict(cached, stale=False, warning='')
    fetch = fetch or fetch_text
    try:
        coverage = 'full index'
        try:
            rows = parse_catalog(source, fetch(SOURCES[source]['url']))
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            if source != 'terminal-trove' or (cached and cached['coverage'] == 'full index'):
                raise
            rows = parse_feed(fetch('https://terminaltrove.com/new.xml'))
            coverage = 'recent feed (full index unavailable)'
        result = dict(schema=1, source=source, fetched_at=time.time(), coverage=coverage, entries=rows)
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile(mode='w', dir=folder, delete=False, encoding='utf-8') as handle:
            temporary = Path(handle.name)
            json.dump(result, handle, ensure_ascii=False)
        try:
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        return dict(result, stale=False, warning='')
    except (ValueError, OSError, csv.Error, ET.ParseError, subprocess.TimeoutExpired) as error:
        if cached:
            return dict(cached, stale=True, warning=clean(str(error), 300))
        raise ValueError(SOURCES[source]['name'] + ' is unavailable: ' + clean(str(error), 300)) from error


def picker_env():
    env = tool_env()
    # This menu has its own bindings; user fzf startup hooks must not run on fetched text.
    for name in ('FZF_DEFAULT_OPTS', 'FZF_DEFAULT_OPTS_FILE', 'FZF_DEFAULT_COMMAND'):
        env.pop(name, None)
    return env


def choose(rows, prompt, header='', query='', preview=False, refresh=False, name_search=False):
    executable = shutil.which('fzf', path=tool_env()['PATH'])
    if not executable:
        raise ValueError('fzf is required for the menu. Install it with brew install fzf, or use catalogs --source NAME --list.')
    if not rows:
        return None
    with tempfile.TemporaryDirectory(prefix='cc-catalog-picker-') as temp:
        data_file = Path(temp) / 'rows.json'
        data_file.write_text(json.dumps(rows))
        data_file.chmod(0o600)
        command = [executable, '--layout=reverse', '--border=rounded', '--delimiter=\t', '--with-nth=2..', '--print-query',
                   '--prompt=' + prompt + '> ', '--header=' + header,
                   '--query=' + query, '--bind=ctrl-p:toggle-preview']
        if name_search:
            # --nth addresses the displayed fields after --with-nth hides the row index.
            command += ['--exact', '--no-extended', '--ignore-case', '--nth=1']
        if preview:
            preview_command = shlex.join([sys.executable, '-B', str(Path(__file__).resolve()),
                                          '--preview', str(data_file)]) + ' {1}'
            command += ['--preview=' + preview_command, '--preview-window=down:40%:wrap']
        if refresh:
            command += ['--expect=ctrl-r']
        lines = '\n'.join(str(index) + '\t' + clean(row['name'], 160) + '\t' +
                          clean(row.get('description', ''), 500) + '\t' + clean(row.get('category', ''), 160)
                          for index, row in enumerate(rows)) + '\n'
        result = subprocess.run(command, input=lines, capture_output=True, text=True, env=picker_env())
        if result.returncode in (1, 130):
            return None
        if result.returncode:
            raise ValueError('Picker failed: ' + clean(result.stderr, 300))
        output = result.stdout.splitlines()
        current_query = output.pop(0) if output else query
        if refresh:
            key = output.pop(0) if output else ''
            if key == 'ctrl-r':
                return {'refresh': True, '_query': current_query}
        if not output:
            return None
        try:
            index = int(output[0].split('\t', 1)[0])
            if 0 <= index < len(rows):
                return dict(rows[index], _query=current_query)
        except ValueError:
            pass
        raise ValueError('Picker returned an invalid selection')


def preview_file(path, index):
    rows = json.loads(Path(path).read_text())
    row = rows[int(index)]
    for key in ('name', 'category', 'description', 'url'):
        if row.get(key):
            print(clean(row[key], 4096))
    if row.get('formula'):
        print('\nInstall command: brew install --formula ' + clean(row['formula'], 200))


APP_TOOLS = BUILTINS


def configured_app(row):
    name = row['name'].casefold()
    aliases = {'btop++': 'btop', 'hermes agent': 'hermes', 'codex cli': 'codex'}
    tool = aliases.get(name, name)
    try:
        Registry().resolve(tool)
        return tool
    except ValueError:
        pass
    return None


def launch_app(tool, placement):
    registry = Registry()
    app = registry.resolve(tool)
    tool = app['tool']
    if placement == 'current':
        command = ([str(ROOT / 'bin/cc-panel'), tool] + (['--compact'] if tool == 'btop' else [])
                   if app['builtin'] else app['argv'])
        os.execvpe(command[0], command, registry.environment())
    if placement not in ('new', 'floating') or not os.environ.get('ZELLIJ'):
        raise ValueError('Open the command center first to launch a new or floating pane')
    command = [str(ROOT / 'bin/command-center'), 'pane', tool]
    if tool == 'btop':
        command.append('--compact')
    if placement == 'floating':
        command.append('--floating')
    subprocess.run(command, env=registry.environment(), check=True)


def floating_menu_target():
    """Find the focused workspace pane underneath this floating menu."""
    if not os.environ.get('ZELLIJ') or not os.environ.get('ZELLIJ_PANE_ID'):
        return None
    pane_id = os.environ['ZELLIJ_PANE_ID'].removeprefix('terminal_')
    if not pane_id.isdecimal():
        raise ValueError('Cannot identify this menu pane')
    zellij = shutil.which('zellij', path=tool_env()['PATH'])
    if not zellij:
        raise ValueError('Zellij is required to locate the workspace pane')
    result = subprocess.run([zellij, 'action', 'list-panes', '--json', '--all'],
                            env=tool_env(), capture_output=True, text=True, check=True, timeout=5)
    panes = json.loads(result.stdout)
    menu = next((pane for pane in panes if pane['id'] == int(pane_id) and not pane.get('is_plugin')), None)
    if not menu:
        raise ValueError('Cannot identify this menu pane')
    if not menu.get('is_floating'):
        return None
    recorded = menu.get('terminal_command') or ''
    prefix = str(ROOT / 'bin/command-center') + ' apps --inline'
    if not (recorded == prefix or recorded.startswith(prefix + ' ')):
        try:
            command = shlex.split(recorded)
        except ValueError:
            command = []
        if command[:3] != [str(ROOT / 'bin/command-center'), 'apps', '--inline']:
            # An explicitly inline picker in a floating shell already owns its intended pane.
            return None
    targets = [pane for pane in panes if pane.get('tab_id') == menu['tab_id']
               and pane.get('is_focused') and not pane.get('is_floating') and not pane.get('is_plugin')
               and not pane.get('is_suppressed') and not pane.get('exited')]
    if len(targets) != 1:
        raise ValueError('Cannot identify one workspace pane behind this menu; run command-center apps from that pane')
    # A suspended starter has no process cwd yet; the menu inherits its launch directory.
    directory = targets[0].get('pane_cwd') or menu.get('pane_cwd') or str(Path.cwd())
    return targets[0]['id'], directory


def app_actions(tool, origin=False):
    actions = []
    if tool:
        if os.environ.get('ZELLIJ'):
            actions += [dict(name='Open in new tiled pane', action='new'),
                        dict(name='Open floating', action='floating')]
        actions.append(dict(name='Open in current pane' if origin else 'Use menu pane', action='current',
                            description=('Close the menu and use the terminal where you typed command-center apps'
                                         if origin else
                                         'Replace the menu; returns to its parent shell when the app exits')))
    return actions


def open_url(url):
    url = safe_url(url)
    if not url:
        raise ValueError('This entry has no usable project URL')
    program = 'open' if sys.platform == 'darwin' else 'wslview' if shutil.which('wslview') else 'xdg-open'
    subprocess.run([program, url], env=tool_env(), check=True)


def install_formula(formula):
    if not FORMULA.fullmatch(formula):
        raise ValueError('Invalid Homebrew formula name')
    executable = shutil.which('brew', path=tool_env()['PATH'])
    if not executable:
        raise ValueError('Homebrew is not installed; use the formula page for other installation options')
    confirm = choose([dict(name='Back'), dict(name='Install ' + formula, install=True)],
                     'Install package', header='Command: brew install --formula ' + formula)
    if not confirm or not confirm.get('install'):
        return
    env = tool_env()
    env['HOMEBREW_NO_INSTALL_CLEANUP'] = '1'
    subprocess.run([executable, 'install', '--formula', formula], env=env, check=True)
    try:
        register_formula(formula)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('Package installed. Could not add its launcher: ' + clean(str(error), 500))
    input('\nInstallation finished. Press Enter to return to the catalog. ')


def register_formula(formula):
    registry = Registry()
    commands = registry.formula_commands(formula)
    primary = [path for path in commands if Path(path).name.casefold() == formula]
    if len(primary) == 1 or len(commands) == 1:
        path = (primary or commands)[0]
    elif commands:
        rows = [dict(name=Path(path).name, path=path, description=path) for path in commands]
        selected = choose(rows, 'Add package app', header='Choose the command to add to apps · Esc: skip')
        if not selected:
            return
        path = selected['path']
    else:
        print('No executable found in this package’s bin folder. Use Add to apps for a custom launch command.')
        return
    tool = Path(path).name.casefold()
    if tool in PANEL_TOOLS:
        registry.restore(tool)
    else:
        registry.register(tool, [path])
    print('Available in apps: ' + clean(tool))


def add_app_menu(query=''):
    registry = Registry()
    rows = [dict(name='Enter a command or executable path…', manual=True)]
    rows += [dict(name=name, path=path, description=path) for name, path in sorted(registry.executables().items())]
    selected = choose(rows, 'Add app', query=query, name_search=True,
                      header='Choose an installed command · Clear search to enter a custom path · Esc: back')
    if not selected:
        return
    if selected.get('manual'):
        command = input('Launch command (quote paths with spaces): ').strip()
        if not command:
            return
        argv = shlex.split(command)
    else:
        arguments = input('Arguments (optional): ').strip()
        argv = [selected['path'], *shlex.split(arguments)]
    tool = re.sub(r'[^a-z0-9+_.@-]', '-', Path(argv[0]).name.casefold()).strip('-._@+') or 'app'
    if tool in PANEL_TOOLS:
        registry.restore(tool)
    else:
        name = input('Display name [' + clean(tool) + ']: ').strip() or tool
        existing = registry.settings()['apps'].get(tool)
        replace = False
        if existing:
            action = choose([dict(name='Back'), dict(name='Replace saved launcher', replace=True)],
                            'Save app', header='Existing launcher: ' + clean(shlex.join(existing['argv']), 500))
            if not action or not action.get('replace'):
                return
            replace = True
        registry.register(tool, argv, name=name, replace=replace)


def search_folders_menu():
    registry = Registry()
    while True:
        custom = registry.settings()['folders']
        rows = [dict(name='Add search folder…', add=True)]
        rows += [dict(name=str(path), path=str(path), custom=str(path) in custom,
                      description='Saved folder' if str(path) in custom else 'PATH / common install folder')
                 for path in registry.directories()]
        selected = choose(rows, 'Search folders', header='Folders are scanned directly; subfolders are not searched · Esc: back')
        if not selected:
            return
        if selected.get('add'):
            value = input('Folder to search: ').strip()
            if value:
                registry.add_folder(value)
        elif selected.get('custom'):
            action = choose([dict(name='Back'), dict(name='Remove search folder', remove=True)],
                            'Search folder', header=selected['path'])
            if action and action.get('remove'):
                registry.remove_folder(selected['path'])


def restore_apps_menu():
    registry = Registry()
    data = registry.settings()
    rows = [dict(name=data['apps'].get(tool, {}).get('name', BUILTINS.get(tool, tool)), tool=tool)
            for tool in data['hidden']]
    selected = choose(rows, 'Restore app', header='Choose an app to show again · Esc: back')
    if selected:
        registry.restore(selected['tool'])


def uninstall_app(tool):
    registry = Registry()
    app = registry.resolve(tool)
    tool = app['tool']
    command = registry.settings()['uninstall'].get(tool)
    if command:
        confirm = choose([dict(name='Back'), dict(name='Uninstall ' + app['name'], uninstall=True)],
                         'Saved uninstall command', header=clean(shlex.join(command), 500))
        if confirm and confirm.get('uninstall'):
            subprocess.run(command, env=registry.environment(), check=True)
            registry.remove(tool)
            input('\nUninstall command finished. Press Enter to return to apps. ')
        return
    formula = registry.homebrew_formula(app)
    if not formula:
        action = choose([dict(name='Back'), dict(name='Remove from apps (keep installed files)', remove=True)],
                        'Manual installation', header=clean(app['name'], 160) + '\n' + clean(app['argv'][0], 500) +
                        '\nNo Homebrew ownership found. Use the original installer/package manager, or save its uninstall command from the app menu.')
        if action and action.get('remove'):
            registry.remove(tool)
        return
    confirm = choose([dict(name='Back'), dict(name='Uninstall ' + formula, uninstall=True)],
                     'Uninstall package', header='Command: brew uninstall --formula ' + formula +
                     '\nThis removes the package and its commands. Command Center preferences are retained.')
    if not confirm or not confirm.get('uninstall'):
        return
    env = dict(registry.environment(), HOMEBREW_NO_AUTO_UPDATE='1')
    brew = shutil.which('brew', path=env['PATH'])
    if not brew:
        raise ValueError('Homebrew is not available')
    subprocess.run([brew, 'uninstall', '--formula', formula], env=env, check=True)
    registry.remove(tool)
    input('\nPackage uninstalled. Press Enter to return to apps. ')


def selected_entry(row, source, origin=False):
    tool = configured_app(row)
    actions = app_actions(tool, origin=origin)
    if not tool:
        actions.append(dict(name='Add to apps…', action='add'))
    if source == 'homebrew':
        actions.append(dict(name='Install with Homebrew…', action='install'))
    else:
        actions.append(dict(name='Search Homebrew for this name', action='search'))
    actions += [dict(name='Open project / formula page in browser', action='web'), dict(name='Back to results')]
    header = clean(row['name']) + '\n' + clean(row.get('description', ''), 500) + '\n' + row.get('url', '')
    selected = choose(actions, 'Action', header=header)
    if not selected or 'action' not in selected:
        return False
    action = selected['action']
    if action == 'current' and origin:
        return tool
    if action in ('new', 'floating', 'current'):
        launch_app(tool, action)
        return True
    if action == 'install':
        install_formula(row['formula'])
    elif action == 'add':
        add_app_menu(query=row['name'])
    elif action == 'web':
        open_url(row['url'])
    elif action == 'search':
        return browse_source('homebrew', query=row['name'], name_search=True, origin=origin)
    return False


def browse_source(source, query='', refresh=False, name_search=False, origin=False):
    while True:
        try:
            print('Loading ' + SOURCES[source]['name'] + '…', flush=True)
            snapshot = load_catalog(source, refresh=refresh)
        except ValueError as error:
            selected = choose([dict(name='Retry', retry=True),
                               dict(name='Open catalog in browser', web=True), dict(name='Back')],
                              SOURCES[source]['name'], header=clean(error))
            if selected and selected.get('retry'):
                refresh = True
                continue
            if selected and selected.get('web'):
                open_url(catalog_page(source))
            return False
        fetched = time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(snapshot['fetched_at']))
        header = (SOURCES[source]['name'] + ' | ' + snapshot['coverage'] + ' | ' + fetched +
                  (' | STALE CACHE' if snapshot['stale'] else '') +
                  '\nEnter: details/actions · Ctrl+R: refresh · Ctrl+P: preview · Esc: back')
        if snapshot['warning']:
            header += '\n' + snapshot['warning']
        if name_search:
            header += '\nPackage names only · No match? Edit search, or Esc then open the project page for installation.'
        while True:
            selected = choose(snapshot['entries'], 'Package name' if name_search else 'Search',
                              header=header, query=query, preview=True, refresh=True, name_search=name_search)
            if selected is None:
                return False
            query = selected.pop('_query', query)
            if selected.get('refresh'):
                refresh = True
                break
            try:
                result = selected_entry(selected, source, origin=origin)
                if result:
                    return result
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                choose([dict(name='Back to results')], 'Could not complete action', header=clean(error))


def catalog_page(source):
    return {
        'terminal-trove': 'https://terminaltrove.com/list/',
        'awesome-tuis': 'https://github.com/rothgar/awesome-tuis',
        'awesome-cli': 'https://github.com/toolleeo/awesome-cli-apps-in-a-csv',
        'homebrew': 'https://formulae.brew.sh/formula/',
    }[source]


def catalogs_menu(origin=False):
    rows = [dict(meta, source=source) for source, meta in SOURCES.items()]
    while True:
        selected = choose(rows, 'Choose catalog', header='Pick a source, then type to search its tools · Esc: back')
        if not selected:
            return False
        result = browse_source(selected['source'], origin=origin)
        if result:
            return result


def apps_menu(pick=False, origin=False):
    query = ''
    while True:
        registry = Registry()
        rows = registry.applications()
        if pick:
            rows = [row for row in rows if row.get('available')]
            rows += [dict(name='Shell', panel='shell', description='Open an ordinary shell in this pane'),
                     dict(name='Weather', panel='weather', description='Show the configured forecast, then a shell')]
        else:
            rows += [dict(name='Add to apps…', add=True), dict(name='Search folders…', folders=True),
                     dict(name='Restore hidden apps…', restore=True),
                     dict(name='Refresh discovery catalogs…', catalogs_refresh=True),
                     dict(name='Browse catalogs…', catalogs=True,
                          description='Terminal Trove · Awesome TUIs · Awesome CLI/TUI Apps · Homebrew')]
        selected = choose(rows, 'Choose an app' if pick else 'Apps', query=query, refresh=True,
                          header=('Enter: use this pane · Ctrl+R: rescan · Esc: shell' if pick else
                                  'Installed and saved apps · Ctrl+R: rescan · Esc: close'))
        if not selected:
            return
        query = selected.pop('_query', query)
        try:
            if pick and selected.get('panel') in ('shell', 'weather'):
                command = str(ROOT / 'bin/cc-panel')
                os.execve(command, [command, selected['panel']], registry.environment())
            if pick and selected.get('available'):
                launch_app(selected['tool'], 'current')
                return
            if selected.get('refresh'):
                continue
            if selected.get('catalogs'):
                result = catalogs_menu(origin=origin)
                if result:
                    return result if isinstance(result, str) else None
                continue
            if selected.get('add'):
                add_app_menu()
                continue
            if selected.get('folders'):
                search_folders_menu()
                continue
            if selected.get('restore'):
                restore_apps_menu()
                continue
            if selected.get('catalogs_refresh'):
                for source in ('awesome-tuis', 'awesome-cli', 'terminal-trove'):
                    print('Refreshing ' + SOURCES[source]['name'] + '…', flush=True)
                    try:
                        load_catalog(source, refresh=True)
                    except ValueError as error:
                        print(clean(str(error)))
                input('Catalog refresh finished. Press Enter to return to apps. ')
                continue
            actions = app_actions(selected['tool'], origin=origin) if selected.get('available') else []
            actions += [dict(name='Remove from apps (keep installed files)', action='remove')]
            if selected.get('available'):
                actions.append(dict(name='Uninstall…', action='uninstall'))
                actions.append(dict(name='Set uninstall command…', action='set-uninstall'))
            actions.append(dict(name='Back'))
            action = choose(actions, 'App', header=clean(selected['name'], 160) + '\n' +
                            clean(shlex.join(selected['argv']), 500))
            if not action or 'action' not in action:
                continue
            if action['action'] == 'current' and origin:
                return selected['tool']
            elif action['action'] == 'remove':
                registry.remove(selected['tool'])
            elif action['action'] == 'uninstall':
                uninstall_app(selected['tool'])
            elif action['action'] == 'set-uninstall':
                value = input('Uninstall command (quote paths with spaces): ').strip()
                if value:
                    registry.set_uninstall(selected['tool'], shlex.split(value))
            else:
                launch_app(selected['tool'], action['action'])
                return
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            choose([dict(name='Back to apps')], 'Could not complete action', header=clean(str(error)))


def run_catalogs(args):
    if args.list:
        if not args.source:
            for source, meta in SOURCES.items():
                print(source + '\t' + meta['name'] + '\t' + meta['description'])
            return 0
        snapshot = load_catalog(args.source, refresh=args.refresh)
        print(SOURCES[args.source]['name'] + ' | ' + snapshot['coverage'] +
              (' | STALE CACHE: ' + snapshot['warning'] if snapshot['stale'] else ''), file=sys.stderr)
        query = args.query.casefold()
        for row in snapshot['entries']:
            if not query or query in ' '.join(row.values()).casefold():
                print('\t'.join(row[key] for key in ('name', 'description', 'category', 'url')))
        return 0
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('Open the menu in an interactive terminal, or add --list')
    if not shutil.which('fzf', path=tool_env()['PATH']):
        raise ValueError('Install the menu dependency: brew install fzf (or use your Linux package manager)')
    if args.source:
        browse_source(args.source, query=args.query, refresh=args.refresh)
    else:
        catalogs_menu()
    return 0


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--preview':
        preview_file(sys.argv[2], sys.argv[3])
