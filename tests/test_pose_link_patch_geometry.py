import unittest
import struct
from reference.central_impulse import f32
from engine.pose_link_patch_geometry import contact_patch_geometry, contact_patch_basis, pack_contact_patch_directions


class ContactPatchGeometryTest(unittest.TestCase):
    basis=[[1,0,0],[0,1,0],[0,0,1]]

    def test_centroid_and_mean_distance(self):
        result=contact_patch_geometry(self.basis,[10,20,30],[[-2,0,0],[2,0,0]])
        self.assertEqual(result['world_points'],[[8,20,30],[12,20,30]])
        self.assertEqual(result['centroid_arm'],[0,0,0])
        self.assertEqual(result['distance_sum'],4)
        self.assertEqual(result['spread'],2)

    def test_floor_applies_before_division(self):
        for count in (1,2,4):
            result=contact_patch_geometry(self.basis,[0,0,0],[[0,0,0]]*count)
            self.assertEqual(result['distance_sum'],0)
            self.assertEqual(result['spread'],f32(f32(.001)*f32(1/count)))

    def test_basis_scaling_affects_spread(self):
        result=contact_patch_geometry([[2,0,0],[0,1,0],[0,0,1]],[0,0,0],[[-1,0,0],[1,0,0]])
        self.assertEqual(result['spread'],2)
        with self.assertRaises(ValueError):contact_patch_geometry(self.basis,[0,0,0],[])


class ContactPatchBasisTest(unittest.TestCase):
    def test_motion_and_axis_fallbacks(self):
        moving=contact_patch_basis([0,0,1],[0,0,0],[1,0,0],[0,0,0],1)
        self.assertEqual(moving['source'],'motion')
        self.assertEqual(moving['first'],[0,-1,0])
        self.assertEqual(contact_patch_basis([0,0,1],[0,0,0],[0,0,0],[0,0,0],1)['source'],'axis_x')
        self.assertEqual(contact_patch_basis([1,0,0],[0,0,0],[0,0,0],[0,0,0],1)['source'],'axis_y')

    def test_component_threshold_and_angular_motion(self):
        def source(v):
            return contact_patch_basis([0,0,1],[0,0,0],v,[0,0,0],1)['source']
        self.assertEqual(source([.0009,.0009,0]),'axis_x')
        self.assertEqual(source([.001,0,0]),'motion')
        spinning=contact_patch_basis([0,0,1],[1,0,0],[0,0,0],[0,0,2],1)
        self.assertEqual(spinning['point_motion'],[0,2,0])
        self.assertEqual(spinning['source'],'motion')

    def test_transpose_and_retained_storage(self):
        basis=dict(first=[1,2,3],second=[4,5,6],first_angular=[7,8,9],
                   second_angular=[10,11,12],spread_direction=[13,14,15])
        row=bytearray([0xa5]*208)
        pack_contact_patch_directions(row,basis)
        self.assertEqual(row[:16],bytes([0xa5]*16))
        self.assertEqual(row[16:32],bytes(16))
        self.assertEqual(row[128:],bytes([0xa5]*80))
        self.assertEqual(struct.unpack_from('<4f',row,0x30),(2,5,0,0))
        self.assertEqual(struct.unpack_from('<4f',row,0x70),(9,12,15,0))
