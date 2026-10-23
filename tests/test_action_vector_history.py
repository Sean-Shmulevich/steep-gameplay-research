import struct
import unittest
from engine.action_vector_history import update_vector_history


class VectorHistoryTests(unittest.TestCase):
    def test_features_observe_new_vector_and_old_time_then_tail_uses_their_writes(self):
        snapshot = bytes(0x3c0)
        vector = struct.pack('<4f', 3, 4, 0, 0)
        def features(state, raw):
            self.assertEqual(state[0x60:0x70], vector)
            self.assertEqual(raw, vector)
            self.assertEqual(struct.unpack_from('<Q', state)[0], 0)
            changed = bytearray(state)
            struct.pack_into('<f', changed, 0x2e0, .25)
            struct.pack_into('<Q', changed, 0, 17)
            return bytes(changed)
        result = update_vector_history(snapshot, vector, now=9, update_features=features)
        self.assertEqual(struct.unpack_from('<2Q', result), (9, 17))
        self.assertEqual(struct.unpack_from('<2f', result, 0x2e0), (1, .25))
        self.assertEqual(result[0x60:0x70], vector)

    def test_ten_entries_drop_oldest_and_do_not_normalize_vectors(self):
        state = bytes(0x3c0)
        for i in range(12):
            state = update_vector_history(state, struct.pack('<4f', i, 0, 0, 0),
                now=i, update_features=lambda s, _: s)
        self.assertEqual(struct.unpack_from('<10Q', state), tuple(reversed(range(2, 12))))
        self.assertEqual([struct.unpack_from('<f', state, 0x60+16*i)[0] for i in range(10)], list(reversed(range(2, 12))))
        self.assertEqual(struct.unpack_from('<10f', state, 0x2e0), (1,)*10)


if __name__ == '__main__': unittest.main()
