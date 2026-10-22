import math
import struct
import unittest
from engine.replay_inspect import inspect_stage


def fixture(width=282):
    rows=[]
    for i in range(2):
        row=bytearray(width)
        row[23+86]=127
        struct.pack_into('<3I2H',row,7,1,2,3,65535,12345+i)
        rows.append(row)
    block=struct.pack('<I',width)+b''.join(bytes([2,rows[0][c],rows[1][c]]) for c in range(width))
    return struct.pack('<4I',94,55,2,len(block))+block


class ReplayInspectTests(unittest.TestCase):
    def decode(self,p,**kw):
        return inspect_stage(p,supplied_version=94,rsqrt_seed=lambda s:1/math.sqrt(s),**kw)
    def test_complete_compressed_path(self):
        p=fixture(285)
        r=self.decode(p+b'tail')
        self.assertEqual(r['consumed'],len(p))
        self.assertEqual(r['record_count'],2)
        self.assertEqual(r['records'][0]['metadata']['raw_words'],[1,2,3])
        self.assertAlmostEqual(r['records'][1]['metadata']['scalars'][1],123.46,places=4)
        self.assertEqual(r['records'][1]['uninterpreted_tail_bytes'],3)
        self.assertEqual(r['records'][0]['state']['spatial']['extra_rotation'],[0,0,0,1])
    def test_declared_boundary_and_limits(self):
        p=fixture()
        with self.assertRaises(ValueError):self.decode(p[:-1])
        with self.assertRaises(ValueError):self.decode(p,max_records=1)
        with self.assertRaises(ValueError):self.decode(p,max_output=1)
        with self.assertRaises(ValueError):self.decode(struct.pack('<I',93)+p[4:])
        with self.assertRaises(ValueError):
            inspect_stage(p,supplied_version=44,rsqrt_seed=lambda s:1)
