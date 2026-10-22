"""Authored recorder fixture; does not load or emulate game code."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]

class SnowUpdateTraceTests(unittest.TestCase):
    def test_batch_frame(self):
        self.run_fixture("snow_batch_frame")

    def test_entry_attribution(self):
        self.run_fixture("snow_entry_attribution")

    def test_native_capture_lifecycle(self):
        self.run_fixture("snow_update_trace")

    def test_guarded_snapshot_reader(self):
        self.run_fixture("snow_update_snapshot")

    def run_fixture(self, name):
        cc = shutil.which('cc')
        if not cc:
            self.skipTest('C compiler unavailable')
        source = ROOT / 'native/snow_host'
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / 'trace_fixture'
            subprocess.run([cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-pthread', '-I', str(source), str(source/(name+'.c')),
                            str(ROOT/('tests/fixtures/'+name+'_fixture.c')),
                            '-o', str(exe)], check=True, capture_output=True, text=True, timeout=60)
            result = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=10)
            self.assertIn('PASS:', result.stdout)
