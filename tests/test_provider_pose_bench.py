import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from engine.provider_pose_bench import run

ROOT=Path(__file__).resolve().parents[1]


class ProviderPoseBenchTests(unittest.TestCase):
    def request(self):
        return json.loads((ROOT/'engine/examples/provider_pose_probe.json').read_text())

    def test_repeatability_and_supplied_record_boundaries(self):
        request=self.request();saved=copy.deepcopy(request)
        result=run(request)
        self.assertEqual(result,run(request));self.assertEqual(request,saved)
        self.assertFalse(result['collision_query_executed']);self.assertFalse(result['provider_selection'])
        self.assertFalse(result['skeleton_commit']);self.assertFalse(result['game_process'])
        self.assertEqual(len(result['records']),5)

    def test_contact_sign_and_skipped_hit_flow_into_tail(self):
        result=run(self.request());accepted=result['records'][1];skipped=result['records'][2]
        a=accepted['preparation']['endpoints'][0];s=skipped['preparation']['endpoints'][0]
        self.assertTrue(a['contact']['accepted']);self.assertEqual(a['above_direction'],(0.,-1.,0.,0.))
        self.assertEqual(a['directions']['below_direction'],(1.,0.,0.,0.))
        self.assertFalse(s['contact']['accepted']);self.assertEqual(s['above_direction'],(0.,1.,0.,0.))
        self.assertLess(s['contact']['point'][2],0.)
        self.assertNotEqual(accepted['filter']['correction'],skipped['filter']['correction'])

    def test_resume_matches_uninterrupted_reconstructed_sequence(self):
        request=self.request();whole=run(request)
        first=copy.deepcopy(request);first['frames']=first['frames'][:2]
        second=copy.deepcopy(request);second['frames']=second['frames'][2:]
        second['initial_state']=run(first)['final_state']
        self.assertEqual(run(second)['final_state'],whole['final_state'])

    def test_missing_extra_estimates_and_overrides_rejected(self):
        for seeds in ([],[1.],[1.,1.,1.]):
            request=self.request();request['frames'][0]['rsqrt_estimates'][0]=seeds
            with self.assertRaises(ValueError):run(request)
        request=self.request();request['frames'][0]['tail']['axis']=[0,0,1,0]
        with self.assertRaises(ValueError):run(request)
        request=self.request();request['frames'][0]['tail']['decay_mode']=True
        with self.assertRaises(ValueError):run(request)

    def test_cli_writes_intermediates(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'result.json'
            proc=subprocess.run([sys.executable,'-m','engine.provider_pose_bench','--request',
                str(ROOT/'engine/examples/provider_pose_probe.json'),'--output',str(output)],
                cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertEqual(proc.returncode,0,proc.stderr)
            result=json.loads(output.read_text())
            self.assertIn('preparation',result['records'][0])
            self.assertNotEqual(result['input_sha256'],result['resolved_tail_input_sha256'])

    def test_record_origins_feed_query_and_tail_without_override(self):
        request=self.request();result=run(request)
        prep=result['records'][0]['preparation']
        for origin,endpoint in zip(prep['endpoint_origins'],prep['endpoints']):
            self.assertEqual(endpoint['contact']['point'],origin['origin'])
            self.assertEqual(endpoint['segment']['start'][1],origin['origin'][1])
        request['frames'][0]['contacts'][0]['endpoint']=[0,0,0,0]
        with self.assertRaises(ValueError):run(request)

    def test_bank_selection_matches_explicit_records(self):
        from reference.ground_response_pose import resolve_pose_channel
        request=self.request();explicit=copy.deepcopy(request)
        for frame in explicit['frames']:
            bank=frame.pop('provider_bank')
            frame['reference_provider']=resolve_pose_channel(bank,0x2c52cbb0)
            frame['endpoint_providers']=[resolve_pose_channel(bank,k) for k in (0x74cb19e4,0xaf72d919)]
        a,b=run(request),run(explicit)
        self.assertTrue(a['supplied_channel_lookup']);self.assertFalse(b['supplied_channel_lookup'])
        self.assertEqual(a['records'],b['records']);self.assertEqual(a['final_state'],b['final_state'])
        request['frames'][0]['provider_bank']['entries']=[]
        with self.assertRaises(ValueError):run(request)
