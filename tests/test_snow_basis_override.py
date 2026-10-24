import math
import unittest
from engine.snow_basis_override import normalize_override_triplet


class BasisOverrideTests(unittest.TestCase):
    def test_independent_normalization_does_not_orthogonalize(self):
        result=normalize_override_triplet([[2,0,0,4],[3,0,0,6],[0,4,0,8]],lambda x:1/math.sqrt(x))
        expected=[[1,0,0,2],[0,1,0,2],[1,0,0,2]]
        for actual,want in zip(result,expected):
            for a,b in zip(actual,want):self.assertAlmostEqual(a,b,places=6)
        self.assertEqual(result[0],result[2])

    def test_xyz_zero_does_not_use_w_as_length_or_repair(self):
        with self.assertRaises(ValueError):
            normalize_override_triplet([[0,0,0,1],[1,0,0,0],[0,1,0,0]],lambda x:1/math.sqrt(x))
