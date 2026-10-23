import struct
import unittest
from engine.action_ownership_layout import *


class OwnershipLayoutTests(unittest.TestCase):
    def test_constructed_regions_and_gate_addresses(self):
        seen = []
        for family, channels in (('fixed', 1), ('scalar', 32), ('vector', 2)):
            for channel in range(channels):
                for adapter in range(8):
                    offset = ownership_record_offset(family, adapter, channel)
                    seen.append(offset)
                    if family != 'fixed':
                        expected = (0x850 if family == 'scalar' else 0xf050) + 0xe8*(adapter+8*channel)
                        self.assertEqual(offset+0x40+6*8, expected)
        self.assertEqual(len(set(seen)), 280)
        self.assertEqual(max(seen)+0xe8, TABLE_SIZE)

    def test_bank_order_and_isolation(self):
        data = bytearray(TABLE_SIZE)
        start = ownership_record_offset('vector', 7, 1)
        for n, (name, offset) in enumerate(BANKS.items()):
            for i in range(7): struct.pack_into('<Q', data, start+offset+8*i, n*100+i)
        result = inspect_ownership_banks(bytes(data), 'vector', 7, 1)
        for n, name in enumerate(BANKS): self.assertEqual(result[name], tuple(n*100+i for i in range(6,-1,-1)))
        self.assertEqual(inspect_ownership_banks(bytes(data), 'vector', 6, 1)['current'], (0,)*7)

    def test_bounds(self):
        for args in (('vector',8,0),('vector',0,2),('scalar',0,32),('fixed',0,1)):
            with self.assertRaises(ValueError): ownership_record_offset(*args)
