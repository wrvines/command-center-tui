"""PTY lifecycle checks for the native smoke-test harness."""
import importlib.util
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("small_screen_smoke", ROOT / "scripts/small-screen-smoke.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class TerminalSmokeTests(unittest.TestCase):
    def test_terminal_close_before_process_exit_still_collects_status(self):
        child = """import os, time, tty
tty.setraw(0)
os.write(1, b'READY\\n')
os.read(0, 1)
for descriptor in (0, 1, 2):
    os.close(descriptor)
time.sleep(0.2)
raise SystemExit(7)
"""
        code, screen = smoke.terminal([sys.executable, '-c', child], os.environ.copy(), 10, 40)
        self.assertEqual(code, 7)
        self.assertIn('READY', screen)
