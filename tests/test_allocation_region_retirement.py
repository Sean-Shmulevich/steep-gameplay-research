import unittest
from engine.allocation_region_retirement import retire_metadata_regions


class RegionRetirementTests(unittest.TestCase):
    def run_scan(self, tables, *, mutate=False, override=False):
        events=[];record=dict(index=3,field10=77)
        registry=dict(regions=tables,override=None)
        def callback(address,size,reason,r,context):
            self.assertEqual(reason,2);self.assertEqual(r['field10'],77)
            events.append((address,size,context))
            if mutate:r['index']=4
        if override:registry['override']=callback
        result=retire_metadata_regions(registry,record,'context',
            lock=lambda _:events.append('lock'),unlock=lambda _:events.append('unlock'),
            ensure_initialized=lambda:None,address_limit=lambda:len(tables)<<32,
            fallback=lambda _,*args:callback(*args))
        self.assertEqual(record['field10'],0)
        return events,result

    def test_span_checks_owner_only_at_start_and_includes_terminator(self):
        tags=bytearray([255])*65536;tags[2:5]=bytes([3,9,137])
        events,result=self.run_scan({0:tags})
        self.assertEqual(events,['lock',(2<<16,3<<16,'context'),'unlock'])
        self.assertEqual(result['spans_dispatched'],1)
        self.assertEqual(tags[2:5],bytes([3,9,137]))

    def test_callback_changes_next_owner_match(self):
        tags=bytearray([255])*65536;tags[2]=131;tags[4]=132
        events,_=self.run_scan({0:tags},mutate=True,override=True)
        self.assertEqual(events[1:3],[(2<<16,1<<16,'context'),(4<<16,1<<16,'context')])

    def test_cross_region_span_does_not_advance_next_outer_region_start(self):
        a=bytearray([255])*65536;b=bytearray([255])*65536
        a[-1]=3;b[0]=131
        events,_=self.run_scan({0:a,1:b})
        self.assertEqual(events[1:3],[(65535<<16,2<<16,'context'),(1<<32,1<<16,'context')])

    def test_null_region_is_skipped(self):
        events,result=self.run_scan({0:None})
        self.assertEqual(events,['lock','unlock']);self.assertEqual(result['spans_dispatched'],0)
