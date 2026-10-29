import struct
import unittest
from engine.pose_constraint_feedback import feedback_pose_constraints, UNBOUNDED_THRESHOLD


class ConstraintFeedbackTests(unittest.TestCase):
    def fixture(self):
        context=bytearray(0x240);struct.pack_into('<I',context,0x178,0x200)
        struct.pack_into('<4I',context,0x200,0x80000000,0x7fc12345,0x3f800000,0)
        struct.pack_into('<f',context,0x210,9)
        record=bytearray(0x1b0);struct.pack_into('<2Q',record,8,2,0)
        struct.pack_into('<3I',record,0x190,0,1,0xffffffff)
        for off in (0xfc,0x110,0x124):struct.pack_into('<f',record,off,UNBOUNDED_THRESHOLD)
        body=bytearray(0x40);struct.pack_into('<Q',body,0x30,3)
        metadata=bytearray(0x60)
        args=dict(constraints={1:record},bodies={2:body},metadata={3:metadata},get_kind=lambda t:2)
        return context,record,metadata,args

    def test_packed_preserves_result_bits(self):
        c,r,m,args=self.fixture()
        feedback_pose_constraints(c,[1],**args)
        self.assertEqual(r[0x19c:0x1a8],c[0x200:0x20c])

    def test_negative_zero_mode_word_selects_scalar_and_missing_preserves(self):
        c,r,m,args=self.fixture()
        struct.pack_into('<I',r,0xf0,0x80000000)
        r[0x1a4:0x1a8]=b'keep'
        feedback_pose_constraints(c,[1],**args)
        self.assertEqual(r[0x19c:0x1a0],c[0x200:0x204])
        self.assertEqual(struct.unpack_from('<f',r,0x1a0)[0],9)
        self.assertEqual(r[0x1a4:0x1a8],b'keep')

    def test_disabled_endpoint_skips_type_query(self):
        c,r,m,args=self.fixture();m[0x52]=1;before=bytes(r)
        args['get_kind']=lambda t:self.fail('disabled constraint queried')
        feedback_pose_constraints(c,[1],**args)
        self.assertEqual(bytes(r),before)

    def test_slot_reloaded_after_type_query(self):
        c,r,m,args=self.fixture();slots=[1];replacement=bytearray(r)
        args['constraints'][4]=replacement
        def kind(t):slots[0]=4;return 2
        args['get_kind']=kind
        feedback_pose_constraints(c,slots,**args)
        self.assertEqual(replacement[0x19c:0x1a8],c[0x200:0x20c])
        self.assertEqual(r[0x19c:0x1a8],bytes(12))
