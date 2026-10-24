"""Behavior checks for ownership, persistence decisions, and network failure handling."""
import json
import os
import pty
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from cc_apps import Registry


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cc-install-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home with spaces"
        self.ghostty = self.home / "Library/Application Support/com.mitchellh.ghostty"
        self.ghostty.mkdir(parents=True)
        self.original = b"theme = GitHub Dark High Contrast\nfont-size = 14\n"
        (self.ghostty / "config.ghostty").write_bytes(self.original)
        (self.ghostty / "config").write_bytes(b"# legacy\n")

    def manage(self, action, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts/manage.py"), action,
                               "--home", str(self.home), "--platform", "darwin", *args], capture_output=True, text=True)

    def test_idempotent_install_and_exact_rollback_preserve_preferences(self):
        self.assertEqual(self.manage("install", "--dry-run").returncode, 0)
        self.assertFalse((self.home / ".local/bin/command-center").exists())
        self.assertEqual(self.manage("install").returncode, 0)
        self.assertEqual(self.manage("install").returncode, 0)
        modern = self.ghostty / "config.ghostty"
        self.assertEqual(modern.read_text().count("# BEGIN command-center"), 1)
        self.assertEqual((self.ghostty / "config").read_bytes(), b"# legacy\n")
        prefs = self.home / ".config/command-center/preferences.json"
        prefs.write_text('{"weather_location":"custom"}\n')
        self.assertEqual(self.manage("uninstall").returncode, 0)
        self.assertEqual(modern.read_bytes(), self.original)
        self.assertFalse((self.home / ".local/bin/command-center").is_symlink())
        self.assertIn("custom", prefs.read_text())
        self.assertEqual(self.manage("uninstall").returncode, 0)

    def test_later_edit_blocks_entire_uninstall(self):
        self.assertEqual(self.manage("install").returncode, 0)
        modern = self.ghostty / "config.ghostty"
        changed = modern.read_bytes() + b"font-size = 18\n"
        modern.write_bytes(changed)
        result = self.manage("uninstall")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("later edit", result.stderr)
        self.assertEqual(modern.read_bytes(), changed)
        self.assertTrue((self.home / ".local/bin/command-center").is_symlink())

    def test_name_collision_does_not_change_ghostty(self):
        binary = self.home / ".local/bin/command-center"
        binary.parent.mkdir(parents=True)
        binary.write_text("user-owned\n")
        self.assertNotEqual(self.manage("install").returncode, 0)
        self.assertEqual((self.ghostty / "config.ghostty").read_bytes(), self.original)
        self.assertEqual(binary.read_text(), "user-owned\n")

    def test_interrupted_install_recovers_without_duplicating_entries(self):
        self.assertEqual(self.manage("install").returncode, 0)
        (self.home / ".local/bin/ccenter").unlink()
        result = self.manage("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("interrupted", result.stdout)
        self.assertTrue((self.home / ".local/bin/ccenter").is_symlink())
        modern = self.ghostty / "config.ghostty"
        self.assertEqual(modern.read_text().count("# BEGIN command-center"), 1)
        self.assertEqual((self.ghostty / "config").read_bytes(), b"# legacy\n")

    def test_install_does_not_treat_later_edits_as_an_interruption(self):
        self.assertEqual(self.manage("install").returncode, 0)
        modern = self.ghostty / "config.ghostty"
        edited = modern.read_bytes() + b"font-size = 18\n"
        modern.write_bytes(edited)
        result = self.manage("install")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Managed files have changed", result.stderr)
        self.assertEqual(modern.read_bytes(), edited)


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cc-weather-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        (self.base / "config").mkdir()
        (self.base / "tools").mkdir()
        self.prefs = self.base / "config/preferences.json"
        self.prefs.write_text('{"weather_location":"84121", "weather_cache_seconds":1800}')
        self.curl = self.base / "tools/curl"
        self.env = dict(os.environ, COMMAND_CENTER_HOME=str(self.base),
                        PATH=str(self.base / "tools") + ":" + os.environ["PATH"])

    def fake_curl(self, body):
        self.curl.write_text("#!/bin/sh\n" + body + "\n")
        self.curl.chmod(0o755)

    def weather(self, *args):
        return subprocess.run([str(ROOT / "bin/cc-weather"), *args], env=self.env,
                              capture_output=True, text=True)

    def test_cache_avoids_request_and_failure_uses_stale_forecast(self):
        self.fake_curl("printf 'Weather report: 84121\\nSunny, 20 C\\n'")
        first = self.weather()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.fake_curl("exit 28")
        cached = self.weather()
        self.assertEqual(cached.returncode, 0)
        self.assertNotIn("STALE", cached.stdout)
        stale = self.weather("--refresh")
        self.assertEqual(stale.returncode, 0)
        self.assertIn("STALE", stale.stdout)
        self.assertIn("Sunny", stale.stdout)

    def test_bad_service_response_is_not_cached(self):
        self.fake_curl("printf '<html>Service temporarily unavailable</html>'")
        result = self.weather()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(list((self.base / "cache/weather").glob("*.txt")))

    def test_empty_location_does_not_fetch(self):
        self.prefs.write_text('{"weather_location":""}')
        self.fake_curl("exit 99")
        result = self.weather()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Set weather_location", result.stdout)

    def test_non_numeric_cache_lifetime_reports_an_error(self):
        self.prefs.write_text('{"weather_location":"84121", "weather_cache_seconds":null}')
        self.fake_curl("exit 99")
        result = self.weather()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("weather_cache_seconds must be a whole number", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_service_escape_sequences_are_not_replayed_to_the_terminal(self):
        self.fake_curl("printf 'Sunny\\033]52;c;cGF5bG9hZA==\\007 20 C\\n'")
        result = self.weather()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Sunny", result.stdout)
        self.assertNotIn("\x1b", result.stdout)
        cached = next((self.base / "cache/weather").glob("*.txt"))
        self.assertNotIn("\x1b", cached.read_text())


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cc-launch-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / 'project with spaces and "quotes"'
        self.project.mkdir()
        (self.base / "tools").mkdir()
        self.log = self.base / "argv.jsonl"
        fake = self.base / "tools/zellij"
        fake.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ['CC_TEST_LOG'], 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
if 'list-sessions' in sys.argv:
    print(os.environ.get('CC_TEST_SESSIONS', ''))
elif 'dump-layout' in sys.argv:
    print('layout { pane; }')
elif 'list-panes' in sys.argv:
    print(os.environ.get('CC_TEST_PANES', '[]'))
elif '--return-selection' in sys.argv and os.environ.get('CC_TEST_ORIGIN'):
    path = sys.argv[sys.argv.index('--return-selection') + 1]
    with open(path, 'x') as f:
        f.write(os.environ['CC_TEST_ORIGIN'])
''')
        fake.chmod(0o755)
        self.env = dict(os.environ, COMMAND_CENTER_HOME=str(self.base / "state"),
                        CC_TEST_LOG=str(self.log),
                        PATH=str(self.base / "tools") + ":" + os.environ["PATH"])
        self.env.pop("ZELLIJ", None)
        self.env.pop("TMUX", None)

    def launch(self, *args):
        master, slave = pty.openpty()
        try:
            result = subprocess.run([str(ROOT / "bin/command-center"), *args], env=self.env,
                                    stdin=slave, stdout=slave, stderr=subprocess.PIPE,
                                    text=True, timeout=10)
        finally:
            os.close(slave)
            os.close(master)
        return result

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_new_session_escapes_project_path_in_layout(self):
        result = self.launch("--session", "fresh", "--project", str(self.project))
        self.assertEqual(result.returncode, 0, result.stderr)
        last = self.calls()[-1]
        self.assertIn("--layout-string", last)
        layout = last[last.index("--layout-string") + 1]
        self.assertIn(json.dumps(str(self.project.resolve())), layout)
        self.assertNotIn("{{", layout)

    def test_existing_session_does_not_receive_new_layout(self):
        self.env["CC_TEST_SESSIONS"] = "existing\n"
        result = self.launch("--session", "existing", "--layout", "dev")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[-1][-2:], ["attach", "existing"])
        self.assertNotIn("--layout-string", self.calls()[-1])

    def test_every_builtin_workspace_starts_with_suspended_app_choices(self):
        import re
        for name, count in (('command-center', 17), ('dev', 4), ('system', 3),
                            ('agents', 4), ('news-weather', 2), ('operations', 4)):
            with self.subTest(layout=name):
                result = self.launch('--session', 'empty-' + name, '--layout', name)
                self.assertEqual(result.returncode, 0, result.stderr)
                command = self.calls()[-1]
                layout = command[command.index('--layout-string') + 1]
                self.assertEqual(layout.count('args "apps"'), count)
                self.assertEqual(layout.count('start_suspended=true'), count)
                self.assertIsNone(re.search(r'^\s*pane(?: size="[^"]+"| focus=true)*$', layout, re.M))

    def test_starter_returns_to_shell_after_picker_exits(self):
        root = self.base / 'fake checkout'
        (root / 'bin').mkdir(parents=True)
        picker = root / 'bin/command-center'
        picker.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\nexit 1\n')
        shell = root / 'bin/cc-shell'
        shell.write_text('#!/bin/sh\nprintf "SHELL_READY\\n"\n')
        for file in (picker, shell):
            file.chmod(0o755)
        result = subprocess.run([str(ROOT / 'bin/cc-panel'), 'apps'],
                                env=dict(self.env, CC_ROOT=str(root)), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['apps', '--pick', 'SHELL_READY'])

    def test_nested_launch_is_rejected(self):
        self.env["ZELLIJ"] = "1"
        result = self.launch()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Already inside", result.stderr)
        self.assertFalse(self.log.exists())

    def test_apps_selection_runs_in_the_invoking_terminal_and_cleans_up(self):
        app = self.base / 'tools/savedtool'
        app.write_text('#!/bin/sh\nexit 7\n')
        app.chmod(0o755)
        Registry(config_dir=self.base / 'state/config', environ=self.env).register('savedtool', [str(app)])
        self.env.update(ZELLIJ='1', CC_TEST_ORIGIN='{"tool":"savedtool"}')
        result = self.launch('apps')
        self.assertEqual(result.returncode, 7, result.stderr)
        calls = self.calls()
        self.assertEqual(len(calls), 1)
        command = calls[0]
        self.assertIn('--blocking', command)
        self.assertIn('--floating', command)
        selection = Path(command[command.index('--return-selection') + 1])
        self.assertFalse(selection.parent.exists())

    def test_floating_inline_menu_opens_current_selection_in_the_workspace_pane(self):
        app = self.base / 'tools/savedtool'
        app.write_text('#!/bin/sh\nexit 7\n')
        app.chmod(0o755)
        Registry(config_dir=self.base / 'state/config', environ=self.env).register('savedtool', [str(app)])
        fzf = self.base / 'tools/fzf'
        fzf.write_text('''#!/usr/bin/env python3
import sys
rows = sys.stdin.read().splitlines()
wanted = 'savedtool' if any(arg.startswith('--prompt=Apps>') for arg in sys.argv) else 'Open in current pane'
selected = next(row for row in rows if row.split('\\t')[1] == wanted)
print('')
if '--expect=ctrl-r' in sys.argv: print('')
print(selected)
''')
        fzf.chmod(0o755)
        panes = [dict(id=17, is_floating=True, is_focused=True, tab_id=1,
                      terminal_command=str(ROOT / 'bin/command-center') + ' apps --inline'),
                 dict(id=3, is_floating=False, is_focused=True, tab_id=1, pane_cwd=str(self.project))]
        self.env.update(ZELLIJ='1', ZELLIJ_PANE_ID='17', CC_TEST_PANES=json.dumps(panes))
        result = self.launch('apps', '--inline')
        self.assertEqual(result.returncode, 0, result.stderr)
        command = self.calls()[-1]
        self.assertIn('new-pane', command)
        self.assertIn('--in-place', command)
        self.assertIn('--close-on-exit', command)
        self.assertNotIn('--close-replaced-pane', command)
        self.assertEqual(command[command.index('--pane-id') + 1], '3')
        self.assertEqual(command[command.index('--cwd') + 1], str(self.project.resolve()))
        self.assertEqual(command[-2:], ['run', 'savedtool'])

    def test_in_place_launch_rejects_a_missing_target_without_creating_a_pane(self):
        self.env.update(ZELLIJ='1', CC_TEST_PANES='[]')
        result = self.launch('pane', 'shell', '--in-place', '99')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('new-pane' in command for command in self.calls()))

    def test_in_place_launch_rejects_malformed_pane_metadata(self):
        self.env['ZELLIJ'] = '1'
        for payload, message in (('not json', 'invalid pane data'),
                                 ('{"id": 3}', 'no longer available')):
            with self.subTest(payload=payload):
                self.env['CC_TEST_PANES'] = payload
                result = self.launch('pane', 'shell', '--in-place', '3')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_newsboat_panel_creates_private_state_directory(self):
        fake = self.base / 'tools/newsboat'
        fake.write_text('#!/bin/sh\nexit 0\n')
        fake.chmod(0o755)
        data = self.base / 'panel data'
        result = subprocess.run([str(ROOT / 'bin/cc-panel'), 'newsboat'],
                                env=dict(self.env, CC_DATA=str(data), CC_CONFIG=str(self.base / 'config')),
                                capture_output=True, text=True,
                                preexec_fn=lambda: os.umask(0o022))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE((data / 'newsboat').stat().st_mode), 0o700)

    def test_canceled_apps_menu_returns_without_launching_an_app(self):
        self.env['ZELLIJ'] = '1'
        result = self.launch('apps')
        self.assertEqual(result.returncode, 0, result.stderr)
        command = self.calls()[-1]
        self.assertIn('--return-selection', command)
        self.assertFalse(Path(command[command.index('--return-selection') + 1]).parent.exists())

    def test_apps_rejects_invalid_returned_selection(self):
        self.env['ZELLIJ'] = '1'
        for payload in ('not json', '{"tool":"amp; touch bad"}'):
            with self.subTest(payload=payload):
                self.env['CC_TEST_ORIGIN'] = payload
                result = self.launch('apps')
                self.assertNotEqual(result.returncode, 0)
                command = self.calls()[-1]
                selection = Path(command[command.index('--return-selection') + 1])
                self.assertFalse(selection.parent.exists())

    def test_theme_selection_uses_separate_config_and_preserves_preferences(self):
        config = self.base / "state/config"
        (config / "zellij").mkdir(parents=True)
        default = config / "zellij/platform.kdl"
        default.write_text("// existing default runtime config\n")
        (config / "btop.conf").write_text("user monitor preferences\n")
        result = self.launch("--theme", "oh-my-pi", "--session", "theme-preview")
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = self.calls()[-1]
        selected = Path(argv[argv.index("--config") + 1])
        self.assertEqual(selected, (config / "zellij/platform-oh-my-pi.kdl").resolve())
        self.assertIn('theme "oh-my-pi"', selected.read_text())
        self.assertIn("frame_unselected", selected.read_text())
        self.assertEqual(default.read_text(), "// existing default runtime config\n")
        self.assertEqual((config / "btop.conf").read_text(), "user monitor preferences\n")
        self.assertEqual(argv[argv.index("--config-dir") + 1], str((config / "zellij").resolve()))

    def test_unknown_theme_is_rejected_before_runtime_changes(self):
        result = self.launch("--theme", "../unknown")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())
        self.assertFalse((self.base / "state").exists())

    def test_run_newsboat_in_current_pane_uses_scoped_feeds_and_forwards_arguments(self):
        fake = self.base / "tools/newsboat"
        fake.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ['CC_TEST_LOG'], 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
sys.exit(7)
''')
        fake.chmod(0o755)
        self.env["ZELLIJ"] = "1"
        result = subprocess.run([str(ROOT / "bin/command-center"), "run", "newsboat", "--", "-e"],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 7)
        calls = self.calls()
        self.assertEqual(len(calls), 1)  # No multiplexer action for a current-pane launch.
        args = calls[0]
        self.assertEqual(args[args.index("-u") + 1], str((self.base / "state/config/feeds").resolve()))
        self.assertEqual(args[args.index("-c") + 1], str((self.base / "state/data/newsboat/cache.db").resolve()))
        self.assertEqual(args[-1], "-e")
        self.assertIn("BBC News", (self.base / "state/config/feeds").read_text())

    def test_optional_apps_run_in_current_pane_and_open_tiled_or_floating_panes(self):
        for tool in ("abtop", "amp"):
            with self.subTest(tool=tool):
                self.log.unlink(missing_ok=True)
                fake = self.base / "tools" / tool
                fake.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ['CC_TEST_LOG'], 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
sys.exit(7)
''')
                fake.chmod(0o755)
                self.env["ZELLIJ"] = "1"
                arguments = ["--version"] if tool == "abtop" else [str(self.project / "file with spaces.txt")]
                result = subprocess.run([str(ROOT / "bin/command-center"), "run", tool, "--", *arguments],
                                        env=self.env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 7, result.stderr)
                self.assertEqual(self.calls(), [arguments])
                for placement in ([], ["--floating"]):
                    with self.subTest(placement=placement):
                        result = self.launch("pane", tool, *placement)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        args = self.calls()[-1]
                        self.assertIn("new-pane", args)
                        self.assertEqual("--floating" in args, bool(placement))
                        self.assertEqual(args[-2:], [str(ROOT / "bin/cc-panel"), tool])

    def test_saved_app_pane_preserves_hidden_state_arguments_and_uninstall_recipe(self):
        fake = self.base / 'tools/savedtool'
        fake.write_text('#!/bin/sh\nexit 7\n')
        fake.chmod(0o755)
        registry = Registry(config_dir=self.base / 'state/config', cache_dir=self.base / 'state/cache', environ=self.env)
        registry.register('savedtool', [str(fake.resolve()), 'file with spaces.txt'])
        registry.set_uninstall('savedtool', [str(fake.resolve()), '--uninstall'])
        registry.remove('savedtool')
        original = registry.settings()
        self.env['ZELLIJ'] = '1'
        result = self.launch('pane', 'savedtool', '--floating')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[-1][-3:], [str(ROOT / 'bin/command-center'), 'run', 'savedtool'])
        self.assertEqual(registry.settings(), original)
        result = subprocess.run([str(ROOT / 'bin/command-center'), 'run', 'savedtool'], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 7, result.stderr)

    def test_builtin_pane_carries_saved_search_folder_to_server_launched_command(self):
        folder = self.base / 'custom apps'
        folder.mkdir()
        fake = folder / 'cc-test-search-app'
        fake.write_text('#!/bin/sh\nprintf "custom amp\\n"\n')
        fake.chmod(0o755)
        registry = Registry(config_dir=self.base / 'state/config', cache_dir=self.base / 'state/cache', environ=self.env)
        registry.add_folder(folder)
        self.env['ZELLIJ'] = '1'
        result = self.launch('pane', 'amp')
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.calls()[-1]
        launch = args[args.index('--') + 1:]
        # A persistent server may have an old PATH; the new-pane argv must carry the current one.
        self.assertTrue(any(item.startswith('PATH=') and str(folder.resolve()) in item for item in launch))
        # Run a lookup through the serialized environment with the server's PATH stripped.
        probe = [*launch[:-2], sys.executable, '-c', "import shutil; print(shutil.which('cc-test-search-app'))"]
        result = subprocess.run(probe, env=dict(os.environ, PATH='/usr/bin:/bin'), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(fake.resolve()))

    def test_compact_pane_keeps_existing_monitor_preferences(self):
        config = self.base / "state/config"
        config.mkdir(parents=True)
        (config / "btop.conf").write_text('shown_boxes = "mem net"\n')
        self.env["ZELLIJ"] = "1"
        result = self.launch("pane", "btop", "--compact", "--direction", "down")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[-1][-2:], ["btop", "--compact"])
        self.assertNotIn("--name", self.calls()[-1])
        self.assertEqual((config / "btop.conf").read_text(), 'shown_boxes = "mem net"\n')
        self.assertTrue((config / "btop-compact.conf").exists())
        result = self.launch("pane", "newsboat", "--compact")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("supported for btop", result.stderr)

    def test_clear_all_titles_backs_up_layout_and_skips_plugins(self):
        self.env["ZELLIJ"] = "1"
        self.env["CC_TEST_PANES"] = json.dumps([
            {"id": 5, "is_plugin": False}, {"id": 9, "is_plugin": False},
            {"id": 5, "is_plugin": True}])
        result = subprocess.run([str(ROOT / "bin/command-center"), "titles", "--all"],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        rename_calls = [args for args in self.calls() if "rename-pane" in args]
        self.assertEqual([args[-1] for args in rename_calls], ["terminal_5", "terminal_9"])
        backups = list((self.base / "state/data/layouts").glob("before-auto-titles-*.kdl"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "layout { pane; }\n")
        self.assertEqual(self.calls()[0][-1], "dump-layout")

    def test_save_layout_never_overwrites_existing_template(self):
        self.env["ZELLIJ"] = "1"
        command = [str(ROOT / "bin/command-center"), "save-layout", "my-layout"]
        first = subprocess.run(command, env=self.env, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        target = self.base / "state/data/layouts/my-layout.kdl"
        content = target.read_bytes()
        second = subprocess.run(command, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(target.read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
