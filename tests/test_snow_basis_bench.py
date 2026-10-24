from copy import deepcopy
import json
from pathlib import Path
import unittest
from engine.snow_basis_bench import inspect


class BasisBenchTests(unittest.TestCase):
    def example(self):
        return json.loads((Path(__file__).resolve().parents[1]/'engine/examples/snow_basis_callback.json').read_text())

    def test_example_consumes_pending_angle_and_supplied_sequence_reproduces_it(self):
        d=self.example();before=deepcopy(d);r=inspect(d)
        self.assertEqual(d,before)
        self.assertEqual(r['effects']['branch'],'secondary')
        self.assertEqual(r['effects']['secondary_angle'],0)
        self.assertTrue(r['effects']['cache_written'])
        d['math']={'mode':'supplied_sequence','calls':r['math_calls']}
        replay=inspect(d)
        self.assertEqual(replay['effects'],r['effects'])
        self.assertEqual(replay['provenance'],'authored_synthetic')

    def test_observation_mismatch_and_unused_tail_rejected(self):
        d=self.example();calls=inspect(d)['math_calls']
        d['math']={'mode':'supplied_sequence','calls':deepcopy(calls)}
        d['math']['calls'][0]['input']+=1
        with self.assertRaisesRegex(ValueError,'mismatch'):inspect(d)
        d['math']['calls']=calls+[calls[-1]]
        with self.assertRaisesRegex(ValueError,'Unused'):inspect(d)

    def test_not_reached_requires_no_runtime_payload(self):
        d=self.example();d={k:d[k] for k in ['schema','provenance','phase_continuity']}
        d['callback_reached']=False
        self.assertEqual(inspect(d)['status'],'not_evaluated')

    def test_disabled_uses_no_math_or_prepass(self):
        d=self.example();d['enabled_byte']=0;d.pop('prepass');d.pop('overrides');d.pop('curves')
        d['math']={'mode':'supplied_sequence','calls':[]}
        r=inspect(d)
        self.assertFalse(r['effects']['success'])
        self.assertEqual(r['effects']['basis'],d['incoming_basis'])
