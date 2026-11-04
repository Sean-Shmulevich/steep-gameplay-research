import struct
import unittest

from engine.pose_pair_link_jobs import run_pose_pair_link_jobs, pose_pair_worker_count, PAIR_WORKER_CALLBACK
from engine.pose_pair_link_worker import PoseFlatMemory, run_pose_pair_worker
from engine.pose_body_connectivity_retire import retire_pose_body_connectivity, reserve_pose_pointer_vector
from engine.pose_dispatch import dispatch_pose_workers, pose_dispatch_serial_atomics
try:
    from tests.test_pose_pair_link_worker import Services
except ImportError:  # discovered with tests/ as top level
    from test_pose_pair_link_worker import Services

P = 0x1000


def recorder(log):
    names = ('retire', 'retire_neighbors', 'rebalance', 'dispatch', 'merge_links', 'merge_neighbors')
    return {n: (lambda n: lambda *a: log.append((n,) + a))(n) for n in names}


class WorkerCountTests(unittest.TestCase):
    def test_count_capacity_and_cap(self):
        self.assertEqual(pose_pair_worker_count(0, 8), 1)
        self.assertEqual(pose_pair_worker_count(9, 8), 1)
        self.assertEqual(pose_pair_worker_count(10, 8), 2)
        self.assertEqual(pose_pair_worker_count(79, 8), 8)
        self.assertEqual(pose_pair_worker_count(1000, 0xFFFFFFFF), 32)
        self.assertEqual(pose_pair_worker_count(1000, 0), 0)
        self.assertEqual(pose_pair_worker_count(0xFFFFFFFF, 40), 32)


class OrchestrationTests(unittest.TestCase):
    def test_order_contexts_publication_and_dispatcher_reread(self):
        provider = bytearray(0x200); log = []
        for i in range(3): struct.pack_into('<Q', provider, 0x70 + 8 * i, 0x5000 + 0x100 * i)
        struct.pack_into('<I', provider, 0x17C, 77)
        current = ['d1']
        services = recorder(log)
        def retire(output, n):
            log.append(('retire', output, n)); current[0] = 'd2'
        def retire_neighbors(n):
            log.append(('retire_neighbors', n)); struct.pack_into('<Q', provider, 0x78, 0x9000)
        services.update(retire=retire, retire_neighbors=retire_neighbors)
        run_pose_pair_link_jobs(provider, P, 0xAAAA, 25, 0xBBBB, current_dispatcher=lambda: current[0],
                                worker_capacity={'d1': 3, 'd2': 1}.get, **services)
        self.assertEqual(log, [('retire', 0xBBBB, 3), ('retire_neighbors', 3),
                               ('rebalance', [0x5028, 0x9028, 0x5228], 3),
                               ('dispatch', 'd2', 3, PAIR_WORKER_CALLBACK, P + 0x70),
                               ('merge_links', 3), ('merge_neighbors', 3)])
        self.assertEqual(struct.unpack_from('<QII', provider, 0x170), (0xAAAA, 25, 0))

    def test_zero_capacity_still_calls_every_stage_with_zero(self):
        log = []
        run_pose_pair_link_jobs(bytearray(0x200), P, 1, 100, 2, current_dispatcher=lambda: 0,
                                worker_capacity=lambda d: 0, **recorder(log))
        self.assertEqual([e[-1] for e in log[:3]], [0, 0, 0]); self.assertEqual(log[2][1], [])


class RetireDispatchWorkerCompositionTests(unittest.TestCase):
    def test_retired_links_feed_the_dispatched_workers(self):
        """Compose the reconstructed retire, dispatcher and pair worker around 18ddc40."""
        mem = PoseFlatMemory(); provider = mem.add(P, bytearray(0x200))
        owners = [0x2000 + 0x100 * i for i in range(3)]
        for i, o in enumerate(owners):
            raw = mem.add(o, bytearray(0x80)); struct.pack_into('<Q', raw, 0, P)
            struct.pack_into('<Q', provider, 0x70 + 8 * i, o)
        kind = mem.add(0x3000, bytearray(0x60)); struct.pack_into('<H', kind, 0x50, 7)   # static class
        for b in (0x3100, 0x3200):
            raw = mem.add(b, bytearray(0x100)); struct.pack_into('<Q', raw, 0x30, 0x3000)
        mem.add(0x3800, bytearray(32)); struct.pack_into('<Qi', provider, 8, 0x3800, 0); struct.pack_into('<i', provider, 0x1C, -1)
        npairs = 25
        mem.add(0x4000, b''.join(struct.pack('<QQQ', 0x3100, 0x3200, k) for k in range(npairs)))
        links = [0x6000 + 0x100 * i for i in range(3)]
        for t in links: mem.add(t, bytearray(0x90))
        s = Services(mem)
        dispatcher = bytearray(0x728); struct.pack_into('<I', dispatcher, 0x10, 4)
        cas, add = pose_dispatch_serial_atomics(dispatcher); queue = []
        invoked = []
        def invoke(callback, owner, caller):
            self.assertEqual(callback, PAIR_WORKER_CALLBACK); invoked.append(owner)
            run_pose_pair_worker(mem, owner, s)
        def dispatch(d, n, callback, table):
            slots = [struct.unpack_from('<Q', provider, table - P + 8 * i)[0] for i in range(n)]
            dispatch_pose_workers(d, n, callback, slots, atomic_compare_exchange=cas, atomic_add=add,
                                  enqueue=queue.append, take=lambda: queue.pop(0) if queue else None,
                                  invoke=invoke, notify=lambda h: None, wait=lambda: self.fail('wait'))
        run_pose_pair_link_jobs(provider, P, 0x4000, npairs, None, current_dispatcher=lambda: dispatcher,
            worker_capacity=lambda d: struct.unpack_from('<I', d, 0x10)[0],
            retire=lambda out, n: retire_pose_body_connectivity(provider, links, n,
                queue_owners={o: mem.regions[o] for o in owners}, queue_arrays=mem.regions,
                detach=lambda t, sel: None, reset=lambda t: None,
                reserve=lambda d, c: reserve_pose_pointer_vector(d, c, allocator=s)),
            retire_neighbors=lambda n: None, rebalance=lambda c, n: None, dispatch=dispatch,
            merge_links=lambda n: None, merge_neighbors=lambda n: None)
        self.assertEqual(invoked, owners)                    # caller slot0, then helped queue
        destroyed = [e[1] for e in s.log if e[0] == 'destroy']
        # serial caller claims every pair: one recycled link, then 5 refills of 5 (4 later recycled each)
        self.assertEqual(destroyed[0], links[0]); self.assertEqual(len(destroyed), 20)
        self.assertEqual(sum(e[0] == 'refill' for e in s.log), 5)
        self.assertEqual(mem.d(owners[0] + 0x10), npairs)
        self.assertEqual([mem.d(o + 0x10) for o in owners[1:]], [0, 0])
        self.assertEqual([mem.d(o + 0x30) for o in owners[1:]], [1, 1])  # unused recycled links remain
        self.assertEqual(mem.d(P + 0x17C), npairs + 3)        # every worker's final failed claim


if __name__ == '__main__':
    unittest.main()
