> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Environment controller logic

The names below describe recovered roles. They do not assign physical units to authored values. These are static formulas, not game-verified behavior.

## Controller selection and update order

```python
aggregate = decode_resource(owner.selected_aggregate_record)
if aggregate is not None:
    use_alternate = (
        owner.alternate_enabled
        and owner.alternate_mode
        and aggregate.alternate_time_of_day_resource_available
    )
    owner.time_of_day = aggregate.alternate_time_of_day if use_alternate else aggregate.time_of_day
    owner.weather = aggregate.weather
    owner.wind = aggregate.wind

# Recovered local update sequence, after the outer eligibility gate.
advance_time_of_day(owner, delta, external_hold)
evaluate_properties(owner.time_of_day, owner.clock.time_of_day)
advance_weather_scalar(owner, delta, external_hold)
run_other_weather_selection_helpers(owner)  # unresolved writers/selection
evaluate_properties(owner.weather, owner.clock.weather_scalar * 100.0)
evaluate_properties(owner.wind, owner.clock.wind_scalar * 100.0)
```

The real update has additional selection and downstream consumers between these steps. The pseudocode preserves the local producer/evaluator ordering and does not claim that the listed writers are exclusive.

## Time of day

For finite values and positive cycle duration:

```python
if owner.selected_duration_index != INVALID:
    source = owner.duration_sources[owner.selected_duration_index]
    cycle_duration = source.clock.duration * source.duration_multiplier
else:
    cycle_duration = owner.stored_cycle_duration

if cycle_duration > 0:
    if not owner.hold_flag and clock.hold_count <= 0 and not external_hold and not global_hold:
        clock.time_of_day += (delta / 60.0) * 24.0 / cycle_duration

    if clock.time_of_day >= 24.0:
        clock.time_of_day = clamp(clock.time_of_day - 24.0, 0.0, 24.0)
        owner.crossing_count += 1
        owner.cyclic_counter = (owner.cyclic_counter + 1) % 7
        if clock.stop_target >= 24.0:
            clock.stop_target -= 24.0

if clock.hold_count <= 0 and clock.stop_enabled and clock.time_of_day >= clock.stop_target:
    clock.time_of_day = clock.stop_target
    clock.hold_count += 1
```

The wrap is not a general modulo. Starting at `23.9`, `delta=1` and `cycle_duration=10` adds `0.04`, giving `23.94`. Starting at `23.99` with the same values gives `0.03` after one crossing. Starting at `60` with a positive duration produces `24` after one subtraction and clamp, with one counter increment. These examples use abstract delta and duration units.

The wrap check can run while progression is held, provided the cycle duration is positive. A nonpositive cycle duration bypasses progression and that wrap block; the stop-target test still runs. Negative-value wrapping and repeated crossings for a large delta are absent from this writer.

## Weather argument producer

One recovered producer behaves as follows:

```python
if not external_hold and modifier_available and modifier_gate_allows_update:
    clock.remaining = max(clock.remaining - delta * modifier.rate, 0.0)
    if clock.remaining > 0.0:
        scalar = clock.destination + (clock.remaining / clock.duration) * (clock.start - clock.destination)
    else:
        scalar = clock.destination
    clock.weather_scalar = clamp(scalar, 0.0, 1.0)
```

For `start=0.2`, `destination=0.8`, `remaining/duration=0.5`, the scalar is `0.5` and the property evaluator receives `50`. At completion it receives `80`. The scalar is a track-selection/evaluation coordinate. It is not established as precipitation intensity, weather severity or elapsed seconds. This branch does not guard a zero denominator when remaining is positive, so valid authored/runtime duration is a precondition for this example.

## Property sampling and ordered preset overlays

```python
def sample(resource, property_index, time, output):
    entry_index = resource.property_map[property_index]
    if entry_index == MISSING:
        return FALLBACK_REQUIRED
    track = resource.entries[entry_index].track
    if track.count_gate != 0:
        track.evaluate(time, output, cursor_hint)  # concrete implementation unresolved
    # A zero count-like gate leaves output as supplied on this branch.

def evaluate_float(controller, property_index, time, initial_output):
    primary = decode_resource(controller.primary_record)
    if primary is None or controller.base_resource is None:
        return initial_output

    value = initial_output
    # Base selection can fall back from selected base to primary, then to a bound property.
    value = sample_selected_base_or_fallback(controller, property_index, time, value)
    for overlay in controller.overlays:  # stored order
        resource = decode_resource(overlay.resource_record)
        if resource is None or overlay.mode == 2:
            continue
        entry_index = resource.property_map[property_index]
        if entry_index == MISSING:
            continue
        if not resource.entries[entry_index].enabled:
            resource.property_map[property_index] = MISSING
            continue
        sample_value = sample(resource, property_index, time, 0.0)
        value += overlay.weight * (sample_value - value)
    return value
```

The map index and track pointer follow a constructor-joined controller resource. The final track evaluator remains unknown, so the pseudocode deliberately leaves interpolation and key-time decoding inside `track.evaluate`.

With base `10`, overlay samples `20` and `0`, each at weight `0.5`, list order gives `10 -> 15 -> 7.5`. Reversing them gives `10 -> 5 -> 12.5`. Equal weights do not remove order dependence.

Automatic overlay weight refresh uses another clock:

```python
tick_duration = unsigned_conversion_trunc(float32(30000) * requested_duration)
start_tick = clock_pointer.value
end_tick = start_tick + tick_duration

if resource_available and not overlay.manual_weight and overlay.transition_active:
    elapsed = unsigned_difference(current_tick, start_tick)
    fraction = elapsed / unsigned_difference(end_tick, start_tick) if end_tick != start_tick else 1.0
    weight = clamp(fraction, 0.0, 1.0)
    if overlay.mode == 1:
        weight = 1.0 - weight
    overlay.weight = weight
```

Tick duration is a numeric conversion, not proof of a 30 kHz clock. Under ordinary finite nonnegative inputs, elapsed halfway between the stored endpoints gives weight `0.5`. Endpoint cleanup and optional completion callbacks follow the refresh; mode-1 overlays near zero can be removed. No atomic snapshot or cross-thread order is implied by these local operations.
