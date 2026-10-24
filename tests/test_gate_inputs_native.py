from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeGateInputsTests(unittest.TestCase):
    def test_bounded_gate_state_and_identity(self):
        cc = shutil.which('cc')
        if not cc:
            self.skipTest('native C compiler unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            exe = str(Path(tmp)/'gate-inputs')
            subprocess.run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-pthread',
                '-I', str(ROOT/'native/snow_host'),
                str(ROOT/'native/snow_host/snow_gate_inputs.c'),
                str(ROOT/'tests/fixtures/snow_gate_inputs_fixture.c'), '-o', exe],
                check=True, capture_output=True, text=True, timeout=30)
            subprocess.run([exe], check=True, capture_output=True, timeout=10)
