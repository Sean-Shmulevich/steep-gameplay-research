import struct
import unittest
from engine.action_root_observation import observe_rooted_action
from tests import test_action_binding_observation as fixtures

class RootObservationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BindingObservationTests()
        self.fixture.setUp()
        self.fixture.q(0xd000, 0x1000)
    def observe(self, read=None):
        return observe_rooted_action(read or self.fixture.read, 0xd000, 0x76, 0xb000)
    def test_current_root_is_used(self):
        self.assertEqual(self.observe().action, 0x8100)
        self.fixture.q(0xd000, 0xe000)
        self.assertEqual(self.observe().status, 'fallback')
    def test_changed_root_discards_valid_candidate(self):
        count = 0
        def read(a,n):
            nonlocal count
            if a == 0xd000:
                count += 1
                if count == 2:
                    return struct.pack('<Q', 0xe000)
            return self.fixture.read(a,n)
        result = self.observe(read)
        self.assertEqual((result.status, result.reason), ('unstable','manager_changed'))
        self.assertEqual((result.action, result.sampled_bits), (0,b''))
    def test_missing_root_and_short_final_read(self):
        self.fixture.q(0xd000,0)
        self.assertEqual(self.observe().reason,'manager_not_published')
        self.fixture.q(0xd000,0x1000)
        count=0
        def read(a,n):
            nonlocal count
            if a==0xd000:
                count+=1
                if count==2:return b''
            return self.fixture.read(a,n)
        self.assertEqual(self.observe(read).status,'invalid')
