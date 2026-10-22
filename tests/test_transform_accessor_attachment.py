import json
from pathlib import Path
import struct
import unittest
from reference.transform_accessor_attachment import attach_direct_child


class AccessorAttachmentTests(unittest.TestCase):
    def test_original_attachment_chain(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/accessor_attachment_validation.json').read_text())
        for sample in receipt['samples']:
            backing=bytes.fromhex(sample['backing_hex'])
            result=attach_direct_child(backing if sample['existing'] else None,
                owner=17,child=19,new_backing=backing,
                initial_transform=bytes.fromhex(sample['initial_transform_hex']),fallback_holder=7)
            self.assertEqual(result['accessor'].hex(),sample['result_hex'])
            self.assertEqual(result['child_next'],sample['child_next'])
            self.assertEqual(result['created'],not sample['existing'])

    def test_reuse_does_not_repair_backlink_or_deduplicate(self):
        backing=bytearray(224)
        struct.pack_into('<QQ',backing,0x40,23,19)
        result=attach_direct_child(backing,owner=17,child=19)
        self.assertEqual(struct.unpack_from('<Q',result['accessor'],0x40)[0],23)
        self.assertEqual(result['child_next'],19)
        self.assertFalse(result['backlink_written'])
        self.assertEqual(struct.unpack_from('<Q',backing,0x48)[0],19)
