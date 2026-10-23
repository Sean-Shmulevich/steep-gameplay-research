import unittest
from engine.loading_destruction_batch import process_loading_destructions
from engine.loading_destruction_enqueue import enqueue_loading_destruction
from engine.loading_destruction import take_staged, publish_captured


class LoadingBatchTests(unittest.TestCase):
    def test_refused_insertion_can_publish_empty_work(self):
        owner = dict(staged=0, pending=0, busy=0,
                     ring=dict(slots=[], count=0, head=0, tail=0, capacity=0))
        admission = enqueue_loading_destruction(
            owner, 'payload', lock=lambda _: None, unlock=lambda _: None,
            grow=lambda *_: None)
        self.assertFalse(admission['inserted'])
        taken = take_staged(owner['staged'])
        owner['staged'] = taken['staged']
        owner['pending'] = publish_captured(owner['pending'], taken['captured'])['pending']
        def unexpected(*_):
            self.fail('empty ring must not reach destruction services')
        result = process_loading_destructions(
            owner, lock=lambda _: None, unlock=lambda _: None,
            allocation_lookup=unexpected, destroy_payload=unexpected,
            free_storage=unexpected)
        self.assertEqual(result['iterations'], 1)
        self.assertEqual(result['destruction_calls'], 0)
        self.assertEqual((owner['staged'], owner['pending'], owner['busy']), (0, 0, 0))

    def run_batch(self, values, pending, publish=False):
        owner = dict(pending=pending, busy=0,
                     ring=dict(slots=values, count=len(values), head=0,
                               capacity=max(1, len(values))))
        events = []
        def destroy(payload, flag):
            self.assertEqual(flag, 0)
            self.assertEqual(owner['busy'], 1)
            events.append(('destroy', payload))
            if publish:
                owner['pending'] += 1
        result = process_loading_destructions(
            owner, lock=lambda _: events.append('lock'),
            unlock=lambda _: events.append('unlock'),
            allocation_lookup=lambda p: ('metadata', p), destroy_payload=destroy,
            free_storage=lambda p, m: events.append(('free', p, m)))
        self.assertEqual(owner['busy'], 0)
        return owner, events, result

    def test_shortage_reuses_last_nonnull_pointer(self):
        owner, events, result = self.run_batch(['a'], 3)
        self.assertEqual(result['destruction_calls'], 3)
        self.assertEqual([e for e in events if isinstance(e, tuple) and e[0]=='destroy'],
                         [('destroy', 'a')]*3)
        self.assertEqual(owner['ring']['count'], 0)
        self.assertEqual(events[:4], ['lock', 'unlock', ('destroy', 'a'),
                                      ('free', 'a', ('metadata', 'a'))])

    def test_null_pop_clears_retained_pointer(self):
        _, _, result = self.run_batch(['a', None], 4)
        self.assertEqual(result['destruction_calls'], 1)
        self.assertEqual(result['iterations'], 4)

    def test_empty_batch_with_positive_budget_has_no_destructor(self):
        _, events, result = self.run_batch([], 3)
        self.assertEqual(events, ['lock', 'unlock']*3)
        self.assertEqual(result['destruction_calls'], 0)

    def test_later_publication_survives_fixed_budget(self):
        owner, _, result = self.run_batch(['a', 'b'], 1, publish=True)
        self.assertEqual(owner['pending'], 1)
        self.assertEqual(owner['ring']['count'], 1)
        self.assertEqual(result['iterations'], 1)

    def test_signed_nonpositive_budget_clears_without_popping(self):
        for pending in (0, 0x80000000, 0xffffffff):
            owner, events, result = self.run_batch(['a'], pending)
            self.assertEqual(events, [])
            self.assertEqual(owner['pending'], 0)
            self.assertEqual(owner['ring']['count'], 1)
            self.assertEqual(result['iterations'], 0)
