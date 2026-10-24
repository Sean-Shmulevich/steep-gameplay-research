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


## Timed-event producer connected to the Kino queue

The earlier [runtime binding research](../systems/animations/runtime-binding/trace-recipe.md#timestamp-batch-append-and-metadata-interval-check)
already identifies timed-track traversal, payload filtering and the parallel-array
append. The newly inspected setup joins that producer to the Kino queue used by
the event drain above. This is a static route, not a live event-production capture.

Setup `0x140dd3000` resolves its owner's active handle and requests the component
through `0x14139bd40`, using the type descriptor loaded from `0x142e908a8`.
That is the same Kino descriptor global identified by the component research.
The result is the fifth argument to `0x140ddaaf0`; the latter builds an evaluator
configuration descriptor whose queue field is that component plus 0xf0.
`0x140db3070` copies this field into evaluator+0x58. Do not confuse this with
other functions that happen to use an offset of 0xf0 on different receivers.

The readable route is:

```python
# Static caller relationship; component lookup must succeed on this path.
owner = resolve_active_handle(binding.owner_handle)
kino = lookup_component(binding.kino_cache, owner, KinoComponentType)
evaluator = acquire_or_construct_evaluator()
configure(evaluator, resource, owner, auxiliary_owner, kino, range_config)

# Selected setup/initializer assignments, not the entire initialization routine.
evaluator.owner = owner
evaluator.auxiliary_context = auxiliary_owner.binding_context
evaluator.event_queue = kino.event_queue
evaluator.track_mask = 0xffff
evaluator.event_mask = 0xffff
evaluator.flags = set_low_two_bits(evaluator.flags, range_config)
evaluator.flags |= 8  # enables the event-producing branch below

# Existing timed-track traversal, when its other gates pass.
for track in eligible_tracks:
    for event in newly_due_events(track, evaluator.absolute_position):
        advance_cursor_before_payload_checks(event)
        if payload_gates_pass(event):
            event.prepare(effective_mask)  # virtual slot 0x60
            enqueue(evaluator.event_queue, event,
                    evaluator.owner.field_60, evaluator.owner)

# Separate scheduler dispatch on the component.
for event, first_handle, second_handle in kino.event_queue:
    event.deliver(resolve(first_handle), resolve(second_handle), 0)
```

The two enqueue arguments are not anonymous clip values on this path:
`0x140db51b0` loads evaluator+0x40 as the second context and dereferences its
+0x60 field for the first context. `0x140db5370` passes those through to
`0x140d2df10`, which creates retained handles in queue+0x90 and queue+0x120.
The drain resolves those handles independently. The semantic type of field+0x60
is deliberately left open here; this route alone does not prove it is the player,
a motion object, or a world. Other callers can supply different contexts.

[1,024 original-instruction setup cases](../../native/snow_host/kino_event_binding_validation.json)
cover every initial flag byte and both values of the two configuration bits.
They execute the setup and initializer prefix together, checking the embedded
queue assignment, both context assignments, masks, and event-enable bit. Resource
and range helpers are intercepted. Component lookup, later initialization,
allocation, queue production and event callbacks are outside this fixture.

This closes the static producer-to-consumer queue identity for this setup path.
It does not identify event classes, prove this evaluator is active on the captured
actor, or connect delivery to markup IDs 84/92. The next observation should identify
a nonempty queue's event tables and handler calls, with owner and request identity,
rather than search again for a generic three-array producer.

## Named event types and delivery distinctions

The metadata type checked by `0x140d8aa80` is now identified as `AnimEvent`:
its target global at RVA 0x2e7fe38 points to descriptor RVA 0x2e85110, whose
name field points to the literal `AnimEvent`. This names the optional resource
metadata used by the timestamp filters; it does not name every queued payload.

The producer's helper `0x1409c3670` recognizes two payload type families through
separate descriptor-interval checks. Their concrete constructor-installed tables
provide the following observation signatures:

| Payload type | Table RVA | Type getter RVA | Delivery slot 0x50 | Preparation slot 0x60 |
| --- | --- | --- | --- | --- |
| AudioEventSeed | 0x1eecd58 | 0xa28270 | 0xa45ec0 | 0x75e600, return only |
| SoundSetEventSeed | 0x1eece18 | 0xa24490 | 0xa45ec0 | 0x75e600, return only |

These are static signatures for this image. A derived payload may use a different
table, and neither table has yet been observed in the captured actor's queue.
The names come from descriptors, not guesses from the surrounding functions.
See the [type and annotation receipt](../../native/snow_host/animation_event_types_validation.json).

The producer helper performs this local annotation:

```python
def annotate_event(payload, supplied_u32):
    if payload is None:
        return False
    if is_a(payload, AudioEventSeed):
        resource = payload.resource
        if resource is not None and resource.byte_68 & 1 and supplied_u32 != 0:
            resource.word32_64 = supplied_u32
            return True
    elif is_a(payload, SoundSetEventSeed):
        resource = payload.resource
        if resource is not None and resource.byte_40 & 1 and supplied_u32 != 0:
            resource.word32_3c = supplied_u32
            return True
    return False
```

The `elif` is significant: an object accepted by the first type check does not
fall through to the second when its resource gate fails. Thirty-six
original-instruction cases cover both recognized families and an unrelated type,
resource presence, flag gating, and values zero/one/uint32-max. Type predicates
are intercepted; the helper's actual stores and return byte execute.

In the timestamp producer, true optionally sets a caller-provided byte to one.
False does **not** reject the event: both outcomes continue to preparation and
queue append. Therefore this byte must not be exposed as a universal
"event delivered" or "motion released" indication.

Both named payloads share this delivery wrapper:

```python
def deliver_named_seed(seed, first_context, second_context, extra):
    manager = load_global_manager()
    # The wrapper ignores first_context and replaces extra with zero.
    if seed.resource is not None:
        resolved = resolve_resource(manager, seed.resource)
        dispatch_seed(seed, second_context, resolved, 0)
```

The wrapper is `0x140a45ec0`, the global getter `0x1409b3e00`, the resource-gated
helper `0x1408fd240`, and downstream dispatcher `0x1408fd290`. The latter obtains
an object through resource virtual slot 0x50, stores a retained handle to the
second context, selects a downstream submission path, then passes the object to
a final helper at `0x140424750`.
Those calls are statically inspected, not executed by the annotation fixture.
Their final effects and synchronization are not reconstructed here.

For the next live capture, retain the event table, delivery target and both
context identities. Classify these two signatures separately from unknown
payloads. The queue can carry audio-related events, so queue activity alone is
not evidence of a markup notification or a snow-motion release.
