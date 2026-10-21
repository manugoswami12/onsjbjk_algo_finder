"""No-install subprocess/CLI checks for the environment-facing entrypoint."""
from __future__ import annotations
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools' / 'run_demo.py'


class RunnerPreflightTests(unittest.TestCase):
    def test_help_does_not_require_tool_install(self):
        result = subprocess.run([sys.executable, str(RUNNER), '--help'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--ast-json', result.stdout)

    def test_missing_source_is_rejected_without_subprocess(self):
        result = subprocess.run([sys.executable, str(RUNNER),
                                 'examples/definitely_not_an_algorithm.py'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn('source not found', result.stderr)

    def test_missing_replay_file_is_rejected(self):
        result = subprocess.run([sys.executable, str(RUNNER),
                                 '--ast-json', 'definitely_no_such_dump.json'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn('saved Semgrep AST not found', result.stderr)
