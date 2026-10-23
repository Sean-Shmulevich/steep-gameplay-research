"""Authored admission fixture; original-instruction evidence has a separate receipt."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]


class AttachedAdmissionTests(unittest.TestCase):
    def test_reference_transfer_refusal_and_consumer_before_return(self):
        cc = shutil.which('cc')
        if not cc:
            self.skipTest('C compiler unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            exe = str(Path(tmp)/'admission')
            subprocess.run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror',
                '-I', str(ROOT/'native/snow_host'),
                str(ROOT/'native/snow_host/snow_command_admission.c'),
                str(ROOT/'native/snow_host/snow_command_attachment.c'),
                str(ROOT/'tests/fixtures/snow_command_attached_admission_fixture.c'),
                '-o', exe], check=True, capture_output=True, text=True, timeout=30)
            subprocess.run([exe], check=True, capture_output=True, timeout=10)
