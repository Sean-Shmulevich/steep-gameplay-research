import unittest
from engine.markup_notification import advance_markup_record as step

class MarkupNotificationTests(unittest.TestCase):
    def test_change_and_forced_repeat(self):
        self.assertTrue(step(1,0,1,0,-1)['notify'])
        self.assertTrue(step(1,1,0,0,-1)['notify'])
        self.assertFalse(step(1,1,1,0,4)['notify'])
        self.assertFalse(step(1,1,1,1,-1)['notify'])
        first=step(1,1,1,1,4)
        self.assertTrue(first['notify'])
        self.assertFalse(step(1,first['previous_value'],1,1,first['pending_index'])['notify'])

    def test_unlinked_preserves_pending_and_cache(self):
        for n in (0,-1,-2**31):
            self.assertEqual(step(n,2,None,255,4),dict(evaluated=False,notify=False,previous_value=2,pending_index=4))
        self.assertTrue(step(1,2,1,0,-1)['notify'])
        self.assertEqual(step(1,0,255,0,-1)['previous_value'],255)

    def test_validation(self):
        for args in [(True,0,0,0,-1),(1,0,None,0,-1),(1,256,0,0,-1),(1,0,0,0,2**31)]:
            with self.assertRaises(ValueError):step(*args)
