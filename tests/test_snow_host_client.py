"""Snow host client protocol checks against a synthetic loopback host; no Wine or game."""
import importlib.util
import json
from pathlib import Path
import socket
import threading
import unittest

spec = importlib.util.spec_from_file_location('snow_host_client', Path(__file__).resolve().parents[1]/'scripts/snow_host_client.py')
client_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_module)


class FakeHost:
    """Answers each request line with scripted response lines."""

    def __init__(self, script):
        self.script = script
        self.received = []
        self.server = socket.socket()
        self.server.bind(('127.0.0.1', 0))
        self.server.listen(1)
        self.port = self.server.getsockname()[1]
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        conn, _ = self.server.accept()
        with conn:
            buf = b''
            for replies in self.script:
                while b'\n' not in buf:
                    chunk = conn.recv(4096)
                    if not chunk:
                        return
                    buf += chunk
                line, buf = buf.split(b'\n', 1)
                request = json.loads(line)
                self.received.append(request)
                for reply in replies(request):
                    conn.sendall(json.dumps(reply).encode() + b'\n')
            while conn.recv(4096):  # hold the connection until the client closes it
                pass

    def close(self):
        self.server.close()


def accepted_then(status, result):
    return lambda r: [{'id': r['id'], 'status': 'accepted'}, {'id': r['id'], 'status': status, 'result': result}]


class SnowHostClientTests(unittest.TestCase):
    def test_completed_call_returns_result_and_sends_params(self):
        host = FakeHost([accepted_then('completed', {'requested': 3})])
        with client_module.SnowHostClient(port=host.port, timeout=5) as c:
            self.assertEqual(c.call('simulation.step_world', count=3), {'requested': 3})
        host.close()
        self.assertEqual(host.received, [{'id': 1, 'method': 'simulation.step_world', 'params': {'count': 3}}])

    def test_failed_call_raises_with_error_code(self):
        host = FakeHost([accepted_then('failed', {'error': 'not_paused_by_host'})])
        with client_module.SnowHostClient(port=host.port, timeout=5) as c:
            with self.assertRaisesRegex(client_module.HostError, 'not_paused_by_host'):
                c.call('simulation.resume')
        host.close()

    def test_rejected_request_is_final_without_accept(self):
        host = FakeHost([lambda r: [{'id': r['id'], 'status': 'rejected', 'error': 'unknown_method'}]])
        with client_module.SnowHostClient(port=host.port, timeout=5) as c:
            self.assertEqual(c.request('host.nope')['status'], 'rejected')
        host.close()

    def test_mismatched_id_is_a_protocol_error(self):
        host = FakeHost([lambda r: [{'id': r['id'] + 1, 'status': 'accepted'}]])
        with client_module.SnowHostClient(port=host.port, timeout=5) as c:
            with self.assertRaises(ConnectionError):
                c.request('simulation.status')
        host.close()

    def test_missing_final_response_times_out(self):
        host = FakeHost([lambda r: [{'id': r['id'], 'status': 'accepted'}]])
        with client_module.SnowHostClient(port=host.port, timeout=0.3) as c:
            with self.assertRaises(TimeoutError):
                c.request('simulation.status')
        host.close()

    def test_demo_resumes_after_step_failure(self):
        status = {'engine': {'held': False, 'step': 1}, 'ordinary': True}
        host = FakeHost([
            accepted_then('completed', status),
            accepted_then('completed', {'baseline_group': '00000001'}),
            accepted_then('failed', {'error': 'step_timeout'}),
            accepted_then('completed', {'fallback_restore': False}),
            accepted_then('completed', status),
        ])
        with client_module.SnowHostClient(port=host.port, timeout=5) as c:
            record = client_module.demo(c, 3, 5000)
        host.close()
        self.assertFalse(record['ok'])
        self.assertIn('step_timeout', record['error'])
        self.assertEqual(record['resume']['status'], 'completed')
        self.assertEqual([r['method'] for r in host.received],
                         ['simulation.status', 'simulation.pause', 'simulation.step_world', 'simulation.resume', 'simulation.status'])


if __name__ == '__main__':
    unittest.main()


class StepTransactionTests(unittest.TestCase):
    def test_failed_step_cannot_be_hidden_by_successful_resume(self):
        host=FakeHost([
            accepted_then('completed', {'host_paused':False}),
            accepted_then('completed', {}),
            accepted_then('completed', {'exactly_one':0}),
            accepted_then('completed', {}),
            accepted_then('completed', {'host_paused':False}),
        ])
        with client_module.SnowHostClient(port=host.port) as client:
            result=client_module.demo(client,5,5000)
        host.close()
        self.assertFalse(result['ok'])
        self.assertEqual(len(result['steps']),1)
        self.assertEqual([r['method'] for r in host.received].count('simulation.step_world'),1)
        self.assertEqual(result['resume']['status'],'completed')

    def test_existing_hold_is_not_touched(self):
        host=FakeHost([accepted_then('completed', {'host_paused':True})])
        with client_module.SnowHostClient(port=host.port) as client:
            result=client_module.demo(client,1,5000)
        host.close()
        self.assertFalse(result['ok']);self.assertEqual(len(host.received),1)

    def test_uncertain_pause_attempts_resume_without_retry(self):
        class Client:
            calls=[]
            def call(self,method,**params):
                self.calls.append(method)
                if method=='simulation.pause':raise TimeoutError('lost pause result')
                return {'host_paused':False}
            def request(self,method,**params):
                self.calls.append(method);raise ConnectionError('lost resume result')
        client=Client();result=client_module.demo(client,1,5000)
        self.assertFalse(result['ok']);self.assertIn('resume_error',result)
        self.assertIn('lost pause',result['error'])
        self.assertEqual(client.calls,['simulation.status','simulation.pause','simulation.resume','simulation.status'])

    def test_invalid_count_does_not_contact_host(self):
        for count in (0,61,True,1.5):
            with self.assertRaises(ValueError):client_module.demo(None,count,5000)
