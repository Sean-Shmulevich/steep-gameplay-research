import struct
import unittest
from engine.snow_pose_drive_row import build_pose_drive_row


class DriveRowTests(unittest.TestCase):
    def args(self):
        return dict(class_byte=0,base_row=0,class_count=0,row_region_offset=256,
                    result_count=7,mode=2,context_scalar=None,context_scale=2,
                    axis=[1,2,3,-0.],target=[1,-2,3,99],strength=[4,5,6,7])

    def test_direct_target_and_packed_strength(self):
        r=build_pose_drive_row(b'\xa5'*96,**self.args())
        self.assertEqual(struct.unpack_from('<4f',r['row'],0x10),(-1,2,-3,8))
        self.assertEqual(r['row'][0x50:0x60],struct.pack('<4f',-1,-2,-3,0.))
        self.assertEqual(r['row'][0x40:0x50],b'\xa5'*16)
        self.assertEqual(r['row'][:4],b'\xa5'*4)

    def test_difference_clamp_and_negative_cap(self):
        args=self.args();args.update(mode=0,context_scalar=2,
            current=[0,0,0,0],cap=[1,1,-1,0])
        r=build_pose_drive_row(bytes(96),**args)
        self.assertEqual(struct.unpack_from('<4f',r['row'],0x10),(-1,1,1,8))

    def test_sse_equal_zero_selects_second_operand(self):
        args=self.args();args.update(mode=1,context_scalar=1,
            target=[0]*4,current=[0]*4,cap=[-0.]*4)
        r=build_pose_drive_row(bytes(96),**args)
        self.assertEqual(r['row'][0x10:0x1c],struct.pack('<3f',0.,0.,0.))

    def test_optional_caller_selects_axis_and_notification(self):
        from engine.snow_pose_drive_row import build_optional_pose_drive
        args=self.args()
        for name in ('mode','axis','current','cap','context_scalar','target','strength'):
            args.pop(name,None)
        args.update(initial_row=bytes(96),state=1,enabled_byte=255,
            suppress_notification_byte=0,swap_byte=1,
            primary_axis=[1,0,0,0],swapped_axis=[0,1,0,0],
            target=3,strength=4,body_indices=[0x12345,2],
            body_group_present=True,body_context_present=True)
        r=build_optional_pose_drive(**args)
        self.assertTrue(r['notification_requested'])
        self.assertEqual(struct.unpack_from('<4f',r['row']['row'],0x30),(0,1,0,0))
        self.assertEqual(struct.unpack_from('<HH',r['row']['row']),(0x2345,2))
        for key,value in [('suppress_notification_byte',255),('body_group_present',False),('body_context_present',False)]:
            changed=dict(args);changed[key]=value
            self.assertFalse(build_optional_pose_drive(**changed)['notification_requested'])
        args.update(state=0,enabled_byte=None,initial_row=None)
        self.assertIsNone(build_optional_pose_drive(**args)['row'])
