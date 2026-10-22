import json
from pathlib import Path
import unittest
from reference.animation_work_timing import advance_work_clock,saved_request_handoff
from reference.animation_request import arbitrate_request
from reference.snow import f32


class AnimationWorkTimingTests(unittest.TestCase):
    def test_original_clock_and_handoff(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/animation_work_timing_validation.json').read_text())
        self.assertEqual(receipt['cases'],384)
        for case in receipt['samples']:
            self.assertEqual(advance_work_clock(**case['inputs']),case['result'])
        for case in receipt['handoff_cases']:
            self.assertEqual(saved_request_handoff(case['saved_flag']),case['result'])

    def test_exact_duration_expires_before_application(self):
        self.assertEqual(advance_work_clock(.125,.25,.125,3),
                         dict(action='expired',elapsed=0.,duration=0.,count=0))
        self.assertEqual(advance_work_clock(0,.25,.125,3)['action'],'apply')

    def test_bank_absence_does_not_advance_clock(self):
        result=advance_work_clock(.125,.25,1.,3,False)
        self.assertEqual(result,dict(action='no_bank',elapsed=.125,duration=.25,count=3))

    def test_saved_handoff_consumes_duration_request(self):
        clock=advance_work_clock(0,.25,.125,3)
        self.assertEqual(clock['action'],'apply')
        handoff=saved_request_handoff(1)
        self.assertTrue(handoff['invoke'])
        request=arbitrate_request(clock['count'],1,0x3f000000,22,0,0)
        self.assertTrue(request['consumed_saved'])
        self.assertEqual(request['effective_scalar'],0x3f000000)
        self.assertEqual(request['work_count'],0)
