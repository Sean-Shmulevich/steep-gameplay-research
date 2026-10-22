"""Synthetic socket integration: actual client/acceptance modules, no game proof."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_host_acceptance
from tests.test_snow_host_client import FakeHost


class AcceptanceCliTests(unittest.TestCase):
    def test_full_sequence_over_socket_retains_receipt_and_releases_hold(self):
        state = {'held': False, 'speed': 10.0}
        def respond(request):
            method = request['method']; params = request.get('params', {})
            if method == 'simulation.status':
                result = {'host_paused': state['held'], 'engine': {'held': state['held']}}
            elif method == 'simulation.pause':
                state['held'] = True; result = {}
            elif method == 'simulation.resume':
                state['held'] = False; result = {}
            elif method == 'simulation.step_world':
                self.assertTrue(state['held'])
                result = dict(requested=params['count'], completed=params['count'], exactly_one=params['count'])
            elif method == 'player.get':
                result = dict(identity='synthetic', flags=3,
                              linear_velocity=[state['speed'], 0, 0], angular_velocity=[0, 0, 0])
            elif method == 'player.adjust_speed':
                self.assertTrue(state['held'])
                state['speed'] += params['delta_speed']
                result = dict(speed_target=state['speed'], after=dict(linear_velocity=[state['speed'], 0, 0]))
            else:
                raise AssertionError(method)
            return [dict(id=request['id'], status='accepted'),
                    dict(id=request['id'], status='completed', result=result)]
        host = FakeHost([respond] * 80)
        try:
            with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()) as stdout:
                output = Path(folder) / 'receipt.json'
                code = run_host_acceptance.main(['--port', str(host.port), '--output', str(output)])
                report = json.loads(output.read_text())
                self.assertEqual(json.loads(stdout.getvalue()), report)
            self.assertEqual(code, 0)
            self.assertTrue(report['ok'])
            self.assertFalse(report['startup_tested'])
            self.assertFalse(report['visual_behavior_tested'])
            self.assertEqual(len(report['stages']), 4)
            self.assertEqual(len(report['captures']), 4)
            self.assertFalse(state['held'])
            self.assertEqual(state['speed'], 10)
            self.assertEqual(sum(r['method'] == 'simulation.step_world' for r in host.received), 7)
        finally:
            host.thread.join(timeout=2)
            host.close()

    def test_invalid_steps_fail_before_connecting(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            run_host_acceptance.main(['--steps', '0'])
        self.assertEqual(caught.exception.code, 2)
