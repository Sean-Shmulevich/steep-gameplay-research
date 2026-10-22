import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from engine.action_response_replay import replay_response

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/fixtures/action_response_synthetic.json'

class ResponseReplayTests(unittest.TestCase):
    def fixture(self):return json.loads(FIXTURE.read_text())
    def test_stateful_replay_no_mutation(self):
        fixture=self.fixture();before=copy.deepcopy(fixture)
        result=replay_response(fixture)
        self.assertEqual(fixture,before)
        rows=result['updates']
        self.assertGreater(rows[1]['output'][0],rows[0]['output'][0])
        self.assertLess(rows[2]['output'][0],rows[1]['output'][0])
        self.assertLess(rows[3]['output'][0],0)
        self.assertEqual(len(rows[0]['output_hex']),32)
        self.assertFalse(result['game_process'])
    def test_cli_and_missing_gate_failure(self):
        good=subprocess.run([sys.executable,'-m','engine.action_response_replay',str(FIXTURE)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(good.returncode,0,good.stderr)
        self.assertEqual(len(json.loads(good.stdout)['updates']),4)
        with tempfile.TemporaryDirectory() as tmp:
            fixture=self.fixture();del fixture['events'][-1]['global_gate']
            path=Path(tmp)/'bad.json';path.write_text(json.dumps(fixture))
            bad=subprocess.run([sys.executable,'-m','engine.action_response_replay',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(bad.returncode,2);self.assertEqual(bad.stdout,'')
    def test_domain_and_unknown_fields_fail(self):
        fixture=self.fixture();fixture['settings']['guess']=1
        with self.assertRaises(ValueError):replay_response(fixture)
        fixture=self.fixture();fixture['events'][0]['start_ticks']=True
        with self.assertRaises(ValueError):replay_response(fixture)
        fixture=self.fixture();fixture['settings']['duration']=0
        with self.assertRaises(ValueError):replay_response(fixture)
