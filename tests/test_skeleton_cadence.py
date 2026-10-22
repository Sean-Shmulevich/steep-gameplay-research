import hashlib
import itertools
import json
import struct
import unittest
from pathlib import Path
from reference.skeleton_cadence import advance_skeleton_cadence


class SkeletonCadenceTests(unittest.TestCase):
    def test_native_tail_digest(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/skeleton_cadence_validation.json').read_text())
        digest=hashlib.sha256();n=0
        for counter,interval,forced,alternate in itertools.product(range(256),(0,1,2,3,7,255),(0,1),(0,1)):
            r=advance_skeleton_cadence(counter,interval,0xa4|forced,255,0.125,0.016 if alternate else 0.01)
            digest.update(struct.pack('<fBBB',r['accumulated'],r['counter'],r['flags'],r['dirty']));n+=1
        self.assertEqual(n,receipt['cases']);self.assertEqual(digest.hexdigest(),receipt['sha256'])

    def test_nondivisor_wrap_has_two_adjacent_resets(self):
        a=advance_skeleton_cadence(255,3,0,255,1.0,0.125)
        b=advance_skeleton_cadence(a['counter'],3,a['flags'],a['dirty'],a['accumulated'],0.125)
        self.assertEqual((a['counter'],b['counter']),(0,1))
        self.assertFalse(a['accumulated_this_call']);self.assertFalse(b['accumulated_this_call'])
        self.assertEqual(b['accumulated'],0)

    def test_force_reset_consumed_and_other_bits_preserved(self):
        r=advance_skeleton_cadence(1,3,255,255,2.0,0.125)
        self.assertEqual((r['accumulated'],r['flags'],r['dirty']),(0,254,239))
        r=advance_skeleton_cadence(r['counter'],3,r['flags'],r['dirty'],r['accumulated'],0.125)
        self.assertEqual(r['accumulated'],0.125)

    def test_interval_zero_resets_without_division(self):
        r=advance_skeleton_cadence(11,0,0,0,float('nan'),float('inf'))
        self.assertEqual(r['accumulated'],0)
