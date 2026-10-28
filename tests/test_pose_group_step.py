import struct
import unittest
from engine.pose_group_step import run_pose_group_step

NAMES=('build_body_buffers','build_link_rows','build_pose_rows','solve','link_feedback',
       'body_feedback','pose_feedback','refresh_secondary_rows','apply_secondary_state','poststep')


def fixture(flags):
    ctx=bytearray([0xa5]*0x600);group=bytearray(0xa8)
    struct.pack_into('<Q',ctx,0x30,99);struct.pack_into('<I',ctx,0x38,flags)
    struct.pack_into('<3I',ctx,0x170,0x200,0x280,0x2c0)
    struct.pack_into('<f',ctx,0x10,.5);struct.pack_into('<3f',ctx,0x24,1,2,3)
    for off,ptr,count in [(0x10,100,3),(0x40,200,2),(0x90,300,1)]:struct.pack_into('<QI',group,off,ptr,count)
    return ctx,group


class GroupStepTests(unittest.TestCase):
    def test_two_phase_order_and_zeroing(self):
        ctx,group=fixture(0x40010000);events=[]
        def call(name,*args):
            events.append((name,args,struct.unpack_from('<I',ctx,0x38)[0]))
            if name=='refresh_secondary_rows':self.assertEqual(ctx[0x280:0x2c0],bytes(64))
        services={name:(lambda *args,name=name:call(name,*args)) for name in NAMES}
        run_pose_group_step(ctx,base_token=1000,groups={99:group},services=services)
        self.assertEqual([x[0] for x in events],list(NAMES[:7])+['refresh_secondary_rows','solve','apply_secondary_state','poststep'])
        self.assertEqual(events[0][1],(1512,1640,100,2,1016,1000))
        self.assertEqual(events[2][2]&0x18000000,0x08000000)
        self.assertEqual(events[7][2]&0x18000000,0x10000000)
        self.assertEqual(events[-1][1],(99,.5,1,1,2,3))

    def test_second_solve_can_disable_application_and_group_is_captured(self):
        ctx,group=fixture(0x10000);events=[];solves=[]
        def call(name,*args):
            events.append((name,args))
            if name=='build_link_rows':
                struct.pack_into('<Q',ctx,0x30,777)
                struct.pack_into('<QI',group,0x10,555,1)
            if name=='solve':
                solves.append(1)
                if len(solves)==2:struct.pack_into('<I',ctx,0x38,0)
        run_pose_group_step(ctx,base_token=0,groups={99:group},services={name:(lambda *a,name=name:call(name,*a)) for name in NAMES})
        self.assertNotIn('apply_secondary_state',[x[0] for x in events])
        self.assertEqual(dict(events)['body_feedback'],(0,555,563))
        self.assertEqual(events[-1][1][0],99)

    def test_no_secondary_preserves_state(self):
        ctx,group=fixture(0);before=bytes(ctx[0x280:0x2c0]);events=[]
        services={name:(lambda *a,name=name:events.append(name)) for name in NAMES}
        run_pose_group_step(ctx,base_token=0,groups={99:group},services=services)
        self.assertEqual(events.count('solve'),1)
        self.assertEqual(ctx[0x280:0x2c0],before)
