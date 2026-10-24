"""Compile-only check. Wine execution is recorded separately, never implicit."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarkupUpdateProbeBuildTests(unittest.TestCase):
    def test_windows_dll_and_fixture_build(self):
        cc = shutil.which('x86_64-w64-mingw32-gcc')
        if not cc:
            self.skipTest('MinGW x64 compiler unavailable')
        native = ROOT/'native/snow_host'
        with tempfile.TemporaryDirectory() as tmp:
            common = [cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(native)]
            subprocess.run(common+['-shared',str(native/'snow_markup_update_probe.c'),
                str(native/'snow_markup_update_trace.c'),'-o',str(Path(tmp)/'probe.dll')],
                check=True,capture_output=True,timeout=30)
            subprocess.run(common+[str(ROOT/'tests/fixtures/snow_markup_update_probe_fixture.c'),
                '-o',str(Path(tmp)/'fixture.exe')],check=True,capture_output=True,timeout=30)
