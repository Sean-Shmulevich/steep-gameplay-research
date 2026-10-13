import json
import threading
import unittest
import urllib.request
from engine.server import make_server
class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=make_server(0);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,data):
        req=urllib.request.Request(self.url+'/api',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req) as response:return json.load(response)
    def test_run_checkpoint_restore(self):
        self.request({'op':'reset','scenario':{}});self.request({'op':'run','count':40,'actions':{'steer':.5}})
        checkpoint=self.request({'op':'checkpoint'});self.request({'op':'step','count':20});restored=self.request({'op':'restore'})
        self.assertEqual(checkpoint['hash'],restored['hash']);self.assertEqual(restored['state']['tick'],40)
    def test_view_and_resources(self):
        with urllib.request.urlopen(self.url) as response:self.assertIn(b'<canvas',response.read())
        with urllib.request.urlopen(self.url+'/resources') as response:self.assertEqual(len(json.load(response)['rig']['bones']),3)
    def test_frame_plan_trace_and_reads(self):
        self.request({'op':'reset','scenario':{'scheduler':{'mode':'subdivision','smoothing_enabled':True}}})
        result=self.request({'op':'advance','dt':.016666667})
        self.assertEqual(result['state']['scheduler']['last_count'],2)
        with urllib.request.urlopen(self.url+'/trace') as response:trace=json.load(response)
        self.assertTrue(trace['complete'])
        kinds=[r['kind'] for r in trace['records']]
        self.assertEqual(kinds.count('substep_committed'),2)
        self.assertEqual(kinds[-1],'frame_committed')
        with urllib.request.urlopen(self.url+'/state') as response:self.assertEqual(json.load(response)['tick'],2)
