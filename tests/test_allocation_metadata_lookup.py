import unittest
from engine.allocation_metadata_lookup import lookup_allocation_metadata


class AllocationMetadataLookupTests(unittest.TestCase):
    def test_two_level_address_partition_ignores_low_sixteen_bits(self):
        region = bytearray(65536); region[0x4321] = 0x85
        for low in (0, 1, 65535):
            seen = []
            result = lookup_allocation_metadata((0x12345678<<32)|(0x4321<<16)|low,
                read_region=lambda high: seen.append(high) or region,
                read_entry=lambda i: ('metadata', i), default_index=lambda: self.fail())
            self.assertEqual(seen, [0x12345678])
            self.assertEqual(result, ('metadata', 5))

    def test_missing_region_and_sentinel_use_unmasked_default(self):
        for region in (None, bytes([255])*65536):
            result = lookup_allocation_metadata(0, read_region=lambda _:region,
                read_entry=lambda i:i, default_index=lambda:200)
            self.assertEqual(result, 200)

    def test_high_bit_is_ignored_except_all_ones_sentinel(self):
        for tag, index in ((0,0),(128,0),(126,126),(254,126),(127,127)):
            self.assertEqual(lookup_allocation_metadata(0,read_region=lambda _:bytes([tag]),
                read_entry=lambda i:i,default_index=lambda:self.fail()), index)

    def test_null_address_is_still_looked_up(self):
        self.assertEqual(lookup_allocation_metadata(0,read_region=lambda _:None,
            read_entry=lambda _:None,default_index=lambda:0),None)
