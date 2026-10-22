import json
import math
from pathlib import Path
import unittest
from reference.animation_work_rotation import blend_work_rotation
from reference.animation_work import encode_work_pose

ROOT=Path(__file__).resolve().parents[1]


class WorkRotationTests(unittest.TestCase):
    def test_original_rotation_cases(self):
        receipt=json.loads((ROOT/'native/snow_host/animation_work_rotation_validation.json').read_text())
        self.assertEqual(receipt['cases'],192)
        for case in receipt['samples']:
            seeds=iter(case['rsqrt_seeds']);services=iter(case['math_services'])
            def service(name,x):
                observed=next(services)
                self.assertEqual((name,x),(observed['name'],observed['input']))
                return observed['output']
            result=blend_work_rotation(**case['inputs'],reciprocal_sqrt=lambda _:next(seeds),
                     acos=lambda x:service('acos',x),sin=lambda x:service('sin',x))
            self.assertEqual(json.loads(json.dumps(result)),case['result'])
            self.assertEqual(list(seeds),[]);self.assertEqual(list(services),[])
    def test_antipodal_rotations_keep_saved_without_normalizing(self):
        def unexpected(*args):raise AssertionError('no math service expected')
        result=blend_work_rotation([0,0,0,1],[0,0,0,-1],.75,unexpected,unexpected,unexpected)
        self.assertEqual(result['branch'],'keep_saved')
        self.assertEqual(result['rotation'],(0,0,0,1))
    def test_negative_dot_spherical_uses_shorter_hemisphere(self):
        result=blend_work_rotation([0,0,0,1],[.8660254,0,0,-.5],.5,
                                  lambda n:1/math.sqrt(n),math.acos,math.sin)
        self.assertEqual(result['branch'],'spherical')
        self.assertLess(result['rotation'][0],0)
        self.assertGreater(result['rotation'][3],0)
    def test_original_setter_cases(self):
        receipt=json.loads((ROOT/'native/snow_host/work_setter_validation.json').read_text())
        self.assertEqual(receipt['cases'],192)
        for case in receipt['samples']:
            result=encode_work_pose(**case['inputs'])
            self.assertEqual(json.loads(json.dumps(result)),case['result'])
    def test_composed_setter_drops_fourth_lane(self):
        result=encode_work_pose([12,24,36,99],[0,0,0,1],[10,20,30,7],[0,0,0,1],False)
        self.assertEqual(result['position'],(2,4,6,0))
        self.assertEqual(result['rotation'],(0,0,0,1))
