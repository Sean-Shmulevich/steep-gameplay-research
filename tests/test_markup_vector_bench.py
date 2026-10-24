from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from engine.markup_vector_bench import inspect

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'engine/examples/markup_vector_projection.json'


class VectorBenchTests(unittest.TestCase):
    def test_projection_to_scaled_pending_without_mutating_inputs(self):
        data=json.loads(EXAMPLE.read_text());before=deepcopy(data)
        result=inspect(data)
        self.assertEqual(result['vector'],[2.,0.,0.,0.])
        self.assertEqual(result['pending_after'],[1.,0.,0.,0.])
        self.assertEqual(data,before)

    def test_mode_skip_needs_no_formula_or_seed(self):
        data=json.loads(EXAMPLE.read_text());data['post_dispatch_state']={'current_mode':1}
        del data['vector_inputs'];del data['rsqrt_seed']
        self.assertEqual(inspect(data)['vector'],[0.]*4)
        data['post_dispatch_state']={'current_mode':0,'outer_state':2}
        self.assertEqual(inspect(data)['route']['route'],'zero')

    def test_missing_seed_rejected_and_nonfinite_not_hidden(self):
        data=json.loads(EXAMPLE.read_text());del data['rsqrt_seed']
        with self.assertRaises(ValueError):inspect(data)
        data['post_dispatch_state']={'current_mode':0,'outer_state':3}
        data['vector_inputs']={'current':[0,0,2],'normal':[0,0,1],'entity_direction':[1,0,0],
                               'gain':1,'direct_direction':False,'reverse_fallback':False}
        data['rsqrt_seed']='positive_infinity'
        result=inspect(data)
        self.assertEqual(result['vector'][:3],['nan']*3)
        self.assertIsNone(result['pending_after'])

    def test_cli_example(self):
        output=subprocess.check_output([sys.executable,'-m','engine.markup_vector_bench',str(EXAMPLE)],cwd=ROOT,text=True)
        self.assertEqual(json.loads(output)['status'],'computed')
