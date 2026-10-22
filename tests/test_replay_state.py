import math
import struct
import unittest
from engine.replay_state import decode_state

class ReplayStateTests(unittest.TestCase):
    def decode(self,p):
        return decode_state(p,version=94,rsqrt_seed=lambda s:1/math.sqrt(s))
    def fixture(self):
        p=bytearray(259)
        p[86]=127
        return p
    def test_layout_signed_scalars_and_flags(self):
        p=self.fixture();p[0]=2;p[1]=255
        struct.pack_into('<h',p,111,-32768)
        struct.pack_into('<I',p,197,0xdeadbeef)
        p[253]=3;p[254]=99
        r=self.decode(p+b'extra')
        self.assertEqual(r['consumed'],259)
        self.assertEqual(r['flags'][:2],[0,1])
        self.assertEqual(r['flags'][-1],1)
        self.assertEqual(r['tags'][-1],99)
        self.assertEqual(r['raw_words'][0],0xdeadbeef)
        self.assertAlmostEqual(r['scalars'][0],-327.68,places=4)
        self.assertEqual(len(r['scalars']),48)
    def test_truncation_and_bad_vectors(self):
        for n in range(259):
            with self.assertRaises(ValueError):self.decode(self.fixture()[:n])
        p=self.fixture();struct.pack_into('<f',p,24,math.nan)
        with self.assertRaises(ValueError):self.decode(p)
