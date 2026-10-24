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

    def test_append_limit_and_growth_publication_order(self):
        from engine.snow_pose_attachment import append_pose_record
        group=dict(token=10,count=0,capacity=0,slots=[]);record=dict(token=20)
        def grow(g,n):
            self.assertEqual((record['group'],record['index']),(10,0))
            self.assertEqual(n,8);g['slots']=[None]*n;g['capacity']=n
        self.assertTrue(append_pose_record(group,record,grow=grow))
        self.assertEqual(group['slots'][0],20);self.assertEqual(group['count'],1)
        original=dict(record);group['count']=65535
        self.assertFalse(append_pose_record(group,record,grow=lambda *a:self.fail('growth at limit')))
        self.assertEqual(record,original)

    def test_append_does_not_invent_growth_failure_rollback(self):
        from engine.snow_pose_attachment import append_pose_record
        group=dict(token=10,count=0,capacity=0,slots=[]);record=dict(token=20)
        with self.assertRaises(ValueError):append_pose_record(group,record,grow=lambda *a:False)
        self.assertEqual(record,dict(token=20,group=10,index=0))
        self.assertEqual(group['count'],0)

    def test_remove_swaps_last_repairs_index_and_preserves_inactive_tail(self):
        from engine.snow_pose_attachment import remove_pose_record
        records={t:dict(token=t,group=10,index=i) for i,t in enumerate((20,21,22))}
        group=dict(token=10,count=3,capacity=5,slots=[20,21,22,None,None])
        remove_pose_record(group,records[21],records)
        self.assertEqual(group['slots'],[20,22,22,None,None])
        self.assertEqual(group['count'],2);self.assertEqual(group['capacity'],5)
        self.assertEqual(records[22]['index'],1)
        self.assertEqual((records[21]['group'],records[21]['index']),(0,0xffffffff))
        with self.assertRaises(ValueError):remove_pose_record(group,records[21],records)
        remove_pose_record(group,records[22],records)
        self.assertEqual(group['slots'][1],22)
        self.assertEqual(records[22]['group'],0)

    def test_append_remove_roundtrip_keeps_capacity(self):
        from engine.snow_pose_attachment import append_pose_record,remove_pose_record
        group=dict(token=10,count=0,capacity=1,slots=[None]);r=dict(token=20)
        append_pose_record(group,r,grow=lambda *a:self.fail('unexpected grow'))
        remove_pose_record(group,r,{20:r})
        self.assertEqual(group,dict(token=10,count=0,capacity=1,slots=[20]))
