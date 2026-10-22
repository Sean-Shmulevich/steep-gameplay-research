import json
from pathlib import Path
import unittest
from reference.animation_work import prepare_application_context
from reference.ground_response_pose import provider_pose_transform


class ApplicationContextTests(unittest.TestCase):
    def test_original_caller_and_transform_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/application_context_validation.json').read_text())
        for sample in receipt['samples']:
            result=prepare_application_context(**sample['inputs'],
                reciprocal_sqrt=lambda _:sample['rsqrt_seed'])
            self.assertEqual(json.loads(json.dumps(result)),sample['result'])
            self.assertEqual(result['position'][3],0.)
            p=sample['saved_position']
            transformed=provider_pose_transform([x*0. for x in p[:3]]+[0.],
                sample['saved_rotation'],result['position'],result['rotation'],False)
            transformed['position']=transformed['position'][:3]+(0.*p[3],)
            self.assertEqual(json.loads(json.dumps(transformed)),sample['transformed'])
            self.assertEqual(transformed['position'][:3],result['position'][:3])
