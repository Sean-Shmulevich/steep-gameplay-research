import json
from pathlib import Path
import struct
import unittest
from engine.pose_link_builder_bench import inspect
from engine.pose_link_solve import solve_pose_link_rows

class LinkSolveTests(unittest.TestCase):
    def fixture(self,flags=12):
        source=Path(__file__).resolve().parents[1]/'engine/examples/pose_link_builder.json'
        document=json.loads(source.read_text());payload=bytearray.fromhex(document['inputs']['payload_hex'])
        struct.pack_into('<f',payload,0x38,-2);document['inputs']['payload_hex']=payload.hex()
        built=inspect(document);context=bytearray(0x190)
        struct.pack_into('<I',context,0x38,flags);struct.pack_into('<I',context,0x108,1);struct.pack_into('<I',context,0x120,2)
        struct.pack_into('<2I',context,0xc,0x80000000,0x7fc12345)
        args=dict(base_token=0,primary_rows=[bytearray.fromhex(x) for x in built['primary_rows_hex']],
            secondary_rows=[bytearray.fromhex(x) for x in built['secondary_rows_hex']],
            results=[bytearray.fromhex(x) for x in built['result_rows_hex']],
            body_data={7:bytearray(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1))},
            body_state={7:bytearray(struct.pack('<8f',10,0,0,0,0,0,0,0))})
        return context,args

    def test_normal_phase_solves_both_categories(self):
        c,args=self.fixture();solve_pose_link_rows(c,**args)
        self.assertEqual(struct.unpack_from('<3f',args['body_state'][7]),(9,0,-2))
        self.assertEqual(struct.unpack('<4f',args['results'][0]),(2,)*4)

    def test_special_phase_skips_tangents_and_restores_scalars(self):
        c,args=self.fixture(0x10030000);saved=bytes(c[0xc:0x14]);tangents=[bytes(x) for x in args['secondary_rows']]
        solve_pose_link_rows(c,**args)
        self.assertEqual(struct.unpack_from('<3f',args['body_state'][7]),(10,0,-2))
        self.assertEqual([bytes(x) for x in args['secondary_rows']],tangents)
        self.assertEqual(c[0xc:0x14],saved)

    def test_zero_iterations_still_apply_cached_result(self):
        c,args=self.fixture(0);solve_pose_link_rows(c,**args)
        self.assertEqual(struct.unpack_from('<3f',args['body_state'][7]),(10,0,-3))

    def test_traversal_counts_not_inferred_from_built_rows(self):
        c,args=self.fixture();struct.pack_into('<I',c,0x108,0);struct.pack_into('<I',c,0x120,0)
        struct.pack_into('<I',c,0xa4,1);struct.pack_into('<I',c,0xbc,2)
        solve_pose_link_rows(c,**args)
        self.assertEqual(struct.unpack_from('<3f',args['body_state'][7]),(10,0,0))

    def test_unsupported_categories_fail_explicitly(self):
        c,args=self.fixture();struct.pack_into('<I',c,0x10c,1)
        with self.assertRaises(ValueError):solve_pose_link_rows(c,**args)
