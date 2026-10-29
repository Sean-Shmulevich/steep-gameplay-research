import math
import unittest
from engine.pose_quaternion import multiply_pose_quaternions, pose_matrix_to_quaternion


class PoseQuaternionTests(unittest.TestCase):
    def test_product_order_and_no_normalization(self):
        x,y = [1,0,0,0], [0,1,0,0]
        self.assertEqual(multiply_pose_quaternions(x,y),[0,0,1,0])
        self.assertEqual(multiply_pose_quaternions(y,x),[0,0,-1,0])
        self.assertEqual(multiply_pose_quaternions([0,0,0,2],[1,2,3,4]),[2,4,6,8])

    def test_identity_and_half_turn_branches(self):
        for diagonal, expected in (
            ((1,1,1),[0,0,0,1]), ((1,-1,-1),[1,0,0,0]),
            ((-1,1,-1),[0,1,0,0]), ((-1,-1,1),[0,0,1,0])):
            columns = [[diagonal[i] if i==j else 0 for j in range(3)] for i in range(3)]
            self.assertEqual(pose_matrix_to_quaternion(columns), expected)

    def test_orientation_and_tie_priority(self):
        # All four candidates equal: W wins, without a sign canonicalization pass.
        self.assertEqual(pose_matrix_to_quaternion([[0,0,1],[1,0,0],[0,1,0]]),[-.5,-.5,-.5,.5])
        # X and Y tie above W: X wins. This reflection is not repaired.
        self.assertEqual(pose_matrix_to_quaternion([[0,0,0],[0,0,0],[0,0,-1]])[1:], [0.,0.,0.])

    def test_unused_w_and_nonunit_matrix(self):
        cols = [[0,0,0,math.nan],[0,0,0,math.inf],[0,0,0,-math.inf]]
        self.assertEqual(pose_matrix_to_quaternion(cols), [0,0,0,.5])

    def test_input_domain(self):
        with self.assertRaises(ValueError): pose_matrix_to_quaternion([[1,2,3]])
        with self.assertRaises(ValueError): pose_matrix_to_quaternion([[math.nan,0,0]]*3)
        with self.assertRaises(ValueError): multiply_pose_quaternions([math.inf,0,0,1],[0,0,0,1])
