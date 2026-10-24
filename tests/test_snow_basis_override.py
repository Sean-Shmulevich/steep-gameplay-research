import math
import unittest
from engine.snow_basis_override import normalize_override_triplet, align_override_basis


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

    def test_alignment_preserves_nonunit_axis_and_removes_parallel_component(self):
        seed = lambda n: 1/math.sqrt(n)
        basis = [[9,8,7,6], [0,2,0,3], [6,7,8,9]]
        result = align_override_basis(basis, [3,5,0,4], seed)
        self.assertEqual(result[1], basis[1])
        for actual, expected in zip(result, [[1,0,0,0],[0,2,0,3],[0,0,1,0]]):
            for a, b in zip(actual, expected):
                self.assertAlmostEqual(a,b,places=6)
        self.assertEqual(basis[0], [9,8,7,6])

    def test_parallel_alignment_has_no_invented_recovery(self):
        with self.assertRaises(ValueError):
            align_override_basis([[1,0,0,0],[0,2,0,0],[0,0,1,0]],
                                 [0,3,0,0], lambda n: 1/math.sqrt(n))
