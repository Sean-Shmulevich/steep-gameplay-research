import json
from pathlib import Path
import struct
import unittest
from reference.transform_composition import compose_transform, transpose_affine_transform


def packed(matrix):
    return struct.pack('<16f', *(x for row in matrix for x in row))


class TransformCompositionTests(unittest.TestCase):
    def test_original_instruction_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/transform_composition_validation.json').read_text())
        self.assertEqual(receipt['cases'], 240)
        for sample in receipt['samples']:
            if sample['kind'] == 'compose':
                result = compose_transform(sample['destination'], sample['source'])
            else:
                result = transpose_affine_transform(sample['matrix'])
            self.assertEqual(packed(result), packed(sample['result']))

    def test_noncommuting_translation_and_scale_resolve_order(self):
        scale = [[2,0,0,0],[0,3,0,0],[0,0,4,0],[0,0,0,1]]
        translation = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[1,2,3,1]]
        self.assertEqual(compose_transform(scale, translation)[3], [2,6,12,1])
        self.assertEqual(compose_transform(translation, scale)[3], [1,2,3,1])

    def test_transpose_helper_does_not_invert_scale(self):
        matrix = [[2,0,0,9],[0,3,0,8],[0,0,4,7],[1,2,3,6]]
        result = transpose_affine_transform(matrix)
        self.assertEqual(result[0], [2,0,0,0])
        self.assertEqual(result[3], [-2,-6,-12,1])

    def test_invalid_matrix_refused(self):
        with self.assertRaises(ValueError): compose_transform([], [])
        with self.assertRaises(ValueError): transpose_affine_transform([[float('nan')]*4]*4)

    def test_combined_accessor_native_receipt(self):
        from reference.transform_composition import recompute_accessor_local
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/accessor_local_math_validation.json').read_text())
        self.assertEqual(receipt['cases'], 76)
        for sample in receipt['samples']:
            result = recompute_accessor_local(sample['parent'], sample['incoming'], sample['previous'])
            self.assertEqual(packed(result['transform']), packed(sample['result']))

    def test_translation_preservation_is_whole_vector_not_per_axis(self):
        from reference.transform_composition import recompute_accessor_local
        identity = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        incoming = [[2,0,0,0],[0,3,0,0],[0,0,4,0],[.0005,.002,0,2]]
        result = recompute_accessor_local(identity, incoming, identity)
        self.assertFalse(result['translation_preserved'])
        self.assertNotEqual(result['transform'][3][0], 0)
        self.assertEqual(result['transform'][3][3], 2)
        incoming[3][1] = .0005
        result = recompute_accessor_local(identity, incoming, identity)
        self.assertTrue(result['translation_preserved'])
        self.assertEqual(result['transform'][3], [0,0,0,1])
        self.assertEqual(result['transform'][0], [2,0,0,0])

    def test_original_child_candidate_modes(self):
        from reference.transform_composition import child_transform_candidate
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/child_transform_math_validation.json').read_text())
        self.assertEqual(receipt['cases'], 72)
        for sample in receipt['samples']:
            result = child_transform_candidate(sample['mode'], sample['local'], sample['incoming'], sample['cached'])
            self.assertEqual(packed(result), packed(sample['result']))
        with self.assertRaises(NotImplementedError): child_transform_candidate(0, [], [])
        with self.assertRaises(NotImplementedError): child_transform_candidate(2, [], [])
        self.assertIsNone(child_transform_candidate(4, [], []))

    def test_child_packet_dispatch_receipt(self):
        from reference.transform_composition import prepare_child_transform_packet
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/child_transform_dispatch_validation.json').read_text())
        self.assertEqual(receipt['cases'], 160)
        for sample in receipt['samples']:
            def modifier(matrix): matrix[3][0] = 123.0
            packet = prepare_child_transform_packet(sample['mode'], receipt['local'],
                receipt['incoming'], receipt['cached'], sample['flags'],
                modifier if sample['modifier'] else None)
            if sample['result'] is None:
                self.assertIsNone(packet)
            else:
                self.assertEqual(packed(packet['first_transform']), packed(sample['result']))
                self.assertIs(packet['first_transform'], packet['second_transform'])
                self.assertEqual(packet['flags'], sample['flags'] & 0xfffffffd)

    def test_original_normalizer_with_observed_rsqrt_seeds(self):
        from reference.transform_composition import normalize_transform_basis
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/transform_normalize_validation.json').read_text())
        self.assertEqual(receipt['cases'], 64)
        for sample in receipt['samples']:
            calls = []
            def seed(n):
                i = len(calls); calls.append(n)
                self.assertEqual(n, sample['seed_inputs'][i])
                return sample['seeds'][i]
            result = normalize_transform_basis(sample['matrix'], seed)
            self.assertEqual(packed(result), packed(sample['result']))
            self.assertEqual(len(calls), 3)

    def test_normalized_modes_with_authored_exact_sqrt_seed(self):
        import math
        from reference.transform_composition import child_transform_candidate
        identity = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        local = [[99,88,77,0],[0,2,0,0],[0,0,3,0],[4,5,6,1]]
        cached = [r[:] for r in identity]; cached[3] = [7,8,9,2]
        for mode, position in ((0,[4,5,6,1]), (2,[7,8,9,1])):
            result = child_transform_candidate(mode, local, identity, cached,
                reciprocal_sqrt=lambda n: 1/math.sqrt(n))
            for i in range(3):
                for j in range(3): self.assertAlmostEqual(result[i][j], identity[i][j], places=5)
            self.assertEqual(result[3], position)

    def test_normalized_child_complete_route_receipt(self):
        from reference.transform_composition import prepare_child_transform_packet
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/child_normalized_dispatch_validation.json').read_text())
        self.assertEqual(receipt['cases'], 64)
        for sample in receipt['samples']:
            calls = []
            def seed(n):
                i = len(calls); calls.append(n)
                self.assertEqual(n, sample['seed_inputs'][i])
                return sample['seeds'][i]
            def modifier(matrix): matrix[3][0] = 123.0
            packet = prepare_child_transform_packet(sample['mode'], receipt['local'],
                receipt['incoming'], receipt['cached'], sample['flags'],
                modifier if sample['modifier'] else None, reciprocal_sqrt=seed)
            self.assertEqual(packed(packet['first_transform']), packed(sample['result']))
            self.assertEqual(packet['flags'], sample['flags'] & 0xfffffffd)
            self.assertIs(packet['first_transform'], packet['second_transform'])
            self.assertEqual(len(calls), 3)

    def test_skeleton_link_modes_are_distinct_from_hierarchy_modes(self):
        from reference.transform_composition import select_skeleton_link_transform
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/skeleton_link_modes_validation.json').read_text())
        self.assertEqual(receipt['cases'], 84)
        for sample in receipt['samples']:
            result = select_skeleton_link_transform(sample['mode'],sample['normalized'],
                sample['provider'],sample['local'],sample['cached'])
            self.assertEqual(packed(result['transform']), packed(sample['result']))
            self.assertEqual(result['publish'],sample['publish'])
            if sample['mode']==5: self.assertFalse(result['publish'])
