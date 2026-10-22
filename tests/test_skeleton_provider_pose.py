import json
from pathlib import Path
import struct
import unittest
from reference.skeleton_provider_pose import convert_skeleton_provider_pose as convert


class SkeletonProviderPoseTests(unittest.TestCase):
    def test_original_conversion_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/skeleton_provider_pose_validation.json').read_text())
        self.assertEqual(receipt['cases'], 120)
        for sample in receipt['samples']:
            actual = convert(**sample['inputs'])
            for field, count in [('position', 3), ('rotation', 4)]:
                self.assertEqual(struct.pack('<%df' % count, *actual[field]),
                    struct.pack('<%df' % count, *sample['result'][field]))

    def test_base_translation_rotation_and_passthrough(self):
        args = dict(position=[2,3,4,0], rotation=[0,0,0,1],
                    base_position=[10,20,30,0], base_rotation=[0,0,1,0])
        self.assertEqual(convert(**args, already_transformed=False),
                         dict(position=[8,17,34], rotation=[0,0,1,0]))
        self.assertEqual(convert(**args, already_transformed=True),
                         dict(position=[2,3,4], rotation=[0,0,0,1]))

    def test_nonunit_base_is_not_silently_normalized(self):
        result = convert([2,3,4,0], [0,0,0,1], [0,0,0,0], [0,0,0,2], False)
        self.assertEqual(result, dict(position=[14,21,28], rotation=[0,0,0,2]))

    def test_existing_provider_receipt_matches_linked_consumer(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/provider_pose_validation.json').read_text())
        for case in receipt['rows']:
            args = case['inputs']
            result = convert(args['position'], args['rotation'], args['parent_position'],
                             args['parent_rotation'], args['direct'])
            self.assertEqual(struct.pack('<3f', *result['position']),
                             struct.pack('<3f', *case['result']['position'][:3]))
            self.assertEqual(struct.pack('<4f', *result['rotation']),
                             struct.pack('<4f', *case['result']['rotation']))
