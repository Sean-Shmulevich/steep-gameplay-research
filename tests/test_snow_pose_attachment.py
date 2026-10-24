import unittest
from engine.snow_pose_attachment import attach_pose_record


class PoseAttachmentTests(unittest.TestCase):
    def test_capture_for_merge_reload_for_append_and_nonzero_flag(self):
        a={'group':1};b={'group':2};events=[]
        def prepare(ctx,group):
            events.append(('prepare',group));a['group']=3;b['group']=3
        def merge(ctx,first,second):
            events.append(('merge',first['group'],second['group']));a['group']=4
        def append(group,record):events.append(('append',group,record));return False
        result=attach_pose_record(None,7,a,b,255,prepare_group=prepare,merge_groups=merge,append_record=append)
        self.assertFalse(result)
        self.assertEqual(events,[('prepare',1),('prepare',2),('merge',3,3),('append',4,7)])

    def test_same_group_prepared_twice_and_absence_skips_preparation(self):
        a={'group':1};events=[]
        services=dict(prepare_group=lambda c,g:events.append(g),merge_groups=lambda *args:self.fail('unexpected merge'),append_record=lambda g,r:(g,r))
        self.assertEqual(attach_pose_record(None,9,a,a,1,**services),(1,9))
        self.assertEqual(events,[1,1]);events.clear()
        attach_pose_record(None,9,a,None,1,**services)
        self.assertEqual(events,[])
