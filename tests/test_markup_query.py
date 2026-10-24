import unittest
from engine.markup_query import candidate_eligible, selector_matches, query_markup


class MarkupQueryTests(unittest.TestCase):
    def test_interval_boundaries_and_unordered(self):
        self.assertTrue(candidate_eligible(3,0x7f7fffff,0,3))
        self.assertFalse(candidate_eligible(3,0x7f800000,0,3))
        self.assertFalse(candidate_eligible(3,0,0xbf800000,3))
        self.assertTrue(candidate_eligible(3,0x7fc00001,0x7fc00001,3))
        self.assertFalse(candidate_eligible(4,0,0,3))

    def test_selector_modes_include_empty(self):
        self.assertTrue(selector_matches(0xffffffff,[]))
        self.assertTrue(selector_matches(0,[]))
        self.assertTrue(selector_matches(0,[0,0]))
        self.assertFalse(selector_matches(0,[0,1]))
        self.assertTrue(selector_matches(7,[3,7]))
        self.assertFalse(selector_matches(7,[]))

    def test_collection_order_and_first_match(self):
        rows=[(4,0,0,2),(3,0,0,0),(3,0,0,2),(3,0,0,2)]
        calls=[]
        def collect(i):calls.append(i);return [i]
        self.assertEqual(query_markup(rows,3,3,collect),3)
        self.assertEqual(calls,[2,3])
        calls.clear()
        self.assertEqual(query_markup(rows,3,0xffffffff,collect),2)
        self.assertEqual(calls,[2])

    def test_invalid_input(self):
        with self.assertRaises(ValueError):selector_matches(-1,[])
        with self.assertRaises(ValueError):candidate_eligible(0,True,0,0)
        with self.assertRaises(ValueError):query_markup([(0,0,0,2)]*4097,0,0,lambda i:[])
