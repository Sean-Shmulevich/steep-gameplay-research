import json
from pathlib import Path
import unittest
from reference.animation_bank_scale import remove_owner_byte_bank_scale


class ByteBankScaleTests(unittest.TestCase):
    def test_original_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/byte_bank_unscale_validation.json').read_text())
        self.assertEqual(receipt['cases'],96)
        for row in receipt['rows']:
            with self.subTest(scalar=row['scalar'],primary=row['primary_count'],offset=row['secondary_offset']):
                data=bytearray.fromhex(row['input_hex'])
                bank=dict(data=data,secondary_data=memoryview(data)[row['secondary_offset']:],
                    profile=dict(primary_count=row['primary_count']),secondary_count=row['secondary_count'])
                wrapper=dict(request_byte=3 if row['prepared'] else 1)
                self.assertIs(remove_owner_byte_bank_scale(wrapper,bank,lambda:row['scalar']),bank)
                self.assertEqual(data.hex(),row['output_hex'])
                self.assertEqual(wrapper['request_byte'],row['final_request_byte'])

    def test_skipped_storage_is_not_required(self):
        for flags,scalar,bank in ((0,None,{}),(2,1.,{}),(2,2.,dict(profile=dict(primary_count=0)))):
            wrapper=dict(request_byte=flags)
            def get():
                self.assertIsNotNone(scalar);return scalar
            remove_owner_byte_bank_scale(wrapper,bank,get)
            self.assertEqual(wrapper['request_byte'],0)

    def test_truncated_visited_storage_refused_before_flag_clear(self):
        wrapper=dict(request_byte=2)
        with self.assertRaises(ValueError):
            remove_owner_byte_bank_scale(wrapper,dict(profile=dict(primary_count=1),data=bytearray(15)),lambda:2.)
        self.assertEqual(wrapper['request_byte'],2)
