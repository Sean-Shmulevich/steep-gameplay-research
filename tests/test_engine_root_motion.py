import copy
import math
import unittest
from engine.root_motion import extract_motion, remove_motion_from_model_pose
from reference.skeleton import native_compose


def pose(x=0, y=0, z=0, yaw=0):
    return {'translation': [x,y,z], 'quaternion_xyzw': [0,0,math.sin(yaw/2),math.cos(yaw/2)]}


def clip(loop=True, initial=None, final=None):
    return {'duration': 1., 'loop': loop, 'channels': {'trajectory': [
        dict(time=0., **(initial or pose())), dict(time=1., **(final or pose(1)))]}}


def query(c, a, b, **kwargs):
    return extract_motion(c,a,b,motion_channel='trajectory',**kwargs)


class RootMotionTests(unittest.TestCase):
    def assertVector(self, a, b):
        for x,y in zip(a,b): self.assertAlmostEqual(x,y,places=10)

    def test_crossing_and_multiple_cycles(self):
        self.assertVector(query(clip(),.75,1.25)['displacement'], [.5,0,0])
        result=query(clip(),0,3.)
        self.assertVector(result['displacement'],[3,0,0])
        self.assertEqual(result['diagnostics']['cycle_crossings'],3)

    def test_turning_cycles_compose(self):
        result=query(clip(final=pose(1,yaw=math.pi/2)),0,2)
        self.assertVector(result['displacement'],[1,1,0])
        self.assertVector(result['delta_transform']['quaternion_xyzw'],[0,0,1,0])

    def test_nonidentity_start_and_reverse(self):
        c=clip(initial=pose(7,2,yaw=.3),final=pose(8,2,yaw=.3))
        self.assertVector(query(c,0,2)['displacement'],[2,0,0])
        self.assertVector(query(c,1.2,-.8)['displacement'],[-2,0,0])
        forward=query(c,.2,2.3)['delta_transform']
        reverse=query(c,2.3,.2)['delta_transform']
        identity=native_compose(forward,reverse)
        self.assertVector(identity['translation'],[0,0,0])
        self.assertAlmostEqual(abs(identity['quaternion_xyzw'][3]),1.)

    def test_reset_and_nonloop_clamp(self):
        self.assertVector(query(clip(),.75,1.25,loop_policy='reset')['displacement'],[-.5,0,0])
        self.assertVector(query(clip(False),-5,8)['displacement'],[1,0,0])
        self.assertVector(query(clip(False),2,7)['displacement'],[0,0,0])

    def test_basis_rotation(self):
        result=query(clip(),0,1,basis=pose(yaw=math.pi/2)['quaternion_xyzw'])
        self.assertVector(result['displacement'],[0,1,0])
        self.assertVector(result['delta_transform']['translation'],[1,0,0])

    def test_quaternion_sign_does_not_create_rotation(self):
        last=pose(1);last['quaternion_xyzw']=[0,0,0,-1]
        result=query(clip(final=last),0,2)
        self.assertAlmostEqual(abs(result['delta_transform']['quaternion_xyzw'][3]),1.)

    def test_in_place_model_space_and_immutability(self):
        c=clip(); bones=[dict(name='root',**pose(.25)),dict(name='child',**pose(.25,0,2))]
        original=copy.deepcopy((c,bones))
        result=query(c,0,1.25,in_place=True,model_pose=bones)
        self.assertVector(result['model_pose'][0]['translation'],[0,0,0])
        self.assertVector(result['model_pose'][1]['translation'],[0,0,2])
        self.assertEqual((c,bones),original)
        self.assertFalse(result['diagnostics']['physics_applied'])
        result['model_pose'][0]['name']='changed'
        self.assertEqual(bones[0]['name'],'root')

    def test_rotated_motion_removal(self):
        motion=pose(2,3,yaw=math.pi/2)
        child=native_compose(motion,pose(1,0,2,yaw=.2))
        clean=remove_motion_from_model_pose([child],motion)[0]
        self.assertVector(clean['translation'],[1,0,2])
        self.assertVector(clean['quaternion_xyzw'],pose(yaw=.2)['quaternion_xyzw'])

    def test_large_cycle_and_zero_interval(self):
        self.assertVector(query(clip(),0,1000000)['displacement'],[1000000,0,0])
        self.assertVector(query(clip(),4.3,4.3)['delta_transform']['translation'],[0,0,0])

    def test_huge_cycle_request_rejected(self):
        with self.assertRaises(ValueError): query(clip(),0,1e300)
        c=clip(); c['duration']=1e-300
        c['channels']['trajectory'][1]['time']=1e-300
        with self.assertRaises(ValueError): query(c,0,1e300)

    def test_inclusive_endpoint_compatible_pose_removal(self):
        c=clip(); c['wrap_policy']='inclusive'
        result=query(c,0,1,model_pose=[pose(1)],in_place=True)
        self.assertVector(result['model_pose'][0]['translation'],[0,0,0])
        self.assertEqual(result['diagnostics']['end_phase'],1.)
        self.assertFalse(result['diagnostics']['crossfade_supported'])

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError): extract_motion(clip(),0,1,motion_channel='Reference')
        with self.assertRaises(ValueError): query(clip(),0,1,in_place=True)
        with self.assertRaises(ValueError): query(clip(),float('nan'),1)
        with self.assertRaises(ValueError): query(clip(),0,1,loop_policy='guess')
        c=clip();c['channels']['trajectory']={'translation':[{'time':0,'value':[0,0,0]}]}
        with self.assertRaises(ValueError): query(c,0,1)


if __name__=='__main__': unittest.main()
