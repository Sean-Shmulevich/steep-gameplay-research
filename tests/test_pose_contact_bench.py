import copy
import json
from pathlib import Path
import struct
import unittest
from engine.pose_contact_bench import inspect


class ContactBenchTests(unittest.TestCase):
    def fixture(self):return json.loads((Path(__file__).resolve().parents[1]/'engine/examples/pose_contact_pass.json').read_text())

    def test_fixture_is_immutable_and_reports_correction_separately(self):
        document=self.fixture();before=copy.deepcopy(document);result=inspect(document)
        self.assertEqual(document,before)
        self.assertEqual(result['planned_counts'][0],2)
        self.assertEqual(result['planned_counts'][4],1)
        self.assertTrue(result['secondary_ran'])
        self.assertNotEqual(result['after']['rider']['frame']['translation'],result['first_pass']['rider']['frame']['translation'])
        self.assertEqual(result['after']['rider']['motion1a0'],result['first_pass']['rider']['motion1a0'])
        self.assertEqual(result['after']['surface'],result['before']['surface'])

    def test_nonzero_mode_changes_row_family(self):
        d=self.fixture();d['inputs']['context']['flags38']|=1
        result=inspect(d)
        self.assertEqual(result['planned_counts'][4],0)
        self.assertEqual(result['planned_counts'][6],4)

    def test_no_implicit_damping_or_index_repair(self):
        for offset,value in ((0x1b8,1),(0x1c,3)):
            d=self.fixture();b=bytearray.fromhex(d['inputs']['bodies']['rider']['raw_hex'])
            struct.pack_into('<Q' if offset==0x1b8 else '<H',b,offset,value)
            d['inputs']['bodies']['rider']['raw_hex']=b.hex()
            with self.assertRaises(ValueError):inspect(d)
