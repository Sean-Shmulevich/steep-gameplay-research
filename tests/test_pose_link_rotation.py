import unittest
from engine.pose_link_rotation import quaternion_basis,selector_rotation_basis
from engine.pose_link_selection import select_pose_link_rows,reduce_pose_link_records


class RotationTests(unittest.TestCase):
    def test_identity_quaternion_and_nonunit_input(self):
        self.assertEqual(quaternion_basis([0,0,0,1]),[[1,0,0],[0,1,0],[0,0,1]])
        self.assertEqual(quaternion_basis([2,0,0,0]),[[1,0,0],[0,-7,0],[0,0,-7]])

    def test_literal_rotation_orientation(self):
        basis=selector_rotation_basis([0,0,1])
        self.assertEqual(basis[0],[0.7987134456634521,0.6017115712165833,0.0])
        self.assertEqual(basis[1],[-0.6017115712165833,0.7987134456634521,0.0])
        self.assertEqual(basis[2],[0.0,0.0,1.0])

    def test_other_angles_not_silently_approximated(self):
        with self.assertRaises(ValueError):selector_rotation_basis([0,0,1],0.5)

    def test_selector_runs_without_external_service(self):
        r=select_pose_link_rows([[-1,-1,0],[1,-1,0],[-1,1,0],[1,1,0]],[0,0,1])
        self.assertEqual(len(r['indices']),4)
        self.assertEqual(sorted(r['indices']),[0,1,2,3])
