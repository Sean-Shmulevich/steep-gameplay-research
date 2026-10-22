import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from engine.ground_response_bench import run
from engine.server import make_server

EXAMPLE=Path(__file__).resolve().parents[1]/'engine/examples/ground_response_probe.json'


class GroundBenchTests(unittest.TestCase):
    def request(self):return json.loads(EXAMPLE.read_text())

    def test_sequence_is_repeatable_and_preserves_inputs(self):
        req=self.request();before=copy.deepcopy(req)
        first=run(req);self.assertEqual(first,run(req));self.assertEqual(req,before)
        self.assertEqual(len(first['frames']),5)
        self.assertNotEqual(first['frames'][0]['state'],first['frames'][-1]['state'])
        self.assertEqual(first['frames'][2]['filter']['drive'],0)
        self.assertFalse(first['body_mutations']);self.assertFalse(first['live_game_execution'])

    def test_supplied_estimates_reproduce_declared_seed_run(self):
        req=self.request();base=run(req);req['rsqrt_policy']='supplied'
        for frame,result in zip(req['frames'],base['frames']):frame['rsqrt_estimates']=result['rsqrt_estimates_used']
        got=run(req)
        self.assertEqual(got['final_state'],base['final_state'])
        self.assertNotEqual(got['input_sha256'],base['input_sha256'])
        req['frames'][0]['rsqrt_estimates'].append(None)
        with self.assertRaises(ValueError):run(req)
        req['frames'][0]['rsqrt_estimates']=[]
        with self.assertRaises(ValueError):run(req)

    def test_limits_and_invalid_inputs(self):
        for change in ({'rsqrt_policy':'automatic'},{'frames':[]},{'frames':[{}]*2401}):
            req=self.request();req.update(change)
            with self.assertRaises(ValueError):run(req)
        req=self.request();req['frames'][0]['observation']['dt']=0
        with self.assertRaises(ValueError):run(req)

    def test_compiled_curve_input_matches_constant_sampled_curves(self):
        req=self.request();baseline=run(req)
        req['curve_format']='compiled'
        req['curves']={role:dict(start=0,index_scale=1,segments=[[0,1]]) for role in ('entry','a','b')}
        self.assertEqual(run(req)['frames'],baseline['frames'])
        req['curves']['entry']['index_scale']=0
        with self.assertRaises(ValueError):run(req)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'result.json'
            subprocess.run([sys.executable,'-m','engine.ground_response_bench','--request',str(EXAMPLE),'--output',str(out)],cwd=EXAMPLE.parents[2],check=True,capture_output=True,timeout=10)
            self.assertEqual(json.loads(out.read_text())['final_state'],json.loads(json.dumps(run(self.request())['final_state'])))

    def test_http_inspection_does_not_mutate_engine(self):
        server=make_server(0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            before=server.engine.state_hash()
            request=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/',json.dumps({'op':'ground_response','request':self.request()}).encode(),{'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=10) as response:result=json.load(response)
            self.assertEqual(len(result['frames']),5)
            self.assertEqual(server.engine.state_hash(),before)
            bad=self.request();bad['rsqrt_policy']='supplied'
            request.data=json.dumps({'op':'ground_response','request':bad}).encode()
            with self.assertRaises(urllib.error.HTTPError) as context:urllib.request.urlopen(request,timeout=10)
            self.assertEqual(context.exception.code,400)
            self.assertEqual(server.engine.state_hash(),before)
        finally:server.shutdown();server.server_close();thread.join(5)
