"""Check scoped shell startup, command-only titles, and existing hook preservation."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TitleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cc-title-startup-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = dict(os.environ, HOME=str(self.home), CC_ROOT=str(ROOT), ZELLIJ="1")
        self.env.pop("ZDOTDIR", None)

    def shell(self, shell, command):
        return subprocess.run([str(ROOT / "bin/cc-shell"), "-i", "-c", command],
                              env=dict(self.env, SHELL=shell), cwd=self.home,
                              capture_output=True, text=True, timeout=10)

    @unittest.skipUnless(shutil.which("zsh"), "zsh is optional on Linux")
    def test_original_zdotdir_and_startup_order_are_preserved(self):
        original = self.home / "original dotdir"
        moved = self.home / "redirected dotdir"
        original.mkdir()
        moved.mkdir()
        (original / ".zshenv").write_text('CC_ORDER=env\nexport ZDOTDIR="$HOME/redirected dotdir"\n')
        for filename, stage in ((".zprofile", "profile"), (".zshrc", "rc"), (".zlogin", "login")):
            (moved / filename).write_text('CC_ORDER+=:' + stage + '\n')
        self.env["ZDOTDIR"] = str(original)
        result = self.shell(shutil.which("zsh"), 'printf "%s\\n" "$CC_ORDER" "$ZDOTDIR"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("env:profile:rc:login", result.stdout)
        self.assertIn(str(moved), result.stdout)

    @unittest.skipUnless(shutil.which("zsh"), "zsh is optional on Linux")
    def test_title_lexing_never_displays_arguments_or_evaluates_them(self):
        command = 'source "$CC_ROOT/config/shell/titles.zsh"; '
        command += "_cc_title_command 'CC_TEST=hidden /usr/bin/sleep $(touch SHOULD_NOT_EXIST) private-argument'; "
        command += "_cc_title_command 'command-center run newsboat --some-private-argument'"
        result = self.shell(shutil.which("zsh"), command)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("\x1b]2;sleep\x07", result.stdout)
        self.assertIn("\x1b]2;newsboat\x07", result.stdout)
        self.assertNotIn("private-argument", result.stdout)
        self.assertFalse((self.home / "SHOULD_NOT_EXIST").exists())

    def test_existing_bash_debug_trap_and_prompt_command_are_preserved(self):
        (self.home / ".bashrc").write_text("trap ': user-debug' DEBUG\nPROMPT_COMMAND=': user-prompt;'\n")
        result = self.shell(shutil.which("bash"), 'trap -p DEBUG; printf "%s\\n" "$PROMPT_COMMAND"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("user-debug", result.stdout)
        self.assertIn("user-prompt", result.stdout)


if __name__ == "__main__":
    unittest.main()
