import struct
import unittest
from engine.vector_action_refresh import refresh_vector_action


class VectorRefreshTests(unittest.TestCase):
    def run_refresh(self, **changes):
        settings = dict(owner_suppressed=False, configuration_available=True,
            kind=0, lane_mode=0, ownership_blocked=lambda *_: False,
            read_vector=lambda _: struct.pack('<4f', .25, .5, 0, 0),
            read_scalar=lambda _: struct.pack('<f', .125),
            processing_enabled=False, process=None)
        settings.update(changes)
        return refresh_vector_action(bytes([0x7b])*192, **settings)

    def test_sample_retains_analog_magnitude_and_raw_input(self):
        result = self.run_refresh()
        snapshot = result['snapshot']
        self.assertEqual(struct.unpack_from('<4f', snapshot, 0x60), (.25, .5, 0, 0))
        self.assertEqual(snapshot[0x50:0x60], snapshot[0x60:0x70])
        self.assertAlmostEqual(struct.unpack_from('<f', snapshot, 0x80)[0], (.25**2+.5**2)**.5)
        self.assertEqual(snapshot[0x30], 1)
        self.assertEqual(snapshot[0x84:], bytes([0x7b])*(192-0x84))

    def test_suppression_and_missing_configuration_do_not_read_sources(self):
        def fail(*_): self.fail('unreachable source called')
        for gates in ({'owner_suppressed': True}, {'configuration_available': False}):
            result = self.run_refresh(read_vector=fail, read_scalar=fail, process=fail,
                                      ownership_blocked=fail, processing_enabled=True, **gates)
            self.assertEqual(result['snapshot'][0x60:0x84], bytes(36))
            self.assertEqual(result['snapshot'][0x30], 0x7b)
            self.assertEqual(result['snapshot'][0x50:0x60], bytes([0x7b])*16)
            self.assertFalse(result['source_evaluated'])
            self.assertFalse(result['processor_invoked'])
            self.assertEqual(result['evaluator_called'], not gates.get('owner_suppressed', False))

    def test_lane_selection_precedes_processing(self):
        seen = []
        def process(raw):
            seen.append(struct.unpack('<4f', raw))
            return struct.pack('<4f', .125, 0, 0, 0)
        result = self.run_refresh(lane_mode=2, processing_enabled=True, process=process)
        self.assertEqual(seen, [(.5, 0, 0, 0)])
        self.assertEqual(struct.unpack_from('<4f', result['snapshot'], 0x50), (.5, 0, 0, 0))
        self.assertEqual(struct.unpack_from('<4f', result['snapshot'], 0x60), (.125, 0, 0, 0))

    def test_blocked_source_can_still_be_processed(self):
        def fail(_): self.fail('blocked cache read')
        result = self.run_refresh(ownership_blocked=lambda *_: True, read_vector=fail,
            processing_enabled=True, process=lambda raw: struct.pack('<4f', 1, 0, 0, 0))
        self.assertEqual(result['snapshot'][0x50:0x60], bytes(16))
        self.assertEqual(result['snapshot'][0x30], 1)

    def test_scalar_selection_and_invalid_processor(self):
        seen = []
        result = self.run_refresh(kind=3, lane_mode=2,
            read_scalar=lambda channel: (seen.append(channel) or struct.pack('<f', .125)))
        self.assertEqual(seen, [12])
        self.assertEqual(struct.unpack_from('<4f', result['snapshot'], 0x60), (.125, 0, 0, 0))
        with self.assertRaises(ValueError):
            self.run_refresh(processing_enabled=True, process=lambda _: b'')


if __name__ == '__main__': unittest.main()
