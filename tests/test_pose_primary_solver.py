import json
from pathlib import Path
import struct
import unittest
from engine.pose_primary_solver import prepare_pose_primary_row,iterate_pose_primary_row
from engine.pose_link_builder_bench import inspect
from engine.pose_link_feedback import write_pose_link_feedback


def data():
    return bytearray(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1))


class PrimarySolverTests(unittest.TestCase):
    def row(self,bias=-2):
        r=bytearray(160);struct.pack_into('<4f',r,0x10,*([bias]*4));struct.pack_into('<4f',r,0x20,1,0,0,0)
        return r

    def test_prepare_and_iterate_apply_result_delta(self):
        row=self.row();state={0:bytearray(32)};results={0:bytearray(struct.pack('<4f',1,1,1,1))}
        args=dict(body_data={0:data()},body_state=state,results=results)
        prepare_pose_primary_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',state[0])[0],1)
        self.assertEqual(struct.unpack_from('<4f',row,0x40),(-1,)*4)
        iterate_pose_primary_row(row,**args)
        self.assertEqual(struct.unpack('<4f',results[0]),(2,)*4)
        self.assertEqual(struct.unpack_from('<f',state[0])[0],2)
        iterate_pose_primary_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',state[0])[0],2)

    def test_clamp_and_optional_accumulation(self):
        for bias,expected in ((2,0),(-2,2)):
            row=self.row(bias);struct.pack_into('<Q',row,0x50,8)
            struct.pack_into('<4f',row,128,5,5,5,5)
            args=dict(body_data={0:data()},body_state={0:bytearray(32)},results={0:bytearray(16)})
            prepare_pose_primary_row(row,**args);iterate_pose_primary_row(row,**args)
            self.assertEqual(struct.unpack('<4f',args['results'][0]),(expected,)*4)
            self.assertEqual(struct.unpack_from('<4f',row,128),(5+expected,)*4)

    def test_builder_primary_solve_and_feedback(self):
        fixture=Path(__file__).resolve().parents[1]/'engine/examples/pose_link_builder.json'
        document=json.loads(fixture.read_text());p=bytearray.fromhex(document['inputs']['payload_hex'])
        struct.pack_into('<f',p,0x38,-2);document['inputs']['payload_hex']=p.hex()
        output=inspect(document);row=bytearray.fromhex(output['primary_rows_hex'][0])
        results=[bytearray.fromhex(v) for v in output['result_rows_hex']]
        args=dict(body_data={7:data()},body_state={7:bytearray(32)},results=results)
        prepare_pose_primary_row(row,**args);iterate_pose_primary_row(row,**args)
        self.assertEqual(struct.unpack('<4f',results[0]),(2,)*4)
        payload=bytearray.fromhex(output['payload_hex'])
        write_pose_link_feedback(dict(flags38=0x20000000,result_rows=results),[1],
            links={1:dict(flags84=1,payload_count=1,payload_slots=[2])},payloads={2:payload})
        self.assertEqual(struct.unpack_from('<f',payload,0x40)[0],2)

    def test_singular_denominator_is_not_repaired(self):
        row=bytearray(112)
        with self.assertRaises(ValueError):prepare_pose_primary_row(row,body_data={0:data()},body_state={0:bytearray(32)},results={0:bytearray(16)})
