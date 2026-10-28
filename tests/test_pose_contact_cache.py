import struct
import unittest
from engine.pose_contact_cache import clear_contact_pair,remove_pair_payload


def row(a,b,detail,identity):
    return struct.pack('<HHIQ',a,b,detail,identity)


class ContactCacheTest(unittest.TestCase):
    def test_removes_all_details_in_reverse_order_preserving_payload_tails(self):
        rows=[row(1,2,7,10),row(3,2,0,30),row(1,2,9,20)]
        cache={'count':3,'slots':rows.copy()}
        payloads={p:bytearray(b'X'*288) for p in (10,20,30)}
        recycled={'count':0,'capacity':0,'slots':[]}
        self.assertEqual(clear_contact_pair(cache,1,2,recycled,payloads=payloads),2)
        self.assertEqual(cache['count'],1);self.assertEqual(cache['slots'],[rows[1],rows[1],rows[2]])
        self.assertEqual(recycled,{'count':2,'capacity':8,'slots':[20,10,0,0,0,0,0,0]})
        for p in (10,20):
            self.assertEqual(payloads[p],b'X'*272+bytes(4)+b'X'*12)
        self.assertEqual(payloads[30],b'X'*288)

    def test_removed_null_stops_loop_without_resetting_other_matches(self):
        cache={'count':2,'slots':[row(1,2,1,10),row(1,2,2,0)]}
        recycle={'count':0,'capacity':0,'slots':[]}
        self.assertEqual(clear_contact_pair(cache,1,2,recycle,payloads={}),0)
        self.assertEqual(cache['count'],1);self.assertEqual(recycle['capacity'],0)

    def test_keys_are_not_silently_truncated(self):
        cache={'count':1,'slots':[row(1,2,0,10)]}
        self.assertEqual(remove_pair_payload(cache,65537,2),0)
        self.assertEqual(cache['count'],1)


class ContactAcquireTest(unittest.TestCase):
    def test_hit_is_first_match_and_has_no_mutation(self):
        from engine.pose_contact_cache import acquire_recycled_contact_payload
        cache={'count':2,'slots':[row(1,2,3,10),row(1,2,3,20)]}
        def forbidden(*args):raise AssertionError('service called on hit')
        result=acquire_recycled_contact_payload(cache,65537,2,3,{},owner=99,
            payloads={},supply_batch=forbidden,append_entry=forbidden)
        self.assertEqual(result,10)

    def test_refill_ten_pop_last_then_reuse_without_reset(self):
        from engine.pose_contact_cache import acquire_recycled_contact_payload
        cache={'count':0,'slots':[]};recycle={'count':0,'capacity':8,'slots':[88]*8}
        payloads={i:bytearray(b'X'*288) for i in range(1,11)};calls=[]
        def batch(n):calls.append(n);return list(range(1,11))
        def append(c,a,b,d,p):c['slots'].append(row(a,b,d,p));c['count']+=1
        for detail,expected in ((4,10),(5,9)):
            self.assertEqual(acquire_recycled_contact_payload(cache,1,2,detail,recycle,
                owner=99,payloads=payloads,supply_batch=batch,append_entry=append),expected)
            self.assertEqual(payloads[expected],struct.pack('<Q',99)+b'X'*280)
        self.assertEqual(calls,[10]);self.assertEqual(recycle['capacity'],16)
        self.assertEqual(recycle['count'],8);self.assertEqual(recycle['slots'][:10],list(range(1,11)))
