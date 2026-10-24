import json
from pathlib import Path
import struct
import unittest
from engine.pose_tangent_solver import prepare_pose_tangent_row,iterate_pose_tangent_row
from engine.pose_primary_solver import prepare_pose_primary_row,iterate_pose_primary_row
from engine.pose_link_builder_bench import inspect


def data():return bytearray(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1))

class TangentSolverTests(unittest.TestCase):
    def fixture(self,primary=2):
        row=bytearray(112);struct.pack_into('<I',row,4,1)
        struct.pack_into('<4f',row,0x20,1,0,0,0);struct.pack_into('<4f',row,0x60,.5,.5,.5,.5)
        args=dict(body_data={0:data()},body_state={0:bytearray(struct.pack('<8f',10,0,0,0,0,0,0,0))},
                  results={0:bytearray(struct.pack('<4f',*([primary]*4))),1:bytearray(16)})
        return row,args

    def test_primary_bound_and_opposite_increment_reduce_motion(self):
        row,args=self.fixture();prepare_pose_tangent_row(row,**args)
        self.assertEqual(struct.unpack_from('<4f',row,0x40),(-1,)*4)
        iterate_pose_tangent_row(row,**args)
        self.assertEqual(struct.unpack('<4f',args['results'][1]),(1,)*4)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],9)
        args['results'][0][:]=struct.pack('<4f',4,4,4,4)
        iterate_pose_tangent_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],8)

    def test_inverted_bounds_are_not_reordered(self):
        row,args=self.fixture(-2);prepare_pose_tangent_row(row,**args);iterate_pose_tangent_row(row,**args)
        self.assertEqual(struct.unpack('<4f',args['results'][1]),(1,)*4)

    def test_response_field_is_not_consumed(self):
        row,args=self.fixture();struct.pack_into('<4f',row,0x10,100,200,300,400)
        prepare_pose_tangent_row(row,**args);iterate_pose_tangent_row(row,**args)
        self.assertEqual(struct.unpack('<4f',args['results'][1]),(1,)*4)

    def test_builder_triplet_with_primary_and_both_tangents(self):
        fixture=Path(__file__).resolve().parents[1]/'engine/examples/pose_link_builder.json'
        document=json.loads(fixture.read_text());payload=bytearray.fromhex(document['inputs']['payload_hex'])
        struct.pack_into('<f',payload,0x38,-2);document['inputs']['payload_hex']=payload.hex()
        out=inspect(document);primary=bytearray.fromhex(out['primary_rows_hex'][0]);tangents=[bytearray.fromhex(x) for x in out['secondary_rows_hex']]
        args=dict(body_data={7:data()},body_state={7:bytearray(struct.pack('<8f',10,0,0,0,0,0,0,0))},results=[bytearray.fromhex(x) for x in out['result_rows_hex']])
        prepare_pose_primary_row(primary,**args)
        for row in tangents:prepare_pose_tangent_row(row,**args)
        for _ in range(3):
            iterate_pose_primary_row(primary,**args)
            for row in tangents:iterate_pose_tangent_row(row,**args)
        self.assertEqual(struct.unpack_from('<3f',args['body_state'][7]),(9,0,-2))
        self.assertEqual(struct.unpack('<4f',args['results'][0]),(2,)*4)
        self.assertEqual(struct.unpack('<4f',args['results'][1]),(-1,)*4)
