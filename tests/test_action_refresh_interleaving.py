"""Match observable lifecycle boundaries from controlled native interleavings."""
import json
from pathlib import Path
import unittest
from engine.mixed_scheduler import MixedScheduler


class RefreshInterleavingTests(unittest.TestCase):
    def test_other_returns_cannot_release_inflight_dispatch(self):
        receipt = json.loads((Path(__file__).parents[1] / 'native/snow_host/action_refresh_interleaving_validation.json').read_text())
        for row in receipt['rows']:
            with self.subTest(row=row):
                seen = []
                model = MixedScheduler([
                    dict(id='refresh', kind='range', receivers=list(range(row['callbacks'])),
                         chunk_size=100000, max_concurrency=row['reservations'],
                         handler='observe', successors=['next']),
                    dict(id='next', kind='callback')],
                    handlers={'observe': dict(version='synthetic-v1', callback=lambda _, r: seen.append(r))})
                model.submit('refresh')
                tokens = [model.reserve('refresh') for _ in range(row['reservations'])]
                span = model.claim_range(tokens[0])
                before_body = row['pause_boundary'] == 'callback_entry'
                if not before_body:
                    model.execute_range(tokens[0], span)
                self.assertEqual(len(seen), row['callbacks_at_pause'])
                for token in tokens[1:]:
                    self.assertIsNone(model.claim_range(token))
                    model.finish_dispatch(token)
                    self.assertNotIn('next', model.ready())
                state = model.snapshot()['jobs']['refresh']
                self.assertEqual(state['remaining'], 0)
                self.assertEqual(state['state'], 'DONE')
                self.assertEqual(state['executions'], row['executions_after_other_returns'])
                self.assertEqual(state['outstanding_dispatches'], 1)
                if before_body:
                    model.execute_range(tokens[0], span)
                model.finish_dispatch(tokens[0])
                self.assertIn('next', model.ready())
                self.assertEqual(seen, list(reversed(range(row['callbacks']))))
                state = model.snapshot()['jobs']['refresh']
                self.assertEqual((state['executions'], state['outstanding_dispatches']), (0, 0))


if __name__ == '__main__':
    unittest.main()
