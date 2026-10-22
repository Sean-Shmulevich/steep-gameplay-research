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

    def test_central_impulse_http_replays_and_invalidates_token(self):
        _, start=self.request(dict(op='reset',scenario={'body':{'mass':4,'velocity':[0,0,0],'angular_velocity':[1,2,3]}}))
        status,result=self.request(dict(op='apply_central_impulse',token=start['token'],impulse=[8,0,0]))
        self.assertEqual(status,200)
        self.assertEqual(result['snapshot']['state']['body']['velocity'],[2,0,0])
        self.assertEqual(result['snapshot']['state']['body']['angular_velocity'],[1,2,3])
        self.assertEqual(self.request(dict(op='apply_central_impulse',token=start['token'],impulse=[8,0,0]))[0],400)
        _,recording=self.request(path='/replay')
        self.assertEqual(replay(recording).state_hash(),recording['expected_hash'])

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

    def test_brake_boost_step_and_replay_over_http(self):
        _, start = self.request(dict(op='reset', scenario={'body': {
            'velocity': [10, 0, 0], 'angular_velocity': [0, 0, .1]}}))
        first = start['token']
        status, boosted = self.request(dict(op='adjust_speed', token=first, delta_speed=2))
        self.assertEqual(status, 200)
        self.assertEqual(boosted['snapshot']['state']['body']['velocity'], [12, 0, 0])
        self.assertEqual(boosted['snapshot']['state']['body']['angular_velocity'], [0, 0, .1])
        self.assertEqual(self.request(dict(op='adjust_speed', token=first, delta_speed=-2))[0], 400)
        status, braked = self.request(dict(op='adjust_speed', token=boosted['token'], delta_speed=-2))
        self.assertEqual(status, 200)
        self.assertEqual(braked['snapshot']['state']['body']['velocity'], [10, 0, 0])
        status, stepped = self.request(dict(op='step_once', token=braked['token']))
        self.assertEqual(status, 200)
        self.assertEqual(stepped['snapshot']['state']['tick'], 1)
        _, recording = self.request(path='/replay')
        self.assertEqual(replay(recording).state_hash(), recording['expected_hash'])
        self.assertEqual(self.request(dict(op='resume', token=braked['token']))[0], 200)

    def test_light_response_preserves_replay_and_complete_trace(self):
        _, start = self.request(dict(op='reset', scenario={}, include_trace=False))
        self.assertNotIn('trace',start['snapshot'])
        token=start['token']
        status, advanced=self.request(dict(op='step_frame_once',token=token,dt=.02,
                                          actions={'steer':.3},include_trace=False))
        self.assertEqual(status,200)
        self.assertNotIn('trace',advanced['snapshot'])
        self.assertFalse(advanced['snapshot']['trace_summary']['records_included'])
        _,light=self.request(path='/state?trace=summary')
        _,full=self.request(path='/state')
        self.assertEqual(light['state'],full['state'])
        self.assertEqual(light['trace_summary']['retained'],len(full['trace']['records']))
        self.assertEqual(light['trace_summary']['attempted'],full['trace']['attempted'])
        _,recording=self.request(path='/replay')
        self.assertEqual(replay(recording).snapshot(),full['state'])
        _,before=self.request(path='/checkpoint')
        status,_=self.request(dict(op='step_once',token=token,include_trace='false'))
        self.assertEqual(status,400)
        self.assertEqual(self.request(path='/checkpoint')[1],before)
        status,failed=self.request(dict(op='step_frame_once',token=token,dt=-1,include_trace=False))
        self.assertEqual(status,400)
        self.assertNotIn('trace',failed['snapshot'])
        self.assertEqual(failed['snapshot']['state'],before['engine']['state'])
