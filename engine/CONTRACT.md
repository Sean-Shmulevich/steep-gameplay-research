

### Broadphase pair lists

`engine/pose_broadphase_pair_lists.py`: `added_pair_count`, `added_pair_array`,
`removed_pair_count`, `removed_pair_array` (vtable `0x29ca8a0` slots 0x40, 0x48,
0x60, 0x68; RVAs `1940410`, `1940400`, `19403f0`, `19403e0`) over a flat object
view plus a `read(address, size)` callback, and `decode_pair_rows` for 24-byte
rows. The row decoder and callback are authored; offsets are evidence anchors.
Harness: `analysis/command-executor-audit/check_pose_broadphase_pair_lists.py`.

### Pair update step (0x18b8fa0)

`engine/pose_pair_update_step.py`: `run_pose_pair_update_step(controller, *, objects,
vcall, select, rebuild, jobs, release) -> True`.

- **Native order.** It sets phase 1, then calls update (+0x90), the removed count and
  array (+0x60/+0x68), select, rebuild, the new count and array (+0x40/+0x48), jobs, the
  conditional release, finish (+0x88), the frame increment, the broadphase +8 and
  provider +0x180 stores, and phase 2.
- **Shared output.** One `PosePairOutputVector` (items, capacity 0x200, storage `INLINE`)
  is shared by select, rebuild and jobs. Release happens only when capacity is nonzero
  and the storage is external.
- **Getters.** `pose_dynamic_tree_broadphase_vcall(objects, update, finish=None)` recovers
  the observed class getters.
- **Supplied.** Select, rebuild, the jobs, the broadphase update and the allocator.
- **Receipt.** 512 native cases in `native/snow_host/pose_pair_update_step_validation.json`.
