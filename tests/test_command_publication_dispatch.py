import unittest
from engine.command_publication_dispatch import decode_store_dispatch


class PublicationDispatchTests(unittest.TestCase):
    def test_original_instruction_boundary_vectors(self):
        vectors = [(0, 0, -1536114346, 2758852950),
                   (0xffffffff, 0, -1536114345, 2758852951),
                   (0, 0xffffffffffffffff, -1536114345, 18446744070950698664),
                   (0xffffffff, 0xffffffffffffffff, -1536114346, 18446744070950698665)]
        for word, key, displacement, updated in vectors:
            with self.subTest(word=word, key=key):
                result = decode_store_dispatch(word, key)
                self.assertEqual(result['handler_delta'], displacement)
                self.assertEqual(result['rolling_key'], updated)
                self.assertEqual(result['decoded_word'], displacement & 0xffffffff)
                self.assertEqual(result['stream_bytes_consumed'], 4)

    def test_high_key_half_is_preserved_and_does_not_decode_word(self):
        low = decode_store_dispatch(0x12345678, 0x87654321)
        high = decode_store_dispatch(0x12345678, 0xabcdef0187654321)
        self.assertEqual(low['handler_delta'], high['handler_delta'])
        self.assertEqual(high['rolling_key'] >> 32, 0xabcdef01)
        self.assertEqual(high['rolling_key'] & 0xffffffff, low['rolling_key'])

    def test_reject_out_of_range_and_noninteger_values(self):
        for word, key in [(-1, 0), (2**32, 0), (True, 0), (0, -1), (0, 2**64), (0, True), (1.0, 0)]:
            with self.subTest(word=word, key=key), self.assertRaises(ValueError):
                decode_store_dispatch(word, key)
