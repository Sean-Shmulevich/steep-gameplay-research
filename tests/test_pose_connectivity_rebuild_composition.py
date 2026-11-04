import struct
import unittest
from engine.pose_body_connectivity_rebuild import rebuild_pose_body_connectivity
from engine.pose_group_link_remove import DETACHED, remove_pose_group_link


class RebuildWithGroupLinkRemovalTests(unittest.TestCase):
    """Bind recovered 19581c0 as the rebuild's link service (both native-validated)."""

    def test_selected_links_leave_their_groups_and_each_group_processes_once(self):
        ctx = bytearray(0x470); struct.pack_into('<Q', ctx, 0x464, 0xFFFFFFFF_00000007)
        group = bytearray(0x100); struct.pack_into('<QI', group, 0x40, 500, 3)
        slots = bytearray(struct.pack('<QQQ', 11, 12, 13))
        body = bytearray(0x40); struct.pack_into('<Q', body, 0x10, 30)
        objects = {}
        for index, token in enumerate((11, 12, 13)):
            obj = bytearray(0x100); struct.pack_into('<Q', obj, 8, 20)
            struct.pack_into('<I', obj, 0x80, index); objects[token] = obj
        objects[12][0x84] = 2        # flags84 bit1: skipped, stays a member
        processed = []

        def link(group_token, token):
            remove_pose_group_link(groups[group_token], objects[token],
                                   objects=objects, slot_arrays={500: slots})

        def process(context, group_token):
            processed.append((context, group_token, groups[group_token][0xa1],
                              struct.unpack_from('<I', groups[group_token], 0x48)[0]))

        groups = {30: group}
        rebuild_pose_body_connectivity(1, [11, 13], contexts={1: ctx}, objects=objects,
            bodies={20: body}, groups=groups, link=link, process=process)
        self.assertEqual(processed, [(1, 30, 0, 1)])
        self.assertEqual(struct.unpack_from('<II', ctx, 0x464), (1, 0))
        self.assertEqual(struct.unpack_from('<Q', slots, 0)[0], 12)
        self.assertEqual(struct.unpack_from('<I', objects[12], 0x80)[0], 0)
        for token in (11, 13):
            self.assertEqual(struct.unpack_from('<I', objects[token], 0x80)[0], DETACHED)


if __name__ == '__main__':
    unittest.main()
