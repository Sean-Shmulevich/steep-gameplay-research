import json
from pathlib import Path
import struct
import unittest
from reference.animation_result_filter import filter_result_records


class ResultFilterTests(unittest.TestCase):
    def test_recursive_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/result_filter_validation.json').read_text())
        self.assertEqual(receipt['cases'],48)
        for row in receipt['rows']:
            threshold=struct.unpack('<f',struct.pack('<I',row['threshold_bits']))[0]
            self.assertEqual([list(r) for r in filter_result_records(row['records'],threshold)],row['result'])

    def test_equal_weight_removes_empty_group(self):
        def record(weight,span,kind):
            b=bytearray(24);struct.pack_into('<fH',b,16,weight,span);b[22]=kind;return bytes(b)
        tree=[record(1,3,1),record(.5,1,0),record(0,1,0)]
        self.assertEqual(filter_result_records(tree,.5),[])
        self.assertEqual(filter_result_records(tree,.25),tree)

    def test_bad_spans_are_refused(self):
        with self.assertRaises(ValueError):filter_result_records([bytes(24)],0)
        b=bytearray(24);struct.pack_into('<fH',b,16,1,2)
        with self.assertRaises(ValueError):filter_result_records([b],0)
