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
