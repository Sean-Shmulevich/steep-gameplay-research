from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeAnimationQueueTests(unittest.TestCase):
    def test_bounded_reader_and_mutation_refusal(self):
        cc = shutil.which('cc')
        if not cc:
            self.skipTest('native C compiler unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            exe = str(Path(tmp)/'animation-queue')
            subprocess.run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror',
                '-I', str(ROOT/'native/snow_host'),
                str(ROOT/'native/snow_host/snow_animation_queue.c'),
                str(ROOT/'tests/fixtures/snow_animation_queue_fixture.c'), '-o', exe],
                check=True, capture_output=True, text=True, timeout=30)
            subprocess.run([exe], check=True, capture_output=True, timeout=10)
