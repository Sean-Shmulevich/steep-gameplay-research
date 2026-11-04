"""Pair-link job orchestration around the per-worker pair callback.

Evidence: docs/reconstruction/LINK_SOLVER.md, "Pair link job orchestration"
(RVA 0x18ddc40).

Recovered local control flow only. The routine sizes a worker count, runs the
retire stage (0x18de440) and the neighbor retire stage (0x18de510) with that
divisor, rebalances the per-worker free lists (0x1989e60), publishes the pair
array on the provider, dispatches callback 0x1418df760 once per provider slot
through the global dispatcher (0x18b7ca0), then merges new links (0x18df4e0) and
new neighbor records (0x18df630). Every callee is a supplied service; tests bind
them to engine.pose_body_connectivity_retire, engine.pose_dispatch and
engine.pose_pair_link_worker where those reconstruct them.
"""
import struct

PAIR_WORKER_CALLBACK = 0x1418df760   # image address passed to the dispatcher
MAX_PAIR_WORKERS = 32


def pose_pair_worker_count(count, capacity):
    """min(32, min(capacity, count/10 + 1)) with 32-bit unsigned arithmetic."""
    count &= 0xFFFFFFFF
    workers = (count // 10 + 1) & 0xFFFFFFFF
    workers = min(workers, capacity & 0xFFFFFFFF)
    return min(workers, MAX_PAIR_WORKERS)


def run_pose_pair_link_jobs(provider, provider_address, pairs, count, output, *,
                            current_dispatcher, worker_capacity, retire, retire_neighbors,
                            rebalance, dispatch, merge_links, merge_neighbors):
    """0x18ddc40(provider, pairs, count, output).

    provider is a writable view of the provider object at provider_address.
    current_dispatcher() reads the global dispatcher pointer (0x143336610);
    worker_capacity(dispatcher) reads its u32 at +0x10. The pointer is read twice,
    once for sizing and again for the dispatch call. Services, in native order:
      retire(output, workers)                  0x18de440(provider, output, workers)
      retire_neighbors(workers)                0x18de510(provider, workers)
      rebalance(contexts, workers)             0x1989e60(&contexts, workers); contexts are
                                               slot owner + 0x28 for each worker slot
      dispatch(dispatcher, workers, callback, table)   0x18b7ca0; table = provider+0x70
      merge_links(workers)                     0x18df4e0(provider, workers)
      merge_neighbors(workers)                 0x18df630(provider, workers), tail call
    The pair array, count and a zero claim cursor are stored at +0x170/+0x178/+0x17c
    after rebalancing and before dispatch.
    """
    workers = pose_pair_worker_count(count, worker_capacity(current_dispatcher()))
    retire(output, workers)
    retire_neighbors(workers)
    contexts = [(struct.unpack_from('<Q', provider, 0x70 + 8 * i)[0] + 0x28) & 0xFFFFFFFFFFFFFFFF
                for i in range(workers)]
    rebalance(contexts, workers)
    struct.pack_into('<Q', provider, 0x170, pairs)
    struct.pack_into('<I', provider, 0x178, count & 0xFFFFFFFF)
    struct.pack_into('<I', provider, 0x17C, 0)
    dispatch(current_dispatcher(), workers, PAIR_WORKER_CALLBACK, provider_address + 0x70)
    merge_links(workers)
    merge_neighbors(workers)
