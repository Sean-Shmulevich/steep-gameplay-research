import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('parent_compare',Path(__file__).resolve().parents[1]/'scripts/compare_animation_parent.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ParentComparisonTests(unittest.TestCase):
    def data(self):
        return dict(rows=[dict(animation=dict(status='completed',result=dict(found=True,
            owner_matrix=[1,0,0,0,0,1,0,0,0,0,1,0,10,20,30,99],owner_accessor_present=True,
            parent_vector=[10,20,30,0],parent_rotation=[0,0,0,1])))])
    def test_equal_does_not_establish_freshness(self):
        r=module.compare_parent(self.data());self.assertEqual(r['bit_exact_parent_matches'],1)
        self.assertFalse(r['freshness_established']);self.assertFalse(r['world_space_established'])
    def test_disagreement_is_observation_not_error(self):
        d=self.data();d['rows'][0]['animation']['result']['parent_vector'][0]=12
        r=module.compare_parent(d);self.assertTrue(r['comparison_completed'])
        self.assertEqual(r['bit_exact_parent_matches'],0);self.assertEqual(r['max_translation_difference'],2)
    def test_missing_parent_fields_rejected(self):
        d=self.data();del d['rows'][0]['animation']['result']['owner_matrix']
        self.assertFalse(module.compare_parent(d)['comparison_completed'])
    def test_owner_body_brackets_report_distance_without_frame_claim(self):
        d=self.data();r=d['rows'][0];r['animation']['result']['identity']=7
        body=dict(identity=7,position=[11,20,30],axes=[[1,0,0],[0,1,0],[0,0,1]])
        r['player']=dict(status='completed',result=body);r['player_after']=dict(status='completed',result=body.copy())
        result=module.compare_owner_body(d)
        self.assertEqual(result['compared_identity_brackets'],1)
        self.assertEqual(result['max_translation_distance'],1)
        self.assertEqual(result['max_stored_basis_lane_difference'],0)
        self.assertFalse(result['coordinate_equivalence_established'])
        r['player_after']['result']['identity']=8
        self.assertEqual(module.compare_owner_body(d)['skipped'],1)
    def test_decimal_json_roundtrip_not_reported_as_translation_error(self):
        d=self.data();p=d['rows'][0]['animation']['result']
        p['owner_matrix'][12]=1234.56787;p['parent_vector'][0]=1234.56787
        result=module.compare_parent(d)
        self.assertEqual(result['bit_exact_parent_matches'],1)
        self.assertEqual(result['max_translation_difference'],0)
    def test_w_difference_preserved_separately_from_xyz(self):
        d=self.data();d['rows'][0]['animation']['result']['parent_vector'][3]=1
        result=module.compare_parent(d)
        self.assertEqual(result['bit_exact_parent_matches'],0)
        self.assertEqual(result['bit_exact_xyz_matches'],1)
        self.assertEqual(result['bit_exact_rotation_matches'],1)
        self.assertEqual(result['parent_w_little_endian_bit_patterns'],{'0000803f':1})
        self.assertEqual(result['reset_parent_formula_matches'],1)
