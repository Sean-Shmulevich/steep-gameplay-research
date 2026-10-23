import unittest
from engine.command_record_cleanup import cleanup_record


class RecordCleanupTests(unittest.TestCase):
    def test_order_and_detach_before_destruction(self):
        a={'count':1}; h1={'status':0x1000001}; h2={'status':1}
        r=dict(associated=a,invoker='invoker',holder_10=h1,holder_08=h2)
        events=[]
        def destroy(obj):
            self.assertIsNone(r['associated']); self.assertEqual(r['invoker'],'invoker')
            events.append('associated')
        def release(obj):
            self.assertIsNone(r['invoker']); events.append('10' if obj is h1 else '08')
        cleanup_record(r,destroy_associated=destroy,release_holder=release)
        self.assertEqual(events,['associated','10','08'])
        self.assertEqual(h1['status'],0x1000000)
        self.assertIs(r['holder_10'],h1)

    def test_aliases_are_decremented_twice(self):
        h={'status':2}; r=dict(associated=None,invoker=123,holder_10=h,holder_08=h)
        events=[]
        cleanup_record(r,destroy_associated=lambda _:self.fail(),release_holder=lambda x:events.append(x['status']))
        self.assertEqual(events,[0]); self.assertEqual(h['status'],0)

    def test_associated_uses_full_count_but_holder_uses_low_24_bits(self):
        a={'count':0x1000001}; h={'status':0}
        r=dict(associated=a,invoker=123,holder_10=h,holder_08=h)
        cleanup_record(r,destroy_associated=lambda _:self.fail(),release_holder=lambda _:self.fail())
        self.assertEqual(a['count'],0x1000000)
        self.assertEqual(h['status'],0xfffffffe)

    def test_composes_with_buffer_disposal_without_invocation(self):
        from engine.command_disposal import release_buffer
        h={'status':2}; r=dict(associated={'count':1},invoker='never-called',holder_10=h,holder_08=h)
        ring=dict(storage=[r],capacity=1,count=1,read=0,write=0,owns_storage=True)
        events=[]
        def cleanup(storage,index):
            cleanup_record(storage[index],destroy_associated=lambda _:events.append('destroy'),
                           release_holder=lambda _:events.append('holder'))
        def free(storage,info):
            self.assertEqual(info,'info'); events.append('free')
        release_buffer(ring,cleanup=cleanup,allocation_lookup=lambda _:'info',free=free)
        self.assertEqual(events,['destroy','holder','free'])
        self.assertIsNone(r['invoker']); self.assertEqual(ring['count'],0)
