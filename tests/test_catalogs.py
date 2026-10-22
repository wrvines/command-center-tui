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

    def test_package_install_requires_selection_and_passes_formula_as_one_argument(self):
        with patch.object(catalogs.shutil, 'which', return_value='/tools/brew'):
            with patch.object(catalogs, 'choose', return_value={'name': 'Back'}):
                with patch.object(catalogs.subprocess, 'run') as run:
                    catalogs.install_formula('btop')
                    run.assert_not_called()
            with patch.object(catalogs, 'choose', return_value={'install': True}):
                with patch.object(catalogs.subprocess, 'run') as run, patch('builtins.input', return_value=''):
                    catalogs.install_formula('btop')
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
