import unittest
from engine.action_device_poll import poll_device_cache

class DevicePollTests(unittest.TestCase):
    def test_missing_device_retains_keyboard_tail(self):
        r=poll_device_cache(bytes([7])*256,packet=False,device_present=False,get_state=None,acquire=None)
        self.assertEqual(r['buffer'],bytes(8)+bytes([7])*248);self.assertFalse(r['success'])
        r=poll_device_cache(bytes([7])*20,packet=True,device_present=False,get_state=None,acquire=None)
        self.assertEqual(r['buffer'],bytes(20))
    def test_failed_partial_write_survives_without_repoll(self):
        calls=[];results=iter((0x8007001e,0))
        def get(data):calls.append('get');data[40]=128;return 0x80004005
        def acquire():calls.append('acquire');return next(results)
        r=poll_device_cache(bytes(256),packet=False,device_present=True,get_state=get,acquire=acquire)
        self.assertEqual(calls,['get','acquire','acquire']);self.assertFalse(r['success'])
        self.assertEqual(r['buffer'][40],128)
    def test_success_and_bound(self):
        def get(data):data[:]=bytes([1])*len(data);return 1
        self.assertTrue(poll_device_cache(bytes(20),packet=True,device_present=True,get_state=get,acquire=None)['success'])
        with self.assertRaisesRegex(ValueError,'limit'):
            poll_device_cache(bytes(20),packet=True,device_present=True,get_state=lambda _:0x80000000,acquire=lambda:0x8007001e,maximum_acquire_calls=2)
