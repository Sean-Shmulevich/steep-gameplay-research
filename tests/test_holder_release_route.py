import unittest
from engine.holder_release_route import holder_release_route

class HolderReleaseRouteTests(unittest.TestCase):
    def route(self, status, **kw):
        args=dict(payload_present=True,global_suppress=False,manager_mode=0,thread_kind=3)
        args.update(kw)
        return holder_release_route(status, **args)

    def test_gate_precedence(self):
        for status in (1,0xffffff,1<<26,(1<<26)|(1<<27)):
            self.assertEqual(self.route(status,payload_present=False)['route'],'no_action')
        self.assertEqual(self.route(1<<24)['route'],'no_action')
        self.assertEqual(self.route(1<<24,payload_present=False)['route'],'cleanup_helper')
        self.assertEqual(self.route(1<<27)['route'],'cleanup_helper')
        self.assertEqual(self.route(0,global_suppress=True)['route'],'cleanup_helper')

    def test_enqueue_preserves_flags_and_post_unlock_condition(self):
        for mode in (0,1,2):
            for thread in (0,3,4):
                result=self.route(0x80000000,manager_mode=mode,thread_kind=thread)
                self.assertEqual(result['route'],'enqueue')
                self.assertEqual(result['status'],0x81000000)
                self.assertEqual(result['post_unlock_service'],mode==1 and thread!=3)

    def test_invalid_inputs(self):
        for status in (-1,2**32,True):
            with self.assertRaises(ValueError):self.route(status)
        with self.assertRaises(ValueError):self.route(0,payload_present=1)
