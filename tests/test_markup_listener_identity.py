import unittest
from engine.markup_listener_identity import same_listener, remove_first_listener

class MarkupListenerIdentityTests(unittest.TestCase):
    def test_identity_ignores_thunk_and_tags(self):
        self.assertTrue(same_listener((1,2,0x1001,3),(1,2,0x1002,99)))
        self.assertFalse(same_listener((1,2,0x1001,3),(1,4,0x1002,3)))
        self.assertFalse(same_listener((1,2,0x1001,3),(1,2,0x2001,3)))
        self.assertFalse(same_listener((1,2,0,3),(1,2,0x1000,3)))
        self.assertTrue(same_listener((1,2,1,3),(1,99,3,77)))
        self.assertFalse(same_listener((1,2,0,3),(2,2,0,3)))

    def test_first_match_swap_last_and_repeat(self):
        a,b,c=(1,0,0x1000,3),(2,0,0x1000,3),(3,0,0x1000,3)
        source=[a,b,a,c]
        result,index=remove_first_listener(source,a)
        self.assertEqual((result,index),([c,b,a],0))
        self.assertEqual(source,[a,b,a,c])
        self.assertEqual(remove_first_listener(result,a),([c,b],2))
        self.assertEqual(remove_first_listener([c,b],a),([c,b],None))
        self.assertEqual(remove_first_listener([a],a),([],0))

    def test_invalid_words(self):
        for bad in [(1,2,3), (1,2,-1,4), (1,2,3,2**64), (True,2,3,4)]:
            with self.assertRaises(ValueError):same_listener(bad,(1,2,3,4))
