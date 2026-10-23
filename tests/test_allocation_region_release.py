import unittest
from engine.allocation_region_release import release_metadata_region
from engine.allocation_region_retirement import retire_metadata_regions


class RegionReleaseTests(unittest.TestCase):
    def test_nonzero_size_uses_floor_but_always_clears_one_tag(self):
        for size,count in ((1,1),(65535,1),(65536,1),(131071,1),(131072,2)):
            tags=bytearray([3])*65536;registry=dict(regions={0:tags});record=dict(field10=0)
            def dispatch(context,address,n,flags):
                self.assertEqual(tags[:count],bytes([255])*count)
                record['field10']=10
            result=release_metadata_region(registry,0,size,2,record,None,
                lock=lambda _:None,unlock=lambda _:None,release_context=dispatch)
            self.assertEqual(result['tags_cleared'],count)
            self.assertEqual(record['field10'],(10-size)&0xffffffffffffffff)

    def test_zero_size_includes_terminal_and_odd_flag_bypasses_edits(self):
        for flags in (0,1,2,3):
            tags=bytearray([3,4,132]);record=dict(field10=999999)
            result=release_metadata_region(dict(regions={0:tags}),0,0,flags,record,None,
                lock=lambda _:None,unlock=lambda _:None,release_context=lambda *_:None)
            self.assertEqual(result['tags_cleared'],0 if flags&1 else 3)
            self.assertEqual(record['field10'],999999 if flags&1 else 999999-3*65536)

    def test_null_record_does_not_clear_tags(self):
        tags=bytearray([3]);result=release_metadata_region(dict(regions={0:tags}),0,0,2,None,None,
            lock=lambda _:None,unlock=lambda _:None,release_context=lambda *_:None)
        self.assertEqual(tags,bytes([3]));self.assertEqual(result['dispatched_size'],0)

    def test_connected_cross_region_scan_dispatches_once(self):
        a=bytearray([255])*65536;b=bytearray([255])*65536;a[-1]=3;b[0]=131
        registry=dict(regions={0:a,1:b},override=None);record=dict(index=3,field10=131072)
        depth=0;maximum=0;calls=[]
        def lock(_):
            nonlocal depth,maximum
            depth+=1;maximum=max(maximum,depth)
        def unlock(_):
            nonlocal depth
            depth-=1
        def dispatch(context,address,size,flags):calls.append((address,size,depth,record['field10']))
        def fallback(*args):
            release_metadata_region(*args,lock=lock,unlock=unlock,release_context=dispatch)
        retire_metadata_regions(registry,record,None,lock=lock,unlock=unlock,
            ensure_initialized=lambda:None,address_limit=lambda:2<<32,fallback=fallback)
        self.assertEqual(calls,[(65535<<16,131072,2,131072)])
        self.assertEqual((a[-1],b[0],record['field10'],depth,maximum),(255,255,0,0,2))
