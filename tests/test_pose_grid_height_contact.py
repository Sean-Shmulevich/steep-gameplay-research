import struct
import unittest
from engine.pose_grid_height_contact import query_grid_height_contact


class HeightContactTest(unittest.TestCase):
    frame=[[1,0,0],[0,1,0],[0,0,1],[10,20,30]]

    def test_admission_uses_center_not_radius_and_preserves_rejected_output(self):
        output=bytearray(b'X'*64)
        self.assertFalse(query_grid_height_contact('grid',self.frame,[1,2,5.1],100,output,
                                                  height_query=lambda *_:(5,9)))
        self.assertEqual(output,b'X'*64)

    def test_equality_record_and_null_output(self):
        output=bytearray(b'X'*64)
        self.assertTrue(query_grid_height_contact('grid',self.frame,[1,2,5],2,output,
                                                 height_query=lambda *_:(5,9)))
        self.assertEqual(struct.unpack_from('<4f',output),(0,0,1,-2))
        self.assertEqual(struct.unpack_from('<3f',output,16),(11,22,37))
        self.assertEqual(struct.unpack_from('<3f',output,32),(11,22,35))
        self.assertEqual(struct.unpack_from('<I',output,44),(9,))
        self.assertEqual(output[48:],b'X'*16)
        self.assertTrue(query_grid_height_contact('grid',self.frame,[1,2,4],2,None,
                                                 height_query=lambda *_:(5,9)))
