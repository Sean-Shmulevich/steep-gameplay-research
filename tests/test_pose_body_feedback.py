import struct
import unittest
from engine.pose_body_feedback import write_pose_body_feedback
from engine.pose_body_buffers import build_pose_body_buffers

class BodyFeedbackTests(unittest.TestCase):
    def test_raw_xyz_copy_excludes_fourth_lanes_and_preserves_tail(self):
        body=bytearray([0xa5]*0x200);original=bytes(body)
        words=[0x7fc12345,0x80000000,0x7f800000,123,4,5,6,456]
        state=struct.pack('<8I',*words)
        write_pose_body_feedback([1],bodies={1:body},body_state=[state])
        self.assertEqual(body[0x1a0:0x1ac],state[:12]);self.assertEqual(body[0x1ac:0x1b8],state[16:28])
        self.assertEqual(body[:0x1a0],original[:0x1a0]);self.assertEqual(body[0x1b8:],original[0x1b8:])

    def test_duplicate_body_last_entry_wins_without_reading_index_field(self):
        body=bytearray([0xff]*0x200)
        write_pose_body_feedback([1,1],bodies={1:body},body_state=[bytes([1]*32),bytes([2]*32)])
        self.assertEqual(body[0x1a0:0x1b8],bytes([2]*24))

    def test_producer_motion_increment_reaches_body_fields(self):
        source=dict(metadata_flags52=0,flagsaa=0,basis=[[1,0,0],[0,1,0],[0,0,1]],
                    tensor170=[[1,0,0],[0,1,0],[0,0,1]],scalar124=1,motion1a0=[1,2,3],motion1ac=[4,5,6])
        output=build_pose_body_buffers([source],scalar=2,vector=[0,0,-1])
        body=bytearray(0x200);write_pose_body_feedback([1],bodies={1:body},body_state=output['body_state'])
        self.assertEqual(struct.unpack_from('<6f',body,0x1a0),(1,2,1,4,5,6))

    def test_missing_state_is_not_filled_in(self):
        with self.assertRaises(ValueError):write_pose_body_feedback([1],bodies={1:bytearray(0x200)},body_state=[])

    def test_producer_builder_solve_and_body_writeback(self):
        import json
        from pathlib import Path
        from engine.pose_link_builder_bench import inspect
        from engine.pose_link_solve import solve_pose_link_rows
        fixture=Path(__file__).resolve().parents[1]/'engine/examples/pose_link_builder.json'
        document=json.loads(fixture.read_text());payload=bytearray.fromhex(document['inputs']['payload_hex'])
        struct.pack_into('<f',payload,0x38,-2);document['inputs']['payload_hex']=payload.hex()
        built=inspect(document);first=document['inputs']['first_body']
        source=dict(metadata_flags52=0,flagsaa=0,basis=first['frame']['basis'],tensor170=[[1,0,0],[0,1,0],[0,0,1]],
                    scalar124=1,motion1a0=first['motion1a0'],motion1ac=first['motion1ac'])
        buffers=build_pose_body_buffers([source],scalar=0,vector=[0,0,0])
        context=bytearray(0x190);struct.pack_into('<I',context,0x38,12)
        struct.pack_into('<I',context,0x108,1);struct.pack_into('<I',context,0x120,2)
        solve_pose_link_rows(context,base_token=0,
            primary_rows=[bytearray.fromhex(x) for x in built['primary_rows_hex']],
            secondary_rows=[bytearray.fromhex(x) for x in built['secondary_rows_hex']],
            results=[bytearray.fromhex(x) for x in built['result_rows_hex']],
            body_data={7:buffers['body_data'][0]},body_state={7:buffers['body_state'][0]})
        body=bytearray([0xa5]*0x200)
        write_pose_body_feedback([1],bodies={1:body},body_state=buffers['body_state'])
        self.assertEqual(struct.unpack_from('<6f',body,0x1a0),(0,0,-2,0,0,0))
        self.assertEqual(body[0x1b8:],bytes([0xa5])*(0x200-0x1b8))
