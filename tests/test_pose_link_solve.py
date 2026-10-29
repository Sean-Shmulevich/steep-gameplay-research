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

    def test_populated_paired_pool_without_storage_fails_explicitly(self):
        c,args=self.fixture();struct.pack_into('<I',c,0x10c,1)
        with self.assertRaises(ValueError):solve_pose_link_rows(c,**args)

    def command_fixture(self,flags):
        c=bytearray(0x190);struct.pack_into('<I',c,0x38,flags);struct.pack_into('<I',c,0x168,1)
        row=bytearray(912);struct.pack_into('<i',row,0x24,1);row[0x20]=1
        struct.pack_into('<4f',row,0x30,1,0,0,0)
        for off,val in [(0x70,2),(0x80,-1),(0x90,1),(0xa0,.25)]:struct.pack_into('<4f',row,off,*([val]*4))
        data=bytearray(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1))
        args=dict(base_token=0,primary_rows=[],secondary_rows=[],command_rows=[row],
                  body_data=[data],body_state=[bytearray(32)],results=[])
        return c,args

    def test_command_normal_phase_updates_body_without_result_array(self):
        c,args=self.command_fixture(4)
        solve_pose_link_rows(c,**args)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],1)
        self.assertEqual(struct.unpack_from('<f',args['command_rows'][0],0xa0)[0],1)

    def test_special_phase_preserves_command_row_and_body(self):
        c,args=self.command_fixture(0x10030000)
        row=bytes(args['command_rows'][0]);state=bytes(args['body_state'][0])
        solve_pose_link_rows(c,**args)
        self.assertEqual(bytes(args['command_rows'][0]),row)
        self.assertEqual(bytes(args['body_state'][0]),state)

    def test_command_append_count_does_not_drive_traversal(self):
        c,args=self.command_fixture(4)
        struct.pack_into('<I',c,0x168,0);struct.pack_into('<I',c,0x104,1)
        solve_pose_link_rows(c,**args)
        self.assertEqual(bytes(args['body_state'][0]),bytes(32))

    def test_constraint_primary_reuses_formula_but_obeys_special_gate(self):
        for flags,expected in [(12,(10,0,-2)),(0x10030000,(10,0,0))]:
            c,args=self.fixture(flags)
            struct.pack_into('<I',c,0x108,0);struct.pack_into('<I',c,0x120,0)
            struct.pack_into('<I',c,0x128,1)
            args['constraint_primary_rows']=args['primary_rows'];args['primary_rows']=[]
            before=bytes(args['constraint_primary_rows'][0])
            solve_pose_link_rows(c,**args)
            self.assertEqual(struct.unpack_from('<3f',args['body_state'][7]),expected)
            if flags==0x10030000:self.assertEqual(bytes(args['constraint_primary_rows'][0]),before)

    def test_missing_constraint_primary_storage_is_explicit(self):
        c,args=self.fixture();struct.pack_into('<I',c,0x12c,1)
        with self.assertRaisesRegex(ValueError,'constraint primary'):
            solve_pose_link_rows(c,**args)

    def test_late_primary_categories_normal_only(self):
        for flags,expected in [(12,(10,0,-2)),(0x10030000,(10,0,0))]:
            c,args=self.fixture(flags)
            struct.pack_into('<I',c,0x108,0);struct.pack_into('<I',c,0x120,0)
            struct.pack_into('<I',c,0x110,1)
            args['late_primary_rows']=args['primary_rows'];args['primary_rows']=[]
            before=bytes(args['late_primary_rows'][0])
            solve_pose_link_rows(c,**args)
            self.assertEqual(struct.unpack_from('<3f',args['body_state'][7]),expected)
            if flags==0x10030000:self.assertEqual(bytes(args['late_primary_rows'][0]),before)

    def test_late_paired_storage_is_required(self):
        c,args=self.fixture();struct.pack_into('<I',c,0x114,1)
        with self.assertRaisesRegex(ValueError,'late primary'):
            solve_pose_link_rows(c,**args)
