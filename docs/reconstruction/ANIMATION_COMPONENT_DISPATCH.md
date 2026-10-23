# Component-to-animation update connection

The update interface is now connected to a concrete `KinoComponent` method and its factory. A named animation-time task configuration provides a receiver-dispatch lead. The component call is established statically. A later [live membership check](ANIMATION_MEMBERSHIP_OBSERVATION.md) observed the selected player's Kino component in the source registry and gathered storage; a later [live call pair](ANIMATION_CALL_TRACE.md) observed its interface update running and returning. Timing relative to physics substeps remains unproved.

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

The selected value is copied as float32. The ordinary and alternate sources are two fields within the same world object. The [shared clock producer](WORLD_CLOCK.md) applies holds and optional scales, then divides its input by 1000. Their precise per-frame scheduling and physics/render relationship remain open. A zero interval does not bypass the component's later dispatch gates by itself.

`engine.animation_component_clock.component_interval` implements this rule over explicit observations. `dispatch_component_update` expresses the three local call gates. Neither function schedules callbacks or identifies a player. Finite-value and bounds validation are adapter guards.

## Named task configuration

The scheduler-owner setup associates `AnimationUpdateTime` and `IAnimationComponent::UpdateTime` labels with a job record. Its callback field receives a generic receiver dispatcher that calls receiver virtual slot `0x270`. The KinoComponent table supplies the thunk above at that slot.

A generic batch consumer reads the same callback-field layout and walks a supplied pointer array in reverse order, applying a signed receiver adjustment before invoking the callback. The subsequent [batch binding audit](ANIMATION_BATCH_BINDING.md) establishes the concrete worker table and selects a different visitor without receiver adjustment. Static configuration alone does not establish player membership. The later passive capture identifies one selected-player receiver in the source and gathered storage; full population behavior across modes remains unproved.

Nearby setup callbacks merely set and clear a thread-local context pointer. They must not be mistaken for the animation workload. Likewise, the separately named `UpdateKino` callback leads through the manager to a queued-record processing routine. Its name alone does not make it the component-time update.

## Validation

The original interval-selection block matched 256 synthetic cases spanning all component-flag bytes, missing owner/world paths, both clock selections, negative intervals and zero. See the [receipt](animation_component_clock_validation.json). Four repository tests exercise source selection, forced-zero paths, adapter guards and all combinations of local dispatch gates. The factory and interface chain were inspected statically, not executed as a complete original-game job.

## Remaining work

1. Extend the observed interface call pair to full component callback boundaries and request identity. The live pair brackets only the nested interface call.
2. Trace the two world-clock producers and job dependencies to relate this update to physics substeps and input ingestion.
3. Find writes to KinoComponent's threshold byte and identify the first threshold component and source table.
4. Follow concrete parameter-group callback types. The interface is now identified, but those producers remain separate.

Evidence anchors: component type global `142e908a8`, descriptor `142e915c0`, constructor `140dd0c50`, component table `141f289d0`, slot-0x270 thunk `140dd37c0`, component update `140de1b60`, interface call `140de1cfd`, manager constructor `1412618b0`, manager table `142906bb8`, interface factory `1412784d0`, owner constructor `1412b7fd0`. Task setup `140905dd0`, receiver dispatcher `1409d44c0`, batch consumer `1408f2b00`. These anchors identify private evidence; no game payload is distributed.

## Queued event drain

A separate component route handles animation events, rather than the slot-0x270
animation-time update above. Live guarded membership now places a KinoComponent
owned by the acquired snow actor's entity in `DispatchAnimEvents`: source index 3
of four, with matching gathered-storage index 3. Its table is RVA 0x1f289d0 and
slot 0x278 is RVA 0xdd37a0. The known motion component is absent from this batch.
See the [live receipt](../../native/snow_host/animation_event_membership_live_validation.json).
This is membership evidence, not observed event-handler execution or independent
local-player selection proof. The earlier two inconclusive attempts remain in
the [attempt receipt](../../native/snow_host/markup_animation_membership_attempts.json).

The slot-0x278 method adds 0xf0 to the component pointer, sets the second argument
to zero, and tail-calls `0x140d5c450`. The event-call portion is:

```python
def drain_calls(queue, suppress):
    if not suppress:
        count = queue.first_handle_count_u16
        for i in range(count):
            event = queue.event_pointers[i]
            if event is None:
                continue
            first = resolve_if_status_bit31(queue.first_handles[i])
            second = resolve_if_status_bit31(queue.second_handles[i])
            event.virtual_50(first, second, 0)
    # Later original code clears counts and conditionally releases handle refs.
```

Offsets relative to the embedded queue: event pointer array at +0, first handle
array at +0x90 with uint16 count at +0x9a, second handle array at +0x120. Each
handle's pointer is at +0 and status word at +0xc. The sign bit selects its
pointer or null independently. The event callback uses RCX=event, RDX=first,
R8=second, R9=0. Their gameplay meanings are unresolved. Null events skip both
handle reads. Count is captured before iteration; producer count consistency,
callback mutation and handler object lifetime remain external requirements.

[`plan_event_dispatch`](../../engine/animation_event_dispatch.py) implements only
the ordered call plan over explicit rows. It never calls handlers or releases
objects. [32 original-instruction cases](../../native/snow_host/animation_event_dispatch_validation.json)
match the planner across one/three events, suppression, null events and independent
handle-status signs. Handlers are intercepted. Three portable tests cover ordering,
null/suppressed skips and malformed input. Queue clearing/refcount retirement are
static findings only and are not implemented by this call planner.

The routine's later code clears event count, conditionally decrements references
in the two handle arrays depending on each header's bit14, and clears their
counts. This does not make listener teardown safe or identify markup IDs 84/92.
The next useful connection is the queued event type and its slot-0x50 handler,
plus the producer that enqueues it. Event payload pointers must remain private.

Graph setup also registers graph+0x65c0 and graph+0x6788 as predecessors of the
event job at graph+0x43d8 using the established successor-registration slot.
Their setup labels are AfterPhysicUpdate and AfterPhysicUpdateMainActor, both
named Ai::UpdateAfterPhysics. The event job registers graph+0x4768 as successor.
These are static edges; request identity, live execution and complete graph
ordering remain to be measured.
