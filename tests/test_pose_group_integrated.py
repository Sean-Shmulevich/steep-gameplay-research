"""Synthetic integration/bounds ordering and quiet-state regression checks."""
import struct
import unittest
from engine.pose_group_poststep import poststep_integrated_pose_group
from engine.pose_box_resource_bounds import box_resource_bounds
from engine.pose_scalar_trig import scalar_sin_cos


class IntegratedPoststepTests(unittest.TestCase):
    def fixture(self):
        body = bytearray(0x200)
        meta = bytearray(0x60)
        for i in range(3):
            struct.pack_into('<3f', body, 0x40+i*16,
                             *[float(i == j) for j in range(3)])
        struct.pack_into('<Q', body, 0x30, 2)
        struct.pack_into('<Q', body, 0xb8, 3)
        struct.pack_into('<H', body, 0xc0, 1)
        struct.pack_into('<3f', body, 0x1a0, 2, 0, 0)
        entries = bytearray(72)
        struct.pack_into('<QQ', entries, 16, 4, 5)
        local = bytearray(body[0x40:0x80])
        struct.pack_into('<3f', local, 48, 0, 3, 0)
        group = dict(slots=[1], count=1, flag_a0=0)
        args = dict(bodies={1:dict(storage=body, metadata=meta)}, scalar=.5,
                    check_enabled=False, duration_threshold=.25,
                    linear_threshold=.1, angular_threshold=.1,
                    links={}, clear_link=lambda t:self.fail('unexpected release'),
                    entry_arrays={3:entries}, transforms={5:local}, metadata={2:meta},
                    resource_bounds=lambda r,f:box_resource_bounds([1,2,3],f),
                    half_angle_trig=scalar_sin_cos)
        return group, body, meta, args

    def test_bounds_use_integrated_transform(self):
        group, body, meta, args = self.fixture()
        poststep_integrated_pose_group(group, **args)
        self.assertEqual(struct.unpack_from('<3f',body,0x70),(1,0,0))
        self.assertEqual(struct.unpack_from('<6f',meta,4),(0,1,-3,2,5,3))
        self.assertEqual(struct.unpack_from('<3f',body,0x1a0),(2,0,0))

    def test_quiet_transition_suppresses_integration_and_bounds(self):
        group, body, meta, args = self.fixture()
        body[0x1a0:0x1b8] = bytes(24)
        args['check_enabled'] = True
        meta[4:28] = b'Q'*24
        poststep_integrated_pose_group(group, **args)
        self.assertEqual(group['flag_a0'],1)
        self.assertEqual(meta[0x53]&15,2)
        self.assertEqual(meta[4:28],b'Q'*24)

    def test_zero_resources_publish_integrated_point(self):
        group, body, meta, args = self.fixture()
        struct.pack_into('<H',body,0xc0,0)
        args['resource_bounds'] = lambda *unused:self.fail('unexpected bounds call')
        poststep_integrated_pose_group(group, **args)
        self.assertEqual(struct.unpack_from('<6f',meta,4),(1,0,0,1,0,0))


if __name__ == '__main__':
    unittest.main()
