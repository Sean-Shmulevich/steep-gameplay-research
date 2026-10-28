import struct
import unittest
from engine.pose_body_quiet_state import reset_pose_body_quiet_state
from engine.pose_group_finalize import finalize_pose_group
from engine.pose_group_poststep import poststep_pose_group


class BodyReactivationTests(unittest.TestCase):
    def test_reset_preserves_motion_and_high_metadata_nibble(self):
        body=bytearray([0xa5]*0x200);meta=bytearray([0xff]*0x60)
        before=bytes(body);reset_pose_body_quiet_state(body,meta)
        self.assertEqual(meta[0x53],0xf0)
        self.assertEqual(body[:0x28],before[:0x28]);self.assertEqual(body[0x28:0x2c],bytes(4))
        self.assertEqual(body[0x2c:],before[0x2c:])

    def test_finalization_queues_state2_links_before_reset_and_enables_poststep(self):
        body=bytearray(0x200);meta=bytearray(0x60);meta[0x53]=0xa2
        struct.pack_into('<f',body,0x28,5)
        g=dict(token=99,index=0,flag_a0=1,count=1,slots=[1],link_count=1,link_slots=[7])
        arr=lambda values:dict(count=len(values),capacity=8,slots=values+[None]*(8-len(values)))
        context=dict(group408=0,group410=0,groups418=arr([]),groups428=arr([99]),tracked=arr([]),pending_links=arr([]))
        records={1:dict(token=1,metadata=dict(kind8=meta[0x53]))}
        def reset(record):
            reset_pose_body_quiet_state(body,meta)
            record['metadata']['kind8']=meta[0x53]
        self.assertTrue(finalize_pose_group(context,g,groups={99:g},bodies=records,
            links={7:dict(first=1)},virtual40=reset,grow=None))
        self.assertEqual(context['pending_links']['slots'][0],7)
        self.assertEqual(meta[0x53],0xa0);self.assertEqual(g['flag_a0'],0)
        self.assertEqual(context['groups428']['count'],0)
        self.assertEqual(context['groups418']['slots'][0],99)
        self.assertEqual(context['tracked']['slots'][0],1)
        calls=[]
        poststep_pose_group(g,bodies={},scalar=.5,check_enabled=False,duration_threshold=1,
            linear_threshold=1,angular_threshold=1,set_inactive=lambda t:self.fail(),
            integrate=lambda t,s:calls.append(('integrate',t)),refresh=lambda t:calls.append(('refresh',t)))
        self.assertEqual(calls,[('integrate',1),('refresh',1)])
