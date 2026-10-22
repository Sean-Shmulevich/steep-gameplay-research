from copy import deepcopy
import json
from pathlib import Path
import unittest
from engine.snow_jump_bench import run


class SnowJumpBenchTests(unittest.TestCase):
    def scenario(self):
        return json.loads((Path(__file__).resolve().parents[1]/'engine/examples/snow_jump_input.json').read_text())

    def test_stateful_sequence_and_spin_preservation(self):
        document=self.scenario(); original=deepcopy(document); result=run(document)
        self.assertEqual(document,original)
        self.assertEqual([r['branch'] for r in result['trace']],['submit','cooldown','disabled','no_release','submit'])
        for r in result['trace']:
            for name in document['bodies']:
                self.assertEqual(r['bodies_after'][name]['angular'],tuple(document['bodies'][name]['angular']))
        self.assertEqual([r['body'] for r in result['trace'][0]['applications']],['rider','main'])
        self.assertGreater(result['final_bodies']['main']['linear'][2],15)

    def test_backend_suppression_does_not_cancel_countdown(self):
        document=self.scenario(); document['bodies']['main']['flags']=8
        result=run(document)
        self.assertEqual(result['final_bodies']['main']['linear'],(3,0,0))
        first=result['trace'][0]
        self.assertGreater(first['state_after']['cooldown'],0)
        self.assertTrue(first['applications'][1]['post_dispatch_requested'])
        self.assertFalse(first['applications'][1]['velocity_write_enabled'])

    def test_missing_rider_and_explicit_provenance(self):
        document=self.scenario(); del document['bodies']['rider']
        result=run(document)
        self.assertEqual([r['body'] for r in result['trace'][0]['applications']],['main'])
        del document['provenance']
        with self.assertRaises(ValueError): run(document)

    def test_invalid_interval_rejected_without_mutating_input(self):
        document=self.scenario(); document['frames'][0]['elapsed_dt']=0; original=deepcopy(document)
        with self.assertRaises(ValueError): run(document)
        self.assertEqual(document,original)
