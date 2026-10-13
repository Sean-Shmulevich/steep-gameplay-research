# Action callbacks can repopulate the cleared sample

The callback following action reset is now resolved for three constructor-backed action types. Each has a concrete path into the binding's action map. These implementations can **repopulate the sampled value immediately after clearing it**. The callback must not be replaced with an empty reset handler in a reconstruction.

The original player's active action subtype and device-source freshness remain unproved. This pass was static only: no game launch, attachment, input injection or native execution. The type labels below describe inspected behavior; they are not original class names or sport labels.

## Construction and map membership are connected

The ownership chain is now:

```text
binding configuration
    -> action-definition list
    -> type-dispatch factory
    -> concrete action allocation and initializer
    -> checked insertion into binding.map
    -> lookup/reset enumeration obtains that same stored action pointer
    -> concrete action callback after clearing
```

The binding initializer finds a matching configuration record, retains it, stores the record pointer in the binding and passes its action-definition list to the binding-map loader. Crucially, its receiver passed to the loader is the same binding-map member used by action lookup and reset; this is not an unrelated map with a similar layout.

For each definition, the loader retains the definition handle, calls a dispatcher and passes the returned action to a checked insertion helper. The dispatcher tests supported definition types in order and tail-calls the matching factory. Unknown or unavailable definitions can return null. This pass inspected three of its six factory branches, not all supported action kinds.

The checked insertion requires a nonnull action and resolved definition owner. Ordinary action IDs reject an existing key before inserting the action pointer. Two special IDs use a generated key based on a map-owner counter instead, then increment that counter; the counter is an allocation/index mechanism, not a sample generation. One sentinel ID is rejected. Failed insertion leads the caller through cleanup of the newly constructed action.

The three inspected factories initialize the shared sample fields, install their distinct concrete virtual tables and invoke type-specific initialization. The callback slot used by the reset helper resolves to the implementations described below. The installed table is proved by the constructor store, rather than guessed from a search for writes to a common displacement.

This establishes a supported constructed-and-inserted type family. It does not prove which member a particular runtime action ID selects in the player's current binding configuration.

## Scalar callback with alternative sources

The first type requires its selected configuration object. It evaluates one or more configured source groups, using a source-dependent count to choose between a single-source helper and a multi-source helper. It retains a successful boolean result and a scalar output from those helpers.

After evaluation, an ordinary mode assigns the result to the action status byte. A selected special mode toggles the previous status only when the boolean result is true; a false result leaves that mode's previous status unchanged. It then writes the evaluated scalar to the **first lane of the sampled vector**.

The zeroing reset ran first, so untouched sample lanes remain zero on this route. The source helpers and their upstream device caches are still separate decoding work. This report does not substitute a guessed axis value or declare that the scalar is a physical velocity.

## Two-axis callback: a recoverable combination formula

The second type evaluates four logical directions. Each direction is true when either of two configured boolean source queries succeeds. With functional labels `negative_x`, `positive_x`, `positive_y` and `negative_y`, the combination is:

```text
negative_x = query(first_x_binding)  OR query(alternate_first_x_binding)
positive_x = query(second_x_binding) OR query(alternate_second_x_binding)
positive_y = query(first_y_binding)  OR query(alternate_first_y_binding)
negative_y = query(second_y_binding) OR query(alternate_second_y_binding)

raw = [float(positive_x) - float(negative_x),
       float(positive_y) - float(negative_y),
       0, 0]
```

These signs and lane placement follow the instructions. The functional direction labels are ours. They do not identify keyboard keys, controller axes, camera space, or ski/snowboard controls. Opposite directions cancel, and an unmodified diagonal has length approximately square root of two.

The callback writes this vector into a subordinate processing object, then conditionally invokes that object's vector-processing callback. A resolved configuration flag can bypass the processing call. The returned or bypassed vector is then published through the action's sample fields:

```text
processor.raw = raw
processor.working = raw
if processor_configuration_is_absent_or_processing_enabled:
    processor.working = processor.process(processor.working)
processor.result = processor.working

action.raw_vector = processor.raw
action.sampled_vector = processor.result
v = action.sampled_vector
squared_length = dot_four_lanes(v, v)
action.magnitude = sqrt(squared_length)

if abs(squared_length) <= float32(9.999999439624929e-11):
    action.direction = v
else:
    action.direction = v * approximate_reciprocal_sqrt(squared_length)

action.status = abs(action.magnitude) > float32(9.999999747378752e-6)
```

The finite-input arithmetic order can be expressed more precisely, with `f32` rounding each marked operation:

