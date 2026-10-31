import struct
import unittest
from engine.pose_body_decode import deserialize_physical_pose_body


def block(tag, payload):
    return struct.pack('<II', 0xecd70000 | tag, len(payload) + 8) + payload


def fixture(data):
    reader = bytearray(0x50)
    struct.pack_into('<QI', reader, 0, 0x1000, len(data))
    struct.pack_into('<QQ', reader, 0x10, 0x1000, 0x1000)
    return reader, {0x1000: data}


class BodyDecodeTests(unittest.TestCase):
    def decode(self, body, reader, buffers):
        events = []
        def setter(name):
            return lambda b, v: events.append((name, v, struct.unpack_from('<Q', reader, 0x10)[0]))
        deserialize_physical_pose_body(body, reader, buffers=buffers,
            read_base=lambda b, r: events.append(('base',)),
            set_scalar=setter('scalar'), set_vector=setter('vector'),
            set_parameters=[setter(i) for i in range(3)])
        return events

    def test_motion_words_and_legacy_flag_preserve_padding(self):
        words = b''.join(struct.pack('<I', i) for i in range(23))
        motion = struct.pack('<6I', 0x80000000, 0x7fc01234, 2, 3, 4, 5)
        for flag in (b'', b'\x82'):
            body = bytearray([0xa5] * 0x200)
            r, buffers = fixture(block(0x1001, words + flag) + block(0x1002, motion))
            self.decode(body, r, buffers)
            self.assertEqual(body[0x1a0:0x1b8], motion)
            self.assertEqual(body[0x120:0x134], words[:20])
            for i in range(6):
                start = 0x140 + 16 * i
                self.assertEqual(body[start:start + 12], words[20 + i*12:32 + i*12])
                self.assertEqual(body[start + 12:start + 16], b'\xa5'*4)
            self.assertEqual(body[0x1c8], flag[0] if flag else 0)
            self.assertEqual(r[0x20], 0)

    def test_setters_receive_captured_values_after_whole_block_read(self):
        data = block(0x1001, bytes(92)) + block(0x1002, bytes(24))
        data += block(0x1003, bytes(range(16))) + block(0x1004, bytes(range(12)))
        r, buffers = fixture(data)
        events = self.decode(bytearray(0x200), r, buffers)
        self.assertEqual([e[0] for e in events], ['base', 'scalar', 'vector', 0, 1, 2])
        self.assertEqual(events[1][1], bytes(range(4)))
        self.assertEqual(events[2][1], bytes(range(4, 16)))
        self.assertEqual(events[1][2], events[2][2])
        self.assertEqual([e[2] for e in events[3:]], [0x1000 + len(data)]*3)

    def test_missing_required_block_preserves_fields_but_later_motion_loads(self):
        body = bytearray([0xa5]*0x200)
        r, buffers = fixture(block(0x1002, bytes(24)))
        self.decode(body, r, buffers)
        self.assertEqual(r[0x20], 1)
        self.assertEqual(body[0x120:0x1a0], b'\xa5'*0x80)
        self.assertEqual(body[0x1c8], 0xa5)
        self.assertEqual(body[0x1a0:0x1b8], bytes(24))

    def test_short_required_block_sets_error_without_partial_copy(self):
        body = bytearray([0xa5]*0x200)
        r, buffers = fixture(block(0x1001, bytes(91)) + block(0x1002, bytes(24)))
        self.decode(body, r, buffers)
        self.assertEqual(r[0x20], 1)
        self.assertEqual(body[0x120:0x134], b'\xa5'*20)
        self.assertEqual(body[0x1a0:0x1b8], bytes(24))
