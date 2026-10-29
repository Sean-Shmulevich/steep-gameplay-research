import struct
import unittest
from engine.pose_constraint_build import build_pose_constraints


class ConstraintDispatchTests(unittest.TestCase):
    def fixture(self):
        c=bytearray(0x1000);struct.pack_into('<I',c,0x16c,0x400)
        constraints={1:bytearray(0x78),2:bytearray(0x78)}
        for r in constraints.values():
            struct.pack_into('<2Q',r,8,10,0)
        bodies={10:bytearray(0x40),20:bytearray(0x40)}
        for t,b in bodies.items():struct.pack_into('<Q',b,0x30,t)
        return c,dict(constraints=constraints,bodies=bodies,metadata={10:bytearray(0x60),20:bytearray(0x60)})

    def test_eligibility_precedes_virtual_kind(self):
        for first,second in ((1,0),(0,1)):
            c,args=self.fixture()
            struct.pack_into('<Q',args['constraints'][1],16,20)
            args['metadata'][10][0x52]=first;args['metadata'][20][0x52]=second
            calls=[];before=bytes(c)
            build_pose_constraints(c,[1],get_kind=lambda t:calls.append(t) or 4,**args)
            self.assertEqual(calls,[]);self.assertEqual(bytes(c),before)

    def test_command_accepts_absent_second_body(self):
        c,args=self.fixture()
        build_pose_constraints(c,[1,2],get_kind=lambda t:4,**args)
        self.assertEqual(struct.unpack_from('<I',c,0x104)[0],2)
        self.assertEqual(struct.unpack_from('<I',c,0x180)[0],2)

    def test_unknown_kind_skips_without_mutation(self):
        for kind in (0,7,0xffffffff):
            c,args=self.fixture();before=bytes(c)
            build_pose_constraints(c,[1],get_kind=lambda t:kind,**args)
            self.assertEqual(bytes(c),before)

    def test_missing_builder_is_explicit(self):
        for kind in (2,5):
            c,args=self.fixture()
            with self.assertRaisesRegex(ValueError,f'Kind{kind}'):
                build_pose_constraints(c,[1],get_kind=lambda t:kind,**args)

    def test_kind_service_does_not_reload_current_slot(self):
        c,args=self.fixture();slots=[1,2];calls=[]
        def kind(token):
            slots[0]=2
            return 2
        build_pose_constraints(c,slots,get_kind=kind,additional_builders={2:lambda c,t:calls.append(t)},**args)
        self.assertEqual(calls,[1,2])

    def test_kind3_needs_math_service(self):
        c,args=self.fixture()
        with self.assertRaisesRegex(ValueError,'atan2'):
            build_pose_constraints(c,[1],get_kind=lambda t:3,**args)
