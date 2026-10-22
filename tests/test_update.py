"""Exercise the public updater against disposable local Git remotes."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class UpdateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="cc-update-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.remote = self.base / "remote.git"
        self.source = self.base / "publisher"
        self.checkout = self.base / "installed checkout with spaces"
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                        GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.invalid",
                        GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.invalid",
                        PYTHONDONTWRITEBYTECODE="1", COMMAND_CENTER_HOME=str(self.base / "private"))
        self.git(self.base, "init", "--bare", str(self.remote))
        self.git(self.base, "clone", str(self.remote), str(self.source))
        self.git(self.source, "checkout", "-b", "main")
        for name in ("bin/command-center", "lib/cc.py", "lib/cc_update.py"):
            target = self.source / name
            target.parent.mkdir(exist_ok=True)
            shutil.copy2(ROOT / name, target)
        (self.source / "notes.txt").write_text("initial notes\n")
        self.commit(self.source, "initial")
        self.git(self.source, "push", "-u", "origin", "main")
        self.git(self.base, "clone", "--branch", "main", str(self.remote), str(self.checkout))
        self.before = self.git(self.checkout, "rev-parse", "HEAD")

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, cwd, message):
        self.git(cwd, "add", ".")
        self.git(cwd, "commit", "-m", message)

    def publish(self):
        (self.source / "release.txt").write_text("new release\n")
        self.commit(self.source, "release")
        self.git(self.source, "push")

    def update(self):
        # Installed symlink, unrelated cwd, and active Zellij are all supported.
        launcher = self.base / "command-center"
        if not launcher.is_symlink():
            launcher.symlink_to(self.checkout / "bin/command-center")
        return subprocess.run([sys.executable, "-B", str(launcher), "update"], cwd=self.base,
                              env=dict(self.env, ZELLIJ="1"), capture_output=True, text=True)

    def assert_unchanged(self):
        self.assertEqual(self.git(self.checkout, "rev-parse", "HEAD"), self.before)

    def test_fast_forward_from_installed_link_preserves_private_settings(self):
        private = self.base / "private"
        private.mkdir()
        prefs = private / "preferences.json"
        prefs.write_text('{"custom": true}\n')
        self.publish()
        result = self.update()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.checkout / "release.txt").read_text(), "new release\n")
        self.assertEqual(prefs.read_text(), '{"custom": true}\n')

    def test_already_current(self):
        result = self.update()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_unchanged()

    def test_local_edits_and_untracked_files_block_pull(self):
        self.publish()
        for name in ("notes.txt", "untracked.txt"):
            with self.subTest(name=name):
                target = self.checkout / name
                original = target.read_bytes() if target.exists() else None
                target.write_text("local work\n")
                result = self.update()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("local changes or untracked files", result.stderr)
                self.assertEqual(target.read_text(), "local work\n")
                self.assert_unchanged()
                (self.base / "command-center").unlink()
                if original is None:
                    target.unlink()
                else:
                    target.write_bytes(original)

    def test_divergence_does_not_merge_or_rebase(self):
        self.publish()
        (self.checkout / "local.txt").write_text("local commit\n")
        self.commit(self.checkout, "local")
        self.before = self.git(self.checkout, "rev-parse", "HEAD")
        result = self.update()
        self.assertNotEqual(result.returncode, 0)
        self.assert_unchanged()
        self.assertFalse((self.checkout / ".git/MERGE_HEAD").exists())

    def test_detached_head_and_missing_upstream(self):
        self.git(self.checkout, "checkout", "--detach")
        result = self.update()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("detached HEAD", result.stderr)
        self.assert_unchanged()
        (self.base / "command-center").unlink()
        self.git(self.checkout, "checkout", "main")
        self.git(self.checkout, "branch", "--unset-upstream")
        result = self.update()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no upstream", result.stderr)
        self.assert_unchanged()

    def test_unreachable_remote_reports_failure(self):
        self.git(self.checkout, "remote", "set-url", "origin", str(self.base / "missing.git"))
        result = self.update()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tool exited with status", result.stderr)
        self.assert_unchanged()

    def test_source_copy_cannot_update_containing_repository(self):
        nested = self.checkout / "copy"
        shutil.copytree(self.checkout / "bin", nested / "bin")
        shutil.copytree(self.checkout / "lib", nested / "lib")
        result = subprocess.run([sys.executable, "-B", str(nested / "bin/command-center"), "update"],
                                env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("original Git checkout", result.stderr)
        self.assert_unchanged()


if __name__ == "__main__":
    unittest.main()
