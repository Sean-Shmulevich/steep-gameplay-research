import struct
import unittest
from engine.animation_thresholds import update_threshold_packet, deferral_threshold
from engine.animation_update_policy import plan_animation_update


class AnimationThresholdTests(unittest.TestCase):
    def test_missing_components_use_defaults(self):
        expected = bytes((0, 0, 0, 0, 1, 2, 0))
        self.assertEqual(update_threshold_packet(), expected)
        self.assertEqual(update_threshold_packet(first_component={}), expected)
        self.assertEqual(update_threshold_packet(second_component={}), expected)

    def test_selector_bits_and_raw_table_word(self):
        words = [0x7f800001 + n for n in range(8)]
        for index in range(8):
            packet = update_threshold_packet(first_component={'selector_word': 0xffc7 | (index << 3)},
                second_component={'kind': 2, 'threshold': 255}, table_words=words)
            self.assertEqual(packet, struct.pack('<IBBB', words[index], 1, 2, 255))

    def test_special_kind_bypasses_table(self):
        packet = update_threshold_packet(first_component={}, second_component={'kind': 40, 'threshold': 3})
        self.assertEqual(packet, bytes((0, 0, 0, 0, 3, 10, 3)))
        result = plan_animation_update(pending_count_word=1, graph_state_word=0, mode_flags=1,
            counter=0, threshold=deferral_threshold(packet), accumulated=0, interval=.125)
        self.assertTrue(result['deferred'])

    def test_invalid_snapshots(self):
        with self.assertRaises(ValueError):
            update_threshold_packet(first_component={'selector_word': 56},
                second_component={'kind': 1, 'threshold': 0}, table_words=[1])
        with self.assertRaises(ValueError):
            update_threshold_packet(first_component={}, second_component={'kind': 40, 'threshold': 256})
        with self.assertRaises(ValueError):
            deferral_threshold(bytes(6))
