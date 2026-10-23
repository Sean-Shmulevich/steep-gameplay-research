import unittest
from engine.command_compact_set import compact_command_insert

class CompactCommandSetTests(unittest.TestCase):
    def test_numeric_order_not_submission_order(self):
        keys=[]
        for key in (30,10,20,10):keys=compact_command_insert(keys,key)['keys']
        self.assertEqual(keys,[10,20,30])
        self.assertEqual(compact_command_insert(keys,20)['result'],0)

    def test_unsigned_extremes_and_promotion_boundary(self):
        self.assertEqual(compact_command_insert([0,2**64-1],2**63)['keys'],[0,2**63,2**64-1])
        keys=list(range(31));self.assertFalse(compact_command_insert(keys,15)['inserted'])
        with self.assertRaises(ValueError):compact_command_insert(keys,40)

    def test_rejects_invalid_existing_set(self):
        for keys,key in [([2,1],3),([1,1],2),([],True),([],-1),([],2**64)]:
            with self.assertRaises(ValueError):compact_command_insert(keys,key)

    def test_iteration_first_next_and_exhausted_cursor(self):
        from engine.command_compact_set import compact_command_seek as seek
        self.assertEqual(seek([0,10,20],0),dict(result=1,cursor=0))
        self.assertEqual(seek([0,10,20],0,advance=True),dict(result=1,cursor=10))
        self.assertEqual(seek([10,20],20,advance=True),dict(result=0,cursor=21))
        self.assertEqual(seek([2**64-1],2**64-1,advance=True),dict(result=0,cursor=0))
        self.assertEqual(seek([],42,advance=True),dict(result=0,cursor=42))

    def test_serial_set_changes_are_not_snapshot_iteration(self):
        from engine.command_compact_set import compact_command_seek as seek
        self.assertEqual(seek([10,15,20,25,30],20,advance=True),dict(result=1,cursor=25))
        self.assertEqual(seek([10,15,25,30],20,advance=True),dict(result=1,cursor=25))
