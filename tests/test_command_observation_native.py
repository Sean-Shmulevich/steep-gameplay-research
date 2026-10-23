"""Authored observer plumbing; no original-game execution claim."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CommandObservationTests(unittest.TestCase):
    def test_copied_descriptor_repeated_delivery_and_close(self):
        cc = shutil.which('cc')
        if not cc:
            self.skipTest('native C compiler unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            exe = str(Path(tmp) / 'command-observation')
            subprocess.run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror',
                '-I', str(ROOT / 'native/snow_host'),
                str(ROOT / 'native/snow_host/snow_delegate_trace.c'),
                str(ROOT / 'native/snow_host/snow_command_observation.c'),
                str(ROOT / 'tests/fixtures/snow_command_observation_fixture.c'),
                '-o', exe], check=True, capture_output=True, text=True, timeout=30)
            subprocess.run([exe], check=True, capture_output=True, timeout=10)
