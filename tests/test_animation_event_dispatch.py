import unittest
from engine.animation_event_dispatch import plan_event_dispatch

class AnimationEventDispatchTests(unittest.TestCase):
    def test_order_and_independent_handle_validity(self):
        rows=[(9,(11,0x80000000),(12,0)), (8,(21,1),(22,0xffffffff))]
        self.assertEqual(plan_event_dispatch(rows),[
            dict(event=9,first=11,second=0,extra=0),
            dict(event=8,first=0,second=22,extra=0)])
        self.assertEqual(rows[0][1],(11,0x80000000))

    def test_suppression_and_null_event_skip_handle_access(self):
        self.assertEqual(plan_event_dispatch([(1,None,None)],suppress=True),[])
        self.assertEqual(plan_event_dispatch([(0,None,None)]),[])
        self.assertEqual(plan_event_dispatch([]),[])

    def test_invalid_count_and_status(self):
        with self.assertRaises(ValueError):plan_event_dispatch([(1,(2,-1),(3,0))])
        with self.assertRaises(ValueError):plan_event_dispatch([],suppress=1)
        with self.assertRaises(ValueError):plan_event_dispatch([(0,None,None)]*65536)
