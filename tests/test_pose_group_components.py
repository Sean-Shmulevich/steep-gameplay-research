import unittest
from engine.pose_group_components import prepare_pose_group_destinations
from engine.pose_group_destinations import assign_pose_group_destinations


class ComponentsTests(unittest.TestCase):
    def test_reversed_edges_components_and_unconnected_body(self):
        b=[dict(index=i,flags16=0x8000,metadata=dict(flags8=0)) for i in range(6)]
        group=dict(token=9,count=6,links=[(b[1],b[2]),(b[0],b[1]),(b[3],b[4])],poses=[],slots=b)
        d=[99]*7;calls=[]
        def acquire():calls.append(88);return 88
        n=prepare_pose_group_destinations(group,d,acquire_group=acquire)
        self.assertEqual((n,d),(2,[9,9,9,88,88,0,99]));self.assertEqual(calls,[88])
        # The following recovered loop keeps all seeded components and allocates
        # for the disconnected body because preparation returned nonzero.
        assign_pose_group_destinations(dict(group410=10),group,d,count=6,
            preparation_result=n,eligible=None,acquire_group=lambda c:77)
        self.assertEqual(d,[9,9,9,88,88,77,99])

    def test_only_second_endpoint_class_gates_edges(self):
        a=dict(index=0,flags16=0);b=dict(index=1,flags16=0x8000)
        g=dict(token=9,count=2,links=[(b,a)],poses=[(a,None)])
        d=[3,4]
        self.assertEqual(prepare_pose_group_destinations(g,d,acquire_group=None),0)
        self.assertEqual(d,[0,0])
        g['links']=[(a,b)]
        self.assertEqual(prepare_pose_group_destinations(g,d,acquire_group=None),1)
        self.assertEqual(d,[9,9])
