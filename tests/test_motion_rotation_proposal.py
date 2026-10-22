import json
from pathlib import Path
import struct
import unittest
from engine.motion_input_latches import InputLatches, update_input_latches
from engine.motion_rotation_proposal import initial_rotation_proposal


class MotionRotationProposalTests(unittest.TestCase):
    def test_original_prefix_bit_comparison(self):
        r=json.loads((Path(__file__).resolve().parents[1]/
                      'native/snow_host/rotation_proposal_validation.json').read_text())
        self.assertEqual(len(r['rows']),120)
        for row in r['rows']:
            result=initial_rotation_proposal(*row['inputs'],
                InputLatches(row['primary_active'],row['secondary_active']),row['limit'])
            self.assertEqual(struct.pack('<3f',*result).hex(),row['proposal_hex'])

    def test_latch_to_proposal_composition(self):
        args=dict(baseline_xy=(0,0),current_secondary_y=0,baseline_secondary_y=0,
                  first_count=4,second_count=4,threshold=0.15,
                  setting_gate=True,action_gate=False,secondary_suppressed=False)
        held=update_input_latches(InputLatches(False,False),current_xy=(.3,0),**args)
        self.assertEqual(initial_rotation_proposal(.3,0,0,held,360),(0,0,0))
        changed=update_input_latches(held,current_xy=(.4,0),**args)
        proposal=initial_rotation_proposal(.4,0,0,changed,360)
        self.assertLess(proposal[2],0)
        self.assertEqual(proposal[:2],(0,0))

    def test_nonfinite_api_rejection(self):
        with self.assertRaises(ValueError):
            initial_rotation_proposal(float('nan'),0,0,InputLatches(True,True),360)
