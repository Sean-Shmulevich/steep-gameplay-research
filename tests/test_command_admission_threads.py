"""Actual host threads exercise authored admission, not original engine concurrency."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]


class AdmissionThreadTests(unittest.TestCase):
    def test_competing_producers_respect_capacity_and_cleanup_order(self):
        cc=shutil.which('cc')
        if not cc:self.skipTest('C compiler unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'admission_threads'
            built=subprocess.run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-pthread',
                '-I',str(ROOT/'native/snow_host'),str(ROOT/'native/snow_host/snow_command_admission.c'),
                str(ROOT/'tests/fixtures/snow_command_admission_threads_fixture.c'),'-o',str(exe)],
                capture_output=True,text=True,timeout=30)
            self.assertEqual(built.returncode,0,built.stderr)
            result=subprocess.run([str(exe)],check=True,capture_output=True,text=True,timeout=15)
            self.assertEqual(json.loads(result.stdout),dict(passed=True,scenarios=3,producers=4,total_attempts=3072,game_loaded=False))
