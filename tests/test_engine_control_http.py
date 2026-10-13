import copy
import json
import threading
import unittest
import urllib.error
import urllib.request

from engine.control_server import make_server
from engine.animation import default_resources
from engine.replay import replay


class ControlHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, body=None, path='/command', origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        request = urllib.request.Request(self.url+path,
            data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, json.load(response)

    def test_pause_step_tune_replay_and_stale_token_over_http(self):
        status, result = self.request(dict(op='reset', scenario={'execution_mode': 'mixed'}))
        self.assertEqual(status, 200)
        token = result['token']
        self.assertEqual(self.request(dict(op='submit_frame', dt=.01))[0], 400)
        status, result = self.request(dict(op='step_frame_once', token=token, dt=1/60))
        self.assertEqual(status, 200)
        self.assertTrue(result['snapshot']['control']['submissions_excluded'])
        tick = result['snapshot']['state']['tick']
        status, tuned = self.request(dict(op='tune', token=token,
                                         changes={'physics': {'brake_deceleration': 4}}))
        self.assertEqual(status, 200)
        self.assertEqual(tuned['snapshot']['state']['tick'], tick)
        self.assertEqual(self.request(dict(op='step_once', token=token))[0], 400)
        self.assertEqual(self.request(dict(op='step_once', token=tuned['token']))[0], 200)
        _, recording = self.request(path='/replay')
        self.assertEqual(replay(recording).state_hash(), recording['expected_hash'])
        _, report = self.request(path='/trace/analysis')
        self.assertEqual(report['anomalies'], [])

    def test_failed_mutation_and_token_schema_preserve_state(self):
        _, result = self.request(dict(op='reset', scenario={}))
        token = result['token']
        _, before = self.request(path='/checkpoint')
        self.assertEqual(self.request(dict(op='tune', token=token,
                            changes={'physics': {'spring_mass': 0}}))[0], 400)
        broken = copy.deepcopy(token)
        broken['generation'] = True
        self.assertEqual(self.request(dict(op='resume', token=broken))[0], 400)
        self.assertEqual(self.request(path='/checkpoint')[1], before)
        self.assertEqual(self.request(dict(op='step_once', token=token))[0], 200)

    def test_restore_and_request_boundaries(self):
        _, result = self.request(dict(op='reset', scenario={}))
        _, checkpoint = self.request(path='/checkpoint')
        self.request(dict(op='step_once', token=result['token']))
        status, restored = self.request(dict(op='restore', checkpoint=checkpoint))
        self.assertEqual(status, 200)
        self.assertEqual(restored['snapshot']['state']['tick'], 0)
        self.assertEqual(self.request(dict(op='resume', token=result['token']))[0], 400)
        self.assertEqual(self.request(dict(op='pause'), origin='https://example.com')[0], 403)
        self.assertEqual(self.request(dict(op='pause'), path='/wrong')[0], 404)
        self.assertEqual(self.request([])[0], 400)
        self.assertEqual(self.request(dict(op='step_frame_once', token=restored['token'], dt=True))[0], 400)

    def test_resource_replacement_remains_paused(self):
        _, result = self.request(dict(op='reset', scenario={}))
        token = result['token']
        rig, clips = default_resources()
        status, replaced = self.request(dict(op='replace_resources', token=token,
            bundle=dict(category='synthetic', rig=rig, clips=clips)))
        self.assertEqual(status, 200)
        self.assertTrue(replaced['snapshot']['control']['submissions_excluded'])
        self.assertEqual(replaced['snapshot']['state']['body'], result['snapshot']['state']['body'])
        self.assertEqual(self.request(dict(op='resume', token=token))[0], 400)
        self.assertEqual(self.request(dict(op='resume', token=replaced['token']))[0], 200)
        self.assertEqual(self.request(dict(op='submit_frame', dt=.01, actions={'steer': .1}))[0], 200)
