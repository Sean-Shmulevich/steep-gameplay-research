
- 2026-11-04 Live riding-state connectivity check (read-only, offline evaluation): two director-startup sessions with forward holds, 11 snapshots ([receipt](../native/snow_host/pose_connectivity_live_ride_validation.json), [LINK_SOLVER](../docs/reconstruction/LINK_SOLVER.md) "Live snapshot check (riding state)"). While riding, both player bodies had a controller and nonempty +0x80 rings, under the controller found by the world scan, with 2 to 11 provider-tree nodes. During a crash tumble, the bodies detached and world rings reached 27 links. Native `18b8860` in Unicorn matched the Python chain in 63 of 63 comparisons. 55 of them were nontrivial: up to 20 rows, 60 process, 41 pool-return and 2 allocator calls, and 5,709 changed bytes. There were 0 mismatches, 0 coverage gaps and no errors. Limits: snapshots are not atomic, services are stubbed, no landing moment was isolated, and no in-game invocation was observed. No engine code was changed.
- Reconstructed `1989e60` (pair link free-list rebalance) as `engine/pose_link_free_list_rebalance.py`;
  512-case Unicorn receipt, 9 unit and composition tests, bound as the orchestration's rebalance service.
- Reconstructed the pair-link post-dispatch merges `18df4e0` and `18df630` plus the link sort comparator `18df4a0` (`engine/pose_pair_link_merge.py`); 1,280 native comparisons, composed with retire, dispatcher and pair worker inside `18ddc40`. Static lead: `18dea90` neighbor-tree walk, tree inserts and the 8-byte sort remain supplied.
- Pair link worker services: reconstructed the pair filter 0x18deb70
  (`engine/pose_pair_link_filter.py`, 512 Unicorn cases) and the external-contacts
  snapshot fill 0x18e0ad0 (`engine/pose_pair_external_contacts.py`, 512 Unicorn cases),
  with tests that bind each into `run_pose_pair_worker`. Predicate targets, the pool
  take 0x18dd100 and two obfuscated stubs stay supplied.
- Reconstructed `18dfa10` (flagged-pair neighbor-record update) as
  `engine/pose_flagged_neighbor_update.py`. It includes append `18dccb0`, reserve
  `18df1e0` and float32 composition `18c16e0`.
  - Found that `18e0a60` forwards the tree index in r8d. Added
    `route_pose_flagged_pair_indexed` and bound it into `run_pose_pair_worker`'s
    flagged route in the composition tests.
  - 512 native cases entered through the router, plus 256 leaf cases.
  - 17 unit and composition tests. The tester factory and the tester remain supplied.
