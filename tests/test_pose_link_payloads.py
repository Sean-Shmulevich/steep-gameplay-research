import unittest
from engine.pose_link_payloads import clear_pose_link_payloads


class PayloadTests(unittest.TestCase):
    def test_release_skips_null_and_preserves_inactive_entries(self):
        s=dict(count=3,slots=[dict(key=i,payload=p) for i,p in enumerate([10,0,20,30])])
        before=[x.copy() for x in s['slots']];calls=[]
        clear_pose_link_payloads(s,None,payloads={},release=calls.append,grow=None)
        self.assertEqual(calls,[10,20]);self.assertEqual(s['count'],0)
        self.assertEqual(s['slots'],before)

    def test_transfer_resets_before_growth_and_keeps_duplicates(self):
        s=dict(count=2,slots=[dict(key=1,payload=10),dict(key=2,payload=10)])
        d=dict(count=0,capacity=0,slots=[]);payloads={10:dict(count110=7)};events=[]
        def grow(d,n):
            events.append((n,payloads[10]['count110']))
            d['slots']=[0]*n;d['capacity']=n
        clear_pose_link_payloads(s,d,payloads=payloads,release=lambda t:self.fail(),grow=grow)
        self.assertEqual(events,[(8,0)]);self.assertEqual(d['slots'][:2],[10,10])
        self.assertEqual((s['count'],d['count']),(0,2))

    def test_captured_source_array_and_extent_with_mutated_future_slot(self):
        s=dict(count=2,slots=[dict(key=0,payload=10),dict(key=0,payload=20)])
        original=s['slots'];calls=[]
        def release(t):
            calls.append(t)
            if t==10:
                s['count']=0;s['slots']=[];original[1]['payload']=30
        clear_pose_link_payloads(s,None,payloads={},release=release,grow=None)
        self.assertEqual(calls,[10,30])

    def test_failure_does_not_clear_source_count(self):
        s=dict(count=1,slots=[dict(key=0,payload=10)])
        def release(t):raise RuntimeError('external service failed')
        with self.assertRaises(RuntimeError):
            clear_pose_link_payloads(s,None,payloads={},release=release,grow=None)
        self.assertEqual(s['count'],1)
