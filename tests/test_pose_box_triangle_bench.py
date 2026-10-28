import json
from pathlib import Path
import unittest
from engine.pose_box_triangle_bench import inspect


class ContactBenchTest(unittest.TestCase):
    def fixture(self):
        return json.loads((Path(__file__).resolve().parents[1]/'engine/examples/pose_box_triangle.json').read_text())

    def test_inspection_labels_linear_distance_and_preserves_input(self):
        doc=self.fixture();before=json.dumps(doc)
        result=inspect(doc)
        self.assertEqual(result['count'],4)
        self.assertEqual(result['provenance'],'authored_synthetic')
        self.assertTrue(all(r['separation_kind']=='linear_plane' for r in result['records']))
        self.assertTrue(all(len(bytes.fromhex(r['record_hex']))==48 for r in result['records']))
        self.assertEqual(json.dumps(doc),before)

    def test_provenance_and_allocation_bounds(self):
        for field,value in [('capacity',1000000000),('edge_enabled',1)]:
            doc=self.fixture();doc['inputs'][field]=value
            with self.assertRaises(ValueError):inspect(doc)
        doc=self.fixture();doc.pop('provenance')
        with self.assertRaises(ValueError):inspect(doc)
