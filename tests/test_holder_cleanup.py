import unittest
from engine.holder_cleanup import cleanup_holder


class HolderCleanupTests(unittest.TestCase):
    def holder(self,**kw):
        h=dict(status=0,count=0,payload={'flags':0xffffffff},token=123,address=0x1030)
        h.update(kw);return h

    def test_detachment_then_pool_link_publication(self):
        h=self.holder(status=1<<31);p=dict(base=0x1000,head=9);events=[]
        def remove(t):
            self.assertIsNone(h['payload']);self.assertEqual(h['status'],1<<26)
            events.append(('remove',t))
        result=cleanup_holder(h,release_payload_token=lambda t:events.append(('release',t)),
            remove_token=remove,locate_pool=lambda _:p)
        self.assertEqual(events,[('release',123),('remove',123)])
        self.assertEqual(h['count'],9);self.assertEqual(p['head'],2)
        self.assertTrue(result['recycled'])

    def test_all_gates_refuse_without_services(self):
        def forbidden(*_):self.fail()
        for kw in ({'status':1},{'status':1<<24},{'status':1<<26},{'count':1}):
            h=self.holder(**kw)
            self.assertFalse(cleanup_holder(h,release_payload_token=forbidden,
                remove_token=forbidden,locate_pool=forbidden)['detached'])

    def test_null_payload_preserves_high_bit_and_null_token_skips_pool(self):
        h=self.holder(payload=None,token=0,status=1<<31)
        result=cleanup_holder(h,release_payload_token=lambda _:self.fail(),
            remove_token=lambda _:self.fail(),locate_pool=lambda _:self.fail())
        self.assertEqual(h['status'],(1<<31)|(1<<26));self.assertFalse(result['recycled'])

    def test_reserved_token_still_recycles(self):
        h=self.holder(payload=None,token=0xf0000000)
        p=dict(base=0x1000,head=3)
        self.assertTrue(cleanup_holder(h,release_payload_token=lambda _:self.fail(),
            remove_token=lambda _:self.fail(),locate_pool=lambda _:p)['recycled'])

    def test_consumer_callback_reacquisition_blocks_cleanup(self):
        from engine.holder_consumer_step import consume_holder_step
        h=self.holder(status=1<<24);original=h['payload']
        registry=dict(mode=1,ring=dict(slots=[h],count=1,capacity=1,head=0))
        results=[]
        def reacquire(_):h['status']+=1
        def cleanup(_,holder):
            results.append(cleanup_holder(holder,release_payload_token=lambda _:self.fail(),
                remove_token=lambda _:self.fail(),locate_pool=lambda _:self.fail()))
        consume_holder_step(registry,payload_virtual48=reacquire,dispatch_payload=lambda _:self.fail(),
            append_output=lambda _:None,cleanup_holder=cleanup)
        self.assertEqual(results,[dict(detached=False,recycled=False)])
        self.assertIs(h['payload'],original);self.assertEqual(h['status'],1)
