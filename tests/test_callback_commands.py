import struct
import unittest
from engine.callback_commands import callback_arguments, submit_callback, drain_counted_callbacks
from engine.command_counter_transfer import replay_counter_transfers


class CallbackCommandTests(unittest.TestCase):
    def test_abi_tag_mask_and_payload(self):
        for kind in (3, 4):
            for tag in range(4):
                record = bytearray(104)
                struct.pack_into('<I', record, 0, kind)
                offset = 24 if kind == 3 else 56
                struct.pack_into('<QQ', record, offset+16, 0x1000 | tag, 0x2000)
                struct.pack_into('<Q', record, 88, 0xffffffffffffffff)
                result = callback_arguments(bytes(record), record_identity='synthetic')
                self.assertEqual((result['storage_offset'], result['context'], result['target']), (offset, 0x1000, 0x2000))
                self.assertEqual('payload' in result, kind == 4)
                if kind == 4:self.assertEqual(result['payload'], 0xffffffffffffffff)

    def test_full_publication_repeats_last_record(self):
        queue = []; deferred = 0
        first = struct.pack('<4Q', 1, 2, 0x1003, 0x2000)
        dropped = struct.pack('<4Q', 3, 4, 0x3000, 0x4000)
        for descriptor, inserted in ((first, True), (dropped, False)):
            receipt = submit_callback(queue, descriptor, capacity=1, deferred=deferred)
            deferred = receipt['deferred']
            self.assertEqual(receipt['inserted'], inserted)
        transfer = replay_counter_transfers({'A':[0,deferred], 'B':[0,0]}, [('exchange','A',None),('add','A',None)])
        seen = []
        result = drain_counted_callbacks(queue, active=transfer['counters']['A'][0], dispatch=seen.append)
        self.assertEqual(seen, [first, first])
        self.assertEqual((result['popped'], result['repeated_cached'], result['active']), (1,1,0))

    def test_newly_published_record_can_replace_cached_one(self):
        first, second = bytes(32), bytes([1])*32
        queue=[first]; seen=[]
        def invoke(descriptor):
            seen.append(descriptor)
            if len(seen)==1:queue.append(second)
        result=drain_counted_callbacks(queue, active=2, dispatch=invoke)
        self.assertEqual((seen,result['popped']),([first,second],2))

    def test_negative_budget_clears_without_consuming_and_counter_wraps(self):
        queue=[bytes(32)]
        result=drain_counted_callbacks(queue,active=0x80000000,dispatch=lambda x:self.fail())
        self.assertEqual((result['active'],len(queue)),(0,1))
        receipt=submit_callback(queue,bytes(32),capacity=1,deferred=0xffffffff)
        self.assertEqual(receipt,dict(inserted=False,deferred=0))

    def test_unknown_initial_record_and_tags_refused(self):
        with self.assertRaises(ValueError):
            drain_counted_callbacks([],active=1,dispatch=lambda x:self.fail())
        with self.assertRaises(ValueError):callback_arguments(bytes(104))


if __name__ == '__main__':unittest.main()
