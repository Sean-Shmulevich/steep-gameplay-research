import unittest
from engine.holder_pool_lookup import locate_holder_pool,holder_slot_index
from engine.holder_cleanup import cleanup_holder


class HolderPoolLookupTests(unittest.TestCase):
    def test_first_matching_descriptor_and_upper_boundary(self):
        first=dict(base=0x1000,capacity=2,head=9)
        second=dict(base=0x1000,capacity=3,head=8)
        self.assertIs(locate_holder_pool(0x1018,[first,second]),first)
        self.assertIs(locate_holder_pool(0x1030,[first,second]),second)
        self.assertIsNone(locate_holder_pool(0x1048,[first,second]))

    def test_not_a_strict_pointer_membership_check(self):
        p=dict(base=0x1000,capacity=1)
        self.assertIs(locate_holder_pool(0x1000-23,[p]),p)
        self.assertIsNone(locate_holder_pool(0x1000-24,[p]))
        self.assertIs(locate_holder_pool(0x1001,[p]),p)
        self.assertIs(locate_holder_pool(0x1000+24*(1<<32),[p]),p)

    def test_real_lookup_composes_with_cleanup_free_list_update(self):
        p=dict(base=0x1000,capacity=4,head=7)
        h=dict(address=0x1030,count=0,status=0,payload=None,token=0xf0000000)
        cleanup_holder(h,release_payload_token=lambda _:self.fail(),remove_token=lambda _:self.fail(),
                       locate_pool=lambda x:locate_holder_pool(x['address'],[p]))
        self.assertEqual((h['count'],p['head']),(7,2))

    def test_signed_wrapping(self):
        self.assertEqual(holder_slot_index(0,24),0xffffffff)
        self.assertEqual(holder_slot_index(0,0xffffffffffffffe8),1)
