import struct
import unittest
from engine.pose_group_prepare import prepare_pose_group


class GroupPrepareTests(unittest.TestCase):
    def prepare(self, mode=0, body_count=2, storage_size=0x2000):
        context=bytearray(b'\xa5'*storage_size)
        settings=bytearray(64)
        struct.pack_into('<IHH',settings,0x24,mode,7,3)
        payload=bytearray(288)
        struct.pack_into('<I',payload,0x110,2)
        payload[0x114]=1
        plan=prepare_pose_group(context,settings,scalar=.5,group_token=99,
            body_count=body_count,link_tokens=[1],pose_tokens=[2],
            links={1:dict(flags84=1,second_body=10,payload_count=1,payload_slots=[20])},
            payloads={20:payload},poses={2:dict(type=1,second_body=10)},
            bodies={10:dict(metadata_flags50=0)})
        return context,plan

    def test_combined_counts_and_retained_storage(self):
        context,plan=self.prepare()
        expected=[0]*25
        expected[0]=2;expected[4]=1;expected[10]=1
        self.assertEqual(plan['row_counts'],expected)
        self.assertEqual(list(struct.unpack_from('<25I',context,0x108)),expected)
        self.assertEqual(context[0xa4:0x108],bytes(100))
        self.assertEqual(context[0x190:plan['results_offset']],b'\xa5'*(plan['results_offset']-0x190))
        self.assertEqual(context[plan['results_offset']:plan['size']],bytes(64))
        self.assertEqual(struct.unpack_from('<2f',context,0xc),(2.,.5))
        self.assertEqual(struct.unpack_from('<Q',context,0x30)[0],99)
        self.assertEqual(struct.unpack_from('<I',context,0x38)[0],0x8003001c)

    def test_full_mode_counts_before_low_bit_settings(self):
        context,plan=self.prepare(mode=4)
        self.assertEqual(plan['row_counts'][4],0)
        self.assertEqual(plan['row_counts'][6],4)
        self.assertEqual(struct.unpack_from('<I',context,0x38)[0]&3,0)

    def test_body_count_truncation_and_capacity_boundary(self):
        _,plan=self.prepare(body_count=0x10002)
        self.assertEqual(plan['body_slots'],2)
        context,exact=self.prepare(storage_size=plan['size'])
        self.assertEqual(len(context),exact['size'])
        with self.assertRaises(ValueError):self.prepare(storage_size=plan['size']-1)
