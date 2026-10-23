import unittest
from engine.command_disposal import clear_records, release_buffer


def ring(**values):
    return dict(storage='buffer', capacity=4, read=3, write=2, count=3,
                owns_storage=True, **values)


class CommandDisposalTests(unittest.TestCase):
    def test_wrap_and_release_order(self):
        state = ring()
        events = []
        def cleanup(storage, index):
            self.assertEqual(state['count'], 3)
            events.append(('cleanup', storage, index))
        def lookup(storage):
            self.assertEqual((state['count'], state['read'], state['write']), (0, 0, 0))
            events.append(('lookup', storage))
            return 'allocator-info'
        def free(storage, info):
            self.assertEqual(state['storage'], storage)
            events.append(('free', storage, info))
        release_buffer(state, cleanup=cleanup, allocation_lookup=lookup, free=free)
        self.assertEqual(events, [('cleanup', 'buffer', i) for i in (3, 0, 1)] +
                         [('lookup', 'buffer'), ('free', 'buffer', 'allocator-info')])
        self.assertEqual(state, dict(storage=None, capacity=0, count=0, read=0,
                                     write=0, owns_storage=True))

    def test_borrowed_still_cleans_records(self):
        state = ring(); state['owns_storage'] = False
        slots = []
        def forbidden(*args):
            self.fail('borrowed storage must not reach allocator')
        release_buffer(state, cleanup=lambda storage, i: slots.append(i),
                       allocation_lookup=forbidden, free=forbidden)
        self.assertEqual(slots, [3, 0, 1])
        self.assertIsNone(state['storage'])
        self.assertTrue(state['owns_storage'])

    def test_clear_preserves_allocation(self):
        state = ring()
        clear_records(state, cleanup=lambda storage, i: None)
        self.assertEqual((state['storage'], state['capacity'], state['owns_storage']),
                         ('buffer', 4, True))
        clear_records(state, cleanup=lambda *args: self.fail('empty clear cleaned a slot'))

    def test_cleanup_exception_does_not_claim_header_reset(self):
        state = ring(); before = state.copy(); visited = []
        def cleanup(storage, i):
            visited.append(i)
            if i == 0:
                raise RuntimeError('service failure')
        with self.assertRaises(RuntimeError):
            clear_records(state, cleanup=cleanup)
        self.assertEqual(visited, [3, 0])
        self.assertEqual(state, before)

    def test_free_exception_leaves_empty_allocation_attached(self):
        state = ring()
        def free(*args):
            raise RuntimeError('free failed')
        with self.assertRaises(RuntimeError):
            release_buffer(state, cleanup=lambda *args: None,
                           allocation_lookup=lambda storage: None, free=free)
        self.assertEqual((state['count'], state['read'], state['write']), (0, 0, 0))
        self.assertEqual((state['storage'], state['capacity']), ('buffer', 4))

    def test_invalid_state_refused_before_cleanup(self):
        for field, value in [('count', 5), ('read', 4), ('capacity', -1),
                             ('write', True), ('storage', None), ('owns_storage', 1)]:
            state = ring(); state[field] = value; before = state.copy()
            with self.subTest(field=field), self.assertRaises(ValueError):
                clear_records(state, cleanup=lambda *args: self.fail('invalid cleanup'))
            self.assertEqual(state, before)

    def test_empty_null_release(self):
        state = dict(storage=None, capacity=0, count=0, read=0, write=0, owns_storage=False)
        def forbidden(*args):
            self.fail('empty storage reached a service')
        release_buffer(state, cleanup=forbidden, allocation_lookup=forbidden, free=forbidden)
        self.assertTrue(state['owns_storage'])
