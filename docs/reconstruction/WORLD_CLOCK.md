# World-clock interval producer

The [component interval selector](ANIMATION_COMPONENT_DISPATCH.md) reads the ordinary or alternate world interval. Static inspection now connects both fields to embedded clock records and a shared update routine. [The implementation](../../engine/world_clock.py) reconstructs its local arithmetic; it does not replace the independent runtime's scheduling policy.

## Ownership and units

The world constructor initializes three adjacent clock records. The ordinary and alternate animation intervals are each at offset 24 within the first two records. A world initialization path invokes the same clock routine on all three records with input 33 and accumulation enabled. This establishes a concrete writer route, not the per-frame producer or every mode's update order.

The routine divides its processed input by 1000 to produce the interval and calculates integer ticks from that input multiplied by 30. This supports interpreting the input as milliseconds, the interval as seconds and ticks as 30000 per second. These unit names are inferred from arithmetic, not recovered symbols. Other consumers and the source of each per-frame input still need tracing.

## Local arithmetic

Every operation labeled f32 rounds to float32. Counter addition wraps signed int32.

```text
previous_hold_count = hold_count
previous_interval = interval
hold_count = wrap_i32(hold_count + pending_holds)
pending_holds = 0
value = f32(input_ms)

if hold_count > 0:
    value = +0.0
else if scale_enabled:
    value = f32(value * scale)
    if secondary_enabled:
        value = f32(value * secondary_scale)
        if value < f32(0.005):
            value = f32(0.005)
else if secondary_enabled:
    value = f32(value * secondary_scale)

interval = f32(value / 1000)
ticks = low_u32(truncate_i64(f32(f32(value * 30) + f32(0.1))))
if abs(interval) <= f32(0.00001):
    reciprocal = +0.0
else:
    reciprocal = f32(1 / interval)
```

The minimum applies only when both scale gates are enabled. It does not override a positive hold count. A negative or zero hold count takes the non-held path. Negative finite intervals are preserved on paths without that minimum; tick conversion is not a general nonnegative-duration guarantee.

The adapter validates finite float32 arithmetic and integer conversion bounds. Those restrictions are ours. It does not reproduce NaN comparison behavior or out-of-range native conversion. It returns interval, reciprocal, tick value and updated/history hold state without mutating the caller's object.

## Operations outside this adapter

After the implemented block, the routine toggles a field when the hold count is nonpositive. An accumulation argument gates an invocation counter and accumulated ticks. It also updates child clocks under a lock. A child flag selects either the parent's previous interval multiplied by 1000 or its newly processed input. These inspected operations are not implemented here and have not received the same instruction-emulation validation. Child ownership, lock behavior, full accumulated-time interpretation and source-clock scheduling remain open.

## Validation and live interpretation

[320 synthetic native comparisons](world_clock_validation.json) execute the original local block and compare exact float32 bits and integer fields with the adapter. They cover both scale gates, zero/negative inputs, pending holds, signed counter overflow, the minimum branch and reciprocal deadband. Five repository tests cover these transitions and adapter exclusions. No original process was used for those comparisons.

The [live animation pair](live_animation_call_validation.json) supplied interval `1.0` before and after the interface call. This producer makes an elapsed-time interpretation more plausible than an idle-animation identifier. It does not explain that particular value: the capture did not record the selected clock, incoming elapsed value, scales, holds or active clip. Debugger interruption can alter timing. Idle remains a proposed comparison condition, not a proved explanation. A follow-up should record those clock inputs alongside the packet during idle and movement, then compare with passive observations that do not stop the process.
