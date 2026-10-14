# Component-to-animation update connection

The update interface is now connected to a concrete `KinoComponent` method and its factory. A named animation-time task configuration provides a receiver-dispatch lead. The component call is established statically; active player membership and execution relative to physics substeps remain unproved.

## Component identity and factory

The second component type used by `GetUpdateThresholds` resolves to a reflection descriptor named `KinoComponent`, with size 864 bytes. Its factory thunk reaches the constructor that clears the threshold byte. That is a type-based join, not an inference from a matching offset.

The constructor requests an animation interface from a manager's virtual factory. The manager's constructor installs a concrete table whose factory allocates the known animation-interface owner, calls its constructor and returns owner+24. The component stores that returned interface. Thus the component's later interface call uses the exact subobject whose update, registration and threshold policy were recovered previously.

The threshold byte's later writer remains open. A candidate stream reader that writes offset `0x358` belongs to `ProgressionCameraTransition`, as identified through its own virtual descriptor getter. It is not evidence of KinoComponent serialization. A search for direct byte writes is also not exhaustive: wider stores, adjusted pointers and indirect writers can escape it.

## Concrete update route

```text
KinoComponent virtual slot 0x270
    -> component update thunk
    -> component update method
    -> stored animation interface virtual slot 0x50
    -> recovered outer animation update
    -> threshold callback, deferral policy and conditional parameter reset
```

The component method first checks the interface's readiness result. The later update call additionally requires an auxiliary object and a nonnull field in that object. Non-dispatch paths perform other work; absence of this call does not imply that the whole component is idle.

Before calling the update slot it builds a packet containing a context pointer, a float32 interval, two zero status bytes and a byte initialized to one. The outer update reads its interval at packet offset 8 and writes status bytes. Their meanings must not be inferred solely from initial values.

## Interval selection

```text
interval = +0.0
if component_flags bit 1 is clear and owner exists and owner.world exists:
    if owner_flags bit 58 is set:
        interval = world.alternate_interval
    else:
        interval = world.ordinary_interval
```

The selected value is copied as float32. The ordinary and alternate sources are two fields within the same world object. They have not been identified as physics, render, scaled or unscaled clocks. A zero interval does not bypass the component's later dispatch gates by itself.

`engine.animation_component_clock.component_interval` implements this rule over explicit observations. `dispatch_component_update` expresses the three local call gates. Neither function schedules callbacks or identifies a player. Finite-value and bounds validation are adapter guards.

## Named task configuration

The scheduler-owner setup associates `AnimationUpdateTime` and `IAnimationComponent::UpdateTime` labels with a job record. Its callback field receives a generic receiver dispatcher that calls receiver virtual slot `0x270`. The KinoComponent table supplies the thunk above at that slot.

A generic batch consumer reads the same callback-field layout and walks a supplied pointer array in reverse order, applying a signed receiver adjustment before invoking the callback. The subsequent [batch binding audit](ANIMATION_BATCH_BINDING.md) establishes the concrete worker table and selects a different visitor without receiver adjustment. The actual receiver population remains unproved; static configuration does not establish player membership.

Nearby setup callbacks merely set and clear a thread-local context pointer. They must not be mistaken for the animation workload. Likewise, the separately named `UpdateKino` callback leads through the manager to a queued-record processing routine. Its name alone does not make it the component-time update.

## Validation

The original interval-selection block matched 256 synthetic cases spanning all component-flag bytes, missing owner/world paths, both clock selections, negative intervals and zero. See the [receipt](animation_component_clock_validation.json). Four repository tests exercise source selection, forced-zero paths, adapter guards and all combinations of local dispatch gates. The factory and interface chain were inspected statically, not executed as a complete original-game job.

## Remaining work

1. Trace the configured animation-time job's gather writer and live receiver membership; its worker table and unadjusted visitor are now established.
2. Trace the two world-clock producers and job dependencies to relate this update to physics substeps and input ingestion.
3. Find writes to KinoComponent's threshold byte and identify the first threshold component and source table.
4. Follow concrete parameter-group callback types. The interface is now identified, but those producers remain separate.

Evidence anchors: component type global `142e908a8`, descriptor `142e915c0`, constructor `140dd0c50`, component table `141f289d0`, slot-0x270 thunk `140dd37c0`, component update `140de1b60`, interface call `140de1cfd`, manager constructor `1412618b0`, manager table `142906bb8`, interface factory `1412784d0`, owner constructor `1412b7fd0`. Task setup `140905dd0`, receiver dispatcher `1409d44c0`, batch consumer `1408f2b00`. These anchors identify private evidence; no game payload is distributed.
