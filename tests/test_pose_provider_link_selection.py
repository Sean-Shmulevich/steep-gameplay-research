import struct
import unittest
from engine.pose_body_connectivity_refresh import refresh_pose_body_connectivity
from engine.pose_provider_link_selection import select_pose_provider_links


def node(left, right, parent, red, value, key):
    raw = bytearray(32)
    struct.pack_into('<iiiBB', raw, 0, left, right, parent, red, 0)
    struct.pack_into('<QQ', raw, 16, value, key)
    return raw


class ProviderLinkSelectionTests(unittest.TestCase):
    def fixture(self):
        # Black root key20 with red children key10 and key30, in slots 0..2.
        nodes = bytearray(node(1, 2, -1, 0, 200, 20) + node(-1, -1, 0, 1, 100, 10)
                          + node(-1, -1, 0, 1, 300, 30))
        provider = bytearray(0x28)
        struct.pack_into('<QIIIii', provider, 8, 9, 3, 0, 0, 0, -1)
        bodies = {}
        metadata = {}
        for token, priority, state in ((1, 0x8000, 0), (2, 0x7fff, 0), (3, 0x8000, 0x32)):
            body = bytearray(0x40); struct.pack_into('<Q', body, 0x30, token + 10)
            meta = bytearray(0x60); struct.pack_into('<H', meta, 0x50, priority); meta[0x53] = state
            bodies[token] = body; metadata[token + 10] = meta
        return provider, nodes, dict(bodies=bodies, metadata=metadata, node_arrays={9: nodes})

    @staticmethod
    def row(endpoint, key):
        return struct.pack('<QQQ', endpoint, 0xAAAA, key)

    def test_eligible_hits_are_removed_and_reported_once(self):
        provider, nodes, services = self.fixture()
        rows = [self.row(1, 20), self.row(1, 20), self.row(1, 99), self.row(1, 10)]
        self.assertEqual(select_pose_provider_links(provider, rows, **services), [200, 100])
        active, free, _, root, head = struct.unpack_from('<IIIii', provider, 0x10)
        # Removing two-child root key20 copies predecessor key10/value100 into slot0
        # and frees slot1. The later key10 hit then removes slot0, promoting slot2.
        self.assertEqual((active, free, root, head), (1, 2, 2, 0))
        self.assertEqual((nodes[13], nodes[32 + 13]), (1, 1))
        self.assertEqual(struct.unpack_from('<ii', nodes, 0), (-1, 1))
        self.assertEqual(nodes[64 + 12], 0)

    def test_priority_and_state_gates_skip_rows(self):
        provider, nodes, services = self.fixture()
        before = bytes(nodes)
        rows = [self.row(2, 20), self.row(3, 10)]
        self.assertEqual(select_pose_provider_links(provider, rows, **services), [])
        self.assertEqual(bytes(nodes), before)

    def test_last_slot_removal_trims_instead_of_freeing(self):
        provider, nodes, services = self.fixture()
        select_pose_provider_links(provider, [self.row(1, 30)], **services)
        active, free, _, root, head = struct.unpack_from('<IIIii', provider, 0x10)
        self.assertEqual((active, free, head), (2, 0, -1))
        self.assertEqual(nodes[64 + 13], 0)

    def test_composes_as_connectivity_collect_stage(self):
        provider, nodes, services = self.fixture()
        body = bytearray(0x200); meta = bytearray(0x60); owner = bytearray(0x40)
        controller = bytearray(0x80)
        struct.pack_into('<Q', body, 0x30, 5); struct.pack_into('<Q', meta, 0x20, 6)
        struct.pack_into('<Q', owner, 0x20, 7); struct.pack_into('<QQ', controller, 0x30, 8, 4)
        struct.pack_into('<Q', body, 0x80, 50)
        link = bytearray(0x40); link[8:0x20] = self.row(1, 30)
        struct.pack_into('<Q', link, 0x30, 50)  # endpoint is not this body: next at+30
        seen = []
        refresh_pose_body_connectivity(
            body, body_token=1000, metadata={5: meta}, owners={6: owner},
            controllers={7: controller}, links={50: link},
            collect=lambda token, rows: select_pose_provider_links(provider, rows, **services),
            rebuild=lambda context, out: seen.append(('rebuild', context, list(out))),
            retire=lambda token, out, flag: seen.append(('retire', token, list(out), flag)))
        self.assertEqual(seen, [('rebuild', 8, [300]), ('retire', 4, [300], 1)])


if __name__ == '__main__':
    unittest.main()
