import unittest
from engine.mixed_scheduler import MixedScheduler


def scheduler(definitions, mappings, slots=None):
    return MixedScheduler(definitions, queue_policy=dict(shared_default=2,
        worker_slots=[True, True] if slots is None else slots, jobs=mappings))


class WorkerTopologyTests(unittest.TestCase):
    def test_lowest_bit_local_owner_and_shared_filter(self):
        m = scheduler([dict(id=n, kind='callback') for n in ('local','shared')], {
            'local': dict(category=0, limit=1, required_mask=3, excluded_mask=1),
            'shared': dict(category=0, limit=1, excluded_mask=1)})
        m.submit('local'); m.submit('shared')
        before = m.snapshot()
        self.assertEqual(m.ready(worker_index=0), ['local'])
        self.assertEqual(m.ready(worker_index=1), ['shared'])
        self.assertEqual(before, m.snapshot())
        with self.assertRaises(ValueError): m.reserve('local', worker_index=1)
        self.assertEqual(before, m.snapshot())
        self.assertEqual(m.run_ready(worker_index=1), 1)
        self.assertEqual(m.snapshot()['jobs']['local']['state'], 'SCHEDULED')
        self.assertEqual(m.run_ready(worker_index=0), 1)

    def test_two_workers_claim_disjoint_ranges_and_delay_release(self):
        m = scheduler([dict(id='range', kind='range', receivers=list(range(4)),
                            chunk_size=2, tail_threshold=0, successors=['end']),
                       dict(id='end', kind='terminal')],
                      {'range':dict(category=0, limit=2)})
        m.submit('range')
        a = m.reserve(worker_index=0); b = m.reserve(worker_index=1)
        ra = m.claim_range(a); rb = m.claim_range(b)
        self.assertEqual((ra.start,ra.count,rb.start,rb.count), (2,2,0,2))
        self.assertEqual(m.snapshot()['jobs']['range']['remaining'],0)
        m.execute_range(b,rb); m.finish_dispatch(b)
        self.assertEqual(m.snapshot()['jobs']['end']['terminal_begins'],0)
        self.assertEqual(m.snapshot()['jobs']['range']['executions'],1)
        m.execute_range(a,ra); m.finish_dispatch(a)
        self.assertEqual(m.snapshot()['jobs']['end']['terminal_begins'],1)
        events = m.snapshot()['trace']['records']
        reserved = [e for e in events if e['kind']=='mixed_dispatch_reserved']
        self.assertEqual([e['worker_index'] for e in reserved], [0,1])

    def test_shared_callback_reserved_only_once(self):
        m = scheduler([dict(id='c',kind='callback')], {'c':dict(category=0,limit=1)})
        m.submit('c'); token = m.reserve(worker_index=0)
        self.assertIsNone(m.reserve(worker_index=1))
        m.execute_callback(token); m.finish_dispatch(token)

    def test_missing_worker_rejected_without_mutation(self):
        m = scheduler([dict(id='c',kind='callback')], {'c':dict(category=0,limit=1)}, [True,False])
        m.submit('c'); before=m.snapshot()
        for worker in (None, True, -1, 1, 2):
            with self.assertRaises(ValueError): m.reserve(worker_index=worker)
        self.assertEqual(before,m.snapshot())
        with self.assertRaises(ValueError):
            scheduler([dict(id='c',kind='callback')], {'c':dict(category=0,limit=1,required_mask=4)})

    def test_worker_cannot_reserve_again_before_return(self):
        m = scheduler([dict(id=n,kind='callback') for n in ('a','b')],
                      {n:dict(category=0,limit=1) for n in ('a','b')})
        m.submit('a');m.submit('b')
        token = m.reserve(worker_index=0)
        before=m.snapshot()
        self.assertEqual(m.ready(worker_index=0), [])
        self.assertIsNone(m.reserve(worker_index=0))
        with self.assertRaises(ValueError):m.reserve('b',worker_index=0)
        self.assertEqual(before,m.snapshot())
        m.execute_callback(token);m.finish_dispatch(token)
        self.assertEqual(m.ready(worker_index=0), ['b'])
