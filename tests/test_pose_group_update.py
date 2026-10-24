import unittest
from engine.pose_group_update import update_pose_body_group


class GroupUpdateTests(unittest.TestCase):
    def test_no_reassignment_finalizes_captured_group(self):
        context=dict(group408=8,group410=10)
        body=dict(group=10,metadata=dict(flags8=8,flags16=0,kind8=0))
        def eligible(c,b):b['group']=99;return 1
        result=update_pose_body_group(context,body,eligible=eligible,detach=None,
            virtual8=None,acquire_group=None,virtual40=None,append=None,
            finalize=lambda c,g:g)
        self.assertEqual(result,10)

    def test_reload_metadata_after_virtual_and_group_after_append(self):
        context=dict(group408=8,group410=10)
        body=dict(group=10,metadata=dict(flags8=8,flags16=0,kind8=0));seen=[]
        def virtual8(b,arg):
            seen.append(('virtual8',arg));b['metadata']=dict(flags8=0,flags16=0x8000,kind8=0x12);return 257
        def acquire(c):seen.append(('acquire',));return 88
        def append(g,b):seen.append(('append',g));b['group']=77
        result=update_pose_body_group(context,body,eligible=lambda c,b:0,
            detach=lambda c,b:seen.append(('detach',)),virtual8=virtual8,
            acquire_group=acquire,virtual40=lambda b:seen.append(('virtual40',)),
            append=append,finalize=lambda c,g:g)
        self.assertEqual(seen,[('detach',),('virtual8',1),('acquire',),('virtual40',),('append',88)])
        self.assertEqual(result,77)
