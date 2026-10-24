import unittest
from engine.pose_context_detach import detach_pose_body


class ContextDetachTests(unittest.TestCase):
    def test_captured_group_array_extent_and_later_array_reload(self):
        c=dict(group408=8,group410=10,groups418=dict(count=2,slots=[1,2]),
               groups428=dict(count=1,slots=[3]),tracked=dict(count=3,slots=[7,9,7]))
        b=dict(token=7,group=8);seen=[]
        def remove(g,b):seen.append(('remove',g));b['group']=0
        def prune(g,b):
            seen.append(('prune',g))
            if g==1:
                c['groups418']['count']=0;c['groups418']['slots'][1]=22
                c['groups428']=dict(count=2,slots=[33,44])
        index=detach_pose_body(c,b,remove_body=remove,prune_constraints=prune,process_group=None)
        self.assertEqual(seen,[('remove',8),('prune',1),('prune',22),('prune',33),('prune',44)])
        self.assertEqual(index,0);self.assertEqual(c['tracked'],dict(count=2,slots=[7,9,7]))

    def test_other_group_processed_before_tracked_lookup(self):
        c=dict(group408=8,group410=10,tracked=dict(count=0,slots=[]));b=dict(token=7,group=12)
        def process(c,g):
            self.assertEqual(g,12);c['tracked']=dict(count=1,slots=[7])
        self.assertEqual(detach_pose_body(c,b,remove_body=lambda g,b:None,
            prune_constraints=None,process_group=process),0)
        self.assertEqual(c['tracked']['count'],0)
