import json
import unittest
from tests import test_player_animation_observation as fixtures
from engine.player_animation_observation import capture_player_cached_parent


class PlayerCachedParentObservationTests(unittest.TestCase):
    setUp=fixtures.PlayerAnimationObservationTests.setUp
    write=fixtures.PlayerAnimationObservationTests.write
    put=fixtures.PlayerAnimationObservationTests.put
    read=fixtures.PlayerAnimationObservationTests.read
    def capture(self,read=None):
        return capture_player_cached_parent(read or self.read,self.entity,self.base,[self.guard],self.profile)
    def test_binding_and_empty_callback(self):
        result=self.capture()
        self.assertEqual(result['binding']['binding_status'],'unique_exact_type')
        self.assertFalse(result['cached_parent']['callback_eligible'])
        self.assertFalse(result['suitable_for_animation_writes'])
        self.assertNotIn(str(self.component),json.dumps(result))
    def test_slot_replacement_during_callback_read_rejected(self):
        def changing(plan):
            result=self.read(plan)
            if (self.component+0x290,40) in plan:self.put(self.base+0x3000,'<Q',self.component+0x100)
            return result
        with self.assertRaises(ValueError):self.capture(changing)
    def test_owner_mismatch_prevents_callback_read(self):
        self.put(self.component+0x10,'<Q',self.entity+8)
        with self.assertRaises(ValueError):self.capture()
        self.assertNotIn((self.component+0x290,40),self.requests)
    def test_external_guard_change_rejected(self):
        def changing(plan):
            result=self.read(plan)
            if (self.component+0x130,32) in plan:self.write(self.guard[0],b'changed!')
            return result
        with self.assertRaises(ValueError):self.capture(changing)
    def test_short_read_rejected(self):
        with self.assertRaises(ValueError):self.capture(lambda plan:[])
