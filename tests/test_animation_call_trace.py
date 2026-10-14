import struct
import unittest
from engine.animation_call_trace import decode_packet, pair_calls


def event(seq, name, thread=1, stack=0x2000, component=0x1000, status=(0, 0, 1)):
    packet = struct.pack('<Qf3B', 0, .125, *status)
    return dict(kind='hit', sequence=seq, event=name, thread=thread,
                registers=dict(rdi=hex(component), rsp=hex(stack)), packet_hex=packet.hex())


class AnimationCallTraceTests(unittest.TestCase):
    def test_pair_keeps_packet_changes_without_measuring_debugger_time(self):
        result = pair_calls([event(1, 'call_before'), event(2, 'call_after', status=(1, 2, 0))])
        self.assertEqual(result['pairs'][0]['before']['status_bytes'], [0, 0, 1])
        self.assertEqual(result['pairs'][0]['after']['status_bytes'], [1, 2, 0])
        self.assertEqual(result['unmatched'], [])
        self.assertFalse(result['timing_cost_established'])

    def test_nested_and_interleaved_threads_pair_by_identity(self):
        records = [event(1, 'call_before'), event(2, 'call_before', thread=2),
                   event(3, 'call_before', stack=0x1800), event(4, 'call_after', thread=2),
                   event(5, 'call_after', stack=0x1800), event(6, 'call_after')]
        self.assertEqual([(p['before_sequence'], p['after_sequence']) for p in pair_calls(records)['pairs']],
                         [(2, 4), (3, 5), (1, 6)])

    def test_missing_events_and_unexpected_stop_break_pairing(self):
        for records in ([event(1, 'call_before'), event(3, 'call_after')],
                        [event(1, 'call_before'), dict(kind='unexpected_stop'), event(2, 'call_after')]):
            result = pair_calls(records)
            self.assertFalse(result['pairs'])
            self.assertEqual(len(result['unmatched']), 2)

    def test_reused_stack_after_missing_return_is_not_a_match(self):
        result = pair_calls([event(1, 'call_before'), event(2, 'call_before'), event(3, 'call_after')])
        self.assertFalse(result['pairs'])
        self.assertEqual(len(result['unmatched']), 3)

    def test_return_for_wrong_component_or_stack_is_rejected(self):
        for kwargs in (dict(component=0x9999), dict(stack=0x9999)):
            self.assertFalse(pair_calls([event(1, 'call_before'), event(2, 'call_after', **kwargs)])['pairs'])

    def test_capture_end_keeps_open_call_unmatched(self):
        result = pair_calls([event(1, 'call_before'), dict(kind='window_end'), event(2, 'call_after')])
        self.assertFalse(result['pairs'])
        self.assertEqual(len(result['unmatched']), 2)

    def test_raw_float_bits_and_defined_packet_length_preserved(self):
        for bits in (0x80000000, 0x7fc01234, 0x7f800000):
            packet = bytes(8) + struct.pack('<I', bits) + bytes(3)
            result = decode_packet(packet)
            self.assertEqual(result['interval_bits'], bits)
            if bits != 0x80000000:
                self.assertIsNone(result['interval'])
        with self.assertRaises(ValueError):
            decode_packet(bytes(16))
        with self.assertRaises(ValueError):
            pair_calls([event(2, 'call_before'), event(1, 'call_after')])
