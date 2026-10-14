# Lazy animation parameter preparation

The class-0 [identity binding path](ANIMATION_IDENTITY_API.md) now has a concrete preparation and reset lifecycle. The original helper, registration path and an update-tail reset loop were inspected. This establishes reuse between explicit resets, not a render-frame or physics-substep cadence.

## Preparation

The parameter context owns a byte array mapping parameter indices to groups, and a collection of 72-byte group records. Each group contains a callable object, a 16-bit tag and a prepared byte.

```text
prepare_parameter(context, parameter_index):
    group_index = context.parameter_to_group[parameter_index]
    if group_index == 255:
        return
    group = context.groups[group_index]
    if group.prepared != 0:
        return
    callback_context = null
    if context.owner != null:
        callback_context = address_of(context.owner.subobject)
    group.callback.virtual_slot_2(address_of(callback_context))
    group.prepared = 1
```

The original optional subobject is at owner offset 24. The callback receives the address of the temporary context pointer, not the pointer directly. The portable adapter supplies a caller-owned context object instead. The prepared byte changes after the callback returns. No in-progress flag is set before invoking the callback, and this helper contains no atomic operation or lock. A surrounding synchronization protocol cannot be inferred from the guarded scalar reader that follows it.

## Registration and mapping

The inspected registration route returns immediately when its supplied identifier collection is empty. Otherwise it appends one group, copies a callable object through virtual operations, stores the supplied 16-bit tag, and initializes prepared to zero. It then visits supplied uint32 identifiers in order, looks each up through another context-owned map, and writes the new group index into the parameter-to-group byte array for successful lookups. Missing identifiers are skipped. The stored group index is the low byte of the resulting group count minus one; this function alone does not establish a safe maximum group count or validate the 255 sentinel collision.

The group-copy helper also copies the prepared flag from its source. Copying a group is therefore not inherently a reset. Registration's explicit clear is significant.

The identifier map used during registration is a further link to inspect. It has not yet been joined to authored parameter names or the 128-bit compiler map.

## Reset boundary

A larger animation update routine has two branches. One accumulates the supplied interval and retains a list of pending entries. The other adds the accumulated interval to the supplied interval, clears the accumulator and calls a further update routine. On the inspected normal path, a local reset gate initialized to true remains enabled. The accumulating branch leaves that gate false.

At the common tail:

```text
if reset_gate:
    for group in update_object.graph.parameter_context.groups:
        group.prepared = 0
```

The graph's parameter-context pointer used here is the same field selected by the class-0 scalar getter. The reset addresses the same collection, stride and prepared-byte offset used by preparation. This is a concrete ownership and lifecycle join, not merely a match to a byte value elsewhere in the image.

The reset occurs after branch work and before final temporary-resource release. Calling the outer update does not unconditionally reset the flags. Its eligibility branches, indirect callers and relationship to the physics scheduler remain unresolved. In particular, this evidence does not establish that newly ingested controls reach each animation or physics substep.

## Executable interface

`engine.animation_parameters` exposes `ParameterGroup`, `prepare_parameter` and `reset_parameter_groups`. The independent caller must explicitly choose the reset boundary. No automatic reset was added to the engine tick, since that would assert an unproved schedule.

```python
from engine.animation_parameters import ParameterGroup, prepare_parameter, reset_parameter_groups

samples = []
groups = [ParameterGroup(lambda context: samples.append(context))]
mapping = [0, 0, 255]  # two parameters share a producer; one has no group
prepare_parameter(0, mapping, groups, context='sample A')
prepare_parameter(1, mapping, groups, context='sample B')
assert samples == ['sample A']
reset_parameter_groups(groups, enabled=False)  # retained preparation
reset_parameter_groups(groups, enabled=True)   # explicit observed boundary
prepare_parameter(1, mapping, groups, context='sample C')
assert samples == ['sample A', 'sample C']
```

Bounds validation, exceptions and Python callback interfaces are adapter behavior. Callback exception tests check that the adapter does not mark a failed callback prepared; they do not reconstruct native exception unwinding. Native callback implementations and parameter values remain external inputs.

## Validation and next probes

The original preparation helper passed 48 isolated calls across absolute and relative arrays, owner/null contexts, mapped/sentinel parameters, initially prepared/unprepared groups and repeated reads. The callback was a synthetic returning stub. Six executions of the original reset block covered zero, one and four groups in absolute and relative storage; only the intended flag bytes changed. See the [receipt](animation_parameters_validation.json). The outer update was statically inspected, not emulated end to end. Four repository tests cover the portable lifecycle and bounds.

Next trace the group registration's identifier-map lookup and concrete callback objects, then the outer update's indirect caller and branch policy. These are separate from the already recovered reset loop.

Static evidence anchors: preparation `1412e9850`, registration `1412c9620`, group copy `1412fa7d0`, outer update `14131bf90`, reset block `14131c534` through `14131c594`, and downstream update `1412c6930`. No original payloads or disassembly are distributed.
