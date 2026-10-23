import unittest
from engine.holder_consumer_step import consume_holder_step


class HolderConsumerStepTests(unittest.TestCase):
    def test_callback_changes_use_new_mode_and_status_but_cached_payload(self):
        h=dict(status=1<<24,payload='old')
        r=dict(mode=0,ring=dict(slots=[h],capacity=1,count=1,head=0))
        events=[]
        def callback(payload):
            self.assertEqual(r['ring']['count'],0)
            h.update(payload='new',status=(1<<24)|7);r['mode']=1
        result=consume_holder_step(r,payload_virtual48=callback,
            dispatch_payload=lambda _:self.fail(),append_output=lambda p:events.append(p),
            cleanup_holder=lambda _,x:events.append(x['status']))
        self.assertEqual(events,['old',7]);self.assertTrue(result['cleanup_called'])
        self.assertEqual(h['payload'],'new')

    def test_nonzero_count_skips_services_and_retains_slot(self):
        h=dict(status=(1<<24)|1,payload='payload');slots=[h]
        r=dict(mode=1,ring=dict(slots=slots,capacity=1,count=1,head=0))
        def forbidden(*_):self.fail()
        result=consume_holder_step(r,payload_virtual48=forbidden,dispatch_payload=forbidden,
            append_output=forbidden,cleanup_holder=forbidden)
        self.assertFalse(result['cleanup_called']);self.assertIs(slots[0],h)
        self.assertEqual(h['status'],1)

    def test_callback_enqueued_work_remains_for_next_iteration(self):
        h=dict(status=1<<24,payload='payload');r=dict(mode=0,ring=dict(slots=[h],capacity=1,count=1,head=0))
        def callback(_):r['ring']['count']=1
        consume_holder_step(r,payload_virtual48=callback,dispatch_payload=lambda _:None,
            append_output=lambda _:self.fail(),cleanup_holder=lambda *_:None)
        self.assertEqual(r['ring']['count'],1)
