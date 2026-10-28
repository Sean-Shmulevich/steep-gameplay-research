import struct
import unittest
from engine.pose_body_bounds import refresh_pose_body_bounds
from engine.pose_body_integration import integrate_pose_body


def fixture(count):
    body = bytearray(0x200)
    frame = bytearray(64)
    for i in range(3):
        struct.pack_into('<f', frame, 16*i+4*i, 1)
    body[0x40:0x80] = frame
    struct.pack_into('<Q', body, 0x30, 1)
    struct.pack_into('<Q', body, 0xb8, 2)
    struct.pack_into('<H', body, 0xc0, count)
    entries = bytearray(72*count)
    for i in range(count):
        struct.pack_into('<QQ', entries, 72*i+16, 10+i, 3)
    return body, {2:entries}, {3:frame}, {1:bytearray(b'\xa5'*96)}


class BoundsTest(unittest.TestCase):
    def test_integrated_translation_reaches_resource(self):
        body, arrays, transforms, metadata = fixture(1)
        struct.pack_into('<3f', body, 0x1a0, 4,-2,6)
        struct.pack_into('<3f', transforms[3], 0x30, 1,2,3)
        integrate_pose_body(body, .5)
        seen=[]
        def supplied_point(resource, frame):
            seen.append((resource, frame[3]))
            return frame[3]*2
        refresh_pose_body_bounds(body, entry_arrays=arrays, transforms=transforms,
                                 metadata=metadata, resource_bounds=supplied_point)
        self.assertEqual(seen, [(10,[3,1,6])])
        self.assertEqual(struct.unpack_from('<6f', metadata[1],4),(3,1,6,3,1,6))
        self.assertEqual(metadata[1][:4], b'\xa5'*4)
        self.assertEqual(metadata[1][28:], b'\xa5'*68)

    def test_capture_count_reload_array_and_metadata_and_zero_ties(self):
        body, arrays, transforms, metadata = fixture(2)
        replacement=bytearray(arrays[2]);struct.pack_into('<Q',replacement,88,99)
        arrays[4]=replacement;metadata[5]=bytearray(96);seen=[]
        def service(resource, frame):
            seen.append(resource)
            if len(seen)==1:
                struct.pack_into('<Q', body, 0xb8,4)
                struct.pack_into('<Q', body, 0x30,5)
                struct.pack_into('<H', body, 0xc0,0)
                return [0.]*6
            return [-0.]*6
        refresh_pose_body_bounds(body, entry_arrays=arrays, transforms=transforms,
                                 metadata=metadata, resource_bounds=service)
        self.assertEqual(seen,[10,99])
        self.assertEqual(metadata[1],b'\xa5'*96)
        self.assertEqual(metadata[5][4:28],struct.pack('<6f',0,0,0,-0.,-0.,-0.))

    def test_empty_is_point_but_all_null_is_rejected(self):
        body, arrays, transforms, metadata = fixture(0)
        struct.pack_into('<3f',body,0x70,1,-2,3)
        def no_calls(*args):self.fail('Unexpected resource call')
        refresh_pose_body_bounds(body, entry_arrays=arrays, transforms=transforms,
                                 metadata=metadata, resource_bounds=no_calls)
        self.assertEqual(struct.unpack_from('<6f',metadata[1],4),(1,-2,3,1,-2,3))
        struct.pack_into('<H',body,0xc0,1);arrays[2]=bytearray(72)
        before=bytes(metadata[1])
        with self.assertRaises(ValueError):
            refresh_pose_body_bounds(body, entry_arrays=arrays, transforms=transforms,
                                     metadata=metadata, resource_bounds=no_calls)
        self.assertEqual(metadata[1],before)
