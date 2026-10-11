"""Platform paths, ownership, and dependency planning without OS/package mutations."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import cc

spec = importlib.util.spec_from_file_location("setup_command_center", ROOT / "scripts/setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class PortabilityTests(unittest.TestCase):
    def test_linux_xdg_paths_and_relative_fallback(self):
        home = Path("/home/test")
        env = {"XDG_CONFIG_HOME": "/settings", "XDG_DATA_HOME": "/state", "XDG_CACHE_HOME": "relative"}
        self.assertEqual(cc.platform_paths(home, "linux", env),
                         (Path("/settings/command-center"), Path("/state/command-center"), home / ".cache/command-center"))

    def test_linux_config_has_no_macos_programs(self):
        with patch("cc.shutil.which", return_value=None):
            text = cc.zellij_config_content("linux")
        self.assertNotIn("pbcopy", text)
        self.assertNotIn("/bin/zsh", text)
        self.assertIn('default_mode "locked"', text)

    def test_missing_homebrew_explains_manual_dependency_option(self):
        with patch.object(setup.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "--no-dependencies"):
                setup.dependency_plan({"PATH": "/empty"})

    def test_dependency_plan_only_installs_missing_tools(self):
        def which(name, **kwargs):
            return None if name in ("btop", "newsboat") else "/tools/" + name
        with patch.object(setup.shutil, "which", side_effect=which):
            self.assertEqual(setup.dependency_plan({"PATH": "/tools"}),
                             [["/tools/brew", "install", "btop", "newsboat"]])

    def linux_install(self, home, action, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts/manage.py"), action,
                               "--home", str(home), "--platform", "linux", *args], capture_output=True, text=True)

    def test_linux_legacy_config_rollback_and_private_state(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            ghostty = home / ".config/ghostty/config"
            ghostty.parent.mkdir(parents=True)
            original = b"theme = custom\n"
            ghostty.write_bytes(original)
            first = self.linux_install(home, "install")
            self.assertEqual(first.returncode, 0, first.stderr)
            manifest = home / ".local/share/command-center/install-manifest.json"
            self.assertEqual(len(json.loads(manifest.read_text())["entries"]), 3)
            self.assertIn('browser "xdg-open %u"', (home / ".config/command-center/newsboat.conf").read_text())
            self.assertEqual(self.linux_install(home, "install").returncode, 0)
            self.assertEqual(self.linux_install(home, "uninstall").returncode, 0)
            self.assertEqual(ghostty.read_bytes(), original)
            self.assertFalse((home / ".local/bin/command-center").is_symlink())
            self.assertTrue((home / ".config/command-center/feeds").exists())

    def test_wsl_no_ghostty_skips_symlinked_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            ghostty = home / ".config/ghostty/config"
            ghostty.parent.mkdir(parents=True)
            ghostty.symlink_to(home / "unrelated-missing-config")
            result = self.linux_install(home, "install", "--no-ghostty")
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = home / ".local/share/command-center/install-manifest.json"
            self.assertEqual(len(json.loads(manifest.read_text())["entries"]), 2)
            self.assertEqual(self.linux_install(home, "uninstall").returncode, 0)
            self.assertTrue(ghostty.is_symlink())

    def test_linux_new_config_removed_by_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            self.assertEqual(self.linux_install(home, "install").returncode, 0)
            ghostty = home / ".config/ghostty/config"
            self.assertTrue(ghostty.exists())
            self.assertEqual(self.linux_install(home, "uninstall").returncode, 0)
            self.assertFalse(ghostty.exists())


if __name__ == "__main__":
    unittest.main()
