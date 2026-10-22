import json
from pathlib import Path
import struct
import unittest
from reference.transform_inverse import inverse_transform
from reference.transform_composition import compose_transform


def packed(matrix):
    return struct.pack('<16f', *(x for row in matrix for x in row))


class TransformInverseTests(unittest.TestCase):
    def test_original_inverse_with_observed_seeds(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/transform_inverse_validation.json').read_text())
        self.assertEqual(receipt['cases'], 80)
        for sample in receipt['samples']:
            calls = []
            def seed(value):
                i = len(calls); calls.append(value)
                self.assertEqual(struct.pack('<f',value), struct.pack('<f',sample['seed_inputs'][i]))
                return sample['seeds'][i]
            result = inverse_transform(sample['matrix'], seed)
            self.assertEqual(packed(result), packed(sample['result']))
            self.assertEqual(len(calls), 4)

    def test_nonuniform_scale_shear_and_reflection_with_authored_seed(self):
        matrix = [[-2,.25,0,0],[0,3,0,0],[0,0,.5,0],[3,4,5,1]]
        inverse = inverse_transform(matrix, lambda x: 1/x)
        for product in (compose_transform(matrix,inverse),compose_transform(inverse,matrix)):
            for i in range(4):
                for j in range(4): self.assertAlmostEqual(product[i][j], int(i==j), places=5)

    def test_singular_refusal_is_authored_policy(self):
        with self.assertRaises(ValueError):
            inverse_transform([[0]*4 for _ in range(4)], lambda x: self.fail('zero determinant rejected first'))
