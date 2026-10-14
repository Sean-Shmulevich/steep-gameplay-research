# Runtime animation output adapter

`engine.animation_outputs` makes the previously documented [runtime conversion rules](../systems/animations/conversion/CLIENT_GUIDE.txt) executable over caller-owned buffers. This pass adds implementation coverage, not a newly recovered authored graph connection.

Supply runtime nodes in their actual stored order, each with its ordered output descriptors. `flatten_outputs` retains empty nodes and multiple outputs without sorting. The flattened table contains descriptors, not node identifiers. `resolve_output(table, source_index, binding_class)` retains class 8 or 9 alongside the selected descriptor.

```python
import struct
from engine.animation_outputs import OutputDescriptor, flatten_outputs, resolve_output, read_scalar

# Invented runtime snapshot: the first node has two outputs.
outputs = flatten_outputs(((OutputDescriptor(0), OutputDescriptor(4)), (),))
arena = struct.pack('<fI', 0.75, 1 << 16)
timeline = bytearray(320)
struct.pack_into('<f', timeline, 160 + 144, 0.25)
assert read_scalar(resolve_output(outputs, 0, 8), arena) == 0.75
assert read_scalar(resolve_output(outputs, 1, 9), arena, timeline) == 0.25
```

The read rules are:

```text
if descriptor has an owner:
    evaluate owner before reading output storage
if runtime class == 8:
    return float32(arena, descriptor.offset)
if runtime class == 9:
    handle = uint32(arena, descriptor.offset)
    return float32(timeline, (handle >> 16) * 160 + 144)
```

An owner requires an explicit `evaluate_owner` callback. Its Python interface is designed; the adapter does not reconstruct native evaluation scheduling or recursion guards. The callback may update the supplied buffers before the read. Callback exceptions propagate. Bounds checks reject incomplete snapshots instead of attempting native memory access. Buffer lifetime and synchronization remain the caller's responsibility.

Class 9's result has no established seconds-based unit here. In particular, authored class 9 scalar or boolean references must not be passed through as runtime class 9 without the missing lowering step. Neither authored node order nor authored output indices have been proved to match this table. This API therefore stays separate from the independent engine's designed graph schema.

Four synthetic tests cover multi-output/empty-node ordering, class retention, timeline high-word selection, owner-before-read behavior, callback failure, unsupported classes and invalid snapshot bounds. They do not establish native graph selection or a playable authored graph.
