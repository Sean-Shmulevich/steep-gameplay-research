import unittest
from engine.allocation_context_release import release_context_region
from engine.allocation_region_release import release_metadata_region


class ContextReleaseTests(unittest.TestCase):
    def test_exact_one_differs_from_other_odd_flags(self):
        for flag in (0,1,2,3,255):
            calls=[]
            result=release_context_region(0x700000,131072,flag,
                invoke=lambda *args:calls.append(args) or 17)
            self.assertEqual(result,17)
            self.assertEqual(calls,[(0x700000,131072 if flag==1 else 0,
                                    0x4000 if flag==1 else 0x8000)])

    def test_fallback_keeps_accounting_size_while_context_passes_zero(self):
        tags=bytearray([3,131]);record=dict(field10=131072);calls=[]
        def context(_,address,size,flag):
            self.assertEqual(tags,bytes([255,255]))
            release_context_region(address,size,flag,invoke=lambda *args:calls.append(args))
        result=release_metadata_region(dict(regions={0:tags}),0,131072,2,record,None,
            lock=lambda _:None,unlock=lambda _:None,release_context=context)
        self.assertEqual(calls,[(0,0,0x8000)])
        self.assertEqual(result['dispatched_size'],131072)
        self.assertEqual(record['field10'],0)
