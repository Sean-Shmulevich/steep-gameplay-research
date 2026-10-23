import unittest
from engine.action_vector_selection import select_vector_source


class VectorSelectionTests(unittest.TestCase):
    def run_selection(self, mode, lane=0, blocked=False):
        calls = []
        vector = bytes.fromhex('00000080 4523c17f 0000803f 000080ff')
        def gate(kind, index):
            calls.append((kind, index))
            return blocked
        def read(kind, index, value):
            calls.append((kind, index))
            return value
        result = select_vector_source(mode, lane,
            vector_blocked=lambda i: gate('vg', i),
            scalar_blocked=lambda i: gate('sg', i),
            read_vector=lambda i: read('vr', i, vector),
            read_scalar=lambda i: read('sr', i, vector[:4]))
        return result, calls, vector

    def test_vector_lane_copies_preserve_other_bits(self):
        for mode in (0, 1):
            for lane in (0, 1, 2, 3, 0xffffffff):
                out, calls, vec = self.run_selection(mode, lane)
                expected = vec if lane not in (1, 2) else (vec[:4] if lane == 1 else vec[4:8]) + bytes(4) + vec[8:]
                self.assertEqual(out, expected)
                self.assertEqual(calls, [('vg', mode), ('vr', mode)])

    def test_gate_suppresses_reads(self):
        for mode in range(4):
            out, calls, _ = self.run_selection(mode, 2, True)
            self.assertEqual(out, bytes(16))
            self.assertEqual(len(calls), 1)

    def test_scalar_mode_ignores_lane(self):
        for mode, index in ((2, 10), (3, 12)):
            out, calls, vec = self.run_selection(mode, 2)
            self.assertEqual(out, vec[:4] + bytes(12))
            self.assertEqual(calls, [('sg', index), ('sr', index)])

    def test_unknown_mode_reads_nothing(self):
        for mode in (4, 0xffffffff):
            out, calls, _ = self.run_selection(mode)
            self.assertEqual(out, bytes(16))
            self.assertEqual(calls, [])