```text
xx, yy, zz, ww = f32(x*x), f32(y*y), f32(z*z), f32(w*w)
n = f32(f32(xx + zz) + f32(yy + ww))
magnitude = float32_sqrt(n)
if abs(n) <= float32(9.999999439624929e-11):
    direction = [x,y,z,w]
else:
    r = native_simd_rsqrt_estimate(n)
    correction = f32(3 - f32(f32(r*n)*r))
    factor = f32(correction * f32(0.5*r))
    direction = [f32(component*factor) for component in [x,y,z,w]]
status = abs(magnitude) > float32(9.999999747378752e-6)
```

The reciprocal square root uses the SIMD estimate and one Newton refinement; a portable exact-square-root substitute would be a derived numerical approximation, not promised bit equality. For finite ordinary vectors, the small-vector branch retains the vector rather than replacing it with a normalized direction. The status comparison is strict.

This gives semantics to the previously unnamed fields **for this concrete type**: the first vector is a processed sample, the adjacent vector is its normalized-or-small direction, and the adjacent scalar is its magnitude. That does not establish those meanings for every action subclass.

The getter used by snow and motion reads `sampled_vector`, not `direction`. Therefore this callback does not establish that the consumed input has unit magnitude. Any normalization performed by the unresolved subordinate processor is a separate question. A reconstruction that silently reads the direction instead would alter analog magnitude and potentially diagonal behavior.

## Edge/timing callback with a source scalar

The third type requires a selected configuration, derives a source selector from it, and queries a source boolean. Its branches use retained prior boolean state to distinguish changes. One branch includes delay/repeat-like comparisons involving two retained clock readings and configured scalar intervals. The clock producer and interval conversion are not closed here, so these are not yet documented seconds or input-generation timestamps.

At the end of the accepted path it obtains a source scalar from the input-context storage, or zero under a source predicate, then writes that scalar to the first lane of the sampled vector. It also writes the computed status and retained prior boolean. This is another concrete repopulation path, but the complete edge/timer state machine is not expressed as a portable formula in this pass.

## Reset, callback gates and locking

The enclosing reset still clears the sampled vector, adjacent vector and scalar storage before selecting a callback. If the action's optional owner exists and its suppression byte is nonzero, the callback is skipped and the cleared values remain on this route. If it runs, the concrete subtype's own missing-configuration branches can also return without repopulation.

Thus a zero observation can reflect suppression, unavailable configuration, a source sample or cancellation of opposing directions. It cannot identify one of those causes without the relevant subtype and gates.

The binding-change callers inspected in [the preceding follow-up](ACTION_PUBLICATION_FOLLOWUP.md) run this work under manager exclusive accounting. A separately retained manager refresh routine also traverses active contexts and invokes the same reset callback path; its existence does not establish a per-frame cadence. Neither route supplies a new sample commit counter.

## What this closes and what remains

**Closed for the inspected type family:** binding-owned map population, definition dispatch to concrete construction, the actual callback-table slot used after reset, and concrete writes that repopulate the sampled vector. The two-axis callback also supplies an executable-level combination formula and distinguishes sample, direction and magnitude storage.

**Still open:** the player's selected action subtype/definition, all other factory branches, the subordinate vector processor's concrete method, source-query ownership and update cadence, and the order in which a particular device update, action refresh, motion ingestion and snow sample occur. Construction and map membership do not by themselves establish current execution.

The most useful next target is the two-axis initializer's subordinate processor construction and virtual processing method. For exact input age, the source query helpers and their producers still need a writer-backed event/version join. The local timer values in the third subtype must not be reused as an input commit generation.

## Static evidence scope

The analysis used the same image SHA-256 recorded in [the scheduler input audit](SCHEDULER_INPUT_AUDIT.md). A bounded constructor-candidate search was followed by direct inspection of factory stores, table entries, tail-dispatch branches, binding-map loader calls and the exact map-slot writes. Candidates were not promoted merely because their fields matched.

The map insertion helper uses the same tagged-map lookup as the consumer, and its insertion wrapper stores the constructed action pointer in the returned value slot. The binding initializer explicitly passes its binding-map member to the loader. These receiver links are the material evidence for the closure.

The three inspected repopulation callbacks occupy 328, 638 and 730 instruction bytes in their complete inspected function ranges. No raw exports, action definitions, device payloads or game assets are included here. This establishes local static behavior, not full input parity or deterministic original-game replay.


### Suitable standalone reference work

A small reference module can implement the boolean-pair combination, optional injected processor, four-lane magnitude, small-vector rule and strict status threshold. Its source-query results and processed vector must remain explicit inputs. Tests should cover opposing-direction cancellation, diagonals, nonunit processed magnitude, zero vectors, both sides of the squared-length threshold and the strict activation threshold. Exact SIMD normalization requires either the original reciprocal-square-root estimate as an input or a clearly labeled scalar substitute. None of these tests would establish the original player's selected binding or device timing.
