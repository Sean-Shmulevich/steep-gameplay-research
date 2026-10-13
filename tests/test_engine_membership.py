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




class RangeClaimTests(unittest.TestCase):
    def test_tail_consumption_and_reverse_visit(self):
        from engine.membership import claim_range
        remaining=10;visits=[];counts=[]
        while (claim:=claim_range(remaining,2,4)) is not None:
            remaining=claim['remaining'];counts.append(claim['count'])
            visits.extend(range(claim['end_exclusive']-1,claim['start']-1,-1))
            self.assertFalse(claim['completion_established'])
        self.assertEqual(counts,[2,2,2,1,1,1,1])
        self.assertEqual(visits,list(reversed(range(10))))
    def test_short_gap_above_tail(self):
        from engine.membership import claim_range
        self.assertEqual(claim_range(5,2,4)['remaining'],4)
        self.assertEqual(claim_range(5,2,4)['count'],1)
    def test_empty_does_not_claim_or_prove_completion(self):
        from engine.membership import claim_range
        self.assertIsNone(claim_range(0))
        last=claim_range(1)
        self.assertEqual(last['remaining'],0)
        self.assertFalse(last['completion_established'])
    def test_setter_differs_from_initial_constructor(self):
        from engine.membership import configured_chunk,claim_range
        self.assertEqual(configured_chunk(0),{'chunk_size':1,'tail_threshold':2})
        self.assertEqual(claim_range(6,**configured_chunk(2))['count'],2)
        for args in ((1,0,0),(-1,1,0),(3,0x7fffffff,1),(True,1,0)):
            with self.assertRaises(ValueError):claim_range(*args)

if __name__=='__main__':unittest.main()
