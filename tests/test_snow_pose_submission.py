import json
from pathlib import Path
import struct
import unittest
from engine.snow_pose_submission import prepare_spring_submission, inspect


class PoseSubmissionTests(unittest.TestCase):
    def test_spring_record_axis_order_and_preservation(self):
        source=b'\xa5'*256;previous=b'\x55'*288
        result=prepare_spring_submission(source,previous,[2,3,4],[1,2,3],[.5,.75,1],request_byte=1)
        self.assertEqual([r['source_axis'] for r in result['records']],[1,2,0])
        self.assertEqual(result['source'][:0x9c],source[:0x9c])
        for r,off in zip(result['records'],(0xc8,0xdc,0xf0)):
            self.assertEqual(result['storage'][off:off+8],struct.pack('<2f',r['stiffness'],r['damping']))
        self.assertEqual(result['storage'][0xfa:0xfc],previous[0xfa:0xfc])
        self.assertTrue(result['notify'])

    def test_fixture_and_required_evidence_labels(self):
        path=Path(__file__).resolve().parents[1]/'engine/examples/snow_pose_submission.json'
        doc=json.loads(path.read_text());result=inspect(doc)
        self.assertEqual(result['provenance'],'authored_synthetic')
        self.assertEqual(len(bytes.fromhex(result['storage'])),288)
        del doc['sequence']
        with self.assertRaises(ValueError):inspect(doc)

    def test_inspector_derives_swap_from_body_pair(self):
        path=Path(__file__).resolve().parents[1]/'engine/examples/snow_pose_submission.json'
        doc=json.loads(path.read_text())
        doc['inputs'].pop('swap_byte')
        doc['inputs']['body_pair']=dict(first=dict(token=1,flags16=0,key32=1),second=dict(token=2,flags16=0x8000,key32=9))
        self.assertTrue(inspect(doc)['body_pair']['frame_swap'])
        doc['inputs']['swap_byte']=0
        with self.assertRaises(ValueError):inspect(doc)
