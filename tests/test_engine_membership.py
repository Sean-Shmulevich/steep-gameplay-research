import unittest
from engine.membership import copy_registered_receivers


class MembershipTests(unittest.TestCase):
    def test_empty_retains_previous_batch(self):
        batch=['previous-player']
        d=copy_registered_receivers([],batch)
        self.assertEqual(batch,['previous-player'])
        self.assertTrue(d['retained_on_empty'])
        self.assertEqual(d['source_count'],0)
        self.assertFalse(d['request_epoch_established'])
        self.assertFalse(d['receiver_lifetime_established'])

    def test_explicit_outer_reset_then_empty(self):
        batch=['previous-player']
        batch.clear()
        copy_registered_receivers([],batch)
        self.assertEqual(batch,[])

    def test_nonempty_replaces_preserving_order_and_duplicates(self):
        batch=['previous-player']
        d=copy_registered_receivers(['b','a','b'],batch)
        self.assertEqual(batch,['b','a','b'])
        self.assertFalse(d['retained_on_empty'])
        self.assertEqual(d['source_count'],3)

    def test_source_list_and_destination_are_independent(self):
        source=[3,2,1]; batch=[]
        copy_registered_receivers(source,batch)
        source.clear()
        self.assertEqual(batch,[3,2,1])
        batch.append(4)
        self.assertEqual(source,[])

    def test_aliasing_source_preserves_entries(self):
        source=[1,2]
        copy_registered_receivers(source,source)
        self.assertEqual(source,[1,2])

    def test_mutable_receiver_and_bad_container_rejected(self):
        with self.assertRaises(ValueError):copy_registered_receivers([{}],[])
        with self.assertRaises(ValueError):copy_registered_receivers(iter([1]),[])
        with self.assertRaises(ValueError):copy_registered_receivers([],())


if __name__=='__main__':unittest.main()
