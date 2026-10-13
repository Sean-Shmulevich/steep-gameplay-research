import threading
import unittest

from engine.control_server import make_server
from engine.examples.controller_experiment import run


class ControllerExperimentTests(unittest.TestCase):
    def test_checkpoint_branches_replay_and_reproduce_over_http(self):
        server = make_server(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}'
            first = run(url, frames=5)
            second = run(url, frames=5)
            self.assertEqual(first['approach']['samples'], second['approach']['samples'])
            self.assertEqual(first['branches'][0]['start'], first['branches'][1]['start'])
            for branch, repeated in zip(first['branches'], second['branches']):
                self.assertEqual(branch['samples'], repeated['samples'])
                self.assertTrue(branch['replay_equal'])
                self.assertTrue(branch['trace']['complete'])
                self.assertEqual(branch['analysis']['anomalies'], [])
                self.assertEqual(len(branch['samples']), 5)
            self.assertNotEqual(first['branches'][0]['samples'][-1]['body']['velocity'],
                                first['branches'][1]['samples'][-1]['body']['velocity'])
            self.assertTrue(first['final_control']['submissions_excluded'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_invalid_spec_rejected_before_connection(self):
        for url, frames in [('https://example.com', 1), ('http://127.0.0.1:1', True),
                            ('http://127.0.0.1:1/path', 1)]:
            with self.assertRaises(ValueError):
                run(url, frames=frames)
