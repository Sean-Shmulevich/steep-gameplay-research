import struct
import unittest
from engine.pose_grid_resource_bounds import grid_resource_bounds
from engine.pose_body_bounds import refresh_pose_body_bounds

class GridBoundsTest(unittest.TestCase):
    def resource(self):
        r=bytearray(0xc0)
        # Deliberately asymmetric XY endpoints set size, not center.
        struct.pack_into('<8f',r,0x7c,10,20,-4,14,26,8,2,10)
        return r

    def test_distinct_extent_and_height_center_fields(self):
        frame=[[1,0,0],[0,1,0],[0,0,1],[100,200,300]]
        self.assertEqual(grid_resource_bounds(self.resource(),frame),[98,197,300,102,203,312])

    def test_rotated_scaled_frame(self):
        frame=[[0,2,0],[-1,0,0],[0,0,.5],[100,200,300]]
        self.assertEqual(grid_resource_bounds(self.resource(),frame),[97,196,300,103,204,306])

    def test_connected_resource_dispatch(self):
        body=bytearray(0x200);local=bytearray(64)
        for i in range(3):
            struct.pack_into('<f',body,0x40+20*i,1)
            struct.pack_into('<f',local,20*i,1)
        struct.pack_into('<Q',body,0x30,1)
        struct.pack_into('<Q',body,0xb8,2)
        struct.pack_into('<H',body,0xc0,1)
        entries=bytearray(72);struct.pack_into('<QQ',entries,16,3,4)
        metadata={1:bytearray(96)};resource=self.resource()
        refresh_pose_body_bounds(body,entry_arrays={2:entries},transforms={4:local},
                                 metadata=metadata,resource_bounds=lambda token,frame:
                                 grid_resource_bounds(resource,frame))
        self.assertEqual(struct.unpack_from('<6f',metadata[1],4),(-2,-3,0,2,3,12))
