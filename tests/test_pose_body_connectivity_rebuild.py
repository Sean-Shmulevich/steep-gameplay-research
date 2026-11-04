import struct
import unittest
from engine.pose_body_connectivity_rebuild import rebuild_pose_body_connectivity
from engine.pose_body_connectivity_refresh import refresh_pose_body_connectivity


class ConnectivityRebuildTests(unittest.TestCase):
    def fixture(self, layout):
        """layout: object token -> (flags84, body token); body token == 100+group."""
        ctx = bytearray(b'\xaa' * 0x480)
        objects = {}; bodies = {}; groups = {}
        for token, (flags, body) in layout.items():
            o = bytearray(0x100); o[0x84] = flags
            struct.pack_into('<Q', o, 8, body); objects[token] = o
            b = bytearray(0x40); struct.pack_into('<Q', b, 0x10, body + 100)
            bodies[body] = b; groups.setdefault(body + 100, bytearray(0x100))
        return ctx, dict(contexts={5: ctx}, objects=objects, bodies=bodies, groups=groups)

    def counter(self, ctx):
        return struct.unpack_from('<II', ctx, 0x464)

    def test_empty_output_only_zeroes_counter_pair(self):
        ctx, args = self.fixture({})
        rebuild_pose_body_connectivity(5, [], **args, link=None, process=None)
        self.assertEqual(self.counter(ctx), (0, 0))
        self.assertEqual(ctx[:0x464] + ctx[0x46c:], b'\xaa' * (0x480 - 8))

    def test_flag_bit1_skips_link_and_queue_other_bits_do_not(self):
        ctx, args = self.fixture({1: (2, 10), 2: (0xfd, 11), 3: (3, 12)})
        events = []
        rebuild_pose_body_connectivity(5, [1, 2, 3], **args,
            link=lambda g, o: events.append(('link', g, o)),
            process=lambda c, g: events.append(('process', c, g)))
        self.assertEqual(events, [('link', 111, 2), ('process', 5, 111)])
        self.assertEqual(self.counter(ctx), (1, 0))

    def test_shared_group_queued_once_but_linked_per_object(self):
        ctx, args = self.fixture({1: (0, 10), 2: (0, 10), 3: (0, 11)})
        events = []
        def link(g, o):
            events.append(('link', g, o, args['groups'][g][0xa1]))
        def process(c, g):
            events.append(('process', g, args['groups'][g][0xa1], self.counter(ctx)[0]))
        rebuild_pose_body_connectivity(5, [1, 2, 1, 3], **args, link=link, process=process)
        self.assertEqual(events, [('link', 110, 1, 1), ('link', 110, 2, 1), ('link', 110, 1, 1),
            ('link', 111, 3, 1), ('process', 110, 0, 0), ('process', 111, 0, 1)])
        self.assertEqual(self.counter(ctx), (2, 0))

    def test_preset_a0_or_a1_prevents_queue_and_a1_is_left_set(self):
        ctx, args = self.fixture({1: (0, 10), 2: (0, 11)})
        args['groups'][110][0xa0] = 7; args['groups'][111][0xa1] = 9
        events = []
        rebuild_pose_body_connectivity(5, [1, 2], **args,
            link=lambda g, o: events.append(g), process=lambda c, g: events.append('p'))
        self.assertEqual(events, [110, 111]); self.assertEqual(args['groups'][111][0xa1], 9)
        self.assertEqual(args['groups'][110][0xa1], 0); self.assertEqual(self.counter(ctx), (0, 0))

    def test_link_clearing_a1_requeues_group_and_link_setting_a0_blocks_later(self):
        ctx, args = self.fixture({1: (0, 10), 2: (0, 11), 3: (0, 12)})
        g = args['groups']; processed = []
        def link(group, obj):
            if obj == 1: g[110][0xa1] = 0; g[112][0xa0] = 1
        rebuild_pose_body_connectivity(5, [1, 1, 2, 3], **args, link=link,
            process=lambda c, group: processed.append(group))
        self.assertEqual(processed, [110, 110, 111]); self.assertEqual(self.counter(ctx), (3, 0))

    def test_counter_is_reloaded_after_process_and_wraps(self):
        ctx, args = self.fixture({1: (0, 10), 2: (0, 11)})
        def process(c, group):
            struct.pack_into('<II', ctx, 0x464, 0xffffffff, 44)
        rebuild_pose_body_connectivity(5, [1, 2], **args, link=lambda g, o: None, process=process)
        self.assertEqual(self.counter(ctx), (0, 44))

    def test_queue_is_captured_and_slots_reread_but_count_is_captured(self):
        ctx, args = self.fixture({1: (0, 10), 2: (0, 11), 3: (0, 12)})
        output = [1, 2]; seen = []; processed = []
        def link(group, obj):
            seen.append(obj)
            if obj == 1: output[1] = 3; output.append(2)
        def process(c, group):
            processed.append(group); args['groups'][112][0xa1] = 0
        rebuild_pose_body_connectivity(5, output, **args, link=link, process=process)
        self.assertEqual((seen, processed), ([1, 3], [110, 112]))

    def test_composes_as_refresh_rebuild_stage(self):
        ctx, args = self.fixture({71: (0, 10), 72: (0, 10)})
        b = bytearray(0x200); m = bytearray(0x60); o = bytearray(0x40); c = bytearray(0x80)
        struct.pack_into('<Q', b, 0x30, 3); struct.pack_into('<Q', m, 0x20, 4)
        struct.pack_into('<Q', o, 0x20, 6); struct.pack_into('<QQQ', c, 0x30, 5, 7, 0)
        struct.pack_into('<Q', b, 0x80, 20); link_row = bytearray(0x40)
        struct.pack_into('<QQ', link_row, 8, 2, 20); struct.pack_into('<Q', link_row, 0x20, 20)
        events = []
        rebuild = lambda context, out: rebuild_pose_body_connectivity(context, out, **args,
            link=lambda g, obj: events.append(('link', g, obj)),
            process=lambda cc, g: events.append(('process', cc, g)))
        refresh_pose_body_connectivity(b, body_token=2, metadata={3: m}, owners={4: o},
            controllers={6: c}, links={20: link_row}, collect=lambda p, rows: [71, 72],
            rebuild=rebuild, retire=lambda p, out, f: events.append(('retire', out)))
        self.assertEqual(events, [('link', 110, 71), ('link', 110, 72), ('process', 5, 110),
            ('retire', [71, 72])])


if __name__ == '__main__':
    unittest.main()
