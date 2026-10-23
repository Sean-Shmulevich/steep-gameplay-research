import unittest
from engine.examples.action_refresh_probe import run_probe


class RefreshLifecycleProbeTests(unittest.TestCase):
    def test_exhausted_claims_do_not_release_next_category(self):
        result = run_probe()
        for request in (1, 2):
            rows = [row for row in result['observations'] if row['request'] == request]
            self.assertEqual([r['remaining'] for r in rows], [0, 0, 0, 0])
            self.assertEqual([r['executions'] for r in rows], [2, 1, 0, 0])
            self.assertEqual([r['category5_started'] for r in rows],
                             [request-1, request-1, request, request])
            self.assertEqual([r['terminal_begins'] for r in rows],
                             [request-1, request-1, request-1, request])

    def test_next_request_suppression_clears_previous_sample(self):
        result = run_probe()
        self.assertEqual(result['events'], [
            ['gather', 1], ['evaluate', 1], ['refresh', 1, 0.75], ['category5', 1],
            ['gather', 2], ['refresh', 2, 0.0], ['category5', 2]])
        self.assertEqual(result['final_sample'], 0.0)


if __name__ == '__main__':
    unittest.main()
