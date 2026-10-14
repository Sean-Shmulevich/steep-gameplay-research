import struct
import unittest

from engine.animation_outputs import OutputDescriptor, flatten_outputs, resolve_output, read_scalar


class AnimationOutputTests(unittest.TestCase):
    def test_runtime_order_is_output_order_not_node_index(self):
        a, b, c = (OutputDescriptor(n) for n in (12, 0, 8))
        table = flatten_outputs(((a, b), (), (c,)))
        self.assertEqual(table, (a, b, c))
        self.assertIs(resolve_output(table, 1, 9)[1], b)
        self.assertEqual(resolve_output(table, 2, 8)[0], 8)
        for index in (-1, True, 3):
            with self.assertRaises(ValueError):
                resolve_output(table, index, 8)

    def test_scalar_and_timeline_storage_are_distinct(self):
        arena = bytearray(12)
        timeline = bytearray(3 * 160)
        struct.pack_into('<f', arena, 0, -2.5)
        struct.pack_into('<I', arena, 8, (2 << 16) | 65535)
        struct.pack_into('<f', timeline, 2 * 160 + 144, 0.375)
        self.assertEqual(read_scalar((8, OutputDescriptor(0)), arena), -2.5)
        self.assertEqual(read_scalar((9, OutputDescriptor(8)), arena, timeline), .375)
        # Low handle bits do not select a different timeline entry.
        struct.pack_into('<I', arena, 8, 2 << 16)
        self.assertEqual(read_scalar((9, OutputDescriptor(8)), arena, timeline), .375)

    def test_owner_evaluates_before_read(self):
        owner = object()
        arena = bytearray(4)
        binding = (8, OutputDescriptor(0, owner))
        with self.assertRaises(ValueError):
            read_scalar(binding, arena)
        calls = []
        def evaluate(node):
            calls.append(node)
            struct.pack_into('<f', arena, 0, 7)
        self.assertEqual(read_scalar(binding, arena, evaluate_owner=evaluate), 7)
        self.assertEqual(calls, [owner])
        def fail(node):
            raise RuntimeError('owner failed')
        with self.assertRaises(RuntimeError):
            read_scalar(binding, arena, evaluate_owner=fail)

    def test_bounds_and_classes_are_explicit(self):
        for binding, arena, timeline in (
            ((8, OutputDescriptor(1)), bytes(4), b''),
            ((9, OutputDescriptor(0)), bytes(4), bytes(147)),
            ((3, OutputDescriptor(0)), bytes(4), b''),
            ((8, OutputDescriptor(-1)), bytes(4), b''),
        ):
            with self.assertRaises(ValueError):
                read_scalar(binding, arena, timeline)
