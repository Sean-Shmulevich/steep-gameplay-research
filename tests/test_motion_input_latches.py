import json
from pathlib import Path
import struct
import unittest
from engine.motion_input_latches import InputLatches, update_input_latches


class MotionInputLatchesTests(unittest.TestCase):
    def test_original_instruction_receipt(self):
        r=json.loads((Path(__file__).resolve().parents[1]/
                      'native/snow_host/input_latch_validation.json').read_text())
        self.assertEqual(len(r['rows']),192)
        for row in r['rows']:
            delta=struct.unpack('<f',struct.pack('<I',row['delta_bits']))[0]
            got=update_input_latches(InputLatches(bool(row['first_latch']),bool(row['second_latch'])),
                current_xy=(delta,0),baseline_xy=(0,0),
                current_secondary_y=delta,baseline_secondary_y=0,
                first_count=row['count'],second_count=row['count'],threshold=1,
                setting_gate=bool(row['setting_gate']),action_gate=bool(row['action_gate']),
                secondary_suppressed=bool(row['secondary_suppressed']))
            self.assertEqual((got.first,got.second,got.combined),
                (bool(row['first_after']),bool(row['second_after']),bool(row['combined'])))

    def test_exact_threshold_and_sticky_history(self):
        args=dict(current_xy=(0,1),baseline_xy=(0,0),current_secondary_y=1,
            baseline_secondary_y=0,first_count=4,second_count=4,threshold=1,
            setting_gate=True,action_gate=False,secondary_suppressed=False)
        self.assertEqual(update_input_latches(InputLatches(False,False),**args),InputLatches(False,False))
        self.assertEqual(update_input_latches(InputLatches(True,True),**args),InputLatches(True,True))
        args['threshold']=0.5
        self.assertEqual(update_input_latches(InputLatches(False,False),**args),InputLatches(True,True))
