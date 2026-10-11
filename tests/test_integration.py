"""Behavior checks for ownership, persistence decisions, and network failure handling."""
import json
import os
import pty
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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

    def test_nested_launch_is_rejected(self):
        self.env["ZELLIJ"] = "1"
        result = self.launch()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Already inside", result.stderr)
        self.assertFalse(self.log.exists())

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

    def test_compact_pane_keeps_existing_monitor_preferences(self):
        config = self.base / "state/config"
        config.mkdir(parents=True)
        (config / "btop.conf").write_text('shown_boxes = "mem net"\n')
        self.env["ZELLIJ"] = "1"
        result = self.launch("pane", "btop", "--compact", "--direction", "down")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[-1][-2:], ["btop", "--compact"])
        self.assertEqual((config / "btop.conf").read_text(), 'shown_boxes = "mem net"\n')
        self.assertTrue((config / "btop-compact.conf").exists())
        result = self.launch("pane", "newsboat", "--compact")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("supported for btop", result.stderr)

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
