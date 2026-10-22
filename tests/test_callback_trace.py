import unittest
from engine.callback_trace import pair_receiver_calls


def event(kind,tick,thread=1,target=True,started=4,requested=4):
    return dict(kind=kind,tick=tick,thread=thread,target=target,started=started,requested=requested)


class CallbackTraceTests(unittest.TestCase):
    def test_nested_interleaved_threads(self):
        r=pair_receiver_calls([event('enter',1),event('enter',2,2),event('enter',3,target=False),
                               event('return',4,2),event('return',5,target=False),event('return',6)])
        self.assertTrue(r['pairing_complete'])
        self.assertEqual([p['duration_ticks'] for p in r['pairs']],[2,2,5])
        self.assertFalse(r['job_completion_established'])
    def test_balanced_totals_do_not_prove_pairs(self):
        r=pair_receiver_calls([event('return',1),event('enter',2)])
        self.assertFalse(r['pairing_complete'])
        self.assertEqual(r['unmatched_entries'],1)
    def test_changed_request_not_hidden_by_matching_return(self):
        r=pair_receiver_calls([event('enter',1),event('return',2,started=5,requested=5)])
        self.assertTrue(r['pairing_complete'])
        self.assertFalse(r['pairs'][0]['request_unchanged'])
    def test_loss_and_wrong_receiver_invalidate(self):
        for opts in ({'dropped':1},{'incomplete':1}):
            self.assertFalse(pair_receiver_calls([event('enter',1),event('return',2)],**opts)['pairing_complete'])
        self.assertFalse(pair_receiver_calls([event('enter',1),event('return',2,target=False)])['pairing_complete'])
