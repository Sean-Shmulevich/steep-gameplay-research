import struct
import unittest
from engine.pose_link_result_binding import bind_pose_link_results,seed_pose_link_result


class ResultBindingTests(unittest.TestCase):
    def test_three_indices_and_first_feedback_reference(self):
        p=bytearray(64);rows=[bytearray(128) for _ in range(3)];c=dict(result_count=17)
        self.assertEqual(bind_pose_link_results(c,p,rows),[17,18,19])
        self.assertEqual(c['result_count'],20)
        self.assertEqual(struct.unpack_from('<I',p,0x34)[0],17)
        self.assertEqual([struct.unpack_from('<I',r,4)[0] for r in rows],[17,18,19])

    def test_counter_wrap(self):
        c=dict(result_count=0xffffffff)
        self.assertEqual(bind_pose_link_results(c,bytearray(64),[bytearray(8) for _ in range(3)]),[0xffffffff,0,1])
        self.assertEqual(c['result_count'],2)

    def test_zero_and_unordered_seed_without_float_conversion(self):
        for gate in (0,0x80000000,0x7fc00001,0xff800001):
            p=bytearray(64);p[0x30:0x34]=bytes.fromhex('0100c07f')
            row=bytearray(128);c=dict(result_rows={9:bytearray([0xa5])*16})
            self.assertTrue(seed_pose_link_result(c,p,row,primary_index=9,gate_bits=gate))
            self.assertEqual(c['result_rows'][9],p[0x30:0x34]*4)
            self.assertEqual(struct.unpack_from('<I',row,0x50)[0],9)

    def test_nonzero_gate_preserves_result_but_publishes_reference(self):
        for gate in (0x3f800000,0xbf800000,0x7f800000,0xff800000,1):
            p=bytearray(64);row=bytearray(128);c=dict(result_rows={9:bytearray([0xa5])*16})
            self.assertFalse(seed_pose_link_result(c,p,row,primary_index=9,gate_bits=gate))
            self.assertEqual(c['result_rows'][9],bytearray([0xa5])*16)
            self.assertEqual(struct.unpack_from('<I',row,0x50)[0],9)

    def test_bind_seed_supplied_result_feedback_and_next_update(self):
        from engine.pose_link_feedback import write_pose_link_feedback
        from engine.pose_link_pipeline import process_pose_link_record_group
        payload=bytearray(288);payload[0x114]=1
        struct.pack_into('<I',payload,0x110,1);struct.pack_into('<I',payload,0x2c,7)
        struct.pack_into('<I',payload,0x40,0x3f000000)
        point=payload[16:80];rows=[bytearray(128) for _ in range(3)]
        c=dict(result_count=2,result_rows={2:bytearray(16)})
        bind_pose_link_results(c,point,rows)
        seed_pose_link_result(c,point,rows[2],primary_index=2,gate_bits=0)
        self.assertEqual(c['result_rows'][2],struct.pack('<4I',*[0x3f000000]*4))
        payload[16:80]=point
        # External solver result is supplied, not calculated by this fixture.
        c['result_rows'][2][:4]=struct.pack('<I',0x3f400000)
        write_pose_link_feedback(dict(flags38=1<<29,result_rows=c['result_rows']),[1],
            links={1:dict(flags84=1,payload_count=1,payload_slots=[2])},payloads={2:payload})
        record=bytearray(48);struct.pack_into('<I',record,28,7)
        frame=dict(basis=[[1,0,0],[0,1,0],[0,0,1]],translation=[0,0,0])
        updated=process_pose_link_record_group(payload,[record],first_frame=frame,second_frame=frame,
            first_index=0,second_index=1,entry_flag=True)
        self.assertEqual(struct.unpack_from('<I',updated['payload'],0x40)[0],0x3f400000)
