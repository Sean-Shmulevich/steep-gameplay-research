import copy
import math
import unittest
from engine.contact import evaluate_cell,apply_result
from engine.procedural import limb_target,orient_bones,landing_alignment
from engine.camera import update
from engine.world import World
class KernelTests(unittest.TestCase):
    def test_cell_pressure_and_angular_impulse(self):
        b=dict(position=[0,0,0],velocity=[0,0,0],angular_velocity=[0,0,0],mass=10)
        surface=dict(normal=[0,0,1],point=[0,0,0],material=World().sample(0,0)['material'])
        settings=dict(face_weight=1,total_weight=1,face_normal=[0,0,1],depth_curve={'domain':[0,1],'$array':[1,1]})
        points=[[0,0,-1],[1,0,-1],[0,1,-1],[0,0,0]]
        result=evaluate_cell(b,points,surface,1/120,settings)
        self.assertAlmostEqual(result['submerged_volume'],1/6)
        self.assertGreater(result['pressure_impulse'][2],0)
        apply_result(b,result,[[1,0,0],[0,1,0],[0,0,1]])
        self.assertGreater(b['velocity'][2],0);self.assertNotEqual(b['angular_velocity'],[0,0,0])
        dry=evaluate_cell(b,[[x,y,z+3] for x,y,z in points],surface,1/120,settings)
        self.assertEqual(dry['submerged_volume'],0)
    def test_orientation_write_does_not_mutate_input(self):
        pose=[dict(translation=[0,0,0],quaternion_xyzw=[0,0,0,1])]
        out=orient_bones(pose,[dict(index=0,target=[0,0,math.sqrt(.5),math.sqrt(.5)],weight=.5)])
        self.assertEqual(pose[0]['quaternion_xyzw'],[0,0,0,1]);self.assertGreater(out['local_pose'][0]['quaternion_xyzw'][2],0)
    def test_limb(self):
        request=dict(root=[0,0,0],middle=[.5,.5,0],end=[1,0,0],requested_middle=[.3,.7,0],requested_end=[.8,.2,0],middle_weight=.8,alignment_control=.3,end_weight=1.,mix_bias=.4)
        self.assertTrue(all(math.isfinite(x) for x in limb_target(request)['target']))
        request['middle']=request['root']
        with self.assertRaises(ValueError):limb_target(request)
    def test_camera_moves_without_body_write(self):
        body=dict(position=[0,0,0],orientation=[0,0,0,1]);original=copy.deepcopy(body);state={};update(state,body,1/120)
        self.assertEqual(body,original);self.assertEqual(state['position'],[-6,0,3])
        body['position'][0]=5;update(state,body,1/120)
        self.assertGreater(state['position'][0],-6);self.assertLess(state['position'][0],-1)
