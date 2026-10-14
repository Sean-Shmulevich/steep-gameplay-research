# Animation update deferral policy

The local policy that surrounds [parameter-group resets](ANIMATION_PARAMETER_LIFECYCLE.md) is now executable in `engine.animation_update_policy.plan_animation_update`. It is a branch planner for the inspected update routine, not a replacement scheduler. It assumes the graph-presence gate has passed; the outer routine returns early when no graph is attached.

## Exact gate and interval effects

```text
pending_count = pending_count_word & 0x1fffffff
deferred = false
if pending_count != 0 and graph_state_word == 0 and (mode_flags & 5) == 1:
    counter = (counter + 1) & 255
    deferred = counter < threshold

if deferred:
    pending-entry callbacks receive the supplied float32 interval
    accumulated = float32(interval + accumulated)
    retain counter
    skip parameter-group reset
else:
    update_interval = float32(interval + accumulated)
    accumulated = 0
    counter = 0
    perform further graph-update work using update_interval
    enable the parameter-group reset at the common tail
```

The strict comparison is unsigned and occurs after the byte increment. Counter 255 wraps to zero before comparison. Threshold zero therefore never selects deferral through this gate. Pending count ignores the high three bits. Mode bit 0 must be set and bit 2 clear; this test does not use the other mode bits. A nonzero graph state word prevents deferral. Its producer and semantic name remain unresolved.

Deferred calls still execute pending-entry callbacks. They are not complete animation pauses. The current interval reaches those callbacks before being added to the retained accumulator. A full update consumes the combined interval and clears the counter. This distinction matters for reconstruction: retaining parameter preparation does not imply that all animation callbacks stop running.

The adapter rounds each supplied interval to float32 before addition. It rejects nonfinite inputs and float32 overflow as a designed guard; native arithmetic has no equivalent validation in these blocks. Finite negative intervals are not clamped. Returned `branch_interval` is the supplied interval for the deferred callback path and the combined interval for the full-update path. Returned `reset_parameter_groups` describes the inspected branch's reset eligibility, not a request to reset every engine tick.

## Interface identity and construction

The update function is installed at virtual slot offset `0x50` of an interface subobject located 24 bytes into its owning object. The same interface has the parameter-group registration wrapper at slot `0xd0`. This joins update and registration to one constructed interface rather than relying on adjacent code addresses.

The constructor installs the interface table and initializes the relevant counter, accumulator and threshold to zero. It clears the low three mode bits. That initial configuration does not enable deferral. The named [threshold producer](ANIMATION_THRESHOLD_PRODUCER.md) refreshes a seven-byte settings record before the gate and supplies the threshold from a resolved component. The constructor does not establish active settings.

The registration wrapper copies the incoming uint32 identifier range into a temporary collection, obtains a 16-bit tag, clones the supplied callable through its virtual interface, and registers the resulting group if a graph is attached. It destroys temporary callable storage afterward and also clears the incoming callable container. A reconstruction should therefore not assume that the wrapper simply borrows the caller's callable unchanged. Exact allocation and callable ownership semantics remain outside the portable group API.

A second registration path rebuilds groups from saved configuration: it resolves parameter identifiers, gathers per-group identifier collections, clears the existing groups, and re-registers callbacks and tags. The clear helper zeroes the group count and fills the parameter-to-group byte array with 255, explaining the preparation sentinel before registration. It also has an early failure when a required configured mapping cannot be matched. The concrete callback classes and the relationship of these identifiers to authored parameter names remain open.

## Example

```python
from engine.animation_update_policy import plan_animation_update

state = dict(counter=0, accumulated=0.0)
results = []
for _ in range(3):
    result = plan_animation_update(
        pending_count_word=1, graph_state_word=0, mode_flags=1,
        threshold=3, interval=0.125, **state)
    results.append(result)
    state = {key: result[key] for key in state}
assert [r['deferred'] for r in results] == [True, True, False]
assert results[-1]['branch_interval'] == 0.375
assert state == {'counter': 0, 'accumulated': 0.0}
```

These are invented settings and intervals. No claim is made that gameplay uses threshold 3 or runs at the corresponding cadence.

## Validation and unresolved scheduling

Four repository tests cover accumulation, each gate, packed count masking, ignored mode bits, counter wrap, float32 rounding and rejected inputs. Original instruction execution matched 400 synthetic cases: 35 deferred and 365 full decisions, with the corresponding counter and accumulator effects. See the [receipt](animation_update_policy_validation.json). The gate and effect blocks were executed separately; intervening callbacks, full graph updates and scheduler dispatch were not emulated.

The next caller search can now target the constructed interface's slot `0x50`, using the owner-to-interface adjustment of 24 bytes. A call to some other object's slot `0x50` is not evidence of this dispatch. The component threshold-field writer, mode-bit setters, graph-state producer and concrete parameter callbacks are still needed to establish actual gameplay timing and input freshness.

Static anchors: update `14131bf90`; gate `14131bff8` through `14131c03a`; deferred accumulation `14131c2c3`; full accumulation `14131c322`; constructor `1412b7fd0`; interface table `142909790`; registration wrapper `1412c9500`; saved-configuration registration `14130da90`; group/mapping clear `1412cdb80`. All executable code here is independent Python; original image bytes and callable payloads remain private.
