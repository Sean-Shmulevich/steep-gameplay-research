import math
import struct
import unittest
from engine.snow_pose_angular_row import build_pose_angular_spring_row
from engine.snow_pose_solver_counts import HARD_THRESHOLD


class AngularRowTests(unittest.TestCase):
    def test_threshold_header_and_unused_layout(self):
        common=dict(class_byte=1,row_region_offset=256,result_count=7,context_scalar=.5,context_flags=8,axis=[0,0,1,0],reference=[1,0,0,0],target=[0,1,0,0],atan2=math.atan2)
        for k,kind,size in ((10.,'soft',80),(HARD_THRESHOLD,'hard',64)):
            layout=dict(initial_row=b'\xa5'*size,base_row=0,class_count=0)
            r=build_pose_angular_spring_row(stiffness=k,damping=2,body_indices=[0x12345,0xffffffff],hard_layout=layout if kind=='hard' else None,soft_layout=layout if kind=='soft' else None,**common)
            self.assertEqual(r['kind'],kind)
            self.assertEqual(r['row'][:8],struct.pack('<HHI',0x2345,0xffff,7))
            self.assertEqual(r['row'][8:16],b'\xa5'*8)
