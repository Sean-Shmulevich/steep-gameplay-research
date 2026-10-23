import unittest
from engine.examples.input_refresh_timeline import run_probe


class InputRefreshTimelineTests(unittest.TestCase):
    def test_refresh_reads_current_cache_not_future_publication(self):
        rows = run_probe()['observations']
        self.assertEqual([r['sample_x'] for r in rows], [0, .25, .25, .75, .875])
        self.assertEqual([r['cache_clock'] for r in rows], [0, 100, 200, 300, 400])
        self.assertTrue(all(not r['sample_generation_established'] for r in rows))

    def test_edge_stamp_is_not_analog_sample_generation(self):
        rows = run_probe()['observations']
        self.assertEqual([r['positive_x_press_stamp'] for r in rows], [0, 0, 0, 300, 300])
        self.assertEqual(rows[1]['sample_x'], rows[2]['sample_x'])
        self.assertNotEqual(rows[1]['cache_clock'], rows[2]['cache_clock'])
        self.assertNotEqual(rows[3]['sample_x'], rows[4]['sample_x'])
        self.assertEqual(rows[3]['positive_x_press_stamp'], rows[4]['positive_x_press_stamp'])


if __name__ == '__main__': unittest.main()
