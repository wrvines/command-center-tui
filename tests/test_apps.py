"""Installed app discovery and persistent launchers, without executing discovered files."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from cc_apps import Registry
import cc_catalogs as catalogs


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cc-apps-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.registry = Registry(config_dir=self.base / 'config', cache_dir=self.base / 'cache',
                                 home=self.base / 'home', environ={'PATH': str(self.bin)})

    def executable(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/sh\nexit 7\n')
        path.chmod(0o755)
        return path

    def catalog(self, names, source='awesome-tuis'):
        folder = self.base / 'cache/catalogs'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (source + '.json')).write_text(json.dumps({
            'schema': 1, 'source': source, 'entries': [{'name': name} for name in names]}))

    def test_recognized_apps_use_path_precedence_and_do_not_execute_commands(self):
        first = self.executable(self.bin / 'mytui')
        self.executable(self.registry.home / '.cargo/bin/mytui')
        self.executable(self.bin / 'compiler')
        self.catalog(['mytui'])
        self.catalog(['compiler'], source='homebrew')
        with patch('subprocess.run', side_effect=AssertionError('Discovery must not execute programs')):
            apps = self.registry.applications()
        self.assertEqual([(app['tool'], app['argv']) for app in apps], [('mytui', [str(first)])])
        self.assertFalse((self.base / 'config/apps.json').exists())

    def test_standard_and_saved_folders_are_scanned_without_recursion(self):
        for folder, name in [('.local/bin', 'localtui'), ('.cargo/bin', 'rusttui'), ('go/bin', 'gotui')]:
            self.executable(self.registry.home / folder / name)
        custom = self.base / 'custom folder'
        self.executable(custom / 'customtui')
        self.executable(custom / 'nested/unwanted')
        self.registry.add_folder(custom)
        self.catalog(['localtui', 'rusttui', 'gotui', 'customtui', 'unwanted'])
        self.assertEqual({app['tool'] for app in self.registry.applications()},
                         {'localtui', 'rusttui', 'gotui', 'customtui'})
        self.registry.remove_folder(custom)
        self.assertNotIn('customtui', {app['tool'] for app in self.registry.applications()})

    def test_registration_persists_literal_arguments_and_missing_executables(self):
        executable = self.executable(self.base / 'outside PATH/my tool')
        self.registry.register('my-tool', [str(executable), 'a file.txt', '$(touch forbidden)'], name='My tool')
        fresh = Registry(config_dir=self.base / 'config', cache_dir=self.base / 'cache',
                         home=self.registry.home, environ={'PATH': str(self.bin)})
        self.assertEqual(fresh.resolve('my-tool')['argv'], [str(executable), 'a file.txt', '$(touch forbidden)'])
        executable.unlink()
        self.assertFalse(fresh.applications()[0]['available'])
        with self.assertRaisesRegex(ValueError, 'not available'):
            fresh.resolve('my-tool')

    def test_hide_survives_rediscovery_and_restore_brings_app_back(self):
        self.executable(self.bin / 'mytui')
        self.catalog(['mytui'])
        self.registry.remove('mytui')
        self.assertEqual(self.registry.applications(), [])
        self.registry.restore('mytui')
        self.assertEqual(self.registry.applications()[0]['tool'], 'mytui')

    def test_hidden_saved_launchers_and_uninstall_commands_survive_pinning_and_restore(self):
        command = self.executable(self.bin / 'mytui')
        uninstall = self.executable(self.bin / 'uninstall-mytui')
        self.registry.register('mytui', [str(command), 'saved argument'])
        self.registry.set_uninstall('mytui', [str(uninstall), '--remove'])
        self.registry.remove('mytui')
        self.registry.register('mytui', [str(command), 'saved argument'], show=False)
        self.assertEqual(self.registry.applications(), [])
        self.assertEqual(self.registry.settings()['uninstall']['mytui'], [str(uninstall), '--remove'])
        self.registry.restore('mytui')
        self.assertEqual(self.registry.resolve('mytui')['argv'], [str(command), 'saved argument'])

    def test_registration_replacement_requires_explicit_choice(self):
        first = self.executable(self.bin / 'first')
        second = self.executable(self.bin / 'second')
        self.registry.register('mytui', [str(first)])
        self.registry.set_uninstall('mytui', [str(first), '--uninstall'])
        with self.assertRaisesRegex(ValueError, 'already saved'):
            self.registry.register('mytui', [str(second)])
        self.assertEqual(self.registry.resolve('mytui')['argv'], [str(first)])
        self.registry.register('mytui', [str(second)], replace=True)
        self.assertEqual(self.registry.resolve('mytui')['argv'], [str(second)])
        self.assertNotIn('mytui', self.registry.settings()['uninstall'])

    def test_saving_uninstall_recipe_pins_a_discovered_executable(self):
        first = self.executable(self.bin / 'mytui')
        self.catalog(['mytui'])
        uninstaller = self.executable(self.bin / 'remove-mytui')
        self.registry.set_uninstall('mytui', [str(uninstaller)])
        self.assertEqual(self.registry.settings()['apps']['mytui']['argv'], [str(first)])
        second = self.executable(self.base / 'other-bin/mytui')
        self.registry.env['PATH'] = str(second.parent) + os.pathsep + str(self.bin)
        self.assertEqual(self.registry.resolve('mytui')['argv'], [str(first)])
        self.registry.register('mytui', [str(second)], replace=True)
        self.assertNotIn('mytui', self.registry.settings()['uninstall'])

    def test_builtin_adapters_win_and_cannot_be_overwritten(self):
        self.executable(self.bin / 'btop')
        self.catalog(['btop'])
        apps = self.registry.applications()
        self.assertEqual(len(apps), 1)
        self.assertTrue(apps[0]['builtin'])
        with self.assertRaises(ValueError):
            self.registry.register('btop', [str(self.bin / 'btop')])

    def test_corrupt_registry_is_not_overwritten(self):
        folder = self.base / 'config'
        folder.mkdir()
        target = folder / 'apps.json'
        target.write_text('{broken')
        with self.assertRaisesRegex(ValueError, 'apps.json'):
            self.registry.add_folder(self.bin)
        self.assertEqual(target.read_text(), '{broken')

    def test_nonexecutables_and_unavailable_or_malformed_catalogs_do_not_break_discovery(self):
        (self.bin / 'textfile').write_text('not executable')
        self.executable(self.bin / 'helper')
        self.catalog(['textfile', '--help', 'helper;touch bad'])
        self.assertEqual(self.registry.applications(), [])
        (self.base / 'cache/catalogs/terminal-trove.json').write_text('{broken')
        self.assertEqual(self.registry.applications(), [])

    def test_discovery_does_not_offer_nested_multiplexers(self):
        for name in ('tmux', 'zellij', 'screen', 'command-center'):
            self.executable(self.bin / name)
        self.catalog(['tmux', 'zellij', 'screen', 'command-center'])
        self.assertEqual(self.registry.applications(), [])

    def test_macos_system_utilities_are_not_mistaken_for_same_named_catalog_apps(self):
        if not Path('/usr/bin/printf').is_file():
            self.skipTest('This host has no /usr/bin/printf fixture')
        self.catalog(['printf'])
        for system in ('darwin', 'linux'):
            registry = Registry(config_dir=self.base / 'config', cache_dir=self.base / 'cache',
                                home=self.registry.home, environ={'PATH': '/usr/bin'}, system=system)
            names = {app['tool'] for app in registry.applications()}
            self.assertEqual('printf' in names, system == 'linux')

    def brew_fixture(self):
        cellar = self.base / 'Cellar'
        prefix = cellar / 'mytui/1.0'
        log = self.base / 'brew-log.jsonl'
        brew = self.bin / 'brew'
        brew.write_text('#!' + sys.executable + '\n' + '''import json, os, sys
from pathlib import Path
with open(os.environ['CC_BREW_LOG'], 'a') as handle:
    handle.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[1] == '--cellar':
    print(os.environ['CC_CELLAR'])
elif sys.argv[1] == '--prefix':
    print(os.environ['CC_PREFIX'])
elif sys.argv[1] == 'uninstall':
    sys.exit(int(os.environ.get('CC_UNINSTALL_STATUS', '0')))
''')
        brew.chmod(0o755)
        self.registry.env.update(CC_CELLAR=str(cellar), CC_PREFIX=str(prefix), CC_BREW_LOG=str(log))
        command = self.executable(prefix / 'bin/mytui')
        return command, log

    def test_homebrew_install_registration_selects_unambiguous_or_chosen_command(self):
        command, log = self.brew_fixture()
        with patch.object(catalogs, 'Registry', return_value=self.registry):
            catalogs.register_formula('mytui')
        self.assertEqual(self.registry.resolve('mytui')['argv'], [str(command)])
        helper = self.executable(command.parent / 'helper')
        with patch.object(catalogs, 'Registry', return_value=self.registry):
            with patch.object(catalogs, 'choose', return_value=None):
                catalogs.register_formula('different-package')
            self.assertNotIn('helper', self.registry.settings()['apps'])
            with patch.object(catalogs, 'choose', return_value={'path': str(helper)}):
                catalogs.register_formula('different-package')
        self.assertEqual(self.registry.resolve('helper')['argv'], [str(helper)])

    def test_homebrew_uninstall_requires_named_selection_and_does_not_force_dependencies(self):
        command, log = self.brew_fixture()
        self.registry.register('mytui', [str(command)])
        with patch.object(catalogs, 'Registry', return_value=self.registry):
            with patch.object(catalogs, 'choose', return_value=None):
                catalogs.uninstall_app('mytui')
            self.assertNotIn(['uninstall', '--formula', 'mytui'], [json.loads(line) for line in log.read_text().splitlines()])
            with patch.object(catalogs, 'choose', return_value={'uninstall': True}) as choose:
                with patch('builtins.input', return_value=''):
                    catalogs.uninstall_app('MyTUI')
        self.assertIn('mytui', choose.call_args.kwargs['header'])
        self.assertEqual(json.loads(log.read_text().splitlines()[-1]), ['uninstall', '--formula', 'mytui'])
        self.assertEqual(self.registry.applications(), [])

    def test_failed_uninstall_keeps_launcher_and_manual_commands_are_literal(self):
        command, log = self.brew_fixture()
        self.registry.register('mytui', [str(command)])
        self.registry.env['CC_UNINSTALL_STATUS'] = '1'
        with patch.object(catalogs, 'Registry', return_value=self.registry):
            with patch.object(catalogs, 'choose', return_value={'uninstall': True}):
                with self.assertRaises(subprocess.CalledProcessError):
                    catalogs.uninstall_app('mytui')
        self.assertTrue(self.registry.applications())
        recipe = self.executable(self.bin / 'manual-uninstaller')
        recipe.write_text('#!' + sys.executable + '\nimport json, sys\n' +
                          'from pathlib import Path\nPath(' + repr(str(self.base / 'manual-args.json')) + ').write_text(json.dumps(sys.argv[1:]))\n')
        arguments = ['--remove', '$(touch forbidden)', 'a file.txt']
        self.registry.set_uninstall('mytui', [str(recipe), *arguments])
        with patch.object(catalogs, 'Registry', return_value=self.registry):
            with patch.object(catalogs, 'choose', return_value={'uninstall': True}):
                with patch('builtins.input', return_value=''):
                    catalogs.uninstall_app('MyTUI')
        self.assertEqual(json.loads((self.base / 'manual-args.json').read_text()), arguments)
        self.assertFalse((self.base / 'forbidden').exists())

    def test_manual_install_without_recipe_only_offers_launcher_removal(self):
        command = self.executable(self.bin / 'mytui')
        self.registry.register('mytui', [str(command)])
        with patch.object(catalogs, 'Registry', return_value=self.registry):
            with patch.object(catalogs, 'choose', return_value={'remove': True}) as choose:
                catalogs.uninstall_app('mytui')
        self.assertEqual(choose.call_args.args[1], 'Manual installation')
        self.assertTrue(command.exists())
        self.assertEqual(self.registry.applications(), [])

    def test_symlinked_registry_is_refused(self):
        self.registry.file.parent.mkdir(parents=True, exist_ok=True)
        elsewhere = self.base / 'elsewhere.json'
        elsewhere.write_text('{"schema": 1}')
        self.registry.file.symlink_to(elsewhere)
        with self.assertRaisesRegex(ValueError, 'symlinked'):
            self.registry.settings()

    def test_menu_headers_never_render_saved_arguments_as_terminal_sequences(self):
        app = self.executable(self.bin / 'mytool')
        self.registry.register('mytool', [str(app), '--flag\x1b]52;c;AAA=\x07'])
        headers = []

        def capture(rows, prompt, header='', **kwargs):
            headers.append(header)
            return rows[0] if len(headers) == 1 else None

        with patch.object(catalogs, 'Registry', return_value=self.registry), \
                patch.object(catalogs, 'choose', side_effect=capture):
            catalogs.apps_menu()
        self.assertEqual(len(headers), 3)
        self.assertIn('--flag', headers[1])
        for header in headers:
            self.assertNotIn('\x1b', header)

    def test_cli_registration_run_and_listing_need_no_fzf_or_live_state(self):
        executable = self.executable(self.base / 'external/my tool')
        env = dict(os.environ, COMMAND_CENTER_HOME=str(self.base / 'state'))
        launcher = str(ROOT / 'bin/command-center')
        added = subprocess.run([launcher, 'apps', 'add', 'my-tool', '--', str(executable), 'some file.txt'],
                               env=env, capture_output=True, text=True)
        self.assertEqual(added.returncode, 0, added.stderr)
        listing = subprocess.run([launcher, 'apps', '--list'], env=env, capture_output=True, text=True)
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn('my-tool', listing.stdout)
        run = subprocess.run([launcher, 'run', 'MY-TOOL'], env=env, capture_output=True, text=True)
        self.assertEqual(run.returncode, 7, run.stderr)


if __name__ == '__main__':
    unittest.main()
