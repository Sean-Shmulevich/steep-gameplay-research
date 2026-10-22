import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from engine.pose_bench import run
from reference.ground_response_pose import resolved_pose_tail

ROOT = Path(__file__).resolve().parents[1]


class PoseTailTests(unittest.TestCase):
    def test_original_uninterrupted_tail_outputs(self):
        evidence = json.loads((ROOT/'native/snow_host/pose_tail_validation.json').read_text())
        self.assertEqual(evidence['cases'],96)
        for i,row in enumerate(evidence['rows']):
            with self.subTest(case=i):
                result = resolved_pose_tail(**row['inputs'])
                for key in ('positions','smoothed'):
                    for a,b in zip(result['output'][key],row['result']['output'][key]):
                        self.assertEqual(struct.pack('<4f',*a),struct.pack('<4f',*b))
                for a,b in ((result['reference_output'],row['result']['reference_output']),
                            (result['state']['correction'],row['result']['state']['correction'])):
                    self.assertEqual(struct.pack('<4f',*a),struct.pack('<4f',*b))

    def request(self):
        return json.loads((ROOT/'engine/examples/pose_tail_probe.json').read_text())

    def test_sequence_repeatability_and_input_preservation(self):
        request = self.request(); saved=copy.deepcopy(request)
        a,b=run(request),run(request)
        self.assertEqual(a,b); self.assertEqual(request,saved)
        self.assertEqual(len(a['records']),5)
        self.assertFalse(a['game_process']);self.assertFalse(a['skeleton_commit'])
        self.assertNotEqual(a['records'][0]['state'],a['records'][1]['state'])

    def test_resume_matches_continuous_sequence(self):
        request=self.request();whole=run(request)
        first=copy.deepcopy(request);first['frames']=first['frames'][:2]
        second=copy.deepcopy(request);second['frames']=second['frames'][2:]
        second['initial_state']=run(first)['final_state']
        self.assertEqual(run(second)['final_state'],whole['final_state'])

    def test_explicit_branch_and_observation_limits(self):
        for alteration in ({'branch':'guessed'}, {'frames':[]}, {'initial_state':{}}):
            request=self.request();request.update(alteration)
            with self.assertRaises(ValueError):run(request)
        for value in (-1,1.01,True):
            request=self.request();request['frames'][0]['blend']=value
            with self.assertRaises(ValueError):run(request)
        request=self.request();request['frames'][0]['decay_mode']=True
        with self.assertRaises(ValueError):run(request)
        request=self.request();request['frames'][0]['endpoint_previous']=[[0,0,0,0]]*2
        with self.assertRaises(ValueError):run(request)

    def test_cli_writes_inspectable_result(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'result.json'
            proc=subprocess.run([sys.executable,'-m','engine.pose_bench','--request',
                str(ROOT/'engine/examples/pose_tail_probe.json'),'--output',str(output)],
                cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertEqual(proc.returncode,0,proc.stderr)
            result=json.loads(output.read_text());self.assertEqual(len(result['records']),5)
