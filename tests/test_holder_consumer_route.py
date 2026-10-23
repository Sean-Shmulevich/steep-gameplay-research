import unittest
from engine.holder_consumer_route import holder_consumer_route

class HolderConsumerTests(unittest.TestCase):
    def test_reacquired_count_skips_payload_and_cleanup(self):
        r=holder_consumer_route(0x81000001,payload_present=True,manager_mode=1)
        self.assertEqual(r,dict(status=0x80000001,events=['clear_queued_bit']))

    def test_zero_count_routes(self):
        for mode in (0,1,2):
            r=holder_consumer_route(0x81000000,payload_present=True,manager_mode=mode)
            self.assertEqual(r['events'],['payload_virtual48','dispatch_payload' if mode==0 else 'append_output','clear_queued_bit','cleanup_holder'])
        r=holder_consumer_route(0x01000000,payload_present=False,manager_mode=0)
        self.assertEqual(r['events'],['clear_queued_bit','cleanup_holder'])

    def test_invalid_fields(self):
        for status in (-1,2**32,True):
            with self.assertRaises(ValueError):holder_consumer_route(status,payload_present=True,manager_mode=0)
