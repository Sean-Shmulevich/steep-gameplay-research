import unittest
from engine.pose_link_selection import select_pose_link_rows

IDENTITY=[[1,0,0],[0,1,0],[0,0,1]]


class SelectionTests(unittest.TestCase):
    def select(self,points,normal=(0,0,1)):
        return select_pose_link_rows(points,normal,rotation_basis=lambda n,a:IDENTITY)

    def test_square_extrema_and_later_ties(self):
        r=self.select([[-1,-1,0],[1,-1,0],[-1,1,0],[1,1,0]])
        self.assertEqual(r['center'],[0,0,0])
        self.assertEqual(r['indices'],[3,1,2,3])

    def test_degenerate_points_can_repeat_indices(self):
        self.assertEqual(self.select([[2,3,4]]*5)['indices'],[4,4,4,4])

    def test_normal_is_not_silently_normalized(self):
        seen=[]
        select_pose_link_rows([[0,0,0],[1,2,3]],[0,0,2],
            rotation_basis=lambda n,a:seen.append((n,a)) or IDENTITY)
        self.assertEqual(seen[0][0],[0,0,2])

    def test_zero_normal_is_explicitly_outside_api_domain(self):
        with self.assertRaises(ValueError):self.select([[0,0,0]],[0,0,0])

    def test_reduction_copies_from_snapshot_and_preserves_tail(self):
        import struct
        from engine.pose_link_selection import reduce_pose_link_records
        records=[]
        for i,p in enumerate([[-1,-1,0],[1,-1,0],[-1,1,0],[1,1,0],[0,0,0]]):
            r=bytearray([i]*48)
            struct.pack_into('<3f',r,0,0,0,1);struct.pack_into('<3f',r,16,*p)
            records.append(bytes(r))
        collection=dict(count=5,slots=records[:])
        selection=reduce_pose_link_records(collection,rotation_basis=lambda n,a:IDENTITY)
        self.assertEqual(collection['count'],4)
        self.assertEqual(collection['slots'][:4],[records[i] for i in selection['indices']])
        self.assertEqual(collection['slots'][4],records[4])
        self.assertIsNone(reduce_pose_link_records(collection,rotation_basis=lambda *a:self.fail()))
