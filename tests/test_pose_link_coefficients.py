import math
import unittest
from engine.pose_link_coefficients import combine_link_scalar,link_response_coefficients,THRESHOLD


class CoefficientTests(unittest.TestCase):
    def test_modes_and_default(self):
        self.assertEqual([combine_link_scalar(4,9,m) for m in range(7)],[4,9,13,36,6.5,6,0])
        self.assertEqual(math.copysign(1,combine_link_scalar(-0.,0.,0)),-1)
        self.assertEqual(math.copysign(1,combine_link_scalar(-0.,0.,1)),1)

    def test_soft_branch_derives_nonzero_seed_gate(self):
        p=dict(field30=1,field40=2,field60=4,field64=2);m={k:0 for k in p}
        r=link_response_coefficients(p,p,m,context_scalar=2,default_factor=9,context_flags=3<<2)
        self.assertEqual(r['scaled_count'],6)
        self.assertEqual(r['response'],-0.5)
        self.assertEqual(r['seed_gate'],0.75)

    def test_threshold_equality_skips_field64_and_keeps_zero_gate(self):
        p=dict(field30=1,field40=2,field60=THRESHOLD);m={k:0 for k in p}
        r=link_response_coefficients(p,p,m,context_scalar=2,default_factor=9,context_flags=0)
        self.assertEqual(r['response'],-18)
        self.assertEqual(r['seed_gate'],0)
        self.assertIsNone(r['combined64'])

    def test_singular_and_negative_root_are_not_repaired(self):
        with self.assertRaises(ValueError):combine_link_scalar(-1,1,5)
        p=dict(field30=1,field40=2,field60=0,field64=0);m={k:0 for k in p}
        with self.assertRaises(ValueError):link_response_coefficients(p,p,m,context_scalar=1,default_factor=1,context_flags=0)

    def test_derived_gate_controls_cached_result_seed(self):
        import struct
        from engine.pose_link_result_binding import seed_pose_link_result
        for value,expected in ((4,False),(THRESHOLD,True)):
            p=dict(field30=1,field40=2,field60=value,field64=2);m={k:0 for k in p}
            coefficients=link_response_coefficients(p,p,m,context_scalar=2,default_factor=9,context_flags=12)
            row=bytearray(64);row[0x30:0x34]=struct.pack('<I',123)
            context=dict(result_rows={0:bytearray(16)})
            gate=struct.unpack('<I',struct.pack('<f',coefficients['seed_gate']))[0]
            self.assertEqual(seed_pose_link_result(context,row,bytearray(128),primary_index=0,gate_bits=gate),expected)
            self.assertEqual(context['result_rows'][0],struct.pack('<4I',*([123]*4 if expected else [0]*4)))
