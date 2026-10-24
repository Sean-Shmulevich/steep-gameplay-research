import struct
import unittest
from engine.pose_solver_control import run_pose_solver,RESULT_SLOT

class SolverControlTests(unittest.TestCase):
    def context(self,flags):
        c=bytearray(0x190);struct.pack_into('<I',c,0x38,flags)
        struct.pack_into('<2I',c,0xc,0x80000000,0x7fc12345)
        struct.pack_into('<4I',c,0x16c,0x100,0x200,0x300,0x400)
        return c

    def test_special_restores_raw_scalars_and_retains_iteration_cursor(self):
        c=self.context(0x10030000);saved=bytes(c[0xc:0x14]);calls=[]
        def prepare(d,cursor):
            self.assertEqual(c[0xc:0x14],struct.pack('<2f',1,1))
            self.assertEqual(d['results'],0x1400)
            cursor['value']=99
            struct.pack_into('<I',c,0x38,0)
        def iterate(d,cursor):
            calls.append(cursor['value']);cursor['value']=len(calls)
            c[0xc:0x14]=bytes(8)
        run_pose_solver(c,base_token=0x1000,prepare=prepare,iterate=iterate)
        self.assertEqual(calls,[RESULT_SLOT,1,2])
        self.assertEqual(c[0xc:0x14],saved)

    def test_other_phases_do_not_restore_service_writes(self):
        for phase in (0,0x08000000,0x18000000):
            c=self.context(phase|8);calls=[]
            def prepare(d,cursor):
                self.assertFalse(d['special']);c[0xc:0x14]=bytes(8)
            run_pose_solver(c,base_token=0,prepare=prepare,iterate=lambda d,p:calls.append(1))
            self.assertEqual(calls,[1,1]);self.assertEqual(c[0xc:0x14],bytes(8))

    def test_zero_iterations_still_prepares(self):
        c=self.context(0);calls=[]
        run_pose_solver(c,base_token=0,prepare=lambda d,p:calls.append('prepare'),iterate=lambda d,p:self.fail('Unexpected iteration'))
        self.assertEqual(calls,['prepare'])
