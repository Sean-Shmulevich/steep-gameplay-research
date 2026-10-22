import math
import struct
import unittest
from engine.replay_spatial import decode_spatial


def block(signs=(0,1), rotations=(0,0,0,127,127,127), final=(0,0,0,127)):
    return (struct.pack('<3f', 10,20,30) + struct.pack('<15b', *([-128,0,127]*5))
            + bytes(signs) + struct.pack('<6b',*rotations)
            + struct.pack('<3f', 1,2,3) + struct.pack('<4b',*final))


def decode(data, **kw):
    return decode_spatial(data, version=94, rsqrt_seed=lambda s:1/math.sqrt(s), **kw)


class ReplaySpatialTests(unittest.TestCase):
    def test_signs_and_overlength_rotation(self):
        result = decode(block()+b'trailing')
        self.assertEqual(result['consumed'],51)
        self.assertEqual(result['rotations'][0],[0,0,0,1])
        self.assertEqual(result['rotations'][1][3],0)
        self.assertAlmostEqual(sum(x*x for x in result['rotations'][1]),1,places=6)
        self.assertEqual(result['extra_vector'],[1,2,3])
        self.assertAlmostEqual(result['extra_rotation'][3],1,places=6)
        self.assertLess(result['relative_points'][0][0],9)
        self.assertEqual(result['relative_points'][0][2],31)

    def test_nonboolean_sign_and_unit_boundary(self):
        result=decode(block(signs=(255,0),rotations=(0,0,0,127,0,0)))
        self.assertEqual(result['rotations'][0][3],-1)
        self.assertEqual(result['rotations'][1],[1,0,0,0])

    def test_guards(self):
        for n in range(51):
            with self.assertRaises(ValueError):decode(block()[:n])
        with self.assertRaises(ValueError):decode(block(final=(0,0,0,0)))
        with self.assertRaises(ValueError):
            decode_spatial(block(),version=76,rsqrt_seed=lambda x:1)
        with self.assertRaises(ValueError):decode(struct.pack('<f',math.inf)+block()[4:])
