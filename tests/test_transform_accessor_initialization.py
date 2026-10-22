import json
from pathlib import Path
import struct
import unittest
from reference.transform_accessor_initialization import initialize_transform_accessor
from reference.transform_access import initial_transform_access_state


class AccessorInitializationTests(unittest.TestCase):
    def test_original_initializer_and_wrapper(self):
        self.check_receipt('accessor_initialization_validation.json')

    def test_original_shared_initializer_then_accessor(self):
        self.check_receipt('accessor_bootstrap_validation.json')

    def check_receipt(self, filename):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host' / filename).read_text())
        for sample in receipt['samples']:
            if 'prior_globals_hex' in sample:
                from reference.transform_accessor_initialization import bootstrapped_transform_default
                self.assertEqual(bytes.fromhex(sample['initial_transform_hex']),bootstrapped_transform_default())
            result=initialize_transform_accessor(bytes.fromhex(sample['backing_hex']),
                bytes.fromhex(sample['initial_transform_hex']),sample['fallback_holder'])
            self.assertEqual(result.hex(),sample['result_hex'])
            word,owner,depth,bypass=struct.unpack_from('<IIIB',result,0x8c)
            self.assertEqual(dict(reader_word=word,owner=owner,depth=depth,
                                 owner_bypass_enabled=bypass),initial_transform_access_state())

    def test_scratch_and_unwritten_bytes_remain_supplied_storage(self):
        result=initialize_transform_accessor(bytes([0xa5])*224,bytes([0x3c])*64,7)
        self.assertEqual(result[:64],bytes([0x3c])*64)
        for start,end in ((0x5e,0x60),(0x7c,0x80),(0x89,0x8c),(0x99,0xe0)):
            self.assertEqual(result[start:end],bytes([0xa5])*(end-start))
        self.assertEqual(struct.unpack_from('<QQQ',result,0x40),(0,0,0))
