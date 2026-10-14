# Clock holds, accumulation and child propagation

[The clock-tree adapter](../../engine/clock_tree.py) extends the [local interval formula](WORLD_CLOCK.md) through the rest of the clock update. It reconstructs state transitions over an explicit immutable tree. It does not operate a native process or pause the scheduler.

## Deferred hold requests

The inspected hold and release leaves perform an atomic increment or decrement of the pending signed 32-bit counter. They do not directly change the current interval or current hold count.

At the next clock update, the routine saves the previous hold count and interval, adds pending holds into the current hold count with 32-bit wrapping, then clears pending holds. A positive resulting count forces the processed input to zero. Zero and negative counts take the ordinary scaling path. There is no clamp to zero in the two request leaves or the inspected consumption block.

Nested requests therefore need balanced releases. The independent `request_hold` returns new state and models one increment/decrement, including wrapping. It is not an atomic Python synchronization primitive. The native request operations are atomic, but the inspected consumption sequence loads, adds and clears separately; caller serialization and concurrent-request behavior remain unproved. Do not expose these native fields as a safe pause API based on this model.

## Remaining update operations

After interval, reciprocal and integer-tick calculation:

```text
if hold_count <= 0:
    toggle ^= 1

if accumulate:
    counter = wrap_u32(counter + 1)
    accumulated_ticks = wrap_u64(accumulated_ticks + zero_extend_u32(ticks))
    divided_ticks = accumulated_ticks // 30

lock child collection
for child in stored order:
    if child.use_parent_previous:
        child_input = f32(parent.previous_interval * 1000)
    else:
        child_input = parent.processed_input_before_division
    update_clock(child, child_input, accumulate)
unlock child collection
```

The child source must retain the parent's processed input before its division by 1000. Multiplying the rounded interval back by 1000 is not necessarily bit-equivalent. The previous-source branch instead uses the parent's interval from before this update.

The accumulation flag gates counters and accumulated time, not interval calculation, toggling or child traversal. A held clock still increments its invocation counter when accumulation is enabled. A child using its parent's previous interval can advance for an update even while the parent's newly produced interval is zero. The child still applies its own holds and scales.

## Runnable example

```python
from engine.clock_tree import ClockState, request_hold, advance_clock

root = ClockState(interval=0.25, children=(
    ClockState(),
    ClockState(use_parent_previous=True),
))
root = request_hold(root)
first = advance_clock(root, 100.0)
assert first.interval == 0.0
assert first.children[0].interval == 0.0
assert first.children[1].interval == 0.25
second = advance_clock(first, 100.0)
assert second.children[1].interval == 0.0
```

The records, API names and immutable ownership are our design. The adapter rejects shared/cyclic trees, more than 256 nodes and depth above 64. These are inspection limits, not recovered engine limits. Finite-value restrictions follow the local interval adapter. Native resource ownership, recursive locking, thread scheduling and callback execution are excluded.

## Validation

[160 original-instruction tree comparisons](clock_tree_validation.json) used a parent and two children with varied holds, pending requests, source flags, scales, accumulation gates, negative inputs and integer wrap boundaries. All implemented scalar/state fields matched exact bits. Ten additional comparisons executed the original increment/decrement leaves at signed counter boundaries. Lock/unlock helpers were replaced by return stubs. This validates serial update behavior, not native synchronization or lock implementation.

Five repository tests cover balanced nested holds, the previous-interval child after a hold, accumulation-disabled updates, wrapping and rejection of shared ownership without input mutation. The full runtime remains independently scheduled; these recovered clocks have not been silently substituted into its fixed-step policy.

## Consequence for scheduler stepping

These clocks can explain paused simulation time, but they do not establish stopped work. Child traversal continues, counters can advance, and component dispatch gates are separate from zero interval selection. Safe original-game stepping still needs scheduler submission exclusion, returned workers, stable ownership and a way to advance one intended generation. The [scheduler roadmap](../../engine/SCHEDULER_ROADMAP.md) retains those gates.
