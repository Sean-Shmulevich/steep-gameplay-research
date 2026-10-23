from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

class FiniteDiagnosticTests(unittest.TestCase):
    def test_finite_guard_diagnostics(self):
        cc=shutil.which('cc')
        if not cc:self.skipTest('C compiler unavailable')
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            exe=Path(d)/'finite_diagnostic'
            subprocess.run([cc,'-std=c11','-Wall','-Wextra','-Werror',
                '-I',str(root/'native/snow_host'),str(root/'tests/fixtures/snow_finite_diagnostic_fixture.c'),
                '-o',str(exe)],check=True,capture_output=True,timeout=60)
            result=subprocess.run([str(exe)],check=True,capture_output=True,text=True,timeout=10)
            self.assertIn('PASS:',result.stdout)
