"""Catalog ingestion, last-good caching, and terminal picker boundaries."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import cc_catalogs as catalogs


class CatalogTests(unittest.TestCase):
    def test_floating_menu_finds_only_the_focused_workspace_pane_in_its_tab(self):
        panes = [dict(id=17, is_plugin=True, is_floating=False, tab_id=1),
                 dict(id=3, is_plugin=True, is_focused=True, tab_id=1),
                 dict(id=17, is_floating=True, is_focused=True, tab_id=1,
                      terminal_command=str(ROOT / 'bin/command-center') + ' apps --inline'),
                 dict(id=3, is_floating=False, is_focused=True, tab_id=1, pane_cwd='/tmp/project with spaces'),
                 dict(id=0, is_floating=False, is_focused=True, tab_id=0),
                 dict(id=18, is_floating=True, is_focused=False, tab_id=1)]
        result = subprocess.CompletedProcess([], 0, json.dumps(panes), '')
        with patch.dict(os.environ, ZELLIJ='1', ZELLIJ_PANE_ID='17'), \
                patch.object(catalogs.shutil, 'which', return_value='/tools/zellij'), \
                patch.object(catalogs.subprocess, 'run', return_value=result):
            self.assertEqual(catalogs.floating_menu_target(), (3, '/tmp/project with spaces'))

    def test_floating_menu_refuses_missing_or_ambiguous_workspace_target(self):
        menu = dict(id=17, is_floating=True, is_focused=True, tab_id=1,
                    terminal_command=str(ROOT / 'bin/command-center') + ' apps --inline')
        target = dict(id=3, is_floating=False, is_focused=True, tab_id=1, pane_cwd='/tmp')
        for panes in ([menu], [menu, target, dict(target, id=4)],
                      [menu, dict(target, is_suppressed=True)], [menu, dict(target, exited=True)]):
            with self.subTest(panes=panes), \
                    patch.dict(os.environ, ZELLIJ='1', ZELLIJ_PANE_ID='17'), \
                    patch.object(catalogs.shutil, 'which', return_value='/tools/zellij'), \
                    patch.object(catalogs.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(panes), '')):
                with self.assertRaisesRegex(ValueError, 'workspace pane'):
                    catalogs.floating_menu_target()

    def test_explicit_inline_picker_in_a_floating_shell_keeps_its_own_pane(self):
        panes = [dict(id=17, is_floating=True, is_focused=True, tab_id=1, terminal_command='/bin/zsh -l')]
        with patch.dict(os.environ, ZELLIJ='1', ZELLIJ_PANE_ID='17'), \
                patch.object(catalogs.shutil, 'which', return_value='/tools/zellij'), \
                patch.object(catalogs.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(panes), '')):
            self.assertIsNone(catalogs.floating_menu_target())

    def test_suspended_workspace_pane_uses_the_menu_launch_directory(self):
        panes = [dict(id=17, is_floating=True, tab_id=1, pane_cwd='/tmp/project with spaces',
                      terminal_command=str(ROOT / 'bin/command-center') + ' apps --inline'),
                 dict(id=3, is_floating=False, is_focused=True, is_held=True, tab_id=1, pane_cwd=None)]
        with patch.dict(os.environ, ZELLIJ='1', ZELLIJ_PANE_ID='17'), \
                patch.object(catalogs.shutil, 'which', return_value='/tools/zellij'), \
                patch.object(catalogs.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(panes), '')):
            self.assertEqual(catalogs.floating_menu_target(), (3, '/tmp/project with spaces'))

    def test_original_pane_choice_returns_only_the_app_identifier(self):
        app = dict(tool='amp', name='Amp', available=True, argv=['/tools/amp'])
        with patch.object(catalogs.Registry, 'applications', return_value=[app]), \
                patch.object(catalogs, 'choose', side_effect=[app.copy(), {'action': 'current'}]) as choose, \
                patch.object(catalogs, 'launch_app') as launch:
            self.assertEqual(catalogs.apps_menu(origin=True), 'amp')
        actions = choose.call_args_list[1].args[0]
        self.assertIn({'name': 'Open in current pane', 'action': 'current',
                       'description': 'Close the menu and use the terminal where you typed command-center apps'}, actions)
        self.assertNotIn('Use menu pane', [row['name'] for row in actions])
        self.assertEqual(actions[0]['action'], 'new' if os.environ.get('ZELLIJ') else 'current')
        launch.assert_not_called()

    def test_shortcut_menu_has_no_original_pane_option(self):
        app = dict(tool='amp', name='Amp', available=True, argv=['/tools/amp'])
        with patch.object(catalogs.Registry, 'applications', return_value=[app]), \
                patch.object(catalogs, 'choose', side_effect=[app.copy(), None, None]) as choose:
            catalogs.apps_menu()
        self.assertNotIn('origin', [row.get('action') for row in choose.call_args_list[1].args[0]])

    def test_catalog_current_pane_returns_to_the_invoking_terminal(self):
        snapshot = dict(entries=[{'name': 'Amp', 'url': 'https://example.com', 'description': 'Editor'}],
                        fetched_at=1, coverage='full index', warning='', stale=False)
        choices = [{'catalogs': True}, {'source': 'awesome-tuis'}, snapshot['entries'][0].copy(),
                   {'action': 'current'}]
        with patch.object(catalogs.Registry, 'applications', return_value=[]), \
                patch.object(catalogs, 'configured_app', return_value='amp'), \
                patch.object(catalogs, 'load_catalog', return_value=snapshot), \
                patch.object(catalogs, 'choose', side_effect=choices) as choose, \
                patch.object(catalogs, 'launch_app') as launch:
            self.assertEqual(catalogs.apps_menu(origin=True), 'amp')
        actions = choose.call_args.args[0]
        self.assertIn('Open in current pane', [row['name'] for row in actions])
        launch.assert_not_called()

    def test_homebrew_search_retains_original_terminal_target(self):
        row = dict(name='abtop', description='Monitor', url='https://example.com')
        with patch.object(catalogs, 'configured_app', return_value=None), \
                patch.object(catalogs, 'choose', return_value={'action': 'search'}), \
                patch.object(catalogs, 'browse_source', return_value='abtop') as browse:
            self.assertEqual(catalogs.selected_entry(row, 'awesome-tuis', origin=True), 'abtop')
        browse.assert_called_once_with('homebrew', query='abtop', name_search=True, origin=True)

    def test_starter_picker_launches_in_place_without_app_actions(self):
        app = dict(tool='amp', name='Amp', available=True, argv=['/tools/amp'])
        with patch.object(catalogs.Registry, 'applications', return_value=[app]), \
                patch.object(catalogs, 'choose', return_value=app.copy()) as choose, \
                patch.object(catalogs, 'launch_app') as launch:
            catalogs.apps_menu(pick=True)
        launch.assert_called_once_with('amp', 'current')
        self.assertEqual(choose.call_count, 1)
        self.assertIn('Esc: shell', choose.call_args.kwargs['header'])

    def test_starter_picker_offers_shell_and_weather_and_can_cancel(self):
        missing = dict(tool='missing', name='Missing app', available=False, argv=['/missing'])
        with patch.object(catalogs.Registry, 'applications', return_value=[missing]), \
                patch.object(catalogs, 'choose', return_value=None) as choose, \
                patch.object(catalogs, 'launch_app') as launch:
            catalogs.apps_menu(pick=True)
        rows = choose.call_args.args[0]
        self.assertEqual([row['panel'] for row in rows if 'panel' in row], ['shell', 'weather'])
        self.assertEqual(len(rows), 2)
        launch.assert_not_called()

    def test_starter_shell_and_weather_use_the_configured_helper(self):
        for panel in ('shell', 'weather'):
            with self.subTest(panel=panel), \
                    patch.object(catalogs.Registry, 'applications', return_value=[]), \
                    patch.object(catalogs, 'choose', return_value={'panel': panel}), \
                    patch.object(catalogs.os, 'execve', side_effect=SystemExit) as execute:
                with self.assertRaises(SystemExit):
                    catalogs.apps_menu(pick=True)
                self.assertEqual(execute.call_args.args[:2],
                                 (str(ROOT / 'bin/cc-panel'), [str(ROOT / 'bin/cc-panel'), panel]))

    def test_optional_installed_apps_are_listed_and_recognized_in_catalogs(self):
        for tool in ('abtop', 'amp'):
            for installed in (True, False):
                with self.subTest(tool=tool, installed=installed):
                    with tempfile.TemporaryDirectory() as temp:
                        folder = Path(temp)
                        if installed:
                            command = folder / tool
                            command.write_text('#!/bin/sh\nexit 0\n')
                            command.chmod(0o755)
                        registry = catalogs.Registry(config_dir=folder / 'config', cache_dir=folder / 'cache',
                                                     home=folder / 'home', environ={'PATH': str(folder)})
                        with patch.object(catalogs, 'Registry', return_value=registry):
                            with patch.object(catalogs, 'choose', return_value=None) as choose:
                                catalogs.apps_menu()
                            rows = choose.call_args.args[0]
                            self.assertEqual([row['tool'] for row in rows if 'tool' in row],
                                             [tool] if installed else [])
                            self.assertEqual(catalogs.configured_app({'name': tool}), tool if installed else None)

    def test_independent_sources_keep_names_categories_and_links(self):
        fixtures = {
            "terminal-trove": '<nav><li><a href="/about/">About</a></li></nav>'
                              '<ol><li><a href="/btop/">btop</a> - Resource &amp; CPU monitor</li></ol>',
            "awesome-tuis": '<summary><h2>Dashboards</h2></summary>\n'
                            '- [btop](https://github.com/aristocratos/btop) Resource monitor\n'
                            '- [Contents](#dashboards)\n',
            "awesome-cli": 'category,name,homepage,git,description\n'
                           'monitoring,btop,,https://github.com/aristocratos/btop,"CPU, memory"\n',
            "homebrew": json.dumps([{"name": "btop", "desc": "Resource monitor",
                                      "homepage": "https://github.com/aristocratos/btop"}]),
        }
        for source, body in fixtures.items():
            with self.subTest(source=source):
                entries = catalogs.parse_catalog(source, body)
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]["name"], "btop")
                self.assertTrue(entries[0]["url"].startswith("https://"))
                self.assertTrue(entries[0]["description"])
        self.assertEqual(catalogs.parse_catalog("homebrew", fixtures["homebrew"])[0]["formula"], "btop")

    def test_trove_published_feed_is_explicitly_recent_not_full(self):
        feed = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>btop</title>'
        feed += '<link href="https://terminaltrove.com/btop/"/><summary>Resource monitor</summary></entry></feed>'
        with tempfile.TemporaryDirectory() as temp:
            def fetch(url):
                if url.endswith('/list/'):
                    raise ValueError('HTTP 403')
                return feed
            result = catalogs.load_catalog('terminal-trove', cache_dir=Path(temp), fetch=fetch)
            self.assertEqual(result['coverage'], 'recent feed (full index unavailable)')
            self.assertEqual(result['entries'][0]['name'], 'btop')

    def test_remote_control_sequences_urls_and_formula_options_are_not_trusted(self):
        body = json.dumps([
            {"name": "--help", "desc": "bad", "homepage": "https://example.com"},
            {"name": "btop", "desc": "CPU\u001b]52;c;payload\u0007\nmonitor",
             "homepage": "https://example.com"},
            {"name": "other", "desc": "bad link", "homepage": "javascript:alert(1)"},
        ])
        entries = catalogs.parse_catalog("homebrew", body)
        self.assertEqual([row['name'] for row in entries], ['btop', 'other'])
        self.assertNotIn('\x1b', entries[0]['description'])
        self.assertNotIn('\n', entries[0]['description'])
        self.assertEqual(entries[1]['url'], 'https://formulae.brew.sh/formula/other')
        with self.assertRaises(ValueError):
            catalogs.parse_catalog('awesome-tuis', '- [bad](javascript:alert) bad')

    def test_empty_or_broken_refresh_preserves_last_good_cache(self):
        body = 'category,name,homepage,git,description\nmonitoring,btop,https://example.com,,CPU\n'
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            original = catalogs.load_catalog('awesome-cli', cache_dir=folder, fetch=lambda url: body)
            cached = (folder / 'awesome-cli.json').read_bytes()
            oversized_csv = 'category,name,homepage,git,description\nmonitoring,btop,https://example.com,,' + 'x' * 131073
            for invalid in ('', '<html>error</html>', oversized_csv):
                with self.subTest(invalid=invalid):
                    result = catalogs.load_catalog('awesome-cli', refresh=True, cache_dir=folder,
                                                   fetch=lambda url: invalid)
                    self.assertTrue(result['stale'])
                    self.assertEqual(result['entries'], original['entries'])
                    self.assertEqual((folder / 'awesome-cli.json').read_bytes(), cached)
            with patch.object(catalogs, 'fetch_text', side_effect=AssertionError('Should use cache')):
                result = catalogs.load_catalog('awesome-cli', cache_dir=folder)
            self.assertEqual(result['entries'], original['entries'])

    def test_picker_ignores_user_fzf_execution_hooks_and_selects_only_an_index(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / 'fzf'
            executable.write_text('#!/usr/bin/env python3\nimport os, sys\n'
                                  'assert "FZF_DEFAULT_OPTS" not in os.environ\n'
                                  'assert "FZF_DEFAULT_OPTS_FILE" not in os.environ\n'
                                  'assert "FZF_DEFAULT_COMMAND" not in os.environ\n'
                                  'lines=sys.stdin.read().splitlines()\nprint("my btop")\nprint(lines[1])\n')
            executable.chmod(0o755)
            with patch.dict(os.environ, {'PATH': temp + os.pathsep + os.environ['PATH'],
                                        'FZF_DEFAULT_OPTS': '--bind=start:execute(touch bad)',
                                        'FZF_DEFAULT_OPTS_FILE': '/untrusted',
                                        'FZF_DEFAULT_COMMAND': 'touch bad'}):
                result = catalogs.choose([{'name': 'first'}, {'name': 'second'}], 'Pick')
            self.assertEqual(result['name'], 'second')
            self.assertEqual(result['_query'], 'my btop')

    def test_search_survives_details_back_and_catalog_refresh(self):
        row = catalogs.entry('btop', 'CPU monitor', 'monitoring', 'https://example.com')
        snapshot = dict(entries=[row], fetched_at=1, coverage='full index', stale=False, warning='')
        selections = [dict(row, _query='my search'), {'refresh': True, '_query': 'my search'}, None]
        with patch.object(catalogs, 'load_catalog', return_value=snapshot) as load:
            with patch.object(catalogs, 'choose', side_effect=selections) as choose:
                with patch.object(catalogs, 'selected_entry', return_value=False):
                    catalogs.browse_source('awesome-tuis')
        self.assertEqual([call.kwargs['query'] for call in choose.call_args_list], ['', 'my search', 'my search'])
        self.assertEqual([call.kwargs['refresh'] for call in load.call_args_list], [False, True])

    def test_homebrew_name_search_does_not_match_descriptions_or_scattered_letters(self):
        executable = catalogs.shutil.which('fzf', path=catalogs.tool_env()['PATH'])
        if not executable:
            self.skipTest('fzf is required for the real search regression')
        rows = [
            {'name': 'clinfo', 'description': 'Print information about OpenCL platforms and devices'},
            {'name': 'a-big-top', 'description': 'Unrelated package'},
            {'name': 'other', 'description': 'abtop integration'},
            {'name': 'abtop-tools', 'description': 'Matching package name'},
        ]
        run = subprocess.run

        def filter_picker(command, **kwargs):
            # Exercise the real picker arguments without requiring an interactive terminal.
            query = next(arg.removeprefix('--query=') for arg in command if arg.startswith('--query='))
            return run(command + ['--filter=' + query], **kwargs)

        with patch.object(catalogs.subprocess, 'run', side_effect=filter_picker):
            selected = catalogs.choose(rows, 'Package name', query='ABTOP', name_search=True)
            self.assertEqual(selected['name'], 'abtop-tools')
            self.assertIsNone(catalogs.choose(rows[:-1], 'Package name', query='abtop', name_search=True))

    def test_catalog_handoff_uses_package_name_search(self):
        row = catalogs.entry('abtop', 'Agent monitor', 'monitoring', 'https://example.com')
        with patch.object(catalogs, 'choose', return_value={'action': 'search'}):
            with patch.object(catalogs, 'browse_source', return_value=False) as browse:
                catalogs.selected_entry(row, 'terminal-trove')
        browse.assert_called_once_with('homebrew', query='abtop', name_search=True, origin=False)

    def test_homebrew_name_search_keeps_mode_and_guidance_after_refresh(self):
        snapshot = dict(entries=[{'name': 'btop'}], fetched_at=1, coverage='full index', stale=False, warning='')
        with patch.object(catalogs, 'load_catalog', return_value=snapshot):
            with patch.object(catalogs, 'choose', side_effect=[{'refresh': True, '_query': 'abtop'}, None]) as choose:
                catalogs.browse_source('homebrew', query='abtop', name_search=True)
        for call in choose.call_args_list:
            self.assertTrue(call.kwargs['name_search'])
            self.assertEqual(call.kwargs['query'], 'abtop')
            self.assertIn('No match?', call.kwargs['header'])

    def test_package_install_requires_selection_and_passes_formula_as_one_argument(self):
        with patch.object(catalogs.shutil, 'which', return_value='/tools/brew'):
            with patch.object(catalogs, 'choose', return_value={'name': 'Back'}):
                with patch.object(catalogs.subprocess, 'run') as run:
                    catalogs.install_formula('btop')
                    run.assert_not_called()
            with patch.object(catalogs, 'choose', return_value={'install': True}):
                with patch.object(catalogs.subprocess, 'run') as run, patch('builtins.input', return_value=''):
                    with patch.object(catalogs, 'register_formula') as register:
                        catalogs.install_formula('btop')
                    register.assert_called_once_with('btop')
                    self.assertEqual(run.call_args.args[0], ['/tools/brew', 'install', '--formula', 'btop'])
                    self.assertNotIn('shell', run.call_args.kwargs)
            with self.assertRaises(ValueError):
                catalogs.install_formula('--help')

    def test_headless_listing_works_without_a_terminal_or_fzf(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'cache/catalogs'
            catalogs.load_catalog('awesome-cli', cache_dir=folder,
                                  fetch=lambda url: 'category,name,homepage,git,description\n'
                                                    'monitoring,btop,https://example.com,,CPU\n')
            env = dict(os.environ, COMMAND_CENTER_HOME=temp)
            result = subprocess.run([str(ROOT / 'bin/command-center'), 'catalogs', '--source',
                                     'awesome-cli', '--query', 'btop', '--list'],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('btop', result.stdout)
            self.assertNotIn('fzf is required', result.stderr)


if __name__ == '__main__':
    unittest.main()
