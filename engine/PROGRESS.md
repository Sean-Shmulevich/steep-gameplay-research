
- Broadphase pair lists: controller+0x28 object identified as the dynamic-tree
  broadphase (vtable `0x29ca8a0`, only class built by `193f450`); four count and
  array getters reconstructed and run natively, 512 cases, 24-byte pair rows.
- Pair update step `18b8fa0` is reconstructed (`engine/pose_pair_update_step.py`, 512/512
  native cases with real and fixture broadphase vtables, plus a composition test through
  select, rebuild, the jobs and retire). It is the per-substep driver, reached from the
  `Physic::UpdateBroadphase` body `1389a50`. Removed broadphase pairs feed the select and
  rebuild stages, new pairs feed the pair jobs, and one shared output vector carries the
  selection into the jobs' retire stage. Pair rows are confirmed as 24 bytes.
