import unittest
from engine.animation_batch import visit_animation_batch


class AnimationBatchTests(unittest.TestCase):
    def test_reverse_supplied_range(self):
        seen = []
        self.assertEqual(visit_animation_batch({'callback': seen.append}, ['a', 'b', 'c', 'unused'], 3), [2, 1, 0])
        self.assertEqual(seen, ['c', 'b', 'a'])
        self.assertEqual(visit_animation_batch({'callback': None}, []), [])

    def test_callback_is_captured_once(self):
        seen = []
        def first(receiver):
            seen.append(('first', receiver))
            job['callback'] = lambda value: seen.append(('next', value))
        job = {'callback': first}
        visit_animation_batch(job, [1, 2])
        visit_animation_batch(job, [3])
        self.assertEqual(seen, [('first', 2), ('first', 1), ('next', 3)])

    def test_receiver_entries_are_read_late(self):
        seen = []
        receivers = ['old', 'last']
        def callback(receiver):
            seen.append(receiver)
            receivers[0] = 'new'
        visit_animation_batch({'callback': callback}, receivers)
        self.assertEqual(seen, ['last', 'new'])

    def test_invalid_counts_and_callback_failure(self):
        for count in (-1, True, 2, 0x80000000):
            with self.assertRaises(ValueError):
                visit_animation_batch({'callback': lambda x: None}, [0], count)
        seen = []
        def fail(receiver):
            seen.append(receiver)
            raise RuntimeError('callback failed')
        with self.assertRaises(RuntimeError):
            visit_animation_batch({'callback': fail}, [1, 2])
        self.assertEqual(seen, [2])
