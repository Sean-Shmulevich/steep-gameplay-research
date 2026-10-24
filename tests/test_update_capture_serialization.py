import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class UpdateCaptureSerializationTests(unittest.TestCase):
    def test_actual_snapshot_formatter_preserves_frame_bits_and_validity(self):
        cc=shutil.which('cc')
        if not cc:
            self.skipTest('native C compiler unavailable')
        source=(ROOT/'native/snow_host/examples/update_capture.c').read_text()
        # Compile the production snapshot formatting functions without the
        # Windows plugin lifecycle; no duplicated serializer implementation.
        functions=source[source.index('static void number('):source.index('static void motion_sample(')]
        harness='''
#include <stdio.h>
#include <math.h>
#include "snow_update_trace.h"
'''+functions+'''
int main(void) {
    SnowUpdateSnapshot s={0};
    s.basis_attempted=1;s.basis_valid=1;s.basis_read_ticks=123;
    s.basis_inputs.receiver=0x12345;s.basis_inputs.callback=0x140001000;
    s.basis_inputs.cached_basis[2][3]=0x7fc12345;
    s.basis_inputs.forward[3][2]=0x80000000;
    s.basis_inputs.inverse[3][3]=0x3f800000;
    sample(stdout,&s);puts("");
    s.basis_valid=0;sample(stdout,&s);puts("");
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'format.c';path.write_text(harness);exe=Path(tmp)/'format'
            subprocess.run([cc,'-std=c11','-Wall','-Wextra','-Werror',
                '-I',str(ROOT/'native/snow_host'),str(path),'-o',str(exe)],
                check=True,capture_output=True,text=True,timeout=30)
            output=subprocess.check_output([str(exe)],text=True,timeout=10)
        valid,invalid=map(json.loads,output.splitlines())
        self.assertEqual(valid['basis_read_ticks'],123)
        data=valid['basis_inputs']
        self.assertEqual(data['receiver'],'12345')
        self.assertEqual(data['callback'],'140001000')
        self.assertEqual(data['cached_basis_bits'][11],0x7fc12345)
        self.assertEqual(data['forward_bits'][14],0x80000000)
        self.assertEqual(data['inverse_bits'][15],0x3f800000)
        self.assertNotIn('basis_inputs',invalid)
        self.assertEqual(invalid['basis_attempted'],1)
