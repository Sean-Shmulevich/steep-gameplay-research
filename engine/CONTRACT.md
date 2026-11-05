

### Broadphase pair lists

`engine/pose_broadphase_pair_lists.py`: `added_pair_count`, `added_pair_array`,
`removed_pair_count`, `removed_pair_array` (vtable `0x29ca8a0` slots 0x40, 0x48,
0x60, 0x68; RVAs `1940410`, `1940400`, `19403f0`, `19403e0`) over a flat object
view plus a `read(address, size)` callback, and `decode_pair_rows` for 24-byte
rows. The row decoder and callback are authored; offsets are evidence anchors.
Harness: `analysis/command-executor-audit/check_pose_broadphase_pair_lists.py`.
