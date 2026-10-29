import struct
import unittest
from engine.pose_link_payloads import clear_pose_link_contacts
from engine.pose_group_poststep import transition_pose_body_inactive


def fixture(payloads):
    link=bytearray(b'\xa5'*0x90)
    struct.pack_into('<QII',link,0x58,100,len(payloads),8)
    entries=bytearray(b''.join(struct.pack('<QQ',i,p) for i,p in enumerate(payloads)))
    return link,entries


class LinkRetirementTests(unittest.TestCase):
    def test_nulls_skipped_keys_and_capacity_retained(self):
        link,entries=fixture([11,0,22]);before=bytes(link);original=bytes(entries);calls=[]
        clear_pose_link_contacts(link,entry_arrays={100:entries},release=calls.append)
        self.assertEqual(calls,[11,22]);self.assertEqual(entries,original)
        expected=bytearray(before);struct.pack_into('<I',expected,0x60,0)
        self.assertEqual(link,expected)

    def test_shared_endpoint_ring_releases_once(self):
        link,entries=fixture([11]);struct.pack_into('<Q',link,8,1)
        struct.pack_into('<4Q',link,0x20,9,9,9,9)
        calls=[]
        def clear(token):
            self.assertEqual(token,9)
            clear_pose_link_contacts(link,entry_arrays={100:entries},release=calls.append)
        for token in (1,2):
            body=bytearray(0x1c0);meta=bytearray(0x60)
            struct.pack_into('<Q',body,0x80,9)
            transition_pose_body_inactive(token,body,meta,links={9:link},clear_link=clear)
            self.assertEqual(meta[0x53]&15,2)
        self.assertEqual(calls,[11])

    def test_captured_span_rereads_later_entries(self):
        link,entries=fixture([11,22]);calls=[]
        def release(token):
            calls.append(token)
            if token==11:
                struct.pack_into('<Q',entries,24,33)
                struct.pack_into('<QI',link,0x58,999,0)
        clear_pose_link_contacts(link,entry_arrays={100:entries},release=release)
        self.assertEqual(calls,[11,33])
        self.assertEqual(struct.unpack_from('<Q',link,0x58)[0],999)

    def test_empty_span_never_resolves_storage(self):
        link,_=fixture([])
        clear_pose_link_contacts(link,entry_arrays={},release=lambda _:self.fail('unexpected release'))

    def test_release_failure_does_not_claim_complete_clear(self):
        link,entries=fixture([11])
        def release(_):raise RuntimeError('service failed')
        with self.assertRaises(RuntimeError):clear_pose_link_contacts(link,entry_arrays={100:entries},release=release)
        self.assertEqual(struct.unpack_from('<I',link,0x60)[0],1)
