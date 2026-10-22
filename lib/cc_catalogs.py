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

from cc import ROOT, paths, tool_env

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
    text = html.unescape(str(value or ''))
    # Strip ANSI/OSC sequences before dropping remaining control and format chars.
    text = re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)', '', text)
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    text = ''.join(ch if unicodedata.category(ch)[0] != 'C' else ' ' for ch in text)
    return ' '.join(text.split())[:limit]


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
        result = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
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
        if target.stat().st_size <= MAX_BYTES:
            candidate = json.loads(target.read_text())
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


def choose(rows, prompt, header='', query='', preview=False, refresh=False):
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


APP_TOOLS = {
    'hermes': 'Hermes Agent', 'opencode': 'OpenCode', 'pi': 'Pi', 'codex': 'Codex CLI',
    'btop': 'btop (compact)', 'newsboat': 'Newsboat', 'lazygit': 'Lazygit',
    'yazi': 'Yazi', 'lazydocker': 'Lazydocker',
}


def configured_app(row):
    name = row['name'].casefold()
    aliases = {'btop++': 'btop', 'hermes agent': 'hermes', 'codex cli': 'codex'}
    tool = aliases.get(name, name)
    if tool in APP_TOOLS and shutil.which(tool, path=tool_env()['PATH']):
        return tool
    return None


def launch_app(tool, placement):
    if tool not in APP_TOOLS:
        raise ValueError('Unknown configured application')
    if placement == 'current':
        command = [str(ROOT / 'bin/cc-panel'), tool] + (['--compact'] if tool == 'btop' else [])
        os.execvpe(command[0], command, tool_env())
    if placement not in ('new', 'floating') or not os.environ.get('ZELLIJ'):
        raise ValueError('Open the command center first to launch a new or floating pane')
    command = [str(ROOT / 'bin/command-center'), 'pane', tool]
    if tool == 'btop':
        command.append('--compact')
    if placement == 'floating':
        command.append('--floating')
    subprocess.run(command, env=tool_env(), check=True)


def app_actions(tool):
    actions = []
    if tool:
        if os.environ.get('ZELLIJ'):
            actions += [dict(name='Open in new tiled pane', action='new'),
                        dict(name='Open floating', action='floating')]
        actions.append(dict(name='Use menu pane', action='current',
                            description='Replace the menu; returns to its parent shell when the app exits'))
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
    input('\nInstallation finished. Press Enter to return to the catalog. ')


def selected_entry(row, source):
    tool = configured_app(row)
    actions = app_actions(tool)
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
    if action in ('new', 'floating', 'current'):
        launch_app(tool, action)
        return True
    if action == 'install':
        install_formula(row['formula'])
    elif action == 'web':
        open_url(row['url'])
    elif action == 'search':
        return browse_source('homebrew', query=row['name'])
    return False


def browse_source(source, query='', refresh=False):
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
        while True:
            selected = choose(snapshot['entries'], 'Search', header=header, query=query,
                              preview=True, refresh=True)
            if selected is None:
                return False
            query = selected.pop('_query', query)
            if selected.get('refresh'):
                refresh = True
                break
            try:
                if selected_entry(selected, source):
                    return True
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                choose([dict(name='Back to results')], 'Could not complete action', header=clean(error))


def catalog_page(source):
    return {
        'terminal-trove': 'https://terminaltrove.com/list/',
        'awesome-tuis': 'https://github.com/rothgar/awesome-tuis',
        'awesome-cli': 'https://github.com/toolleeo/awesome-cli-apps-in-a-csv',
        'homebrew': 'https://formulae.brew.sh/formula/',
    }[source]


def catalogs_menu():
    rows = [dict(meta, source=source) for source, meta in SOURCES.items()]
    while True:
        selected = choose(rows, 'Choose catalog', header='Pick a source, then type to search its tools · Esc: back')
        if not selected:
            return
        if browse_source(selected['source']):
            return


def apps_menu():
    rows = [dict(name=name, tool=tool, description=tool + ' · installed on PATH')
            for tool, name in APP_TOOLS.items() if shutil.which(tool, path=tool_env()['PATH'])]
    rows.append(dict(name='Browse catalogs…', catalogs=True,
                     description='Terminal Trove · Awesome TUIs · Awesome CLI/TUI Apps · Homebrew'))
    while True:
        selected = choose(rows, 'Apps', header='Configured installed apps · Esc: close')
        if not selected:
            return
        if selected.get('catalogs'):
            catalogs_menu()
            return
        action = choose(app_actions(selected['tool']), 'Open ' + selected['name'])
        if action:
            launch_app(selected['tool'], action['action'])
            return


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
