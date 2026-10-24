# Central impulse and rotation-preserving boost

This finding connects the existing [jump impulse research](../systems/snow/integration/CLIENT_GUIDE.txt)
to a candidate mod API. It does not add a live game function to the host yet.
The portable implementation is [reference/central_impulse.py](../../reference/central_impulse.py).

## Recovered routine contract

Inputs are a body, a three-component impulse, and a force flag. The body supplies
live inverse mass, linear velocity, descriptor motion kind, and descriptor flags.
The wrapper examines the low four motion-kind bits. If they equal 2 and force is
false, it returns without entering the arithmetic routine or dispatching.
Otherwise the inner routine checks suppression bit 8. If that bit is clear:

```text
for axis in x, y, z:
    product = float32(body.inverse_mass * impulse[axis])
    body.linear_velocity[axis] = float32(product + body.linear_velocity[axis])
```

Angular velocity is not written. There is no application point, torque arm,
timestep multiplier, orientation change, speed-history reset, or rider re-pose in
this inspected inner routine. It differs from the host's current actor velocity
assignment, which clears angular velocity and refreshes rider/history state.

After the inner call, force=true requests backend dispatch, even when suppression
bit 8 prevented velocity writes. This dispatch must not be described as a proven
wake operation. Its downstream synchronization and island effects remain open.

```text
entered = (body.motion_kind & 15) != 2 or force
if entered:
    if (body.flags & 8) == 0:
        add_inverse_mass_scaled_impulse(body, impulse)
    if force:
        request_backend_dispatch(body)
```

The original jump caller submits this central-impulse API to the main body and,
when present, the separate rider body. Its configured jump mass split is already
documented in the jump research. Those configuration masses must not be silently
substituted for the live backend mass in a general mod API.

## Derived boost policy

For a desired common velocity increment `dv` and dynamic bodies with live inverse
masses `im_i > 0`, choose `J_i = dv / im_i`. Each body then receives approximately
the same `dv`, subject to float32 rounding and its own submission gates. This is
our proposed mod policy, not a recovered boost mechanic.

Synthetic example: main inverse mass 0.25 and rider inverse mass 0.05 correspond
to masses 4 and 20. For `dv=(2,0,0)`, submit impulses `(8,0,0)` and `(40,0,0)`.
Both linear velocities increase by approximately 2; their angular velocities
remain unchanged by the central arithmetic. The next constraint/contact solve
can still alter both linear and angular motion.

For a continuous acceleration command, calculate `dv = acceleration * dt` once
at the verified physics boundary. The central-impulse routine does not multiply
by dt again. A brake policy must clamp the requested reduction to avoid reversing
the chosen motion component. Ground-tangent selection, input mapping and dt
ownership require explicit contracts; they are not inferred from this routine.

## Verification

On 2026-10-15, a private Unicorn harness executed the original wrapper and inner
routine across 960 synthetic cases. Cases covered five kind bytes, four flag
bytes, both force states, three inverse masses including zero, and randomized
linear velocities, nonzero spins and impulses. Kind 18 checked low-nibble masking.

Linear results matched the portable implementation bit-for-bit at float32
precision. Angular velocity and all other bytes of the synthetic body remained
unchanged. The dispatch gate and body/service arguments matched. The downstream
dispatch routine was replaced with a return; no game process was launched.
Private instruction-image hashes and test artifacts are retained in the workspace.
The public [validation record](../../native/snow_host/central_impulse_validation.json)
contains no game payload. Portable tests cover gate combinations, unequal body
masses, zero inverse mass and invalid inputs.

Finite values representable as float32 are the portable API domain. Its rejection
of invalid values is authored validation, not original-engine behavior. NaN,
infinity, denormal handling and non-default floating-point environments are not
established by this test.

## Remaining live gates

1. Resolve main and rider bodies from the current actor and revalidate both lifetimes.
2. Read and validate both live inverse masses and suppression/kind state. Preflight
   every body before any submission; never report partial application as success.
3. Establish the runtime lock protocol and required thread context. The central
   wrapper itself does not acquire the actor runtime lock. A host-held physics
   step is not a proof that every other game job is quiescent.
4. Reuse the observed BeforeSimulation-to-PhysicsWorldStep ordering to identify
   a callback that runs once for the intended step and a dt with matching meaning.
   An actor receiver exit alone does not prove all other receivers have completed.
5. First validate a small held impulse with before/after spin and both-body
   velocity reads. Then record effects after steps and through respawn/rebinding.
6. Expose continuous boost only after those checks; stop applying on player loss,
   inactive bodies, callback teardown or invalid timing.

The existing host plugin thread is not a native physics callback. No instruction
patch, live pointer replacement or impulse injection was performed for this pass.

## Pending-impulse consumer and lock scope

A second inspected path in the snow update consumes a four-lane pending vector.
For finite lanes it tests whether every absolute component is less than or equal
to float32 `1e-5`. If all four pass, the pending vector is retained, with no lock
or impulse call. If any lane exceeds the threshold:

```text
lock = runtime.lock_holder.value
enter(lock)
central_impulse(runtime.main_body, pending.xyz, force=true)
if runtime.rider_body exists:
    central_impulse(runtime.rider_body, pending.xyz, force=true)
leave(lock)
pending.xyzw = zero
```

Both submissions use the SAME impulse. They are not mass-scaled here. The fourth
lane participates in the threshold test but not the central-impulse arithmetic.
A nonzero fourth lane can therefore request dispatch with no linear momentum
change. A suppression flag can prevent a body's velocity writes while the pending
vector is still consumed. Clear occurs after lock release, not inside the lock.

A private emulator executed the original consumer and both original impulse
routines in 48 additional cases. It verified the same lock argument at entry and
exit, main-before-rider ordering, the optional rider branch, exact float32 results,
unchanged angular velocity, threshold equality and the next greater float, and
pending retention/clear behavior. Lock helpers and downstream dispatch were
intercepted. This proves call order and arguments, not mutual-exclusion behavior.
See the [pending validation record](../../native/snow_host/pending_impulse_validation.json).

The jump branch also brackets its paired submissions with this runtime lock,
but submits the rider before the main body and uses its configured mass split.
Do not conflate the two sequences.

The lock helper's available static image includes protected control transfers;
its blocking, recursion and ownership semantics are not established. We must not
substitute a Windows critical section or call an assumed try-lock API. The
existing game setter's successful lock usage does not prove arbitrary-thread
impulse submission is safe.

The initial unwind-bounded scan found initialization/reset and consumption but
missed the queue producer. The follow-up below supersedes that search result.

## Queue producer recovered from leaf-function gaps

The queue and clear methods are small actor leaf functions with no entry in the
image's exception/unwind function table. Restricting disassembly to that table
excluded them. Searching the snow/actor code interval for pending-field operands,
including gaps between recorded functions, found both methods.

```text
queue_impulse(actor, aligned_float4):
    runtime = actor.runtime
    if runtime is absent:
        return
    for lane in x, y, z, w:
        runtime.pending[lane] = float32(runtime.pending[lane] + input[lane])

clear_impulse(actor):
    if actor.runtime exists:
        actor.runtime.pending.xyzw = zero
```

The native vector loads/stores require the alignment implied by MOVAPS. Queueing
has no lock, allocation, mass factor, timestep factor, body-kind gate or wake
operation. It accumulates rather than replaces all four lanes. With no runtime,
it returns before reading the input vector. Clear also returns on absent runtime.
Neither leaf directly writes body velocity or angular velocity.

A full executable-text direct-call scan found one direct caller of the queue
leaf and one direct caller of the clear leaf in the analyzed image. The queue
caller scales a basis vector by a clamped scalar and submits it through an actor
owned by another object. Its full semantic role and scheduler context remain
unresolved. The clear caller invokes the actor velocity-assignment routine,
then clears the pending impulse. This is a concrete reason not to mix repeated
velocity assignment with queued impulses and expect both to accumulate.

The adjacent scaled queue leaf is a separate static lead: it follows actor to
entity to world, multiplies a supplied vector by a world scalar times 30, and adds
that to the same pending storage. The scalar's meaning has not been established;
do not call it dt or a mass conversion without further evidence. That leaf is not
included in the portable queue API or the native validation below.

The original unscaled queue and clear leaves passed 256 additional synthetic
cases, including absent runtime with an invalid input pointer. Four-lane sums
matched bit-for-bit, all four lanes cleared when present, no body state changed,
and neither leaf called lock or dispatch. See the [queue validation record](../../native/snow_host/queue_impulse_validation.json).

This closes the nonzero producer's arithmetic and actor/runtime connection, not
its thread safety. The read/add/write is not an atomic accumulator. A concurrent
consumer can clear a new write after releasing its lock, so merely taking that
lock around a mod's queue call is not sufficient proof against lost impulses.
The next required edge is the producer caller's execution order relative to the
snow consumer. A native engine-ordered callback remains the preferred mod entry.

## Synthetic queue interleavings

A 96-case original-instruction experiment forced producer execution at three
consumer boundaries, 32 synthetic inputs each. The producer ran with a saved
consumer CPU context and shared memory, then the consumer resumed. Locks and
backend dispatch were intercepted. This models possible instruction ordering;
it does not establish that the live engine permits these interleavings.

- Before consumption: both bodies receive the accumulated old-plus-new impulse.
- Between main and rider submissions: the main receives the old impulse and the
  rider receives old-plus-new. The consumer passes the pending storage again;
  it does not use one immutable local snapshot for both submissions.
- After unlock, before clear: both bodies have received the old impulse, then
  the new queued addition is erased by the following clear without application.

All cases retained angular velocity. These results strengthen the requirement
for an engine-ordered producer boundary; a mod-side lock alone cannot be assumed
to cover the consumer's post-unlock clear. They do not justify patching out the
clear, changing the original lock, or submitting from the host executor. See the
[interleaving receipt](../../native/snow_host/pending_interleaving_validation.json).
The next live gate remains request-correlated producer/consumer observation,
followed by a bounded submission at an established ordered boundary.

## Producer route reaches BeforeSimulation

The previously isolated unscaled queue caller now has a static chain back to the
selected snowboard actor's motion update:

```text
BeforeSimulation actor receiver
  -> actor motion update, when actor gates pass
    -> input ingestion
    -> carrier preparation
    -> motion-state dispatch
      -> selected state handler
        -> shared state update
          -> conditional impulse producer
            -> actor.queue_pending_impulse(vector)
```

The motion dispatcher acquires its own owner/recursion lock before selecting a
state. That is distinct from the body/runtime lock used by the snow consumer.
The observed handler route requires outer state code 3 and inner variant 1, 2,
or an unsigned variant value greater than 8. Other variants select other handlers.
These codes do not yet have established sport/action names. The shared producer
has additional thresholds and clamping; selecting this route does not guarantee
that an impulse will be queued.

The original state-dispatch fragment was emulated in 72 cases across outer codes
0 through 5 and twelve inner values, including negative signed values that become
large unsigned values in the range check. Calls to state handlers were intercepted.
The selected route and forwarded state-object argument matched in every case.
The portable route predicate is tested against these [native observations](../../native/snow_host/impulse_route_validation.json).

The static chain joins the actor receiver already covered by the
[live BeforeSimulation ordering observation](MOTION_MEMBERSHIP_OBSERVATION.md#order-against-physicsworldstep).
That session proved the actor callback returned before PhysicsWorldStep began.
It did not record this particular state handler, queue invocation or pending-vector
consumption. Therefore the combined evidence supports a conditional pre-world-step
producer path, not universal live queue freshness or an exclusive writer guarantee.

The snow consumer is inside the world/substep route described in the
[input/publication audit](SCHEDULER_INPUT_AUDIT.md). Subject to its gates, a queued
impulse can be consumed on an eligible snow invocation and cleared; it should not
be reapplied once per substep merely because the producer ran once per outer
request. Retention through skipped consumers is part of the contract.

A useful next live trace records, for the same actor/runtime and request identity:
queue entry with vector and pending-before; queue return with pending-after;
consumer entry/exit with pending values; and world-step entry. It must record
state codes and distinguish missing/disabled consumers from stale objects. Start
with observation, then test one bounded queued impulse at a proven ordered entry.
Do not call the queue from the host's arbitrary executor thread during gameplay
or treat the motion lock as proof that it protects the consumer's clear.

## Actor virtual boundary leading to the consumer

A static call-chain audit connects the pending consumer to slot `0x2c0` of the
previously identified player actor vtable. The selected player override checks
four byte fields, calls a preparation helper, invokes the shared snow update,
and calls a finishing helper. The shared update reaches the runtime dispatch
which tail-calls the routine containing the pending consumer. This is a
conditional route, not proof that every slot invocation consumes an impulse.

The wrapper has this recovered control flow. Field names below are deliberately
ordinal because their gameplay meanings are unresolved. The two scalar lanes
are `elapsed_dt` and `derivative_dt`, as established by the scheduler carrier
chain in the [input/publication audit](SCHEDULER_INPUT_AUDIT.md) and
[scheduler reconstruction](research/scheduler.md). The former is per substep;
the latter is the consumed outer interval. They must not be merged.

```python
def player_snow_wrapper(actor, elapsed_dt, derivative_dt):
    if actor.byte_1fa == 0:
        return
    if actor.byte_fdc != 0:
        return
    if actor.byte_fc8 == 0 or actor.byte_fc9 == 0:
        return
    saved_byte = prepare(actor.subobject_1010) & 0xff
    shared_snow_update(actor, elapsed_dt, derivative_dt)
    finish(actor.subobject_1010, elapsed_dt, derivative_dt, saved_byte)
```

A private emulator ran the original wrapper in **64 synthetic cases**: all 16
boolean gate combinations and four preparation return values. All three callees
were intercepted. The test confirmed call order, receiver identities, preservation
of both low float32 argument lanes even when intercepted callees clobbered their
registers, and zero-extension of the preparation return byte. The player table's
slot was also checked against the analyzed image. See the
[sanitized validation receipt](../../native/snow_host/consumer_wrapper_validation.json).
This validates wrapper behavior only; no snow calculation ran in this experiment.

### Writers that release the wrapper's blocking byte

The paced [input capture](SCHEDULER_DELEGATES.md#live-input-interval-and-moving-body-observations)
observed `actor+0xfdc` change from 1 to 0 at the first sampled nonzero body
velocity. The wrapper above establishes a concrete consequence: clearing this
byte removes one early-return condition. It does not by itself enable the wrapper
unless the other three gates also pass, nor does it directly apply a force.

Two inspected owner callbacks clear this byte through an actor reached at
`owner+0x10 -> context+0x40`. The actor's slot `0x4b0` is a leaf that returns the
byte as an unsigned value. The callbacks differ by an additional `actor+0xfc9`
guard. Their local behavior is:

```python
def release_snow_block(owner, require_fc9):
    # resolve_actor performs both pointer loads on every call, as the code does.
    if resolve_actor(owner).virtual_4b0() == 0:
        return
    actor = resolve_actor(owner)
    if require_fc9 and actor.byte_fc9 == 0:
        return
    actor.byte_fdc = 0
    physics_side_helper(resolve_actor(owner), 1)
    resolve_actor(owner).byte_2ae = 0
```

The helper is external to this local model. Its inspected entry resolves the
actor's entity/world physics owner, takes a lock, and branches on the argument
and body state. Its complete transitive effects are not validated here. In
particular, skipping it and writing only the byte is not an equivalent operation.
The pointer reload after the helper is preserved because transitive changes have
not been excluded. The final byte's gameplay meaning is unresolved.

[Sixteen isolated original-instruction cases](../../native/snow_host/snow_gate_release_validation.json)
execute both callbacks and the actual virtual getter using synthetic objects.
They cover blocked-byte values 0, 1, 2 and 255, and `fc9` values 0 and 1.
The physics helper is intercepted; its receiver and low-byte argument are checked,
as are the cleared fields and skipped-call behavior. This proves the local
nonzero tests, not a native mod API or the identity of the writer in the live run.

Evidence anchors for this build: unconditional callback `0x140536620`, guarded
callback `0x140537640`, getter `0x14052bbb0`, external helper `0x141373250`.
Other writers exist, including setters that record a clock before writing 1.
The search was limited to decoded exception-table regions with literal field
displacements; it is not a complete writer inventory and unrelated object types
can use the same offset. The next live attribution needs a callback identity or
state transition, rather than labeling this byte a key, contact, or crash flag.

### State-dispatch routes to gate release

Correction: the initial dispatch note called the top-level `+8` field an event
code. It is the embedded motion machine's current mode, as established by its
[commit routine](MOTION_MEMBERSHIP_OBSERVATION.md#guard-can-return-a-decision-from-the-previous-state).
The selector's parameter is now `current_mode`. Its branch predicates are
unchanged; no input-event producer was identified by the previous pass.

The two release callbacks have direct callers in nested state dispatch. The
portable [route selector](../../engine/snow_block_route.py) reconstructs the local
branch predicates, using authored labels A/B rather than guessed gameplay names.
Inputs are raw uint32 current mode, outer state and, when needed, inner state.
The inspected handler stores current mode at `+8`, owner at `+0x10`, and the owner
stores outer state at `+0x18` and its child at `+0x20`. The child's `+0x18` is
the inner state; its `+0x20` supplies the deeper callback receiver.

| Variant | Current mode | Outer state | Inner state | Selected callback | Receiver |
| --- | --- | --- | --- | --- | --- |
| A | 0 | 1 | Not read | External outer-one callback | Owner's child |
| A | 0 | 0 | 5 | Unconditional block release | Child's child |
| B | 0 | 0 | 0 | External inner-zero callback | Child's child |
| B | 0 | 0 | 1 | Block release requiring `fc9` | Child's child |
| B | 0 | 0 | 5 | Unconditional block release | Child's child |
| Either | Other combinations | | | No callback in this fragment | None |

```python
def select_route(variant, current_mode, outer_state, inner_state):
    if current_mode != 0:
        return None
    if variant == "A" and outer_state == 1:
        return "outer_one_callback", 1
    if outer_state != 0:
        return None
    if inner_state == 5:
        return "release_block", 2
    if variant == "B" and inner_state == 1:
        return "release_block_if_fc9", 2
    if variant == "B" and inner_state == 0:
        return "inner_zero_callback", 2
    return None
```

The native branch marks its local handled result after calling the selected
callback, even if that callback's own byte guard causes no mutation. Therefore
route selection, callback execution and gate clearing are separate observations.
The surrounding routine acquires an owner-thread/depth lock, tracks active
dispatch and checks pending flags afterward. This selector neither implements
that lifecycle nor grants permission to invoke callbacks from another thread.

[Ninety original-instruction branch cases](../../native/snow_host/snow_gate_dispatch_validation.json)
match the selector's callback, receiver depth and native handled result across
both variants, current modes 0/1/UINT32_MAX, outer states 0/1/2 and inner states
0/1/5/6/UINT32_MAX. Synthetic callback interception isolates dispatch; it does not
validate locking, pending transitions or the external callback effects.
The earlier 16-case check separately validates the two release callbacks' local
guards. No live trace yet joins these two layers for the observed transition.

Build-specific branch anchors are `0x1405364bf..0x1405364f5` and
`0x14053713f..0x140537185`. External callback anchors are `0x140536680` and
`0x1405372b0`. A useful next observation records handler identity, nested state
codes and callback entry/return alongside the actor gate and physics-job identity.
Do not equate current mode zero or state five with a named input or sport without
following their producers. Existing input-ingestion evidence remains a separate
join, not proof that keyboard delivery directly invokes either handler.

### Actor entry route and reuse of the motion observer

Two inspected entry adapters resolve the dispatcher as `actor+0x1010`, the same
embedded object observed by `snow_motion_observe`. Adapter A tail-calls dispatch
A. Adapter B calls dispatch B only when actor byte `+0xfe4` is zero, then always
calls the existing state guard with output address `actor+0xfe5`:

```python
def actor_adapter_b(actor):
    if actor.byte_fe4 == 0:
        dispatch_b(actor.motion)
    state_guard(actor.motion, output_byte=actor.byte_fe5_address)
```

The final guard may service pending state changes after saving its result, as
the earlier integrated guard/commit tests establish. It is not a pure query and
the adapter does not reset the output byte before calling it. Skipping dispatch
B therefore does not make the entire adapter side-effect-free.

[Eight isolated adapter cases](../../native/snow_host/snow_gate_adapter_validation.json)
execute its original instructions with dispatch and guard intercepted. Gate values
0/1/2/255 and initial output bytes 0/123 confirm conditional dispatch, unconditional
guard call, both receiver arguments, and preservation of the output byte before
the guard. Transitive dispatch/guard effects are excluded from this check.

The existing bounded motion reader already records `current_mode`, `state_mode`
and `child_mode` with `state_observed` and `child_observed` availability flags.
Those are respectively the selector's current, outer and inner fields. Follow
the selector's conditional dependencies: a top-level nonzero mode skips without
requiring child data; top-level zero requires the first state, and first-state
zero requires the next level. Never substitute zero for an unavailable level.
The reader's stable sequential observations do not prove the state at a callback
instruction or pin objects across dispatch. Continuous writer attribution still
requires callback entry/return evidence.

Static anchors: adapter A `0x140536460`, adapter B `0x1405370b0`, final guard
`0x14052c4a0`. An upstream component callback at `0x1405c74f0` takes a low-byte
boolean argument, resolves components through an entity, and chooses adapter B
for its true branch or another motion dispatcher for false. This is a concrete
caller lead, not yet a named input binding. Its component queries, alternate
branch and fallback effects remain external to the route selector.

### Markup notifications reach the motion adapters

The caller lead now has a concrete registration route. Component construction
builds captured callback descriptors, and its later bind routine registers them
against the object at `component+0x388`, using that object's embedded receiver at
`+0x18`. The binary's diagnostics name this subsystem "Markup", including
`LinkToMarkup` and `AddCallbackToMarkupChanged`. These names support a markup
notification interpretation; they do not identify the authored markup names or
prove that a particular animation clip emitted the live transition.

| Markup ID | Descriptor in component | Callback | Observed downstream route |
| --- | --- | --- | --- |
| `0x54` / 84 | `+0x948`, 32 bytes | `0x1405c7040` | Resolve actor, dispatch A, then additional zero-vector calls |
| `0x5c` / 92 | `+0x9c8`, 32 bytes | `0x1405c74f0` | Boolean true resolves actor and calls adapter B; false selects a different dispatcher |

Constructor `0x14057ea90` builds both descriptors with the component captured as
receiver. Registration routine `0x1405b8c50` skips this registration block if
`component+0x388` is null. Otherwise it copies each descriptor to temporary storage
and calls `0x14153c3c0` with receiver `markup_object+0x18`, the numeric ID and the
descriptor address. This is registration, not evidence of callback execution.

```python
def bind_release_notifications(component):
    markup_object = component.markup_object
    if markup_object is None:
        return
    register_markup_callback(markup_object, 84, component.callback_A)
    # Other callbacks are registered between these two.
    register_markup_callback(markup_object, 92, component.callback_B)

def notification_B(component, argument_byte):
    if component.interface_predicate():
        entity = component.interface_entity()
        if argument_byte != 0:
            optional_component_call(entity, argument=0)
            actor = lookup_actor(entity)
            if actor is not None:
                actor_adapter_b(actor)
        else:
            actor = lookup_actor(entity)
            if actor is not None:
                other_motion_dispatch(actor.motion)
    elif argument_byte != 0:
        fallback(component.field_628)
```

These descriptive labels leave unresolved callees explicit. The boolean's authored
meaning and the callback's emitting thread/job remain unknown. Do not translate
it to "animation finished" or a keyboard action without producer evidence.

[Eight original-instruction cases](../../native/snow_host/snow_markup_binding_validation.json)
execute the constructor fragment and registration call sequence with synthetic
storage, crossing all four initial low tag combinations and present/absent markup
owner. They verify function pointers, receiver tagging, copied 32-byte descriptors,
IDs and registration receiver. The registration callee is intercepted, so neither
its allocation nor notification delivery is executed in this check.

Static inspection of the registration helper supplies an additional hook-design
constraint: it increments a bounded per-markup link count, then stores a copy of
the callback descriptor in a listener entry. Changing the component's original
descriptor after binding therefore does not necessarily change the registered
callback. An observation hook must locate the registered copy or intercept a
validated dispatch boundary, with ownership and restoration checks. Do not rewrite
the descriptor source and assume notification coverage.

This provides a candidate explanation for the live gap between mode eligibility
and gate clearing: the release can be requested by a separate markup notification.
It remains a hypothesis until IDs 84/92 or their callbacks are observed alongside
the actor transition. The IDs are build-specific; authored markup/resource names,
clip timing, live component ownership and notification scheduling remain open.

### Markup dispatch and callback argument contract

The registered-listener dispatch is now identified at `0x141539f90`. Its local
notification decision is implemented by
[`advance_markup_record`](../../engine/markup_notification.py). The dispatcher
uses 20-byte markup records, with signed link count at `+0x10`, cached byte at
`+0x0e`, force byte at `+0x0d` and pending index at `+8`. These are operational
labels, not authored marker names.

```python
def process_markup(record, sampled_byte):
    if record.link_count <= 0:
        return  # no query, notification or cache write
    notify = (sampled_byte != record.cached_byte or
              (record.force_byte != 0 and record.pending_index != -1))
    if notify:
        notify_global_callback_if_present()
        notify_registered_listeners(markup_id, sampled_byte, 0xffffffff)
    record.cached_byte = sampled_byte
    record.pending_index = -1
```

The actual query is external to this model. Record byte `+0x0c` chooses one of
two sources: one helper's integer result becomes 0/1 by comparison with zero;
the other helper's low byte is retained. The reconstructed decision preserves raw
bytes instead of normalizing both paths. Nonpositive link counts leave cached
state and pending index unchanged. A processed record clears the pending index
even when no callback is emitted. Thus a forced repeated notification normally
requires another producer to repopulate that index.

The original dispatch accesses 40-byte listener entries. Each entry contains its
copied 32-byte descriptor at `+8`. It clears the captured receiver's low two tag
bits and invokes the descriptor thunk with markup ID, sampled byte, and sentinel
`0xffffffff`. The actual shared thunk `0x140397a20` forwards these as:

```text
callback(captured_component, markup_id, sampled_byte, uint32(0xffffffff))
```

This identifies the origin of notification B's tested low-byte argument: it is
the sampled markup value. It is not inherently "finished", "landed" or "jump".
Both changes to true and changes to false can notify; the callback chooses its
two motion routes from that value. The global callback runs before listener-map
lookup. Listener count is reread after each invocation, so callback mutation and
reentrancy cannot be replaced by an assumed immutable list without further work.

[216 original-instruction cases](../../native/snow_host/markup_dispatch_validation.json)
execute the dispatch fragment and actual shared thunk with synthetic records and
one listener. External source queries and listener-map lookup are intercepted.
They cross link counts -1/0/1, cached/query bytes 0/1/2, both query branches, force
0/1 and pending -1/4. Callback arguments, notification decision and cache writes
match the portable model. This is local instruction validation, not execution of
an authored marker, full graph evaluation, or a live scheduler join.

An upstream virtual callback at `0x14053c760` conditionally invokes slot `0x4e0`
when receiver byte `+0x294` is nonzero, then dispatches the object at receiver
`+0x6c0` through adapter `0x1405eab70`, which adds `0x18` and reaches this markup
processor. It finally tail-calls another routine. This is an observation-point
lead; its live relationship to the selected snow actor and enclosing job is not
yet established. Do not hook the snow vtable at an inferred matching slot: the
inspected snow table does not directly contain this callback target.

### Live markup ownership joins the acquired actor's component chain

The callback's table is now identified: the owned component table `0x1e789b8`
contains `0x14053c760` at slot `0x4b0`. Its destructor also installs that table,
supporting the table origin rather than inferring an offset from an arbitrary
nearby function pointer. This is the component previously observed in the
[`Ai::UpdateAIPreUpdate` membership](MOTION_MEMBERSHIP_OBSERVATION.md#live-result),
not the snow actor table. Its unrelated slot `0x270` is the AI preupdate entry;
membership there does not establish which job calls slot `0x4b0`.

A [bounded live ownership check](../../native/snow_host/markup_binding_live_validation.json)
now joins the paths:

```text
owned component, table 0x1e789b8
  +0x6c8 -> controller, table 0x1e7d4b0
              +0x628 -> same owned component
  +0x6c0 -> markup object <- controller+0x388
              +0x18 -> markup dispatcher
```

The component/controller relationship and boxed actor route are acquired freshly,
with the actor also matching the world registry candidate. Both markup paths
resolve to the same object before and after the input capture. Exact reads and
rechecks confirm the controller descriptor function, captured receiver and shared
thunk for IDs 84/92. The dispatcher has 148 records in this session:

| ID | Query words | Source branch | Link count | Cached byte before / after | Force / pending index |
| --- | --- | --- | --- | --- | --- |
| 84 | `0x00c00002`, `0xffffffff` | 0 | 1 | 0 / 0 | 0 / -1 |
| 92 | `0x00c0000b`, `0xffffffff` | 0 | 1 | 0 / 0 | 0 / -1 |

These query words are build/session evidence, not decoded authored names. Branch
zero uses the helper that follows its query owner at `+0xb0` and invokes that
object's slot `0xb8`; branch one instead follows `+0x10` and slot `0x20`, returning
zero if that pointer is null. The branch-zero query's concrete provider is the
next producer lead.

The run also returns 16 resident requests with all 32 motion and 32 physics samples
valid, 201 callbacks and zero drops. Delegate restoration, continued engine
progress and outer cleanup pass. The cached bytes match at the endpoints; no
conclusion about notifications between them follows. A link count of one does
not prove the identity or execution of the subscribed descriptor copy. The source
descriptors are verified, but the listener entries are not yet read. The next
capture must inspect or trace registered notification delivery, retaining this
ownership chain and the existing motion/physics request correlation.

### Bounded registered-listener observation

[`observe_markup_listeners`](../../engine/markup_listener_observation.py) reuses
the inspected compact/radix map decoder to follow dispatcher `+0x60` by numeric
markup ID. The returned map value is a listener-vector pointer on this route,
not an action object despite the shared decoder's historical `action` field name.
The observer reads the vector header at `+8`, count at `+0x12`, and each 40-byte
entry's table plus copied descriptor. Returned receiver values have their two
tag bits separated; dispatch-presence is reported without calling any function.

Callers supply an exact `read(address, size)` transport and 1–16 current
identity/ownership byte guards. The default listener cap is 16, with an allowed
maximum of 128. Total work is capped at 320 reads / 49,152 bytes. The reader
rechecks the map result, vector header, descriptor bytes, markup header/record
and external guards. It rejects incomplete reads, excessive counts and changed
storage. Missing keys, present-null values and unsupported map forms remain
distinct. An empty vector does not cause its data pointer to be dereferenced.

```python
result = observe_markup_listeners(
    read, dispatcher, 92, current_identity_guards, max_listeners=16)
if result["status"] == "found":
    for entry in result["entries"]:
        # Compare function, receiver and thunk with the verified build/owner.
        inspect(entry)
```

The output contains private runtime addresses and should remain outside the
findings repository. Matching reads do not pin listener allocation, prove
atomicity or demonstrate callback execution. A callable-looking descriptor is
not authorization to invoke it. Public tests cover compact-map copies, receiver
tags, dispatch-presence checks, missing/null/unsupported/empty cases, count limits,
failed reads and changes to descriptors, headers or identity guards. The existing
map decoder retains its separate radix validation.

The [live listener receipt](../../native/snow_host/markup_listeners_live_validation.json)
now verifies the subscribed copies. IDs 84 and 92 each resolve to exactly one
entry with table `0x1e66660`, expected callback function, the acquired controller
as receiver, shared thunk `0x397a20`, zero receiver tags and zero adjustment.
Value slot, vector address and full decoded descriptor match at both endpoints.
Each observation uses 56 exact reads totaling 3,328 bytes, within the cap.

The same bounded run returns 32 valid motion and 32 valid physics samples, with
161 callback records and zero drops. Restoration, continued progress and outer
cleanup pass. Neither listener is invoked by the observer. Cached markup values
remain zero at the endpoints; pulses and notification execution remain open.

The next recorder can target these verified subscribed descriptors, but endpoint
stability is not a lifetime guarantee. Before a live interception, qualify the
callback ABI, cached-reader forwarding, entry invalidation, compare-and-swap
restoration and retained wrapper lifetime in fixtures. Preserve the descriptor
and markup owner identity in every event, and distinguish an empty trace from a
failed installation. Do not treat a matching listener address as an allocation
pin or assume that the listener vector cannot reallocate.

### Listener relocation changes the interception plan

The growth helper at `0x14153bd00`, called by listener registration, moves
40-byte entries into a new allocation. Its capacity is the low 14 bits of the
header word, and count is the uint16 at header+0x0a. Without force, a requested
capacity no greater than current capacity returns without moving entries.
Otherwise it allocates, writes each destination entry's table, copies the entire
32-byte descriptor, calls each old entry's virtual destructor with argument zero,
and passes the new allocation/count/capacity to the publication helper.

```python
def grow_listeners(header, requested_capacity, force):
    if not force and (header.flags_capacity & 0x3fff) >= requested_capacity:
        return
    new = allocate_external(requested_capacity, stride=40, alignment=8)
    for i in range(header.count):
        new[i].table = listener_table
        new[i].descriptor = copy_32_bytes(header.array[i].descriptor)
    for i in range(header.count):
        header.array[i].virtual_destructor(0)
    publish_external(header, new, header.count, requested_capacity)
```

[12 original-instruction cases](../../native/snow_host/markup_growth_validation.json)
cover zero/one/three entries, force on/off and sufficient/insufficient capacity.
Nine relocate. Synthetic descriptors deliberately contain substituted thunk
pointers; the copied descriptors preserve those pointers exactly. Allocation,
destruction and publication are intercepted. This validates the local copy and
call order, not actual allocation, retirement or live reallocation.

Separate static inspection of publication helper `0x14115baa0` shows conditional
old-storage release before replacing the array pointer and packed header. A
nonnull old pointer is sent through the allocator release path when header bit
15 is clear. That release path was not executed by the fixture.

**Installer consequence:** restoring the saved original slot is insufficient.
A growth operation can copy an installed wrapper to a new slot, leaving the
new listener redirected after the old slot is restored or retired. Checking an
old address and using compare-and-swap does not resolve this propagation or pin
allocation lifetime. Never write the old slot after a failed identity check.
Module retention prevents an unloaded wrapper target, but does not by itself
make descriptor dereferences or restoration safe.

Direct listener-slot interception is therefore deferred until mutation and
restoration can run under a proven lifetime/synchronization boundary that covers
registration, growth and removal. Alternatives to investigate are a stable
upstream callback boundary or supported listener registration/removal with
qualified ownership. An upstream observation alone would not prove which
listener fired. The recorder core remains useful for any route that establishes
the actual five-argument callback boundary.

### Native listener removal and identity

The diagnostic-named removal routine at `0x14153e0a0` validates the markup ID,
looks up its listener vector, scans descriptors, and removes the first match.
The comparison helper at `0x141152e20` has these semantics, implemented in
[`markup_listener_identity.py`](../../engine/markup_listener_identity.py):

```python
def same_listener(a, b):
    ar, br = a.tagged_receiver & ~3, b.tagged_receiver & ~3
    if ar == 0:
        return br == 0 and a.function == b.function
    return (ar == br and a.function == b.function
            and a.adjustment == b.adjustment)
```

The thunk is ignored. Receiver tags are ignored. Adjustment is also ignored when
both untagged receivers are null. Therefore a different thunk alone does not
create a distinct subscription identity. A recorder subscription must use a
unique function/receiver identity rather than borrowing a gameplay descriptor.

Removal helper `0x14153dfc0` copies the last descriptor into the matched slot
unless that slot is already last, calls the last entry's virtual destructor with
argument zero, then decrements count. It preserves the destination entry's table.
This is swap-last removal, not stable-order removal. If the vector becomes empty,
the enclosing routine destroys/releases it and removes its map entry. Missing
map entries and missing descriptors return without a removal.

Paired routine `0x14153eba0` copies the supplied descriptor, calls removal, then
tail-calls unlink at `0x14153eb10` regardless of whether a descriptor was found.
For a valid ID with a positive link count, unlink decrements the count; invalid
IDs or nonpositive counts take the diagnostic path. It does not report a matched
subscription token. Consequently, blindly retrying paired removal can consume
another user's link reference. Match/ownership and exactly-once cleanup must be
part of any authored subscription API. Registration's first-link path also calls
an external initializer; subscribing is not a universally passive operation.

[Original-instruction validation](../../native/snow_host/markup_removal_validation.json)
covers 392 comparator combinations and seven swap-last cases with one, two and
four entries. Comparisons match the portable model; the removal cases preserve
the expected surviving descriptors, including synthetic thunk values, and call
the last entry destructor before decrementing count. Destruction is intercepted.
Full map search, empty-vector cleanup, paired unlink and synchronization are
static findings, not executed by those cases. Ten focused Python tests pass.

A separate recorder subscription is now a concrete alternative to replacing an
existing listener. It avoids restoring copied gameplay thunks, but still needs
an established owner lifetime, a safe registration/removal execution boundary,
exactly-once link accounting, and wrapper retention for in-flight dispatch. The
inspected local registration/removal routines show no explicit synchronization;
that does not prove their callers lack it. Trace their actual caller context
before calling them live. Listener-order changes and callback-triggered mutation
remain relevant to dispatcher behavior.

### Controller lifecycle and mutable dispatch iteration

The controller table already verified in the live ownership chain, RVA
`0x1e7d4b0`, contains registration routine `0x1405b8c50` at virtual slot `0x48`
and cleanup routine `0x1405e07f0` at slot `0x18`. Cleanup reads the same markup
owner at controller+0x388 and passes the original stored descriptors to paired
removal. The inspected list is:

| Markup ID | Controller descriptor offset |
| --- | --- |
| 84 | 0x948 |
| 2 | 0x9e8 |
| 87 | 0xa08 |
| 88 | 0xa28 |
| 92 | 0x9c8 |
| 93 | 0x968 |
| 94 | 0x988 |
| 95 | 0x9a8 |
| 96 | 0x928 |

These are static lifecycle relationships joined to a previously live-verified
table, not a live cleanup trace or a proof of caller synchronization. The cleanup
routine does other work before removing markups. It must not be invoked merely
to remove a recorder subscription. No direct relative-call reference to this
routine was found; its virtual caller context remains to be identified.

The notification loop retains the listener-vector object, but reloads its entry
array each iteration and its count after each callback. It increments the index
unconditionally. It neither snapshots the listener list nor revisits a slot
filled by swap-last removal. This matters even on one thread:

| Authored callback-side mutation of initial listeners A, B, C | Observed original-loop callback order |
| --- | --- |
| None | A, B, C |
| A removes itself using swap-last effect | A, B; C is skipped |
| A removes B using swap-last effect | A, C |
| A appends D | A, B, C, D |
| A moves the entries to another allocation | A, B, C from the reloaded array |
| A sets count to zero while retaining vector storage | A only |

[Six original-loop cases](../../native/snow_host/markup_iteration_validation.json)
validate these orders and preserve the ID/raw-byte/sentinel argument contract.
The callback mutations are authored synthetic effects; original registration,
removal, allocators and destructors are not executed by these cases. In
particular, retaining the vector at count zero does not validate actual
last-listener removal, which can destroy that vector. The loop reads its count
after the callback returns, so storage retention is a real requirement.

Recorder policy: callbacks should record and request deferred shutdown, not
mutate the listener vector. Attach/detach must occur outside active dispatch at
a verified lifecycle/update boundary. Next caller tracing should follow controller
slots `0x18` and `0x48`, and the owned component markup-update slot `0x4b0`, to
establish ordering and retirement. Those slot numbers are build/type-specific,
not generic mod API entry points. Existing engine-phase observations alone do
not prove these operations are serialized there.

### Component update route and after-physics job lead

Further static tracing connects the owned component's markup update to a
three-phase wrapper and a graph descriptor. On table RVA `0x1e789b8`:

| Slot | Target | Inspected role |
| --- | --- | --- |
| 0x278 | 0x14038a590 | Component route selection |
| 0x470 | 0x1405290a0 | Setup path calling controller slot 0x48 |
| 0x488 | 0x1404fe3e0 | Releases controller and markup storage among other children |
| 0x4a0 | 0x14034df20 | Three-phase update wrapper |
| 0x4b0 | 0x14053c760 | Markup update |
| 0x4b8 | 0x14053b950 | Middle phase, not decoded here |
| 0x4c0 | 0x14053c610 | Includes controller slot 0x50 update |

The wrapper reads one float32 time value from helper `0x140472b60` result+0x18,
then invokes slots 0x4b0, 0x4b8 and 0x4c0 in order with that same value in XMM1.
The controller update at slot 0x50 resolves to `0x1405ead50`. These observations
establish a local call sequence, not a cross-job dependency or substep identity.

Route selection first calls external helper `0x1406a30e0`, then reads flags:

```python
def component_route(component):
    pre_helper_external(component)
    if component.byte_14c != 0:
        return special_path_external(component)
    if component.byte_14d == 0:
        return
    if (component.byte_158 & 0x10) == 0:
        parent = component.entity_at_10.pointer_at_60
        if parent:
            return alternate_path_external(parent + 0x110, component)
        return
    if (component.word_8 >> 26) & 1:
        component.virtual_4a0()
```

The alternate path `0x140862860` brackets its inner helper with lock-like calls
on receiver+0xd80. This is not evidence that the direct route, listener
registration, or cleanup shares that lock. Its full operation remains external.
[32 original-instruction cases](../../native/snow_host/markup_update_route_validation.json)
exercise the flag combinations and actual three-phase wrapper with external
helpers and phase bodies intercepted. Phase order and identical float32 argument
bits pass; no original phase body, listener mutation or live job ran.

Graph setup around `0x14090207d` constructs a job at graph+0x7218 with name
`AfterPhysicPropsUpdate` and label `PropsUpdateAfterPhysics`. It stores the
callback function `0x1408c2080` in descriptor graph+0x73b0. That function:

1. Gets the world from its captured action-graph receiver's first pointer.
2. Uses world+0x11e0 as a cached component pointer, populating it through
   `0x14139fb20` and `0x1408e3300` when null.
3. Reads cached-component+0x70 and, if nonnull, tail-calls its virtual slot 0x278.

This is a concrete **candidate** job-to-markup route. It is not yet proved that
cached-component+0x70 equals the owned component in our captured session, that
its flags choose the direct path, or that this callback executes during the
notification of interest. The earlier AI preupdate membership does not establish
this after-physics execution either.

Constructor `0x140903b80` stores its second argument as the graph owner. Its
caller at `0x1408e5402` supplies world+0x1038 as the graph and the world as owner.
This action graph is distinct from world+0xff0 -> physics+0x18, the smaller
physics scheduler state. Job offsets from one must not be applied to the other.

Next read-only check: freshly resolve action graph/world, verify the job descriptor,
join world+0x11e0 then cached-component+0x70 to the known owned component, and
record the route flags with before/after ownership guards. Then qualify a bounded
job callback capture to observe entry/return and correlate with motion/physics.
Successful sequential pointer checks would establish a session identity join,
not synchronization or permission to call subscribe/unsubscribe at that phase.

### Live after-physics check rejects the direct receiver join

The [bounded live check](../../native/snow_host/markup_job_route_live_validation.json)
found the expected job and descriptor on the **world action graph**, but its
receiver did not equal the tracked component. The action graph comes from
world+0x1038 and points back to that world. Job+0x7218 has table RVA 0x1e89618;
graph+0x73b0 contains callback RVA 0x8c2080, captured graph and invoker RVA 0x8ab390.
World+0x11e0 and cached-object+0x70 resolve successfully, with stable guards.

The resulting receiver has table RVA `0x2912dc0`, not the known component's
`0x1e789b8`. Static inspection of that actual table resolves slot 0x278 to
`0x1413c03e0`, not `0x14038a590`. Thus the proposed direct job-to-player-markup
join is rejected for this session. This does not rule out an indirect route
inside its external callees, but none has been established.

The first attempt mistakenly used the smaller physics scheduler state as the
action graph. Its job/descriptor reads were zero and the guard stopped traversal.
Constructor tracing corrected the root before the second session. Both sessions
ended normally and restored saves/settings/original DLL; no movement stimulus,
listener writes or notification calls were performed. The phase recorder plugin
was present but not triggered.

The second private capture also sampled candidate route bytes before requiring
receiver-type equality. Their interpreted flags are invalid for this receiver
and are explicitly rejected. They must not be used to claim that markup's direct
branch is disabled. The reader now restricts those layout reads to exact equality
with the known component. The actual evidence here is receiver/type mismatch,
not branch selection.

Next work should follow type-qualified callers of the known component's slot
0x278 or its three-phase wrapper. Slot numbers shared across unrelated tables
are not evidence of shared behavior. The valid local wrapper reconstruction
remains intact; this failed candidate job join does not invalidate its formulas
or qualify listener synchronization.

### Animation-event batch discovered through leaf dispatch thunks

The earlier relative-call/exception-function scan omitted tiny leaf thunks that
have no exception-table function entry. A raw instruction-pattern search followed
by disassembly found two relevant `mov rax,[rcx]; jmp [rax+0x278]` thunks:

- `0x141371bd8`, the existing physics-state after-simulation range callback.
- `0x140732320`, registered for the action graph's animation-event range job.

A [live check](../../native/snow_host/markup_after_sim_membership_validation.json)
of the first route finds zero receivers in world+0x7f0 and one in world+0x8b0.
The known component appears in neither list nor the one-entry work array at
physics-state+0xc00. Job identity, roots and source/storage guards pass. This
rejects that batch as demonstrated membership for this component in this session.
The correctly typed component flags were byte14c=0, byte14d=1, byte158=16, and
word8 bit26 set, selecting the direct local update route when invoked. These
flags do not prove invocation. Cleanup restored saves/settings/original DLL and
stopped the bottle; no movement input or listener mutation occurred.

The second thunk has a more specific static registration:

| Field | Inspected value |
| --- | --- |
| Job in world action graph | graph+0x43d8 |
| Job name | DispatchAnimEvents |
| Label | IAnimationComponent::DispatchAnimEvents |
| Gathered storage | graph+0x4570, job+0x198 |
| Callback | graph+0x4598, job+0x1c0 -> thunk RVA 0x732320 |
| Source | world+0x570, registry entry 17 |
| Gather call | 0x1408be169..0x1408be17d, append argument zero |

Setup at `0x140907fdb` stores the thunk and the nearby name/label strings.
The gather path passes world+0x570 and graph+0x4570 to `0x1408a6440`.
This is still a candidate; no live source/receiver join for this batch has yet
been performed.

The public [`capture_motion_membership`](../../engine/motion_membership_observation.py)
now accepts `job=0x43d8, entry=0x570`. It requires this batch's specific thunk and
reads receiver slot 0x278, rather than reusing the motion batches' slot 0x270.
Returned `dispatch_slot` and `callback_rva` make that distinction explicit. The
historical `motion_method_rva` field names carry the selected dispatch method,
not an assertion that every method performs motion. Fourteen portable tests pass,
including animation-slot resolution and rejecting the wrong batch thunk.

Next live check should use this bounded reader with fresh component/entity/world
identity guards and compare the known component against the source and storage.
If present, observe actual batch execution before treating registration or
cleanup as safe at that phase. A batch name alone is not a synchronization proof.

### Animation-event membership attempts remain inconclusive

[Two bounded live attempts](../../native/snow_host/markup_animation_membership_attempts.json)
did not establish membership. The first reached gameplay and the reader rejected
a changed identity/storage guard. Its exact changed range was not retained, so
this is not assigned to a claim counter, owner transition or list mutation. The
second reached the title screen without native-host readiness and timed out
before reading membership. Both stopped the bottle and restored saves/settings
and the original DLL. No movement input or listener mutation occurred.

The reader now identifies changed ranges in private diagnostics; the controller
retains read-call evidence and permits at most three fresh guarded attempts.
Acceptance conditions have not been weakened. Fifteen portable tests pass,
including continued rejection and precise diagnostics for a changed source list
and changed claim counter. These diagnostics are session-private addresses, not
portable identifiers or proof of why a field changed.

Component membership in DispatchAnimEvents remains unresolved. A later accepted
capture or a diagnosed rejection is still needed before any batch instrumentation.

### Accepted animation-event membership identifies a different owned receiver

A third [live capture](../../native/snow_host/animation_event_membership_live_validation.json)
passes all membership guards without retries. Four source receivers match gathered
storage. The tracked motion component is absent, but source/storage index 3 is a
KinoComponent owned by the same acquired actor entity. Its table and method match
the independently researched animation component. This is not a direct join to
the motion component's markup updater.

The Kino method drains an embedded event queue through event-specific handlers.
The [queued-event reconstruction](ANIMATION_COMPONENT_DISPATCH.md#queued-event-drain)
provides call pseudocode and a portable planner checked against 32 original-loop
cases. Connecting concrete event types to markup notification remains open.
This accepted capture supersedes the earlier inconclusive membership attempts
without converting them into positive evidence. All launch cleanup checks pass.

### Authored notification recorder core

[`snow_markup_trace.h`](../../native/snow_host/snow_markup_trace.h) and
[its implementation](../../native/snow_host/snow_markup_trace.c) provide bounded
recording around the inspected five-argument descriptor thunk. The caller passes
the descriptor, untagged receiver, markup ID, raw value byte and uint32 sentinel;
the recorder forwards all five unchanged to the original thunk. It never reads
or rewrites the descriptor. Entry/exit ticks, thread, caller and opaque integer
return bits accompany each record. The configured owner is an identity label,
not independently validated ownership. Clock units come from the supplied clock.

This is authored instrumentation, not recovered engine logic. Initialization is
one-shot before publication. Concurrent callers reserve separate records;
capacity exhaustion counts drops while still forwarding. Closing stops new
record admission, but cached calls continue forwarding. Records may be read only
after all admitted calls return. Drain does not permit unloading the wrapper or
freeing game storage. Exceptions or nonlocal exits can prevent drain. No capture
status implies that a listener was installed; installation needs its own receipt.

The [native fixture](../../tests/fixtures/snow_markup_trace_fixture.c), run with
`python3 -m unittest tests.test_markup_trace`, checks 800 calls from eight threads,
17 retained records and 783 drops, five-argument/result preservation, raw bytes,
close during an active call, post-close forwarding, read publication and zero
capacity. Eight tests across this recorder, notification model and listener
observer pass. Windows x64 cross-compilation passes. Native fixture execution was
on the development host, not Windows or the live game; it does not prove the
installed wrapper ABI or game callback execution.

Remaining before interception: fixture-qualified slot replacement/restoration,
entry identity checks, a storage-lifetime strategy covering listener-vector
reallocation, and retained wrapper lifetime. Then capture actual notifications
alongside motion and physics. This core alone does not close those boundaries.

The tagged-record visitor supplies the caller relationship:

```python
def visit_snow_record(task, record):
    if record.tag == 0:
        record.actor.virtual_2c0(task.elapsed_dt, task.derivative_dt)
    elif record.tag == 2:
        pass  # the inspected alternate target is a no-op
    # Other tags return without entering either target.
```

The first actor batch creates these records, claims ranges and visits each claimed
range in reverse record order. It waits for completion before backend integration.
That ordering does not establish a total order between actors on different workers.
The visitor loads its two floats from callable storage immediately before the tail
dispatch. It does not rely on the incoming floating-point register values.

A follow-up [448-case emulator check](../../native/snow_host/consumer_dispatch_validation.json)
executes the original visitor and wrapper together, using seven record tags, all
16 flag combinations and four preparation return values. Incoming scalar registers
were deliberately different from callable storage. Tag zero forwards the stored
pair, tag two executes the original no-op, and the remaining tested tags skip the
wrapper. Physics callees are still intercepted. This closes the tested carrier
boundary, not the scheduler's live membership or body-update behavior.

This gives the next recorder a more specific candidate boundary than the whole
world-step callback. A read-only entry/return trace here could record the same
actor/runtime identities, both scalar arguments, all four gates, pending vector,
and both bodies' linear and angular velocities, correlated with the existing
request and substep records. It must count skipped wrappers separately from
eligible wrappers. Changes across the shared update still include other snow
forces, so they cannot be attributed entirely to pending impulse consumption.

A later [moving-rider capture](../../native/snow_host/update_capture_live_success.json)
observed 235 paired invocations of this selected actor slot and restored it after
a bounded interval. Object lifetime guarantees and general instrumentation safety
remain unproved; that one successful run does not establish them. A vtable location is not permission
to call the function from an arbitrary host thread or proof that replacing the
slot is safe. Exact consumer entry/exit remains the stronger measurement target.

## Callback-boundary recorder

A private observation plugin now samples the pending vector, main/rider linear
and angular velocities, inverse masses, and motion state codes at actor
BeforeSimulation entry, actor return, and PhysicsWorldStep entry. It uses the
previously exercised callback-pointer replacements and restores both pointers.
This observes boundaries around the conditional producer route; it does not
intercept queue calls or the snow consumer itself.

The Wine synthetic fixture checked forwarded arguments, preserved registers,
unwinding through the actor wrapper, restoration, and known snapshot contents.
A second fixture with an invalid identity refused installation. These fixture
results establish recorder behavior in a synthetic process, not live-game safety
or impulse timing.

The portable [aggregate analyzer](../../scripts/analyze_pending_boundary.py)
accepts the private 35-column recorder format and emits no object addresses.
It groups actor entry/return and world-step entry by request, rejecting missing or
duplicate boundaries, changed object links, failed read masks, and reversed
chronology. It reports dropped/incomplete records separately from usable groups,
plus snapshot overhead and observed velocity ranges. Eleven synthetic tests cover
transitions, zero observations, identity changes, record loss, ordering and
malformed/non-finite input.

Reads remain sequential and do not pin object lifetime. A valid identity does
not establish active body membership. Zero pending values at these boundaries
cannot exclude a producer and consumer running between observations. Changes in
velocity also include ordinary physics and are not attributed to a pending
impulse merely because both appear in the same request.

### Live pending-vector observation

A ten-second bounded gameplay recording produced 7,920 complete callback records
and 720 matched actor-entry/return/world-step-entry groups, with no rejected
groups, drops or incomplete records. Both callback pointers were restored. The
launcher restored configuration and stopped the research bottle; the original
XInput DLL hash remained unchanged. A brief forward input was sent through the
existing input tool. OS delivery does not establish which game action accepted it.

The pending vector changed during the actor callback in 56 requests. All 56
had outer state 3 and inner variant 1 at both boundaries, consistent with the
statically identified producer route. Pending values were unchanged between
actor return and world-step entry in all 720 groups. Neither body's recorded
linear/angular velocity changed during the actor callback in this sample.

Pending was nonzero at 66 world-step entries. Of those, 65 were zero by the next
consecutive actor entry with unchanged object identity; one had a different
nonzero value. This bounds a clearing/replacement interval. It does not identify
the exact consumer invocation, exclude another writer, or isolate impulse-induced
velocity from gravity, contacts and constraints.

Main-body speed ranged from 0 to approximately 14.33 in the recorded convention;
angular-speed magnitude reached approximately 5.94. Snapshot overhead was 17.9 us
median, 47.8 us at the 95th percentile and 361.3 us maximum. These costs perturb
timing and are not an uninstrumented baseline.

The [sanitized aggregate](../../native/snow_host/pending_boundary_observation.json)
contains counts and timing without raw addresses or memory payloads. The next
useful measurement is a direct consumer entry/exit observation with the same
request and body identities. Until that boundary and synchronization are proved,
the host executor must not enqueue impulses concurrently with gameplay.

Timing qualification: only the first input pulse overlaps the ten-second recording.
It began about 7.04 seconds after the first recorded world-step entry and ended
at 8.55 seconds. A second pulse began at 11.43 seconds, after recording ended at
9.99 seconds. The last recorded speed was approximately 14.33, still moving.
The user observed movement followed by a stop before the window closed, but the
final stop is outside this trace. This capture must not be used as a stopping,
coasting-duration or full-action-response measurement. The private runner now
requires at least 20 seconds for riding observations and requests only one pulse;
the follow-up below validates the revised one-pulse timing.

### Input-window qualification

The analyzer accepts `--input-log` with a private input-control JSONL trace.
It compares the input and recorder QPC frequencies, checks that exactly one
hold start and successful key-release completion fall within the world-step
recording, and reports seconds observed after release. Missing, duplicate,
out-of-window, unreleased and clock-mismatched inputs are tested explicitly.
OS delivery remains distinct from game acceptance; a low final speed alone does
not prove a persistent stop or explain its cause.

The private runner discovers the window before installing the recorder and runs
a single input helper synchronously, so helper exceptions and nonzero exits
propagate to the experiment result. Riding observations require a longer window.
The runner now also checks complete recorder accounting and requires at least
ten seconds of post-release observation before reporting a fully covered input
experiment. This is a capture-quality requirement, not a claim that ten seconds
is enough for every terrain or motion to settle.

### Extended post-release observation

The revised single-pulse session recorded 29.99 seconds and 2,407 matched requests
from 53,607 complete callback records. One 1.5-second forward hold began 3.45
seconds into the trace and completed at 4.98 seconds, leaving 25.01 seconds of
post-release observation. Clock alignment confirms the whole pulse was covered.
The full-input-window quality check was performed after this session; the runner
now performs it automatically in subsequent runs.

All 58 pending-vector changes within the actor callback had state 3:1 at both
boundaries. As before, neither body's velocity changed during that callback,
and pending was unchanged from actor return to world-step entry in every matched
request. Of 69 nonzero world-step-entry observations, 68 were zero by the next
consecutive actor entry; one had a different nonzero value. This repeats the
queued-producer observation over a longer motion trace without proving the exact
consumer or exclusive ownership of the pending vector.

Additional observed state/variant pairs included 4:6 and 3:7. Their appearance is
not sufficient to name them as crash, jump or landing states. Main speed reached
54.69 and ended at 32.35 in the recorded convention. The player was still moving
at the final sample, so this is post-release coverage, not a full stopping test.
No brake or boost was injected in this experiment.

All groups passed the analyzer's checks, no records were lost, both callbacks
restored, the launcher restored configuration, and the bottle stopped. Snapshot
cost was 17.3 us median, 41.6 us at the 95th percentile and 411.8 us maximum.
See the [extended sanitized aggregate](../../native/snow_host/pending_boundary_extended_observation.json).

## Local pre-consumption branch

The flags, counter and two timers immediately before the pending-vector test
select an optional helper. They do not themselves branch around the pending
threshold. With a valid configuration and finite scalar inputs, the local flow is:

```text
if enabled_byte != 0 and blocked_byte == 0:
    if signed_counter <= 0 and timer_a <= 0 and timer_b <= 0:
        require configuration_validity_byte != 0
        if helper_gain > 0:
            optional_helper(runtime, descriptor)  # effects not reconstructed here
signed_counter = wrap_signed_32(signed_counter - 1)
check_pending_threshold_and_consume_if_above_it()
```

The prepass model reports the helper without executing it; its direct-impulse
tail is reconstructed below, while other effects remain outside that model. No sport,
landing, crash or cooldown meaning is assigned to these fields. The configuration
failure path transfers to protected code and was not executed. This local flow
also does not prove that the outer actor update always reaches this region.

The portable `pending_consumer_prepass` reports the optional call and decremented
counter. It leaves actual helper execution to a caller-supplied implementation.
It does not execute the pending consumer automatically, since the helper might
change its inputs. Its returned counter value assumes the helper did not alter
the supplied counter; the real decrement reads the counter after helper return. Counter decrement uses signed 32-bit wrap, including the
minimum signed value wrapping to the maximum value.

The original local instructions matched the portable branch/counter behavior in
[432 synthetic cases](../../native/snow_host/pending_prepass_validation.json).
The optional helper was intercepted, its runtime/descriptor arguments checked,
and it returned without effects. Every case reached the pending threshold under
that assumption. This distinguishes the nearby helper gates from the consumer's
own four-lane magnitude threshold; it is not live proof of consumer execution.

## Optional helper direct-impulse tail

The optional helper has an independently gated direct-impulse branch before it
returns to the pending consumer. Its full upstream force calculation is not yet
implemented here. The recovered submission tail takes an already-computed signed
scale and direction, timestep, descriptor scale, combined mass, configured rider
mass, mask-query result and override byte:

```text
if signed_scale < float32(-0.1):
    timed_scale = float32(signed_scale * dt)
    if mask_query_passed or override_byte != 0:
        for axis in x, y, z:
            base[axis] = float32(float32(timed_scale * direction[axis]) * descriptor_scale)
        enter_runtime_lock()
        rider_impulse = float32(configured_rider_mass * base)
        central_impulse(rider_body, rider_impulse, force=true)
        main_share = float32(combined_mass - configured_rider_mass)
        main_impulse = float32(main_share * base)
        central_impulse(main_body, main_impulse, force=true)
        leave_runtime_lock()
```

Both body pointers and valid configuration are prerequisites for this local
branch; it has no optional-rider null check. The submission order is rider then
main, whereas the pending-vector consumer uses main then optional rider. The
mask query consumes the retained modal key described in the
[contact ownership evidence](../systems/snow/contact-ownership/evidence.md),
not a current fluid-profile pointer. The override byte can permit submission
when that query fails.

The threshold is strict and checked before timestep scaling. Thus zero dt or
zero descriptor scale can still submit zero impulses with force=true. The main
mass share is not clamped when the configured rider mass exceeds combined mass.
Those shares scale the impulse; each body's separate live inverse mass then
scales its velocity change in the central-impulse routine.

`helper_direct_impulses` implements this finite-input tail with supplied upstream
values. It does not reconstruct direction production, force-curve selection,
the helper's entry gates, velocity-history updates or later scalar filters.
Do not label this path as a jump, landing or adhesion force solely from this tail.

In [192 original-instruction cases](../../native/snow_host/helper_impulse_validation.json),
submitted impulses and resulting velocities matched bit-for-bit. Cases cover
the threshold and adjacent float32 value, mask/override combinations, zero dt,
zero descriptor scale and negative main mass share. The original central-impulse
arithmetic ran; locks, mask query and backend dispatch were intercepted. Angular
velocity and the pending vector remained unchanged in this tested tail. This
is synthetic local validation, not proof of which path caused a live velocity
change. Other operations within the full helper remain outside that guarantee.

## Helper scalar force assembly

`helper_force_scale` reconstructs the scalar stage before the direct-submission
tail. It starts after the helper's geometric eligibility checks. Inputs include
two supplied curve outputs and an upstream alignment scalar. The observed pivot
and gain are 15 and 2; they are read from image-backed storage and exposed as
parameters rather than asserted to be universal constants. Units and the action
meanings of the two override bytes remain unresolved.

For finite inputs, with float32 rounding after each arithmetic operation:

```text
ceiling = 2 * pivot
if speed_scalar >= ceiling and neither override is set:
    skip scalar stage

if speed_scalar < pivot:
    speed_factor = speed_scalar * gain
elif either override is set:
    speed_factor = pivot * gain
else:
    speed_factor = (ceiling - speed_scalar) * gain
if speed_factor <= 0:
    skip scalar stage

if (measure > 0 and measure_limit > measure) or activity_scalar != 0:
    ratio = measure / measure_limit
    response = max(1, sqrt(1 - min(1, ratio)) * response_strength)
elif override_a != 0:
    response = 1
else:
    response = min(contact_time * 6, 1)

multiplier = override_gain if override_a != 0 else 1
scale = curve_a
scale *= alignment
scale *= curve_b
scale *= speed_factor
scale *= response
scale *= multiplier
scale = -scale
```

There is no lower clamp on the contact-time ramp. Override B changes the speed
branch but does not by itself substitute override A's response or multiplier.
On the square-root branch, negative measures can produce a ratio below zero
and a square-root input greater than one. The portable API rejects division by
zero only if that branch actually needs the denominator. This validation is an
authored API policy, not an original native guard.

With default pivot/gain, speed scalar 7 gives factor 14, 15 gives 30, and 20
gives 20. Scalar 30 skips when neither override is set. With either override,
the high-speed factor stays at 30. These examples do not assign m/s or km/h units.

A synthetic composition example uses speed scalar 15, unit curve/alignment/
descriptor factors, contact time 1, neither override, direction +Z and dt 1/60.
It produces scale -30. With combined mass 80 and configured rider mass 20,
the submission tail gives rider impulse (0,0,-10) and main impulse (0,0,-30).
This demonstrates the reconstructed arithmetic; it is not a measured game force
or a claim that the real producer always chooses +Z.

The [280-case original-instruction validation](../../native/snow_host/helper_force_scale_validation.json)
matched the final scale bit-for-bit over speed boundaries, both overrides, contact
ramp and square-root branches, and supplied curve values. Curve evaluator calls
were intercepted, but the original finite nonnegative square-root instructions
executed. Four additional tests cover those observations, speed-branch boundaries,
composition with the direct tail, and branch-dependent denominator validation.
The vector sequence and local entry gate are reconstructed below. Semantic
input ownership, full curve selection and outer actor eligibility remain open.

## Helper direction, alignment and entry gates

The helper's initial curve must evaluate strictly above float32 0.1. It then
continues if contact fraction is positive or override A is set. Otherwise it
requires both override B and an auxiliary scalar strictly below float32 0.05.
The auxiliary scalar's physical meaning remains unassigned. The
[144-case instruction validation](../../native/snow_host/helper_entry_validation.json)
covers equality and adjacent curve values, positive/zero/negative contact and
both overrides. The curve result is supplied; this does not validate selection
of its authored profile.

`helper_force_geometry` implements the next vector stage. Its input names describe
the operations, not fully established gameplay meanings:

```text
unit_input = normalize_with_rsqrt_refinement(direction_input)
residual = source_vector - dot(source_vector, reference_axis) * reference_axis
if residual.x^2 + residual.y^2 > float32(0.0001):
    unit_residual = normalize_with_rsqrt_refinement(residual)
    horizontal = cross(unit_residual, world_Z)
    horizontal.z = 0
    horizontal = normalize_with_rsqrt_refinement(horizontal)
    force_direction = cross(horizontal, unit_residual)
    alignment = dot(unit_residual, unit_input)
else:
    force_direction = world_Z
    alignment = 0
continue_to_scalar_stage = dot(reference_axis, unit_input) > float32(-0.6)
```

The native sequence does not normalize `reference_axis` here. Its producer must
supply the intended convention. The fallback threshold uses only the horizontal
components, although the first residual normalization uses all three components.
The output force direction has no final normalization in this block. Dot products
use x + (y + z) float32 accumulation, not an arbitrary reordered sum.

The normalization uses an approximate processor reciprocal-square-root estimate
`s` and a refinement with this operation order:

```text
n = squared_length(input)
s = RSQRT_estimate(n)
k = float32(float32(3 - float32(float32(s * n) * s)) * float32(0.5 * s))
normalized = float32(k * input)
```

The portable function requires the estimate provider explicitly. An implementation
using `1/sqrt(n)` as the initial seed is a derived numerical alternative and must
not be labeled native-estimate equivalent. The API rejects degenerate direction
inputs instead of reproducing native nonfinite results; that is an authored
validation policy. The finite-vector contract excludes those cases.

In [112 original-instruction cases](../../native/snow_host/helper_geometry_validation.json),
the portable refinement, direction, alignment and eligibility matched bit-for-bit
when supplied the RSQRT estimates captured from the same emulated instruction
execution. Cases include the horizontal fallback boundary, tilted/nonunit axes,
reversed directions and the eligibility threshold. Body-velocity reads and locks
were intercepted. This proves the tested vector sequence given those estimates,
not that every CPU or Wine backend produces identical estimates.

The reconstructed sequence now connects entry gating, geometry, scalar assembly
and direct submission. These are still separate callable stages: live input
ownership and authored curve selection remain open. The history/filter stage
below supplies the remaining local state updates, but the stages still need
whole-helper integration and validation.

## Helper velocity history and response filter

On the path that passes the helper entry gate, the native helper copies its
cached body velocity to the previous sample, reads current main-body velocity
under a read-lock pair, and replaces the current sample. It computes
`acceleration = (current - previous) / dt` componentwise with float32 rounding.
This sample precedes the helper's direct impulses. It must not be replaced with
a post-impulse velocity while claiming the same update order.

`helper_velocity_history` models the supplied samples and acceleration. Its
positive-dt requirement is authored validation; the native block has no equivalent
zero-dt guard. The lock and body read are adapter responsibilities.

After geometry/scalar processing, the helper updates two persistent scalars and
publishes a copy of both to another object. Names `rate` and `displacement` below
describe their integration relationship, not a proven animation or physical
consumer. All operations retain the native float32 ordering:

```text
stiffness = 1000 if rate > 0 else 3000
restoring = -(stiffness * displacement)
damping = -300 * rate
projection = dot(reference_axis, acceleration) * reference_axis
if projection.z < 10:
    drive = 0
else:
    drive = projection.z

new_rate = rate + dt * ((damping + restoring) / 80 + drive)
new_displacement = displacement + dt * new_rate
if new_displacement > float32(0.8):
    new_displacement = float32(0.8)
    new_rate = 0
elif new_displacement < float32(-0.2):
    new_displacement = float32(-0.2)
    new_rate = 0
store_and_publish(new_rate, new_displacement)
```

Drive exactly equal to 10 is retained. Values exactly on either displacement
bound do not trigger the rate reset. The stiffness branch tests the old rate's
sign, not displacement's sign. The divisor 80 is an arithmetic constant here;
this finding does not establish a physical mass of 80. Negative projected drive
is suppressed by the same threshold. The filter can run after geometric or scalar
force rejection, so no submitted impulse does not imply no filter-state update.
An early helper-entry return bypasses this history/filter path.

[Original-instruction validation](../../native/snow_host/helper_filter_validation.json)
matched 675 isolated filter cases and both published values bit-for-bit. A further
180-update sequence applied a drive pulse and then zero drive, feeding each
original output into the next update and matching the portable state throughout.
Twelve history cases matched both stored samples and acceleration; locks and body
reads were intercepted. These are synthetic inputs, not a live landing or body
absorption measurement. The downstream reader of the published scalars remains
unresolved.

## Relationship to the earlier ground-stick reference

The speed envelope and configured mass split also appear in the earlier
`reference.snow.ground_stick_impulses` model. The current work refines that prior
research with original-instruction validation, finite float32 operation order,
conditional response branches, history and publication. It is not evidence that
a wholly separate force was discovered. The earlier function accepts simplified
boost/timer inputs; do not silently multiply a boost and contact ramp in branches
where the native helper selects one response formula instead. Its historical
examples and provenance remain preserved.

## Compiled curve evaluation

[reference/runtime_curve.py](../../reference/runtime_curve.py) evaluates the
slope/intercept tables used by this helper. The builder added below converts
caller-supplied sampled data into the same runtime representation. Given start, positive index scale and N
slope/intercept segments:

```text
position = float32(float32(value - start) * index_scale)
if position < 0:
    segment = 0
    value = start
else:
    segment = floor(position)
    if segment >= N:
        segment = N - 1
        value = float32(float32(float32(N) / index_scale) + start)
result = float32(float32(value * slope[segment]) + intercept[segment])
```

The upper clamp uses the runtime index scale, not an assumed asset-domain endpoint.
There is no fused multiply-add. Positive scale, valid tables and representable
index conversion are authored portable-API requirements.
[180 original-instruction cases](../../native/snow_host/runtime_curve_validation.json)
matched, including execution of the finite floor helper and values near segment
boundaries. Tables were synthetic. This evaluation alone does not establish
which sport/profile table is selected live or how its coefficients were built.

## Composed helper contract

[reference/ground_response.py](../../reference/ground_response.py) provides the
callable `update(state, observation, curves, reciprocal_sqrt, force=..., submission=...)`.
It returns an immutable next state, ordered impulse submissions and optional
published scalars. Inputs and dictionary fields are specified in its docstring.
The caller supplies already-selected curve callables, which may wrap the compiled
curve evaluator, and a declared reciprocal-square-root estimate provider.

The execution order is entry curve/gate, velocity history, geometry, conditional
force curves and scale, optional direct submissions, then filter/publication.
Entry rejection preserves all supplied state and produces no publication.
Geometric rejection and the outer speed gate skip force-curve calls but still
update the filter. A nonpositive speed factor is checked after force-curve calls.
Filter acceleration always uses the pre-impulse velocity sample. Returned impulse
plans are not live body writes, and this interface does not acquire locks.

The [complete-helper validation](../../native/snow_host/helper_complete_validation.json)
executed the original helper from entry through return in 32 synthetic cases.
It ran the runtime curve evaluator and floor helper, geometry, central-impulse
arithmetic, state filter and publication. The portable composition matched
curve-call order, retained/updated history, rate/displacement, publication,
submissions and resulting linear/angular body velocities. The separate pending
vector stayed unchanged in every case. Cases include entry rejection, geometric
rejection, speed gating, override and mask combinations.

Locks, body-velocity read, mask query and backend dispatch were intercepted.
Synthetic tables, objects and captured emulated RSQRT estimates were supplied.
Thus this is an integrated local helper validation, not validation of the game's
scheduler, authored tuning selection, downstream dispatch or all possible inputs.
The published filter consumers and live ownership of its input fields remain open.

## Sampled-data builder and selected-profile adapter

`runtime_curve.compile_samples(domain, samples, zero_origin=False)` reconstructs
the native uniform-sample builder. For N segments and finite ascending bounds:

```text
width = float32(high - low)
step = float32(width / float32(N))
for i in 0 .. N-1:
    slope[i] = float32(float32(sample[i+1] - sample[i]) / step)
    x = float32(float32(float32(i) * step) + low)
    intercept[i] = float32(sample[i] - float32(x * slope[i]))
epsilon = min(float32(0.0001), float32(width * float32(0.0001)))
start = float32(low - epsilon)
index_scale = float32(float32(N) / float32(float32(2 * epsilon) + width))
```

The native alternate flag uses start=0 and one epsilon in the denominator.
It is exposed as `zero_origin=True` without assigning an unproved semantic role.
The ordinary selected-profile adapter uses the default two-sided mode. Memory
allocation is replaced by Python storage; invalid/empty domains are rejected by
our API rather than following the native protected failure paths.

[18 synthetic builder cases](../../native/snow_host/runtime_curve_builder_validation.json)
matched all coefficients, start and index scale bit-for-bit, in both modes.
The original evaluator then matched 90 queries on those generated tables.
Allocation was intercepted; coefficient generation and evaluation executed as
original instructions.

A private check also compiled the extracted force-speed, leg-coil and force-depth
curves from all 12 available simulation profiles. All 36 tables and 180 evaluation
queries matched the original routines. Only a
[profile/field/count summary](../../native/snow_host/authored_curve_validation_summary.json)
is included here. Authored samples and generated coefficients remain private.
This establishes the data-to-table arithmetic for those curves, not live selection.

`ground_response.compile_curves(selected_ground_stick_settings)` returns the
three curve callables expected by `update`:

| Helper role | Selected settings field |
| --- | --- |
| entry gate | forceSpeedCurve |
| force factor A | legCoilCurve |
| force factor B | forceDepthCurve |

These mappings follow the prior snow research. The caller must explicitly supply
one profile's `groundStickSettings` object; the adapter does not guess sport,
normal/fast state or profile ownership. It copies values into compiled tables and
does not bundle game data. This closes sampled-curve compilation while preserving
the separate unresolved question of which tuning object drives a live player.


## Published displacement to Reference pose correction

`reference.ground_response_pose` implements two local scalar consumers. Static
ownership tracing connects helper publication in the writable state buffer to
its readable counterpart after a pointer swap. The actor then either copies
that readable displacement or multiplies its previous local displacement by
float32(0.9). This decay is per invocation; no elapsed time enters this block.
The flag's complete state meaning and invocation cadence remain unresolved.
The actor reader also has outer activation gates; callers must establish those
before invoking this local model.

A later pose routine looks up the `Reference` skeleton channel, identified in
[the binding research](ANIMATION_BINDING_API.md), and reads the actor-local
scalar. Its length comes from the four-component provider vector. The supplied
factor is an argument from a selected handle; it is not established as elapsed
time. Given that length, the implemented scalar contract is:

```text
if abs(length) <= float32(0.01):
    correction_vector = zero
    leave stored_length unchanged
else:
    adjustment = 0 if suppress else float32(float32(displacement * 0.5) * factor)
    target = float32(length - adjustment)
    if not unclamped:
        target = min(upper, max(lower, target))
    correction_scale = float32(float32(target - length) * -2)
    stored_length = float32(length - float32(correction_scale * 0.5))
```

All inputs and intermediate operations in the reference model use float32.
The same native actor mode byte selects reader decay and bypasses the pose
length clamp. The API keeps the calls separate because their scheduling and
whether that mode changes between them have not been established. The suppress
flag skips displacement/factor access. Bounds are read only in the clamped path.
The short-length result returns `stored_length=None` to mean preserve the prior
value, not overwrite it with zero. Inputs are finite scalar observations; NaN
behavior and invalid native objects are outside this contract.

For an illustrative synthetic input, length=1, displacement=0.8, factor=1,
no suppression, and bounds [0.2, 1.5] produce a target near 0.6 and correction
scale near 0.8. This is a scalar correction, not a recovered distance in metres
or a complete knee/board IK solution.

[Original-instruction validation](../../native/snow_host/ground_response_pose_validation.json)
matched 24 copy/decay cases and 108 pose scalar cases bit-for-bit. Six additional
compositions executed the native pointer swap followed by the native reader,
with a different sentinel in the old readable buffer. These establish the local
buffer linkage. The scalar cases begin after the short-length gate and finish
before the final actor store; that gate and store are statically inspected.
Public tests replay the synthetic inputs and expected results, not the private
original executable.

The pose routine subsequently normalizes/transforms a vector, scales it by the
correction, and stores it for later use. The vector operations are now implemented in the extension below. Provider lookup,
final skeleton application, mode/factor producers and live publication freshness
remain outside this implementation. This supplies a concrete physics-to-pose
scalar link without claiming a complete absorption or landing animation system.


### Reference transform and correction-vector publication

`reference_pose_correction` extends the scalar contract through the local vector
calculation and actor stores. Inputs are the provider's four-component vector
and XYZW rotation, plus the explicit scalar controls described above. This
implements the valid finite-input path; the inspection API rejects degenerate
rotations or transformed directions rather than emulating invalid native data.

The provider vector's four lanes participate in its length. The rotation is
conjugated in XYZ and divided by its squared four-lane norm. Let that result
be `q`, and the provider vector be `v`. The transformed XYZ calculation is:

```text
d = q.x*v.x + (q.y*v.y + q.z*v.z)
t.xyz = 2 * (cross(q.xyz, v.xyz)*q.w + d*q.xyz + (q.w*q.w - 0.5)*v.xyz)
t.w = 0
```

This formula describes the operations, not a license to replace them with a
unit-quaternion library call: nonunit inputs retain the observed arithmetic.
The implementation rounds each multiply/add/subtract/divide to float32 and
preserves the native reduction order. It then applies the scalar length gate
and correction already documented. For an active length:

```text
n2 = (t.x*t.x + t.z*t.z) + (t.y*t.y + t.w*t.w)
s = supplied_reciprocal_sqrt_estimate(n2)
k = (3 - (s*n2)*s) * (0.5*s)
correction = ((k*t) * -0.5) * correction_scale
```

The final factor is **-0.5**, not merely a sign reversal. The implementation
returns `correction`, `stored_length`, the input length and transformed vector.
The short-length path returns a zero correction and preserves stored length.
A supplied reciprocal-square-root estimate keeps processor-specific behavior
explicit; using `1/sqrt(n2)` as a seed is a derived numerical policy.

[160 synthetic original-instruction cases](../../native/snow_host/ground_response_pose_vector_validation.json)
execute from the provider-return values through the actor's correction-vector
and stored-length writes. They include zero and threshold-length vectors,
nonunit rotations, mode variations and a nonzero fourth provider-vector lane.
Both stored outputs match bit-for-bit using the emulator's recorded RSQRT
estimates. This extends the earlier scalar-block evidence to the short-length
gate and actual local stores. Provider lookup, downstream skeleton application
and original live cadence remain unexecuted.

A follow-up search found a candidate consumer which reads the same relative
vector offset as the fourth row of a transform, composes transforms, and visits
a collection of body wrappers. It also replaces that cached transform afterward.
Offset equality alone does not prove that this is the same object type as the
producer. That identity/caller join is the next research boundary, not evidence
that this correction already reaches player-body or skeleton actuation.


### Candidate consumer dispatch audit

A follow-up static audit weakens the transform/body-consumer lead above. Two
constructors assign different virtual tables. The candidate class's relevant
slot reaches an override, a base forwarding thunk, then the transform consumer.
At the same slot, the previously identified player table selects a no-op return.
[Nine instruction/table checks](../../native/snow_host/pose_consumer_identity_validation.json)
confirm those edges and assignments in the analyzed image. The public receipt
contains the checks and their limits; private instructions remain excluded.

Therefore, this virtual-dispatch route does **not** establish player actuation.
The arithmetic implementation remains locally validated, but its correction
must not be applied to body transforms merely because the candidate reads the
same relative field offset. This is not proof the player never uses such a
consumer: a direct call, a different representation, or another state could
provide another route. None has been established here.

The producer caller obtains an actor through an embedded object's handle and
supplies its factor from a selected global handle's scalar. The next ownership
check must bind that embedded handle to the actor whose displacement reader
was traced, then follow reads under that same actor identity. Relevant private
leads retained for the next pass are the embedded object's initialization,
the displacement-reader caller, and the separate stored-length reader. Their
matching offsets and nearby code locations are leads, not sufficient type proof.
No game launch, attachment, input or live memory access was used in this audit.


### Embedded pose-helper owner handle

The setup path passes the enclosing actor as the owner argument when initializing
its embedded pose helper. The initializer calls the shared registry with key zero
and that explicit record, retains the returned entry, exchanges the helper's old
handle, releases the old reference and the temporary lookup reference, then calls
the helper's virtual initialization callback. This is ownership registration,
not an animation clone or a copy of actor data.

The existing-entry fast path uses the actor record's low-19-bit one-based index:

```text
index = (record_word & 0x7ffff) - 1
block = index >> 14
slot = index & 0x3fff
entry = block_base[block] + 24*slot
if entry.record == actor:
    return entry
```

The zero-index case, allocation and differing-record rebinding take other paths.
The arithmetic is already implemented by `engine.animation_resource_index`;
it is shared registry behavior, not an animation-only ownership scheme. The
producer caller later resolves the helper's handle to its record if entry flag
bit 31 is set, otherwise to zero. Its complete call path is not a safe public
null-checked API, so that decode must not be mistaken for lifetime validation.

[Twenty synthetic instruction cases](../../native/snow_host/pose_owner_validation.json)
execute the setup argument preparation, existing-entry lookup, initializer
retain/exchange/release sequence and caller decode. Cases span the registry
block boundary and both validity-bit outcomes. The registry's outer wrapper is
replaced with the prepared lookup result; its locks and allocation are not run.
The virtual callback is intercepted after its receiver is checked. The original
initializer preserves the returned entry's net count while decrementing the old
entry once in these non-destroying cases.

This establishes a concrete initialization route from the enclosing actor to the
pose producer's owner handle. It does not establish that every live invocation
still resolves that owner, or that the rejected transform consumer shares it.
No new native dereference or mutation API is exposed.

A separate static caller trace also places the readable-buffer swap before the
displacement reader within one actor-transform routine. An intervening virtual
call and optional entity notification remain between them. Thus local call order
is established, while same-substep freshness, cross-thread ordering, and which
caller invokes this route during gameplay remain open. The next useful trace is
the actor's stored-length consumer, preserving receiver identity through its
callers rather than matching a scalar offset alone.


### Stored-length signed-reach filter

A separate reader uses the stored Reference length in a persistent positional
correction. Its caller queries the same entity-component type key as the pose
producer's caller, then passes the returned object as the receiver. This is a
stronger static type relationship than the rejected transform-consumer offset
match. It does not prove the two callers run on the same live entity or frame.

`stored_length_filter` implements the arithmetic after provider queries and
outer gates. Inputs are four-component reference point `p`, two resolved
endpoint positions `a` and `b`, axis `n`, previous correction `old`, stored
length `L` and blend `alpha`. Endpoint roles are left explicit; the routine
queries the same two channel identifiers used by the length producer, but their
anatomical names and full contact adjustments are not inferred here.

```text
signed_distance(p, endpoint, n):
    delta = p - endpoint
    return sign(dot4(delta, n)) * sqrt(dot4(delta, delta))

left  = signed_distance(p, a, n)
right = signed_distance(p, b, n)
error = -(0.5 * (left + right) - L)
new_correction = (error * n) * alpha + (1 - alpha) * old
corrected_reference = p + new_correction
```

The sign helper returns zero for a zero dot product. Thus a nonzero endpoint
distance perpendicular to the axis contributes zero. These are **signed full
distances**, not scalar projections onto the axis. The reference implementation
preserves every float32 operation and the four-lane reduction order
`(x+z)+(y+w)`. The native block stores `new_correction` in the actor and carries
`corrected_reference` forward in a register for later calculations.

Upstream, alpha is `min(1, max(0, 6 * source_time_scalar))` using float32. The
source comes from the entity's context; its time units and relation to the
physics substep clock are not established in this pass. The axis normally uses
a normalized Reference-to-origin difference, with a transform-axis fallback at
small lengths. The local function accepts both as observations instead of
inventing an update cadence or geometry producer.

The inspected outer branch requires the decay-mode byte to be zero, another
pose-enable byte nonzero, suppression byte zero and state outside inclusive
21..23. The complete routine also has virtual capability checks and provider
availability checks. Callers of the local arithmetic must supply the active
branch's observations; the local function does not replace those gates.

[144 synthetic instruction cases](../../native/snow_host/stored_length_filter_validation.json)
matched the persistent vector store and corrected reference register bit-for-bit,
including the original sign helper calls. Cases cover alpha 0, 0.1, 0.5 and 1,
zero/perpendicular signed distance, mixed signs and nonunit input axes.
Provider queries, capability gates, endpoint/contact adjustments and final
skeleton writes were outside the emulated block. No live game access occurred.

After this block, the routine compares endpoint reach against bounds, updates
two further persistent vectors, and modifies its supplied endpoint positions.
Those later operations remain to reconstruct. This filter closes a local
stored-length consumer, not the entire procedural-pose routine.


### Endpoint reach bounds

`reach_limit_endpoints` implements the next pair of local branches. It takes
resolved endpoints, their signed distances from the **corrected** reference,
axis, above/below adjustment directions, velocity, stored rest lengths and
configured lower/upper bounds. Signed distances must be recomputed after the
stored-length filter moves the reference; the filter's earlier diagnostic
distances are not the inputs to these branches.

The native speed test is a strict squared-four-lane magnitude greater than 0.5.
At or below that threshold, each endpoint's upper bound becomes
`max(configured_upper, rest_length)` and its lower bound becomes
`min(configured_lower, rest_length)`. Above the threshold, configured bounds
are used directly. These units and the full velocity producer remain explicit.

For each endpoint `p` with signed distance `d`, axis `n` and two supplied
directions, the arithmetic is:

```text
if d > upper:
    excess = d - upper
    amount = min(0.15 if moving else 0, max(0, excess))
    p = (amount * above_direction + p) + excess * n
if lower > d:
    amount = min(0.25, max(0, lower - d))
    axial = (d - lower) + amount * 0.3
    p = (amount * below_direction + p) + axial * n
```

Each operation is float32. The two conditions are independent, as in the native
code, rather than replaced with a generic distance clamp. At low speed only the
above-direction contribution is disabled; the full axis correction still occurs.
The lower branch's 0.25 cap and 0.3 gain apply in both speed modes. Neither input
direction is silently normalized by this local model.

[192 synthetic original-instruction cases](../../native/snow_host/reach_limits_validation.json)
match both adjusted endpoint registers bit-for-bit. The executed block includes
the velocity threshold and per-endpoint rest-length bound selection. Cases
include zero speed, exactly 0.5 squared speed, a value just above that threshold,
rest lengths outside the configured interval, and above/below/in-range reaches.
Public tests also check low-speed suppression, strict threshold behavior and
lower-branch saturation. These tests do not execute provider/contact queries or
establish that a particular sport selects this branch.

The routine then turns adjusted positions into endpoint deltas, smooths those
deltas into two persistent vectors, adds offsets and writes supplied endpoint
positions. The full producer-to-final-output composition remains the next step;
these local branches alone do not write a skeleton or a physical body.


### Endpoint smoothing and output writes

`endpoint_output_stage` implements the final local output block. Inputs are two
origin positions and XYZW rotations, requested endpoint deltas, previous
persistent deltas, blend alpha, two offsets, two contact scalars, the actor mode
and the current auxiliary reference Z value. Contact scalar names are descriptive
API labels; their complete producer meaning is not assigned. All arithmetic is
float32 and all positions/deltas have four lanes.

For each endpoint:

```text
smoothed = (1 - alpha) * previous + alpha * requested_delta
bump = 0.02 if contact_scalar == 0 and not decay_mode else 0
amount = (offset + 0.13) + bump
position = amount * rotation_y_axis(rotation) + (origin + smoothed)
```

The original orientation helper computes the Y basis direction directly from
quaternion components, without normalization:

```text
Y = [2*(x*y - w*z), 1 - 2*(x*x + z*z), 2*(x*w + y*z), 0]
```

The block stores both smoothed vectors and both supplied endpoint positions.
It leaves the rotations intact. A separate output receives:

```text
reference_z = 0.1 * (offset_b + offset_a) + reference_z
```

The multiplier is 0.1, not the 0.5 used by the earlier signed-reach average.
No physical units are inferred for these offsets or the reference value.

[216 synthetic instruction cases](../../native/snow_host/endpoint_output_validation.json)
execute the original output block and both orientation-helper calls. Both
persistent vectors, both endpoint positions and the reference Z store match
bit-for-bit. Rotation bytes remain unchanged. Cases cover alpha 0/0.1/0.5/1,
negative/zero/positive contact scalars, both actor modes, identity and nonunit
rotations, and positive/negative offsets. API rejection of nonfinite or malformed
inputs is authored policy; native invalid-data behavior is outside this model.

This validates final writes to the routine's **supplied endpoint records**,
not final skeleton-palette or physical-body publication. Between reach limiting
and this block, the native path computes deltas and performs two additional
transform operations to establish an auxiliary reference. Provider/contact
production and those intermediate transforms remain to connect before treating
all these stages as one reconstructed procedural-pose routine.


### Composed active pose tail

`resolved_pose_tail` now joins the signed-length correction, remeasured signed
reach, endpoint bounds, intermediate reference-vector transformation and final
smoothing/output stages. It begins after provider/contact queries and assumes
that this active branch was selected. It is not the whole procedural-pose
routine or an animation graph evaluator.

The intervening inverse-transform helper produces a translated/scaled origin
and a conjugated rotation. This caller uses **only the rotation** to rotate the
persistent correction vector. It neither adds the inverse translation nor
multiplies by the inverse scale. The quaternion is not normalized in this helper;
replacing it with a library inverse that divides by squared norm would change
nonunit-input behavior. `reference_local_correction` preserves the actual local
operation order. The resulting vector is the auxiliary reference output before
its Z offset adjustment in the final stage.

[96 uninterrupted original-instruction cases](../../native/snow_host/pose_tail_validation.json)
execute from the signed-reach calculation through all final output stores,
including the original sign, inverse-transform, vector-rotation and orientation
helpers. Both endpoint positions, both persistent endpoint deltas, the persistent
Reference correction and the complete auxiliary reference vector match bit-for-bit.
The synthetic provider transform includes varied translation and scale, including
zero scale; the original inverse helper executes, but these values do not enter
the caller's rotation-only use. No external call in this tail is stubbed.

Earlier isolated block tests remain useful for threshold coverage. The composed
check additionally verifies that remeasuring distances from the corrected
Reference, computing endpoint deltas against the supplied origins, and applying
smoothing in the observed order are necessary to match the original stores.
Provider selection, endpoint/contact preparation, branch gates and the eventual
consumer of the supplied endpoint records remain outside this validation.

Run a synthetic five-observation sequence from the repository root:

```sh
python3 -m engine.pose_bench --request engine/examples/pose_tail_probe.json --output /tmp/pose-tail-result.json
```

The runner requires `branch="resolved_active_tail"`, initial `correction` and
`endpoints` filter states, and one to 2400 frames of explicit observations. It
carries those three filter vectors between frames and emits intermediate results,
final state, evidence limits and a canonical input digest. Blend must be within
[0,1] and decay mode must be false, consistent with this active branch gate.
The isolated native tail fixtures also exercise mode-true arithmetic without
claiming those cases pass the full routine gate. This input validation and sequence limit are authored testbench policy.
The example's geometry and contact values are synthetic. It does not feed output
positions back as physics, infer providers, access the game or commit a skeleton.
Checkpoint/resume and repeated-run equality apply to this offline sequence only.


### Ordered contact-hit response

`resolve_pose_contacts` reconstructs the hit-processing portion of the endpoint
query helper. It accepts the query's already ordered hit records, axis, existing
point/normal and initial scalar. It does not invent a collision solver, traversal
order, native handle lifetime or the meaning of the inspected flag bits.

The helper starts with an actor-supplied scalar. For each hit, a nested handle
may resolve a scalar-bearing record. A missing record or value strictly below
float32(0.05) sets the working scalar and effective hit value to zero. Otherwise
the hit value is retained separately, and a virtual capability result decides
whether to replace the working scalar. If that capability is false, the working
scalar can retain its initial value or a value from an earlier skipped hit.

```text
for hit in supplied_query_order:
    if hit.scalar_record_missing or hit.scalar < float32(0.05):
        working_scalar = 0
        effective_hit_scalar = 0
    else:
        effective_hit_scalar = hit.scalar
        if override_allowed:
            working_scalar = hit.scalar

    point = hit.point - working_scalar * axis
    if hit.flags.bit15 and hit.body_flags.bit15:
        continue
    if not hit.flags.bit24:
        point = effective_hit_scalar * axis + point
    normal = hit.normal
    return accepted=true
return accepted=false
```

Point and scalar mutations occur **before** the bit-15 skip decision. Exhausting
the hit sequence can therefore return false while leaving a modified point and
scalar. The normal changes only for an accepted hit. Do not implement a failed
query as an unconditional rollback of every output. Missing hit data is not
silently synthesized; the API models supplied observations and rejects malformed
finite-vector/flag inputs as authored inspection policy.

[240 synthetic original-instruction cases](../../native/snow_host/pose_contact_validation.json)
match the point, normal, scalar and accepted flag. Cases include absent records,
values below and exactly at the threshold, both capability outcomes, both flag
bits and ordered multi-hit sequences. The native next-hit iterator and capability
callback are intercepted with supplied results; their internals, the collision
query, registry lifetime and cleanup are not executed.

The same helper initially constructs a segment from an endpoint plus/minus
1.2 times the supplied axis, then derives its query direction and range. Its
query wrapper, hit ordering and provider-facing endpoint preparation remain open.
On return, the pose caller uses an accepted normal to choose the sign of one
adjustment direction. The returned scalar feeds the later zero/nonzero offset
condition, but its broader material/gameplay meaning is not established here.
These findings refine the pose-contact boundary; the older landing-alignment
reference remains a separate component with different inputs and behavior.

### Pose contact query segment

`reference.ground_response_pose.pose_contact_segment` now implements the local
geometry preceding collision dispatch. Each arithmetic operation rounds to
float32, including the endpoint additions before subtraction:

```text
extent = float32(1.2) * axis
start = endpoint + extent
end = endpoint - extent
delta = end - start
range = sqrt(delta.x² + (delta.y² + delta.z²))
direction = delta / range if range > 0 else delta
direction.w = 0
```

There is no preliminary axis normalization. Range is computed from the rounded
endpoints, rather than replaced by `2.4 * length(axis)`. Large coordinates can
collapse the probe to zero range. W participates in endpoint arithmetic but not
the range, and the query direction W is always cleared. These are local numeric
behaviors, not evidence that normal gameplay supplies large coordinates or
nonzero axis W.

[192 original-instruction cases](../../native/snow_host/pose_segment_validation.json)
match the query start, direction and range bit for bit. Synthetic cases cover
non-unit axes, zero XYZ extent and coordinate rounding. Execution stops before
the collision call. The active mode/enable gates are supplied, not selected by
this API. The endpoint source, collision filtering and ordering, normal-based
adjustment-direction sign, and skeleton commit remain separate boundaries.

### Contact normal orientation and pose integration

Both endpoint callers apply the same local rule after the contact helper:

```text
if accepted:
    products = normal * above_direction
    dot = (products.y + products.w) + (products.x + products.z)
    if dot > 0:
        above_direction = sign_bit_flip_all_lanes(above_direction)
```

Every multiply and addition rounds to float32. Zero dot leaves the direction
unchanged, and a rejected query does not inspect its normal. The four-lane dot
includes W. The native sign-bit operation preserves the distinction between
positive and negative zero. Crucially, the below-limit direction was computed
before this decision and is not flipped with the above-limit direction. This is
not a reflected vector, a slope projection, or a normal-driven recalculation of
both directions.

`orient_pose_contact_direction` matches [384 original-instruction checks](../../native/snow_host/pose_contact_direction_validation.json),
192 synthetic inputs executed through each endpoint's sign block. These checks
exclude direction generation and collision dispatch.

`resolved_pose_contact` combines query geometry, supplied ordered-hit processing
and this sign choice for one endpoint. `contacted_pose_tail` accepts two such
observations and feeds their final points, oriented above-limit directions and
contact scalars into `resolved_pose_tail`. It retains mutations from skipped
hits even when the contact helper returns false. Its caller still supplies the
below-limit directions and every other resolved tail input.

These composed interfaces are authored wiring of separately recovered blocks.
Unit tests verify their composition; no uninterrupted original execution across
provider lookup, collision services and the pose tail has been validated. The
collision backend, provider transforms, direction-generation normalization,
active branch selection and final skeleton commit remain unresolved here. The
interfaces run offline and do not claim live game or complete animation parity.

### Endpoint adjustment direction generation

`pose_adjustment_directions(rotation, axis, reciprocal_sqrt)` replaces the
previously supplied direction-generation formula. Rotation is an already resolved
provider quaternion in XYZW order. It is not normalized by this block:

```text
basis = [1 - 2*(y*y + z*z), 2*(w*z + y*x), 2*(z*x - w*y), 0]
above = normalize_or_preserve(cross(axis, basis))
below = normalize_or_preserve(cross(above, axis))
```

Every operation rounds to float32. For each cross-product vector, the squared
length reduction is `(y*y + w*w) + (x*x + z*z)`. If this is at most float32
`1e-10`, the original vector is retained. Otherwise, with the hardware RSQRT
estimate `s`, the multiplier is `(3 - (s*n)*s) * (0.5*s)` and each vector lane
is multiplied by it. The callback explicitly supplies this estimate; using an
exact reciprocal square root is a substitute and need not produce identical
bits. Although native instructions evaluate the estimate even for tiny vectors,
the masked result retains those vectors. The model skips the unused estimate
on that branch; floating-point exception/status flags are not modeled.

The second cross product uses the first direction **before** contact-normal
orientation. An accepted normal can subsequently reverse `above` without
recalculating `below`. A parallel axis and basis produce zero directions through
the preserve branch. Tiny vectors retain their small magnitude.

Both endpoint implementations were checked separately:
[first endpoint, 192 cases](../../native/snow_host/pose_directions_validation.json)
and [second endpoint, 192 cases](../../native/snow_host/pose_directions_second_validation.json).
Original instructions match both direction stores bit for bit with captured
RSQRT estimates. Cases include zero and parallel inputs, values around the tiny
threshold, non-unit axes and non-unit quaternions. Provider lookup/transform
selection, pose-axis construction and collision dispatch remain outside these
checks. The basis intermediate is explained by the inspected arithmetic; the
reported native comparisons target the final direction stores.

To use this with the contact pipeline, pass `above_direction` to
`resolved_pose_contact` and retain `below_direction` for the pose tail. A caller
can generate both endpoint direction pairs this way before calling
`contacted_pose_tail`. These APIs still require resolved provider rotations and
ordered hit observations; no collision hits or missing provider data are invented.

### Pose contact axis and fallback

`pose_contact_axis(reference_position, origin, fallback_axis)` implements the
axis preceding endpoint direction generation. Reference and origin are already
resolved positions. Their W lanes are cleared before subtraction:

```text
delta = xyz0(reference_position) - xyz0(origin)
length = sqrt((delta.y² + delta.w²) + (delta.x² + delta.z²))
axis = fallback_axis if length <= float32(0.01) else delta / length
```

The arithmetic rounds after each operation. The fallback is copied unchanged,
including W and magnitude. Do not normalize it or substitute a world-up vector.
The caller obtains it from a selected transform record: an entity with an
indirect transform source uses an accessor; otherwise it uses the inline record.
This identifies the local selection branch, not the accessor's implementation,
transform lifetime or the semantic source of every record.

[224 original-instruction cases](../../native/snow_host/pose_axis_validation.json)
match the axis, length and masked Reference-position stores. Cases exercise both
transform routes, threshold equality, values on either side, nonzero position W,
and non-unit fallback vectors. The indirect accessor is intercepted to return a
supplied transform; the inline route reads its prepared record directly. All
inputs are synthetic. Provider lookup and the origin producer remain outside
this validation.

Use the returned axis in `pose_adjustment_directions` and the contact/pose-tail
interfaces. This closes the local axis arithmetic, while provider coordinate
conversion, origin acquisition and collision services remain explicit inputs.

### Entity origin and rotation record

`entity_pose_transform(basis_rows, position, stored_scalar)` reconstructs the
helper supplying the pose-axis origin. It reads the entity's stored three basis
rows and position directly. It converts the basis into an XYZW quaternion, copies
position XYZ and replaces W with a separately stored scalar. The scalar's broader
meaning is not assigned here. The axis consumer subsequently clears position W.
This origin helper does not call the indirect transform accessor described above.

Let `M[r][c]` mean storage row r, column c. Arithmetic rounds to float32 after each
operation. The conversion uses these branches:

```text
t = ((M00 + M11) + M22) + 1
if t > 1:
    numerator = [M12-M21, M20-M02, M01-M10, t]
    q = numerator / (2 * sqrt(t))
else:
    i = index of largest diagonal, using strict > comparisons
    # Equal diagonals keep the earlier index.
    j = (i+1) mod 3
    k = (j+1) mod 3
    t = ((Mii - Mjj) - Mkk) + 1
    numerator[i] = t
    numerator[j] = Mij + Mji
    numerator[k] = Mki + Mik
    numerator.w = Mjk - Mkj
    q = numerator / (2 * sqrt(t))
```

The square root and doubled denominator each round separately. No basis repair,
scale removal or quaternion normalization is inserted. The inspection API
requires finite inputs and a positive finite conversion radicand; this is authored
validation policy, not recovered native error handling for malformed transforms.

[240 synthetic original-instruction cases](../../native/snow_host/entity_pose_validation.json)
match both complete output vectors bit for bit, covering all four conversion
branches. Execution includes the complete original helper, matrix-to-quaternion
routine and finite square-root path with no intercepted callees. These fixtures
use generated rotation matrices. Unit tests also describe non-orthonormal input
behavior, but those additional examples are not included in this native receipt.

The separately used indirect fallback-transform accessor has more work than a
pointer lookup: inspected code invokes a refresh helper, uses a counter and
thread-related branch, and copies four rows from an associated entity record to
its own return storage. Its refresh dependencies and concurrent lifetime are
still unmodeled. No atomic snapshot or freshness guarantee follows from the
origin conversion tests. Provider coordinate conversion also remains open.

### Provider coordinate conversion

`provider_pose_transform` recovers the direct/composed branch selected by provider
flag bit 26. The API exposes that selection as `direct`; the bit's broader name
is not established. Direct mode copies position and rotation and does not read
parent records. Composed mode uses parent position `p`, parent quaternion `q`,
child position `v` and child quaternion `c`:

```text
dot = q.x*v.x + (q.y*v.y + q.z*v.z)
cross = q.xyz cross v.xyz
rotated = 2 * ((cross*q.w + dot*q.xyz) + (q.w*q.w - 0.5)*v.xyz)
position.xyz = rotated + p.xyz
position.w = p.w
rotation = q * c
```

No quaternion normalization or position scaling by `p.w` is performed. The native
four-lane arithmetic multiplies the rotated W result by zero before adding p.w;
the implementation preserves that operation sequence. Position W is later masked
by the axis consumer. The formula assumes finite arithmetic; malformed values
and native exception flags are not modeled.

Quaternion multiplication accumulates four terms in this order, rounding every
multiply and addition to float32:

```text
result = q.w * [c.x, c.y, c.z, c.w]
result += [ q.x, -q.x,  q.x, -q.x] * [c.w, c.z, c.y, c.x]
result += [ q.y,  q.y, -q.y, -q.y] * [c.z, c.w, c.x, c.y]
result += [-q.z,  q.z,  q.z, -q.z] * [c.y, c.x, c.w, c.z]
```

[720 original-instruction checks](../../native/snow_host/provider_pose_validation.json)
use 240 synthetic inputs through three paths: the Reference position/rotation
branch, the first endpoint's inline quaternion branch and the second endpoint's
quaternion-helper branch. Both flag outcomes are exercised, including non-unit
quaternions. All compared outputs match bit for bit. The second endpoint executes
the original multiplication helper without an intercepted callee.

This resolves conversion after records have been supplied. It does not resolve
provider resource lookup, missing-channel handling, record freshness or skeleton
ownership. Use the converted Reference position with `pose_contact_axis` and the
converted endpoint rotations with `pose_adjustment_directions`. These connections
remain offline composition of separately validated stages, not a claim that the
whole original animation update has been reproduced in one execution.

### Runnable supplied-provider pose sequence

The offline runner [engine/provider_pose_bench.py](../../engine/provider_pose_bench.py)
connects entity conversion, Reference/provider conversion, axis construction,
endpoint adjustment directions, supplied-hit response and the existing pose tail.
From the repository root:

```sh
python3 -m engine.provider_pose_bench \
  --request engine/examples/provider_pose_probe.json \
  --output /tmp/provider-pose-result.json
```

The [example](../../engine/examples/provider_pose_probe.json) contains five frames
of synthetic records and synthetic reciprocal-square-root estimates. It includes
empty, accepted and skipped contacts. It contains no captured game data. The
result includes every preparation stage, query segment, visited-hit decisions,
pose outputs, final filter state and hashes of both the original request and the
resolved tail request.

Each frame supplies `entity_transform`, `reference_provider`, two
`endpoint_providers`, `fallback_axis`, two `contacts`, two `rsqrt_estimates`
sequences and the remaining `tail` observations. Reference position, provider
rotation, axis, endpoint points, above/below directions and contact scalars are
derived and cannot be overridden in `tail`. The endpoint record rotations used
by the final output stage remain separate observations from the provider rotations
used to construct adjustment directions. Query endpoint origins also remain
explicit; the runner does not equate those representations implicitly.

Estimate sequences are consumed in normalization order, skipping tiny-vector
branches. Missing or unused estimates are errors. The runner does not verify
where an estimate came from or claim it matches a particular CPU. Blend, stored
length, velocity, rest lengths, bounds, offsets and output origins/rotations still
come from the caller. Only the explicit active branch is accepted.

Filter states carry between frames. To resume, set `initial_state` to the prior
result's `final_state`; output positions are not fed back as physical motion.
Tests check resume equivalence, input preservation, accepted/skipped-hit behavior,
observation limits and the command-line output. This validates authored composition
of separately recovered blocks. It is not an uninterrupted original-game update,
collision simulation, provider lookup, skeleton commit or live modding test.

### Endpoint-record origin preparation

`pose_endpoint_origin(position, rotation)` recovers the preparation shared by the
two endpoint records. With XYZW quaternion `q`, without normalization:

```text
Y = [2*(x*y - w*z), 1 - 2*(x*x + z*z), 2*(x*w + y*z), 0]
origin = xyz0(position) - float32(0.13) * Y
```

Every arithmetic operation rounds to float32. This origin becomes the initial
contact point and query-segment center. It is also retained as the base from which
the later pose tail calculates endpoint deltas and output positions. The output
stage adds its own offset along the same endpoint rotation's Y direction. Do not
replace this input endpoint rotation with the separately selected provider rotation
used to generate adjustment directions.

[192 uninterrupted original-instruction runs](../../native/snow_host/endpoint_origins_validation.json)
validate 384 endpoint origins, including the duplicated first-origin store and
second-origin register result. Synthetic non-unit rotations and nonzero position W
are included. Execution starts after the preceding virtual callback; that callback,
record ownership and entity/context acquisition remain outside the check.

The supplied-provider runner now accepts two `endpoint_records`, each containing
`position` and `rotation`. When present, it derives contact `endpoint` and
`initial_point`, plus tail `origins` and `rotations`; duplicate overrides are
rejected. Its example uses this path. Without `endpoint_records`, the earlier
explicit-origin input form remains available. Diagnostics expose the prepared
origins either way, using null when origins were supplied directly.

The preceding runnable-sequence contract's list of supplied query origins applies
to that older explicit-origin form. Both forms still require hit observations,
initial normals/scalars, provider records and the remaining unresolved tail inputs.
No query backend or original-game execution is introduced by this integration.

### Supplied channel-table lookup and record selection

The earlier [skeletal sorted-key finding](research/skeleton.md#new-focused-check-name-lookup-is-a-sorted-key-join)
now has an executable implementation and original-instruction validation in this
pose path. `pose_channel_index(entries, key)` searches unsigned 32-bit keys using
lower bound. A matching entry returns its encoded index masked to 16 bits. Missing
table/key returns `0xffff`. Duplicate keys select the first equal entry; semantic
hash collision resolution is absent from this routine.

The table count is 16-bit and entries occupy eight bytes. The raw pose accessor
computes `record_base + 32 * (index & 0xffff)`. Each selected record holds the
four-lane position followed by XYZW rotation. The accessor itself has no bounds
or missing-index guard. Do not pass its sentinel through as a valid index.

[512 original-instruction checks](../../native/snow_host/pose_lookup_validation.json)
cover 256 complete lookup executions and 256 raw record-offset calculations.
Cases include absent/empty tables, misses, duplicate keys, unsigned high-bit keys
and encoded indices with high bits. These checks do not dereference the resulting
record address or establish table construction, sorting policy or live lifetime.

`resolve_pose_channel` selects from a supplied logical bank and rejects missing or
out-of-range records. Sorted-input checks, count limits and these errors are
**authored inspection safeguards**, not native failure behavior. In particular,
the inspected pose caller explicitly checks missing endpoint indices, while the
Reference lookup's surrounding assumptions have not been fully established.

The provider runner optionally accepts `provider_bank`, containing `entries`,
`records`, `parent_position`, `parent_rotation` and `direct`. It resolves the
inspected channel keys `0x2c52cbb0` for Reference and `0x74cb19e4`/`0xaf72d919` for
the two endpoint roles. Their human-readable endpoint names remain unassigned.
Explicit `reference_provider`/`endpoint_providers` overrides are rejected in bank
mode. The synthetic example now exercises this route; the explicit-record form
remains supported. Output marks `supplied_channel_lookup` separately from
`provider_selection=false`, which still means no active game provider was acquired.

This closes local lookup and indexing from supplied data. Active rig selection,
addon merging, table construction, record population and freshness remain open.

### Entity provider-acquisition cache

`acquire_pose_provider(cached_tag, cached_index, entity_tag, components, lookup)`
implements the local cache protocol used by the entity's pose-provider getter.
The getter obtains a type descriptor, passes an entity-local cache to a shared
resolver and selects from the entity's component-pointer array:

```text
if cached_index == 0xfffe or cached_tag != entity_tag:
    cached_tag = entity_tag
    found_slot = virtual_type_search(entity, type_descriptor)
    cached_index = 0xffff if found_slot == component_array_end else slot_index
return null if cached_index == 0xffff else components[cached_index]
```

The tag is one byte and the cached index is 16-bit. `0xfffe` forces refresh;
`0xffff` is a cached missing result. A missing result with a matching tag does not
retry. Only tag equality is checked, so this cannot establish freshness after an
unknown number of tag changes or prove that an object remains alive. The native
resolver indexes the component array without a recovered bounds guard here.

The refresh routine writes the current tag before calling the virtual search.
That search returns a pointer to a component-array slot; the refresh compares it
to the array end, otherwise derives an index from the byte difference divided by
eight. The model accepts a logical index or None from its callback and validates
bounds. It does not expose native pointers, reproduce malformed-pointer arithmetic
or claim those authored bounds errors are native behavior.

[108 original-instruction runs](../../native/snow_host/provider_cache_validation.json)
execute the public getter, type-descriptor load, cache resolver and refresh
writeback. The virtual type-search callback alone is intercepted to supply a slot
or end pointer. Comparisons cover returned component identity, updated tag/index
and whether lookup occurred. Cases include forced refresh, valid cached indices,
cached misses, changed tags and byte wrap from 255 to 0. Component identities in
the public receipt are synthetic labels, not heap addresses.

This resolves the acquisition **cache protocol**, not the virtual type-search
algorithm, entity component-array construction, provider lifetime, synchronization
or active rig selection. The supplied-provider runner continues to report no live
provider acquisition. A live adapter must reacquire and validate its entity and
component observations; a matching cache tag alone is not a lifetime guard.

### Candidate virtual component type search

A separately inspected component-search routine has the calling shape required by
the acquisition cache: entity, requested type descriptor and output slot pointer.
It appears in multiple candidate virtual-table locations. That is a lead, not a
verified binding to the active player entity's search slot. It is therefore kept
separate from `acquire_pose_provider` and the supplied-provider runner.

`component_type_slot(type_ranges, requested_range)` implements its local search.
Each component's virtual descriptor getter supplies two unsigned 16-bit fields,
here called lower and upper bounds. The requested descriptor supplies the same
pair. The inspected containment predicate is:

```text
contains(candidate) = requested.low <= candidate.low
                      and candidate.high <= requested.high
start = 0
count = number_of_components
while count != 0:
    half = count // 2
    mid = start + half
    if not contains(component[mid]) and component[mid].low < requested.low:
        start = mid + 1
        count = count - half - 1
    else:
        count = half
return start if start != count_of_components and contains(component[start])
       else missing
```

The native result is a pointer to an array slot, or the end pointer on failure.
The model returns a logical index or None. It preserves supplied order and does
not replace this algorithm with a linear first-match scan. Descriptor numbering,
array ordering and inheritance semantics must be established before assuming
that arbitrary overlapping intervals behave like a generic type hierarchy.

[240 original-instruction cases](../../native/snow_host/component_type_search_validation.json)
match the returned slot through the full candidate routine. Only component
virtual descriptor getters are supplied by the test. Cases include empty arrays,
misses, exact/broad requested ranges, duplicates, nested synthetic ranges and
unsigned high-bit values. These are local algorithm checks, not evidence that
all synthetic range configurations occur in the game.

The next binding check is to identify the actual entity virtual table through a
constructor or guarded live observation, then confirm its search slot targets
this candidate. Until that evidence exists, neither the cache's virtual callback
nor active type search is claimed fully reconstructed.

### Constructor-bound provider search

The previous candidate-search boundary is now narrowed by constructor evidence.
Three tables belong to one inspected entity construction chain: a base constructor
assigns one table, a derived constructor calls it and replaces the table, and a
further derived constructor repeats that pattern. All three assign the recovered
type-range search to the required virtual slot. The base also initializes the
provider cache tag to 255 and its index to the force-refresh sentinel `0xfffe`.

[Eight focused binding checks](../../native/snow_host/provider_binding_validation.json)
verify the three constructor stores, their search slots, two direct parent calls
and provider-cache initialization. The constructor stores are executed locally;
parent calls and table entries are checked statically. Whole constructors are not
executed. No class names or live player subtype are inferred from these checks.

[480 original-instruction checks](../../native/snow_host/provider_bound_search_validation.json)
then execute 240 search cases and 240 complete getter/cache/refresh/search cases
through these constructor-assigned tables. The second group uses forced refresh
and checks the returned component plus tag/index writeback. The virtual type-search
callback is no longer intercepted: the original search runs through the table.
Only component descriptor getters supply synthetic ranges. Tests cover all three
table variants, missing components, nested/duplicate ranges and unsigned values.

`acquire_pose_provider_by_ranges` composes the recovered cache protocol with the
range search for callers that have established applicability to this entity
family. On a valid cached path it does not read descriptors. On refresh it requires
one supplied descriptor range per component. This adds an offline inspection API,
not live pointer acquisition. A current player receiver's table, descriptor
population, component-array ordering, synchronization and lifetime still require
separate evidence. The provider runner's live-acquisition flag remains false.

### Type-range entry and exit numbering

The range fields used by component search have a concrete writer.
`number_type_subtree(children, root, counter)` reconstructs its recursive local
numbering, with ordered child relationships supplied:

```text
visit(type):
    counter = uint16(counter + 1)
    type.lower = counter
    for child in supplied_child_order(type):
        visit(child)
    counter = uint16(counter + 1)
    type.upper = counter
```

The original routine obtains a first-child index using the type's numeric ID,
walks a prepared descriptor array, and recurses while each descriptor's parent
pointer equals the current descriptor. It stops at a different parent or array
end. Thus child contiguity and order are dependencies of this routine, not a
policy chosen by the reconstruction.

[128 synthetic trees](../../native/snow_host/type_numbering_validation.json)
match every lower/upper write and the final counter through the original recursive
routine with no intercepted callees. Fixtures prepare the contiguous child table
and first-child index. They include branching trees, chains, leaves, different
starting counters and uint16 wrap. The public model uses an explicit stack and
rejects cycles/repeated reachable nodes as authored validation policy.

Before counter wrap, descendant bounds lie inside ancestor bounds. This explains
the containment predicate used by the bound component search. A unit test connects
numbering to that search; it does not establish the live component-array sort order.
The native increments wrap at 16 bits, so containment is not generally valid across
wrap. No global overflow-prevention policy is established by these local tests.

The surrounding registry routine enumerates descriptors, prepares temporary
arrays, invokes a sorting helper, builds first-child indices and runs this walker.
It also has separate root initialization and fallback assignment for unvisited
entries. Those outer operations, registration callbacks, child ordering and the
runtime registry contents remain outside the executable model. This is a recovered
subtree-numbering stage, not a complete type-registry reconstruction.

### Post-sort type assignment and disconnected fallback

`assign_type_ranges(parents, order, root)` extends subtree numbering through the
outer assignment stage, starting after the registry's sorting helper. Parent IDs
and descriptor order are explicit inputs. It builds a first-child index by walking
that order: each change to a non-null parent records the current array position.
A null parent does not reset the remembered parent. If a parent appears in a later
separate group, its recorded start is overwritten. The walker then consumes only
the contiguous group at that start. The model does not silently repair ordering.

The designated root receives lower bound 2. Its reachable children use the
previously recovered increment-on-entry/increment-on-exit routine. The root upper
bound is the incremented final traversal counter. Finally, each still-unvisited
descriptor is handled in supplied array order:

```text
unvisited.lower = counter
counter = uint16(counter + 1)
unvisited.upper = counter
counter = uint16(counter + 1)
```

That fallback does not recurse through the unvisited descriptor's children. It
therefore differs from numbering each disconnected tree as another root. The
original unvisited test checks an upper bound of zero; these tests begin with the
registry's observed initialization of lower=32767 and upper=0. The model's bounded
input size prevents reaching uint16 wrap from the fixed starting value; the
separate subtree API retains explicit wrap behavior for supplied counters.

[160 original-instruction runs](../../native/snow_host/type_assignment_validation.json)
match first-child indices, every type's final bounds and the final counter through
one uninterrupted post-sort assignment, including the original recursive calls.
No calls are intercepted. Cases contain connected and disconnected trees plus
shuffled synthetic descriptor orders. Shuffled cases verify the routine's actual
order dependency; they do not establish malformed ordering in a running game.

Registry enumeration, allocation, registration callbacks, the comparator and
sorting implementation remain outside this validation. The caller must still
supply the descriptor population and order. This extends the recovered range
writer; it does not prove live registry contents or global type-system equivalence.

### Descriptor sort keys and equal-key boundary

The registry's sorter compares three fields lexicographically as unsigned values:
a 32-bit field, the 16-bit lower-range field, then another 32-bit field. In private
layout terms these are the first and second words of a stored identifier with the
lower-range field inserted between them. Their full registration-time meanings
are not established. The comparison does **not** directly read parent pointers.
Contiguous child groups therefore depend on upstream field assignment as well as
this sort; do not replace the sort with parent-ID ordering and call it recovered.

`type_descriptor_order(keys)` implements the unambiguous order for distinct keys
and the observed stable order for arrays of at most 32 elements. Original code
uses insertion sort at that size, a partitioning path above it, and a heap fallback
when its partition budget is exhausted. Large-array equal-key rearrangement is
not yet reconstructed; the API explicitly rejects that domain.

[192 full original-sort executions](../../native/snow_host/type_sort_validation.json)
validate unsigned sorted order and identity preservation for sizes 0 through 128.
The model matches all 166 cases in its supported domain. The remaining 26 cases
have more than 32 elements and duplicate keys; **all 26 differ from stable input
order**. Their exact native permutations are retained in the synthetic receipt as
future regression targets. No calls are intercepted, including the native move
helpers. These runs do not establish heap-fallback coverage.

This distinction matters because sibling order can change assigned type numbers.
It is not enough to reproduce sorted key values while silently substituting stable
tie order. The post-sort assignment API continues to accept explicit order for
that unresolved domain. Registration callbacks, key-field producers, complete
sort tie behavior and live registry contents remain open.

### Exact partition ordering, including duplicate keys

The preceding large-array duplicate-key rejection is superseded for the native
partitioning path. `type_descriptor_order` now reconstructs its median selection,
equal-key partition swaps, budget reduction and smaller-side recursion. Arrays of
at most 32 entries still use stable insertion ordering. Larger arrays use a median
of first/middle/last; when last-minus-first exceeds 40 entries, four three-element
median operations select a median of nine samples with spacing `count // 8`.

The partition grows an equal-key region around the pivot. It scans outward,
collects equal keys at that region and swaps misplaced smaller/larger elements.
When one scan reaches its end, it rotates the equal region to continue processing
the other side. These swaps account for the observed identity order among ties.
The implementation preserves those moves rather than only producing sorted values.

After partitioning, budget becomes `floor(budget/2) + floor(floor(budget/2)/2)`.
The sorter recurses on the smaller side and iterates on the larger side. An equal
size chooses the right side for recursion. Exhausted budget on a range larger than
32 still raises an explicit error: the native heap fallback is not reconstructed.
There is no silent stable-sort substitution for that remaining branch.

All 192 earlier native permutations now match, including the 26 former failures.
[160 additional full-native-sort cases](../../native/snow_host/type_sort_partition_validation.json)
match exact identity permutations for arrays from 31 to 1,024 entries, including
sizes 40, 41 and 42 around the sampling threshold, unique and duplicate keys.
Forty-eight of these additional cases differ from stable sorting and now match
the reconstruction. Native move helpers execute without interception. The tests
establish these concrete paths and cases; they do not prove heap-fallback behavior
or registration-time key production.

### Heap fallback and complete local sort control flow

The partition-budget rejection described above is superseded. The descriptor
sorter now includes the native heap construction and heap-pop fallback. It builds
a max heap from the last parent toward the root. Each adjustment first moves the
larger child upward until reaching the bottom, choosing the **right** child on an
equal-key comparison, then moves the saved element upward only while its parent
key is strictly smaller. Heap pops use the same adjustment order. This preserves
the native identity permutation among ties.

`type_descriptor_order(keys, partition_budget=None)` starts with the record count
by default, matching the registry caller. A nonnegative explicit budget allows
branch inspection. At 32 or fewer entries insertion sorting still wins even when
the budget is zero. Larger ranges with exhausted budget use heap construction
followed by pops. The model no longer rejects that algorithm branch.

[160 additional original-sort runs](../../native/snow_host/type_sort_heap_validation.json)
match exact permutations with zero, one, two and normal-count budgets. Native
entry observations record whether heap construction actually ran, including
forced and mixed partition/heap cases. Sizes range from 2 to 257, with both odd
and even heap sizes and duplicate/unique keys. No calls are intercepted. These
cases supplement the earlier 352 partition/insertion cases, whose tests remain.

This completes the inspected local sorter control-flow implementation for
supplied valid keys within the API's count limit. It is not a completeness claim
for type registration or the game engine. Key-field production, registry callbacks,
allocation/population and live type contents remain separate unresolved work.

### Continuous descriptor preparation validation

`prepare_type_ranges(parents, keys, root)` composes the recovered sorter and range
assignment. It returns descriptor order, first-child indices, assigned ranges,
fallback nodes and the final counter. It does not reorder by parent ID. The keys
are supplied observations after registration callbacks; the sort's lower-range
key is read before the numbering stage overwrites that field.

[128 continuous original-instruction cases](../../native/snow_host/type_preparation_validation.json)
now execute the complete native sort followed by first-child indexing, designated
root assignment, recursive numbering and disconnected fallback. No calls are
intercepted. Exact comparisons cover descriptor identity order, each child-start
index, every range pair and the final counter. Sizes reach 96 descriptors and
include duplicate keys plus parent/key combinations that break contiguous child
groups, preserving the observed fallback behavior rather than repairing it.

This validates the join between sorting and numbering, beyond the prior separate
checks. The prepared tables and keys remain synthetic and supplied. Registry
enumeration, allocation, callbacks, key production and live contents remain
unmodeled; successful local preparation does not prove those inputs were acquired
from the original game correctly.

### Parent-key resolution before type preparation

The caller preceding range preparation resolves parent links from the registry.
For every enumerated descriptor, it zero-extends the sorter's first 32-bit key
field into the registry lookup key. If lookup returns an entry, the descriptor
pointer held by that entry replaces the descriptor's parent pointer. If lookup
returns no entry, the previous parent pointer remains unchanged.

```text
for descriptor in supplied_registry_enumeration:
    entry = registry_lookup(uint64(descriptor.parent_key32))
    if entry exists:
        descriptor.parent = entry.descriptor
    # Missing entry does not clear descriptor.parent.
prepare_sorted_type_ranges()
```

This identifies the first sort field's role as a parent lookup key and explains
how equal parent keys can form contiguous child groups without a pointer comparator.
It does not prove collision handling, key uniqueness, initialization of previous
parent pointers or all registration-time mutations. The third sort field's producer
remains separately unresolved.

`link_type_parents` models this pass using logical descriptor indices and a supplied
lookup callback. [128 original-instruction runs](../../native/snow_host/type_parent_link_validation.json)
match all final parent links and the ordered lookup keys, including high unsigned
keys, empty registries, successful replacements and misses retaining old links.
The registry iterator and lookup services are intercepted with supplied results;
their data-structure internals and lifetime are not validated. A separate unit test
connects parent linking to the recovered sort/numbering stages using synthetic keys.

The pass itself does not reject cycles or a descriptor resolving to itself. The
numbering inspection API's tree checks remain authored safeguards. Registration
callbacks inside preparation still run after this linking pass and before sorting;
their possible effects on descriptor fields remain an open dependency.

### Compact registry lookup

The parent-link service has a recovered compact-root branch. The low three root
bits select its representation. Tag 1 selects a compact table; a null root returns
no entry. Tag 3 selects a separate radix-tree path, which is not implemented here.
Nonzero unsupported tags take an error path, so they must not be treated as empty.

The compact table starts with a 64-bit last-key index, followed by sorted unsigned
64-bit keys. A size-dependent layout table locates a separate array of value slots.
A successful lookup returns the address of a value slot, not the stored descriptor
pointer. The parent-link caller dereferences that slot once.

```text
last = table.last_key_index
if key > keys[last]: return missing
i = 0
while key > keys[i]: i += 1
if key != keys[i]: return missing
return address_of(values[i])
```

The reference function `compact_type_registry_index(keys, key)` returns the logical
slot index. `None` as the key array represents a null root. The inspection API
accepts 1..31 keys, matching the inspected compact layout table. It checks uint64
keys and sorted order before lookup; those checks are authored safeguards, not
native validation. Equal keys select the first matching slot in synthetic tests.
This does not prove that registry insertion permits duplicates. Parent keys remain
zero-extended uint32 even though this general lookup accepts uint64 keys.

[256 original-instruction cases](../../native/snow_host/compact_registry_validation.json)
execute the complete lookup with synthetic compact/null roots and no intercepted
calls. They verify the exact returned slot location and its contents, covering all
31 compact sizes, unsigned high keys, extrema, duplicates and misses.
[128 joined cases](../../native/snow_host/type_parent_link_compact_validation.json)
execute parent linking with the original compact lookup, removing the earlier
supplied-lookup stub. Registry iteration still supplies descriptor slots. These
joined fixtures do not prove that the supplied enumeration could be produced by
the same registry's iterator. A null registry skips the entire parent-link pass;
it cannot be used to simulate missing parent keys while enumerating descriptors.

Larger tree roots, insertion, allocation, registry enumeration, lifetime and live
provider identity remain open. The compact representation does not establish which
representation the active game's type registry uses.

### Compact registry iteration and complete parent linking

The registry iterator holds a uint64 key, not an array position. The initial
operation returns the exact key if present, otherwise calls next. Next leaves a
null-root cursor unchanged. For a non-null compact root, it increments the key
first, then returns the first key greater than or equal to the incremented value.
On a match it writes the selected key back to the cursor. On exhaustion it retains
the incremented key. Incrementing the maximum uint64 key writes zero and returns
no entry, without searching again.

```text
first(table, cursor):
    entry = lookup(table, cursor.key)
    if entry exists: return entry
    return next(table, cursor)

next(table, cursor):
    if table is null: return missing
    previous = cursor.key
    cursor.key = (previous + 1) modulo 2^64
    if previous == UINT64_MAX: return missing
    i = first index where table.keys[i] >= cursor.key
    if i does not exist: return missing
    cursor.key = table.keys[i]
    return address_of(table.values[i])
```

This skips later slots with duplicate keys. Duplicate acceptance by the registry's
insertion routines remains unproved. The iterator does not store a persistent
exhausted flag: calling next again after the maximum-key wrap can restart a search
from key 1. Consumers must stop when it returns no entry. The parent-link loop does.

`compact_type_registry_cursor` exposes the recovered cursor transition as a pure
function returning `{key, index}`. `link_compact_type_registry` joins iteration and
lookup against the same supplied compact registry. Its value array contains logical
descriptor indices; descriptor arrays may also contain unregistered entries. Those
remain unchanged. Missing parent keys still preserve existing parent links.
Validation of array bounds, key ordering and descriptor indices is an authored
inspection safeguard. The functions do not allocate native nodes or read a process.

[512 original-instruction cases](../../native/snow_host/compact_iteration_validation.json)
cover initial and next operations, null roots, all compact sizes, gaps, duplicate
keys, high unsigned keys and maximum-key wrap. The lookup and search helper both
execute their original instructions; no calls are intercepted.
[160 complete parent-link cases](../../native/snow_host/compact_parent_registry_validation.json)
execute the parent-link loop with original iteration and lookup against one synthetic
table. They check the ordered visited slots, final cursor and every descriptor's
parent. Fixtures include shuffled descriptor values, unregistered descriptors,
duplicate keys and maximum keys. This removes both service stubs used in the older
joined tests and supersedes their enumeration-consistency limitation for compact
roots only. Range preparation is still validated separately.

The remaining registry boundary is the larger radix-tree representation and its
construction. Nothing here establishes which root form the live player registry
uses or proves live pointer lifetime. Registration callbacks and concrete key
production remain separate dependencies before full provider acquisition.

### Radix registry branch traversal

The larger root representation uses 16-byte nodes with a dispatch kind and
compressed-prefix metadata. Three branch families choose a key byte, check any
stored prefix above it, then continue at the selected child:

| Native kinds, hexadecimal | Layout | Selected key-byte shifts |
| --- | --- | --- |
| 0f..15 | Linear byte labels with parallel child nodes | 8, 16, 24, 32, 40, 48, 56 |
| 16..1c | Eight bitmap groups with packed child nodes | 8, 16, 24, 32, 40, 48, 56 |
| 1d..22 | Direct 256-child array | 8, 16, 24, 32, 40, 48 |
| 23 | Direct 256-child array, root entry only | 56 |

For shifts 8..40, the prefix check compares key bits from `shift+8` through 55.
Shifts 48 and 56 have no such prefix comparison. The highest byte is handled by
ancestor selection when present; these nodes do not compare it again. Do not
replace the mask with a full-key comparison. Kind 23 is special at root entry;
the general node dispatch treats it as an error.

```text
if shift < 48:
    mask = low_56_bits XOR low_(shift+8)_bits
    if ((prefix XOR key) AND mask) != 0: return missing
digit = (key >> shift) AND 255

linear:
    i = first label equal to digit
    if none: return missing
    node = children[i]

bitmap:
    group = groups[digit >> 5]
    bit = 1 << (digit AND 31)
    if (group.bitmap AND bit) == 0: return missing
    i = popcount(group.bitmap AND (bit - 1))
    node = group.packed_children[i]

direct:
    node = children[digit]
```

Empty kinds 08..0e return missing. Single-value kinds 2c..32 compare the lower
56 key bits with the node metadata and return the value slot in that node on a
match. The reconstructed API returns the supplied logical value held in that slot.
It does not return a native pointer. The same local comparison applies to all seven
single-value kinds; a different comparison based only on each kind's apparent key
width would not match the inspected dispatch.

`reference.type_registry.radix_type_registry_lookup(nodes, root, key)` models these
branches over supplied logical nodes. Node kinds are numeric; children are indices
into the supplied node array. Linear nodes have `labels` and `children`. Bitmap
nodes have eight `groups`, each with a uint32 `bitmap` and packed `children`.
Direct nodes have 256 `children`. Single-value nodes have `prefix` and uint64
logical `value`. The API checks node bounds, cycles and selected structural fields
as authored safeguards. It supports no mutation or native allocation.

[1,064 original-instruction cases](../../native/snow_host/radix_branch_validation.json)
cover every branch kind, all selected byte positions, bitmap group boundaries,
compressed-prefix misses, missing children, singleton misses and mixed paths.
[64 further cases](../../native/snow_host/radix_dense_chain_validation.json)
exercise the optimized consecutive direct-array path through all seven levels.
The complete native lookup executes against synthetic trees without intercepted
calls. These checks include low-bit-tagged child-storage pointers, which the native
routine masks before following them.

Packed multi-value leaf kinds 24..2b and 33..3b remain unsupported. Encountering
one raises `UnsupportedRegistryNode`, distinct from a missing-key result. Invalid
kinds also raise rather than silently succeeding or returning missing. The native
error structure and sentinel representation are not reproduced by this logical API.
Full tree iteration, insertion, construction, live identity and lifetime remain
open. No actual game registry or asset payload is included in the fixtures.

### Radix packed and bitmap leaves

The remaining multi-value lookup leaves now have an implementation in
`reference.type_registry`. This supersedes the unsupported-leaf boundary in the
previous section. It does not extend tree iteration or construction.

| Native kinds, hexadecimal | Key representation | Prefix comparison | Supported key count |
| --- | --- | --- | --- |
| 24..2a | Arrays of 1..7-byte unsigned keys | Bits above key width through bit 55 | Respectively 1..13, 1..51, 1..46, 1..42, 1..39, 1..36, 1..34 |
| 2b | Four 64-bit bitmaps with packed values | Bits 8..55 | Bitmap population |
| 33..38 | Inline 1-byte keys | None | Respectively 2..7 |
| 39..3a | Inline 2-byte keys | None | Respectively 2..3 |
| 3b | Inline 3-byte keys | None | 2 |

Array count bounds come from the nonzero entries in the inspected value-layout
lookup tables. They are inspection limits, not proof of every insertion policy.
Array leaves store their last-key index in the metadata's lowest byte, outside
the compared prefix. The API accepts decoded `keys` and parallel uint64 logical
`values`; physical key packing and value-slot offsets are exercised privately by
the instruction validator. Inline kinds encode their fixed count in the kind and
compare only the key's low-width bits, without a prefix check.

The 1-, 2- and 4-byte search helpers scan forward and select the first equal key.
The 3-, 5-, 6- and 7-byte helpers use block-tail tests and reverse scans. Preserve
that order even though unique sorted keys would hide the difference:

```text
threshold = {3:40, 5:24, 6:20, 7:16}[width]
block_size = 4 if width == 6 else 8
start = 0; count = key_count
if count > threshold:
    if query <= keys[threshold-1]: count = threshold
    else: start = threshold; count -= threshold
while count >= block_size:
    tail = start + block_size - 1
    if query == keys[tail]: return values[tail]
    if query < keys[tail]: count = block_size - 1; break
    start += block_size; count -= block_size
for i from start+count-1 down to start:
    if query == keys[i]: return values[i]
    if query > keys[i]: return missing
return missing
```

For example, an eight-entry 3-byte leaf containing eight equal keys selects slot
7, while the 2-byte form selects slot 0. A two-key inline 3-byte leaf selects slot
1 for equal keys. These are synthetic observations of the lookup helpers; they
do not establish that native insertion accepts duplicate keys.

Bitmap leaves select group `low_byte >> 6`, test bit `low_byte & 63`, then use the
population count of lower set bits to index packed values. Their groups have
`bitmap` and `values` fields in the logical API. This differs from branch bitmaps,
which have eight 32-bit groups and packed child nodes.

[3,501 original-instruction cases](../../native/snow_host/radix_leaf_validation.json)
cover every multi-value leaf kind, every supported array count, initial/block scan
boundaries, duplicates, unsigned extrema, prefix misses and bitmap boundaries.
The checks execute the complete native lookup and its packed search helpers with
no call interception. They include 253 top-byte branch-to-leaf joins covering every
multi-value leaf kind. Returned native slots are resolved to synthetic logical
values and compared with the reconstruction.

All normal lookup node families in the inspected dispatch now have logical models.
This remains a supplied-node inspection API, not a native registry reader. Invalid
kinds and invalid root-only kind placement still raise. The native error-record
format, raw node decoder, tree iteration, allocation/insertion, live registry owner
and object lifetime remain unresolved. A complete lookup model alone does not
establish safe component discovery in a running game.

### Bounded registry snapshot decoder

`reference.registry_snapshot.decode_type_registry(read, tagged_root, resolve_value)`
now converts supplied native-layout bytes into the validated logical registry model.
This supersedes the raw-node-decoder gap above. The module includes no process
attachment, saved addresses, native calls or memory writes.

The caller provides two callbacks:

- `read(address, size)` must return exactly that many bytes from one stable snapshot.
- `resolve_value(raw_uint64)` maps a stored value to a uint64 logical identity.
  This mapping is required; the decoder does not assume a stored pointer is a safe
  or current player component. For a type registry it may identify a descriptor,
  which is a further step removed from a component instance.

The decoder recognizes null, compact and radix roots. It masks the low three tag
bits from child-storage pointers, decodes little-endian packed keys, uses the
recovered count-dependent value-array offsets, and converts physical child links
to logical indices. Returned snapshots contain `representation`, decoded content,
`bytes_read` and `read_calls`. Native node addresses are not included. The caller's
value mapper determines whether stored values become portable identifiers.

`decoded_type_registry_lookup(snapshot, key)` performs a lookup using the recovered
compact or radix model. For example, once a caller has acquired a stable source:

```python
snapshot = decode_type_registry(read_snapshot_bytes, tagged_root,
                                descriptor_to_logical_id)
descriptor_id = decoded_type_registry_lookup(snapshot, parent_key)
```

This is a descriptor lookup, not yet `player.get_component(type)`. Component
acquisition must still join the descriptor to the player's component list and
check current ownership.

Default authored inspection limits are 4,096 logical nodes and 1 MiB of requested
bytes, and callers may lower them. The decoder rejects short reads, overflowing
read ranges, excessive counts, invalid kinds, unsupported root tags, unsorted
leaf keys and invalid mapped values. Shared physical node addresses map to one
logical node, so repeated references do not cause unbounded decoding. The lookup's
existing cycle check still rejects a cyclic traversed path. These safeguards are
not claims about native validation. The decoder visits all reachable children,
including branches a single lookup would not take, and may therefore reject a
snapshot whose queried path alone would have succeeded.

Three private validations now decode the same synthetic memory consumed by the
original instructions, then compare decoded lookup results with the native slots:

- [1,128 branch cases](../../native/snow_host/registry_decoder_branches_validation.json).
- [3,501 multi-value leaf cases](../../native/snow_host/registry_decoder_leaves_validation.json).
- [256 compact/null cases](../../native/snow_host/registry_decoder_compact_validation.json).

The 4,885 receipts include read counts and byte totals, without raw memory or game
payloads. Unit tests separately exercise mixed dense/bitmap/inline paths, packed
layout boundaries, explicit value mapping and budget/short-read failures. These
checks validate decoding against synthetic layouts and native lookup behavior;
they do not prove safe acquisition of an actual running game's registry.

Sequential live reads are not a stable snapshot merely because the decoder is
bounded. The caller still needs an ownership/lifetime check and a consistency
strategy. Native tree iteration, insertion/allocation, live registry owner binding
and the final player-component/provider join remain unresolved.

### Radix leaf cursor transitions

`reference.type_registry.radix_leaf_cursor(node, key, advance=False)` now models
initial/next cursor operations for a standalone radix leaf. It returns `{key,value}`,
where a missing value is `None` and logical value zero remains valid. All leaf
kinds 24..3b are covered. This is the leaf portion of tree iteration; it does not
search an ancestor's next sibling when the current leaf is exhausted.

Initial lookup returns an exact key without changing the cursor. If missing, it
uses next. Next writes `(key+1) modulo 2^64` before searching; an increment from
the maximum key returns missing with cursor zero. Array and bitmap leaves compare
their compressed prefix with the incremented key. A larger node prefix selects
the leaf's minimum entry and updates the prefix and suffix. A smaller node prefix
exhausts that subtree. Equal prefixes search the low-width suffix using the
recovered helper, or choose the first greater suffix if no exact key exists.
Inline leaves search their low-width suffix while retaining higher cursor bits.

Exact packed-key hits preserve the previously recovered duplicate scan order.
A gap that selects a later duplicated key chooses the first greater slot, which
can differ from the slot returned by an exact lookup of that same key. For two
inline 3-byte keys `[7,7]`, initial key 7 selects slot 1, while initial key 5 selects
slot 0 and writes cursor 7. Advancing from 7 skips both and reports exhaustion.

Single-value leaves have a less obvious rule: they compare the stored lower 56
bits with the incremented cursor's lower 56 bits, but write only their kind's
1..7-byte suffix when selecting a larger key. They retain the rest of the cursor.
For a synthetic one-byte leaf with metadata `0x1234` and initial cursor zero,
initial/next returns that value with cursor `0x34`, not `0x1234`. This fixture need
not be a constructible native root. It demonstrates why ancestor context must be
preserved and why lookup metadata alone is insufficient to invent full iteration.

[768 original-instruction cases](../../native/snow_host/radix_leaf_cursor_validation.json)
execute the complete native first/next entry points on synthetic standalone leaves,
without intercepted calls. They check exact cursor writes and selected value slots
for every leaf kind, exact/gap queries, prefix changes, duplicate selection and
maximum-key wrap. They do not establish registry insertion invariants, valid live
root forms or parent-stack traversal.

The next missing iterator work is branch descent, saved ancestor state and sibling
selection after leaf exhaustion. The snapshot decoder remains useful for known-key
lookup now; full native-order enumeration is not exposed yet.

### Radix branch iteration and sibling continuation

`radix_type_registry_cursor(nodes, root, key, advance=False)` now joins branch
descent, leaf transitions and ancestor sibling continuation. This supersedes the
missing-tree-traversal boundary above for the modeled valid node layouts.
`decoded_type_registry_cursor(snapshot, key, advance=False)` exposes the same
operation for decoded null, compact and radix snapshots without further byte reads.

Initial traversal first performs exact lookup. If it misses, it enters next.
Next increments the uint64 key and handles maximum-key wrap as already described.
Each branch compares the compressed prefix, then seeks the selected byte:

```text
seek(node, incremented_key):
    if node is a leaf: perform its recovered leaf search
    if query_prefix > node_prefix: exhaust this subtree
    if query_prefix < node_prefix: select minimum entry in this subtree
    if a child has the exact selected byte:
        save this ancestor and child position
        search that child with the incremented key
        if it returns a value: return it
    select the next child after the searched position or missing byte
    if no child remains: return to the saved ancestor
    replace this branch's byte in the cursor
    descend to that child's minimum entry
```

Linear branches retain their child-list order. Bitmap branches use increasing set
bits and packed child ranks. Direct branches skip only empty kinds 08..0e. After an
exact child exhausts, its next sibling is entered through minimum descent, not
through another comparison against the old leaf's suffix. Minimum descent rewrites
branch prefix/selected-byte fields and then the leaf's suffix using the recovered
width rules. The reconstruction uses logical recursion in place of native ancestor
storage. The native exact-descent path rejects an eighth saved ancestor; the
inspection model preserves that bound. Cycles and malformed shapes have authored
rejections rather than native memory faults.

For example, advancing from a leaf at key `0x01fe` to a sibling containing `0x0203`
returns `0x0203`. Retaining the old low byte would incorrectly skip that entry.
Exhaustion returns `value=None`. Logical value zero remains a successful result.
Callers must stop on `None`; maximum-key exhaustion writes zero, not a persistent
end flag. Enumeration should also have an application-level entry limit when
handling externally supplied or potentially inconsistent snapshots.

[3,836 original-instruction cases](../../native/snow_host/radix_tree_cursor_validation.json)
execute native first/next operations across all branch kinds, mixed three-level
trees, all leaf forms under their byte context, sibling transitions, gaps and
maximum-key wrap. They include repeated advancement until exhaustion. No calls
are intercepted. Each case also decodes the same synthetic native memory and
checks the new decoded-cursor API against the native result. Shared logical
subtrees and branches separated by large unsigned key gaps are included.

This establishes modeled traversal on the tested synthetic layouts, not native
insertion invariants or a live registry snapshot. Invalid error-record details,
allocation/mutation, current owner identity and snapshot consistency remain open.
The complete parent-link pass has previously been validated on compact registries;
its join to radix enumeration and lookup is the next integration boundary.

### Complete parent linking from a decoded registry

`reference.registry_snapshot.link_decoded_type_registry(snapshot, parent_keys,
previous_parents)` now joins decoded registry enumeration and lookup in one
parent-link pass. It supports null, compact and radix representations. Registry
values must map to indices in the supplied descriptor arrays.

```text
parents = copy(previous_parents)
entry = first(registry, cursor_key=0)
while entry exists:
    descriptor = entry.logical_value
    parent = lookup(registry, uint64(parent_keys[descriptor]))
    if parent exists:
        parents[descriptor] = parent.logical_value
    entry = next(registry, cursor_key)
return parents, visited_descriptors, visited_keys, final_cursor_key
```

Parent keys are validated uint32 values before zero-extension. A missing lookup
preserves the existing parent. Aliases can enumerate the same descriptor through
multiple registry keys; the API preserves those visits. Descriptors absent from
the registry remain unchanged. The result records both visited keys and descriptor
indices, allowing callers to inspect aliasing without assuming a bijection.

The implementation is pure: it does not modify supplied arrays or the snapshot and
performs no process reads or writes. Authored safeguards reject out-of-range logical
identities, an exceeded entry budget, or non-increasing successful cursor keys.
The entry budget defaults to 4,096 and may be set to 1..65,536. A failure raises
without returning a partial parent graph. These checks are not native insertion
rules or a claim that the original pass rejects graph cycles.

Three validations execute the complete original parent-link loop with the original
radix iterator and lookup, with no service-call interception:

- [87 branch and mixed-tree cases](../../native/snow_host/radix_parent_branches_validation.json).
- [24 cases covering every leaf kind in its branch context](../../native/snow_host/radix_parent_leaf_context_validation.json).
- [32 successful-match fixtures with 32-bit keys and high-byte aliases](../../native/snow_host/radix_parent_matches_validation.json).

The 143 fixtures compare every descriptor's final parent, the actual ordered native
visits and cursor keys, zero-extended lookup arguments, and the final cursor. They
include successful replacements, misses preserving prior links, repeated descriptor
values, unregistered descriptors and unsigned high registry keys. Synthetic native
memory is decoded before the reconstructed pass. The exported receipts contain
logical snapshots and results, not memory addresses or game payloads.

The general API also replays the earlier 160 compact parent-loop fixtures. A separate
unit test connects a synthetic radix parent graph to recovered descriptor sorting
and range numbering; this composition test is not a new continuous native execution
of linking plus range preparation.

This closes the radix-enumeration/parent-link integration boundary identified above.
The next dependencies remain registration callbacks and concrete key production,
plus live owner/lifetime and snapshot consistency. A recovered type graph can guide
component lookup, but it does not by itself identify the active player instance or
make component mutation safe.

### Registration callback dispatch observes list changes

The range-preparation callback loop does not capture a fixed list at entry. It
reads a uint16 count before the first callback, reloads the entry-array pointer for
each selected index, and reloads the count after each callback returns. Entries
have a 32-byte stride. The callback receives the entry itself as the first argument
and its stored context with the lowest two bits cleared as the second argument.
The callback return value does not control this loop.

```text
index = 0
while index < current_callback_count_uint16:
    entry = current_callback_array[index]
    entry.callback(entry, entry.tagged_context & ~3)
    index += 1
    # Re-read count; re-read array when selecting the next entry.
```

A callback that increases the count can make additional entries run in the same
pass. Reducing it to the current index or below stops further dispatch. Replacing
the array changes which entry is selected at the next index; the loop does not
restart at index zero. These are consequences of the recovered control flow, not
claims that particular game callbacks perform those mutations.

`dispatch_type_registration_callbacks(read_count, read_entry, invoke)` models the
dispatch through caller-supplied services. `read_entry(index)` must resolve the
current array and return an entry with uint64 `context`; `invoke(entry, context)`
supplies its body. A default 4,096-call budget, uint16 count checks and uint64
context checks are authored inspection safeguards. Callback exceptions propagate,
and a budget failure does not undo side effects of callbacks already invoked.
This is distinct from the pure parent-link API.

[192 original-instruction cases](../../native/snow_host/registration_dispatch_validation.json)
validate exact entry selection, context masking, and count/array refresh. Supplied
callback bodies mutate the synthetic count and array during execution. Cases cover
zero callbacks, unchanged lists, growth, shrinkage, array replacement and high
unsigned context bits. The native dispatch loop executes unchanged; callback bodies
are intercepted, so their real registration behavior remains unresolved.

The earlier ordering still applies: parent linking precedes range preparation;
preparation gathers descriptor pointers and resets their bounds, dispatches these
callbacks, then sorts and numbers the gathered descriptors. Sort keys must therefore
be observations after callback execution. The new dispatch model does not establish
which descriptors or keys actual callbacks change, nor does it prove that newly
registered descriptors are added to the already-gathered array. Concurrent changes,
callback implementations and the active registry owner remain open.

### Pose provider identified as SkeletonComponent

The concrete type requested by the cached provider getter is `SkeletonComponent`.
This is a static identity finding, not an inferred name from its behavior. The type
getter loads the global descriptor whose name metadata reads `SkeletonComponent`.
A virtual table points to that same getter in the component type-query slot. The
component constructor assigns that table after a direct call to the base
`Component` constructor. The base constructor assigns its own table, whose type
getter loads a descriptor named `Component`.

The constructor chain, table slot, type getter and descriptor metadata therefore
agree on the requested provider class. This joins the previously unnamed provider
acquisition to a concrete skeleton component. It does not establish a selected
animation clip, landing state, active player instance or complete rig binding.

[256 original-instruction cases](../../native/snow_host/skeleton_provider_binding_validation.json)
now execute the complete provider getter, cache refresh, entity range search and
component type getters through actual tables. No calls are intercepted. The cases
use the three previously verified entity-family tables and the actual `Component`
and `SkeletonComponent` tables, with supplied descriptor ranges and synthetic object
arrays. They cover empty arrays, missing skeleton components, successful search,
cache misses, matching-tag cached hits, and tag-triggered refresh. The first
observed type getter in every case is the requested `SkeletonComponent` getter.

The validation also executes the focused constructor table-assignment blocks and
verifies the direct base-constructor call encoding. It does not execute full
constructor allocation, registration or initialization. The fixtures supply valid
component-array storage and descriptor bounds; those are not acquired from a live
game. Actual descriptor getters replace the service stubs used in the older
provider-search validation.

The existing `acquire_pose_provider_by_ranges` API already matches this behavior;
its acquisition semantics did not need to change. A matching cache tag can return
the cached array slot without checking the component's type again. A synthetic
cache slot pointing to `Component` instead of `SkeletonComponent` is returned until
a tag mismatch forces search. This preserves the observed cache contract rather
than silently adding a type check. It does not prove such stale caches occur in
the game, and the cache tag alone is not a lifetime or ownership guarantee for a
mod-loader binding.

The next practical step is a guarded read of the current player's component array,
its concrete skeleton type identity and current provider/channel data. That live
join still needs owner, lifetime and snapshot-consistency evidence before exposing
a stable skeleton-component handle to mods.

### Passive skeleton binding observer

`engine.skeleton_observation.capture_skeleton_binding` implements a bounded,
read-only inspection of the recovered binding. The caller supplies a verified
image profile, player entity, external identity guards and an exact-read transport
that checks process identity and enforces timeouts. The module itself neither
opens a process nor runs game code.

The observer reads the component count as a uint16 at entity offset `0x92`,
leaving the preceding word uninterpreted. It scans at most 256 component tables,
records exact SkeletonComponent matches, and reports missing or ambiguous results
without guessing. A unique match must also pass the virtual type-getter slot,
RIP-relative descriptor-load instruction and descriptor-name checks. The return
value contains indices, cache facts, type range and boolean link observations;
it contains no object addresses or memory bytes.

The owner backlink is reported as a comparison, not treated as an established
SkeletonComponent ownership guarantee. A nonzero provider-bank pointer only
establishes presence of that pointer value. The bank is not dereferenced. Exact
table matching does not classify derived components. All retained identity spans
are reread before return, in batches of at most 32 ranges. These sequential reads
cannot exclude intervening changes or allocation reuse and do not pin lifetime.
The cache is observed without refreshing it or changing its native semantics.

Eleven synthetic tests cover the binding, stale cache, missing and ambiguous matches,
owner mismatch, non-dereferenced bank, read/count bounds, profile/type validation
and changes to retained identity spans. This is offline adapter validation; no
live skeleton capture has established its behavior against an active player yet.

### Pose-channel observation from supplied component identity

`engine.pose_channel_observation.capture_pose_channels` connects the recovered
channel lookup and provider conversion to a caller-supplied bounded read transport.
It reads SkeletonComponent's lookup pointer at `0x240`, the table's entry pointer
at `0x38` and uint16 count at `0x42`. Each sorted entry contains a uint32 key and
encoded index; lookup selects the first equal key and uses the index's low 16 bits.
A missing table or key yields `0xffff` and causes no pose-record read.

The component's `0x258` pointer selects the provider bank. Its `0x198` pointer selects
32-byte records containing four position lanes and an XYZW quaternion. The bank's
first 32 bytes contain the parent transform, and bit 26 of its `0x8c` word selects
direct copying. Otherwise the reader applies the previously recovered quaternion
and position conversion. It does not label the result world-space or identify a
clip, authored bone name, animation state or final rendered joint.

The native accessor performs no record bounds check. The observer therefore
accepts either an independently verified `record_count` from its caller or
`None` to decode the metadata bound described below. It does not infer capacity
from mapped memory or the highest referenced index. The caller also supplies identity
and record-bound guards and a process-identity-checked transport. The skeleton
binding observer does not yet automatically supply a lifetime-pinned component.

Authored inspection limits allow 16 requested keys, 4096 table entries, 4096 bytes
per read range and 32 ranges per recheck batch. The reader rejects unsorted tables,
out-of-range indices, nonfinite transforms, short reads and changed retained data.
It returns numeric transforms and channel indices without raw memory or addresses.
Before/after agreement does not establish atomicity, lifetime or unchanged data
between those reads.

Thirteen offline tests cover layout decoding, missing channels, duplicate-key
selection, direct and parent conversion, bounds, changed data and chunked tables.
One test replays all 240 supplied inputs from the existing native provider-transform
receipt and compares float32 outputs byte-for-byte. That reuses earlier native
instruction evidence; it is not a new native execution or live pose capture.

### Provider metadata supplies a transform bound and allocation size

The provider bank points to metadata at offset `0x190`. A complete native leaf
getter returns the uint16 at metadata offset `0x5a`. A transform-processing wrapper
uses that field as its count, and the called routine scales its range by 32 bytes
and advances through position/quaternion pairs. This supports interpreting it as
the transform-record count for this recovered bank layout.

Initialization stores the same metadata pointer, then selects a uint16 at metadata
`0x14` or `0x16` according to provider flag bit 28. It passes that value to an
allocation helper and stores the result in the bank's `0x198` field. The helper
passes the value unchanged as allocation size and zero-fill byte length, with
16-byte alignment. These are byte sizes, not record counts. Other routines process
typed channels at byte offsets within this storage, so total allocation size must
not be interpreted as exactly `transform_count * 32`.

```python
metadata = bank.metadata
count = metadata.transform_count_u16
size = metadata.alternate_bytes_u16 if bank.flags & (1 << 28) else metadata.primary_bytes_u16
transform_bytes = count * 32
# Authored inspection checks, not native accessor behavior:
require(transform_bytes <= size)
require(requested_index < count)
record = bank.storage + requested_index * 32
```

`reference.ground_response_pose.pose_bank_layout` expresses this selection and the
separate inspection fit check. The [512-check receipt](../../native/snow_host/pose_bank_layout_validation.json)
executes the complete native count getter and the size-selection block across 256
synthetic cases, including zero, uint16 maximum and both flag branches. Selection
stops before calling the allocator. It proves the getter/selector instructions;
it does not execute allocation, full initialization or a live skeleton binding.
The allocation-helper and transform-range interpretations above come from static
instruction inspection, not those 512 executions.

The passive channel reader now accepts `record_count=None`. In that mode it retains
and rechecks the metadata link, both size fields and the count, alongside the bank
flags and storage pointer. It rejects a transform range exceeding the selected
allocation and rejects indices outside the count before reading a record. When
all requested channels are absent, it leaves the bank unread and reports the bound
as unobserved. Supplying an integer preserves the earlier caller-verified mode.

This removes the missing-layout dependency for the reader, but not the live
validation dependency. Inconsistent or transient metadata is rejected, and these
checks cannot establish that the current allocation still matches initialization,
that an object has not been reused, or that sequential reads form one pose frame.
Nineteen observer tests now include metadata bounds and changed-metadata rejection,
plus replays of the metadata and transform receipts.

### Typed channel copying inside the provider storage

`reference.animation_channels.copy_typed_channels` reconstructs a complete native
copy routine used with the provider's mixed channel storage. The destination bank
selects metadata through `0x190`, then an eight-byte descriptor array through
metadata `0x08`. Each descriptor contains a byte offset at `+4` and a type word
at `+6`. The low four type bits select the operation; higher bits do not affect
this routine. Source and destination use the same descriptor byte offset within
their respective `0x198` storage arrays.

| Low type nibble | Copy operation |
| --- | --- |
| 0 | One byte |
| 1 through 3 | Four bytes |
| 4 | Three consecutive four-byte loads/stores, in order |
| 5 through 15 | One aligned 16-byte load/store |

These widths do not establish authored type names or numerical interpretation.
The native copy moves bits without conversion, interpolation or normalization.
The descriptor's first four bytes do not participate in this operation. A caller
supplies the starting descriptor index and count; descriptors are processed in
that order. The destination flag word at `0x8c` is ORed with bit 27 after the loop,
including an empty range. Therefore that flag alone is not evidence of a changed
pose or copied channel.

```python
for descriptor in descriptors[first:first + count]:
    offset = descriptor.byte_offset
    kind = descriptor.type_word & 15
    chunks = [1] if kind == 0 else [4] if kind < 4 else [4, 4, 4] if kind == 4 else [16]
    for width in chunks:
        destination[offset:offset + width] = source[offset:offset + width]
        offset += width
flags |= 1 << 27
```

Aliasing matters. With type 4 and destination four bytes after source, the first
four-byte write overwrites the next four-byte source. The same first word then
propagates into all three destination words. Treating this as an atomic 12-byte
copy would produce different output. Descriptor-to-descriptor aliasing also follows
the original order. The reference accepts one shared synthetic byte buffer and
logical source/destination bases to preserve those cases. It returns a new buffer;
input immutability and prevalidated bounds are authored API policy.

[256 original-instruction cases](../../native/snow_host/typed_channel_copy_validation.json)
execute the full native routine without intercepted calls. The synthetic cases
cover all 16 low-nibble types, high type bits, selected descriptor subranges,
zero-count, distinct storage, identical storage and overlapping regions. Native
storage bytes and destination flags match the reference. Seven public tests replay
that receipt and cover overlap, order, alignment policy and bounds separately.
The hex strings in the receipt are generated synthetic bytes, not game memory.

This gives the reconstruction an exact channel-copy operation and a concrete
update-flag producer. The scheduling of its callers, semantic channel names,
metadata construction and current live bank ownership remain separate questions.

### Bank-combination copy modes and descriptor groups

The three direct call sites of the typed-copy routine belong to one bank-combination
entry. `select_channel_copy` now expresses its copy branches. Mode 2 selects the
first input bank; mode 3 selects the second; mode 1 selects the first when the
float32 weight is below 0.5 and the second at or above 0.5. These are recovered
numeric mode values, not established animation-state names. Modes 0 and 4 take
arithmetic paths and remain outside this selector.

The first input bank supplies the range metadata. A mask of `0xffff` selects index
zero and the full uint16 descriptor count at metadata `0x8a`. Otherwise the code
repeatedly shifts the mask until it is at most one. The number of shifts selects a
14-byte row through the pointer at metadata `0xa4`. Zero selects row zero too.
Thus a mask with several bits set selects its highest set bit; it does not union
groups. Each row supplies a uint16 first index and six uint16 counts. A separate
selector chooses the count. Six-count bounds and containment within the supplied
full table are authored guards; the native code performs raw indexed access.

[192 native cases](../../native/snow_host/channel_copy_route_validation.json) execute
the complete entry through modes 1, 2 and 3, including the original typed-copy
callee, without intercepting calls. They cover all-table and group selection,
zero and multibit masks, all six count selectors, empty ranges, and weights just
below, equal to and above 0.5. Selected source/range, destination bytes and flags
match the composed reference. Six additional tests replay the route receipt and
check threshold and range policies. This establishes copy-path selection, not the
higher-level scheduling of the bank-combination entry or arithmetic modes.

### First live skeleton binding and rejected pose capture

After the live-probe hold was lifted, a bounded session reached the map screen.
Startup navigation sent menu keys; no gameplay input, debugger attachment or
memory writes occurred. Three passive acquisitions identified the current player.
The [address-free observation](../../native/snow_host/skeleton_binding_live_observation.json)
records the evidence and rejected-capture boundary.

The exact SkeletonComponent occupied slot 38 of 43 components. Its type getter,
descriptor name and range passed the observer checks; cache and entity tags were
both 27 and the cached slot was 38. The owner backlink matched the acquired entity.
These establish this observed binding, not a lifetime-pinned mod handle.

Two captures detected the provider pointer at component `0x258` changing between
the same two addresses. This is evidence consistent with buffer swapping, not a
proof of exactly two buffers or their ownership rules. The binding observer now
allows `include_provider_bank=False` so mutable pose storage does not define the
stable component identity. The separate pose reader retains its own bank guard;
this change does not allow an inconsistent pose capture to succeed.

The third capture reached metadata and record reads. It observed a 485-entry lookup
table, 485 transforms, primary allocation size 16758 and alternate size 16490. The
selected primary size accommodates the 15520-byte transform range. The requested
reference key resolved to index zero; both snow-endpoint keys were absent. The
bank pointer and selected-bank flags then failed rechecks, so no coherent pose
result was returned. These metadata values are observations within a rejected
capture, not a validated single-frame snapshot. Map state, sport selection and rig
identity remain possible reasons for endpoint absence and need separate evidence.

The next live/static join is the provider-pointer publication path and a reader
boundary that remains valid across animation work. Removing guard checks or
repeatedly reading until values happen to match would not establish that boundary.

### Later guard-accepted live pose read

A later passive capture accepted the player, skeleton and pose guards. The
[sanitized receipt](../../native/snow_host/pose_channel_live_observation.json)
contains metadata and channel-presence results only. Transform samples remain
private. This supersedes the earlier zero-success count for this observer;
the rejected captures remain evidence of concurrent storage changes.

The skeleton again occupied slot 38 of 43, with matching cache/entity tag 27 and
an owner backlink. Metadata bounded 485 transform records in 16758 allocated
bytes. One requested channel resolved to index zero and produced finite local
and provider-converted transforms; two keys were absent. A separate capture
observed the player actor at index 2 of five BeforeSimulation receivers. This
is not an atomic join between motion and pose. Game state and sport were not
visually confirmed; provider conversion does not establish bone/world semantics.

The API is now live-observed for an individual bounded pose read. It does not
promise one sample per animation frame, pin lifetime or identify the active clip.
A jump/landing recorder needs these explicit boundaries:

1. Reacquire session player/skeleton identities, never saved heap pointers.
2. Timestamp both ends of reads; preserve rejected reads as gaps. Do not retry
   under the same frame label or interpolate failures into measured animation.
3. Verify an animation request/epoch around the read before claiming frame
   association. Matching pointers and wall-clock times alone are insufficient.
4. Keep input press/release separate from observed ingestion and takeoff.
5. Join accepted pose samples to verified contact/controller transitions.
   Clip selection and procedural contributions still need independent evidence.

The existing final recheck can reject an ordinary buffer swap. Relaxing it needs
a verified publication/lifetime boundary, not a higher sampling success rate.

### Epoch-gated skeleton bank rotation and publication

A concrete writer now explains a two-slot rotation consistent with the live
provider-pointer changes. `reference.animation_bank.advance_pose_bank` reconstructs
its state transitions with logical bank IDs. The component fields are:

| Offset | Observed use in this routine |
| --- | --- |
| `0x210` | Address passed to lock/unlock services |
| `0x258` | Current selected provider bank |
| `0x260` | Previous selected bank |
| `0x268`, `0x270` | Two configured rotation slots |
| `0xc58` | Last processed uint32 epoch |
| `0xe8` | Flag byte whose mask `0x38` controls bank flag bit 31 |

The epoch getter loads a uint32 from a global context. Its precise relationship
to render frames, physics substeps and animation executions is not established.
The rotation compares equality; it does not require that epochs increase.

```python
lock(component.lock)
epoch = read_global_epoch()
rotated = False
if component.last_epoch != epoch:
    component.previous = component.current
    if component.last_epoch != 0xffffffff or owner.publication_present:
        if component.current == component.slot_a:
            component.current = component.slot_b
            component.slot_a.flags |= 1 << 29
            component.slot_b.flags &= ~(1 << 29)
        else:
            component.current = component.slot_a
            component.slot_a.flags &= ~(1 << 29)
            component.slot_b.flags |= 1 << 29
        if owner.publication_present:
            publication.flags |= 8
            publication.bank = component.current
        rotated = True
    component.current.flags = replace_bit_31(component.current.flags,
                                             bool(component.flags & 0x38))
    component.last_epoch = epoch
unlock(component.lock)
return rotated
```

The owner-presence check tests owner offset `0x138`; a separate helper resolves the
publication object, whose flag word and bank pointer are at `0xa8` and `0xb0`.
The initial epoch sentinel with no owner publication skips rotation but still
updates previous, bit 31 and the stored epoch. Equal epochs skip all state changes.
If current differs from slot A, the routine selects A without requiring current
to equal B. The reference preserves that branch for an external supplied bank.

[256 native cases](../../native/snow_host/pose_bank_rotation_validation.json) execute
the complete rotation routine and original epoch getter with synthetic objects.
Lock/unlock and publication-object resolution are intercepted service boundaries;
their arguments and order are checked. Actual synchronization, allocation lifetime
and concurrent execution are not exercised. Seven public tests cover receipt
replay, repeated epochs, initial sentinel, external current bank and flag retention.

This writer is a bank-selection boundary, not a completed-pose publication fence.
All three direct call sites were inspected. Two write the selected bank's first
32 bytes through a parent-transform setter after rotation returns. One of those
callers takes the same component lock around rotation and subsequent transform
operations, and releases it only afterward. Another can then run the previously
identified transform-processing path according to rotation return and bit 27.
Thus observing the new pointer or new epoch does not establish that those writes
have finished. Nested lock calls are visible statically; lock recursion semantics
have not been independently reconstructed.

Next work should join the outer update's completion to the animation job boundary,
then establish whether a reader can use the lock or a completed previous bank.
Neither reading `previous` blindly nor waiting for epoch equality supplies that
proof. The last live session did not capture the two configured slot fields, so
its alternating addresses have not yet been matched to this exact writer live.

The optional `engine.pose_channel_observation.capture_pose_interval` observer
brackets the existing guarded read with current/previous/configured-bank pointers
and the stored epoch. It rejects any endpoint difference and reports logical slot
matches, including aliases and external banks, without returning bank addresses.
This is an additional observer rejection policy. Matching endpoints do not exclude
ABA reuse, same-epoch writes or incomplete updates, and do not prove animation
completion. Four synthetic tests cover stable reads, every changed boundary field,
alias/external/null slots and truncated reads.

### Lazy getters can rotate and refresh a skeleton

Caller tracing found that the guarded outer update is also invoked by channel
accessors. One complete explicit-component rotation accessor checks component byte
`0xc80 >= 0x80`, invokes the outer update with both boolean arguments false if set,
then reloads component `0x258` and copies the selected record's quaternion. It does
not retain the pre-refresh bank. Its channel index comes from a uint16 cached slot;
this accessor does not refresh that slot's generation or reject `0xffff` itself.
A different handle-based accessor does check the component generation at `0xc74`
and refresh its cached channel index before reaching the same update gate.

`reference.animation_bank.refresh_then_read_rotation` expresses the explicit
accessor's ordering using supplied services. Its name deliberately exposes the
possible mutation. It is separate from the passive observation APIs, and its
reader owns bounds and missing-channel policy.

[256 native accessor cases](../../native/snow_host/rotation_accessor_validation.json)
cover every value of the dirty-state byte. They execute the complete accessor and
original raw quaternion-copy callee. The outer-refresh service is intercepted and
changes the selected bank to a second synthetic bank. Results prove that bytes
below 128 skip refresh and bytes at or above 128 read from the bank selected after
refresh. This does not emulate the full refresh or prove concurrent safety.

The statically inspected guarded update has the following control flow. Service
names below describe observed operations, not recovered exported engine names:

```python
if not (state_c80 >= 128 or ((state_c81 & 1) and force)):
    return
if primary_bank is None or current_bank is None or state_c76 != 0:
    return
lock(component_lock)
if state_c80 >= 128:                 # reread after locking
    transform = prepare_owner_transform()
    set_parent_transform(primary_bank, transform, reset=False)
    rotated = rotate_for_epoch()
    set_parent_transform(current_bank, transform, reset=False)
    if rotated or (current_bank.flags & (1 << 27)) or (primary_bank.flags & (1 << 27)):
        process_transforms(current_bank, primary_bank, (component_flags >> 3) & 7)
    state_c80 &= 0x7f
if force and (state_c81 & 1):
    evaluate_with_mask(0xffff, secondary_argument)
unlock(component_lock)
```

The rotation routine takes this same lock internally. The actual lock wrappers
forward into protected/runtime-resolved code, so the nested calls do not yet prove
its implementation or recursive behavior. Native validation of rotation still
uses the explicitly documented lock stubs.

A separate outer path also takes the component lock, resets per-entry bytes,
rotates, updates the component's cached owner transform, invokes another animation
operation, adjusts dirty-state bits and finally unlocks. Another simple wrapper
runs that sequence plus a further helper before unlocking. These paths establish
that there are multiple refresh/update contexts, not one isolated bank-swap call.
Their scheduler-job identities and complete callee side effects remain unresolved.

A native getter returning is therefore stronger than observing a changed bank
pointer, but it still does not pin the bank after return. The explicit accessor's
quaternion copy occurs after the guarded refresh has released its lock. External
readers must not treat its existence as a ready-made synchronized API. The next
useful investigation is the outer operations' scheduler ownership and the actual
lock service, with an in-process snapshot taken inside a validated synchronization
scope rather than after a standalone getter returns.

### Guarded refresh normal-return ordering checked

`reference.skeleton_refresh.plan_guarded_refresh` models this outer routine's
branch and service-call order. The [512-case receipt](../../native/snow_host/guarded_refresh_validation.json)
executes the complete original routine through normal return. Lock, preparation,
parent setter, rotation, transform processing and evaluation are intercepted.
The lock service supplies a changed dirty byte to verify the native post-lock
reread. Missing banks, disabled state, dirty/force/pending gates, rotation result
and current-bank processing flag are varied. Original transform arithmetic and
asynchronous work inside those services are not executed.

The dirty byte can become clean while waiting for the lock. In that case this
routine skips preparation, rotation and transform processing, while a requested
forced evaluation can still occur. On the dirty path it clears bit 7 before the
optional evaluation call. Therefore a clear dirty bit does not certify evaluation
has completed. Every tested entered-lock normal path ends with unlock; early
returns occur before lock entry. Exception unwinding is outside this receipt.

The model accepts post-lock dirty state and post-rotation bank flags as supplied
observations. Other modeled fields remain fixed across service calls in these
fixtures. It does not model arbitrary callbacks mutating pending state or banks.
The primary-bank flag and component mask branches are statically expressed;
this receipt varies only the current-bank processing flag and uses mask seven.

The next completion candidate is the outer locked scope after evaluation returns,
with owner lifetime established. Whether evaluation starts work that outlives its
return, and which scheduler job owns this scope, remain unresolved. A clear dirty
bit, matching epoch or returned standalone getter cannot replace those proofs.

### The optional evaluation call propagates linked-object transforms

Tracing the previously opaque `evaluate_with_mask` narrows its role. Its entry
reads a 16-byte-stride array and uint16 count from component `0x280`/`0x28a`.
A selector of `0xffff` clears component pending bit zero before traversing the
array, even if empty; another selector filters entries by their uint16 field at
entry `0xc`. Consecutive equal selectors reuse the calculated provider transform.
These loop and transform observations are static, not full-routine emulation.

Each eligible entry resolves a referenced object through the known status/TLS
visibility mask, requires its object field `0x18`, applies an additional component
state gate, builds a transform and chooses adjustments by a mode field. Exact
mode semantics and callback side effects remain open. This is linked-object
transform propagation, not evidence of a general animation-graph evaluator.

The per-entry tail is independently checked against
[64 original-instruction cases](../../native/snow_host/pose_propagation_validation.json).
Its operation order is:

```python
if transform_callback is not None:
    transform_callback(callback_context & ~3, transform)
    publish_transform = True
if publish_transform:
    target.virtual_transform_event(transform, transform, type_code=0x1d)
child = lookup_skeleton_component(target)
if child is not None:
    child.dirty |= 0x80
    child.pending |= 1
    if secondary_argument != 0:
        guarded_refresh(child, force=True, secondary=secondary_argument)
```

The callback context's two low tag bits are stripped. The virtual event receives
both transform references pointing to the same stack temporary. Neither fact
establishes whether a callback copies, queues or retains data. Callback, virtual
event, skeleton lookup and recursive refresh are stubbed in the tail receipt;
actual child flag writes and direct call arguments execute as original code.
The pure `plan_pose_propagation` models these effects. Its returned child bytes
are the state before any opaque recursive refresh can alter them.

A zero secondary argument still marks a found child dirty/pending, but does not
immediately refresh it. A nonzero argument makes a direct recursive call before
continuing the loop. No explicit queue submission or wait appears in this outer
routine; that observation does not exclude asynchronous behavior inside its
callbacks. Return therefore establishes completion of this traversal's direct
calls, not a completed descendant pose or all animation jobs. A dirty/pending
clear is particularly weak: the outer routine clears dirty before propagation,
and this routine clears pending before traversal.

For an in-process snapshot API, the next missing proof is the virtual transform
event/callback contract and ownership of the linked-object traversal. Do not hold
an arbitrary additional skeleton lock across this recursive path without first
establishing lock order and lifetime.

### Entity transform event scope and component callbacks

Three previously identified entity vtables resolve the propagation event to a
base implementation and two variants sharing one derived wrapper. This establishes
those routes, not the type of every object in a live linked-object list.
The [27 native cases](../../native/snow_host/transform_event_validation.json)
execute these vtable-selected routes, the base lock arithmetic and both component
loops. Thread identity, transform apply, entity refresh, component callbacks and
derived propagation remain intercepted services.

The base route uses an inline recursive spin lock at entity `0x160`: a lock word,
owner uint32 and recursion count. A different owner spins on atomic acquisition;
the same owner increments depth. Normal release decrements depth, and only zero
resets owner to `0xffffffff` and clears the lock word after a locked barrier.
Fixtures cover uncontended acquisition and same-owner depths one and three;
contention, invalid lock states and exception cleanup are not tested.

```python
enter_entity_recursive_lock()
entity.flag_1f8 = 0
for component in captured_component_list():
    component.before_transform(event)    # virtual slot 0x118
apply_entity_transform(event)
refresh_entity_transform_dependents()
entity.flag_11a = 1
for component in captured_component_list():
    component.after_transform(event)     # virtual slot 0x120
leave_entity_recursive_lock()
# Only the two inspected derived variants:
propagate_derived_entity_links(event)
```

Each component loop separately loads the array pointer and uint16 count. The
native loop captures its traversal extent once; callbacks can have unmodeled
side effects. The executable `reference.transform_event.plan_transform_event`
expresses the fixed-list normal path, not a mutable component registry.

The derived tail runs after this invocation relinquishes its acquisition. An
outer same-thread acquisition can still hold the entity lock, so saying the tail
always runs unlocked would be incorrect. Nor does this entity lock establish
skeleton-bank lifetime or lock ordering with the earlier skeleton critical section.
The next concrete callees are the transform application service and component
before/after methods for the actual linked-object types. These could forward work;
absence of an explicit enqueue in the wrapper does not establish synchronous
completion of all effects.

### Exact skeleton transform callbacks invalidate rather than evaluate

The exact SkeletonComponent vtable resolves the entity's before-transform slot
`0x118` to an immediate return. Its after-transform slot `0x120` performs only:

```python
component.dirty_c80 |= 0x80
component.pending_c81 |= 1
```

Neither callback reads the event, evaluates transforms, queues work or acquires a
lock. The callback is called inside the entity event scope established above;
that does not imply it independently takes the skeleton critical section.
[Exhaustive original-instruction execution](../../native/snow_host/skeleton_transform_notice_validation.json)
checks both callbacks for all 65,536 input byte pairs, without service stubs.
The compact receipt records enumeration order, output digests and representative
synthetic samples. `reference.transform_event.skeleton_after_transform` reproduces
the writes and preserves every unrelated bit.

This closes a concrete invalidation-to-refresh link: an entity transform event
notifies its skeleton after applying the transform, marking it for the previously
traced guarded update. The event returning can therefore mean the skeleton has
just become dirty, not that its pose reflects the new entity transform. A later
non-forced guarded refresh can process/clear dirty without taking the forced
pending-propagation branch. The identity of the later caller still matters.

These callbacks are established only for the exact inspected skeleton vtable.
Other components and overrides can have different behavior. The transform apply
service, linked-object callbacks, actual scheduler caller and lifetime exclusion
remain separate open boundaries. This result does not justify placing a pose
snapshot directly after the generic entity transform event.

### SkeletonPostUpdate reaches forced guarded refresh

Scheduler setup registers the non-getter component update under
`Anim::SkeletonPostUpdate` and `Anim::UISkeletonPostUpdate`. The world setup also
constructs a list callable under the former name. Three original instruction
slices verify the function-pointer stores; names are checked in static setup
metadata. The [route receipt](../../native/snow_host/skeleton_post_route_validation.json)
also executes the complete list adapter in 64 combinations of world/skeleton
presence across three synthetic entries, with lookup/update services stubbed.

```python
for entity in entity_list:             # uint16 count, captured at entry
    if entity.world is not None:
        skeleton = lookup_skeleton(entity)
        if skeleton is not None:
            skeleton_post_update(skeleton)
```

`reference.skeleton_refresh.plan_skeleton_post_list` expresses this adapter's
selection and order. A world pointer is only a selection gate; it does not prove
that the entity is the player, active or lifetime-pinned.

Static inspection of the registered component update finds early return when
component `0xc82` bit 2 or byte `0xc84` is set. After preliminary update helpers,
it checks dirty bit 7 or pending bit 0. If either is set, it enters the skeleton
lock, calls the previously validated guarded refresh with `force=True` and
`secondary=False`, then releases its outer acquisition. Additional update work
continues afterward. Thus this job has a concrete route to both pose refresh and
linked-object propagation, but that call deliberately does not request immediate
recursive refresh of the linked skeletons.

This is a static scheduler-to-consumer join with native setup/adapter validation,
not a live execution trace. It does not establish which job variant contains the
player, which preliminary helpers ran, or which later job consumes invalidated
linked skeletons. A snapshot candidate can now target this specific post-update
job instead of treating bank epoch equality as completion. Before exposing it,
verify live player membership, callback completion and the enclosing lifetime
scope; a pending-count of zero alone is still insufficient.

### Skeleton post-update gather membership

The gather copies the world registry at `0x4f0` into the post-update job storage
at graph `0x7908`, with count at `0x7910` and capacity at `0x7914`. It enters the
source lock at world `0x500`. The configured per-receiver callback at graph
`0x7930` is the component update identified above. This separates the post-update
registry from the previously observed physics actor registry.

The [six-case native segment check](../../native/snow_host/skeleton_post_gather_validation.json)
executes the sufficient-capacity path with lock/copy services stubbed. A nonempty
source resets count, copies receiver pointers in order, then increments count.
An empty source skips that reset and preserves existing storage/count. The segment
stops before restore/unlock; allocation and worker consumption are not tested.

`engine.skeleton_post_observation.capture_skeleton_post_membership` now exposes a
bounded passive join: current entity/world identity, exact configured callback,
source pointers, exact skeleton vtable/owner and destination indices. It guards
and rereads all observed identity/storage spans. It reports source membership
separately from destination capacity and the remaining-prefix indices. Stale
storage, including a positive retained count after an empty gather, is not proof
of an active source receiver or executed callback.

Four synthetic tests cover exact type/owner selection, empty-source stale storage,
wrong callback/owner and a changing source. The later live check below validates
one guarded membership observation.
Matching rechecks do not exclude ABA reuse or establish lifetime, atomicity or
completion. This API supplies the specific membership test needed before a
post-update player-pose callback experiment.

### Live player membership in SkeletonPostUpdate

A bounded D3DMetal session reached a recognized gameplay HUD using startup-only
navigation. A fresh player acquisition then passed the post-update reader.
The [sanitized live receipt](../../native/snow_host/skeleton_post_membership_live_observation.json)
reports two source receivers and two destination slots. The exact skeleton owned
by the acquired player was source index 1 and destination index 1. Its callback,
world links, type, owner and storage rechecks passed. Remaining claims read zero.

This closes live membership for this session. It does not show that the callback
entered, returned, or finished dependent work; zero remaining claims is not a
completion fence. No debugger, gameplay input or memory writes were used. The next
bounded probe can target this job and receiver, correlate request identity with
entry/return, and preserve the separate owner-lifetime and pose-publication checks.

### Post-update callback tracer fixture and pairing API

A private adaptation of the prior motion-order tracer now targets the skeleton
post-update callback layout. A Wine fixture runs four concurrent receiver callers
and a separate synthetic world-step caller. It uses a direct single-argument
receiver callback, matching the inspected post-update callback shape. The wrapper
preserves tested arguments/return/register state and has unwind metadata. Both
swapped callback fields restore with compare-and-swap; the module stays pinned.
A record-ready flag prevents serialization of a partially populated record.

The [sanitized fixture receipt](../../native/snow_host/skeleton_callback_probe_fixture.json)
records 6,447 paired calls, 3,224 target calls, no dropped/incomplete records and
100 successful stack walks. A separate wrong-callback fixture refuses installation
and leaves both fields untouched. These are synthetic results, not live game
callback execution or proof of safe insertion into an active lifetime scope.

`engine.callback_trace.pair_receiver_calls` pairs receiver entry/return records
using per-thread stacks, including nested calls and interleaved threads. It keeps
request-counter changes visible. Missing entries/returns, receiver mismatches,
negative time intervals, drops or incomplete records prevent complete pairing.
Feed recorder reservation order, not a cross-thread timestamp sort; retain all
receiver calls so non-target nesting is not lost. Equal numbers of entries and
returns alone are insufficient. Four tests cover these failure boundaries.

The analyzer operates on logical records, without addresses or transform payloads.
Complete pairing establishes observed normal callback returns only. It explicitly
does not establish job completion, ownership or a pose publication fence. Separate
job counters cannot be treated as a shared frame number.

Before the next live insertion, replace the tracer's fixed 500 ms settling grace
with explicit outstanding-call accounting or report the recording as partial.
Pinning the DLL prevents code unloading but does not retain the receiver. The
existing fixture validates the adapted wrapper, not exceptions through game
callbacks, long-running returns, world replacement or shutdown races.

### Explicit callback admission and bounded drain

The fixed settling delay described above is superseded by an explicit recording
lifecycle. The adapted tracer serializes admission and record publication with a
private lock, calls the original callback outside that lock, and retains an
admission token in its wrapper frame. Its normal teardown is:

```python
restore_callback_fields_with_compare_exchange()
close_new_recording_admission()
wait_until(admitted_calls_outstanding == 0, deadline=5_seconds)
seal_recording()                      # rejects later record writes
serialize_ready_records()
```

Each admitted entry increments outstanding; its normal return records an exit
while recording remains open, then decrements outstanding. New entries after
admission closes still call the original but produce no trace records. A timeout
seals a partial recording with the outstanding count. Late returns cannot modify
the sealed record array. Failure-path serialization also seals recording first.
An exception bypassing the normal-return wrapper leaves an outstanding call and
therefore makes the bounded drain partial; this is not exception interception.

[Four Wine fixtures](../../native/snow_host/skeleton_probe_drain_fixture.json) cover
normal concurrent calls, a 3000 ms delayed callback, an 8000 ms callback exceeding
the 5000 ms drain, and identity refusal. The slow case drains with balanced pairs.
The timeout case reports `restored_partial`, one outstanding call and one unmatched
entry; the public trace analyzer correctly refuses complete pairing. Refusal has
no recorded calls. Complete pairing of an empty trace does not mean installation
or execution occurred; consumers must also inspect capture status and call count.

This is recording completion for admitted normal calls, not process quiescence.
A thread can retain a previously loaded wrapper pointer and enter later. The
module remains pinned and forwards those calls without recording. No claim of
receiver lifetime, safe DLL unloading or animation-job completion follows. Before
live insertion, reacquire the session's exact player and job identities and retain
the bounded watchdog/restoration checks. Shared instrumentation adds contention;
fixture timings are not engine performance measurements.

### Live player post-update callback entry and return

An eight-second in-process trace after fresh gameplay/player acquisition recorded
[649 player-skeleton call pairs](../../native/snow_host/skeleton_post_callback_live_observation.json)
in SkeletonPostUpdate. Each of the 649 observed target request pairs had exactly
one entry and matching normal return. No target call changed its started/requested
counters between entry and return. Calls ran on ten worker threads. Across both
receivers the recorder paired 1298 calls; no records were dropped/incomplete, no
entries were unmatched, and outstanding admitted calls were zero at sealing.

The experiment temporarily replaced two callback fields: post-update with an
entry/return wrapper and world-step with an entry recorder. Both were restored.
No gameplay input or debugger was used, but module loading and callback swaps are
process mutations; this was not a passive read. The session stopped and bytewise
checks confirmed bottle/game settings restoration. No pose payloads are published.

This closes the normal callback-execution boundary for the observed player and
session. It does not establish all modes, exception paths or a safe pose-copy
scope. The callback can leave linked skeletons dirty, and opaque callbacks may
forward work. The next test should establish receiver lifetime and a guarded
snapshot inside an appropriate update/lock scope, rather than declaring callback
return a universal completed-animation fence. Cross-job ordering is not inferred
by equating their independent request counters.

### Post-update tail cadence and remaining linked work

The callback does not return immediately after the guarded refresh. It invokes a
helper that holds a separate spin lock at component `0xc48` while traversing
48-byte entries from `0xc60`, count `0xc6a`. Static inspection shows referenced
entity visibility checks, removal of unresolved entries, skeleton lookup and
conditional linked-skeleton updates/forced refresh. This is separate from the
component critical-section wrapper at `0x210`; the helper is not fully emulated
here. Therefore one lock does not cover all post-update work.

After that helper, the callback updates cadence state with the following exact
arithmetic, expressed by `reference.skeleton_cadence.advance_skeleton_cadence`:

```python
# uint8 counter c8c, interval ea, flags c8d, dirty c80
if interval != 0 and counter % interval != 0 and not (flags & 1):
    accumulated_c88 = float32(accumulated_c88 + selected_world_dt)
else:
    accumulated_c88 = 0.0
counter = (counter + 1) & 0xff
flags &= 0xfe
dirty &= 0xef
```

The modulo uses the pre-increment counter. `interval=0` avoids division and resets
elapsed accumulation. Counter wrap is byte arithmetic: interval three resets at
both 255 and zero, two adjacent calls. No clamping or finite-value guard occurs in
this tail. The dt source is the owner's selected world time-group field `0x18`;
owner flag bit 58 selects between the previously identified time-group blocks.
This does not establish a fixed animation frame rate or original authoring units.

[6144 original-instruction cases](../../native/snow_host/skeleton_cadence_validation.json)
execute the full cadence tail with no service stubs, covering all counter values,
six intervals, reset-flag states and both world time-group branches. Outputs match
float32 accumulator bytes and the three modified bytes. The receipt stores an
ordered output digest and synthetic examples. Tests also exercise interval zero,
wraparound and preservation of unrelated flag bits.

An earlier path in the same callback adds this accumulator to selected dt before
calling the main update helper. That use is statically observed, but the full
mode-dependent update cadence is not reconstructed by this tail alone. The new
API models the actual accumulation rule rather than approximating it as a fixed
number of frames. A future snapshot must distinguish selected-bank state, linked
updates and cadence bookkeeping; clear dirty bit 4 at return is not clear dirty
bit 7, and neither supplies a lifetime fence.

### Skeleton lock adapters resolved in a live process

The lock pair used by the rotation and outer refresh routines now has exact API
identity. A passive observation in an existing DXMT Wine session resolved:

| Operation | Exact destination | Verified live instruction spans |
| --- | --- | --- |
| Entry | `ntdll.dll!RtlEnterCriticalSection` | 54 |
| Exit | `ntdll.dll!RtlLeaveCriticalSection` | 64 |

Both targets were in executable module sections. Encoded target slots and module
headers were reread unchanged. The [public receipt](../../native/snow_host/skeleton_lock_target_observation.json)
contains the evidence summary without process addresses, module paths or memory
bytes. No lock was acquired, no game code was invoked, and no input, debugger or
memory write was used. A launch attempt refused to start because the other agent's
session was active; this check did not change that session's renderer or lifecycle.

The entry wrapper first dereferences its argument. Thus the component field at
`0x210` is a wrapper containing the critical-section pointer, not necessarily an
inline critical-section structure at that offset. Its protected transfer reduces
to an encoded-slot load plus a fixed addend. Forty synthetic transfer cases reached
a supplied target with the dereferenced pointer in RCX, the original caller stack
and return address intact, and tested callee-saved registers preserved. Each case
read one encoded image-data slot. The external API itself was not executed.

The earlier exit-adapter identity had already appeared in engine-event lifecycle
research. This pass independently resolved both entry and exit in the same current
process, joining that existing evidence to the skeleton call sites. Earlier
sections describing the lock service as unresolved now refer only to implementation,
contention and coverage; the target API names are resolved.

This narrows the snapshot design but does not authorize treating the lock as a
universal pose fence. The observation did not acquire the current player's actual
critical-section pointer, pin its component, test contention, or show that every
writer of the selected bank uses this lock. The pure rotation/accessor models
continue to use service stubs and make no synchronization guarantee.

The next concrete gates are:

1. Acquire the current skeleton, its lock-wrapper pointer and configured bank
   slots together under identity checks; compare the rotating pointer with those
   slots rather than inferring them from alternating addresses.
2. Trace each relevant bank/record writer and its outer job context, distinguishing
   work covered by the component critical section from later asynchronous writes.
3. Only after lifetime and writer coverage are established, place a bounded
   in-process copy in that proven scope and compare it with the passive reader.
   A blocking lock call on an arbitrary worker is not yet a justified capture API.

### Lock construction and destruction belong to the component lifetime

The SkeletonComponent constructor passes `component + 0x210` to the lock-wrapper
initializer. That wrapper stores `wrapper + 8` in its first pointer-sized field,
then initializes the storage at that address. For the normal constructor path,
the critical section is therefore inline at component `0x218`, behind a wrapper
at `0x210`. This is more specific than the earlier observation that the wrappers
dereference a pointer; it does not prove that all copied or reused objects followed
this constructor successfully.

The component teardown passes `component + 0x210` to the destruction wrapper. It
loads the stored pointer and tail-transfers to the external deletion routine.
The copied component-field region previously inspected starts after this wrapper;
it does not establish lock sharing between component copies.

Live target resolution in the same existing Wine session identified:

| Wrapper | Exact destination | Live instruction spans |
| --- | --- | --- |
| Initialize | `kernel32.dll!InitializeCriticalSectionEx` | 82 |
| Destroy | `ntdll.dll!RtlDeleteCriticalSection` | 29 |

Both encoded slots and module headers passed rechecks. No target API was called
by the probe. [The lifecycle receipt](../../native/snow_host/skeleton_lock_lifecycle_validation.json)
contains the address-free live result and 128 synthetic wrapper cases.

```python
def initialize_wrapper(wrapper):
    wrapper.pointer = address_of(wrapper) + 8
    InitializeCriticalSectionEx(wrapper.pointer, 4096, 0x02000000)
    # The native wrapper does not inspect the API return value.
    return wrapper

def destroy_wrapper(wrapper):
    return RtlDeleteCriticalSection(wrapper.pointer)  # native tail transfer
```

Sixty-four synthetic initialization cases execute the complete protected transfer,
then simulate different API return values and execute the original return path.
The wrapper always returns its own address and retains the inline pointer,
including with a simulated zero result. Sixty-four deletion cases verify the
stored-pointer argument, preserved caller stack and tested callee-saved registers
at the API boundary. The wrapper pointer has not been cleared before that transfer.
The external APIs and full component construction/destruction are not emulated.
The numeric initialization flag is retained as an observed value without assigning
an unverified semantic name.

This places the synchronization object's storage inside the component's allocation
and its deletion on the component teardown path. It does not supply ownership.
A non-null wrapper pointer or expected `component + 0x218` relationship cannot prove
successful initialization, exclude concurrent teardown or prevent address reuse.
An in-process snapshot needs retained component lifetime as well as the correct
lock and writer coverage. The earlier passive identity guards remain useful for
rejecting changes, but they are not a replacement for that retention mechanism.

### Channel handles resolve through thread context without retaining

`reference.animation_handle.resolve_channel_handle` reconstructs the complete
channel-handle resolver. The handle points to a control record containing a raw
object pointer at `0`, a counter at `8`, and a status word at `0xc`. The channel
handle itself stores its key at `8`, cached uint16 index at `0xc` and cached uint16
generation at `0xe`. These are distinct layouts despite overlapping offsets.

The resolver calls a native thread-local getter. That getter reads the process TLS
index, loads the thread's block from `GS:[0x58]`, and returns its eight-byte field
at `0x48`. The resolver uses this value as a bit mask:

```python
mask = 0xffffffffffffffff if control.status & 0x80000000 else thread_mask
component = control.raw_pointer & mask
if component != 0 and handle.generation != component.generation:
    handle.index = lookup(component.channel_table, handle.key)  # missing -> 0xffff
    handle.generation = component.generation
return component
```

Null resolution preserves the cache. Equal generation preserves even a cached
missing index; the resolver does not force a fresh lookup just because the index
is `0xffff`. A non-null resolved value is returned without a reference increment,
component lock or lifetime pin. Two explicit zero/all-ones writers are now identified below; the complete runtime
range and thread-role mapping remain unresolved. Arbitrary masks are supported by the inspection
model to express the actual bitwise operation, not to claim they occur in play.

[256 original-instruction cases](../../native/snow_host/channel_handle_validation.json)
execute the full resolver, native TLS getter and original sorted channel lookup.
No calls are intercepted. Synthetic cases cover both status-sign branches,
null/non-null pointer outcomes, matching/mismatched generations, missing tables,
missing keys and duplicate-key lookup. The control record is unchanged in every
case. Published pointers and masks are normalized to logical values for replay;
no game memory or process address is included. Six public tests replay the receipt
and check partial-mask arithmetic and cache boundaries.

A separately inspected bind/rebind routine obtains the component's control record
through component `0xa8`, increments its counter at `+8`, exchanges the handle's
control pointer, and decrements the old record's `+8` counter. If the old count was
one and its status word's low 24 bits are zero, it invokes a pool cleanup service.
Null binding releases the old counter and installs a sentinel with key `0xffffffff`,
index `0xffff` and generation zero. This establishes reference bookkeeping for the
control record, but does not yet establish which count retains the component
allocation or how concurrent destruction is excluded. The pool cleanup and other
status/count users must be traced before labeling these strong or weak handles.

The immediate API consequence is that a native channel handle is neither a passive
raw pointer nor a demonstrated retained component. Resolution also depends on the
calling thread's initialized context. An arbitrary injected worker cannot assume
it sees the same pointer as an engine animation worker. The next retention study
should follow the control-record lifecycle and the thread-context setup together;
the critical section alone does not answer either question.


## Handle visibility is deliberately scoped by thread context

Static inspection now identifies writers for the same TLS field consumed by the
channel-handle resolver. One loop's setup sets the 64-bit mask to all ones and a
separate TLS uint32 at offset `0x68` to one. The loop's exact thread role remains
unresolved. Another routine saves the mask and a context uint32 at offset `0x64`,
zeros both, performs work, and restores both on its ordinary return paths.

The recovered scope can be expressed without process addresses:

```python
saved_mask = thread.handle_mask
thread.handle_mask = 0
saved_context = thread.context_64
thread.context_64 = 0

lock(owner.list_lock)
work_items = collect_registered_items(owner)
unlock(owner.list_lock)
process_work_items(work_items)
lock(owner.list_lock)
process_selected_items_still_registered(owner, work_items)
unlock(owner.list_lock)
release_temporary_storage_if_owned(work_items)

thread.handle_mask = saved_mask
thread.context_64 = saved_context
return early_exit_requested
```

This is a control-flow outline, not a decoded implementation of the work services
or a guarantee about exception cleanup. Nonempty processing invokes object
callbacks; their effects and the work service remain outside this validation.
Both ordinary false and early-true return branches join the same restore block.
The native code saves/restores the prior value rather than unconditionally
restoring all ones. Nested scope behavior is therefore compatible with an outer
zero mask, although nested live execution has not been observed.

Combining this with the verified resolver yields a useful exact distinction:
when this mask is zero, a record with status bit 31 clear resolves to null even if
its raw pointer is nonzero. A record with status bit 31 set bypasses the mask and
can still resolve. This is conditional visibility, not proof that the hidden
object was freed. Neither a nonzero result nor changing TLS establishes retention
or authorization to use a component from an arbitrary mod thread.

[Validation receipt](../../native/snow_host/handle_thread_scope_validation.json):
128 original-instruction executions of the complete empty-list path preserve
arbitrary prior 64-bit masks and 32-bit contexts. The two lock/unlock pairs and
work service are intercepted; each observes zero mask and context. The native
TLS getter and setter execute unchanged. Three additional setup slices verify
the all-ones mask and `0x68 = 1` write. No live TLS mutation, actual lock call,
nonempty callback, exception path or safe pose snapshot is claimed.

Next capture boundary work: identify the callers and thread roles of these
scopes, join the skeleton writer to its job completion, and establish component
retention. Writing all ones into a mod thread would skip these unresolved
requirements and is not exposed as an API.


## Ragdoll jobs are additional skeleton pose writers

The previously unidentified skeleton batch has a concrete registration name:
`Anim::SkeletonUpdateForRagdoll`, with the second label
`SkeletonUpdateForRagdollInteractions`. Original setup constructs a callback
wrapper holding this batch function and passes it to the callback assignment
helper. A separate range callback labeled `RagdollAfterCamera` obtains its owner's
skeleton and invokes the locked prepare/update/finalize wrapper when component
byte `0xc9` is nonzero. That invocation occurs before its later `0x416` gate.
These names identify registrations; they do not establish runtime scheduling
order relative to the camera or prove that a particular player participates.

The ragdoll batch first builds a list from supplied entities. It skips an entity
with no world pointer, no resolved skeleton, or skeleton byte `0xc81` bit 2 clear.
For each selected skeleton, if byte `0xc82` bit 2 is clear it calls a preparation
service before the second pass. That service has not been decoded here. The
second pass is:

```python
for skeleton in selected:
    if not skeleton.primary_bank:
        continue
    lock(skeleton.lock)
    prepare_and_rotate(skeleton)
    update_skeleton(skeleton)
    if skeleton.primary_bank:  # rechecked after calls
        skeleton.state_c82 &= 0xfd
        skeleton.state_c80 &= 0x7f
        if skeleton.count_28a > 0:
            skeleton.state_c81 |= 1
        if skeleton.flags_e8 & 0x2000:
            supplemental_update(skeleton)
        flags = skeleton.flags_e8  # reload after supplemental call
        skeleton.flags_e8 = (flags & ~7) | ((flags >> 3) & 7)
        skeleton.state_c80 |= 4
    unlock(skeleton.lock)
```

The operation names above describe call boundaries, not fully reconstructed
animation evaluation. In particular `prepare_and_rotate` is the previously
traced writer of current/previous pose-bank selection. This establishes a route
from a named ragdoll job to that writer. A bank disappearing during the update
skips subsequent flag writes but still unlocks. The initial primary-bank test is
outside the lock; this wrapper alone does not establish component lifetime.

[Validation receipt](../../native/snow_host/ragdoll_pose_stage_validation.json):
256 original-instruction single-iteration cases cover absent primary banks,
primary removal by the update stub, zero/nonzero counts, and varied flag bytes.
They verify call ordering and resulting flags. All five effect services, including
synchronization and evaluation, are stubbed. Two original callback-setup slices
verify that the registered callback is this batch function. They stop at callback
assignment, without executing its copying helper or scheduler dispatch. The
initial entity collection and the `RagdollAfterCamera` route are static findings,
not part of that emulation receipt.

This changes the capture plan. The animation-time job's completion alone cannot
be assumed to cover these other writers. Before exposing `get_pose_snapshot`,
join the ragdoll job's incoming/outgoing dependencies and runtime membership,
then choose a retained component scope in which all relevant writers are excluded.
The two-pass batch and post-camera route are specific next tracing targets, not
proof that an end-of-frame snapshot is already safe.

The TLS-zero scope's sole direct-call candidate was also confirmed in an owner
routine that scans four queue records. It invokes that scope after finding the
second queue empty, temporarily releasing its outer lock and reacquiring it after
the scope returns. This connects the scope to queue processing but does not yet
identify its OS thread or connect it to the ragdoll jobs. The all-ones initializer
has a table reference; a complete thread-entry chain remains open.


### Ragdoll dependency join recovered

The [ragdoll dependency reconstruction](RAGDOLL_STAGE_DEPENDENCIES.md) now connects
end-animation to both skeleton-update branches and reconverges them at
PhysicForRagdollUpdate. The interaction branch is a range job with a callable
visitor, not a once-per-job callback. Four registrations matched original setup
instructions at two synthetic owner bases. A runnable scheduler probe holds the
join while either branch has claimed all work but has not finalized. The separate
post-camera route and component lifetime still prevent claiming a safe snapshot.

### Referenced records can lose their object pointer

Channel-handle binding increments the control record's `+8` counter; replacing
that binding decrements the old record's counter. That operation does not establish
that the skeleton itself remains alive. Static tracing of the skeleton cleanup
virtual method reaches indexed-record invalidation, with a global mode selecting
a locked or lock-free helper. Neither helper gates invalidation on that counter.

The complete lock-free helper has the following serial behavior:

```python
encoded = lookup_object.flags & 0x7ffff
if encoded == 0:
    return
index = encoded - 1
record = pages[index >> 14].records[index & 0x3fff]
target = record.object_pointer
if target is not None:
    atomic_and(target.flags, 0xfff80000)
    record.object_pointer = None
    atomic_and(record.status, 0x7fffffff)
    atomic_and(target.flags, 0xfff80000)  # repeated by the implementation
# record.count_at_8 is untouched; status low 24 bits are also preserved
```

The lookup object and pointer target are separate inputs: this helper does not
check their identity. A nonzero record reference count therefore cannot by itself
serve as our component-retention proof. The producer connection is now established for the existing-index path below.
Cleanup call-chain inspection does not establish which live scheduler scope
excludes destruction.

The [portable model](../../reference/animation_handle.py) and
[validation receipt](../../native/snow_host/control_record_invalidation_validation.json)
cover 320 original-instruction cases: page boundaries, absent indices, null targets,
varied flags/status, and counters including positive values. The complete helper
ran against synthetic records without intercepted calls. This verifies serial
invalidation, not concurrent CAS retries, the entire destruction path, or a safe
live retain API. A pose API still needs a verified owner scope or exclusion
mechanism; retaining the channel record alone is insufficient evidence.

### Skeleton cached record joins the cleanup registry

The skeleton setup/rebuild path obtains a record using the skeleton object as
its lookup input, then exchanges it into the cached handle field. The supplied
pool's page-array member is the same global page array read by indexed
invalidation. This closes the cached-record-to-registry connection for an
already indexed object whose record points back to it.

```python
# Existing-index path, inside the record lookup wrapper:
lock(pool)
index = (skeleton.flags & 0x7ffff) - 1
record = pool.pages[index >> 14].records[index & 0x3fff]
# Native lookup has additional absent-index and mismatched-target branches.
assert record.object_pointer == skeleton  # tested case, not a native assertion
atomic_increment(record.count_at_8)        # temporary returned reference
unlock(pool)

atomic_increment(record.count_at_8)        # cached reference
old = atomic_exchange(skeleton.cached_record, record)
if atomic_decrement_return_old(old.count_at_8) == 1:
    if (old.status & 0xffffff) == 0:
        record_reclaim_service(old)
if atomic_decrement_return_old(record.count_at_8) == 1:
    if (record.status & 0xffffff) == 0:
        record_reclaim_service(record)    # release returned temporary
```

When old and new records differ, the new record gains one net reference and the
old record loses one. When they are identical, the count is unchanged. This
identity case matters when rebuilding a skeleton that already has a cached record.
The subsequent invalidation helper can still clear that record's object pointer
and the object's index bits while leaving both its positive count and the
skeleton's cached-record field unchanged.

The [binding validation receipt](../../native/snow_host/skeleton_record_binding_validation.json)
contains 64 original-instruction cases covering both identity cases, page
boundaries, positive counts and old-record reclaim dispatch. The assignment slice
executes the complete lookup wrapper and its existing-index branch, then executes
the complete invalidation helper. Pool locks and the reclaim service are
intercepted; profiling is disabled. Allocation of missing records, rebinding a
record with a different target, concurrency and the complete skeleton cleanup
remain outside this check.

For the mod API, a cached handle is a lookup route, not a lifetime lease. The next
useful ownership trace is the low-24-bit reference path and the queue that invokes
object cleanup. We still need to establish whether retaining there delays cleanup
and which scheduler/thread scope permits acquisition without a race. Incrementing
that field from a mod is not yet a verified operation.

### Retirement queue ownership gate

The queue consumer checks the low 24 bits of the popped record's status before
calling the object's cleanup virtual method. A nonzero value skips object cleanup,
disposal scheduling and record reclamation. It still removes the queue entry and
clears status bit 24. It does not requeue the item in this branch.

```python
record = queue.pop()                     # advances head modulo capacity
owned = (record.status & 0xffffff) != 0
object_to_dispose = record.object_pointer
if owned:
    atomic_and(record.status, 0xfeffffff) # clear queued bit
else:
    if object_to_dispose is not None:
        object_to_dispose.cleanup()
        if pool.mode == 0:
            schedule_object_disposal(object_to_dispose)
        else:
            disposal_list.append(object_to_dispose)
    atomic_and(record.status, 0xfeffffff)
    record_reclaim_service(record)
```

The local object pointer is captured before cleanup. Cleanup may invalidate the
record's pointer or alter its status. The later clear operation acts on the then
current status, preserving other changes. Record reclamation remains a separate
service with additional gates; reaching it does not mean the record was freed.
The record's `+8` count is not checked by this queue dispatch.

The [effect planner](../../reference/record_retirement.py) exposes this local
behavior without pretending to execute cleanup or acquire lifetime. Its output
names a status mask rather than predicting a final status across an opaque
callback. The [validation receipt](../../native/snow_host/retirement_queue_validation.json)
contains 144 original-instruction queue-loop cases covering zero/nonzero ownership,
null targets, three pool modes, ring-head wrap, record counts and callback status
changes. Cleanup, disposal scheduling and record reclamation were intercepted.
The outer locking, allocation and destructor paths were not executed.

Static tracing of the retirement-request routine supplies the complementary lead:
it rejects nonzero low-24 counts and status bit 26, sets bit 24 before enqueueing,
and avoids duplicate enqueue when bit 24 is already set. Other flags and a global
mode can instead route it directly to record reclamation. This request routine has
not yet received the same original-instruction validation as the consumer loop.

These observations support a specific next experiment: trace the existing
low-24-bit acquisition and release operations, their locks and the caller's object
ownership. The queue recheck can defer cleanup after a count becomes nonzero,
but it does not establish race-free acquisition from an arbitrary raw pointer.
No live retain/release operation is exposed by this planner.

### Ownership acquisition shares the cleanup pool lock

A sibling of the cached-handle lookup wrapper increments status `+12` rather
than the record-only count at `+8`. For a nonnull object or identifier, it takes
`pool.lock`, calls the same registry lookup helper, increments the returned
record's status word, and releases the lock. The cleanup queue also holds that
pool lock across its ownership test and cleanup dispatch.

```python
# Tested path: valid, already indexed object, matching record target.
lock(pool.lock)
record = lookup_record(pool, identifier=0, object=known_live_object)
atomic_increment_u32(record.status)
unlock(pool.lock)
return record
```

The [96-case validation](../../native/snow_host/ownership_acquisition_validation.json)
executes the complete original acquisition wrapper and existing-index lookup
branch. Lock-call arguments match `pool.lock`; observations at lock entry/exit
show that the status increment precedes unlock. Each case then executes the
original cleanup queue loop. For nonsaturated counts, its new nonzero ownership
causes cleanup to be skipped. The record-only count remains unchanged. Lock
implementations and cleanup/disposal/reclaim services are intercepted, so this is
serial original-instruction validation, not a concurrent lock stress test.

The increment operates on the entire unsigned 32-bit status word. It does not
mask, saturate or reject an ownership count of `0xffffff`. At that boundary the
low count becomes zero and carry changes the upper flags; `0xffffffff` wraps to
zero. The queue subsequently takes its zero-count branch in those synthetic
boundary cases. The [arithmetic model](../../reference/record_retirement.py)
preserves this behavior and labels overflow explicitly. This is a boundary
observation, not evidence that normal gameplay reaches count saturation.

This is a stronger lifetime lead than merely retaining a channel record. The
shared lock orders a valid acquisition against queued cleanup. It does not make
an arbitrary raw object pointer safe: lookup dereferences the object's flags
inside the lock, and the object may already have died before that lock is taken.
The helper can also allocate missing records or rebind mismatched targets, paths
not exercised here. Existing animation-side callers use this ownership wrapper,
but their full caller preconditions remain to be traced.

The next candidate API path is acquisition by an existing retained record or a
stable identifier, checking the target while holding the pool lock. That is a
proposal, not an implemented live API. Trace the identifier resolver, release-to-
retirement pairing and thread restrictions before exposing a lifetime lease.

### Identifier lookup and null overlay entries

The identifier resolver provides a route that does not require the caller to
supply an object pointer. With a nonzero identifier and its global enable gate
set, it searches an ordered overlay, then the record map, then a fallback map.
The overlay's behavior is unusual and must be preserved:

```python
if identifier == 0 or not resolver_enabled:
    return None
lock(resolver_lock)
# This helper takes resolver_lock again.
entry = first(overlay, lambda e: e.object is None or e.identifier == identifier)
if entry exists:
    result = entry.object  # a null result here suppresses both fallback searches
else:
    # This helper takes the pool lock and reads the found record's object pointer.
    result = record_map_object(identifier)
    if result is None:
        result = fallback_map_object(identifier)
unlock(resolver_lock)
return result
```

The overlay helper actually matches either an object argument or an identifier;
this caller supplies zero as the object argument. Consequently an earlier null
object entry wins even if its identifier differs from the requested identifier.
Do not rewrite this as a dictionary lookup or silently skip null entries. The
producer and intended meaning of these overlay entries remain open.

The [portable resolver](../../reference/object_identifier.py) accepts logical
identifiers and supplied overlay/map results. It has no process access and does
not retain the selected object. The [128-case receipt](../../native/snow_host/object_identifier_validation.json)
executes the complete original resolver, overlay search and record-map helper.
Lock calls and hash-table searches are intercepted. Cases cover disabled/zero-ID
requests, ordered duplicate/mismatched/null overlay entries, map fallbacks and
nested lock-call ordering. It does not validate identifier reuse, hash-table
implementation, ownership acquisition or concurrency.

Lock nesting is material. The resolver and overlay helper request the same lock;
the record-map helper additionally requests the pool lock. The ownership wrapper
already holds the pool lock when it calls this resolver. A replacement using
ordinary nonrecursive locks would not preserve that call structure. The tests
verify requested lock identities/order, not lock implementation or deadlock freedom.

A failed object lookup is also not necessarily a failed ownership lookup. Static
inspection of the outer registry helper shows that a null resolved object can
still lead to an existing identifier record, or to record allocation. The ownership
wrapper increments the returned record even if it has no object target. Treat an
owned record and a usable object as separate results. Those missing-object
allocation/reuse paths still need direct validation before exposing a live lease.

### Null-target ownership still needs release

An identifier acquisition can succeed at the record level while returning no
usable object. This is now checked through the original wrapper and lookup, with
the object-resolver enable gate off and an existing identifier-map record whose
object pointer is null. The wrapper still increments the status ownership count
and returns that record.

The paired release operation is a whole-word atomic decrement. It requests
retirement when the resulting low 24 bits are zero:

```python
old_status = atomic_fetch_add_u32(record.status, 0xffffffff)
new_status = (old_status - 1) & 0xffffffff
if (new_status & 0xffffff) == 0:
    request_retirement(pool, record)
```

Requesting retirement does not mean that the record was reclaimed. In the tested
null-target path, the request first rejects status bit 26 or a nonzero ownership
count. Otherwise it reaches the record-reclaim service. That service separately
rejects status bit 24, status bit 26, a nonzero record-only `+8` count, or nonzero
ownership. The tests keep the record-only count positive, so the empty record
survives the ownership acquire/release pair.

The [40-case receipt](../../native/snow_host/missing_object_lease_validation.json)
executes the complete acquisition wrapper and existing identifier lookup, followed
by an original single-field release slice. Its retirement-request routine and
record-reclaim gate execute directly, not as stubs. Pool lock and hash-table
lookup calls are intercepted. Cases vary status flags, ownership counts including
wrap boundaries, and positive record-only counts. No allocation, actual record
recycling, concurrent access or complete holder destructor is exercised.

The [release arithmetic model](../../reference/record_retirement.py) preserves
whole-word wrap and reports underflow. It does not perform retirement side effects.
Decrementing a zero low count borrows from upper flags and produces `0xffffff`,
which does not request retirement. This is another reason a public wrapper must
track whether it acquired an ownership reference and release exactly that
reference rather than infer ownership from a nonnull object pointer.

A future live API should represent at least two separate outcomes: a returned
owned record and whether that record currently resolves to an object. Its failure
path must release an acquired record even when object validation fails. This is
an API design consequence of the checked sequence, not a completed live lease
implementation. Missing identifier allocation, generation/reuse checks and the
thread scope for acquisition and release remain unresolved.

### Record slot reuse and identity

A fully released null-target record can return to its page's free list and be
reused at the same address for a different identifier. Reclamation first checks
status bits 26 and 24, the record-only count and low-24 ownership. With all gates
clear, it sets bit 26. For a nonzero identifier, it links the slot into the free
list by overwriting the record-only count field with the previous free-list head.

```python
# Null-target path; counts are already zero and reclamation gates passed.
record.status |= 1 << 26
if record.identifier != 0:
    if not reserved_identifier(record.identifier) and not (record.status & (1 << 28)):
        erase_identifier_map_entry(record.identifier)
    record.count_or_free_link = page.free_head
    page.free_head = record.slot

# Later, allocation from a page that has a free slot:
slot = page.free_head
record = page.records[slot]
record.object_pointer = None
record.identifier = requested_identifier
next_free = record.count_or_free_link
record.count_or_free_link = 0
record.status = 0
page.free_head = next_free
# The ownership wrapper increments status after lookup/allocation returns.
```

The inspected reserved identifier interval is inclusive `0xf0000000` through
`0xf7ffffff`. Map erasure is also skipped when status bit 28 is set. The tested
null-target path leaves the identifier in the freed record until reuse overwrites
it. The free-list empty marker is the 32-bit value `0xffffffff`.

The [record-pool model](../../reference/control_record_pool.py) represents null-
target recycling and slot initialization. The [54-case receipt](../../native/snow_host/record_reuse_validation.json)
executes complete original reclamation and page search, then complete ownership
acquisition using an existing free page and a missing identifier-map entry.
The returned record is the exact slot just reclaimed, with the new identifier,
null target, record-only count zero and ownership count one. Cases cover page-slot
boundaries, free-list heads, ordinary/reserved identifier transitions and relevant
status flags. Locks, map lookup/erase/insert and map-context calls are intercepted.
Page growth, object rebinding and concurrent reuse are not tested.

No generation increment occurs in the 24-byte record during this sequence. This
does not prove that the engine has no generation or identifier uniqueness scheme
elsewhere. It does prove that a raw record address can refer to a different
logical identity after reclamation. A durable mod token must therefore retain a
record or revalidate identity through a proven registry route. The skeleton's
channel-table generation addresses a different cache concern; it is not evidence
of record-slot generation protection.

Missing-object record allocation is now exercised for an existing free page.
The live lease still needs a verified acquisition context and identity guard, plus
cleanup on every failed object validation. New-page allocation and identifier
producer/reuse rules remain separate open paths.

### Thread context controls record publication

The nonnull-target record-binding helper reads the thread-local context at `+0x64`.
It selects deferred publication exactly when that value is `3` and the global
pool mode is not `1`. This does not identify context `3` as a particular OS thread.

```python
if record.object_pointer == new_object:
    return
prepare_registry_mapping(record.identifier, new_object)  # separate service
new_object.flags = (new_object.flags & 0xfff80000) | (record_index + 1)
if thread.context_64 == 3 and global_pool_mode != 1:
    if record.object_pointer is None:
        record.object_pointer = new_object
        atomic_clear_bit(record.status, 31)
    publication_queue.append((record.identifier, new_object, record))
else:
    if record.object_pointer is None:
        record.object_pointer = new_object
        atomic_set_bit(record.status, 31)
```

If a record already targets a different object, this helper does not overwrite
that pointer in the tested local path. The deferred branch queues the new target;
the immediate branch leaves the prior target in place. Both still encode the
record index into the new object's flags after registry preparation. If the target
already matches, the routine returns before preparation, flag updates or queueing.
Do not replace these cases with unconditional pointer assignment.

Bit 31 connects this result to the previously recovered handle resolver. When
clear, resolution applies the caller's TLS visibility mask. When set, that mask is
bypassed. A nonnull stored pointer with bit 31 clear is not necessarily visible to
a reader whose mask is zero, and this is separate from ownership reference counts.

The [publication planner](../../reference/record_publication.py) models these local
changes with registry preparation left as an explicit opaque effect. The
[216-case receipt](../../native/snow_host/record_publication_validation.json)
executes the complete nonnull-target helper, actual TLS context getter, actual
record-index calculation and original ring-queue append. Registry preparation is
intercepted without changing supplied state. Cases cover empty/matching/different
targets, context and pool-mode branches, flag preservation, page-slot boundaries
and ring write-index wrap. Queue growth, the queued consumer, original preparation
side effects, concurrency and OS thread identity are not validated.

The successful append writes three machine words: identifier, new object, record.
It advances the ring write index modulo capacity, increments the item count, and
atomically increments a separate submission counter. The sufficient-capacity path
contains no additional lock call. Its required caller synchronization remains open.
This queue is now the direct next tracing target for publication completion and
permitted mod-callback context. Changing a thread's TLS context to force a branch
is not a supported acquisition strategy.

### Ready-publication drain and identifier guard

The publication drain takes the pool lock and exchanges its ready count at `+0x50`
with zero. It pops exactly that many items from the ring. A queued item becomes
visible only if its identifier still equals the record's current identifier:

```python
lock(pool.lock)
remaining = atomic_exchange(pool.ready_count, 0)
while remaining != 0:
    identifier, queued_object, record = publication_queue.pop()
    if record.identifier == identifier:
        atomic_set_bit(record.status, 31)
        current_object = record.object_pointer
        if current_object is not None:
            notify_object(current_object)
    remaining -= 1
unlock(pool.lock)
```

The queued object is not installed by this consumer. Notification uses the
record's current object, which can differ from the queued object. Identifier
mismatch discards the item without setting visibility or notifying. The guard
compares only identifiers here; it does not establish protection against identifier
reuse or prove that a queued record pointer remains valid until dequeue.

The [completion model](../../reference/record_publication.py) and
[64-case drain receipt](../../native/snow_host/publication_completion_validation.json)
cover matching/mismatched identifiers, null/current objects, varied status flags,
ring wrap and a zero ready count with a nonempty queue. Original full drain
instructions execute, with pool locks and object notification intercepted. The
queued pointer deliberately differs from the current pointer. Visibility is set
before notification; ready count becomes zero while submitted count is untouched.

A separate original routine contains the submitted-to-ready handoff:

```python
batch = atomic_exchange(pool.submitted_count, 0)
if batch != 0:
    atomic_add_u32(pool.ready_count, batch)
```

Twelve additional instruction-slice cases validate that arithmetic, including
uint32 wrap. The slice receives an explicitly zero exchange-source register;
a traced enclosing path clears that register before reaching the handoff, but the
complete preceding work and all enclosing paths were not emulated. The handoff
sits between two work-service calls. Their detailed relation to the queued object
updates remains open, so this is not yet a proven frame or mod-callback boundary.

A static outer drain calls visibility completion before the retirement queue while
holding the pool lock. This gives a specific ordering lead: make ready records
visible, then consider queued cleanup. Its complete live execution, notification
side effects and synchronization with readers still require validation.

The original completion loop relies on a ready-count/queue-count invariant. The
tests keep ready count within queued entries; they do not claim graceful handling
of an inconsistent counter or a stale queued record. Do not invoke this drain from
a mod simply because its local behavior is understood.

### Callback phases around publication readiness

The service called on either side of the submitted-to-ready transfer is a
category-filtered callback dispatcher. The enclosing caller supplies skip mask
`2` before the transfer and skip mask `1` after it. These are exclusion masks:

| Category flags, low two bits | Before transfer, mask 2 | After transfer, mask 1 |
| --- | --- | --- |
| 0 | Invoked | Invoked |
| 1 | Invoked | Skipped |
| 2 | Skipped | Invoked |
| 3 | Skipped | Skipped |

Within each included category, the dispatcher visits entries in reverse array
order. Null receiver entries are skipped. Each remaining entry receives its stored
32-bit tag and a pointer to a context slot containing the current category
descriptor. The primary callback runs first, followed by the optional secondary
callback for the same receiver/tag/context slot.

```python
registry.count_word |= 0x80000000
for category in registry.categories_in_order:
    context_slot.value = category.descriptor
    if category.descriptor.flags & skip_mask:
        continue
    for entry in reversed(category.entries):
        if entry.receiver is not None:
            entry.primary(entry.receiver, entry.tag, context_slot)
            if entry.secondary is not None:
                entry.secondary(entry.receiver, entry.tag, context_slot)
```

The routine leaves the count word's high bit set on normal return; the meaning
and reset owner of that bit remain open. The pseudocode above assumes a fixed
registry. The native loop reads the category count during traversal, so callbacks
that mutate registration need separate study. The dispatcher also allocates or
selects scratch storage; no semantic role for that scratch is claimed here.

The [callback planner](../../reference/publication_callbacks.py) and
[256-case receipt](../../native/snow_host/publication_callbacks_validation.json)
validate the complete original dispatcher with zero to three synthetic categories,
mask values 1 and 2, varied category flags, null receivers, reverse entry order and
optional secondary callbacks. The capacity helper is intercepted for an already
selected inline scratch buffer, and callbacks record their arguments without
side effects. Heap growth, callback effects, registry mutation and concurrency are
outside this receipt. The before/after call-site ordering is static evidence,
not a complete emulation of the enclosing routine.

This narrows what the handoff means. It separates two callback passes with
different category exclusions; it is not simply a wait for all engine jobs or a
frame boundary. Categories with neither low flag bit run on both sides. To expose
a mod callback here, identify the relevant category descriptor and registration
site, then verify its receiver lifetime and execution thread. Publication queue
retention and the concrete callbacks that install or replace targets remain open.

### Concrete animation-side registration routes

Three concrete call-site slices now connect resource-reader code to the callback
registry used by the two passes. Their published route labels below are inspection
labels, not recovered engine names or proof that their receivers are player skeletons.

| Inspection route | Registered entry | Category flags | Dispatch phase |
| --- | --- | --- | --- |
| animation_resource_a | Receiver, primary callback, tag 0 | 1 | Before readiness handoff |
| animation_resource_b | Receiver, primary and secondary callbacks, tag 0 | 1 | Before readiness handoff |
| custom_resource_c | Receiver, primary callback, tag 0 | 1 | Before readiness handoff |

The resource-reader adapter follows `reader.owner` to its callback registry and
passes the receiver, callbacks and category descriptor to registration. The
registration helper reads the descriptor's runtime category index. If that index
is `-1`, it does not append an entry. Otherwise it selects the category's entry
array and writes the receiver, primary callback, optional secondary callback and
32-bit tag. An optional argument suppresses registration when the last entry has
the same receiver; it does not compare callback pointers in that test. These
particular reader-adapter routes supply tag zero.

The [three-route receipt](../../native/snow_host/animation_registration_validation.json)
executes each original setup slice through the complete reader adapter and
registration helper, with an empty synthetic category list and initialized index.
The append/capacity service is intercepted; the original callback pointer values
are checked privately and omitted from the public receipt. The descriptor flags
are 1 in the inspected image, connecting these entries to the previously validated
before-only phase selection. Category bootstrap, resource reads, callback bodies,
receiver ownership and live thread identity are not executed by this check.

Static inspection offers concrete next leads. Route A's primary callback forwards
to a routine that tests a count, takes an object-local lock and prepares a cached
array. Route B's secondary callback tests a nonzero field and an absent service
pointer before obtaining a service and storing its result. Their precise resource
types and downstream side effects remain unresolved. Neither observation establishes
that these are per-frame skeleton pose updates.

The surrounding readers advance a stream cursor and resolve referenced data.
Together with the registration routes, that supports interpreting this dispatcher
as resource/object finalization infrastructure. It does not establish a universal
frame callback or a safe live mod registration point. The most useful next step is
to identify these receiver types and the concrete callback effects, then link the
finalization owner to its worker/thread setup. The already recovered per-frame
ragdoll/skeleton job graph remains a separate scheduling path.

### Animation resource raw-pointer cache

The primary callback on `animation_resource_a` is now decoded beyond registration.
It forwards directly to a handle-to-pointer cache builder. The receiver has a source
array of record pointers and a separate raw-pointer cache. Both counts are uint16.

```python
if receiver.cached_count != 0:
    return
lock(receiver.cache_lock)
reserve_pointer_array(receiver.cache, receiver.source_count)
receiver.cached_count = receiver.source_count
for index, record in enumerate(receiver.source_records):
    mask = current_thread.visibility_mask
    if record.status & 0x80000000:
        mask = UINT64_MAX
    receiver.cache[index] = record.object_pointer & mask
unlock(receiver.cache_lock)
```

The native routine reads the TLS mask separately for each entry. A nonzero cache
count suppresses all later work, including locking, regardless of whether its
entries are null. It does not filter out null entries, retry hidden records or
increment either reference count. A zero-length source leaves cached count zero,
so a later invocation repeats the reserve/lock path.

This makes finalization context consequential: if a nonempty source is first
resolved with a zero visibility mask and its records lack bit 31, the resulting
null entries remain cached on a later call with a fully visible mask. The observed
routine has no refresh path for that case. This does not prove an in-game bug;
the engine may ensure correct initialization context or reset the count elsewhere.

The [portable cache builder](../../reference/object_pointer_cache.py) and
[96-case receipt](../../native/snow_host/pointer_cache_validation.json) execute the
original registered thunk, complete cache builder and actual TLS getter. Each
case calls the routine twice with different visibility masks. Cases cover empty
and nonempty sources, preexisting caches including null entries, status-bit override
and partial masks. Lock and capacity services are intercepted. Original record
pointer/count/status fields remain unchanged. The public pointers are synthetic.
No real allocation, concurrent initialization or object lifetime is validated.

The count gate is outside the lock, with no second count check after locking.
The routine also stores the cache count before filling entries. These facts limit
what can be inferred from the lock alone: a nonzero count is not proof of an atomic
snapshot for an unsynchronized reader. We still need the receiver's owner and
consumer protocol before using this cache as a pose or skeleton API source.
The exact resource type, count-reset paths and object lifetime owner remain open.

### Cache receiver identified as ActionKit

Type metadata identifies `animation_resource_a` as **ActionKit**. Its constructor,
finalizer, `0xa8` object size and vtable reader/type getter all agree with the
inspected pointer-cache layout. Thirty-two original-constructor cases validate
initial empty array descriptors, with lock initialization intercepted.

See the [ActionKit cache guide](ACTION_KIT_CACHE.md) for the layout, identity receipt
and lifetime/reset limits. This resolves the receiver type while separating this
resource cache from the player skeleton's pose storage. Constructor initialization
is confirmed; an in-place cache reset and complete source-handle ownership remain
open.

## Linked-skeleton pruning and unregister scope

The post-update linked helper holds the parent's linked-list spinlock across
traversal, child service calls and optional unregister. This is distinct from
the parent pose-bank critical section. The list uses 48-byte entries and a
uint16 count. Each entry resolves its holder using status bit 31 and the holder
pointer; this particular resolution has no additional TLS visibility mask.

For an unresolved entry, the helper assigns the last entry into the current
slot unless it is already last, destroys the last slot, decrements the count,
and revisits the current slot. Order is therefore unstable. A resolved entity
without a world, or with no skeleton, stays in the list but receives no child
update. An eligible child requires a primary pose bank as well.

After traversal, if the list is empty, parent pending bit 6 is set and the
parent owner's world exists, the helper calls the world registration service
with category 14 and then clears pending bit 6. It releases the list spinlock
only after this service returns. A missing owner world leaves the bit set.
The registration service's internal effects remain opaque.

```python
lock(linked_list)
i = 0
while i != count:
    child = resolve(entries[i])
    if child is None:
        if i + 1 != count:
            assign(entries[i], entries[count - 1])
        destroy(entries[count - 1])
        count -= 1
        continue
    if child.world and (skeleton := find_skeleton(child)):
        if skeleton.primary_bank:
            update_eligible_child(skeleton)  # opaque here; separate lock scope
    i += 1
if count == 0 and parent.pending & 64 and parent.owner.world:
    unregister(parent.owner.world, parent, category=14)
    parent.pending &= ~64
unlock(linked_list)
```

The executable [pruning model](../../reference/skeleton_links.py) explicitly
accepts only unresolved, worldless and no-skeleton outcomes. It rejects eligible
children rather than inventing their updates. The [validation receipt](../../native/snow_host/skeleton_links_validation.json)
contains 484 synthetic cases executed through the full original helper with
zero to four entries. The uncontended spinlock, list traversal, count mutation,
unregister predicate and final unlock execute as original instructions. Record
assignment is supplied as a 48-byte copy; destructor and registration calls are
intercepted, and lookup returns null. Reference-count side effects, concurrent
mutation, eligible-child evaluation and object lifetime are not established.
Every intercepted service observes the list lock held; every return observes
it released. This is offline evidence, not an additional live test.

For a pose API, the consequence is that list indexes cannot serve as persistent
child identities. Reading after post-update also does not retain a child or
protect its bank from another worker. A snapshot needs a verified retention and
synchronization contract beyond this traversal model.

## Eligible linked-child update order

After resolution and lookup, a child without a primary bank receives no update.
For a child with a bank, link mode 2 writes float32 -1 to the child's stored
scalar; other modes call the child preparation helper. The scalar's semantic
meaning is not established here.

If the parent's uint16 flags intersect `0x38` and parent control bit 0 is set,
the helper prepares scratch data, clears child control bit 3, and advances the
child using its entity's selected world time group. Entity flag bit 58 selects
the alternate group. The advance receives that group's float32 dt and companion
uint32 field; this pass verifies the argument routing, not the uint32's meaning.
The helper then sets child pending bit 0. Scratch storage is released if its
ownership bit says it is heap-backed and its pointer is nonnull.

Next, independently of the parent advance gate, child dirty bit 7 or pending
bit 0 causes child lock, forced refresh with secondary argument zero, and child
unlock. The parent's linked-list spinlock remains held throughout. The called
refresh also has its own lock acquisition as described above, so this is not a
single flat lock scope.

```python
if child.primary_bank:
    if link.mode == 2:
        child.stored_scalar = float32(-1)
    else:
        prepare_child(child)
    if parent.flags16 & 0x38 and parent.control & 1:
        scratch = prepare_link_scratch(parent, link, child)
        child.control &= ~8
        time = child.entity.world.time_group(child.entity.alternate_time)
        advance_child(child, time.dt, time.companion_u32, scratch)
        child.pending |= 1
        release_if_heap_owned(scratch)
    if child.dirty & 128 or child.pending & 1:
        lock(child.pose_lock)
        guarded_refresh(child, force=True, secondary=0)
        unlock(child.pose_lock)
```

[The executable branch planner](../../reference/skeleton_links.py) and
[768-case receipt](../../native/snow_host/eligible_child_validation.json) cover
both time groups, missing primary banks, link modes, parent gates, dirty and
pending combinations, and control-bit preservation. The full original linked
helper runs with a single resolved child and its uncontended parent spinlock.
Lookup, preparation, advance, child lock services and refresh are intercepted.
They are non-mutating in this fixture, and scratch remains inline. The fixture
checks both time arguments at advance, cleared child control bit 3 at that
point, refresh arguments, parent lock ownership at every intercepted call and
release at return. This establishes orchestration, not the services' internal
animation effects, heap-scratch destruction, concurrent behavior or lifetime.
The real refresh predicate reads state after the services, whose mutations can
therefore affect it. The planner explicitly excludes those mutations.

## Child preparation consumes deferred work

The child preparation helper has two stages. First, an ordered float32 comparison
checks the stored scalar against zero. For a nonnegative value, including negative
zero, it calls an evaluator with the scalar, selected bank and a context pointer,
then writes float32 -1 into the scalar field. Negative values and quiet NaNs skip
this stage in instruction emulation. This establishes a one-shot input, not its
units or an animation-rate interpretation. Hardware floating-point exception
policy is outside this check.

Second, it reads the work pointer and uint16 count after evaluation. No work or
zero count returns immediately. The component mask is `(flags16 >> 3) & 7`.
A zero mask tail-calls a clear helper that zeroes the work count and two uint32
counters. Otherwise, it takes the component pose lock, applies work to either
the primary or current bank according to the bank-selection byte, then calls
the corresponding bank-processing service with current bank, primary bank and
mask. It sets pending bit 0 before releasing the lock. The two processing
services remain distinct; this pass does not equate their mathematical effects.

```python
if ordered_nonnegative(child.stored_scalar):
    evaluate_work(child.work, child.stored_scalar,
                  child.primary if child.use_primary else child.current,
                  child.context)
    child.stored_scalar = float32(-1)
work = child.work  # reread after evaluator
if work and work.count:
    mask = (child.flags16 >> 3) & 7
    if mask == 0:
        work.count = work.counter_a = work.counter_b = 0
    else:
        lock(child.pose_lock)
        apply_work(work, child.primary if child.use_primary else child.current)
        process_selected_variant(child.current, child.primary, mask)
        child.pending |= 1
        unlock(child.pose_lock)
```

This supplies a missing mutation in the preceding eligible-child branch:
preparation may set pending even when the parent advance gate is false. The
subsequent refresh predicate reads that modified byte. Link mode 2 bypasses
preparation, so it also bypasses this source of pending work.

The [reference planner](../../reference/skeleton_preparation.py) takes the work
count **after** the opaque evaluator as an external input. The
[432-case receipt](../../native/snow_host/skeleton_preparation_validation.json)
executes the complete original preparation routine and clear-work leaf. Evaluation,
application, bank processing and lock services are intercepted without mutations.
It checks bank/context/mask arguments, scalar preservation/reset, pending before
unlock and both cleared counters. It includes absent/empty/nonempty work, both
bank selections, zero/nonzero masks, signed zero, a negative subnormal, infinities
and quiet NaNs. It does not establish full evaluation math or lock contention.

A static follow-up lead lies inside the evaluator: with existing work and no
saved request, it stores the scalar and context for later use. A later call with
zero scalar and null context can restore those saved inputs. That path is not
implemented or validated here; it may explain why a zero-input call still performs
work. It should be traced before treating zero as a universal no-op.

## Saved animation request arbitration

The evaluator prefix has one saved scalar/context slot. With an existing work
object, its branch order is:

```python
if work.count != 0:
    if work.saved_flag == 0:
        work.saved_flag = 1
        work.saved_scalar = incoming_scalar
        work.saved_context = incoming_context
        return DEFERRED
    work.count = 0
if work.saved_flag != 0 and ordered_equal(incoming_scalar, 0.0) and incoming_context is None:
    incoming_scalar = work.saved_scalar
    incoming_context = work.saved_context
    work.saved_flag = 0
    work.saved_scalar = float32(0)
    work.saved_context = None
continue_to_bank_selection_and_evaluation(incoming_scalar, incoming_context)
```

Both signed zeros consume a saved request when context is null. NaN, a nonzero
scalar, or a nonnull context does not consume it. When the saved slot is already
occupied, a new nonzero request clears the existing work count but leaves the
saved request intact and continues with its own inputs. This prefix neither
adds scalars nor overwrites that occupied slot. It is not a FIFO. Later evaluator
behavior remains outside this local claim.

A representative sequence is: existing work causes request A to be saved; a
nonzero request B clears the work count and continues with B while retaining A;
a later zero/null call consumes A and clears its saved fields. A second zero/null
call has no saved request to recover. This establishes request arbitration,
not how many animation frames any of those evaluations advance.

[The executable model](../../reference/animation_request.py) uses binary32 bits
and opaque context tokens. Its [504-case receipt](../../native/snow_host/animation_request_validation.json)
executes the original prefix with no service stubs, stopping at the deferred
return path or immediately before bank selection. Cases include zero and nonzero
work counts, zero/one/noncanonical nonzero saved flags, both signed zeros,
positive/negative inputs, infinity, quiet NaN, a subnormal, and null/non-null
contexts. Allocation when the work object is absent, later evaluation and
floating-point exception policy are excluded. The prefix stores raw context
values without a retain call in this span; that does not establish whether the
context is owned, borrowed, or protected by the caller. Do not expose a delayed
mod callback that assumes this slot retains its context.

## Evaluator context retention boundary

Past saved-request arbitration, the evaluator rejects negative scalar inputs
and values whose absolute magnitude is at most the stored float32 epsilon.
This gate precedes the ownership operations below. The branch inspection alone
does not establish the scalar's units. When evaluation proceeds, a nonnull
context supplies a reference holder from its context field; a null context
selects a global fallback holder.

The holder is installed into the work object with this sequence:

```python
atomic_increment(new_holder.references)
atomic_increment(new_holder.references)
old_holder = atomic_exchange(work.context_holder, new_holder)
release(old_holder)
release(new_holder)  # drops temporary acquisition

# Each release uses the pre-decrement count:
def release(holder):
    before = atomic_fetch_add(holder.references, -1)
    if before == 1 and (holder.status & 0xFFFFFF) == 0:
        retirement_service(holder)
```

For distinct holders and valid positive counts, the net effect is one retained
reference on the new holder and one released reference on the old. For the same
holder, the count returns to its starting value without retiring it. Retirement
is an opaque service; invoking it is not proof of immediate destruction. High
status bits alone do not suppress that call, whereas any low 24 status bits do.

[The executable arithmetic model](../../reference/animation_context.py) and
[90-case validation receipt](../../native/snow_host/animation_context_validation.json)
cover distinct/aliased holders, multiple positive starting counts and status
masks. The original atomic instructions run in a single emulator thread; only
the retirement service is intercepted. The check includes the installed holder
identity. This does not test competing acquisitions, retirement-service effects,
invalid starting references or refcount overflow.

This narrows the lifetime question without closing it. The deferred-request
prefix previously inspected stores a raw context value. The later evaluation
path retains a holder obtained from that context. No retention of the saved
raw context is established between those stages. Nor does retaining this holder
prove that a skeleton, primary bank, or pose buffer remains valid. A pose API
must identify the holder's payload and its owner/destructor relationships before
using this operation as a lifetime pin.

## Context-free animation work transforms

The retained context holder is resolved with status bit 31 and its target pointer.
A visible target supplies a transform through an indirect transform service or
an inline transform record. The evaluator converts that transform and uses it
in a separate context-relative output path. This establishes a coordinate-frame
role for the holder's target. It does not identify its full type or prove that
retaining it retains the skeleton, bank, or output allocation.

When the holder has no visible target, the evaluator gathers a uint16 selection
list from the chosen pose bank into a contiguous work buffer. Input records and
output records each contain two four-float vectors. Selection order is retained,
including duplicate indices. Bank flag bit 26 chooses direct copying; otherwise
the evaluator composes each record with the bank's parent transform.

The exact arithmetic matches the existing `provider_pose_transform` kernel.
For the composed path its XYZ result is:

```text
p_out.xyz = p_parent.xyz + 2 * (
    cross(q_parent.xyz, p.xyz) * q_parent.w
    + dot(q_parent.xyz, p.xyz) * q_parent.xyz
    + (q_parent.w*q_parent.w - 0.5) * p.xyz)
p_out.w = p_parent.w
q_out = q_parent * q_record
```

The implementation preserves the inspected float32 operation order. This path
neither normalizes quaternions nor multiplies position by an implicit scale.
The direct path copies all eight lanes. Do not transfer these omissions to the
visible-context path, which has additional scale/transform and normalization
instructions.

[The work gatherer](../../reference/animation_work.py) composes the existing
kernel with selection-list traversal. Its [256-case receipt](../../native/snow_host/animation_work_validation.json)
executes the complete original no-visible-target gather loop with no service
stubs. Every output byte matches for direct and composed records, including
non-unit quaternions, arbitrary fourth lanes, repeated/out-of-order selections,
and empty lists. Synthetic inputs use finite float32 values. The public adapter
adds bounds checks; the native loop trusts its indices. Work allocation,
concurrent mutation, visible-context conversion and safe buffer retention remain
outside this validation.

The holder retirement service was also followed statically. It rechecks status
and reference-count gates under a manager lock, can detach the target and clear
its indexed back-reference, and can recycle a holder slot. This supports keeping
holder lifetime separate from target validity. The retirement service was not
executed in this pass; its full allocator and target-lifecycle effects remain open.

## Context-present work transform kernel

After the target transform has been converted, the evaluator gathers the same
selected bank records but applies a second transform. Let `C` be that supplied
converted context, with `C.position.w` its scale. First perform the bank's
direct/composed transform described above. For the resulting record `(p, q)`:

```text
scaled_xyz = p.xyz * C.position.w
out.xyz = rotate(C.rotation, scaled_xyz) + C.position.xyz
out.w = C.position.w * p.w
raw_rotation = C.rotation * q
squares = raw_rotation * raw_rotation
n = (squares.x + squares.z) + (squares.y + squares.w)
r = RSQRT_estimate(n)
factor = (0.5 * r) * (3 - (r * n) * r)
out.rotation = raw_rotation * factor
```

Every operation follows the inspected float32 order. The context rotation formula
uses the same quaternion polynomial as the provider kernel. The bank composition
stage remains unnormalized; final normalization occurs after context composition.
In a composed bank, `p.w` comes from the bank parent, so the final fourth lane
is context scale times bank-parent fourth lane. In a direct bank it comes from
the selected record. This differs from the no-visible-context path, which does
not normalize output orientation or add this scale operation.

[The context work kernel](../../reference/animation_work.py) accepts the converted
context and reciprocal-square-root seed provider explicitly. The
[192-case receipt](../../native/snow_host/context_work_validation.json) executes
the original loop after context conversion with no service stubs. It covers
empty/nonempty selections, both bank modes, varied scales and non-unit input
quaternions. Output bytes match exactly using each emulator-observed RSQRT seed.
The receipt carries only synthetic inputs and numerical seeds, not game poses.
This does not promise identical seeds across hardware. A caller using exact
`1/sqrt(n)` supplies a numerical substitute. The adapter rejects nonfinite or
zero rotation norm; the original loop has no corresponding guard in this span.

The context's acquisition, initial quaternion extraction/normalization and
inverse-transform helper are still outside this kernel. Their static route is
identified but should be validated separately before accepting a raw target
transform as this function's input. Buffer lifetime and concurrent publication
remain open as well.

## Raw context conversion and unit-scale constraint

The raw context conversion is now implemented, superseding the preceding
section's unvalidated-conversion boundary. After obtaining the target's matrix,
the animation caller extracts its quaternion using the existing matrix-to-quaternion
helper, normalizes it with an RSQRT estimate and one refinement, and copies
translation XYZ while **masking position W to zero**. It then calls the transform
inverse helper.

The inverse helper conjugates quaternion XYZ, preserving W. It treats either
signed zero scale as one, then computes:

```text
s = 1 if input.position.w == 0 else input.position.w
inverse.rotation = conjugate(input.rotation)
inverse.position.xyz = -rotate(inverse.rotation, input.position.xyz) / s
inverse.position.w = 1 / s
```

It does not normalize the supplied quaternion itself. In this animation caller,
the masked W therefore always yields inverse scale 1. The previously recovered
gather loop supports arbitrary scale, but that general capability must not be
mistaken for a varying scale supplied by this caller. Raw matrix position W is
ignored, not inverted. Basis-derived quaternion extraction still uses the raw
matrix; this is not a general matrix inverse with arbitrary scale/shear handling.

The [work module](../../reference/animation_work.py) now exposes the inverse,
raw conversion and composed `gather_raw_context_work` pipeline. Callers supply the
raw matrix, selected bank records and RSQRT estimates in execution order. The
[280-case inverse receipt](../../native/snow_host/context_inverse_validation.json)
executes the complete inverse helper without stubs, covering signed zero,
positive/negative scales, signed-zero translations and non-unit quaternions.
The [128-case raw conversion receipt](../../native/snow_host/raw_context_validation.json)
executes the original matrix-extraction/normalization/masking/inversion chain;
its scalar sqrt service is supplied as float32 sqrt, and the observed RSQRT seed
is passed to the reference. Every output byte matches. Matrices and positions
are synthetic. The composed public API is additionally tested with a labeled
exact-reciprocal-square-root substitute for an identity-transform example.

Numerical conversion no longer requires an opaque converted-context input.
Live acquisition through the target's optional indirect transform service,
pose-buffer retention and concurrency remain unresolved. These numerical tests
do not turn a raw pointer read into a safe snapshot.

## Indirect transform copy and shared return storage

The indirect getter first calls a refresh helper, then obtains the current thread
ID. It admits a reader using a uint32 word. If stored owner thread equals current
thread and the owner-active byte is nonzero, it increments that word directly.
Otherwise it checks mask `0x7FF00000`, waits if any masked bit is set, atomically
adds one, and checks the resulting value again. If the increment encounters a
masked bit, it decrements back and retries. The owner branch bypasses this mask.
These are observed predicates; the full writer protocol is not yet reconstructed.

Once admitted, it copies four 16-byte rows from the associated entity into its
own scratch matrix, decrements the reader word, and returns a pointer to that
scratch matrix. It does not return an independently owned copy or retain a reader
count across the caller's use of the pointer.

```python
refresh_if_needed(accessor)  # opaque here; may update the associated transform
if accessor.owner_thread == current_thread() and accessor.owner_active:
    atomic_increment(accessor.reader_word)
else:
    while True:
        if accessor.reader_word & 0x7FF00000:
            pause()
            continue
        after = uint32(atomic_fetch_add(accessor.reader_word, 1) + 1)
        if not after & 0x7FF00000:
            break
        atomic_decrement(accessor.reader_word)
        pause()
accessor.scratch_matrix = copy_64_bytes(accessor.entity.matrix)
atomic_decrement(accessor.reader_word)
return pointer_to(accessor.scratch_matrix)
```

The [one-attempt model](../../reference/transform_access.py) exposes copy/retry
outcomes and counter state without pretending to implement a live lock. The
[60-case receipt](../../native/snow_host/transform_access_validation.json) runs
the original accessor with refresh and thread-ID services intercepted. Original
atomic operations and all copy instructions execute. A competing writer is
simulated by replacing the word immediately before fetch-add; retries stop at
the pause instruction. A separate two-call sequence verifies that both calls
return the same scratch storage and the second overwrites the first result.
No game process or genuine contention is involved.

This resolves the earlier uncertainty about whether the getter returns stable
caller-owned storage: it does not. Copying the returned matrix immediately reduces
exposure but does not prove safety against another concurrent getter. The code
allows multiple readers, and those readers write the shared scratch matrix. A
safe mod snapshot still needs an established caller serialization/lock scope and
object lifetime, or a separately validated copy operation performed under that
scope. Do not infer an atomic matrix snapshot from the reader-word protocol alone.

The refresh helper statically checks two descriptor predicates, may resolve a
reference through a thread-visibility mask, obtains a transform through a virtual
service, and publishes a transform event with flags `0x1F`. Its service effects
and writer-lock interaction remain open; no freshness guarantee is claimed here.

## Transform writer admission and publication

The transform-event producer uses the same reader word as the indirect getter.
An ordinary writer waits for mask `0x7FF00000` to be clear, atomically adds
`0x100000`, and accepts only if the masked post-add value equals `0x100000`.
Otherwise it subtracts its addition and retries. Once claimed, it waits for
low bits `0xFFFFF` to become zero before recording the owner thread. New ordinary
readers see the writer claim and cannot enter; existing readers can decrement.
A wait for readers retains the writer claim and must not be modeled as a failed,
fully rolled-back attempt.

Matching owner thread plus nonzero owner-active byte bypasses acquisition. On
entry to publication, the producer increments a separate depth word. It creates
an event with two pointers to the same prepared matrix and flags equal to the
incoming flags with bit 1 cleared, then invokes the associated entity's transform
virtual method. On normal return it decrements depth. At zero depth it sets owner
to all ones and atomically subtracts `0x100000`; otherwise the outer claim stays.
This is the entity transform event path examined earlier, whose callbacks can
mark skeletons dirty/pending. Receiver-specific callback effects remain external
to this lock model.

```python
if not (owner == current_thread and owner_active):
    while True:
        if word & WRITER_MASK:
            pause()
            continue
        post = uint32(atomic_fetch_add(word, WRITER_UNIT) + WRITER_UNIT)
        if post & WRITER_MASK == WRITER_UNIT:
            break
        atomic_fetch_add(word, -WRITER_UNIT)
        pause()
    while word & READER_MASK:
        pause()
    owner = current_thread
depth += 1
entity.transform_event(matrix, matrix, incoming_flags & ~2)
depth -= 1
if depth == 0:
    owner = UINT32_MAX
    atomic_fetch_add(word, -WRITER_UNIT)
```

The [writer-attempt model](../../reference/transform_access.py) returns retry,
wait-readers or published, with the exact descriptor and normal-return state.
Its [192-case receipt](../../native/snow_host/transform_write_validation.json)
executes the original segment with thread-ID and virtual publication intercepted.
It includes competing-word updates at atomic acquisition, low-reader waits,
owner bypass and nested depth. Some synthetic owner/depth combinations are
arithmetic probes and are not claimed reachable states. Genuine concurrent
execution, abnormal exits, owner-active-byte producers and matrix preparation
are excluded. Unit tests additionally compose writer admission with reader
admission to verify that a pending writer excludes new ordinary readers.

This identifies a publication exclusion window, not a ready-to-use mod lock API.
The transform callback runs while the writer claim is held, but arbitrary work
there may reenter the system or depend on other workers. The getter's shared
scratch storage is still released before its caller converts the matrix. The
next synchronization questions are who sets owner-active, which scopes serialize
getters, and whether the animation caller holds a broader lock or lifetime pin.

## Caller-owned transform copy and bypass initialization

A separate native copy-out helper accepts an accessor and destination matrix.
It uses the same thread comparison, bypass byte, reader admission/retry, and
reader decrement as the shared getter, but copies the four source rows directly
into the supplied destination and returns that destination. It does not call
the shared getter's refresh helper. This separates copy consistency from freshness.

The [60-case copy-out receipt](../../native/snow_host/transform_copy_validation.json)
executes the complete helper with only thread-ID lookup intercepted. It covers
the same admission and synthetic competing-word cases as the shared getter,
checks output and return destination, and verifies that two calls with distinct
destinations preserve the first result. It also executes the complete initializer
without stubs and checks the synchronization fields:

```text
reader_word = 0
owner_thread = UINT32_MAX
depth = 0
owner_bypass_enabled = 1
```

This corrects the earlier provisional `owner_active` name. The byte is initialized
enabled while no writer is active. The reference planners keep the old parameter
name for compatibility, but it means **owner bypass enabled**, not proof of an
active writer. The thread/depth state carries current ownership. Other writes
to this byte have not been exhaustively excluded.

The initializer was absent from the unwind-function inventory because it is a
leaf. A direct instruction-pattern search located it. This is a concrete example
of why an unwind-only function scan cannot prove a field has no writer.

The copy-out helper is a better candidate for an inspection API than returning
the shared getter pointer. Its proposed adapter contract is:

1. Acquire/validate the accessor and source entity under an established lifetime
   scope. Freshness policy must separately decide whether to invoke refresh.
2. Provide a dedicated 64-byte destination and call the native copy-out helper
   at an allowed execution point. Its original wait has no timeout.
3. Publish only copied values to the client; expose neither native pointers nor
   a promise that a newer transform cannot immediately replace the source.

The helper solves result-storage ownership, not accessor/entity lifetime, lock
ordering, unsupported source writers, or thread-affinity requirements. No live
copy-out API was enabled in this pass. A bounded live test should first identify
the player accessor, verify its entity link and current writer state, then invoke
copy-out at a proven callback boundary without introducing a second refresh path.
The original getter remains appropriate only where its caller's serialization
makes shared scratch use valid; that broader scope is still unproven.

## Accessor attachment and cleanup lifetime boundary

Static attachment paths allocate an accessor only if the entity's accessor field
is null, store it into that field, and write the entity backlink into the new
accessor. A direct-entity attachment descriptor also inserts the attached child
at the parent's child-list head: the child's next link receives the previous
head. The inverse unlink helper handles head or interior removal and clears the
removed child's next link. These fields are topology links, not observed accessor
reference counts. Attachment and unlink are static findings in this pass.

The cleanup routine takes an entity and a child to unlink. It returns immediately
if the entity has no accessor. Otherwise it unlinks the child and checks the
accessor's descriptor and remaining child/sibling links. If any dependency remains,
it leaves the accessor attached. Otherwise it releases the two descriptor holders,
passes the accessor to its allocator's deallocation service, and clears the
entity's accessor field **after** that service returns.

```python
if entity.accessor is None:
    return
unlink_child(entity.accessor, child)
a = entity.accessor
if descriptor_valid(a.descriptor) or a.children or a.next_sibling:
    return
allocation_info = allocation_metadata(a)
release(a.descriptor.second_holder)
release(a.descriptor.first_holder)
allocator_free(a, allocation_info)
entity.accessor = None
```

[The cleanup planner](../../reference/transform_access.py) uses supplied
post-unlink predicates. The [48-case receipt](../../native/snow_host/accessor_cleanup_validation.json)
executes the complete original cleanup routine with unlink, descriptor predicate,
allocator metadata and deallocation intercepted. Holder decrement instructions
and owner-slot clearing execute unchanged. Holder counts start at two so the
retirement service is not reached. The receipt varies reader words zero, three
and a writer-plus-reader value; the cleanup result does not depend on them.
The deallocation callback still sees the entity pointing at the accessor.

This routine does not read or drain the accessor reader word. That is a concrete
limit on using reader admission as a lifetime pin, not proof of a live race:
callers may already serialize topology changes or hold a broader scope. Likewise,
checking the entity/accessor backlink once cannot guarantee survival through a
later copy call, and the owner-slot clear occurs too late to be a universal
pre-deallocation signal. A live snapshot API must use a scope that excludes this
cleanup path, not just validate links or increment the reader word.

The next lifetime investigation should trace callers of cleanup and attachment,
identify their world/entity mutation phase, and compare that phase against the
verified player post-update callback. The copy-out helper remains the preferred
storage operation once that exclusion is established. No live accessor call or
new mutation API was enabled by this pass.

## Cleanup callers and invalidation order

A direct-call scan followed by instruction inspection identifies two routes into
the previously validated accessor cleanup: direct-entity descriptor detachment,
and child-list traversal detachment. The descriptor route resolves its holder
through the thread-visibility mask before calling cleanup. The child traversal
copies descriptor holders, invokes a child callback, then dispatches detachment
by descriptor kind. These local routines do not establish a scheduler barrier;
opaque callbacks and outer callers may provide additional synchronization.

There is also an accessor deallocation block inside parent detachment itself.
It resets descriptor references, then, when its release argument is enabled,
checks the descriptor and remaining links before deallocation. Like the separate
cleanup routine, that inspected block does not consult the reader word. This
second free site must be included in any lifetime probe or caller audit.

The higher transform-teardown wrapper executes:

```python
if entity.accessor is not None:
    detach_parent(entity, release_unused_accessor=True)
    detach_children(entity)
base_control_record_invalidation(entity)
```

The base helper conditionally performs global tracking removal and invalidates
the object's indexed control record. This ordering means external control-record
invalidation follows detachment rather than preceding it. An observer must not
use a still-valid entity control record alone as proof that its accessor survived.
This is an ordering limitation, not a demonstrated race or proof that all callers
permit simultaneous observation.

The [16-case teardown receipt](../../native/snow_host/transform_teardown_validation.json)
executes the original wrapper and base invalidation dispatcher with detachment
and final control-record invalidation intercepted. Optional global tracking is
disabled. Cases cover accessor presence, indexed state, both invalidation modes,
and a simulated detach that clears the accessor slot. Child detachment is still
called after that clear because the wrapper's initial test selects both calls.
The [order planner](../../reference/transform_access.py) exposes only this verified
local order. Destruction and scheduler exclusion are not executed by the fixture.

The attachment wrapper can explicitly detach an old relationship before creating
a new one, while a separate refresh/reattach path also reaches attachment. Thus
accessor topology changes are not yet confined to an established destruction-only
phase. A claim that post-update universally excludes these paths would be premature.

For the next live instrumentation design, record parent-detach entry/return,
child-detach traversal and both accessor-free sites alongside the player
post-update callback. Correlate entity identity and request IDs, retain incomplete
traces, and observe reattachment/respawn as well as ordinary riding. Such a trace
can find overlap or narrow phase candidates; absence of overlap in one capture
still will not prove a lifetime contract. Static caller-to-scheduler joins remain
required before releasing a general snapshot API.

## Passive accessor preflight observations

The new [passive reader](../../engine/transform_accessor_observation.py) accepts
a process-identity-checked `readv`, a freshly acquired entity and external identity
guards. It reads the entity accessor slot, checks the accessor's entity backlink,
and reads the reader word, owner thread, depth and bypass byte. It rechecks every
observed field and supplied guard before returning. A missing accessor reports
the inline-transform path without following a null pointer.

The report contains metadata, not process addresses or matrix contents. It splits
the reader word into low reader units, masked writer units and the high bit,
without inventing a meaning for that high bit. The owner sentinel is reported as
null. It exposes both raw and boolean bypass values. Changed linkage/state,
backlink mismatch and incomplete reads reject the observation. There is no
"safe to call" success state: lifetime retention, atomic snapshot, freshness and
native-call safety remain explicitly false even when all guards match.

A private capture adapter now connects this reader to fresh process/player/world
acquisition and the existing bounded memory reader. It does not inject, call a
native accessor, collect matrix payloads or generate gameplay input. It was
syntax-checked but not run live in this pass because another agent's terrain
capture owns the current game session. Six synthetic tests cover indirect/inline
sources, metadata-only reporting, changed accessor, changed reader state, wrong
backlink and short reads. This prepares the passive prerequisite for the later
callback-correlated lifetime experiment; it is not that experiment's result.

Guard matches permit ABA changes and do not prevent freeing between reads. A
reader count of zero is merely an observation, not authorization to dereference
or call later. The capture deliberately preserves this distinction so downstream
agents cannot mistake a clean preflight report for the missing lifetime proof.

## Animation work duration and saved-request handoff

Following the work-buffer application routine resolves the previously unknown
scalar's role in this path: it is a blend duration. The evaluator stores the
incoming scalar as work duration and resets elapsed time. Application obtains dt
from the owning entity's selected world time group, adds it to elapsed in float32,
and compares the new elapsed value with duration before processing records.
Missing entity or world supplies dt zero. A null destination bank returns before
changing the clock.

```python
if destination_bank is None:
    return
work.elapsed = float32(work.elapsed + selected_world_dt_or_zero)
if work.elapsed >= work.duration:
    work.count = 0
    work.elapsed = work.duration = float32(0)
    return
# With matching selected-channel/work counts:
alpha = float32(work.elapsed / work.duration)
position = saved_position + float32((current_position - saved_position) * alpha)
# Rotation uses the branch-specific quaternion interpolation path.
```

Thus equality expires the work before applying a final alpha-one pose through
this routine. Position moves from saved work toward the current bank pose as time
increases. The duration uses the same units as the selected world timestep; this
pass does not independently calibrate those units against wall-clock seconds.
It establishes this consumer's duration semantics, not every use of the component's
stored scalar. The two fields earlier described as cleared uint32 counters are
now identified as float32 duration and elapsed; the zero-bit clearing observation
remains correct.

If the nonexpired application path reaches its normal tail and a saved-request
flag is nonzero, it invokes the evaluator with scalar zero, null context and the
current destination bank. This connects directly to the earlier saved-request
arbitration: that zero/null call can consume a deferred request. The expired path
jumps past this tail and does not perform that handoff here. A selected-channel
count mismatch can skip per-channel writes while still reaching the handoff.
Rotation interpolation, bank writeback and exact count-mismatch behavior are
static leads beyond this pass's executed boundaries.

[The timing model](../../reference/animation_work_timing.py) and
[384-case clock receipt](../../native/snow_host/animation_work_timing_validation.json)
execute the original prefix without service stubs. Cases cover no bank, missing
owner/world, both time groups, zero/positive durations, zero dt and elapsed values
below, at or above the duration. Four additional tail checks verify zero scalar,
null context, bank argument and nonzero flag behavior with the evaluator intercepted.
Tests compose that handoff with the independently recovered request model.
No pose writes or complete animation cycle are claimed by these checks.

The next numerical step is recovering quaternion interpolation and bank setter
semantics, then joining clock, gather, apply and deferred-request behavior into an
executable work-buffer state machine. Live accessor lifetime remains a separate
open dependency for original-process observation.

## Work rotation interpolation branches

The no-visible-context application path calls a quaternion helper distinct from
the graph's polynomial blending helper. With saved rotation `a`, current rotation
`b`, float32 alpha `t` and pairwise-reduced float32 dot product `d`:

1. If `abs(abs(d) - 1) <= 2^-23`, copy `a` unchanged. This includes exact antipodal
   quaternions and does not normalize or consult alpha.
2. Otherwise, if `d < float32(0.9893559813499451)`, call the spherical helper.
   That helper returns `b` if dot is outside the open interval `(-1, 1)`.
   Within the interval it uses `theta = acos(abs(d))`, sine weights, and negates
   the weight on `b` for negative dot. It returns `b` for a tiny angle at or below
   float32 `1e-5`; otherwise it combines and normalizes the weighted rotations.
3. Otherwise, compute `(1-t)*a + t*b` with the original float32 order, then normalize
   using an RSQRT estimate plus one Newton refinement.

Alpha is not clamped by this helper. The model's finite/positive-norm checks are
inspection policy. The visible-context application code inlines similar branch
arithmetic after normalizing the reconstructed saved rotation; this pass validates
the standalone helper called by the no-visible-context branch, not that entire
other application loop.

[The rotation kernel](../../reference/animation_work_rotation.py) exposes `acos`,
`sin` and RSQRT estimates as numerical services. Its
[192-case receipt](../../native/snow_host/animation_work_rotation_validation.json)
executes the complete original helper and spherical callee with acos/sin supplied
as float32-rounded host math. The same results and observed RSQRT seeds feed the
reference. Output matches byte-for-byte across near-aligned, opposite, wider-angle,
non-unit/out-of-range and randomized quaternion cases. This verifies the branch
and arithmetic orchestration, not the original transcendental library internals
or universal hardware RSQRT equivalence.

## Work pose-bank setter

The [bank encoder](../../reference/animation_work.py) recovers the setter's direct
and composed branches. Direct mode writes both input vectors unchanged. Composed
mode conjugates the bank parent quaternion, rotates the negative parent translation,
then applies that inverse rigid transform to the incoming record. It does not
divide by parent scale or normalize the resulting quaternion. Its stored position
W becomes zero, even when the incoming record and parent have nonzero W.

Conceptually, for unit parent quaternion:

```text
q_inverse = conjugate(q_parent)
p_local.xyz = rotate(q_inverse, p_input.xyz) - rotate(q_inverse, p_parent.xyz)
p_local.w = 0
q_local = q_inverse * q_input
```

The executable preserves the original separate float32 rotation/addition order,
including non-unit-quaternion polynomial behavior. It does not replace the two
rotations with a differently rounded rotation of a subtraction.

[192 original setter cases](../../native/snow_host/work_setter_validation.json)
execute the complete helper without stubs and match every output byte. The native
index uses its low 16 bits; cases check this truncation, both bank modes, arbitrary
finite fourth lanes and non-unit quaternions. Unselected records and bank flags
remain unchanged. The application caller separately sets bank bit 27 after each
write. Allocation, index bounds and synchronization are not supplied by the setter.
These local kernels now provide the missing rotation/writeback pieces for a
no-visible-context work-buffer application state machine; that composition still
needs its own original-loop validation.

## Context-free work application loop

`reference.animation_work_application.apply_work_records` reconstructs the whole
context-free application loop, including provider composition, work quaternion
interpolation, four-lane position interpolation, and bank-local writeback.
The caller supplies the already-advanced elapsed time and duration. Alpha is
float32(elapsed / duration), without a clamp. A selected-count/work-count mismatch
skips all pose writes. Empty matching lists also perform no writes.

Each selected index reads the current bank **at that iteration**. Duplicate
indices therefore observe earlier writes. Position uses float32 subtract,
multiply, then add in saved + (current - saved) * alpha order. The setter converts
that result to bank storage. The original loop sets bank bit 27 after each write;
the independent kernel reports `written` rather than exposing a native bank.

The [synthetic receipt](../../native/snow_host/work_application_validation.json)
contains 128 original-instruction emulation cases with exact record-byte matches,
including repeated indices, empty and mismatched counts, direct and composed
banks, randomized parent rotations and four interpolation fractions. Original
rotation helpers and setter execute inside the loop. Transcendental services use
float32-rounded host math and RSQRT estimates are supplied from the emulator.
This does not establish original transcendental implementation parity.

Clock advancement, the caller's initial dirty-bit clear, context-bearing branch,
and deferred-request tail are outside this receipt. Object retention, live
synchronization and scheduler placement remain separate requirements. The
adapter rejects zero duration rather than emulating native exceptional division.

## Context-free update timing and dispatch

`update_context_free_work` combines the clock and application loop through the
saved-request dispatch boundary. `dt` is the caller-selected world timestep;
`bank_flags` is the initial uint32 state. Direct/composed selection must agree
with bank bit 26. Input records and output records are independent Python values.

- No destination bank: preserve clock, records and flags; no handoff.
- Elapsed plus dt reaches duration: clear work count, elapsed and duration;
  preserve bank flags and records; no handoff.
- Active work: clear bank bit 27 before checking selected/work count equality.
  Apply matching records in order, setting bit 27 after a write.
- Both matching and mismatched active work reach saved-request dispatch. A nonzero
  saved flag requests evaluation with scalar zero and null context.

The returned `handoff` describes dispatch only. The deferred evaluator can change
work state and is not executed by this adapter. The returned clock and records
therefore describe state before those possible effects.

The [full-update receipt](../../native/snow_host/work_update_validation.json)
checks 256 synthetic cases against the entire original context-free routine,
including its prologue and return, world timestep read, clock state, count,
record bytes, dirty flag and deferred-call arguments. The deferred evaluator is
intercepted without effects. The same explicit trig services and captured RSQRT
seeds used for the local loop apply. Cases include missing destination, expiry,
empty selection, mismatched counts, repeated indices and direct/composed banks.
The context-bearing branch and live lifetime/thread requirements remain open.

## Application context has literal zero scale

`reference.animation_work.prepare_application_context` recovers the forward
context conversion in the context-bearing application caller. It extracts and
normalizes the matrix quaternion, copies translation XYZ, and clears position W
to zero. Unlike the gathering caller, it does not call the inverse helper, whose
zero-scale fallback would have changed that W to one.

The next transform-composition helper uses context W as scale. Consequently its
saved-position XYZ contribution is multiplied by zero: the intermediate position
becomes the context translation, with zero W. Rotation still composes with the
saved rotation and is subsequently normalized by the caller. This is a literal
local instruction result, not evidence that all animation positions collapse
in gameplay. Context-bearing activation, real inputs, later interpolation and
bank conversion must still be validated together.

The [128-case synthetic receipt](../../native/snow_host/application_context_validation.json)
executes the original matrix extraction and normalization caller and then the
original transform-composition helper. Converted context and composed record
bytes match the reconstructed math. Inputs vary rotation matrices, translation,
raw fourth lanes and saved positions. Scalar square root is supplied by host
math; RSQRT seeds are observed. Context acquisition, the intervening loop setup,
post-composition normalization and complete application are outside this receipt.
Do not replace the zero scale with one merely because that looks more plausible.

## Complete inline-context update

`reference.animation_work_application.update_context_work` composes the recovered
clock, forward context conversion, saved-pose transformation and normalization,
per-record interpolation, bank conversion and deferred-dispatch decision.
The supplied context matrix represents the inline target-transform route.
Acquiring an indirect accessor result remains external and requires separate
lifetime and synchronization guarantees.

Normalization and blending are interleaved for each record. Do not gather and
normalize all saved records first: explicit RSQRT services are consumed in native
execution order, and each bank read observes preceding writes. Context conversion
occurs before the selected/work count comparison, even on a mismatch. Missing
bank and expiry return before context conversion. The literal zero context scale
identified above survives into this complete instruction path.

The [512-case receipt](../../native/snow_host/context_update_validation.json)
executes the original routine from entry to return with inline context storage.
It checks exact bank record bytes, clock, count, dirty flags, and deferred-dispatch
arguments. Synthetic cases cover randomized context/parent rotations, identity
contexts, non-unit saved rotations, interpolation fractions, repeated indices,
empty and mismatched counts, expiry and missing banks. Original pose composition,
normalization, rotation blending and setter instructions execute. Host sqrt/trig
services and observed RSQRT seeds remain explicit numerical dependencies. The
deferred evaluator is intercepted without effects. No live target acquisition,
object retention, scheduling guarantee or original-engine equivalence is claimed.

## Evaluator work replacement

`reference.animation_evaluator.evaluate_work_request` connects saved-request
arbitration to the duration gate, gathering and persistent clock updates.
It requires an existing work-state object and a supplied bank. It is independent
Python storage, not a native allocator or ownership implementation.

For nonzero work count with an empty saved slot, the incoming request is saved
and evaluation returns without changing records or timing. Otherwise arbitration
may consume the saved request. A negative effective duration, or magnitude at
most float32(1e-5), clears count, elapsed and duration. Old storage contents are
not erased. Larger positive durations replace the selected work records with
current gathered poses, store the duration and reset elapsed to zero.

A `resolve_context(token)` service supplies either no visible target or a raw
matrix for context-relative gathering. Tokens are symbolic identities. This
service does not establish retained ownership. `records` in work state are backing
contents; only the first `count` entries are active after a clear/defer operation.
Incoming and effective scalar finiteness checks are adapter policy.

The [80-case full evaluator receipt](../../native/snow_host/work_evaluator_validation.json)
executes the original routine with preexisting work storage and holders without
visible targets. Cases cover zero/nonzero active count and saved flag, negative,
zero, epsilon, just-above-epsilon and ordinary positive durations, direct/composed
banks and explicit versus skeleton-fallback bank selection. Checks include
request fields, count, elapsed/duration and replacement record bytes. The native
capacity service is intercepted with synthetic storage; the resize wrapper and
count write execute. Reference operations execute but retirement is not triggered.
Absent-work allocation, allocator effects, visible-target evaluator integration,
concurrent ownership and nonfinite native behavior are not covered.

## Evaluator with a visible context

The [context evaluator receipt](../../native/snow_host/context_evaluator_validation.json)
adds 80 complete original-routine cases with visible inline context targets and
randomized rotation matrices/translations. It verifies the same request,
count, clock and gathered-record results as the no-target evaluator receipt.
Matrix extraction, normalization, inverse conversion and context-relative gather
all execute within the original evaluator. This validates the composition already
implemented by `evaluate_work_request`, not merely its individual helpers.

Scalar sqrt uses host math rounded to float32; captured RSQRT seeds are supplied
to the reconstruction in call order. The capacity service still supplies
synthetic storage. All work objects preexist, reference counts avoid retirement,
and target transforms use inline storage. Indirect accessor refresh/copy, absent
work allocation, allocator failure and live lifetime/concurrency remain outside
these cases. The synthetic global fallback holder also has a visible target in
this experiment; this is a coverage fixture, not a claim about its game state.

## Connected update and deferred evaluation

`reference.animation_evaluator.finish_work_update` joins a validated update
receipt to its deferred evaluator. It carries the updated count/clock into work
state, supplies the **post-update bank**, and invokes evaluation with scalar zero
and null context only when the update requests a handoff. The update receipt
remains a pre-handoff observation; returned work is post-evaluator state.

The [256-case connected receipt](../../native/snow_host/work_cycle_validation.json)
executes the original context-free update and its real evaluator call without
intercepting the handoff. It checks bank bytes/flags, final count/clock, saved flag
and scalar, plus replacement work-record bytes. Cases include missing bank,
expiry, empty/mismatched/repeated selections, direct/composed banks, and queued
negative, zero, epsilon and positive durations. Deferred evaluation either clears
work or gathers replacement records from the newly written bank. Expiry leaves
the deferred request untouched because that path never calls the evaluator.

Capacity allocation supplies synthetic backing storage. Trig services and RSQRT
seeds retain the numerical-service limitations of earlier receipts. All objects
preexist, replacement contexts have no visible target, and no holder retirement
is triggered. This verifies a connected state transition, not native allocation,
live ownership, scheduling, or a multi-frame original-game replay.

## Connected cycle switching visible contexts

The [context-switching receipt](../../native/snow_host/context_cycle_validation.json)
executes 256 complete context-bearing update/evaluator cycles. The active work
uses one synthetic inline target matrix; the queued request selects a different
visible target matrix. Both transforms vary across cases. Original application,
deferred dispatch, request consumption, holder exchange, matrix inversion and
replacement gathering execute in one call chain.

Checks cover final bank bytes/flags, work count and clock, saved request fields,
replacement pose bytes, installed holder identity and both reference counts.
On successful replacement, the old holder changes from 20 to 19 references and
the new holder from 20 to 21. Clear/no-handoff paths preserve those counts and
the original installed holder. No retirement service is triggered.

The independent evaluator now returns `active_context_token` after replacement.
It identifies the symbolic context selected for gathering; a caller can use it
to resolve the next update's context. Existing active tokens are preserved on
clear/defer/no-handoff paths. A token is not a retained native reference or an
address, and the resolver still owns visibility/freshness policy.

Capacity remains synthetic. Sqrt/trig services and observed RSQRT seeds have the
previous numerical limitations. Context access is inline and all objects already
exist. This closes the connected visible-context arithmetic/state transition,
not allocator behavior, concurrent ownership, target refresh or live safety.

## Animation work storage initialization

`reference.animation_work_storage.plan_work_creation` describes work creation
without implementing the native allocator. Existing work, missing skeleton or
zero selected channels returns unchanged. Otherwise the routine requests 1120
bytes with 16-byte alignment. It installs inline record storage with capacity
32 and zero active count. More than 32 selected channels requests larger backing
storage through the reserve helper. Count stays zero until evaluator gathering.

Duration, elapsed, saved flag, saved scalar and saved context are initialized to
zero. Pose backing bytes are not initialized here. An independent runtime must
not treat reserved capacity as valid poses or manufacture identity transforms as
recovered initial contents. The initial holder is the global fallback holder.

The [40-case original-instruction receipt](../../native/snow_host/work_creation_validation.json)
covers existing/missing work and skeleton, selections 0/1/32/33/64, and synthetic
allocation success/null. Both allocation services are intercepted; reserve
allocation also receives synthetic storage. The original reserve wrapper and
capacity handler execute. Poisoned inline pose bytes remain unchanged, while
header, count, timing and request fields match. Dynamic allocation/free behavior
is not established by this test.

When the allocation service is made to return null, the routine stores null in
the work slot and then attempts a null-relative duration write. The emulator
faults at that write. This is not a graceful native failure branch and is not
evidence that the real allocator ever returns null: it may throw, terminate or
otherwise enforce success. The reconstruction reports `null_write_path` rather
than pretending the operation succeeds or safely returns unchanged.

With a synthetic initial fallback reference count of 20, this routine's increment
and two decrements leave 19; no retirement is triggered. That local count delta
is not a complete global-holder ownership model. Allocator policy, fallback
lifetime conventions and concurrency remain unresolved.

## Preparation hierarchy conversion

After primary-bank work application, skeleton preparation calls a hierarchy
conversion before marking pending. `reference.animation_hierarchy.compose_primary_hierarchy`
recovers the numeric loop: read primary poses and rebuild current poses in index
order, composing each eligible pose with its already-stored current parent pose.
Normalize each composed quaternion using RSQRT plus the recovered refinement.
The root uses the identity rotation and no parent-position add. Its rank gate is
bypassed; the omitted add preserves a signed-zero distinction in position W.

Metadata supplies a parent uint16, skip-span uint16 and three-bit rank. For
nonroot records, rank greater than the caller's three-bit value skips `span + 1`
records, leaving their current poses unchanged. Otherwise compose and advance
one. The comparison is a numeric threshold, not a bitwise intersection. The
rank's producer/meaning is unresolved; do not label it animation LOD without
further evidence. The adapter requires preceding valid parents and nonwrapping
skip increments rather than reproducing malformed native metadata behavior.

The native wrapper obtains total count from the current bank's skeleton table.
It skips the numeric loop for zero count and always clears bit 27 in both banks,
including that empty case. The independent numeric function returns records and
visited/skipped indices; its caller must perform those flag clears separately.
The alternate current-bank processing branch uses a different helper and is not
established by this reconstruction.

The [192-case receipt](../../native/snow_host/primary_hierarchy_validation.json)
executes the complete primary-processing wrapper and hierarchy loop without
service stubs. Captured hardware RSQRT estimates are supplied to the model.
Cases cover zero/one/multiple records, all eight threshold values, randomized
metadata skips, non-unit pose rotations, and signed-zero root W. Exact output
record bytes and both flag clears are checked. Real skeleton metadata, skip-span
semantic validity and end-to-end preparation integration remain unverified.

## Alternate preparation reconciles both pose banks

`reference.animation_hierarchy.reconcile_current_hierarchy` reconstructs the
mode-one path selected by current-bank preparation. Metadata bit 3 selects the
conversion direction independently for each eligible bone:

- Set: subtract current parent position from current child position, rotate by
  the conjugate of the current parent quaternion, compose the conjugate with the
  current child quaternion, normalize and store into the primary/local bank.
- Clear: compose the primary/local pose with the current parent pose, normalize
  and store into the current bank.

These operations preserve native float32 order. The inverse position path rotates
`child - parent` as one vector; it is not the setter's separately rotated terms.
The root uses identity orientation without a parent translation. All child parent
reads use the current bank as it exists at that iteration. Metadata rank/skip
handling matches the primary converter, while root bypasses the rank test.
`current_authoritative` is our descriptive API name for bit 3, not a recovered
field name or a claim about what sets it.

The wrapper tests the skeleton's total-count field before dispatch. The dispatched
loop uses a separate count field as its processed prefix. Their producer relationship remains unknown. The adapter accepts an explicit
`processed_count` independently of total bank length; validation now varies them
separately. A nonempty total with prefix zero still processes the root. Mode zero's external selection bitset and
other mode values are outside this recovered entry path.

The [384-case receipt](../../native/snow_host/current_hierarchy_validation.json)
executes the entire wrapper and mode-one helper, with no service stubs and
observed RSQRT estimates supplied to the model. Both output banks match byte for
byte under mixed direction bits, rank thresholds, skip spans, non-unit rotations, independently varied prefix
counts and varied bank sizes. Nonempty processing clears bit 27 in both banks. An empty
wrapper returns without clearing either flag, unlike the primary wrapper.
Real metadata producer semantics and complete skeleton-preparation integration
remain open.

## Integrated skeleton preparation

`engine.animation_preparation.prepare_animation` connects the recovered caller
with request evaluation, work application, deferred evaluation and both hierarchy
processing branches. It accepts separate current/primary banks, existing work,
selected indices and hierarchy metadata. Numerical services and context
resolution remain caller supplied. Total count follows supplied metadata/bank length. Optional
`hierarchy_prefix_count` supplies the alternate helper's separate processed count;
when omitted it defaults to total count.

A nonnegative scalar requests evaluation before the component lock and is then
replaced with -1. The post-evaluation active count determines whether preparation
continues. Zero mask clears work count and clock without applying poses. Otherwise
the caller locks, applies work, runs its selected hierarchy pass, marks pending
bit zero and unlocks. It does not recheck work count between apply and hierarchy
processing: expiry during application still reaches processing and pending.
Returned lock events describe native order; the independent adapter acquires no
native lock. The runner stores timing as float32 at initialization so skipped
work paths retain native-width values.

The [128-case integrated receipt](../../native/snow_host/preparation_integrated_validation.json)
executes the complete original preparation call chain, including real evaluators,
application, hierarchy helpers and clear-work leaf. It checks both bank record
bytes and flags, active work/count/timing, scalar sentinel, pending and service
order. Pending is checked before unlock. Locks and capacity allocation are
intercepted; trig services and captured RSQRT seeds retain earlier limitations.
Objects preexist and contexts have no visible target in these cases. Separate
context-bearing cycle evidence does not by itself establish complete preparation
with indirect targets, real locks, real metadata or competing jobs.


## Zero-prefix hierarchy boundary

The alternate wrapper gates on total skeleton count, while its helper processes
the root before checking the separate prefix end. Therefore a nonempty bank with
prefix zero still converts and normalizes root zero, then clears both dirty flags.
An actually empty bank bypasses the helper and preserves those flags. Prefixes
shorter than total count leave the remaining records in both banks untouched.
The revised 384-case hierarchy receipt checks these byte-level boundaries; the
128-case complete preparation receipt also varies prefix independently.

The adapter bounds prefix to supplied bank length. It does not manufacture
unavailable tail records or infer why an original skeleton chose its prefix.
This resolves consumer behavior, not the metadata producer or live LOD policy.

## Hierarchy rank producer

`reference.animation_metadata.assign_hierarchy_ranks` recovers the assignment
loop for metadata bits 4 through 6. Its default rank is 5 when a resolved owner
is visible and its uint32 selector is at most 1; otherwise the default is 1.
For each parallel uint32 key, the producer queries an owner-held map. A hit
replaces the default with the returned uint32 value. The low three bits become
rank; all other metadata flag bits, including direction bit 3, remain unchanged:

```python
rank = overrides.get(key, default) & 7
flags = (flags & 0x8f) | (rank << 4)
```

The [128-case receipt](../../native/snow_host/hierarchy_rank_validation.json)
executes original default-selection and complete assignment-loop instructions.
A visibility helper supplies zero and map lookup supplies synthetic hit/miss
results. Cases cover visible/hidden owners, selector 0/1/2/uint32-max, empty and
multiple records, high-bit keys, arbitrary override values and existing flag
bits. Keys and exact flag writes match. The owner selector's enum name, map's
semantic identity, override authoring and nonzero visibility-helper behavior
remain unknown. This is a producer rule, not proof that the rank means LOD.

Static builder inspection also links each 32-byte metadata record's parent to
its source parent object's index, its skip span to the source bone's stored
uint16 span, and its parallel key to the source bone's uint32 identifier. These
joins were inspected, not covered by the assignment-loop receipt. The metadata
array's own count supplies the alternate helper's processed count; the count
previously called total belongs to a separate uint16 mapping array. One assembly
path sizes that mapping from metadata count, but this does not prove universal
equality across all mutations. Direction-bit production remains open.

## Direction-bit producer selects named channels

`choose_authority_preset` and `mark_authority_channels` recover the producer of
metadata bit 3 and the work-selection list. A visible owner with selector at most
1 takes one of two fixed identifier tables: if `LeftToeBase` lookup returns missing
uint16 65535, use the 22-entry standard table; otherwise use the 26-entry extended
table. Outside that owner branch, an alternate selector equal to 2 chooses a
third 22-entry table; other values make no additions in this span. These preset
names are ours, and the numeric selectors are not assigned sport/type labels.

Each table key is resolved against the assembled skeleton. A missing result is
skipped. A found result sets metadata bit 3 and appends the uint16 index to the
selected-work list, in table order. Duplicate resolved indices are retained.
The operation does not clear existing flags or reset an existing list in this
span. Earlier construction must establish that state.

The [identifier catalog](../../native/snow_host/authority_channel_identifiers.json)
contains only resource keys and CRC-matched names, no transforms or asset bytes.
The standard table includes Reference, Spine/Spine1/Spine2, Neck, Head, bilateral
upper leg/leg/foot, shoulder/arm/forearm/hand and first middle-finger joints. The
extended table additionally includes both toe bases and third middle-finger
joints. The alternate table overlaps those channels, includes second index-finger
joints, and retains six unresolved identifiers rather than guessing their names.
CRC matches establish spellings subject to collision limits, not stored strings.

The [128-case receipt](../../native/snow_host/authority_channels_validation.json)
executes the original selection gates, original fixed-table loops and actual
append helper with preallocated capacity. Visibility, key lookup and alternate
selector services are supplied synthetically. Checks cover exact lookup keys,
flag writes, appended indices/count, missing entries and duplicate resolutions.
This connects named channel selection to current-to-local hierarchy conversion
and work gathering. It does not identify runtime sport ownership, discover the
lookup implementation, or prove allocation/concurrent mutation safety.

## Authority selection with original lookup routines

`resolve_authority_channels` joins preset selection to two recovered unsigned
lower-bound searches. Both tables hold eight-byte entries: uint32 key followed
by an encoded value whose low uint16 is returned. First equal key wins; missing
keys return 65535. The existing `pose_channel_index` implementation supplies this
same algorithm, now validated against these two additional original callers.

The owner target's table answers the LeftToeBase predicate. The assembled runtime
skeleton's separate table resolves preset keys into channel indices. Do not use
one table for both operations merely because both accept the same identifiers.
The alternate-selector helper reads the same owner uint32 value, or returns 8
when that owner is not visible. Under stable-owner inputs the policy simplifies:
visible values 0/1 use toe-dependent standard/extended sets, visible value 2 uses
the alternate set, and other/hidden values add nothing in this producer span.
Repeated native owner reads could observe changes; the independent adapter's
stable-owner assumption is explicit, not a concurrency guarantee.

The [128-case connected lookup receipt](../../native/snow_host/authority_lookup_validation.json)
executes both original lookup routines, the original alternate-selector helper,
preset loops and append helper. Only the visibility helper is supplied as zero;
capacity is preallocated. Duplicate runtime keys verify first-equal selection,
including high-bit identifiers. Owner-table entries with a 65535 value behave as
missing for the toe predicate. Flags and complete appended index lists match.
The owner value's semantic enum names and table construction remain unresolved.

## Initial source-bone metadata builder

`build_source_metadata` recovers the initial empty-table population loop from
source bone objects to 32-byte runtime records. The first record receives parent
65535 regardless of the source parent. Later records copy the source parent's
stored uint16 index. Each row copies the source skip span, source index and
uint32 identifier; the same identifier is written to a parallel key array.
The caller's selector byte is copied independently of the rank/direction fields.

A nonnull linked source supplies its stored index and the low three bits of the
source link-mode value. With no link, the linked-index field uses the current
output index and those mode bits become zero. This fallback is not necessarily
the source index. Updating low mode bits preserves the higher flag bits, including
rank and direction; their later producer passes remain separate. The native loop
also writes a parallel array of source pointers, which the portable structured
result deliberately omits.

The [128-case receipt](../../native/snow_host/source_metadata_validation.json)
executes the complete nonempty initial population loop with no service stubs.
All written fields, parallel keys and copied pointer identities are checked;
other record bytes are poisoned and verified unchanged. Inputs vary source and
parent indices, spans, link presence/modes, selectors, identifiers and initial
flags. The public receipt contains symbolic numeric fields only, no source
pointers or bone transform payloads.

The preceding reserve/default-initialization helper, existing-skeleton merge and
reindex paths, and serialized-object decoder are outside this receipt. In
particular, callers must supply initial flags rather than treating untouched
bytes as zero or assigning semantic names to the unknown low-bit link modes.

## Runtime metadata initialization and in-capacity resize

`initialize_metadata_record` writes only the native initializer's observed
fields in a supplied 32-byte backing record. Parent and linked index become
65535; skip span and source index become zero; selector byte becomes zero;
byte 9 becomes 15; bytes 16 through 23 become zero. Flag byte 10 becomes
`(old & 0x90) | 0x10`, equivalently preserving bit 7 while setting rank 1 and
clearing low mode bits and direction bit 3. Bytes 11 through 15 and 24 through
31 remain untouched. This is not a whole-record zero fill.

`resize_metadata_in_capacity` updates count and initializes only indices in
`[old_count, new_count)` when growing. Shrink and equal-size operations do not
erase or reinitialize records. Capacity and storage remain unchanged. This
provides the actual starting flags for the initial source-metadata builder;
later rank and direction producers then modify their respective bit fields.

The [81-case receipt](../../native/snow_host/metadata_initialization_validation.json)
executes the complete original resize helper and initialization leaf without
service stubs for every old/new count from 0 through 8. Random backing bytes
verify all written and retained bytes, not just the named fields. Capacity growth,
allocation failure and malformed native count/range behavior remain outside this
in-capacity model. Backing bytes are synthetic fixtures, not game records.

## Animation array capacity replacement

`reference.animation_capacity.plan_capacity_change` recovers the shared capacity
helper used by work and metadata arrays. The packed header holds capacity in low
14 bits, an embedded-storage flag at bit 15, and active uint16 count in the upper
half. Without force, sufficient capacity returns unchanged. Otherwise request
allocation for the requested element count and supplied stride.

A null allocation result preserves the old pointer/header and skips copy/release.
On success, copy `active_count * stride` bytes when nonzero, release the old
pointer only if present and not marked embedded, then install the new pointer.
The replacement header preserves active count, records requested capacity and
clears the old storage flag bits. Copy length follows active count, not requested
capacity. The adapter restricts capacity to its representable range; callers
must still avoid forced requests smaller than their active data.

The [48-case receipt](../../native/snow_host/animation_capacity_validation.json)
executes the full original capacity helper with allocation, memcpy, allocation
metadata and free services intercepted. It checks service order, copied bytes,
old-pointer visibility during release, final pointer and packed header. Cases
cover zero/nonzero active count, sufficient/growing capacity, force, embedded
versus separately owned old storage, and allocation success/failure. No actual
allocator policy or concurrent access guarantee is established.

This helper's failure behavior is not a safe-failure guarantee for its callers.
The previously inspected metadata resize wrapper unconditionally updates count
and initializes the newly active range after calling it. A synthetic null return
with insufficient old storage could therefore leave a caller writing beyond its
capacity. Whether real allocation services can return null here remains unknown;
the independent adapter must report failure instead of inventing native recovery.


### Float channel arithmetic in bank combination

Following the previously recovered bank-combination entry's arithmetic branches
identifies two helpers used for mode 0 and mode 4 when its arithmetic selector
is 2 and the weight is outside the near-one shortcut. The precise outer gate,
source-swapping option, type exclusion mask and other arithmetic selectors are
not implemented by this new numerical API. It receives the actual first and
second helper operands; callers must not assume those always equal the original
bank-entry argument order.

`reference.animation_channels.combine_float_channel` reconstructs two descriptor
kinds. The native dispatch uses the low type nibble; this API expects the decoded
kind, rather than an entire descriptor word. The observed formulas are:

| Descriptor kind | Mode 0 helper | Mode 4 helper |
| --- | --- | --- |
| 1, scalar float | first + weight * (second - first) | first + weight * (second - first) |
| 5, four float lanes | first + weight * (second - first) | first + weight * second |

Each subtraction, multiplication and addition rounds to float32 separately. No
weight clamp or quaternion normalization occurs in these branches. The mode-4
four-lane operation is additive, but this does not justify naming the entire
mode additive animation: its scalar branch still interpolates. Other descriptor
kinds include separate numerical paths and must not inherit these formulas.

The [160-case receipt](../../native/snow_host/float_channel_math_validation.json)
executes complete original helper calls for both kinds and both modes, with
synthetic nonoverlapping storage and uniformly broadcast weights. Weights zero,
one, half, negative half and 1.5 are included. Output bytes match the reference.
This does not validate outer dispatch, aliasing, nonuniform SIMD weight inputs,
other kinds, flag updates or scheduling of these writes. Finite input and shape
checks are authored inspection policy. The next join is the outer arithmetic
routing and its near-one shortcut, followed by the remaining typed formulas.


### Arithmetic near-one routing

`plan_arithmetic_channel_route` now exposes the selector-2 outer routing for
modes 0 and 4 over a supplied, already selected descriptor range. The native
comparison is `abs(float32(weight - 1)) <= float32(1e-5)`. It switches helper
families, rather than clamping the weight. Mode 0 outside that interval uses
first/second interpolation; inside it copies the second bank. Mode 4 outside
uses weighted combination and inside uses unweighted combination. In mode 4,
a zero swap control orders helper operands second/first; nonzero orders them
first/second. Mode 0 ignores that control. The planner uses a boolean API.

A set exclusion-mask bit skips the descriptor whose low type nibble names that
bit. High descriptor type bits do not affect selection. Mask zero enables all
selected descriptors. Mode-0 near-one copying may use a single range call or
one call per nonexcluded descriptor; the API reports per-descriptor effects.
It does not promise matching call granularity.

The [112-case routing receipt](../../native/snow_host/arithmetic_channel_route_validation.json)
executes original entry/filter/dispatch instructions with arithmetic and copy
helpers intercepted. It stops before the common tail. Tests cover both modes,
source orders, exclusions, high type bits and adjacent representable weights
on either side of the tolerance. This proves routing independently from the
separate numerical helper receipts, not a fully joined bank update.

Static inspection of the mode-4 unweighted helper shows addition for kinds 1
and 5 and quaternion multiplication for kind 6. Thus the scalar near-one route
is not simply the continuous limit of its weighted interpolation formula.
Those unweighted formulas still need dedicated instruction comparisons; the
numerical `combine_float_channel` API models only the weighted helpers and must
not be used directly as the entire outer mode-4 operation. NaN weights, source
storage aliasing, group-range integration, other arithmetic selectors and common
tail effects remain outside this routing proof.


### Unweighted typed channel combination

The near-one mode-4 helper is now implemented as
`combine_unweighted_channel(first, second, previous, kind)`. This completes its
local low-nibble dispatch, including the branches that leave storage untouched:

| Low type nibble | Operation |
| --- | --- |
| 0 | uint8 addition modulo 256 |
| 1 | Scalar float32 addition |
| 5 | Four independent float32 additions |
| 6 | XYZW Hamilton product, first quaternion times second |
| All others | No write; previous destination retained |

Quaternion products and sequential sums round separately to float32. Neither
input nor output quaternion is normalized. Source order therefore matters,
especially because the outer mode-4 route can swap sources. A no-write branch
must not be replaced with zeroing, copying either input or generic interpolation.
The value API returns the supplied previous destination for these branches;
this return convention and input validation are authored inspection choices.

The [320-case receipt](../../native/snow_host/unweighted_channel_validation.json)
executes the complete original helper without intercepted calls. All 16 low
nibbles are exercised with high type bits set and synthetic independent storage.
Destination bytes match the reference, including byte wrap, non-unit quaternion
products and retained destination values. Dedicated tests also check quaternion
noncommutativity. This upgrades the prior static-only unweighted formulas to
bounded instruction-emulation evidence. It does not yet validate source/destination
aliasing, outer-route-plus-helper integration, common-tail bank flags, or scheduling.
The weighted kind-6 rotation path remains a separate unresolved formula.


### Joined float bank update

`combine_float_channel_batch` joins the recovered selector-2 route and numerical
helpers for supplied kind-1 and kind-5 channels. It retains excluded destination
values and applies native source order, including mode-4 swapping. The input
range is already selected and values represent separate storage; it does not
model aliases, metadata reads, supplemental records or status flags.

The [80-case joined receipt](../../native/snow_host/joined_float_bank_validation.json)
executes the complete original bank-combination entry, original arithmetic/copy
helpers and shared tail without interceptions. Synthetic banks have separate
storage, matching metadata, all-range selection and empty supplemental arrays.
Both modes, swap controls, exclusions and weights around the near-one boundary
match the composed API byte for byte. For example, mode-4 scalar inputs 10 and
20 yield 30 at weight 1 through the unweighted helper; just outside the near-one
interval the weighted helper interpolates using the selected source order.
That discontinuity is preserved, not smoothed as an authored correction.

Zero-initialized destination flags finish either zero or with bit 27 set in
these fixtures, depending on the executed path. The receipt retains flags as
observations; the value API makes no promise to reconstruct them. Do not infer
an unconditional dirty-bit write from successful arithmetic output.

The common tail is a separate routine operating on the bank's array at +0x1a0,
count at +0x1aa and mask at +0x1ac. Static inspection shows mode-dependent copy
selection and, for mode 0, count checks and 48-byte records with identifier
comparisons, vector interpolation and another rotation helper. Mode 4 bypasses
those inspected tail operations. Record semantics, nonempty-tail behavior and
its caller relationships remain open. The empty-tail executions above are not
validation of that separate record system. Next work should decode that tail
and weighted quaternion channels before claiming a complete bank combination.


### Equal-count supplemental pose records

The mode-0 supplemental tail now has an executable adapter for equal source
counts. Destination count must equal that common count or the routine returns
without writes. Records are paired by index, not searched by identifier. Only
matching source identifiers permit an update. The destination identifier and
other metadata are not rewritten or compared in this branch.

```text
if destination.count != first.count: return
for i in source indices:
    if first[i].id != second[i].id: continue
    destination[i].vector = first[i].vector + weight * (second[i].vector - first[i].vector)
    destination[i].rotation = rotation_service(first[i].rotation, second[i].rotation, weight)
```

The four-lane vector arithmetic rounds each operation to float32; weight is not
clamped. Vector storage precedes the rotation call. The adapter accepts an
explicit rotation service rather than guessing its interpolation rule. Immutable
returned records and shape checks are authored API choices, not native behavior.
The inspected loop increments a byte counter against a uint16 count; the adapter
refuses more than 255 records. This is an inspection guard, not proof that native
metadata can reach an invalid count or that a live infinite loop occurs.

The [36-case receipt](../../native/snow_host/supplemental_equal_validation.json)
executes the original complete mode-0 tail with equal source counts, intercepting
only the rotation helper with a fixed synthetic result. It covers zero/nonzero
counts, mismatching destination counts, matching/mismatching source IDs and
weights outside 0..1. Vector bytes, retained identifiers/padding, callback order
and callback arguments match the adapter. The destination ID deliberately differs
from both source IDs in the fixtures. This establishes local update gating, not
record semantics, rotation fidelity, unequal-source behavior, aliases or live
animation ownership. Unequal-source branches and the rotation helper remain
explicit next work.


### Supplemental rotation branch selection

The equal-count tail's rotation helper is now partially reconstructed in
`blend_supplemental_rotation`. Its float32 dot-product grouping is
`(x_product + z_product) + (y_product + w_product)` up to commuted addition.
It does not normalize inputs before selecting a branch:

1. If `abs(float32(abs(dot)-1)) <= 2^-23`, return the first quaternion unchanged,
   independently of weight. This includes opposite-sign equivalent unit inputs.
2. Otherwise, if dot is below float32 `0.9893559813499451`, call another rotation
   helper. Negate the second quaternion when dot is negative before that call.
3. Otherwise compute `(1-weight)*first + weight*second`, then normalize using
   reciprocal-square-root estimation followed by one Newton refinement.

Every product and addition in the API follows inspected float32 order. It takes
an explicit reciprocal-square-root seed service because native approximation
bits need not equal a host language's exact square-root expression. The other
rotation helper remains an explicit fallback service; this is not a complete
spherical interpolation implementation.

The [69-case receipt](../../native/snow_host/supplemental_rotation_validation.json)
executes the original dispatcher and normalized-linear instructions, recording
emulator reciprocal-square-root seeds. Only the fallback call is intercepted
with a synthetic output. Fixtures include identical, opposite, nearby and more
separated rotations, non-unit values, and weights outside 0..1. Output bytes and
fallback inputs match with the recorded seeds. The expanded receipt includes adjacent float32 values at the dispatcher thresholds.
Cross-hardware approximation equivalence remains unvalidated.

A non-unit fixture with first w=1, second w=2 and weight=-1 produces a zero
normalization candidate. The portable API rejects that case as authored policy;
it is excluded from the 69-case equivalence receipt. Native degenerate output
is not modeled, and this refusal must not be described as recovered behavior.
The next dependency is the fallback helper's arithmetic and boundary tests,
followed by replacing the equal-record test's synthetic rotation service with
this implementation under an explicit seed/fallback policy.


### Polynomial rotation fallback

`polynomial_rotation_blend` reconstructs the previously external fallback helper.
It uses a polynomial-adjusted normalized interpolation, not exact trigonometric
SLERP. For input quaternions a and b, signed dot d and weight t, the real-number
summary of its coefficient calculation is:

```text
k = (1 - 0.8227968811988831*d)^2 * 0.5854921936988831
P(x) = x * ((2*x - 3)*x*k + 1 + k)
u = P(t) if t <= 0.5 else 1 - P(1-t)
b_adjusted = -b if d < 0 else b
candidate = a + u*(b_adjusted-a)
result = normalize(candidate)
```

The implementation preserves each float32 operation and the inspected dot/norm
sum grouping. Coefficient calculation uses the signed dot before hemisphere
adjustment. The outer dispatcher may already have flipped b before invoking this
helper, so direct-helper and dispatcher inputs must not be conflated. Normalization
uses a supplied reciprocal-square-root estimate and one Newton refinement.
There is no weight clamp. Finite/positive-length guards are authored policy.

The [160-case receipt](../../native/snow_host/polynomial_rotation_validation.json)
executes the entire helper without interceptions, recording emulator approximation
seeds. Synthetic unit quaternions span positive and negative dots; weights include
extrapolation, endpoints and adjacent float32 values around 0.5. All output bytes
match with the observed seeds. This does not prove every degenerate/nonfinite
input or cross-CPU approximation equivalence. The dispatcher receipt separately
expanded from 29 to 69 cases with adjacent values around its dot thresholds.

The fallback formula is now available for composition with the supplemental
record dispatcher. A joined record-update execution using both real rotation
helpers is still needed; the earlier equal-record receipt's stub remains labeled
as such. The weighted bank kind-6 path has similar instructions but has not yet
been proved interchangeable with this helper.


### Joined supplemental record evaluation

`evaluate_equal_supplemental_records` now composes the count/ID gates, vector
interpolation, rotation dispatcher and polynomial fallback. It requires only a
reciprocal-square-root seed service for approximation-sensitive normalization;
no rotation-output stub is used by this entry point. Supplying exact inverse
square roots is a possible authored policy, not a claim of native seed parity.

The [36-case joined receipt](../../native/snow_host/supplemental_joined_validation.json)
executes the complete original equal-source-count mode-0 tail and both rotation
helpers with no calls or instructions replaced. Passive instruction hooks record
normalization lengths and emulator seeds. Inputs exercise retained rotations,
normalized-linear and polynomial paths, negative-dot adjustment, skipped source
IDs, destination-count rejection, empty lists and extrapolation weights. All
record output bytes and unchanged metadata match the composed reference using
the observed seeds, with seed consumption checked in order.

This supersedes the need for a synthetic rotation service for the validated
nondegenerate equal-count path. The earlier stubbed receipt remains useful for
isolating call order. The proof still excludes unequal-source branches, aliases,
nonfinite/degenerate rotations, count overflow, actual record meanings and live
bank ownership. It also does not establish bit equivalence across host CPUs.
The next implementation gap is the unequal-source path that fades one selected
record list toward zero translation and identity rotation.


### Unequal-count supplemental source selection

`evaluate_supplemental_records` extends the joined mode-0 evaluator to unequal
source counts. It first requires destination count to equal the maximum source
count. Otherwise nothing is written. The chosen source is the first list whenever
it is nonempty; only an empty first list selects the second. This is not a
longest-list selection or a union of identifiers.

For selected first-list records the fade parameter is weight. For selected
second-list records it is float32(1-weight). Each vector is evaluated as
`vector + fade * (zero-vector)` with separate float32 operations. Each rotation
uses the recovered rotation logic toward identity, including retain-first,
normalized-linear and polynomial branches. No identifier comparison or metadata
copy occurs in this branch. Destination metadata is preserved. If both lists
are nonempty and the first is shorter, only its number of records is updated;
the remaining destination tail is untouched.

The [48-case receipt](../../native/snow_host/supplemental_unequal_validation.json)
executes the complete original mode-0 tail, including inline rotation math and
the original fallback helper. No calls or instructions are replaced. Passive
hooks record emulator normalization seeds. Source counts 0/4, 4/0, 1/4 and 4/1,
destination-count rejection, differing IDs and extrapolation weights are tested.
All output bytes, retained metadata and ordered seed inputs match the composed
reference. A separate regression checks that a short first list leaves the
longer destination tail unchanged.

This closes the previously missing unequal-source local branch for the tested
finite, nondegenerate, nonaliasing domain. It does not identify the records'
gameplay role, establish live count invariants, reproduce unsupported degenerate
normalization or guarantee cross-hardware seed equivalence. Copy modes 1/2/3
in the supplemental tail and aliasing still need their own integration proof.


### Supplemental copy gating

`plan_supplemental_copy` reconstructs the tail's modes 1/2/3. Mode 2 selects the
first bank and mode 3 selects the second. Mode 1 selects first below float32 0.5
and second at or above it. Selection precedes validation: an empty selected bank
does not fall back to the other bank. Copy is requested only when selected count
is nonzero, selected mask intersects the requested mask, and destination is not
the same bank object. The identity check compares embedded list-object addresses;
it does not compare their backing-storage pointers or exclude overlapping arrays.
A failed gate retains the existing destination, rather than clearing it.

The [162-case receipt](../../native/snow_host/supplemental_copy_gate_validation.json)
executes the original copy-mode tail with the copy service intercepted. It covers
both sides and equality at the half-weight boundary, empty banks, intersecting
and disjoint masks, and destination identity with either source. The planner's
copy requests match. Its reason labels are explanatory API output; the receipt
observes copy/no-copy and source, not a native reason code. Nonfinite weights are
rejected by authored policy and excluded from equivalence claims.

Static inspection of the selected copy helper shows destination count reset to
zero, a capacity/allocation service called for the source count with alignment
16, then ordered 48-byte source records passed to an append helper. Therefore
this is a container replacement operation, not a proven single memcpy. Allocation,
append behavior, failure recovery and overlapping storage remain to be decoded
and tested. The gate receipt does not execute that service. Metadata mask updates
must not be inferred merely because records were selected for copying.


### Supplemental copy with retained capacity

`copy_supplemental_storage` models the copy helper when existing destination
capacity is sufficient. The native container count resets to zero, reserve returns
without allocating, and append increments the count before copying each 48-byte
record in three ordered 16-byte load/store pairs. Capacity uses the low 14 bits
of its control word. The destination mask at list +0x0c is not copied from the
source in this path. Records beyond the new count are not cleared.

The [32-case receipt](../../native/snow_host/supplemental_copy_storage_validation.json)
executes the complete copy helper, reserve early-return and append callees with
no interceptions. Synthetic counts 0/1/3/8, previous counts 0/2, identical backing
buffers, forward overlaps of 16/48 bytes and separated buffers are included.
All storage bytes, final count, retained capacity and destination mask match.
Container objects remain distinct, so the outer same-object gate would not
suppress these shared-buffer cases. A forward overlap is not equivalent to
copying a snapshot: earlier writes can feed subsequent loads within a record.
The public fixture hex contains generated synthetic data, not game memory.

The API rejects inadequate capacity rather than inventing an allocator. Static
append inspection requests growth by four slots below capacity 24, otherwise
by floor(capacity/3), capped at 0x3fff. Reserve can allocate, relocate existing
records and call a storage-replacement service. These allocation/release paths,
failure handling and maximum-capacity append behavior remain unvalidated.
The existing-capacity proof must not be extended to them or to native ownership
safety. Immutable output and bounds/alignment guards are authored API choices.


### Supplemental reserve ownership and relocation

`plan_supplemental_reserve` expresses reserve selection and successful replacement
metadata. Capacity is control-word bits 0..13, two flags occupy bits 14..15, and
count is bits 16..31. Without force, sufficient capacity returns unchanged.
Otherwise allocation requests 48-byte elements, the original routine relocates
count records in order, then replaces storage while retaining count.

Old nonnull storage is passed to release services only when old bit 15 is clear.
Bit 14 does not suppress that release. In this reserve caller all replacement
policy arguments are true, so the replacement control word clears both flags,
sets the requested capacity and preserves count. The separate mask at list
+0x0c remains unchanged. These are observed bit roles; the planner does not
assert a broader ownership type system or allocator provenance.

The [64-case receipt](../../native/snow_host/supplemental_reserve_validation.json)
executes reserve, actual record relocation and replacement metadata instructions.
Allocator success and release services are intercepted; the native heap is not
used. Cases cover empty/nonempty storage, sufficient/insufficient capacity,
forced replacement including bounded shrink, and all combinations of the two
control flags. Event ordering, copied bytes, pointer selection, count/capacity
and retained mask match. Real release side effects, allocation failure, forced
capacity below count and same-allocation allocator results remain untested.

This closes the successful local reserve/replace policy with supplied allocation
services. It is not proof that arbitrary mod-side allocation is compatible with
the game heap. Integration of outer copy gates with a growing destination and
runtime-owned allocation still requires separate validation.


### Growing supplemental copy integration

`plan_supplemental_rebuild` joins count reset with reserve/replacement and final
append count. Copy clears the destination count before reserve. Consequently,
when growth allocates new storage, reserve sees zero live records and relocates
none of the old destination records. It releases old storage according to the
old ownership flag, replaces control metadata, then appends source records.
This differs from calling reserve directly on a nonempty destination.

For sufficient capacity, the pointer and low control flags are retained while
count becomes the source count. For growth, requested capacity equals source
count and successful replacement clears the two control flags as previously
recovered. The separate destination mask remains unchanged. Neither path clears
storage beyond the new count; old logical records have been discarded even if
their bytes remain in retained storage. The inspection planner assumes allocator
success and a distinct source container, with counts bounded to 14-bit capacity.

The [48-case receipt](../../native/snow_host/supplemental_rebuild_validation.json)
executes the complete copy/reserve/replacement/append chain. Only successful
allocation and release services are supplied. Native count reset is observed at
the allocation boundary; source bytes, final pointer/control word, mask and
untouched trailing storage are checked. Cases cover empty/nonempty sources,
previous destination counts, retained/growing capacities and all low flag
combinations. There is no record-relocation or append stub in this receipt.
Real heap side effects, failures and source storage freed by replacement remain
unvalidated. This integration must not be treated as an allocator suitable for
in-process mods without a proven runtime-owned service boundary.


### Weighted quaternion bank channels

`combine_rotation_channel` reconstructs descriptor kind 6 for both weighted
helper families. Mode 0 calls the previously decoded supplemental rotation
dispatcher on first/second with the supplied weight. Mode 4 computes a polynomial
normalized blend from identity to the second quaternion, then takes the Hamilton
product of the first quaternion and that weighted result, in that order.

```text
weighted mode 0: rotation_dispatch(first, second, weight)
weighted mode 4: first * polynomial_rotation_blend(identity, second, weight)
```

The API preserves the helper arithmetic by composing the independently recovered
functions, with explicit reciprocal-square-root seeds. Mode 4 does not normalize
the final product after multiplication. The outer near-one route bypasses this
weighted helper and uses the unweighted product instead; source swapping also
belongs to the outer route. Callers must not use this weighted API as the whole
bank-combination operation.

The [160-case receipt](../../native/snow_host/weighted_rotation_channel_validation.json)
executes complete original kind-6 helpers for both modes, including their original
callees, without replacements. Synthetic unit quaternion inputs cover both dot
signs, endpoints, extrapolation weights and adjacent values around half weight.
Output bytes and ordered normalization inputs match the composed reference with
observed emulator seeds. This closes the earlier weighted kind-6 local formula
gap for the tested domain. It does not validate nonfinite/degenerate inputs,
aliasing, cross-CPU seed equivalence or full outer-route integration. The next
join is a mixed scalar/vector/quaternion bank update with source swapping and
near-one dispatch exercised together.


### Joined mixed numeric bank update

`combine_numeric_channel_batch` now joins scalar, four-lane vector and quaternion
channels, kinds 1/5/6, under selector-2 mode-0/4 routing. The float-only API remains
a compatibility wrapper. Exclusions preserve prior values. Near-one mode 0 copies
the selected source; near-one mode 4 uses unweighted operations; other cases use
the recovered weighted helpers. Source swaps happen before numerical dispatch.
A normalization seed service is required for an executed weighted quaternion
channel, not for excluded or copied channels. No exact-sqrt substitute is chosen
silently.

The [100-case joined receipt](../../native/snow_host/joined_numeric_bank_validation.json)
executes the complete original bank entry, all selected original numerical
callees, and empty-supplemental tail. No calls or instructions are replaced.
Fixtures combine three channel types with both modes, source order controls,
type exclusions and float32 near-one boundaries. All output bytes and ordered
normalization inputs match the composed API with observed emulator seeds.
Destination flags remain separately recorded, outside the value API's contract.

This is an integrated mixed-channel proof for a selected descriptor range and
separate storage. It does not yet cover nonempty supplemental records in the
same bank-entry execution, all typed channels, group-range integration, aliased
banks or native scheduling. Kind-6 local arithmetic is now connected to its outer
routing rather than supported only by isolated-helper comparisons.


### Mixed channels with supplemental evaluation

`evaluate_numeric_pose_bank` composes the recovered numeric channel batch and
supplemental evaluator for selector-2 modes 0/4. Numeric channels execute first.
Mode 0 then evaluates supplemental records with the original first/second source
order and weight; numeric source swapping does not reorder that tail. Mode 4
leaves the supplemental destination unchanged. Channel-type exclusions apply
to the numeric portion, not to the subsequent supplemental update.

The [100-case nonempty-bank receipt](../../native/snow_host/joined_pose_bank_validation.json)
executes the complete original entry and callees without replacing instructions
or calls. Synthetic scalar/vector/quaternion channels coexist with a nonempty
supplemental record requiring rotation interpolation. Both modes, swaps,
exclusions and near-one boundaries are covered. Numeric bytes, supplemental
bytes, preserved record metadata and normalization-seed consumption match the
composed API. In particular, excluding all numeric kinds does not suppress the
mode-0 supplemental update, while mode 4 retains it even when numeric outputs
change. Normalization uses observed emulator seeds for this comparison.

The API is an inspection/value evaluator, not a live engine callback. It assumes
separate source/destination storage and a preselected descriptor range. This
receipt joins the equal-count supplemental path; the unequal-count evaluator
has separate native evidence but is not exercised in this same entry fixture.
Other arithmetic selectors/types, group selection, status flags, live scheduling
and cross-hardware approximation behavior remain explicit gaps.


### Numeric bank status is path dependent

`evaluate_numeric_pose_bank` now accepts an initial uint32 status and returns
`flags`, using `numeric_bank_status_after` for the recovered selector-2 mode-0/4
path. Mode 0 near one sets bit 27 only when at least one nonexcluded numeric
channel is copied. An empty range or an all-excluded range does not set it.
All other validated arithmetic paths preserve status. In particular, numeric
arithmetic and supplemental record writes can occur without setting this bit.
The name and consumers of the flag remain unproved; it is not a universal
changed-pose indicator.

This copy helper differs from the earlier typed-copy helper used in entry modes
1/2/3, which sets bit 27 even for its empty range. Do not apply the new rule to
those modes. The original near-one helper returns before its flag write on an
empty range. For a nonzero exclusion mask, it is called only for selected
individual records, so an all-excluded list never reaches that write.

The [48-case complete-entry receipt](../../native/snow_host/numeric_bank_status_validation.json)
executes original arithmetic, copy and nonempty supplemental paths without
replaced calls. It varies initial status, empty/nonempty descriptor ranges,
exclusions, both modes and near-one selection. Status, numeric output and
supplemental output match the composed reference with captured normalization
seeds. This supersedes the earlier status-observation-only limitation for this
specific selector/mode domain. Other selectors, callbacks, concurrent writers
and the flag's higher-level meaning remain outside the proof.


### Grouped numeric bank evaluation

`evaluate_numeric_pose_bank` now accepts `group_mask`, `groups` and
`range_selector`. Defaults preserve the full-table behavior. It reuses the
recovered shared range-selection prefix: 0xffff selects all descriptors;
otherwise the highest set bit selects a group row, with zero selecting row zero.
A multibit mask does not union rows. Each row contains a first index and six
counts; `range_selector` chooses the count. This range selector is distinct from
the arithmetic selector, which remains fixed at 2 in this evaluator.

The evaluator retains channels outside the selected range and reports absolute
processed indices plus the selected range. Type exclusions apply within that
range. Mode-0 supplemental evaluation still follows afterward, including when
the numeric range is empty. This extends the earlier preselected-range-only API.
The group metadata is supplied; its resource producer and authored group names
remain unknown.

The [48-case grouped receipt](../../native/snow_host/grouped_pose_bank_validation.json)
executes complete original entries with synthetic group metadata, mixed channel
types and nonempty supplemental records. Zero, multibit and single-bit masks,
empty/nonempty selected ranges, two count selectors, both modes, near-one routing
and quaternion exclusion are covered. Original helpers execute without replacements;
normalization seeds are recorded for the portable comparison. Full destination
channels, status and supplemental records match. The six-count layout has earlier
copy-route evidence; this joined receipt does not exhaust every selector or
metadata mismatch. First/destination metadata agree in the fixtures; distinct
schemas, aliases and live publication remain unvalidated.


### Aliased float bank storage

`evaluate_float_bank_storage` adds an ordered shared-storage evaluator for
selector-2 kinds 1/5. Unlike the separate-value batch API, it reads each channel's
operands after previous channel writes. Descriptor offsets and logical bank
bases refer to one supplied synthetic byte buffer. Within the tested scalar and
four-lane helpers, operands are read before that channel's result is stored.
The near-one copy branch moves bytes without converting through Python floats.

The [16-case receipt](../../native/snow_host/aliased_float_bank_validation.json)
executes complete original entries with distinct bank objects but shared,
overlapping or separated backing storage. Both modes and weighted/near-one
routes are covered. Destination equal to the first source, one vector ahead of
it, equal to the second source and separated storage are tested. All bytes and
status match with original helpers and no interceptions. A dedicated regression
shows a prior vector write becoming the next descriptor's source input; a
snapshot of all source channels would produce a different result.

This extends alias evidence for scalar/vector arithmetic only. Quaternion
aliasing, overlap between numeric and supplemental regions, metadata aliases,
grouped alias combinations and concurrent readers remain unvalidated. Bounds,
alignment checks and immutable API output are authored policies. Fixture hex
is synthetic data, not an original memory dump. The JSON value testbench remains
explicitly nonaliasing; this separate byte-storage API must be selected when
modeling these overlap effects.


### Outer wrappers expand group masks

Tracing direct callers establishes an important API-layer distinction. The
inner bank entry chooses the highest set bit of an input mask. Its mode-0 and
mode-4 wrappers instead expand a nonsentinel mask into ascending single-bit
calls, iterating up to the first bank metadata's uint16 group count. Therefore
mask 3 at the wrapper produces calls for 1 and 2, while mask 3 passed directly
to the inner evaluator selects only group row 1. Zero produces no wrapper calls;
0xffff bypasses iteration and makes one full-table call even with zero groups.
Earlier highest-bit statements describe the inner entry, not these wrappers.

`plan_bank_group_calls` emits the recovered argument sequence with explicit
`arithmetic_selector=2`. The mode-0 wrapper fixes mode 0 and swap-control integer
2; swapping has no effect in the decoded mode-0 inner route. The mode-4 wrapper
fixes mode 4 and forwards a caller-provided swap control, represented as a boolean
in this API. Both forward weight, range selector and type exclusion mask.
The API bounds group count to 16 as authored inspection policy; native shift
behavior at larger counts and metadata invariants remain unproved.

The [80-case wrapper receipt](../../native/snow_host/bank_group_wrapper_validation.json)
executes complete original wrappers and intercepts only the inner entry to log
arguments. Stable metadata counts 0/1/3/16, zero/single/multiple/sentinel masks
and swap controls match the planner. It does not execute the inner entry in
this receipt or prove the upstream operation's authored name. The native loop
rereads metadata after inner calls, so a static plan is valid only for stable
metadata. Multiple calls can also run the supplemental tail multiple times;
flattening them into one merged descriptor range would erase that ordering.

Next integration should execute this ordered call sequence through the mixed
bank evaluator with explicit destination state carried between calls, then trace
the higher callers that choose masks and weights. The existing JSON testbench
still invokes one inner entry per case; it must not silently reinterpret a
multibit case mask as the new outer wrapper.


### Complete grouped wrapper evaluation

`evaluate_grouped_pose_bank` executes the recovered mask-expansion plan through
the mixed numeric/supplemental evaluator in order. Destination channels, records
and status carry forward between calls; source values remain separate supplied
arrays. Zero mask makes no inner calls and retains destination state. The
full-table sentinel makes one call. Ordinary masks can trigger multiple
supplemental passes, preserving normalization-service call order.

The [64-case wrapper receipt](../../native/snow_host/grouped_wrapper_pose_validation.json)
executes complete original mode-0/4 wrappers, inner entries, numeric helpers and
nonempty supplemental tails without replacing calls or instructions. Synthetic
stable metadata contains three groups. Zero, multibit, single-bit and full-table
masks, two range selectors, exclusions and weighted/near-one behavior match the
composed API in full output bytes, status and normalization inputs. This joins
rather than merely replays the previously isolated wrapper and entry findings.
The supplied seed sequence remains emulator-specific evidence.

The JSON testbench exposes this explicitly with case `entry: "group_wrapper"`;
`entry: "inner"` remains the default. Wrapper inputs add `group_count` alongside
group metadata. Output lists the executed group calls. A multibit mask is never
silently reinterpreted between these two entry choices. This stable-metadata
value composition does not model aliasing, metadata changes inside callbacks,
other wrapper families, or live animation-graph scheduling.


### Pose operation selects blend family

One higher caller now connects operation state to the recovered mode-0/4
wrappers. `plan_pose_operation_route` expresses its dispatch prefix with a
supplied nonnull component and stable input observations. It intersects an
operation mask with the requested mask before routing. If operation kind's low
three bits equal 5 and its two required pointers plus component are present,
it selects a separate special service. That service is not decoded here.

Otherwise equal source-kind bytes select mode 0; differing bytes select mode 4.
For a nonzero first kind and zero second kind, the caller writes float32
`1-weight` back into the operation and sends swap control zero. Other differing
pairs retain weight and send swap control one. This is an actual stored-state
mutation, not merely a temporary complement passed to interpolation. No weight
clamp occurs. Both wrappers receive zero type-exclusion mask and range selector
`(component_flags >> 3) & 7`. Values 6/7 can emerge synthetically; the existing
bounded group-range API rejects them rather than pretending a seventh/eighth
count field is known. Valid runtime constraints on those values remain open.

The [80-case dispatch receipt](../../native/snow_host/pose_operation_route_validation.json)
executes original prefix branches and weight stores, with component lookup and
downstream services intercepted. It stops before the keyed operation tail.
Equal/different byte pairs, complement direction, out-of-range weights, special
readiness and flag extraction match the planner. Kind 2 versus kind 1 is included
to avoid silently treating these byte comparisons as boolean equality.

The operation's semantic name and source-kind meanings are not established.
The component is obtained through an existing lookup; its lifetime is not proved
by this fixture. The caller continues with resource-key lookup and another
operation-specific tail after blending. The next useful trace is its upstream
caller and this remaining tail, preserving the complemented stored weight when
building a replay or a full operation adapter.


### Pose command record reaches blend routing

The direct caller of the operation prefix is a command-record dispatcher.
Records advance by 48 bytes and have a command kind at +0x28. Its type-1 case
passes the operation pointer at +0, destination at +8, first bank at +0x18,
second bank at +0x20 and uint16 requested mask at +0x10. The two source-kind
arguments are respectively bits 0 and 1 of the byte at +0x12. Their semantic
names remain unknown, but this caller constrains them to boolean values.
Other possible callers were not excluded by this local trace.

`pose_command_source_kinds` exposes that bit decode. The
[256-case receipt](../../native/snow_host/pose_command_flags_validation.json)
executes the original dispatch slice through the operation call boundary for
every uint8 flag value, checking bit arguments, receiver/source argument wiring
and mask. It stops before the operation executes. This links command decoding
to the separately tested routing planner; it is not a full command-loop or
command-production proof. Type-1 bits 00/11 select mode 0, 01 complements the
stored weight and selects mode 4 with swap zero, and 10 selects mode 4 with
swap one, absent the special-operation path.

### Post-blend operation tail and provider flag lead

Static inspection after blend dispatch shows an optional lookup of numeric key
0x530ec1cb. A present descriptor supplies a group-bit index; if it intersects the
operation's effective mask, another helper is called with the current stored
weight. The key's authored meaning and that helper's formula remain unproved.
The operation then ORs its completed-mask field with the effective mask and
passes noncached first/second banks to another manager helper.

That manager helper scans 16-byte entries for the supplied bank. On a match,
it sets bank flag bit 26 and clears selected bits of the entry mask while
preserving bit 15. It may also clear supplemental masks or replace supplemental
storage depending on additional fields. These are static observations, not yet
instruction-emulation proof of this tail. Bit 26 is the same field tested by the
provider conversion bypass, giving a concrete writer/consumer lead; it does not
by itself prove world-space semantics, final pose readiness or safe publication.
Next work should decode and validate this matched-entry transition, then trace
the command producer to establish scheduling and source-kind meaning.


### Manager group release sets provider conversion flag

`release_pose_bank_groups` reconstructs the manager's first-match transition.
It scans entries by bank identity and changes only the first match, even if the
same bank appears again. A missing match produces no effects. On a match it:

```text
bank.flags |= 1 << 26
entry.mask &= (~requested_mask & 0xffff) | 0x8000
if bank.supplemental_mask & requested_mask and bank.supplemental_counter != 0:
    bank.supplemental_mask &= ~requested_mask & 0xffff
    bank.supplemental_counter -= 1
    if bank.supplemental_counter == 0: reset supplemental storage
```

Bit 15 of the entry mask survives this clearing. The supplemental mask does not
have that preservation rule. The counter decrements once per successful gate,
not once per requested bit. The reset calls the previously decoded replacement
service with null storage, zero count and zero capacity. The field's precise
producer and meaning remain unknown, so it is called a counter rather than a
reference count. Flag bit 26 is set even when requested mask is zero or no
supplemental update follows.

The [72-case receipt](../../native/snow_host/bank_group_release_validation.json)
executes the complete original manager routine and actual storage-reset service
without interceptions. Synthetic storage has the borrowed flag set so no external
release service is invoked. Cases cover duplicate/no matching entries, zero and
multibit requests, intersecting/disjoint masks, and counters 0/1/2/7. Entry masks,
bank flags, supplemental mask/counter and reset pointer/control bytes match the
portable effect planner. Owned-storage deallocation, concurrent access and entry
insertion/removal remain outside this proof.

This upgrades the earlier static bit-26 writer lead to instruction-emulation
evidence. It connects a post-operation manager transition to the provider's
conversion-bypass field. It still does not prove the pose's absolute coordinate
frame, lifetime, publication readiness or the counter's ownership semantics.
A full operation-tail integration should preserve this transition after blend
and any keyed helper, including repeated calls for uncached source banks.


### Keyed helper blends three auxiliary poses

`reference.animation_channels.blend_auxiliary_pose_triplet` reconstructs a
post-blend keyed helper. Each supplied bank has three four-lane vector/quaternion
pairs, three scalar weights and flags. Names are authored; the poses' coordinate
frame, units, gameplay role and update cadence remain unknown. This is not yet
identified as root motion, IK, landing absorption or a specific bone group.

```text
if any bank pointer is null: retain destination
left = bool(first.flags & requested_mask)
right = bool(second.flags & requested_mask)
if neither: retain destination
otherwise: destination.flags |= requested_mask
if both:
    destination.weights = [1, 1, 1]
    for each of three records:
        vector = first.vector + weight * (second.vector - first.vector)
        rotation = external_rotation(first.rotation, second.rotation, weight)
else:
    copy all three pose records from the available source
    scale = 1 - weight for first, or weight for second
    destination.weights = clamp(source.weights * scale, 0, 1)
```

Availability means any intersecting bit, not every requested bit. Vector
arithmetic preserves individual float32 subtraction, multiplication and addition.
Blend weight itself is not clamped. Rotation uses a distinct native service;
its remaining fallback is unresolved and is an explicit callback in this API.
It must not silently use the supplemental polynomial blend already recovered.

The [32-case receipt](../../native/snow_host/auxiliary_triplet_validation.json)
executes the complete original helper in instruction emulation with only the
rotation service intercepted. It compares all three records, scalar weights,
flags and ordered rotation arguments. Synthetic cases cover absent, single and
dual sources, partial mask intersections and weights below zero and above one.
This establishes gates and arithmetic, not rotation output or live scheduling.
Null handling is statically recovered and separately tested in the reference;
these native fixtures use nonnull banks. Separate storage is assumed.

Shape, uint32 flag and finite-input checks are authored interface policy. Native
NaN, signed-zero clamp behavior, overlapping banks and external rotation failures
are outside the validated contract. The next step is decoding that distinct
rotation fallback, then composing this helper with the higher operation tail and
its manager release transitions.


### Auxiliary rotation uses a spherical fallback

The distinct auxiliary fallback now has a recovered formula in
`reference.supplemental_pose_records.spherical_auxiliary_rotation`. This
supersedes the preceding section's unresolved-fallback statement, but the outer
rotation dispatcher and three-record helper are not yet composed with it.
For finite inputs its computation is:

```text
d = pairwise_float32_dot(first, second)
if d <= -1 or d >= 1: return second
theta = acos(abs(d))
left = sin((1 - weight) * theta)
right = sin(theta * weight)
if d < 0: right = -right
if epsilon >= abs(theta): return second
inverse = 1 / sin(theta)
left *= inverse
right *= inverse
candidate = left * first + right * second
return normalize_with_rsqrt_and_one_Newton_refinement(candidate)
```

Every arithmetic stage rounds to float32. The dot reduction groups lanes as
`(a_y*b_y + a_w*b_w) + (a_x*b_x + a_z*b_z)`, not a sequential sum. The outer
caller supplies epsilon approximately `1e-5`. Weight is not clamped; negative
dot changes the second coefficient's sign. The small-angle return occurs after
the first two sine calls. Direct returns preserve the second input, including
its sign and magnitude, rather than normalizing or returning the first.

The [70-case receipt](../../native/snow_host/auxiliary_spherical_validation.json)
executes the original fallback and its math routines without replacing calls or
instructions. Observed math-call inputs/outputs and reciprocal-square-root seeds
are supplied to the portable comparison; this validates the formula and call
ordering without claiming Python libm or other CPUs produce identical bits.
The observed math outputs also agree with acos/sin within a small numerical
tolerance. Cases include negative/zero/positive dots, endpoints, a nonunit input,
extrapolation weights and an epsilon that forces the small-angle return.
Finite synthetic inputs and separate storage bound this evidence. It does not
establish live animation semantics, original clip availability or full graph
execution. The next integration must preserve the outer dispatcher's different
retain-first rule before entering this fallback.


### Complete auxiliary triplet evaluation

`evaluate_auxiliary_pose_triplet` joins the keyed helper to
`blend_auxiliary_rotation` and its recovered spherical fallback. The outer
rotation dispatcher first computes the pairwise float32 dot product:

```text
if abs(float32(abs(dot) - 1)) <= 2^-23: return first
if dot < float32(0.9893559813499451):
    return spherical_auxiliary_rotation(first, second, weight, float32(1e-5))
candidate = float32((1-weight)*first + weight*second)
return normalize_with_rsqrt_and_one_Newton_refinement(candidate)
```

Each product and sum rounds separately; the pseudocode's last arithmetic line is
abbreviated. Unlike the supplemental dispatcher, this dispatcher sends the
original second rotation to its fallback without pre-negating it. The fallback
handles negative dot through a signed sine coefficient. The outer retain-first
rule also precedes the fallback's direct-second domain checks. Reusing the
supplemental dispatcher would therefore erase relevant distinctions.

The [160-case joined receipt](../../native/snow_host/auxiliary_triplet_joined_validation.json)
executes the complete original keyed helper, rotation dispatcher, spherical
fallback and math routines with no calls or instructions replaced. All 112 bytes
of three pose records, three weights and flags match the reference. Recorded
math outputs and rsqrt seeds are consumed in order with exact argument matching.
Synthetic cases cover mask availability, first/second-only copying, negative
and zero dots, close rotations, antipodal/equal rotations and extrapolation.
The three records deliberately exercise different rotation branches together.

This supersedes the earlier triplet receipt's intercepted-rotation limitation.
It does not prove every floating-point threshold neighbor, arbitrary overlapping
storage, runtime ownership, cross-hardware math equivalence or gameplay meaning.
The remaining useful integration is the higher pose operation: blend-family
selection, keyed resource lookup, this triplet update and manager release in the
native order. Resource lookup and live command production remain unresolved.


### Pose operation tail orders keyed blend and releases

`plan_pose_operation_tail` exposes the original post-blend ordering with resource
lookup and effect services explicit. Its inputs include the effective mask
already intersected by the operation prefix, prior completion bits, resource
presence, lookup result and descriptor group byte. Cache matches represent
exact pointer comparisons in the original, not equivalence of pose contents.

```text
if component.resource exists:
    index = lookup(resource, key=0x530ec1cb)
    if index != 0xffff:
        group = resource.descriptors[index].group_byte
        if effective_mask & (1 << (group & 31)):
            blend_auxiliary_triplet(destination, first, second,
                                   current_operation_weight, effective_mask)
operation.completed_mask |= effective_mask
if first != operation.cached_first:
    manager.release_groups(first, effective_mask)
if second != operation.cached_second:
    manager.release_groups(second, effective_mask)
```

The register-form 32-bit bit-test wraps the group index modulo 32. This is an
instruction property, not evidence that out-of-range descriptor groups exist in
assets. Mask bits above 15 are absent. Both releases are independently gated and
ordered; do not deduplicate them merely because a future caller supplies the
same source twice. Even a zero effective mask reaches the completion update and
uncached release calls. The manager's already decoded bit-26 effect can therefore
matter even when no requested groups remain.

The [192-case receipt](../../native/snow_host/pose_operation_tail_validation.json)
executes the original tail through both release call sites, stopping before the
epilogue. Lookup, auxiliary blend and manager release are intercepted services.
It checks lookup key, blend source/destination arguments, release manager/mask,
effect ordering and completion-mask visibility at release. Cases cover resource
absence, failed lookup, cache matches and synthetic group-boundary probes.
This proves dispatch and ordering, not full service composition or atomicity.

The key's semantic name and resource producer remain unknown. No per-frame
completion or safe mod invocation is inferred from the completion mask alone.
Next integrate these calls with actual reconstructed service effects, including
sequential manager changes and potential source aliases, before exposing a
complete higher-operation evaluator.


### Shared source releases consume the mask once

`apply_pose_source_releases` composes the two post-operation manager calls against
one evolving manager/bank state. Logical source identities let the two call slots
refer to the same bank. The returned effects preserve both calls and report
storage reset separately; no native heap is manipulated by the reference API.

When both uncached sources are the same bank and its counter is positive, the
first matching release clears the requested supplemental-mask intersection and
decrements once. The second release observes those bits already clear, so it
cannot decrement again for the same request. It still performs the first-match
entry-mask operation and sets bit 26. With counter one, the first call resets
storage and the second leaves the reset state intact. With a zero requested
mask, neither call decrements, but both still reach the manager's flag update.
This is mask-gated behavior, not proof of a conventional reference count.

The [72-case receipt](../../native/snow_host/shared_source_release_validation.json)
executes the original operation tail and actual manager/reset routines without
replacing calls or instructions. Cases include shared/distinct source banks,
independent cache gates, duplicate manager entries, zero/nonzero masks and
counters zero/one/two. Manager masks, source flags, supplemental masks/counters,
reset storage metadata and operation completion bits are compared. Borrowed
storage avoids external deallocation. The keyed resource is absent in these
fixtures, so this does not yet join the auxiliary blend to the release path.

The public adapter deep-copies state to model ordered effects reproducibly.
That is authored inspection policy, not evidence of an atomic native operation.
Concurrent mutation, owned-storage deallocation, destination/source aliasing
through the preceding blend and resource lookup remain outside this proof.


### Keyed blend and releases composed

`evaluate_pose_operation_tail` joins the supplied resource lookup result, keyed
auxiliary update, operation completion-mask write and ordered source releases.
Banks share one logical identity map, so first and second may reference the same
state. Destination/source aliasing is rejected as an authored domain boundary;
its full native overlap behavior has not been established. Updated bank state,
manager masks, ordered events and explicit storage-reset effects are returned.
The input state is preserved by the inspection API.

The [48-case integrated receipt](../../native/snow_host/pose_tail_joined_validation.json)
executes the original tail with actual auxiliary blend, rotation dispatcher,
spherical/math routines, manager releases and storage reset. Only resource lookup
is intercepted, supplying index zero. The descriptor selects group zero. Cases
vary shared/distinct sources, cache matches, zero/nonzero effective masks and
counters one/two. Pose bytes, scalar weights, flags, supplemental masks/counters,
manager masks, reset metadata and completion bits match the composed evaluator.
Recorded math-call results and rsqrt seeds preserve numerical evidence boundaries.
Borrowed storage avoids external deallocation; the tail epilogue is excluded.

This integrates the previously separate blend and release proofs. It remains a
post-blend tail, not the complete higher operation: the preceding general bank
blend, special route, resource producer and command scheduling are not included.
The resource key still has no established gameplay name. A useful next step is
to join the already reconstructed general blend for the ordinary route, retaining
the distinct special-service dependency and explicit source/destination limits.


### Ordinary pose operation composition

`evaluate_ordinary_pose_operation` connects source-kind routing, grouped numeric
and supplemental evaluation, the auxiliary tail and ordered manager effects.
The source-kind route selects mode 0 or 4 and may mutate weight to `1-weight`;
that resulting weight is used by both the general blend and the auxiliary tail.
The grouped blend's resulting destination flags are carried into the tail.
Source reset effects clear the reference's supplemental record lists. Native
storage ownership remains represented by effects, not executable deallocation.

The [96-case receipt](../../native/snow_host/ordinary_pose_operation_validation.json)
executes the complete original ordinary operation through return. Only component
lookup and keyed resource lookup are intercepted. Original grouped arithmetic,
auxiliary rotations/math, manager transitions and storage reset execute. Fixtures
cover equal and both unequal source-kind directions, weights 0.25 and 1, zero
and nonzero masks, independent cache matches and shared/distinct source banks.
Compared outputs include scalar/vector channel bytes, auxiliary poses/weights,
flags, manager and supplemental state, storage reset, completion bits and the
stored operation weight. Recorded math results and rsqrt seeds remain explicit.

This integrated receipt uses kinds 1/5 and empty supplemental arrays. Prior
component-level proofs cover wider channel/record domains, but they do not turn
this receipt into a full-operation proof for those combinations. The public
composition can evaluate supported numeric kinds and record branches; integrated
coverage for nonempty records and numeric quaternion channels remains open.
Destination/source aliasing is rejected. Metadata is stable, the component is
nonnull and storage is borrowed. The special route raises `NotImplementedError`
instead of selecting an ordinary substitute. Resource meaning, command producer,
concurrency and live invocation safety remain unresolved.


### Full ordinary operation with mixed channels and supplemental poses

The [96-case mixed-operation receipt](../../native/snow_host/ordinary_pose_mixed_validation.json)
extends full-operation evidence to scalar, vector and quaternion numeric channels
plus one nonempty supplemental record in each bank. Original supplemental
rotation, polynomial fallback, numeric quaternion composition and auxiliary
spherical rotation execute in the same invocation, followed by manager effects.
Component and resource lookups remain the only intercepted services.

The same routing/cache/source-sharing matrix as the preceding receipt is used.
Exact channel bytes and all auxiliary records are compared. Supplemental IDs,
padding, vectors and rotations are compared while retained; reset sources are
checked for null storage and zero control word. Destination supplemental ID and
padding survive the blend. Math service arguments/results and normalization
seeds are consumed in order across the entire operation. Source record lists in
the reference become empty only when the manager reports a storage reset.

This supersedes the preceding section's missing integrated coverage for numeric
quaternion channels and nonempty equal-count supplemental records. It does not
cover unequal record counts in the full operation, multiple groups, destination
aliasing, special service, lookup internals or live scheduling. The existing
component proofs for some of those domains remain separate evidence. No runtime
modding safety or original-engine equivalence follows from this emulator check.


### Pose resource lookup is an unsigned lower bound

`lookup_pose_resource(entries, key)` reconstructs the keyed descriptor lookup.
The resource provides a uint16 entry count and an array of eight-byte entries:
uint32 key, uint16 descriptor index, then two unused bytes. The search uses
unsigned key comparisons and lower-bound logic:

```text
start = 0; count = number_of_entries
while count > 0:
    half = count // 2
    middle = start + half
    if entries[middle].key < key:
        start = middle + 1
        count -= half + 1
    else:
        count = half
if start != number_of_entries and entries[start].key == key:
    return entries[start].descriptor_index
return 0xffff
```

Duplicate keys select the first matching entry. The returned descriptor index is
stored data, not the position in the lookup table. A stored index of `0xffff`
is indistinguishable from a miss to the caller. Native code trusts sortedness;
the portable API rejects unsorted and out-of-range values as authored guards.
The search does not establish how keys are generated or what the operation's
`0x530ec1cb` key names.

The [78-case lookup receipt](../../native/snow_host/pose_resource_lookup_validation.json)
executes the complete original search without replaced calls. Synthetic tables
cover empty/singleton inputs, duplicates, missing keys, unsigned high-bit values
and sentinel indices. The [96-case integrated receipt](../../native/snow_host/ordinary_pose_lookup_joined_validation.json)
then reruns the mixed ordinary operation with the actual lookup on a one-entry
synthetic table. Results and numerical observations match the preceding mixed
receipt exactly. Only component lookup remains intercepted in this new full
operation proof. Real resource construction, key naming and resource lifetime
remain unresolved. The high-level evaluator still accepts the lookup result;
callers may now derive that result from a supplied sorted table using this API.


### Ordinary operation executes without intercepted services

The component lookup at the ordinary operation's entry is the previously decoded
SkeletonComponent provider getter. It reads the operation's entity receiver,
loads the SkeletonComponent type descriptor and uses the entity-local cache.
A matching tag and valid cached slot return that component; index `0xfffe` forces
the existing virtual type-range search. This connection reuses the earlier
[provider binding evidence](#entity-provider-acquisition-cache), not a new assumed
meaning for an opaque lookup.

The [96-case unintercepted receipt](../../native/snow_host/ordinary_pose_unintercepted_validation.json)
executes the full ordinary operation with actual entity and SkeletonComponent
tables, native descriptor getter, cache resolver, forced-refresh search, resource
lookup, numeric/supplemental/auxiliary blends and manager reset. No calls or
instructions are replaced. Half the synthetic fixtures use a valid cached slot;
half force refresh and verify the resulting cache tag/index. The operation results
and math/normalization observations match the prior 96-case receipt exactly.

This removes all substituted callees from this particular full-operation proof.
It does not remove supplied data: the entity/component array, type range, resource
table, pose banks and borrowed storage are synthetic fixtures. No constructors,
real clip selection, resource loading, scheduler invocation, concurrent access or
live player lifetime are established. The chosen family tables and getter linkage
were independently bound in the earlier skeleton-provider research. The original
math routines execute in the emulator; portable comparison still consumes their
recorded outputs and the emulator's rsqrt seeds rather than assuming universal
CPU/libm bit equivalence. Null/missing components are not valid fixtures for this
ordinary path, which later dereferences the component.

The public evaluator intentionally receives component-derived inputs instead of
pretending to acquire live objects. `acquire_pose_provider_by_ranges` supplies the
separate reconstructed acquisition protocol for callers with validated entity
metadata. End-to-end gameplay and mod-loader binding still require live identity,
lifetime and scheduling evidence.


### Special pose route uses cubic Hermite terms

`hermite_pose_pair` reconstructs the special helper's arithmetic for one
contiguous kind-5 vector / kind-6 quaternion descriptor pair. With blend weight
`t` and supplied scalar `s`, its coefficients are:

```text
h0 = 2*t^3 - 3*t^2 + 1
h1 = 3*t^2 - 2*t^3
h2 = (t^3 - 2*t^2 + t) * s
h3 = (t^3 - t^2) * s
result = ((h0*first + h1*second) + h2*first_tangent) + h3*second_tangent
```

The reference preserves float32 instruction order rather than algebraically
rearranging those expressions. The two extra arrays contain 32-byte records,
vector then quaternion contributions. Calling them tangents follows the Hermite
formula, not a proved producer or physical unit. The caller supplies `s` from a
separate operation field; no timestep or velocity semantics are established.

The vector is written only when its descriptor key equals `0x2c52cbb0`; a miss
retains the destination vector but still permits the following quaternion path.
For quaternion endpoints, a negative dot negates the second endpoint before the
weighted sum. Tangent signs are not changed along with it. An all-zero candidate
returns the original second quaternion, otherwise the candidate is normalized
with rsqrt and one Newton refinement. No weight clamp is applied.

The [40-case receipt](../../native/snow_host/hermite_pose_pair_validation.json)
executes the complete original special helper without replaced calls, using one
kind-5/6 pair and the full-range mask. It checks vector and rotation bytes across
key match/miss, negative and positive dot, interpolation/extrapolation weights
and tangent scales zero/two. Recorded normalization seeds bound portable numeric
equivalence. The zero-candidate fallback is statically recovered but not exercised
by these fixtures. Group-range traversal, malformed or differently ordered
channels, multiple tangent records and full higher-operation special routing
remain outside this proof. The general operation API therefore still rejects the
special route; the recovered pair arithmetic is available separately until its
traversal and input contracts are established.


### Special helper traversal and tangent indexing

`plan_special_pose_walk` recovers the special helper's range selection and ordered
writes. Its range differs from the ordinary selector-2 group handling:

```text
if mask == 0xffff: start = 0; end = metadata.total_end
else:
    row = groups[highest_set_bit(mask)]  # zero also selects row zero
    start = 0 if mask bit zero is set else row[0]
    end = row[6]
tangent = 0
while channel < end:
    if low_kind(channel) == 5:
        if key(channel) == 0x2c52cbb0: write vector using tangent
        channel += 1
        if low_kind(channel) == 6:
            write quaternion using tangent
            tangent += 1
    channel += 1
```

`channel` initially equals `start`. Row field six is an end bound in this loop,
not a count added to the start. A multibit mask selects one highest-bit row;
bit zero independently forces start zero. A zero mask does not automatically
skip the helper. A kind-5 descriptor consumes the next descriptor even if it is
not kind 6. The quaternion lookahead can read and write at the exclusive loop
end; authored API bounds reject missing supplied lookahead storage, rather than
silently truncating this behavior. These synthetic probes do not establish
whether unusual layouts occur in valid resources.

Tangent index starts at zero for every helper invocation and advances only on a
quaternion write. A vector key miss does not prevent a following quaternion from
consuming a tangent record. Conversely, a vector write without a following kind-6
channel does not advance the tangent index. Reusing ordinary group iteration or
assigning tangent indices directly from descriptor indices would be incorrect.

The [48-case receipt](../../native/snow_host/special_pose_walk_validation.json)
executes the complete special helper without replacement, observing actual vector
and quaternion store sites and their tangent indices. Zero-valued poses/tangents
exercise the zero-rotation fallback without normalization. Cases cover key misses,
non-pair kinds, boundary lookahead, zero/full/multibit masks and empty selected
ranges. This proves traversal for supplied metadata; tangent production, authored
asset layout rules and higher-operation special-route composition remain open.


### Special bank traversal and arithmetic composed

`evaluate_special_pose_bank` combines the recovered descriptor walk with cubic
Hermite vector/quaternion arithmetic. It accepts logical channel arrays, descriptor
keys/kinds, group metadata and two supplied tangent-record arrays. Each planned
write consumes the tangent index established by traversal. Unselected channels
remain unchanged. Vector-only writes do not invoke quaternion normalization or
advance the tangent index. No status or supplemental-record effects are added.

The [48-case integrated receipt](../../native/snow_host/special_pose_bank_validation.json)
executes the entire original special helper without replacing calls/instructions.
Nonzero endpoint values and distinct tangent records exercise multiple writes,
key misses, unusual descriptor ordering, selected group starts and lookahead.
All channel bytes and write order match the composed API; recorded rsqrt inputs
and seeds are consumed exactly. These cases establish the composition of the
previous separate arithmetic and traversal proofs, not valid asset schemas.

Source and destination arrays are separate value storage. Descriptor byte offsets
are represented by array indices; offset aliasing is not covered. Bounds and
finite-value checks are authored API policy. The special higher-operation route
still needs integration with this helper and its post-blend tail, and the tangent
producer, scale units and gameplay meaning remain unknown. No live callback or
scheduler behavior is inferred from these offline fixtures.


### Complete special pose operation

`evaluate_special_pose_operation` now joins special-route selection, Hermite bank
updates and the common keyed auxiliary/completion/release tail. Unlike ordinary
source-kind routing, the special route retains the stored weight. The special
helper itself changes numeric channels without adding supplemental or bank-status
writes; those later effects come from the common tail. Tangent arrays and their
scale are explicit inputs with unresolved producers and units.

The [96-case full special receipt](../../native/snow_host/special_pose_operation_validation.json)
executes the complete original operation through actual skeleton acquisition,
resource lookup, Hermite helper, auxiliary rotations, manager transitions and
reset. No calls or instructions are replaced. Fixtures cover cached/refresh
acquisition, shared/distinct sources, independent source-cache matches, source
kind combinations, weights .25/1 and masks zero/one. Nonempty supplemental records
are retained or reset by the tail, not blended by the special helper. All numeric
channels, auxiliary records, bank flags, manager/supplemental state, completion
bits, operation weight and reset metadata match the reference. Normalization
and math results are recorded for the portable comparison.

A zero effective mask still selects special group row zero and can change numeric
channels. It suppresses the keyed auxiliary blend and supplemental-counter change,
but does not suppress manager bit-26 writes on uncached matched sources. Therefore
a caller must not turn zero effective mask into an unconditional operation no-op.

The JSON operation bench now accepts `entry: "special"`, requiring descriptor
keys/kinds, `total_end`, groups, both tangent arrays and `tangent_scale` in place
of ordinary `kinds`/`group_count`. Default entry remains ordinary and rejects a
special route rather than silently changing algorithms. This supersedes earlier
statements that no full special-operation evaluator exists. Native storage aliases,
tangent production, scale units, actual resource schema and live scheduling remain
unresolved; the fixture data is synthetic and storage borrowed.


### Tangent storage cloning and record count

A matching operation-copy path uses the same source-cache, manager and entity
fields as the blend operation. Its two tangent slots are independently allocated
when the source slot exists and the destination slot is absent. Each allocation
copies the source's uint32 record count into the destination count field. After
both allocation gates, it copies each present source array using the final
destination count multiplied by 32 bytes. Existing destination slots are retained;
this local code does not check their capacities or update count unconditionally.

`plan_tangent_storage_clone` exposes the allocation/copy order and count writes.
It reports zero-count allocations as absent results, matching the allocator
wrapper's zero fast path. Nonzero allocator success is an explicit assumption.
If both destination arrays already exist, copies use the old destination count.
If either missing slot triggers allocation, both later copies use the new count.
No source slot means no copy or release of its corresponding destination slot.

The [32-case slice receipt](../../native/snow_host/tangent_clone_validation.json)
executes the original allocation-gate/count-write slice and later bulk-copy
argument slice with allocation and memcpy intercepted. It checks presence/count
transitions and ordered call arguments. The intervening component and cached-bank
copy work is skipped, so this is not a complete clone proof. The allocator's
32-byte stride is statically recovered from a 32-bit left shift, while the later
copy size uses a widened 64-bit shift. Extreme-count overflow behavior has not
been instruction-tested and is not evidence of a reachable runtime condition.

This establishes operation-copy storage, not tangent generation. A nearby object
initializer with superficially similar offsets allocates whole pose banks and
has different receiver fields; it is not used as evidence for this operation.
The original tangent writer and scale producer remain unresolved. The clone's
caller and the operation's count-field writers are concrete next leads; actual
heap capacity, allocator failure, lifetime and concurrency remain unproved.


### Clone callers tie Hermite scale to progress bound

The two direct callers of the tangent-aware operation clone address an embedded
operation at receiver-relative `0x170`. This means its tangent slots and record
count must be sought relative to the embedded record, not assumed to be fields
of every surrounding object with the same offsets. Both callers skip cloning
when a predicate returns true, also test the destination operation's low three
kind bits, and set an enclosing flag after the clone. Full caller/list mutation
has not been emulated here.

`pose_operation_copy_guard` reconstructs that predicate for finite inputs:

```text
kind = operation.kind_word & 7
if kind == 0: return true
if kind == 5 and (flags & 4) == 0: return false
if flags & 2: return true
if progress_value > scale_value: return true
return abs(float32(progress_value - scale_value)) <= float32(1e-5)
```

The kind-5 early false return precedes other flag and scalar checks. The
`scale_value` is the same field used to multiply Hermite tangents. The operation
clone copies both scalars and caps copied `progress_value` at `scale_value`.
Together these are a concrete progress/limit lead, consistent with a duration
scale but insufficient to establish seconds, timestep ownership or a transition
clock. The public names remain neutral and no inferred time conversion is added.

The [384-case predicate receipt](../../native/snow_host/pose_copy_guard_validation.json)
executes the full original boolean helper without replaced calls across low kind
values, flag combinations, above/equal/below bounds and adjacent float32 epsilon
cases. This validates the predicate, not clone caller execution or tangent math
production. The clone callers and scalar cap are static evidence. The source
array calculation remains unfound; further work should trace the embedded
record's scalar updates and first population, keeping whole-pose-bank fields on
other receiver types separate from these tangent slots.


### Composed player animation observation API

`engine.player_animation_observation.capture_player_animation` joins existing
skeleton identity and pose-interval observations. It requires a caller-verified
entity/profile and 1..12 external guards, leaving room for retained array header,
slot, type and owner checks. Exactly one known SkeletonComponent and its owner
backlink must match before pose storage is inspected. The pose reader validates
lookup bounds and bank metadata, retains read data, and compares selection/epoch
endpoints. Skeleton binding facts are checked again after the pose observation.

Synthetic tests exercise a successful metadata-bounded read, missing channel,
wrong owner, a component-slot change during the pose read, epoch change and
incomplete transport. These test the authored observation orchestration, not
native algorithm recovery or live safety. Equal endpoints remain vulnerable to
ABA and within-epoch changes. No lifetime pin or scheduler completion is claimed.
The return value contains no raw process addresses and explicitly reports
`suitable_for_animation_writes=False`.

This API uses the existing pose-reader format; it does not pretend that a final
provider pose is a complete blend-operation input. Capturing operation sources,
tangents and weight at one consistent boundary remains a separate requirement
before comparing a live operation against the ordinary/special JSON testbench.
Native host integration and a live capture have not been performed for this API.

### Owner transform supplies guarded-refresh bank parents

The dirty-path preparation in guarded refresh is now joined through its actual
matrix-to-quaternion conversion and parent-bank writes. The component's owner
supplies a transform: when the owner has an indirect transform accessor, the
routine calls that accessor and uses its returned matrix; otherwise it reads the
owner's inline matrix. The accessor can have refresh/locking effects and remains
a service boundary in this validation.

The preparation is specifically:

```python
matrix = owner_accessor(owner) if owner_has_accessor else owner_inline_matrix
parent_rotation = recovered_matrix_to_quaternion(matrix.basis)
parent_position = (matrix.translation.x, matrix.translation.y,
                   matrix.translation.z, 0.0)
write_parent(primary_bank, parent_position, parent_rotation, reset=False)
rotate_for_epoch(component)
write_parent(component.current_bank, parent_position, parent_rotation, reset=False)
```

Translation W is cleared with a bit mask. This path does **not** substitute the
owner's separately stored scalar into W, unlike the other entity-conversion
helper. It adds no quaternion normalization or position scaling. The second
write reloads the current bank after rotation; it does not keep writing the old
bank when rotation chooses a different one.

`reference.skeleton_parent_transform.prepare_skeleton_parent_transform` accepts
the resolved owner matrix and returns those parent inputs. It reuses the already
validated matrix conversion while explicitly selecting W=0. It neither invokes
an accessor nor asserts that the supplied matrix is current or world-space.

[64 joined original-instruction cases](../../native/snow_host/refresh_parent_join_validation.json)
execute full guarded refresh through return, including the actual matrix
conversion, square-root path and both parent setters. Synthetic matrices cover
all four quaternion branches, inline and indirect selection, and unchanged or
swapped current banks. The indirect case poisons the inline matrix to detect use
of the wrong source. A separate stored scalar is supplied but not consumed.
Lock/unlock, indirect accessor, bank rotation and transform processing are
intercepted. Rotation changes the current bank in swap cases; the old bank's
sentinel stays unchanged. This validates data flow and arithmetic, not native
synchronization, real accessor freshness, processing side effects or scheduling.

This narrows interpretation of the live conversion: in this refresh path the
bank parent is derived from its skeleton owner's transform. It does not prove
which update path last populated the particular live bank, nor that the owner's
transform equals the sampled physics-body transform. The approximately 0.943-unit
separation remains an observation, not a named bone offset.

The observed key `0x2c52cbb0` already has a CRC-matched `Reference` spelling in
[the channel-name evidence](animation_binding_channels.json). It is also consumed
by the recovered ground-response pose correction. This is stronger than an
arbitrary unknown key, but CRC matching does not resolve collisions or establish
an anatomical root/pelvis identity. The two other ground-response endpoint roles
remain unnamed; do not label them as feet without a separate binding proof.

### Reset-parent writers explicitly use W one

The live parent-W discrepancy now has concrete writer candidates. A separate
owner-based wrapper resolves the same inline/indirect owner matrix and converts
its basis, but explicitly overwrites translation W with float32(1). Its order is:

```python
lock(component)
owner_matrix = resolve_owner_transform(component.owner)
parent = prepare_reset_parent_transform(owner_matrix)  # XYZ copied; W=1
rotate_for_epoch(component)
set_parent(component.primary_bank, parent, reset=True)
set_parent(component.current_bank, parent, reset=True)
copy_bank_service(component.primary_bank, component.current_bank, mode=5)
unlock(component)
```

The bank-copy service's argument order and literal mode are observed; this section
does not assign a source/destination interpretation or execute that service.
Another statically inspected writer takes a supplied matrix, performs the same
W=1 preparation, then visits both configured bank slots in order. It invokes the
parent setter with reset enabled for each non-null slot. That writer has no lock
operation in its own body; its caller's synchronization remains unresolved.

This is different from guarded dirty refresh, which uses W=0, writes primary
before rotation, and calls the setter with reset disabled. Both are intentional
native paths. The APIs `prepare_skeleton_parent_transform` and
`prepare_reset_parent_transform` preserve that distinction rather than assigning
a universal homogeneous-coordinate convention.

[64 reset-wrapper instruction cases](../../native/snow_host/reset_parent_join_validation.json)
execute the full owner-based wrapper, including actual matrix conversion and
both actual parent setters. Inline/indirect transform selection and current-bank
swaps are varied. Lock/unlock, accessor resolution, rotation, default-pose supply
and the mode-5 copy service are intercepted. The actual setter's reset path copies
the supplied default pose, runs the zero-record reset case, and clears its stored
reset word. That word starts nonzero in the fixture; the unselected bank retains
its sentinel. Nonempty record resets and the copy service's effects are not
validated here.

Reanalysis of the prior forty live parent observations finds thirty-six compatible
with W=0 preparation and four compatible with W=1 preparation; XYZ and quaternion
agree in all forty. This explains how both values can be produced by decoded
code, but does not establish which caller ran for any sample. Initialization,
other parent writers and cached-parent publication remain candidates. The four
samples must not be relabeled as proved reset events.

### Supplied-matrix slot reset and caller order

The supplied-matrix writer prepares the W=1 parent once and visits two configured
bank slots in order. Null entries are skipped; aliases are not deduplicated.
Each selected bank receives the parent setter with reset enabled:

```python
parent = prepare_reset_parent_transform(matrix.basis, matrix.translation)
for bank in configured_slots:  # exactly two slots, ordered
    if bank is not None:
        set_parent(bank, parent, reset=True)
```

The independent `reset_configured_parent_slots` wrapper exposes reset as an
explicit supplied service. It does not manufacture default animation records.
[80 original-instruction cases](../../native/snow_host/slot_parent_join_validation.json)
execute the complete slot writer, matrix conversion, parent setters and empty
record reset. Only the default-pose supplier is intercepted. Cases cover all
four quaternion branches, neither/either/both slots present and aliased slots.
Selected banks reset their default pose and clear the reset field; unselected
banks retain sentinels. Nonempty record reset remains outside this validation.

Static caller inspection establishes this order:

```python
matrix = construct_transform_from_receiver_state(receiver)
set_entity_transform(entity, matrix)
skeleton = find_skeleton_component(entity)
if skeleton is not None:
    reset_configured_parent_slots(matrix, skeleton.configured_slots)
```

This is a static call-order finding, not a live completion boundary. One upstream
wrapper optionally refreshes receiver position and orientation through virtual
services before calling the transform publisher. Another conditionally invokes
a preparation service when its state word is zero, publishes the transform, then
clears that word. The receiver's runtime type, service meanings, scheduling trigger
and relationship to the four live W=1 observations remain unresolved. Do not
label this a per-physics-step callback or expose it as a safe pose-write API yet.

### Spawn-position caller identity and gate

The two supplied-matrix publisher callers are now statically bound to
`SpawnPositionPlayerParams` and `SpawnPositionVolumeParams`. This is supported by
constructor table installation, the table's type getter, the descriptor name,
the descriptor's matching constructor pointer, and the publisher entry at slot
25. It is not inferred from nearby strings. The shared publisher belongs to
spawn-position handling; this evidence does not establish a regular physics tick.

The volume variant has this recovered wrapper:

```python
if state.publication_state == 0:
    prepare_volume_position(state)
publish_entity_and_skeleton_transform(state)
state.publication_state = 0
```

The state is a full unsigned 32-bit word. Preparation may change it before the
publisher runs. Any nonzero value skips preparation, including values with the
high bit set. The clear occurs after publication. The independent
`publish_volume_spawn_transform` exposes both services explicitly; their internals
and runtime scheduling are not invented. Python service exceptions propagate
without reaching the trailing clear; that is an authored service-error contract,
not a claim about native exception handling.

[Type binding and four wrapper cases](../../native/snow_host/spawn_parent_dispatch_validation.json)
validate this distinction. The original wrapper executes while both services are
intercepted. The player variant instead optionally obtains position/orientation
through virtual services before the shared publication path. Neither type binding
proves that these callbacks caused the four live W=1 observations. Teleport and
respawn are follow-up integration leads, not exposed or tested mod features here.

This supersedes the preceding section's unknown static receiver-type boundary.
Concrete live receiver identity, invocation trigger, and any completion or lock
requirements remain open.

### Player spawn provider refresh ordering

The player spawn-position wrapper always calls the shared transform publisher.
A missing provider skips refresh and retains the receiver's stored position and
rotation. A present provider takes this ordered path:

```python
provider = owner.get_pose_provider()
if provider is not None:
    context = owner.context_source.get_context()
    provider.configure(context, 0)
    returned_position = provider.read_position(scratch)
    receiver.position = (returned_position.x, returned_position.y,
                         returned_position.z, 0.0)
    returned_rotation = provider.read_rotation(scratch)
    receiver.rotation = copy_four_lanes(returned_rotation)
publish_entity_and_skeleton_transform(receiver)
```

The service names above describe their observed roles, not recovered method
names. The owner is dereferenced unconditionally; no owner-null fallback is
present. Configuration receives zero in its third argument. Each pose read uses
its returned pointer rather than assuming that the supplied scratch buffer was
filled. Position is stored before the rotation getter runs. Rotation is copied
without normalization at this wrapper level; the downstream publisher has its
own arithmetic. Neither coordinate space nor world-unit equivalence is inferred.

[34 instruction-emulation cases](../../native/snow_host/player_spawn_wrapper_validation.json)
execute the complete wrapper, with virtual services and shared publication
intercepted. Synthetic providers cover absence, scratch-buffer returns, separate
returned storage and non-unit rotations. The rotation service checks that the
position store already occurred. Both missing-provider cases preserve the old
pose and still publish. No actual spawn or teleport was invoked in a game.

The independent `publish_player_spawn_transform` provides this order through
explicit callbacks. It models returned values, not native pointers. Its Python
service-error behavior preserves any earlier stores and does not publish after a
failed read; this is an authored error contract, not native exception recovery.
Remaining boundaries include the concrete provider type, configuration semantics,
coordinate frames, publisher context transformation, and live dispatch timing.

### Spawn parent coordinate conversion

The spawn transform publisher resolves a parent through its retained context and
mask service. Parent availability is an explicit input to the independent
`resolve_spawn_position` and `resolve_spawn_rotation` helpers; pointer masking,
lifetime and refresh services remain outside these numerical APIs.

For a resolved parent with four stored rows, position follows this operation
order, with float32 rounding after every multiply and add:

```python
v = position.z * parent.row2 + parent.translation
v = v + position.y * parent.row1
v = v + position.x * parent.row0
result = (v.x, v.y, v.z, 0)
```

The stored input W never scales translation. Without a parent, this intermediate
step copies all four position lanes, including W. This describes the intermediate
position, not the final published matrix's fourth lane.

Rotation takes a different route. Without a parent it copies the stored
quaternion. With a parent it converts that quaternion into a 3x3 basis, places the
basis in a runtime 4x4 template, composes each local row as a weighted sum of
parent rows in x/y/z/w order, and extracts a quaternion using the already
reconstructed matrix-to-quaternion branches. No quaternion normalization occurs
inside this resolver. The shared publisher normalizes afterward, outside these
helpers' contract.

The globals are zero in the analyzed image, but a subsequently traced initializer
writes the identity matrix. The API now defaults to that reconstructed initialized
state and accepts an explicit template override. This supersedes the earlier
required-template boundary. An altered template's fourth lanes can affect the
composed basis through parent translation, so the general calculation retains them.
See the initializer validation below for the limits of the default.

[60 original-instruction cases](../../native/snow_host/spawn_coordinates_validation.json)
match both helpers exactly. These execute the complete rotation resolver and the
publisher's position branch with synthetic matrices/quaternions, absent/inline/
indirect parents and original-initialized identity or synthetic altered-fourth-lane templates. Mask and
accessor calls are intercepted; matrix conversion, composition and quaternion
extraction execute unchanged. The indirect cases poison inline storage to check
that the accessor's returned matrix is used. No live game observation or runtime immutability claim follows.

The publisher resolves/reads the parent for position, then the rotation resolver
performs its own resolution/read. These may refresh separately. The two numerical
helpers must not be taken as proof of an atomic shared-parent snapshot, a safe
teleport call boundary, or world-space equivalence.


### Spawn matrix template identity initializer

A leaf initializer loads four constant unit rows and stores all 16 floats into
the template globals. Its address is present in a table of function pointers.
This establishes the initializer's contents and table membership; it does not
independently observe startup dispatch or prove the globals are never modified.
The earlier scan used unwind-described functions and omitted this leaf routine.
A direct store-pattern search found it, followed by instruction inspection and
emulation. Absence from the unwind index was a search limitation, not obfuscation.

```python
def initialize_spawn_matrix_template():
    return ((1, 0, 0, 0),
            (0, 1, 0, 0),
            (0, 0, 1, 0),
            (0, 0, 0, 1))
```

The coordinate validation now executes this original initializer in 30 cases,
first poisoning all 64 template bytes. It verifies every output byte, then runs
the original coordinate resolver. The remaining 30 cases retain explicit altered
templates to test the general formula. The independent rotation resolver defaults
to the recovered initialized template. Callers investigating an unknown runtime
state can still supply the observed template explicitly. No initializer service
is intercepted; parent accessor and mask services remain intercepted as before.

### Spawn publication matrix normalization

The shared publisher normalizes the resolved quaternion before constructing its
entity matrix. `build_spawn_publication_matrix` reconstructs that arithmetic;
it accepts the already resolved pose and a reciprocal-square-root estimate
service. Every operation below rounds to float32:

```python
squares = quaternion * quaternion
norm = (squares.x + squares.z) + (squares.y + squares.w)
estimate = reciprocal_sqrt_estimate(norm)
factor = (3 - (estimate * norm) * estimate) * (0.5 * estimate)
normalized = factor * quaternion
matrix.basis = quaternion_to_basis(normalized)
matrix.translation = (position.x, position.y, position.z, 1)
```

The basis uses the same doubled-product construction and storage order as the
parent rotation conversion. Its three fourth lanes come from the initialized
matrix template, normally zero; explicit template overrides retain them. The
translation fourth lane is replaced with one independently of incoming position
W. The output is the matrix prepared for the entity setter and later skeleton
slot reset, not a direct physics-body velocity or teleport operation.

[80 instruction-emulation cases](../../native/snow_host/spawn_publication_matrix_validation.json)
execute the original normalization and matrix-building block up to the entity
setter call. Cases include non-unit rotations, axis rotations, arbitrary incoming
position W, original identity initialization and altered template fourth lanes.
All 64 output bytes match the reference. The RSQRT instruction itself executes;
the private validator captures its emulator-produced estimate and supplies that
to the reference. This verifies the refinement and downstream arithmetic, not
hardware-estimate equivalence or original-game execution. The entity setter is
not executed in these cases.

The numerical API rejects nonfinite inputs, zero/overflowed squared norms and
nonpositive/nonfinite estimates. These are authored input guards, not recovered
native fallback behavior. The native block has no observed zero-norm guard in
this span. Publisher call scheduling, entity setter side effects and a live-safe
spawn/teleport interface remain separate work.

### Spawn entity publication dispatch variants

The spawn setter wrapper builds a packet whose first and second matrix pointers
both refer to the supplied matrix, with flags 31, then calls the entity's
transform virtual method. The three entity tables accepted by the current private
reader do not all select the same body. One selects the already reconstructed
base update; two select a wrapper that runs the base update and then a linked
transform propagation routine.

[36 original-instruction cases](../../native/snow_host/spawn_entity_dispatch_validation.json)
execute the setter packet wrapper, actual table dispatch, base recursive-lock
handling, component notification loops and matrix copy. Thread identity, cache,
component callbacks and the derived linked-transform tail are supplied services.
The packet's two aliases and flags are checked at dispatch. Cases cover three
tables, empty/nonempty component lists, replaced post lists and fresh/nested locks.

The linked tail sees the base update's *incoming* lock depth restored. For a fresh
lock this means unlocked; for a nested call an outer lock remains held. Thus the
whole derived operation is not covered by one newly acquired base-update lock.
The independent `publish_spawn_entity_transform` makes receiver variant selection
and linked propagation explicit. It rejects missing required services before
mutation. This is a reconstructed dispatch API, not a native teleport API.

Static inspection of the unresolved linked routine shows another list traversal:
it resolves retained targets, skips a target flag, acquires/checks/releases a
descriptor, composes each packet matrix with an indexed stored transform, and
invokes the selected target's transform virtual method with inherited flags.
It reloads list storage and count during traversal. Descriptor meanings, target
identity, mutation/lifetime behavior and full execution of that routine remain
unvalidated here. Do not silently omit it or equate it with a physics-body setter.

The reconstructed join reuses the base ordering documented in
[entity transform notifications](ANIMATION_CONTEXT_RETIREMENT.md#entity-transform-notification-lists-are-captured-separately).
It does not add live synchronization, object lifetime guarantees or prove that a
spawn publisher runs on a suitable modding thread.

### Linked spawn transform propagation loop

`propagate_linked_spawn_transforms` now reconstructs the derived entity tail's
local loop. The retained-target resolver, flag reader, descriptor services and
target dispatch remain explicit. For each indexed link:

```python
target = resolve(link)
if target is not None and not (target.flags & 1):
    descriptor, cleanup_token = acquire_descriptor(target)
    blocked = descriptor_blocks(descriptor)
    release_descriptor(cleanup_token)
    if not blocked:
        second = local[index] * packet.second
        first = local[index] * packet.first
        target.update_transform(first, second, packet.flags)
```

Multiplication uses the recovered four-row storage convention and float32 order.
The second matrix is composed first; outgoing packet order remains first/second.
Packet flags are preserved, including high bits. The descriptor predicate consumes
the returned descriptor; cleanup consumes the temporary acquisition object. These
are separate identities in the API and synthetic validation. Descriptor meaning
is still unresolved and must not be relabeled as a grounded/physics-active test.

[24 original-instruction cases](../../native/snow_host/linked_spawn_validation.json)
execute the complete loop and both actual matrix multiplications. Supplied services
cover target masking, descriptor acquisition/predicate/release and target dispatch.
Cases cover empty lists, missing targets, skipped flag, blocking predicate, mixed
entries, and dispatch callbacks that shrink, grow or replace the list. Flags span
zero, 31 and the high bit. All dispatched matrices match bit-for-bit.

The native loop reloads backing storage at each iteration and count after each
iteration. It does not snapshot the initial collection. The stored transform at
the current index is loaded only after descriptor cleanup. Replacement backing
stays alive in these synthetic tests; this does not establish safety under freed
storage, target destruction, concurrent updates or recursive mutation. Return
true indicates the routine reached its end, not that any target was updated.

The Python reconstruction keeps objects alive through normal references and
releases the cleanup token if its predicate raises. That exception cleanup is an
authored contract. Normal native cleanup order is verified; native exception
handling is not. Target virtual side effects, concrete target types, descriptor
internals and safe live scheduling remain open.

### Linked descriptor visibility and ownership join

The linked pass's predicate is the previously recovered
[descriptor validity test](ANIMATION_CONTEXT_RETIREMENT.md#descriptor-visibility-connected-to-cleanup).
It returns true for a visible direct holder in mode 1, or a visible second holder
in mode 2 with a non-sentinel index. Other modes return false. Visibility is a
bitwise target/status/thread-mask test; the mask is not a boolean permission.
In this particular caller, **true skips linked transform dispatch**. This does not
justify calling the target grounded, active, or safe to mutate.

`linked_spawn_descriptor_blocks` reuses that predicate and preserves lazy mask
lookup. Mode 1 queries the mask regardless of index; mode 2 does so only when the
index is not 65535. Unknown modes and mode-2 sentinel never query it. The initial
linked-target resolution separately queries the mask before this predicate.

[96 joined instruction cases](../../native/snow_host/linked_spawn_descriptor_validation.json)
now execute actual acquisition, descriptor copy, validity test, holder increments,
release/decrements, the linked loop and matrix compositions. Only the thread-mask
getter and final target dispatch are intercepted. Cases span modes 0–3, valid/
sentinel index, empty/nonempty target bits, clear/set status bit 31 and masks
0, 128 and 256. Both source holders start at count two, reach three during the
predicate/release entry, and return to two before target dispatch or return.
No holder reaches retirement. The sentinel holder is synthetic and kept alive.

This closes the predicate-meaning and normal temporary ownership boundaries for
these cases. Actual mask-service values, concrete linked target types, holder
retirement, descriptor mutation during calls and concurrency safety remain open.
The model exposes the recovered test through supplied observations rather than
reading or retaining native pointers.

### Joined spawn publication service pipeline

`publish_spawn_pose` joins the shared publisher's recovered pieces in order:
entity acquisition, parent resolution for position, separate parent resolution
for rotation, normalization/matrix construction, entity publication, skeleton
lookup and optional configured-slot resets. Entity publication is a supplied
service and can use the reconstructed base/derived dispatch adapter. Skeleton
lookup happens after publication, permitting that service's state changes to be
observed. The same prepared matrix supplies both entity publication and reset.

[12 joined original-instruction cases](../../native/snow_host/spawn_pipeline_validation.json)
execute the complete shared publisher and its actual rotation resolver, matrix
arithmetic, slot writer and parent setters. They cover absent parent, unchanged
parent, changed matrix between parent reads, missing skeleton, empty slots,
distinct slots and aliased slots. Engine getter/setter, accessor/mask, skeleton
lookup and default-pose services remain supplied. Record banks are empty.
The emulator's RSQRT estimate is captured for reference replay. Both final matrix
and selected bank parent bytes match. No live scheduler/lifetime proof follows.

Run `python3 -m engine.examples.spawn_publication_probe` for a synthetic example
that connects the pipeline to the existing base entity update. It reports
notification order, lock depth, the output matrix and two reset bank records.
The example's exact reciprocal square root is an explicitly authored estimate
source; it does not reproduce or measure a hardware estimate. No game payloads,
process access or native pointers are required. This is a runnable reconstruction
path, not a command for teleporting a live player.

### Nonempty animation bank reset

The parent setter always copies the incoming 32-byte parent pose. With reset
false, it performs no default-pose or record work. With reset true, it obtains the
default pose, copies it to the bank's default slot, resets each active 32-byte
record, then clears the bank's reset word. The recovered default is zero position
and XYZW rotation `(0,0,0,1)`.

[16 original-instruction cases](../../native/snow_host/bank_record_reset_validation.json)
execute the actual setter, default getter, GS/TLS reads, initialization stores and
record loop for counts 0, 1, 3 and 64, reset on/off, and ready/cold defaults.
Initialization synchronization header/footer are supplied services; their locking
behavior is not emulated. Each active record matches the identity default and the
next record's sentinel remains intact. Reset false preserves all record/default
storage and the reset word. Cold reset invokes initialization only once here.

`reset_animation_bank_parent` supplies a runnable byte-record model. The default
provider abstracts the TLS guard/global reads: once for the bank slot and again
for every record. The native loop also reloads count each iteration. It neither
allocates records nor changes the count. Python storage and invalid-input errors
are authored behavior. No claim is made about allocation capacity, full skeleton
pose semantics, concurrent default initialization or live reset safety.

This supersedes the empty-record-only boundary of earlier setter tests. Those
historical receipts retain their original scope; the new receipt validates the
nonempty reset separately, not every publication path under concurrency.

### Joined publication with nonempty record banks

The [12 joined nonempty-bank cases](../../native/snow_host/spawn_pipeline_records_validation.json)
extend the full shared-publisher replay through actual default-getter/TLS reads
and three active records per selected bank. Missing skeleton, empty slots, distinct
slots and aliases remain covered, as do absent/unchanged/changing parents. Every
active record, bank default, parent and reset word matches the composed reference;
unselected banks and the fourth tail record retain their sentinels. Aliased slots
execute reset twice rather than deduplicating the bank.

These cases use an initialized default and synthetic TLS, while the separate cold
reset receipt covers initialization. Engine getter/setter, parent mask/accessor
and skeleton lookup remain supplied services. The entity setter's own behavior
is validated separately; this joined run does not execute an entire game world.
The example now connects `reset_animation_bank_parent` as its reset service and
reports active record values, reset words and untouched-tail checks.

### Offline spawn sequence inspection command

Run the supplied-input sequence bench without game files:

```sh
python3 -m engine.spawn_publication_bench \
  --request engine/examples/spawn_publication_input.json \
  --output spawn-result.json
```

The request requires branch `supplied_spawn_publication`, initial named banks and
one to 256 frames. Each frame explicitly supplies position, rotation, separate
`position_parent` and `rotation_parent` matrices or null, a positive
`reciprocal_estimate`, and two named/null slots or a null skeleton. An optional
matrix template overrides the recovered initialized identity. Bank count must fit
supplied records; storage is bounded to 16 banks and 512 records each as authored
inspection limits. No arbitrary data are inferred for missing banks or estimates.

The result reports matrix/normalization outputs, ordered events, final bank
records, evidence limits and a canonical input hash. Bank state carries between
frames. Missing skeletons leave banks unchanged; aliases reset the same bank
twice. Caller input is deep-copied. Entity publication is recorded only, so this
command does not simulate entity notifications, linked targets, native scheduling
or physics. Use the separate service pipeline when supplying those integrations.

Tests replay all 12 joined nonempty-pipeline matrix receipts through this command's
Python API, plus state carry, input preservation, alias ordering, inactive-tail
preservation and invalid dependency/capacity rejection. Repeated output is a
property of supplied-input reconstruction, not deterministic original-game replay.

### Cached parent callback publication boundary

A separate animation path prepares the cached component parent from the owner
matrix, explicitly clearing W to zero. One inspected caller performs preparation
then calls a processing routine whose prefix optionally invokes a registered
callback before copying that cached parent to primary and current banks. Both
setters use reset=false. The current bank and cached pose are read after callback
execution; this is a different publication route from spawn-position reset.

[24 instruction-emulation cases](../../native/snow_host/cached_parent_prefix_validation.json)
execute cached preparation and this prefix through both actual parent setters.
Owner access and rotation services are supplied. Cases cover inline/indirect owner
matrices, no callback, and synthetic callbacks that change cached W to one or
also replace the current-bank pointer. All preparation results have W=0. The
writes reflect the callback's changes and leave bank defaults/reset words intact.
The callback mutations are test inputs, **not recovered original callback behavior**.
Registration lists are empty and downstream animation processing is not executed.

`publish_cached_parent_prefix` exposes the ordered prefix with an explicit
already-gated callback service. Its missing-primary branch skips all work. Native
callback selection checks callback storage and a retained holder's status/target;
the model does not infer callback eligibility or hold native references.

This narrows the live W=1 investigation: cached preparation alone cannot explain
those values, while an intervening callback or another parent writer still could.
Live callback identity, callback contents, scheduler cadence and last-writer
attribution remain unresolved. No new animation-write safety claim follows.

### Cached parent callback gate

The callback gate differs from the thread-mask-based descriptor predicate. It
requires a primary bank, nonempty callback storage, status bit 31 set on the
retained holder, and a nonzero holder target. Callback storage is considered
nonempty when either its first word is nonzero or its tagged context has any bits
other than the low two set. The forwarded context clears those low two bits.

```python
context = tagged_context & UINT64_MASK_WITH_LOW_TWO_BITS_CLEAR
registered = bool(storage_word or context)
invoke = primary_present and registered and bool(holder_status & 0x80000000) \
         and bool(holder_target)
if invoke:
    callback(callback_storage, context)
```

[168 original-instruction gate cases](../../native/snow_host/cached_callback_gate_validation.json)
cover missing primary, empty/nonempty storage, context tags 0–3, aligned contexts,
all-one context, status sign bit and missing/present targets. Only the selected
callback is supplied. No TLS getter appears in this gate. A nonzero first storage
word can permit forwarding a zero context after tag clearing; the model preserves
that rather than inventing a nonnull-context requirement.

`cached_parent_callback_gate` exposes this rule using numeric observations without
native pointer access. The actual path does not separately null-check the stored
function pointer before its indirect call. Eligibility therefore does not prove
that invoking an arbitrary supplied callback address is safe.

Static constructor inspection initializes the storage/context/function fields to
zero and assigns the retained holder. Destructor inspection releases that holder
and clears the function field. The registration writer and a concrete live
player callback are still unidentified. Apparent matching stack offsets elsewhere
were not accepted as registration evidence. This gate narrows a probe plan; it
does not attribute the observed W=1 values to callback execution.

### Callback registration search and next observation

The [bounded registration search](../../native/snow_host/cached_callback_registration_search.json)
expanded beyond skeleton routines to unwind-indexed functions and supplemented
embedded-storage immediate additions with a raw-byte candidate scan. It did not
identify a new registration writer with proven skeleton receiver provenance.
Shared offsets, stack locals and unrelated embedded-member destructors were not
accepted as a connection. Aliased access, bulk copies, leaf omissions and dynamic
code remain search limitations; this is not proof that registration never occurs.

The next useful observation is a passive, identity-bracketed capture of cached
parent, callback storage/context/function, retained holder target/status and bank
identities. Retain and reread the bounded record and holder; refuse invalid ranges
or changing identities. Report callback eligibility separately from function-field
presence and observed invocation. Even a matching reread is not lifetime pinning
or an atomic snapshot. A nonzero function field needs module/executable provenance
before becoming a disassembly target. Empty storage describes only that interval.
This observation is a plan, not an installed native-reader feature or completed
live experiment. No game was launched during the search.

### Passive cached-parent callback reader

`engine.cached_parent_observation.capture_cached_parent` now implements the planned
bounded read using a caller-supplied read transport, fresh component/entity/table
identities and external guards. It reads the cached pose, primary/current parents,
callback storage, tagged context/function and retained holder. All observed spans
are reread before returning. Wrong owner/table, incomplete reads, invalid ranges,
nonfinite poses and changed endpoints are refused. The function never invokes
native methods or writes memory.

Output includes callback eligibility, function presence, tag bits, holder presence
and status sign, bank aliasing and pose values. Raw pointers are not returned.
Optional caller-supplied code ranges produce label matches only; the reader does
not query executable permissions or establish module provenance itself. A null
function with an otherwise eligible registration remains distinguishable from a
safe callable registration. Guards do not pin lifetime, prevent ABA or make the
sequential reads atomic.

Six synthetic transport tests cover gate/pose reporting, inactive holders, wrong
ownership, truncated reads, empty registrations and mutations of cached pose,
callback storage, holder and bank parent. This reader is not yet wired into the
native host command or exercised against a live game. Caller acquisition and
process identity checks remain required dependencies.

### Player-bound cached-parent observation

`capture_player_cached_parent` in `engine.player_animation_observation` now joins
callback observation to the existing exact-type skeleton binding reader. Callers
supply a verified player entity, image base/profile, external identity guards and
read transport. The reader retains the component-array header/selected slot,
requires a unique exact SkeletonComponent and matching owner backlink, and
repeats binding verification after the callback observation. Component pointers
are resolved within the call rather than accepted as persisted inputs.

The binding implementation is shared with `capture_player_animation`; their
output schemas remain separate. Five new synthetic tests check successful empty
registration, slot replacement during callback reads, early owner rejection,
external identity mutation and truncated transport. The five existing player-pose
tests and 23 compiled native animation-reader tests pass after the shared-binding
refactor. Neither path acquires a live player or pins native lifetime. Native-host
command wiring and original-game validation are still pending.

### Portable native cached-parent reader

`snow_cached_parent_observe` now provides the callback observation in the portable
C reader. It shares exact skeleton binding with the existing channel reader,
retains every binding/callback/holder/pose span, and rereads those spans before
publishing output. Refusal leaves output zeroed. The result has no addresses and
separates eligibility from function presence. It makes no executable-permission,
lifetime, invocation or completion claim.

The compiled synthetic reader suite now has 28 passing tests, including the
existing 23 channel regressions and new callback success/empty/refusal/mutation
cases. The fixture also cross-compiles for Windows x64 with warnings as errors.
No transport or private process access is included in the portable fixture.
The native adapter callback, host command and live session remain pending; this
is the reader implementation, not yet an exposed mod-host endpoint.

### Cached-parent host command wiring

The host now exposes `animation.get_cached_parent` through an optional adapter
callback. The analyzed-build adapter uses the bounded native reader and brackets
it with the same actor/entity/world identity checks as channel observation.
The fixture adapter supplies clearly synthetic cached W=0 and bank W=1 data
with an empty callback. Unsupported adapters refuse the command.

The host validates finite output poses and boolean/tag ranges before serializing
address-free results. Missing bank poses are null. The adapter callback is appended
to the internal adapter interface; the plugin ABI is unchanged. Both fixture and
analyzed-build hosts compile for Windows x64 with warnings treated as errors.
Original-game validation is still pending; build success does not establish a
usable live callback registration or attribute any parent write.

### Live cached-parent observation

The subsequent bounded original-game capture accepted 26 of 32 identity-bracketed
queries over 3.31 seconds. Six queries were refused with the reader's combined
identity/bounds/read/endpoint error; the exact reason is not distinguished.
The maximum three-request bracket took 8.47 ms. These are sequential observations.
The [aggregate receipt](../../native/snow_host/cached_parent_live_observation.json)
contains counts and flags only; raw pose rows remain private.

All accepted samples had separate primary/current banks and equal bank contents.
Cached parent W stayed zero. Bank W included zero and one, with three parent-pose
changes across 20 adjacent accepted same-identity pairs. Cached parent contents
did not change across those pairs. Cached and primary parent contents agreed in
24 of the 26 accepted samples.

The callback storage, forwarded context and function were empty in every accepted
sample. A holder existed with its status sign bit set but no target, so callback
eligibility was false. Thus this session supplies no evidence of callback
invocation, and bank changes cannot be attributed to that callback. Transient
registration between samples remains possible. The next writer investigation
should follow the already decoded direct parent setters/reset/publication paths
while retaining the unresolved callback-registration lead.

Startup navigation sent input before capture; the capture plan sent no riding
input, pause, step, or mutation commands. Ordinary advancement passed the
20-second stability check. The bounded runner restored settings, stopped its
bottle, verified the original DLL, and did not replace that DLL. This validates
the observation endpoint for one active-player session, not animation mutation
or a safe callback interface.

### Non-reset writer also publishes W one

A direct parent-setter caller supplies owner XYZ with W explicitly replaced by
one while passing `reset=false`. This closes an important interpretation gap:
W=1 does **not** identify an animation-bank reset or a spawn operation. The local
slice is implemented as `publish_nonreset_owner_parent` in
`reference/skeleton_parent_transform.py`.

```text
owner = wrapper.component.owner
matrix = owner.accessor ? resolve(owner.accessor) : owner.inlineMatrix
parent.rotation = matrixToQuaternion(matrix.basis)
parent.position = (matrix.translation.xyz, 1)
setParent(selectedDestination, parent, reset=false)
```

The [32-case instruction receipt](../../native/snow_host/nonreset_owner_parent_validation.json)
compares direct and supplied-accessor matrices, including all four quaternion
conversion branches. It executes the actual conversion and parent setter and
checks exact parent bytes plus preservation of the remaining synthetic bank
storage. The destination-selection prefix, preceding preparation service, and
following bank-processing call are outside this validation scope.

Static inspection of the surrounding routine shows two candidate banks selected
using bit 26 of bank flags. It can obtain a missing alternate bank from a service;
that service remains an explicit dependency. With no newly obtained bank, a null
source or a source without flag bit 27 skips the preparation/publication path.
After publication it passes `(component.flags16 >> 3) & 7` to bank processing.
These surrounding gates are static findings, not yet joined instruction tests.

This writer is a candidate for the live W=1 observations. No observed call,
component membership, or destination-bank identity currently attributes those
samples to it. Another direct caller uses a separately normalized conversion
helper, so numerical coincidence alone would still be insufficient attribution.

### Alternate-bank selection and publication gates

The full surrounding wrapper now matches
[64 instruction-emulation cases](../../native/snow_host/owner_parent_selection_validation.json).
`select_and_publish_owner_parent` provides the executable reference, keeping
acquisition, preparation, owner access, and bank processing as explicit services.

```text
created = false
if primary.flags.bit26 and alternate == null:
    alternate = acquire(component.pool, 65535, requestByte & 1)
    alternate.flags.bit26 = false
    created = true
destination, source = primary, alternate
if destination.flags.bit26:
    destination, source = source, destination
if not created and (source == null or not source.flags.bit27):
    return destination
prepare(wrapper, source)
publishOwnerParent(destination, resolveOwner(wrapper.component), W=1, reset=false)
process(destination, source, (wrapper.component.flags16 >> 3) & 7)
return destination
```

The reference reloads bank selection after acquisition, owner/component after
preparation, and processing mode after publication. The supplied preparation
service changes the mode in half of the synthetic cases, verifying that the later
read sees the new value. Destination and source remain the selected local bank
references even if later services mutate wrapper fields.

All combinations of primary bits 26/27, alternate presence and bit 27, request
low bit, and preparation mode mutation were checked. Actual parent writes retain
the banks' reset words. Acquisition, preparation internals, and processing are
still supplied services; their effects are not reconstructed by these tests.
The native acquisition result is dereferenced without a null check. The reference
instead raises on null as an explicit safety guard, not original behavior.
Active-player ownership and live execution of this wrapper remain unverified.

### Remapped pose queries can publish parent state

A direct caller of the alternate-bank wrapper is a remapped pose query. Its
uint16 input index and mapped index each use 65535 as an invalid sentinel.
Either invalid sentinel returns two default four-lane values without selecting
a bank. Otherwise it selects/prepares the bank through the wrapper above and
then calls the bank pose reader with the mapped index. The output buffers are
copied from that read. Consequently this query is not inherently read-only:
the selection call can allocate an alternate, prepare a source, publish its
parent transform, and process the bank before returning the requested pose.

```text
if index == 65535: return defaults
mapped = remap[index]
if mapped == 65535: return defaults
bank = selectAndPublishOwnerParent(wrapper)
return readBankPose(bank, mapped)
```

`query_remapped_parent_bank` implements this ordering with explicit services
and caller-supplied default values. The
[five instruction cases](../../native/snow_host/remapped_parent_query_validation.json)
cover both invalid gates, zero, ordinary and high valid mapped indices. Selection
and pose reads were substituted; the actual query branches and output copies
ran. Default globals came from the analyzed image and are not live-verified.
Public reference bounds/type rejection is an authored safety check.

This caller connection strengthens the case that W=1 publication can occur
outside spawn/reset. It does not establish that this query ran during the live
capture, nor connect its wrapper to the active player. A nearby remapped setter
also invokes the wrapper, but its full write semantics remain unvalidated.
Keep passive observation on the bounded memory-reader API; calling an apparent
native getter is not equivalent to reading memory without side effects.

### Stack work wrappers and output publication

A direct caller constructs two temporary work wrappers on its stack. Static
inspection establishes that both reference its supplied skeleton component.
The input wrapper starts with that component's current bank and a null alternate;
the output wrapper starts with both bank references null. Each has an inline
scratch-storage pointer, header value 32772, index sentinel 65535, and cleared
low three flag bits. These are call-scoped objects, not proved persistent player
fields. A work packet holds pointers to both wrappers and a supplied time value.

The caller invokes a virtual work service with the packet and an extra-work
flag. If it succeeds, output publication follows this order:

```text
capturedCurrent = component.current       // captured before the work callback
success = work(packet, extraWork)
if success:
    selected = selectAndPublishOwnerParent(packet.outputWrapper)
    copySelected(capturedCurrent, selected, mode, index=65535)
    copyPrimary(capturedCurrent, component.primary, mode)
```

`publish_pose_work_result` implements the success-gated publication portion.
[32 original-instruction cases](../../native/snow_host/pose_work_publication_validation.json)
cover all eight processing modes, success/failure, and primary replacement during
the first copy service. The synthetic work callback changes component.current;
the native caller still uses its captured bank. The second copy instead reads
component.primary after the first copy returns. Failure skips selection and both
copies. The work service, bank selection, and two copy services are substituted;
their bodies and the earlier wrapper construction are not validated by this
receipt. The synthetic pointer changes test reload order, not observed behavior.

This gives a concrete ownership route from a supplied component's current bank
through call-scoped work descriptors. It does not yet establish that the caller's
component is the active player or that the output wrapper uses that same bank.
The output starts empty and the work service must populate it before selection.
For live attribution, capture the packet during this call, verify its component
against the freshly bound player, and retain the pre-call current bank identity.
Do not search for a persistent wrapper field or reuse a stack address after return.

### Work-wrapper initialization contract

The earlier static construction finding now has
[512 original-instruction checks](../../native/snow_host/work_wrapper_init_validation.json):
all 256 prior flag-byte values, each with null and non-null component current bank.
The check compares the entire synthetic stack region, including bytes that must
remain untouched, and verifies the captured-current and sentinel registers.

`initialize_pose_work_descriptors` exposes these initialized fields without
addresses. Both wrappers refer to the supplied component, have no alternate bank,
point their scratch storage at their own inline region, and receive header 32772
and index 65535. Input primary is the captured component current bank; output
primary is null. Each flag byte becomes `oldFlags & 248`, preserving the upper
five bits. The surrounding scratch contents are not initialized by this slice.
The encoded header's subfield semantics remain unresolved.

The public representation leaves scratch contents absent and preserves explicit
prior flag inputs. It does not model an all-zero native object. Native stack
addresses are temporary; the symbolic component/bank references in the reference
implementation do not establish native lifetime. Packet time and work-mode inputs
are assigned by surrounding code and remain outside this initialization contract.

### Bounded work-packet observation

`engine.pose_work_observation.capture_pose_work_packet` reads the packet and two
wrapper headers through a supplied read-only transport. The caller must supply
a packet address valid during the work call, a freshly verified component/entity,
the expected skeleton table, and 1–16 external identity guards. It verifies table,
owner and both wrapper component links, retains all spans, and rereads them before
returning. Short reads, nonfinite packet time, aliased wrappers, and changed spans
are refused. Scratch payloads and bank contents are not read.

Results contain no addresses. They report bank presence/current-bank comparisons,
inline-storage relationships, encoded headers, indices, flags and stored packet
time. `initialization_pattern_matches` describes only agreement with the decoded
initialization pattern. Populated output is allowed but no longer matches that
pattern. Neither result establishes callback execution, writer identity, atomicity
or lifetime. The time value is reported as stored; its clock/units are not asserted.

Five synthetic tests cover initialized/populated states, component mismatches,
mutation of packet/wrapper/external guards, truncated reads and invalid values.
Transport attachment, call-time packet acquisition, and original-game validation
remain pending. In particular, sequential rereads cannot make a stale stack
address safe or detect an ABA reuse that restores the same bytes.

### Debugger boundary adapter for work packets

`capture_pose_work_boundary` maps a signature-verified work-call stop to the
reader. At the inspected caller sites, RDI identifies the supplied component and
RSP+48 addresses the packet. Unrelated components are filtered before memory
access. The adapter requires integer registers and valid address ranges; it
does not verify the instruction site itself or attach a debugger.

The private bounded LLDB observer now has an optional work-packet mode, separate
from its older animation-interface packet mode. It requires a component filter
and 1–16 identity guards, retains existing signature checks, bounded hardware
breakpoints and cleanup, and invokes the reader at accepted stops. Raw register
receipts remain private; the embedded work observation has no addresses.

Seven synthetic reader/adapter tests pass, including no-read filtering and
caller-stack derivation. The modified observer passes Python compilation.
This new mode has **not** passed a native debugger fixture or original-game
capture. Existing debugger-fixture evidence for the older packet mode does not
validate this mode. Next build a synthetic caller with two work wrappers at the
same stack-relative layout, mutate output during its callback, and verify bounded
before/after observations plus breakpoint removal and detach under Wine/LLDB.

### Work-packet debugger fixture validation

The subsequent isolated Windows x64 fixture under Wine/LLDB passed all 14 checks.
Its synthetic caller places the packet at caller RSP+48, keeps the component in
RDI, and alternates selected/unrelated components. Each selected call starts with
an empty output wrapper; its callback populates the output primary bank. The
observer captured three ordered before/after pairs, with initialization matching
before each call and not afterward. Output/current-bank equality changed false
to true, while stored packet time remained 0.125. Unrelated stops were filtered.

Both hardware breakpoints were removed, code signatures were unchanged, detach
succeeded, and fixture/debugger exited normally with no cleanup error or outer
timeout. The [aggregate receipt](../../native/snow_host/pose_work_debugger_fixture_validation.json)
records checks and private source/receipt hashes without raw addresses. An earlier
runner attempt rejected the fixture's hexadecimal identity format before attach;
that parser was corrected before this successful run.

This validates the new observer mode against a synthetic native caller, not the
game. The fixture does not execute original animation routines. Next acquire a
fresh player skeleton, verify the actual work-call signatures and component
identity, and attempt the bounded call-time capture. Debugger stops perturb
execution; their elapsed time must not be used as ordinary animation timing.

### Fresh exact-skeleton acquisition for the debugger capture

The private original-game capture runner now supports a separate work-packet mode.
It first performs fresh player membership and exact-type skeleton binding, checks
retained binding spans, and records a private same-session debugger target. Guards
include the skeleton table/owner, selected component slot, entity component-array
header, actor/entity link and entity/world link. Absolute pointers remain private
and are never reusable across sessions.

The work mode uses the two inspected virtual-call boundary signatures, each
checked against the hash-verified analysis image during preparation and rechecked
by the observer in the stopped process before setting hardware breakpoints. It
uses the skeleton component filter and the work-packet reader, rather than the
older animation-interface component/packet convention. It requires at least
100 seconds of the supplied game watchdog budget before acquisition and 70
seconds remaining before attachment. A changed host PID aborts the attempt.

Both modified private scripts pass Python compilation; both boundary signatures
match the analyzed image. This is capture preparation, not live evidence. No
original game was launched in this pass. The next bounded launch must supply its
actual watchdog deadline and inspect observer cleanup and post-detach game state.

### Partial live work-call evidence and debugger failure

The subsequent bounded `work-packet` launch reached gameplay and freshly acquired
the exact player skeleton at component index 38 of 43. The observer recorded two
consecutive before/after pairs, each matching thread, component and caller stack,
on two different task threads. A third entry was unmatched. The
[partial live receipt](../../native/snow_host/pose_work_partial_live_observation.json)
retains address-free observations and the failed experiment status.

Both complete pairs matched the initialized wrapper pattern before the call.
Afterward, output primary and alternate banks were both present, distinct, and
the output primary differed from component.current. Input primary continued to
match component.current. Inline-storage/header/index fields remained consistent.
This establishes observed work-call boundaries for the freshly bound player and
output population during those calls. It does not identify a particular parent
setter or prove the later success-gated publication branch ran.

After the fifth hit LLDB reported `resume request failed - process already running`.
The cleanup code read then failed because the process was running, and LLDB exited
with signal-abort status. No breakpoint-removal or detach receipt exists. Thus
the live observer workflow failed despite useful partial observations. The outer
runner closed its game session, restored settings and verified the original DLL;
this is session containment, not successful debugger cleanup. No ordinary
post-detach stability result is claimed. Packet times must not be interpreted as
normal frame times under debugger stops.

The runner now requires explicit successful debugger exit, breakpoint removal,
unchanged code and detach before accepting this plan. The launch passes its actual
watchdog deadline into acquisition. Next reproduce the asynchronous stop/resume
failure with a multithreaded synthetic fixture before another game attachment.
The single-threaded fixture does not cover the task-thread transitions observed here.

### Multithreaded fixture did not reproduce the resume failure

The fixture now supports three Windows worker threads sharing immutable component
identity while each constructs its own stack packet/wrappers. The original
single-thread mode remains available. A six-hit trial passed, followed by an
expanded 24-hit trial that captured 12 matching thread/component/stack pairs
across all three workers with no unmatched entry. The
[aggregate receipt](../../native/snow_host/pose_work_multithread_fixture_validation.json)
records all 15 checks and explicitly marks the game failure as not reproduced.

Initialization/output transitions and stored time were correct. Both trials
removed breakpoints, verified unchanged code, detached and exited normally.
The expanded test permits global interleaving rather than requiring alternating
before/after events across different threads. Pairing remains thread-local.

This narrows the diagnosis: switching among three task-like threads is not by
itself sufficient to trigger the observed failure in this fixture. It does not
rule out a stop-state race, higher stop pressure, Wine-specific activity, or an
LLDB fault. The retained LLDB diagnostic log contains only a shared-cache warning,
not an abort backtrace. No fix or safe game reattachment is established. Next
instrument the observer's stop IDs, process states and resume transitions in the
fixture, then test cleanup when resume explicitly fails; do not silently accept
an already-running error or delete breakpoints while state is uncertain.

### Resume transitions and forced-failure cleanup

The private observer now records state and stop ID before each Continue, its
result, cleanup stop checks, and the state before code verification/removal. It
refuses removal if state is no longer stopped or terminal. A fixture-only runner
argument raises an explicit observer exception immediately after a successful
Continue; this injection is not accepted from game capture configuration.

The [transition receipt](../../native/snow_host/debugger_resume_transition_validation.json)
contains an 11-check forced-failure run and a 15-check normal 24-hit three-thread
run, both with clean fixture exit, breakpoint removal and detach. In the forced
run, Continue returned success while GetState still reported stopped with stop
ID 1. Cleanup shortly afterward observed running, requested Stop, and confirmed
stopped with ID 2 before removal. This is direct fixture evidence that the
asynchronous state report can lag a successful resume.

It supports a stale-state race as a lead for the game error but does not reproduce
that error or prove its root cause. The injected exception is an authored test,
not a failed native Continue. Current instrumentation detects a state change
before removal but cannot atomically pin LLDB state across calls. Next replace
implicit stopped-state assumptions after resume with explicit transition tracking
and exercise the cleanup race in the fixture before another game attachment.

### Explicit resume-stop generation guard

`engine.debugger_stop_state.ResumeTransition` is authored tooling policy. Before
attempting Continue, the observer records the current stop ID. A later stopped
report is accepted only if its stop ID is strictly newer. This rule applies to
normal stop processing, another resume, and cleanup. A successful Continue cannot
leave its old stopped report eligible for memory inspection or breakpoint removal.
The attempt is recorded even if Continue reports failure, because the process may
already be running. The original error remains an error rather than being ignored.

Cleanup waits up to three seconds for a newer stopped state or process termination.
If running is observed, it requests Stop once. If the transition remains unclear,
it reports cleanup failure and skips breakpoint removal rather than acting on the
stale stop. The outer bounded runner remains responsible for session containment.
Separate LLDB queries are still not atomic; this rule closes a specific stale-ID
assumption, not every debugger race.

The [guard receipt](../../native/snow_host/debugger_resume_guard_validation.json)
records three deterministic policy tests, the native forced-failure cleanup with
11 passing checks, and normal 24-hit multithread observation with 15 passing checks.
All native fixture sessions detached and exited cleanly. No game was launched in
this pass. The prior game failure remains unreproduced and is not claimed fixed.

### Guarded live retry still fails at a newer stop

The next bounded game session reproduced the resume failure with the stop-ID
guard enabled. Fresh skeleton acquisition succeeded. One matched work-before/
work-after pair showed empty output becoming populated; another entry was
unmatched. LLDB again exited with abort status without breakpoint removal or
detach. The outer runner stopped its session, restored settings and verified the
original DLL. The [retry receipt](../../native/snow_host/pose_work_resume_guard_live_retry.json)
preserves failure and state transitions, not a successful capture claim.

The new logs narrow the failed assumption. The last successful Continue began at
stop ID 8. The rejected Continue followed a stopped report with newer ID 9, so the
generation guard admitted it. No hit or trace event was emitted for ID 9 before
that resume attempt. Two trace stops had appeared earlier at ID 7. Thus the
observer can try Continue after a newer stopped report with no recognized thread
stop reason. A newer ID alone is insufficient evidence that this is a stable,
user-visible stop under this Wine/LLDB combination.

The reader's partial player observations remain evidence, but this debugger path
must not be treated as fixed. Next distinguish owned breakpoint events from
internal/trace/transitional stops and inspect event-driven stop delivery in an
isolated fixture. Do not repeatedly attach to the game on the strength of the
single-thread or three-thread fixture successes. No causal claim about game
protection or intentional termination is supported by these logs.

### Reasonless stopped reports are deferred

The observer now snapshots thread stop reasons before consuming a new stop ID.
If every reason is None, it logs one deferred event for that ID, waits, and does
not call Continue or mark that stop consumed. It can therefore inspect the same
ID again when reasons become available. Before reading registers/packets it also
rechecks that the process remains stopped at the same ID. Deferred distinct IDs
are bounded at 128 and the existing observation deadline still applies.

An explicit fixture-only injection hides the first meaningful reason snapshot.
The [18-check native receipt](../../native/snow_host/debugger_empty_stop_validation.json)
confirms that this ID was deferred, later produced a hit, and had no intervening
Continue. The three-thread run captured 24 observations, matched 12 pairs with no
unmatched entries, and removed breakpoints/detached/exited cleanly.

This eliminates the demonstrated observer branch that resumed after seeing no
recognized stop reason. It does not reproduce the underlying Wine behavior or
prove game-session stability. Trace-only handling still resumes under the older
bounded trace policy and must be examined separately; genuine unstable cleanup
also remains unresolved. No game attachment was made in this validation pass.

### Trace stops terminate observation rather than automatically resuming

The earlier trace-count policy is superseded. A trace stop now emits its record,
reports an explicit refusal error, and enters cleanup without another Continue.
The observer must not interpret an internal stepping stop as an ordinary owned
breakpoint merely because it has a new stop ID. Existing evidence captured before
the refusal remains partial; the original-game runner rejects the experiment.

The [11-check fixture receipt](../../native/snow_host/debugger_trace_refusal_validation.json)
uses an explicit fixture-only substitution of the first breakpoint reason with
Trace. It confirms the refusal, no subsequent resume, unchanged code, breakpoint
removal, detach and normal fixture/debugger exits. This validates the authored
decision path on a stable synthetic breakpoint; it does not reproduce Wine's
internal trace machinery or prove cleanup safe in the original failing state.

The game remains closed. The next investigation should inspect actual debugger
event delivery and internal stop/resume ownership in fixtures, or pursue static
work-callback reconstruction while that tooling issue is open. Repeated live
attachments are not a substitute for resolving this failure boundary.

### Owner-scalar bank preparation

The preparation service used by the alternate-bank wrapper now has a joined
reference, `prepare_owner_scaled_bank`, and
[192 original-instruction cases](../../native/snow_host/owner_bank_scale_validation.json).
If wrapper flag bit 1 is set, it returns the supplied bank without reading the
owner scalar. Otherwise it reads the component owner's stored scalar, computes
`abs(float32(scalar - 1))`, and compares against float32 0.00001. Outside that
tolerance, a nonzero profile primary-record count enables scaling of both arrays.
Zero primary count skips even a nonempty secondary array. The wrapper bit is set
after preparation, including tolerance/zero-count skips.

```text
if wrapper.flags & 2: return bank
s = owner.scalar
if abs(float32(s - 1)) > float32(0.00001):
    if bank.profile.primaryCount != 0:
        for record in primary[0:primaryCount]:
            record.lanes[0:4] = float32(record.lanes[0:4] * s)
        for record in secondary[0:secondaryCount]:
            record.lanes[0:4] = float32(record.lanes[0:4] * s)
wrapper.flags |= 2
return bank
```

This finite-input pseudocode includes W in the scaled first four lanes and leaves
the second four lanes of each 32-byte record unchanged. Aliased arrays are visited
twice over their respective ranges, so overlapping records scale twice. Tests
exercise zero/negative/fractional/large finite scalars, near-one tolerance, counts
0/1/3, secondary counts 0/2, aliasing and already-prepared flags. The actual
preparation, threshold checks and both loops execute without substituted services.
Nonfinite scalar behavior is outside this receipt's validation scope.

The owner scalar's gameplay units and connection to rider size remain unproved.
This closes the local preparation arithmetic, not live selection of this path.
The reciprocal preparation helper and lifetime of the once-prepared flag remain
separate investigation targets.

### Reciprocal bank preparation and round trips

`remove_owner_bank_scale` implements the paired path. It returns immediately if
wrapper bit 1 is clear. Otherwise it rereads the owner's current scalar. Outside
the same near-one tolerance, it computes float32 `1 / scalar` and sends that to
the shared scaling helper, which performs its own near-one tolerance check and
primary-count gate. Finally it clears wrapper bit 1. No original scalar is saved.

```text
if not wrapper.flags & 2: return bank
s = currentOwner.scalar
if abs(float32(s - 1)) > float32(0.00001):
    scaleBankWithOwnToleranceAndCountGate(bank, float32(1 / s))
wrapper.flags &= ~2
return bank
```

The [192 reciprocal cases](../../native/snow_host/owner_bank_unscale_validation.json)
and [192 joined forward/removal cases](../../native/snow_host/owner_bank_scale_roundtrip_validation.json)
execute both actual loops and threshold paths without substituted services. They
cover finite nonzero scalars, prepared/unprepared flags, zero and nonzero counts,
separate and aliased arrays. Of the 96 joined cases starting unprepared, 14 fail
to restore all original record values exactly despite using the same scalar in
both directions. The reference matches those rounded outputs; it does not replace
them with an ideal inverse. Zero/nonfinite reciprocal arithmetic is outside these
receipts' validated scope.

A separate synthetic reference test changes the scalar from 2 to 4 between calls;
the resulting first lanes are half their original values. That is a consequence
of rereading the scalar, not evidence of a live game transition. Modding APIs must
not assume this pair is a reversible transaction or change owner scale between
the two phases without understanding the caller's lifecycle. Live ownership of
the scalar and the actual invocation cadence remain unresolved.

### Opposite bank selection and flag lifecycle

`select_converted_owner_bank` reconstructs the opposite selection route with
[64 instruction cases](../../native/snow_host/opposite_bank_selection_validation.json).
It acquires a missing alternate when primary bit 26 is **clear**, using the
wrapper's stored uint16 index and request low bit. It does not clear acquired bit
26. Destination/source are selected oppositely to the parent-publication route.
Mode is read before conversion. A newly acquired alternate bypasses the source
readiness gate; otherwise absent source or clear source bit 27 skips conversion.

```text
created = false
if not primary.flags.bit26 and alternate == null:
    alternate = acquire(component.pool, wrapper.index, wrapper.flags & 1)
    created = true
destination, source = primary, alternate
if not destination.flags.bit26: swap(destination, source)
mode = (component.flags16 >> 3) & 7
if created or (source != null and source.flags.bit27):
    convert(source, destination, mode)
    wrapper.flags |= 2
    source.flags &= ~(1 << 27)
    destination.flags &= ~(1 << 27)
return destination
```

The tests execute the complete selector while supplying acquisition and conversion
services. Synthetic conversion mutations verify that the later bit operations
preserve other newly written flags. The conversion mathematics are reconstructed below. Real allocation remains
an unresolved service boundary; the selector receipt still supplies conversion
as a stub. This establishes that wrapper bit 1 can
also be set after conversion, not only by explicit owner scaling. Therefore a set
bit alone does not prove the scale-preparation routine ran. The nearby scale-on-
selection helper skips explicit scaling when this selector has already set the
bit; its full joined behavior remains a next validation target.


### Parent-relative bank conversion

`reference.animation_hierarchy.decompose_bank_hierarchy` reconstructs the
converter called by opposite bank selection and successful work publication.
The [192-case instruction receipt](../../native/snow_host/relative_hierarchy_validation.json)
executes the complete converter without service stubs on synthetic banks. It
checks exact record bytes, destination flags and parent-header copying. Public
unit tests replay those observations without the private executable.

Each record contains a four-lane position and XYZW quaternion. Root is processed
regardless of metadata rank. For later records, rank greater than the supplied
three-bit mode skips `skip_span + 1` records, preserving destination contents.
Otherwise the operation is:

```text
parent = source[metadata[index].parent]
delta = float32(source[index].position - parent.position)
inverse_rotation = conjugate(parent.rotation)
position = recovered_quaternion_transform(delta, inverse_rotation)
rotation = recovered_quaternion_product(inverse_rotation, source[index].rotation)
norm2 = float32(float32(x*x + z*z) + float32(y*y + w*w))
seed = RSQRTSS(norm2)
factor = float32((3 - float32(float32(seed * norm2) * seed)) * float32(0.5 * seed))
destination[index] = position, float32(rotation * factor)
```

The executable reference preserves the transform's float32 operation order and
fourth-lane behavior through `provider_pose_transform`; the pseudocode above is
an explanatory outline. It uses a conjugate, not division by the parent's
squared norm. The root uses identity parent rotation and its original position,
then normalizes rotation by the same refinement. The reference accepts a supplied
reciprocal-square-root seed function. Receipt replay uses emulator-observed seeds;
this does not prove matching approximation bits on every physical CPU.

Null destination selects the source bank. With aliasing, forward traversal reads
parents after earlier writes. For identity rotations and X positions 2, 5, 9 in
a three-node chain, separate output produces child X values 3 and 4. In-place
output produces 3 and 6 because the last node reads its parent's converted X.
The public helper models this internally without mutating caller-owned lists.

For nonempty banks, the native routine also copies the source's 32-byte parent
header to destination, clears destination bit 27 and sets bit 26. Empty banks
return without these operations. The record helper returns records and traversal
diagnostics only; callers modeling whole banks must apply these header/flag rules.
The instruction receipt checks distinctive header sentinels for empty, separate,
null-destination and explicit-self cases.

Bounds checks, preceding-parent requirements and finite nonzero rotation limits
are authored inspection safeguards. Synthetic ordered metadata validates local
arithmetic and control flow, not the complete live rig, coordinate-frame meaning,
allocation lifetime or animation selection. The joined selector/converter path is validated below with allocation still supplied.


### Joined relative bank selection

The [joined 192-case receipt](../../native/snow_host/joined_relative_selection_validation.json)
executes the original opposite selector and complete relative converter in one
instruction run. Only allocation is intercepted to return a synthetic bank.
The public composition uses `select_converted_owner_bank` with
`reference.animation_hierarchy.convert_relative_pose_bank` as its conversion
service. It supplies metadata and an opaque immutable 32-byte parent header
alongside each bank's records and flags.

Validation covers all combinations of primary bits 26/27, alternate presence,
alternate readiness, counts 0/1/3/8 and modes 0/3/7. It checks returned identity,
acquisition arguments, installed alternate identity, every bank's record bytes,
parent headers, final bank flags and wrapper flags. Approximate normalization
uses captured emulator RSQRT seeds. The public test replays synthetic inputs and
recorded results; it does not execute original instructions itself.

When conversion is selected for an empty bank, the converter writes nothing,
but its caller still sets wrapper bit 1 and clears source/destination bit 27.
For nonempty input, the converter first sets destination bit 26, copies the
parent header and writes selected records. The caller's later readiness clear
preserves bit 26. The allocation-created route runs conversion regardless of
source readiness; a missing alternate with primary bit 26 set returns primary
without acquisition or conversion.

This removes conversion as a stub from the selector validation. Allocation,
real bank capacity/lifetime and active player call cadence remain unproved.
The adapter mutates caller-supplied bank dictionaries for offline reconstruction;
it is not a live-game animation setter or a scheduling guarantee.


### Selection followed by owner scaling

`reference.skeleton_parent_transform.select_owner_scaled_bank` composes opposite
bank selection with conditional owner preparation. The [192-case joined
receipt](../../native/snow_host/scaled_relative_selection_validation.json)
executes the complete original selection helper, selector, converter and scaling
arithmetic. Only allocation is supplied. It checks all bank records, headers,
flags and returned/installed identities against the composition.

```text
bank = select_converted_owner_bank(wrapper)
if not wrapper.flags.bit1:
    scale = wrapper.component.owner.scalar
    if abs(float32(scale - 1)) > float32(1e-5):
        scale_bank_first_four_lanes(bank, scale)
    wrapper.flags |= 2
return bank
```

The ordered finite-scalar predicate above is explanatory pseudocode; the
reference retains the original unordered comparison behavior. The helper reads
owner state after selection. Conversion sets bit 1, so that route suppresses both
scalar lookup and multiplication. If selection skips conversion and the wrapper
is not already prepared, scaling remains eligible. Even an empty bank ultimately
gets wrapper bit 1 set, while its record arrays stay unchanged. The bit therefore
reports preparation state, not proof that an owner scale was multiplied.

This receipt uses counts 0/1/3/8, modes 0/3/7, readiness/presence combinations and
finite scalar examples including zero, negative, near-one and nonunit values.
Secondary arrays are empty in this joined receipt. Separate owner-scaling tests
cover secondary arrays and their aliasing, but do not prove those combinations in
this joined caller. The reference composition requires the conversion service to
update the same primary/secondary record storage that scaling sees. The receipt
adapter bridges the pair-of-vectors hierarchy format to eight-lane scale records;
that bridge is our API design, not an original data structure.

Live scalar meaning, bank allocation/lifetime and active animation cadence remain
open. This helper operates on supplied offline bank state, not the live game.


### Animation bank pool reuse

The allocator's reuse branch now has an independent reference in
`reference.animation_bank_pool.reuse_pose_bank` and a [96-case instruction
receipt](../../native/snow_host/pool_reuse_validation.json). The original entry
resolves the component, extracts its three-bit mode and updates a pool stamp.
Those lookup/stamp services are supplied in the receipt. The scan and reuse
instructions execute directly. The copy service is also supplied, so this check
establishes call ordering and flags rather than copied pose arithmetic.

The argument previously labeled `index` by wrapper adapters is consumed as a
**request mask** here. Its low 15 bits participate in overlap tests and accumulated
state. Bit 15 has a separate role; a full uint16 value of 65535 sets a marker in
the second mask. Existing wrapper field names remain compatible, but must not be
interpreted as a simple array offset.

```text
for entry in pool.entries, in stored order:
    if entry.occupied_mask & request & 0x7fff: continue
    if (entry.representation_word & 1) != requested_representation: continue
    entry.occupied_mask |= request & 0x7fff
    entry.initialized_mask = (entry.initialized_mask & 0x7fff)
                             | (0x8000 if request == 65535 else 0)
    if entry.initialized_mask & request & 0x7fff:
        bank.flags = (bank.flags | bit26) & ~request & ~bit30
        copy_selected(bank, selected_source, mode, request)
        bank.flags &= ~bit27
    entry.initialized_mask |= request & 0x7fff
    entry.representation_word = (entry.representation_word & 0xfffe)
                                | requested_representation
    return bank
```

Names `occupied_mask` and `initialized_mask` describe these observed operations;
they are our names, not recovered type declarations. The copy condition tests
nonzero overlap with the second mask. It must not be inverted into a guessed
"copy missing channels" policy. For representation zero, source comes from the
component's direct bank; representation one follows its container to the bank.
The original function scans 16-byte entries. The reference accepts only binary
representation values, matching the known callers' low-bit arguments.

Tests cover zero, individual, combined, high-bit-only and full masks; second-mask
values with/without overlap; both representations; and zero/all-set bank flags.
The first candidate is rejected by overlap or representation and the second is
reused. Additional public synthetic tests cover first-match selection, preserving
copy-service mutations except readiness, and an explicit miss.

A miss returns `None` in the reference to expose the unresolved growth path.
The native miss path instead grows the table, allocates/constructs a bank and
initializes record storage. That path is not reconstructed here. Pool mask release,
stamp meaning, thread synchronization and actual bank lifetime remain open.
These local mask rules are not permission to retain live bank pointers across jobs.


### Animation bank release

`reference.animation_bank_pool.release_pose_bank` reconstructs the matching-bank
release routine. The [120-case instruction receipt](../../native/snow_host/pool_release_validation.json)
executes the whole routine with only its auxiliary container-clear service
supplied. That service's arguments are checked, including zero counts, stride
48 and four boolean arguments set to one. No storage deallocation semantics are
inferred from the service name.

```text
entry = first pool entry whose bank pointer equals requested bank
if no entry: return
bank.flags |= bit26
entry.occupied_mask &= uint16(~request_mask | 0x8000)
if (bank.auxiliary_mask & request_mask) and bank.auxiliary_count != 0:
    bank.auxiliary_mask &= uint16(~request_mask)
    if bank.auxiliary_count == 1:
        clear_auxiliary_container(bank)
        bank.auxiliary_count = 0
    else:
        bank.auxiliary_count -= 1
```

Release preserves occupied bit 15, initialized-mask state, representation and the
pool entry. It does not free the bank in this routine. The auxiliary mask/count
are separate fields from the pool masks and pose-record count. A zero auxiliary
count leaves that mask unchanged even when requested bits overlap. Count greater
than one decrements once per qualifying call, not once per set request bit.
The reference returns a boolean match diagnostic; the native caller does not
provide that public API contract.

The synthetic cases cover matched/missing bank identity, zero/low/combined/high/
full request masks, auxiliary overlap, counts 0/1/2/5 and preserved pool fields.
A separate public composition test releases and reacquires the same bank identity.
That composition is a reference test, not an original-instruction joined trace.

Static direct calls in the already studied pose-work caller reach this routine
while cleaning its temporary output and input wrappers. This connects the release
lead to animation work rather than merely a similarly shaped pool. The release
routine and allocator share the pool table/count layout and bank pointer field.
Exact caller ownership gates and release ordering still need joined validation.
Neither these static calls nor instruction emulation establish live lifetime,
thread safety, allocation growth or a safe pointer-retention period for plugins.


### Pose-work wrapper cleanup

`reference.animation_bank_pool.cleanup_pose_work_wrappers` implements the
output-then-input cleanup slice of the studied work caller. The [128-case
receipt](../../native/snow_host/work_cleanup_validation.json) runs that original
slice together with the actual pool-release routine. Allocation lookup and storage
free services are supplied; auxiliary bank counts are zero in this joined test.

For each wrapper, cleanup releases a non-null primary only when wrapper flag bit
2 is set. It then captures alternate and clears primary. A non-null alternate is
released regardless of that ownership flag. Each release uses the wrapper request
mask when the bank currently has bit 26 set, otherwise 65535. The first release
can set bank bit 26, so aliased references must observe that mutation before the
second mask is chosen. Do not precompute all release masks from an initial snapshot.

After bank release, cleanup clears wrapper bit 1 and nulls alternate. If header
bit 15 is clear and storage is non-null, it resolves the allocator and calls its
free service. It does not null the recorded storage pointer in this slice. The
initial wrapper header 32772 has bit 15 set, suppressing that free path for its
inline scratch. This gives the header bit an observed ownership effect, without
claiming the entire header encoding is decoded.

The receipt covers null/non-null banks, ownership flags, both header modes,
null/non-null storage, zero/partial/full request masks and shared bank identities
within and across wrappers. It checks exact event order, resulting bank flags,
pool occupied masks, cleared pointers and wrapper flags. Public replay also
checks that the model retains storage identity. The native slice does not validate
arbitrary hostile pointers; the synthetic cases supply valid memory.

This closes the earlier local caller-order gap. It does not establish allocator
internals, release concurrency, live timing or a safe animation-modification
window. Whole-job execution, including the virtual work service and allocation
misses, remains outside this joined receipt.


### Masked pose-bank record copy

`reference.animation_bank_copy.copy_masked_pose_bank` reconstructs the partial-
mask branch of the copy service used by pool reuse. The [128-case instruction
receipt](../../native/snow_host/masked_copy_validation.json) executes the original
entry and descriptor copy helper without service stubs on synthetic byte buffers.
The full uint16 mask 65535 selects a distinct bulk path and is explicitly refused
by this reference pending reconstruction.

If destination bank bit 26 is clear, the entry first copies the source's 32-byte
parent header. It then loops over the source profile's group count. For each
selected request bit, it reads a start descriptor index and a mode-dependent
length from the destination profile's group table. Group rows have a 14-byte
stride. The model retains a flat uint16 table: start is word `group*7`, length is
word `group*7 + mode + 1`. Modes 6 and 7 therefore access beyond a nominal row;
the reference preserves that indexing rather than inventing separate row storage.
Actual profile constraints for those modes remain unknown.

Each destination descriptor supplies a byte offset and a low-four-bit kind:

| Kind | Bytes copied at the same source/destination offset |
| --- | --- |
| 0 | 1 |
| 1, 2, 3 | 4 |
| 4 | 12 |
| 5 through 15 | 16 |

Selected descriptors are processed in stored order, and unselected bytes remain
unchanged. The function sets destination bit 27 even with no selected groups or
zero group count. This path is byte copying, not float conversion or interpolation.
The original helper has an unrolled loop plus a remainder loop; the receipt checks
both, all low-nibble kinds, high descriptor bits, modes 0 through 7, mask selection,
header gating and exact untouched bytes. Buffers are separate and aligned in this
receipt. Partial buffer overlap and malformed native metadata are not validated.
Bounds limits in the public reference are authored safeguards.

This recovers one previously supplied copy service branch. Pool reuse and this
copy implementation have not yet been instruction-tested together; full-mask
copy remains a separate gap. No authored pose or game asset bytes are included.


### Full-mask pose-bank copy

`reference.animation_bank_copy.copy_pose_bank` now dispatches both the masked
branch and the full-mask 65535 branch. The [192-case instruction receipt](../../native/snow_host/full_bank_copy_validation.json)
executes the full-mask entry, its bulk loops and the original trailing-byte copy
routine with no substituted services. The earlier masked-only helper remains
available and still refuses full masks; callers wanting both use the dispatcher.

The full path reads three uint16 boundaries from the source profile: first-region
end, second-region end and total size. It copies 32-byte records in the first
region, four-byte elements in the second and trailing bytes in the third. For
ordered boundaries, a first region divisible by 32, a middle region divisible by
four and separate buffers, this is equivalent to copying the contiguous prefix
`source.data[:total]` into destination. Destination bytes beyond total stay intact.
The reference enforces these layout constraints instead of emulating malformed
metadata. Partial buffer overlap remains outside the validated contract.

Like the masked branch, it copies the source parent header only when destination
bit 26 is clear, then sets bit 27. Mode does not select ranges on the full path.
Tests cover zero-length regions, first-region unrolling boundaries, middle-region
unrolling, tail sizes 0/1/16/17/33/129 and both header gates. All resulting bytes,
including trailing destination sentinels, match the original instructions.

Both copy branches now have executable local semantics. Pool reuse and copy still
need a joined instruction validation, and the offline session's JSON service policy
continues to record copy requests without executing them. No asset payloads or
native game-memory access are added by this implementation.


### Pool reuse with actual bank copy

The [96-case joined receipt](../../native/snow_host/pool_reuse_copy_validation.json)
executes allocator reuse and the actual partial/full copy service together.
Component lookup and stamp lookup are supplied; allocation misses are excluded.
The native copy entry and all selected byte-copy loops execute directly. Tests
compare pool fields, calls, bank flags, header and all data bytes.

Reuse sets destination bit 26 before copying, so the copy entry preserves that
bank's parent header. Copy sets bit 27, then reuse clears it after the call. The
final bank is therefore not equivalent to calling copy alone. The joined receipt
checks zero/partial/full masks, both representations and copy/no-copy gates.
Source routing uses the direct bank for representation zero and the container's
bank for representation one, with supplied valid synthetic component links.

The offline session now accepts explicit policy `copy_supplied_pose_bytes` to
execute these byte rules using named source descriptions in its input. Auxiliary
clear and storage free remain recorded external services. This adds actual pose
buffer copying to the inspection API without inventing allocation or treating
synthetic inputs as decoded game assets.


### New pool entry initialization

`reference.animation_bank_pool.initialize_pool_entry` reconstructs the 16-byte
slot initialization performed after the allocator finds no reusable entry. The
[60-case instruction receipt](../../native/snow_host/pool_entry_init_validation.json)
executes the growth-initialization slice with reserve supplied as a capacity-
sufficient service. The original code requests old count plus one, updates count,
initializes the appended slot and writes request metadata before bank allocation.
Prefix and suffix sentinels verify that existing entries remain unchanged.

The slot's first mask becomes `(old_mask & 0x8000) | (request & 0x7fff)`.
Its second mask becomes `request & 0x7fff`, with bit 15 set only for request 65535.
The representation word preserves all bits except bit zero, which receives the
requested binary representation. Bytes 6 and 7 remain untouched. The bank-pointer
field is zeroed at this stage. Thus initialization requires supplied backing bytes;
assuming an entirely zero-filled slot would discard observed preserved bits.

Tests cover old counts 0/1/3, zero/low/high/full masks, both representations and
all-zero/all-set backing bytes. This is a stage helper, not an implementation of
reserve, bank construction, allocation failure or a complete miss path. The
session still returns `allocation_required` on a miss.

Static continuation after allocation initializes the bank profile/data pointers,
sets bit 26 and invokes the copy service with request 65535, then clears bit 27.
The full-copy request is independent of the original partial allocation request.
This is a static lead, not yet a joined allocation-path instruction receipt.
Constructor services, TLS-initialized default transforms and backing-storage
allocation still need validation before the miss path can be implemented faithfully.


### Pose-bank constructor initialization

`reference.animation_bank_pool.construct_pose_bank_fields` expresses the fields
written by the bank constructor. The [96-case instruction receipt](../../native/snow_host/bank_constructor_validation.json)
executes the complete constructor, default-transform accessor on its initialized
TLS path, empty secondary-container resize and auxiliary initializer without call
stubs. The fixture supplies synthetic object backing and default-transform bytes.
It compares the entire 448-byte object, including all untouched bytes.

The constructor clears a pointer/word pair, copies a supplied 32-byte default into
the secondary transform, points secondary storage at the object's inline region
and sets its header to 32773 with count zero. It clears the work word, profile and
data pointers, auxiliary storage/header, auxiliary mask and auxiliary count.
Flags become `(prior_flags & 0x0b000000) | (1 << 26)`; selected old flag bits survive.
The main parent header and inline record contents are not initialized here.

The reference returns symbolic fields, with `own_inline_storage` representing the
self-relative storage pointer. Omitted fields are deliberately unspecified; this
helper must not be treated as a fully initialized pose bank. Field names are our
labels, and the supplied default is not silently assumed to be identity or an
extracted animation payload.

The allocator's later stages still attach a profile, allocate data, initialize
other fields and copy source contents. First-time TLS default initialization,
allocation failure and the complete miss path are outside this receipt. The
constructor's empty resize uses existing inline capacity and therefore does not
exercise the underlying allocator. Live thread ownership/lifetime remain open.


### Post-construction bank seeding

`reference.animation_bank_pool.seed_new_pose_bank` reconstructs profile/data
attachment, default transforms and full-copy seeding after bank construction.
The [24-case joined receipt](../../native/snow_host/bank_seeding_validation.json)
executes the setup slice, initialized TLS path, empty secondary reset and actual
full-copy routine. The data allocator is supplied as zeroed storage; constructor
count-zero state is a fixture precondition. The native slice also publishes the
bank pointer into its pool entry before allocating data, and returns that bank.

Setup attaches the pool profile, masks prior flags with `0xaf000000`, sets bit 26,
requests `profile.total_size` bytes and clears readiness. It stores the allocated
data pointer, initializes secondary/default transform state and clears the work
word. It writes the default parent header, sets bit 26 and masks flags with
`0xbfff0000`, then copies with request 65535 and finally clears bit 27 again.
The reference's allocation callback must return sufficient storage; its rejection
of missing/short storage is an authored safeguard, not recovered failure handling.

The default parent header survives source copying because destination bit 26 is
already set. Consequently new-bank setup copies source data bytes without cloning
the source parent header. The receipt uses deliberately different default/source
headers, sizes 0/32/48/85, modes 0/7 and several prior flag patterns. It checks both
transforms, all data bytes and trailing sentinels, final flags, profile/data pointer
attachment, pool publication and returned identity.

Static inspection of the data allocation helper shows a zero-size branch and a
post-allocation zero-fill call. That helper's heap services, failure handling and
profiling branch remain unvalidated here. First-time TLS initialization, nonempty
secondary reset and the entire miss path from scan through construction are still
separate boundaries. The public session continues to report allocation misses;
this stage helper does not silently turn them into a fabricated native allocator.


### Joined successful pool allocation miss

The [40-case instruction receipt](../../native/snow_host/pool_miss_join_validation.json)
executes the complete allocator entry on a miss through slot initialization,
original bank constructor, profile/data setup and actual full-copy seeding.
Component lookup, stamp lookup, table reserve, allocator selection and successful
bank/data allocation are supplied. Constructor and post-construction TLS accessors
execute their already-initialized paths. This joins the earlier staged evidence;
it does not reconstruct the underlying heap or claim all failure paths.

Cases cover empty/nonempty tables, request masks 0/1/3/32768/65535, both
representations and zero/all-set backing bytes. Nonempty cases have an existing
entry with the opposite representation, forcing a genuine scan miss. Checks
include preserved prior entries and trailing sentinels, appended slot masks,
updated table count, returned bank identity, parent/secondary transforms, complete
copied data and final flags. The observed service sequence is component lookup,
stamp lookup, reserve, allocator selection, bank allocation, constructor, data
allocation and full-mask copy.

The appended entry retains the request mask while its new bank is initialized by
a full-mask copy regardless of that request. Parent transforms retain the supplied
default rather than the source header. Public tests replay the slot, constructor
and seeding composition against these observations. Lookup and heap effects stay
explicit dependencies; the inspection session still reports allocation misses.

Reserve is capacity-sufficient and does not relocate in this receipt. Null/failed
allocation, zero-sized data allocation, first-time TLS setup and concurrent pool
use remain unvalidated joined boundaries. The actual raw object and source data
are private/synthetic respectively; no game payload is distributed.


### Pool relocation and null-allocation boundaries

The [40-case relocation receipt](../../native/snow_host/pool_relocation_validation.json)
repeats the successful miss path while the supplied reserve service moves the table
to different storage and poisons the old table. Constructor and copy instructions
still execute directly. The caller reloads table storage after reserve, initializes
and publishes the appended bank in the new table, and leaves the poisoned old
storage untouched. This verifies the caller's relocation handling, not reserve's
allocation algorithm or synchronization.

Two fault-injection receipts supply null instead of a successful allocation:
[bank allocation](../../native/snow_host/pool_null_bank_validation.json) and
[data allocation](../../native/snow_host/pool_null_data_validation.json). In each,
the actual instructions reach an invalid low-address access before returning.
The bank case reaches a four-byte access; the nonzero-size data case reaches an
eight-byte access during subsequent copying. These observations establish no
local null recovery before the fault in these tested paths. They do not execute
OS exception dispatch, prove game-process termination or determine whether native
allocation contracts allow null in practice.

The independent reference retains explicit allocation validation and raises on
missing/short supplied storage. That is an authored safeguard, not emulation of
an original recovery branch. A future mod API must report allocation failures
rather than claim that this caller recovers from them. Zero-size data allocation,
first-time TLS and concurrent reserve/release remain separate questions.


### Explicit-service acquisition API

`reference.animation_bank_pool.acquire_pose_bank` composes reuse and successful
miss construction behind supplied services. It first tries reuse. On a miss,
`reserve_slot(new_count)` supplies the appended slot's backing bytes. The model
initializes masks, appends a null-bank entry, calls `allocate_bank(448,16)`, applies
constructor fields, publishes the bank, then seeds it using `allocate_data(size)`.
`copy_selected` supplies the reuse-copy service; new-bank seeding always uses the
reconstructed full-copy implementation.

The Python list, dictionaries and symbolic pointers are authored representations.
The API is replay-tested against both fixed-table and relocated-table miss receipts,
including mask bytes, flags, source contents and publication ordering. It does not
implement heap allocation, physical table movement or native lifetime management.
Callers provide actual allocation policy and default-transform bytes explicitly.

The API raises on invalid supplied allocation instead of reproducing the observed
native invalid accesses. This is an authored guard, and there is no rollback.
A failed bank allocation leaves an appended null-bank entry; failed data allocation
can leave a published bank with a profile but no data. Callers must abandon or
repair that state explicitly rather than continuing as though acquisition succeeded.
Count overflow and allocator-returned aliases to existing banks are also refused.

A runnable synthetic demonstration allocates once, copies data, releases the request
and reacquires the same identity:

```sh
python3 -m engine.examples.animation_pool_allocation_demo
```

Its allocation callbacks are labeled synthetic. The JSON inspection runner retains
its explicit `allocation_required` behavior; no automatic allocator is silently
introduced into existing scenarios.


### Attached-profile copy integration

The copy reference now resolves layout metadata through `bank.profile` when
present, matching the native profile pointer. Earlier flat fixture inputs remain
supported only when no profile is attached. An attached profile takes precedence
over stale flat fields. Source profile supplies group count/bulk boundaries;
destination profile supplies group words and descriptors.

An integration regression exposed the former mismatch: allocation attached a
profile, but the isolated copy helper expected top-level metadata, so a constructed
bank could not complete a subsequent partial-copy cycle without manual flattening.
The fixed API passes create, release, partial reuse and copy-as-source tests.
A second test changes profile descriptors between calls and verifies that current
profile metadata is used. Existing native-receipt replays remain unchanged.
These are public composition tests, not additional native instruction cases.

Profiles are shared supplied metadata, not copied per bank or guessed from records.
The runnable allocation demo now performs full-copy initialization followed by
partial-mask reuse using an attached profile. Missing profile fields remain errors;
no default channel layout is fabricated.


### Concrete pose-work interface dispatch

The existing [Kino factory/type chain](ANIMATION_COMPONENT_DISPATCH.md) identifies
the stored animation-interface subobject. Its work slot selects a concrete wrapper,
now reconstructed by `reference.animation_work_dispatch.dispatch_pose_work`.
The [32-case instruction receipt](../../native/snow_host/pose_work_dispatch_validation.json)
executes that wrapper with preparation and downstream evaluation supplied.

```text
owner = interface.owner
if owner == null: return 0
prepare(owner.context, float32_bits=0)
return evaluate(interface.owner, packet.input, packet.output,
                packet.time_bits, extra_work_byte)
```

Preparation receives positive zero rather than the packet interval. Owner and
all packet fields are loaded again after preparation. Synthetic callback mutation
checks demonstrate that evaluation sees replacement owner/input/output/time.
The return low byte is forwarded, including values other than 0 and 1; the work
caller subsequently tests it for zero. The reference transports time as raw float32
bits, preserving signed zero and NaN payload examples without inferring units or
sanitization. An absent owner returns false without reading the packet.

The concrete downstream evaluator is now a precise static target. Preparation
walks context records and performs a locked publication/reset sequence before
that evaluator is called; its full effects are not reproduced by the wrapper
reference. The evaluator itself remains a supplied service, not an inferred
animation algorithm. Static identification of this interface does not prove the
same receiver was selected in every live gameplay state.

Private evidence anchors are work wrapper `14131c5e0`, preparation `141302850`
and evaluator `141301590`, reached through interface table `142909790` slot 0x60.
The earlier factory/type chain provides receiver provenance; these build-specific
anchors are research identifiers, not portable API fields or live pointer values.


### Pose evaluator output gates

`reference.animation_work_dispatch.pose_output_route` expresses three local gates
in the concrete evaluator. The [90-case instruction receipt](../../native/snow_host/pose_output_gates_validation.json)
executes those gate slices with supplied intermediate predicate results and result
headers. It is not a full evaluator execution and does not validate intervening
calls or their allocation effects.

```text
if extra_work_byte == 0 or owner_link == null:
    route = skip_extra_path
elif graph_predicate_low_byte != 0:
    route = predicate_skips_output
elif (result_header & 0x1fffffff) <= 1:
    route = insufficient_results
else:
    route = publish_output
```

The evaluator initializes its output-success byte to zero. On the producing path,
it prepares a destination descriptor around the caller's output wrapper, converts
results into it and invokes a completion helper before setting success to one.
The returned low byte comes from this success flag. Header high bits do not count
as results. Our route labels describe branches, not original enum names.

Static continuation after the optional output branch still processes selected
parameter groups, performs owner work and cleans temporary descriptors. Therefore
`skip_extra_path` does not mean the evaluator does nothing or that the interface
call is safe to omit. The unresolved graph predicate must not be replaced with a
constant or interpreted as a crash/landing test without tracing its body.

The next concrete leads are the graph predicate, graph evaluation, result-to-output
conversion and output completion. Private anchors: predicate `141291520`, graph
work `14126d930`, conversion `1412d2680`, completion `1412e64e0`, and subsequent
parameter processing `1412e99b0`. Output conversion receives a descriptor that
contains the caller's output wrapper. This gives a specific route to investigate
for pose production; it does not yet decode active clip selection or IK.


### Result-tree weight filtering

`reference.animation_result_filter.filter_result_records` reconstructs the
recursive filter called before output conversion. The [48-case instruction
receipt](../../native/snow_host/result_filter_validation.json) executes recursion,
comparison, record copying and span rewriting directly, with vector append and
truncate services supplied. Inputs are synthetic 24-byte records, not animation
assets or captured graph payloads.

Each record carries a float32 weight at byte 16, uint16 span at byte 20 and kind
byte at 22. The filter visits a record then advances by its span. Only weights
strictly greater than the threshold survive; equality or unordered comparison
with NaN rejects the record. Rejection skips its whole span.

Kinds 1/3/5/7 are recursive groups. A surviving opening record is appended, then
its interior `span - 2` records are filtered recursively. If any child survives,
the original closing record is appended and the opening span is rewritten to the
new output length. If none survives, the opening record is removed. Other kinds
copy their 24 bytes unchanged and still advance by the supplied span. No inferred
clip, additive-blend or IK semantics are assigned to these numeric kinds.

Tests cover all four group kinds, nested pruning, strict equality, positive and
negative thresholds, NaN thresholds and NaN leaf weights. The reference bounds
input size, spans and recursion depth as authored safeguards. Pointer-relative
vector storage and vector allocation internals are outside the receipt.

Static wrapper inspection shows a nonnegative clamp before invoking this filter,
then an attempted conversion of the filtered results. A false conversion result
invokes a fallback using the original unfiltered list. That wrapper orchestration
is the next joined-validation target; the filter alone does not select an output
bank or prove clip sampling behavior.


### Result conversion orchestration

`reference.animation_result_conversion.convert_result_records` now expresses the
normal-path wrapper around the result filter. Evidence is static instruction
inspection of `1412d2680`, not a joined native-byte validation or live pose test.
The separately validated recursive filter remains unchanged.

Contract: caller supplies 24-byte records, a float32 threshold, an opaque context,
an output descriptor, and explicit conversion/fallback callbacks. MAXSS with a
positive-zero second operand clamps negative values, negative zero and NaN to
positive zero; positive infinity survives. Filtering retains strictly greater
weights. The attempt runs even with zero surviving records, receiving start 0,
filtered count, output descriptor, weight 1.0, and two zero options. The weight
constant was checked in the inspected image at `141df3150`.

Only the returned low byte controls fallback. Zero invokes fallback with the
original unfiltered records and the same context/output descriptor. Thus a failed
attempt may have already changed the output; this wrapper does not roll it back.
A nonzero low byte skips fallback. The reference returns authored diagnostics;
the native wrapper's return value is not asserted to be a conversion status.

Tests cover NaN, signed zero, strict equality, infinite threshold, empty filtered
input, callback ordering, original-list fallback, and integer results with zero
low bytes. These are reference behavior tests, not instruction-emulation proof.
Unresolved dependencies remain explicit: attempted conversion `1412d2830`,
fallback `1412c8540`, temporary-vector allocation/cleanup, and output completion.
Python callback exceptions propagate; native exception behavior is not modeled.


### Fallback result selection

`reference.animation_result_fallback` reconstructs the fallback selector and
exposes its final publication as two explicit services. The [76-case instruction
receipt](../../native/snow_host/result_fallback_validation.json) executes the
original fallback, candidate resolver and maximum scan with direct and relative
vector storage. Only the final provider virtual call is supplied. All records
are synthetic; the public receipt replaces provider pointers with symbolic 99.

The outer loop visits roots by their uint16 spans. It resolves each root to a
candidate, compares the candidate weight strictly against a running maximum,
and keeps the first equal-weight winner. The maximum starts at the most negative
finite float32, and the selected index starts at zero. NaNs and negative infinity
do not improve it. Consequently a nonempty flat list whose weights never improve
the maximum still selects index zero, not an invented no-result status.

Resolution rules use numeric kinds only. Kinds 5 and 7 scan subsequent siblings
until closing kind 6 or 8, select the strict maximum, then resolve that selection
again. Kind 1 first advances one record: closing kind 2 immediately returns an
invalid candidate. Otherwise it scans starting one further record, stopping at
kind 4, and resolves the selected index again. Other kinds, including kind 3,
return directly. The scan advances by spans and also initializes its best index
to zero. A malformed/no-winning group can therefore cycle; the reference detects
that cycle as an authored refusal instead of silently choosing a substitute.

An invalid candidate cancels the entire outer fallback, including any previously
selected candidate. Empty input also produces no dispatch. A valid selected
record supplies two opaque uint64 values: its first word is stored in the context
at field +0x30, then its second word identifies the provider whose virtual slot
+0x80 is called with the output descriptor. `publish_fallback_result` preserves
this store-before-dispatch order through callbacks and never dereferences tokens.
No claim is made that the token names a clip or that the provider samples joints.

Private anchors: fallback `1412c8540`, resolver `1412eba60`, sibling scan
`1412ebba0`. Tests replay every receipt row, check publication order, initial-index
behavior, cycle refusal, and compose the previous failed-conversion wrapper with
this fallback. Bounds checking and returned index diagnostics are authored.
The provider implementation and attempted multi-result conversion remain open.


### Flat result pose accumulation

`reference.animation_flat_conversion.convert_flat_results` reconstructs the
kind-zero, unit-span path through the main converter. The [80-case instruction
receipt](../../native/snow_host/flat_conversion_validation.json) starts at the
actual converter entry and executes its loop, float arithmetic, dispatch choices,
weight reporting and success return. Provider evaluation, temporary preparation,
pose blend and cleanup are supplied services. It does not validate pose contents.

For each record, `weighted = f32(parent_weight * record_weight)`. The first
provider writes directly into the caller's output descriptor; later providers
write into a prepared temporary descriptor. Each later result blends into output
with `factor = f32(weighted / f32(weighted + accumulated))`. After each record,
`accumulated = f32(accumulated + weighted)`. The token is published before provider
evaluation. Provider dispatch receives output/temporary plus the same context.
This is sequential accumulation, not an independently normalized weight vector.

There is no denominator guard on this path. Zero weights can yield NaN blend
factors; signed weights can yield infinity. The reference preserves these cases
rather than silently replacing them. At completion, optional weight reporting is
MINSS(1, accumulated): a ceiling, not a lower clamp, with unordered comparisons
selecting the accumulated NaN. Empty input reports zero and returns false;
nonempty flat input returns true regardless of the provider's return register.
Temporary cleanup occurs on the normal completion path, including empty input.

Tests cover direct/relative vectors, parent scaling, sequential weights, zeros,
negative values, NaN and infinity. Group kinds are explicitly refused by this
API; it does not flatten a graph and claim equivalent output. Callback exceptions,
MXCSR trap/denormal modes, group conversion and actual provider/pose-blend bodies
remain outside the reconstruction. Python diagnostics and refusal bounds are
authored. Private anchors: converter `1412d2830`, leaf branch `1412d32f6`, blend
wrapper `1412eccd0`. The blend wrapper calls output completion for both descriptors
before invoking a bank-blend service; that service remains the next concrete lead.


### Pending animation completion groups

`reference.animation_completion.complete_pending_groups` reconstructs the
completion dispatcher called before blending. It is not itself a joint sampler.
The [96-case instruction receipt](../../native/snow_host/animation_completion_validation.json)
executes the actual entry, flag clearing, vector views and group traversal with
direct/relative storage. Vector cleanup and provider readiness/completion are
supplied services; synthetic descriptors contain no animation payloads.

The output descriptor's pending object is optional. Missing object or clear flag
bit zero returns immediately. Otherwise the pending byte clears bit zero before
any provider call. Descriptor pointers come from that object's owner list and
remain the iteration list. Only descriptor kinds whose low nibble equals 8 begin
a dispatch group. The provider is loaded using the descriptor's uint16 byte
offset into the current pending object's provider storage; this is a byte offset,
not an automatically scaled index.

A group starts at its kind-8 descriptor and ends just before the next descriptor
with marker 65535, or at list end. The boundary descriptor is reconsidered by the
outer loop. A missing provider or readiness low-byte zero skips the entire group.
Otherwise provider slot +0x28 receives output, the reloaded current pending object,
and the half-open descriptor range. Readiness uses slot +0x20 and the pending
object read before that call. The reference preserves the reload if a callback
changes the pending object, while retaining the original iteration list.

Normal repeat calls do nothing unless another producer rearms the flag. Exceptions
are not caught or rearmed by the Python adapter; native exception handling remains
unmodeled. Tests check group boundaries, high kind bits, declined providers, flag
consumption, callback replacement and every instruction receipt row. The callback
replacement test is reference-level evidence, not part of the native receipt.
The returned dispatch count and bounded-list guard are authored diagnostics.
Private anchor: completion `1412e64e0`. Remaining lead: concrete providers behind
slots +0x20/+0x28 and the producer setting the pending flag.


### Pending animation side-state copy

`reference.animation_pending_copy.copy_pending_state` reconstructs a concrete
pending-flag transfer path. The [32-case instruction receipt](../../native/snow_host/pending_copy_validation.json)
executes the complete copy routine with alias/nonalias objects and varied flag
bytes. Vector assignment is supplied; its allocation and deep-copy semantics are
not inferred. All unrelated destination bytes were checked for preservation.

Order: assign provider vector, copy only source flag bit zero into destination,
assign auxiliary vector, copy the uint32 word at +0x20. The destination's other
flag bits, owner link and reference count are preserved. Exact object aliasing
skips both vector services. Scalars are read after the corresponding services,
not all snapshotted beforehand. Public field names are authored; the copied
uint32 word and auxiliary vector's meaning remain unresolved.

This can rearm a destination that was already completed if its source is pending.
An integration test copies a pending source and then runs the completion dispatcher,
which consumes the destination flag while preserving the source. This establishes
flag propagation, not the first producer that marks new work pending. Callback
exceptions have no rollback in the reference; native unwinding is unmodeled.

Static call context: the side-state blend router `14130c6d0` invokes copy
`1412bf020` directly for mode 4 (first source), mode 5 (second source), or some
mode-6 branches. Other modes dispatch through `14130d450`. Mode names/semantics
and recursive descriptor blending remain unresolved. Temporary preparation
`1412f98d0` is lazy: an existing output bank skips initialization. Its empty-bank
path retains context handles and obtains a bank through service slot +0x70.
That preparation is a static lead, not yet a validated reference implementation.


### Temporary animation bank initialization

`reference.animation_temporary.prepare_temporary_bank` replaces the previously
opaque temporary-preparation step with a lazy lifecycle adapter. The [64-case
instruction receipt](../../native/snow_host/animation_temporary_validation.json)
executes the actual preparation and binding-assignment helper. Backend release,
retain and acquire calls are supplied; their concrete allocation behavior remains
unknown. Existing bank, missing bindings, null acquisition, byte modes and absent
backend handles are covered. The pending-completion field stays untouched.

A nonnull bank returns immediately without refreshing context or bindings. With
no bank, the descriptor stores the context's bank/auxiliary owners, assigns its
binding, copies the mode byte, marks ownership, and acquires a bank using owner,
retained binding, mode and zero option. Metadata then points at context base+160;
the reference represents this as an opaque base token and offset. A null acquired
bank is retained as null with ownership/metadata writes still applied. Later calls
retry initialization. There is no invented rollback or successful-allocation claim.

Binding assignment releases an existing binding through its owner, clears both
value/owner, copies the source owner, and retains a nonnull source value. Exact
self-assignment has no guard and therefore clears its own source; this alias case
is a reference test from static ordering, not included in the native receipt.
The adapter passes opaque owners to services, which are responsible for resolving
optional backend handles. Native backend absence forwards null to the service.

The reference rechecks ownership after binding assignment, preserving the branch
that can release a bank if a supplied service changed it. No such reentrant bank
mutation is claimed in the native receipt. Source/destination field names, return
identity and metadata tuple are authored interface choices. Provider sampling,
actual backend bank acquisition, final cleanup and grouped conversion remain open.
Private anchors: preparation `1412f98d0`, binding assignment `1412bf0a0`.


### Temporary animation bank cleanup

`reference.animation_temporary.cleanup_temporary_bank` supplies the matching
release path. The [48-case instruction receipt](../../native/snow_host/temporary_cleanup_validation.json)
executes reference decrement, reuse-list slot publication, ownership gates and
handle clearing, with pool append and backend release services supplied. All
unrelated descriptor bytes are checked unchanged.

Order: decrement the optional pending object's uint32 reference count; if it
becomes zero, append the object to its owner's reuse list; clear the pending
handle. Release a nonnull binding and clear binding value/owner. Release a nonnull
bank only when its ownership byte is nonzero; clear bank value, ownership byte
and bank owner regardless. Context metadata remains. A second normal cleanup has
nothing left to release. The count wraps on zero-to-minus-one; this is observed
arithmetic, not a valid-lifecycle recommendation or a repaired underflow policy.

The Python recycle callback represents append-and-store, not destruction. The
reference has no exception rollback or concurrency guarantee. Integration tests
run three flat result providers through lazy temporary preparation, reuse and
cleanup, observing exactly one temporary allocation and ordered binding/bank
release. Providers and blend remain supplied, so this proves API composition and
lifecycle ordering rather than pose accuracy. Private anchor: `1412bdfc0`.


### Animation service registry resolves opaque callback names

The [43-service registry](../../native/snow_host/animation_service_registry.json)
maps original registration strings to their callback-table setters. Each setter
was executed against a synthetic table and checked to modify only its assigned
slot. Name association comes from static constructor inspection, not emulation of
the registry hashing/lookup. The table global is null in the inspected image, so
these results do not establish installed runtime implementations.

This corrects earlier generic **retain** terminology: temporary binding assignment
calls **CopySelectionMask**, and release calls **ReleaseSelectionMask**. Reference
APIs now use `copy_selection_mask` for that callback. Historical synthetic receipt
labels still say `retain`; they name the supplied test service and do not prove
reference-count retention. Whether the concrete copy shares or duplicates storage
remains open. Do not conflate selection masks with the separately named blend masks.

| Observed slot | Registered service | Reconstructed call context |
| --- | --- | --- |
| 0x48 | CopySelectionMask | Temporary binding assignment |
| 0x60 | ReleaseSelectionMask | Binding replacement and cleanup |
| 0x70 | AcquireSkeletonPose | Lazy temporary bank initialization |
| 0x88 | ReleaseSkeletonPose | Owned temporary bank cleanup |
| 0xb8 | BlendSkeletonPose | Output and temporary bank blending |

The full registry also names local/global bone get/set, local-to-global pose
update, selection-mask intersection/union, multipass pose blend, effector snapshots,
prop transforms, and biped/quadruped/climb IK acquisition, release and solving.
These are concrete integration leads, not implemented or safe public game APIs.
The setter only accepts a function pointer; resolving the code registered by the
engine remains necessary before replacing our supplied service bodies.

Private anchors: registry construction `141262390`, global table `1433102b0`.
Constructor ordering is not slot ordering; the registry records actual setter
stores. Global/local transform setters, for example, occupy 0x108/0x100 respectively.


### Concrete animation service implementations

The engine registration sequence now resolves all 43 registry names to concrete
callbacks in the [service map](../../native/snow_host/animation_service_registry.json).
The actual sequence and actual setters were executed, with the registry name
lookup supplied. Each final table slot was checked against its registered function.
This proves the inspected registration mapping, not that those bindings are
installed in an active game process. Private registrar anchor: `140dddfe0`.

Selection masks are now executable value services in
`reference.animation_selection_mask`. The [36-case instruction receipt](../../native/snow_host/selection_mask_validation.json)
executes all six leaf services without stubs. Acquire returns 65535 for an absent
blend-mask object, otherwise the object's uint16 word at +0x40. Copy returns the
entire input uint64 unchanged. Intersection/union operate on low 16 bits; active
tests low 16 bits for nonzero. Release does nothing. Thus the earlier uncertainty
about heap copying/reference retention is resolved for these registered callbacks:
selection-mask copy neither allocates nor retains. High bits survive copy but not
intersection/union. The temporary lifecycle test now uses these concrete mask
services, with skeleton-pose acquisition/release still supplied.

Several registry names lead to stubs in this build: quadruped/climb acquisition
returns null, their release callbacks do nothing, quadruped solve returns false,
and climb solve does nothing. These static body observations do not prove that
other animation paths lack those capabilities. They do show why registration names
alone must not be advertised as functioning mod features.

Concrete next leads: AcquireSkeletonPose `140dd31e0` routes through `140dd6410`;
ReleaseSkeletonPose is `140ddeb90`; BlendSkeletonPose `140dd45a0` forwards to
`140dd3d10`. Selection-mask copy is `140d4b030`, and release is `14075e600`.
The named API-to-implementation gap is closed for this registration sequence;
pose-service body reconstruction and live object/thread requirements remain open.


### Concrete skeleton-pose acquisition

`reference.animation_pose_acquisition.acquire_skeleton_pose` reconstructs the
registered acquire service and wrapper initializer. The [48-case instruction
receipt](../../native/snow_host/pose_acquisition_validation.json) joins both original
bodies, supplying resource resolution/cache lookup, wrapper storage, and eager
bank allocation. All untouched wrapper bytes are checked. It does not validate
allocator concurrency or live object lifetime.

Backend resource flag bit 31 gates its payload. A nonnull gated payload goes
through a backend-specific lookup/cache service to obtain the component. The
allocated wrapper stores that component, clears primary/alternate banks, uses its
own inline scratch, sets header 0x8004, and truncates the selection mask to uint16.
Flags preserve the upper six bits, clear low bits zero/one, set bit zero from the
mode and set ownership bit two. Prior scratch bytes are not initialized.

An eager low byte of zero returns the wrapper without acquiring a primary bank.
Otherwise, when primary is absent, the service invokes the already reconstructed
bank allocator with component pool, wrapper request mask and representation bit.
The temporary lifecycle always passes eager zero, so its acquired pose object is
initially a lazy wrapper, not an allocated joint bank. A null wrapper is returned
on lazy allocation failure. The reference refuses eager null use with an authored
ValueError; no native recovery is claimed. Invalid-resource cases in the receipt
are lazy only, and eager missing-component behavior is not reconstructed.

Private path: registered acquire `140dd31e0` -> wrapper factory `140dd6410` ->
storage allocator `140dd6360`; eager bank acquisition reaches `140d85220`. The
storage allocator has a 25-slot inline free list and heap fallback, with a tagged
compare/exchange head; its concurrent policy is still unimplemented.

Static release tracing also joins known code: registered release `140ddeb90`
selects a wrapper pool and dispatches `140dd6a40`. Inline-pool and heap branches
both clear bank ownership through `140dde450`, whose primary/alternate mask rules
match the earlier pose-work cleanup. Wrapper recycling/heap freeing remain
unimplemented services; no new live release operation is exposed.


### Typed animation channel blending

`reference.animation_channel_blend.blend_channel` implements the regular typed
channel helper reached by the unmasked mode-zero pose blend. The [90-case
instruction receipt](../../native/snow_host/channel_blend_validation.json) executes
the original helper for every low-nibble kind except quaternion kind 6, without
stubs. Tests compare entire destination buffers. Finite synthetic scalar/vector
inputs, reverse integer differences and no-op kinds are covered.

An eight-byte descriptor supplies a uint16 data offset at byte four and kind in
the low nibble of byte six. Kind 1 performs float32 `a + weight*(b-a)`, rounding
subtract/multiply/add separately. Kind 5 performs the same four-lane formula with
supplied per-lane weights. Kind 4 performs three scalar lanes but loads both inputs
from source A: it computes `a + weight*(a-a)`, not ordinary interpolation. Finite
inputs are preserved; infinities/NaNs can differ from a raw copy. Do not repair
this observed branch without evidence of a different caller or variant.

Kinds 0 and 2 operate on byte/uint32 values. Difference and multiplication by the
supplied integer weight wrap modulo 2^32. The unsigned result is multiplied by
0x80808081, shifted right 39, then added to A and truncated to the output width.
This preserves the native descending-value behavior rather than substituting a
signed lerp. The caller derives integer weight by truncating float32(weight*255);
this API accepts that integer explicitly so conversion policy is not hidden.

Kind 6 calls a supplied quaternion service; its concrete helper is `140dcec30`.
Kinds 3 and 7..15 do not write. Buffer bounds and callback interfaces are authored.
Partial-overlap semantics, SSE exception/denormal modes and quaternion-body parity
remain open. The quaternion callback test proves wiring only. Private leaf anchor:
`140d78960`; common bank traversal `140d88ee0`; unmasked router `140d88580`.

The concrete pose wrapper chooses bank paths using destination/source mask
intersection, prepares/converts both banks, and sets destination flag bit 27 after
its branch. Mode-zero unmasked blending reaches this helper through the traversal;
masked/additive and transform-space variants still require separate reconstruction.


### Byte-channel quaternion integration

The regular byte-buffer channel adapter now uses the existing reconstructed
`combine_rotation_channel(..., mode=0)` for kind 6 when given an explicit
`reciprocal_sqrt` seed service. An optional caller-supplied quaternion callback is
still supported, but no longer required. This closes a wiring gap, not a newly
discovered formula: see Weighted quaternion bank channels and the existing
[160-case receipt](../../native/snow_host/weighted_rotation_channel_validation.json).
The adapter is checked byte-for-byte against all 80 mode-zero receipt cases,
including each ordered normalization input and observed emulator seed.

The path uses only lane zero of the weight vector. It retains the first quaternion
when absolute-dot distance from one is within float32 2^-23; otherwise it chooses
the recovered polynomial or normalized-linear branch by the signed-dot threshold.
The existing helpers preserve hemisphere handling, float32 operation order and
one reciprocal-square-root refinement. No replacement SLERP is introduced.

An unspecified seed service is refused instead of silently claiming that Python
square root reproduces hardware RSQRT. The integrated kernel accepts the finite,
nondegenerate domain enforced by the existing reference; native NaN/degenerate
behavior and CPU-specific seed equivalence remain outside that contract. Separate
storage is instruction-validated; partial overlaps are still unproved. Quaternion
interpolation is therefore available to the reconstruction, while full bank
traversal, masked variants and game-driven pose/clip selection remain distinct work.


### Regular byte-bank traversal

`reference.animation_bank_blend.blend_regular_pose_bank` joins regular channel
arithmetic, quaternion wiring and near-one copying to bank/profile byte storage.
The [20-case joined receipt](../../native/snow_host/regular_bank_blend_validation.json)
executes the original router, range traversal, channel leaves and copy helper.
Only the supplemental-record tail is supplied. Joined fixtures cover whole mask,
zero mask, separate/combined groups, kind exclusion, ordinary weights and weight
one. Quaternion leaves are covered separately by the preceding 80-case integration.

Full mask 65535 traverses the complete channel range once. Partial masks traverse
each selected group in ascending order using the first bank's group ranges. The
actual descriptor offsets/types come from the destination profile. Profile-backed
metadata takes precedence over legacy flat fixtures. Seven uint16 words per group
are preserved; selectors 6/7 may cross a nominal row boundary, as in the code.

Each range reuses the recovered near-one decision. Within float32 1e-5 of one,
selected descriptors copy source B and mark destination bit 27. Otherwise the
regular typed interpolation helper runs, with integer weight obtained from
truncated float32(weight*255). Kind exclusion applies to both paths. Copy supports
kinds whose arithmetic branch is a no-op; these paths must not be conflated.
The supplemental callback runs once per selected range, including a zero-length
range, and receives that mask, weight and mode zero. Mask zero selects no ranges.

This adapter models the unmasked regular bank router, not the outer pose wrapper's
mask/transform variants. Supplemental execution, implicit primary-bank acquisition,
component scale handling and group-dependent rotation context remain separate.
Finite weights, bounded group counts/storage and representable integer-weight
conversion are authored safeguards. Partial overlap and concurrent mutation are
unverified. The existing quaternion seed requirement remains explicit.


### Regular bank supplemental integration

The regular byte-bank API now defaults to the existing reconstructed supplemental
record evaluator when all three banks supply explicit `records` lists. Missing
records are refused rather than treated as empty. A custom supplemental callback
remains available for inspection. The default adapter requires a separate destination
bank because shared supplemental-list mutation semantics are not established.

The [20-case joined receipt](../../native/snow_host/regular_bank_supplemental_validation.json)
executes the original regular router, bank traversal, typed helpers, near-one copy
and supplemental tail without replacements. Fixtures use one equal-ID supplemental
record per bank with identity rotations, so no approximate RSQRT seed is needed.
Full output storage, bank status, record metadata/vector/rotation and per-group tail
calls match the composed reference. This closes the tail wiring gap for that domain;
it is not a new claim of arbitrary skeletal pose fidelity.

Mode-zero supplemental arithmetic does not gate on the requested group mask. The
outer router still controls whether a range runs: mask zero does nothing, while
multiple selected groups invoke the tail repeatedly. Each invocation reads source
records and current destination metadata. Near-one channel copy does not bypass
the supplemental evaluator. Unequal counts and nontrivial rotations continue to
use the existing reconstructed kernels with their documented constraints and
separate receipts; this joined receipt does not broaden those domains.


### Joined channel and supplemental rotation validation

The [90-case joined rotation receipt](../../native/snow_host/regular_bank_rotation_join_validation.json)
extends the regular bank validation to a kind-6 channel and a nontrivial
supplemental quaternion in the same operation. The actual router, range traversal,
channel helpers, quaternion dispatch/polynomial callees, near-one copies and
supplemental evaluator execute without replacements. Normalization inputs and
emulator RSQRT seeds are observed, not injected into the original instructions.
The reference consumes those seeds in order and matches every output byte, bank
status word, supplemental record and group visit.

Cases cover three quaternion pairs spanning near-parallel and polynomial branches,
positive/negative dot signs, weights 0.3/0.5/1, zero/full/single/multiple group masks,
and quaternion-kind exclusion. Exclusion skips channel rotations but does not
suppress the mode-zero supplemental tail. Multiple groups cause repeated tail
normalizations, and the joined reference matches that ordered seed sequence.

This strengthens integration evidence beyond the earlier identity-only join.
It still uses equal-count/equal-ID supplemental records and separate storage.
Unequal counts, mismatched IDs and aliasing are not newly validated in this join.
Recorded seeds are emulator-specific evidence, not a cross-CPU deterministic
normalization policy. No claim of active clip selection or original game pose
fidelity follows from these synthetic tests.

## Regular pose wrapper orchestration

The registered pose blend reaches helper `0x140dd3d10`. Its mode-zero,
inactive-mask route is implemented in
[animation_pose_blend.py](../../reference/animation_pose_blend.py).
It allocates a missing destination primary bank using the destination pool,
16-bit selection index and request-byte bit zero. Before calling selection
services it caches `source.index & destination.index` and the destination
component selector `(flags16 >> 3) & 7`.

The exact service order is source selection, source reciprocal-scale removal,
destination selection, destination reciprocal-scale removal, then regular bank
blend. The output is the destination wrapper's primary bank, which can differ
from its selected input bank. Exclusion mask is zero. Finally the helper reloads
the primary pointer and ORs bank flag bit 27, including when the intersection
mask is zero and no channels were visited. This is separate from the inner
blend's copy-path flag update.

[64 synthetic original-instruction cases](../../native/snow_host/regular_pose_wrapper_validation.json)
execute the full outer helper with a null blend mask. They check allocation
arguments, service order, selection masks, selectors, float32 weights and final
flags. Allocation, selection, reciprocal scaling and arithmetic calls are
supplied services in this check. The independent reference is tested against
that receipt. Callback exception propagation and failed-allocation rejection
are adapter behavior, not recovered engine error handling.

The wrapper uses the existing selector's `request_byte` schema. The acquisition
adapter's `flags` field names the same conceptual byte but is not automatically
bridged. Likewise the reciprocal-scale helper's eight-lane records are not yet
mapped to the byte-bank adapter's storage. These remain explicit integration
boundaries. Active blend masks and modes one/two use other routes and are not
implemented by this API. No live gameplay or full pose-pipeline equivalence is
claimed.

## Byte-bank scale storage bridge

[animation_bank_scale.py](../../reference/animation_bank_scale.py) now connects
reciprocal owner scaling to mutable byte buffers. The primary pointer at bank
`+0x198` is shared with channel blending; profile `+0x5a` supplies its uint16
record count. The secondary pointer/count are bank `+0xb0/+0xba`. Both loops
visit 32-byte records and multiply the first 16 bytes as four float32 lanes.
Secondary records are distinct from the 48-byte supplemental records used by
the blend tail. They must not be mapped to that list.

The bridge exposes primary storage as `data`, its count as
`profile.primary_count`, and the other storage/count as `secondary_data` and
`secondary_count`. Memoryviews retain aliases and partial overlap. It reuses the
existing reciprocal-scale reference through write-through record views; no
copied record array can hide repeated writes. Storage is accessed lazily after
the original flag, tolerance and primary-count gates. Bounds failures are
explicit adapter errors, not native recovery.

[96 original-instruction cases](../../native/snow_host/byte_bank_unscale_validation.json)
execute the reciprocal wrapper and both loops without substituted services.
Whole synthetic buffers and wrapper flags match for finite nonzero scalars,
near-one skips, primary counts 0/1/3, secondary counts 0/2, and disjoint or
partially overlapping storage. Tests also check that skipped storage is not
required. This resolves the scale-record to channel-byte storage boundary;
conversion between alternate bank representations, supplemental alias handling,
masked blending and complete live pose-pipeline validation remain separate.

## In-place regular bank blending

The regular byte-bank adapter now permits its destination to be the first or
second input bank. Each selected group reads the current input storage; its
supplemental tail therefore sees writes from earlier groups. The adapter replaces
the destination record list after each tail evaluation, so the next group reads
the updated list through that same bank object. It does not snapshot all groups
at entry. This allows the outer wrapper to blend directly into a primary bank
when that bank is also the selected input.

[40 identity-rotation cases](../../native/snow_host/regular_bank_alias_validation.json)
and [180 nontrivial-rotation cases](../../native/snow_host/regular_bank_rotation_alias_validation.json)
execute the original regular router, typed channel operations and supplemental
tail without supplied calls. Destination aliases each input in turn. They cover
zero/full/individual/combined masks, near-one copy, exclusions and repeated tail
execution. The rotation cases compare actual observed normalization inputs and
RSQRT seeds as well as whole channel outputs, supplemental records and flags.

These receipts prove the tested whole-bank alias paths with one equal-ID
supplemental record. They do not prove arbitrary cross-record overlap, shared
record lists between distinct bank objects, unequal-count alias paths or aliased
metadata. The value-list supplemental evaluator still is not a general memory
alias simulator. The earlier separate-bank-only adapter rejection has been
removed; the narrower tested scope remains explicit here.

## Joined regular byte pose path

`blend_regular_byte_pose` in
[animation_pose_blend.py](../../reference/animation_pose_blend.py) composes the
outer wrapper, recovered opposite-bank selection, byte-buffer reciprocal scale
removal, regular channel traversal and supplemental evaluation. Bank objects
retain their identity, including destination-as-input. The API accepts explicit
`acquire`, `convert`, `get_owner_scalar(wrapper)` and optional reciprocal-square-
root services. Allocation and representation conversion are not fabricated.

[24 original-instruction cases](../../native/snow_host/joined_byte_pose_validation.json)
execute the full outer helper and its actual callees without substituted calls.
The fixture starts with existing primary banks marked as the selected
representation and no alternate banks. It covers prepared/unprepared flags,
owner scalars 0.3/1/2, zero/full selection masks, weights 0.3/1, two four-lane
channels and empty supplemental arrays. Both input/output buffers, both bank
flags and both wrapper preparation bytes match the composed API. In particular,
zero selected channels still allow scale removal and destination-ready
publication; a no-channel blend is not a no-op for the whole wrapper.

This is joined original-instruction validation for that branch, not a live
animation test. Alternate acquisition/conversion, active blend masks, other
operation modes and nonempty supplemental records in this full outer fixture
remain outside its coverage. Separate lower-level receipts cover supplemental
arithmetic and selected in-place cases.

## Relative conversion byte adapter

The already recovered parent-relative converter is now available for channel
byte banks through
[animation_bank_conversion.py](../../reference/animation_bank_conversion.py).
`convert_relative_byte_bank` reads `profile.primary_count` consecutive 32-byte
position/quaternion records and uses `profile.metadata` for parent, rank and
skip-span fields. Supplemental `records` are untouched. The existing hierarchy
math supplies normalization and float32 ordering; only visited records are
written, preserving skipped byte patterns and buffer tails. Nonempty conversion
copies the opaque 32-byte parent header, clears destination bit 27 and sets bit
26. Empty input requires no storage and changes neither header nor flags.

Tests replay all 192 cases in the existing original-instruction hierarchy
receipt through this byte adapter. Shared whole buffers preserve forward parent
reads; a separate regression checks the chain positions 2/5/9 converting to
2/3/6 in place. Arbitrarily overlapping memoryview slices are explicitly refused
rather than silently snapshotted. Bounds and buffer-type errors are authored
adapter safeguards.

`blend_regular_byte_pose` now defaults to this converter. Allocation remains a
supplied service, and callers can override conversion explicitly. A synthetic
integration test exercises creation of both alternate banks, conversion,
preparation-bit clearing, interpolation and final ready publication. That test
checks composition; it is not an additional full-path original-instruction
receipt. The earlier joined original-instruction fixture still covers the
existing-primary/no-conversion branch only.

## Joined conversion and blend instruction validation

The [64-case converted byte pose receipt](../../native/snow_host/joined_converted_byte_pose_validation.json)
now exercises the complete regular outer blend through actual bank selection,
parent-relative conversion, reciprocal scale removal and channel blending. Only
allocation is supplied, returning initialized synthetic alternate banks. No
conversion, scaling or arithmetic call is replaced. Captured RSQRT seeds are
replayed by the independent implementation.

The matrix covers present/missing alternates, primary ready flags clear/set,
selectors 0/7, owner scalars 0.3/2, zero/full masks and weights 0.3/1. Each bank
contains two transform records; the second has rank 3, so selector zero checks
skip preservation. All four banks' complete record buffers, parent headers and
flags match, as do allocation order, installed identities and final wrapper
preparation bytes. Existing alternates without source readiness intentionally
bypass conversion; newly allocated alternates convert regardless of readiness.

This extends the earlier no-conversion full-path receipt. It does not establish
allocator internals, live object lifetime, active blend-mask preparation,
nonempty supplemental arrays in this joined fixture, or other operation modes.
The public regression replays synthetic receipt data without private game files.

## Blend-mask byte preparation

[animation_mask_preparation.py](../../reference/animation_mask_preparation.py)
implements the pre-blend scatter helper `0x140ddc9f0`. It returns immediately
for a null bank profile or an operation mode outside 0/1/2. Valid modes choose
value-array descriptors at mask offsets 12/36/24 respectively. Each descriptor
contains a byte-buffer pointer and a uint16 count at descriptor offset 10.
The channel-index array is the pointer at mask offset zero.

For each entry in order, the helper reads a uint32 channel index, looks up the
uint16 byte offset at channel descriptor offset four, and copies one selected
value byte to `bank.data[offset]`. It does not inspect the channel kind. Native
four-entry unrolling preserves this write order. Duplicate offsets overwrite
earlier values. Value storage can alias output storage, so later reads can see
earlier writes; the adapter reads each value at its turn rather than copying
the value array first.

[96 original-instruction cases](../../native/snow_host/blend_mask_preparation_validation.json)
execute the complete helper without replaced calls. They cover modes 0/1/2/3,
null/present profiles, counts 0/1/4/5/8/9, repeated destinations and aliased value
storage. The adapter exposes `indices` and `mode_values[mode]` with each array's
length supplying its count. Descriptors and index metadata are treated as stable;
aliasing those tables into writable data is not modeled. Bounds failures are
adapter safeguards, not native recovery.

This preparation mutates the selected source bank before the outer masked blend.
It is not itself a per-bone weight formula. The masked consumer and the meaning
of the written channel bytes remain to be connected; the existing regular byte
pose API still represents the inactive-mask route only.

## Masked channel weight selection

[animation_mask_weights.py](../../reference/animation_mask_weights.py) implements
the regular inner blend's keyed weight walk. Descriptor dword zero is a grouping
key. When a new key is encountered, effective weight resets to the weight mode's
default, zero for mode 0 and one for mode 1. If the following descriptor has that
same key and kind zero, its byte supplies:

```text
effective = float32(float32(byte * float32(1 / 255)) * blendWeight)
integerWeight = truncateToInt64(float32(effective * 255)) low32
```

That following descriptor is consumed as weight metadata and skipped by the
channel output loop. Further descriptors with the same key retain the cached
weight; they do not probe another following byte. A later different key resets
the cache. The initial previous-key sentinel is uint32 `0xffffffff`, so a first
descriptor with that key uses the default directly. There is no clamp here;
weights above one can produce integer weights above 255.

The [24-case instruction receipt](../../native/snow_host/masked_channel_weights_validation.json)
executes the actual regular inner routing and records effective float/integer
weights, descriptor indices and consumed-byte decisions. It supplies the typed
arithmetic leaf and stops before the supplemental tail. Cases cover modes 0/1,
weights 0.3/1/1.5, bytes 0/1/127/255, sentinel keys, repeated keys and key changes.
This validates routing, not complete masked output. The generator reads values
lazily so output writes can affect later reads when buffers alias. Descriptor
metadata itself remains stable in the adapter.

The inner routine reads weight bytes from first input for mode zero and second
input for mode one. The outer masked router can override selected groups to
mode two, which uses the existing uniform-weight route. Full-mask requests take
a distinct route that does not test that group override mask. Integrating these
routes, their special integer-weight-255 copy behavior and supplemental tail
remains the next step; no masked pose API is claimed yet.

## Masked bank blend output

`blend_masked_pose_bank` in
[animation_bank_blend.py](../../reference/animation_bank_blend.py) now composes
masked group traversal, keyed byte weights, typed channel math and supplemental
evaluation. Partial request masks visit selected groups in ascending order.
Groups intersecting `uniform_groups` use the established uniform kernel;
full-mask `0xffff` requests bypass that override test and use the masked mode.
Each group restarts the keyed weight cache. The supplemental tail uses the global
blend weight, independently of the last channel's effective weight.

The masked integer-weight-255 branch has distinct copy semantics: kinds 0/1/2/5/6
copy from the second input, kind 4 copies three scalar lanes from the first,
and kind 3 or kinds above 6 do nothing. It does not set bank-ready bit 27.
Exclusion applies before either copy or arithmetic. Uniform override groups
retain their own near-one copy behavior and flag updates. These are separate
native paths, not interchangeable optimizations.

[80 original-instruction cases](../../native/snow_host/masked_bank_blend_validation.json)
execute the actual masked router, channel traversal, typed leaves, copy paths
and supplemental tail without replaced calls. They compare all output bytes,
flags, supplemental vectors and identity rotations across modes 0/1, zero/full/
partial masks, uniform overrides, exclusions and weights 0.3/1. Synthetic channel
descriptors include a paired weight byte and kinds 0/1/2/3/4/5/7. Quaternion
channels, nonidentity supplemental rotation, arbitrary storage overlap and the
outer active-mask wrapper are not covered by this joined receipt. The ordinary
masked byte-bank kernel is now callable; the public pose wrapper still uses the
inactive-mask route.

## Joined active-mask pose wrapper

`blend_regular_byte_pose` now accepts an optional `blend_mask` with
`active_count`, `uniform_groups`, `indices` and `mode_values`. Null masks and
zero active counts retain the inactive route. An active mask first selects and
unscales the source bank, then scatters mode-zero mask bytes into it. The wrapper
captures `uniform_groups`, selects/unscales the source again, selects/unscales
the destination, and invokes masked blending in weight mode one. Destination
primary ready-bit publication still occurs last. The cached intersection and
selector precede preparation, as in the original helper.

[96 original-instruction cases](../../native/snow_host/joined_masked_byte_pose_validation.json)
execute the entire helper and callees without supplied calls. They cover present
inactive/active masks, prepared/unprepared wrappers, scalars 0.3/2, zero/partial/
full masks, weights 0.3/1 and prepared bytes 0/255. Both banks' full data buffers,
flags and wrapper bytes match. The partial mask takes a uniform override while
the full mask follows keyed weighting. Zero intersection still permits source
scale removal and byte preparation; it is not a no-mutation shortcut.

The fixture uses existing primary banks, empty supplemental arrays and no
quaternion channel. Conversion/allocation have separate joined evidence and
are not exercised together with active mask preparation here. Runtime lifetime,
nonidentity rotations on this path and operation modes one/two remain open.
The public low-level orchestration API retains explicit services; the composed
byte API supplies the recovered preparation and masked blend implementations.

## Masked rotation output validation

The [432-case masked rotation receipt](../../native/snow_host/masked_bank_rotation_validation.json)
extends masked-bank output checks to a kind-six quaternion channel paired with
a byte-weight descriptor and a nonidentity supplemental rotation. All original
router, channel and supplemental instructions execute without supplied calls.
The observer records normalization inputs and RSQRT seeds, then the independent
implementation uses those seeds and checks each input in order.

Cases span weight modes 0/1, uniform overrides absent/present, byte weights
0/127/255, masks 2/3/0xffff, blend weights 0.3/1 and quaternion-kind exclusion
clear/set. Three input rotations exercise positive-dot polynomial, near-parallel
and negative-dot paths. Complete channel buffers, supplemental vectors/rotations,
bank flags, group visits and normalization-call consumption match. The same
synthetic receipt cases pass through the public JSON boundary.

The runnable fixture
[animation_masked_rotation_input.json](../../engine/examples/animation_masked_rotation_input.json)
contains one recorded-seed example. Its multiple groups expose the repeated
supplemental-tail behavior while the quaternion channel uses a byte-derived
weight. These are separate bank buffers; this receipt does not prove active-mask
outer-wrapper conversion, arbitrary aliasing, physical-CPU approximation bits or
live animation selection. The prior identity-only masked receipt remains useful
for its simpler branch matrix; this result extends rather than replaces it.

## Active masks with alternate conversion

The [64-case joined conversion/mask receipt](../../native/snow_host/joined_converted_masked_pose_validation.json)
executes the full mode-zero outer helper with active mask preparation and
alternate-bank selection/conversion together. Allocation is the only supplied
native service. The relative converter, reciprocal scale removal, mask byte
scatter, second source selection, masked channel weighting and empty
supplemental tail execute their original instructions.

The mask writes byte 127 to a paired kind-zero weight channel stored after the
two transform records. The first vector channel consumes that byte; remaining
vectors use their unpaired defaults. The weight byte survives conversion and
the repeated source selection. All four 80-byte buffers, parent headers, bank
flags, wrapper preparation flags, allocation order and installed identities
match the composed API. Cases cover missing/existing alternates, readiness,
rank skips, owner scalars, zero/full selection masks and blend weights 0.3/1.
Normalization observations remain emulator-specific inputs to receipt replay.

This joins branches previously checked separately. It still does not exercise
nonempty supplemental arrays or quaternion channel blending within this full
outer fixture; separate masked-bank receipts cover those arithmetic paths.
Allocator internals, live lifetime and operation modes one/two remain open.

## Additive byte channels

`blend_additive_channel` in
[animation_channel_blend.py](../../reference/animation_channel_blend.py)
provides the mode-four typed byte leaf. Its name does not imply that every type
adds: kind zero uses the existing wrapped byte interpolation; kind one uses
`a + (b-a)*weight`; kind five uses lane-wise `a + vectorWeight*b`; kind six
reuses the recovered weighted-rotation composition. Kinds 2/3/4 and 7..15 leave
the output unchanged. The scalar weight drives quaternion weighting, independently
of the supplied four-lane vector weights. Float32 operation order is preserved.

[90 original-instruction cases](../../native/snow_host/additive_channel_blend_validation.json)
execute the typed leaf for every non-quaternion kind with no substituted calls.
They compare the entire destination, test reversed inputs, wrapped bytes and
nonuniform vector weights. The byte adapter also replays the 80 mode-four cases
from the existing weighted-rotation instruction receipt, checking exact output
bytes and all normalization inputs/seeds. Descriptor bounds checks are authored
safeguards. Arbitrary partial overlap, additive bank routing and the outer
mode-one/two pose operations remain separate integration work; a local mode-four
leaf does not establish their complete semantics.

## Unweighted additive byte leaf

`combine_unweighted_byte_channel` in
[animation_channel_blend.py](../../reference/animation_channel_blend.py) provides
the additive router's near-one helper `0x140d78860`. It wraps byte addition,
adds scalar/four-lane float channels, and multiplies quaternion channels using
the already recovered operation order without normalization. Other kinds leave
storage untouched. The input records are read before their output writes, so
whole-channel in-place updates retain their inputs.

The router selects this helper when `abs(float32(weight-1))` is within its
float32 1e-5 tolerance. It does not merely call the weighted helper with weight
one. In particular, a scalar with inputs 2 and 8 interpolates to approximately
7.994 at weight 0.999 but adds to 10 at weight 1. Byte interpolation likewise
changes to wrapped addition. This observed type-specific discontinuity must not
be smoothed away by the reconstruction.

[96 original-instruction cases](../../native/snow_host/unweighted_byte_channel_validation.json)
execute the complete leaf for kinds 0..15, including non-unit quaternion inputs,
with no substituted calls. Every destination byte is compared, including
untouched regions and unsupported kinds. Independent regressions check the
near-one scalar route and whole-channel in-place vector addition. Arbitrary
partial overlap and complete additive bank traversal remain separate work.

## Additive byte-bank traversal

`blend_additive_pose_bank` in
[animation_bank_blend.py](../../reference/animation_bank_blend.py) joins the
uniform additive router to its weighted and near-one typed leaves. Selection
ranges come from the first input profile; descriptors come from destination.
Partial masks visit groups in ascending order and full mask visits all channels
once. Exclusions apply by kind. Without swap the arithmetic source order is
second then first; with swap it is first then second. This matters for both
weighted arithmetic and quaternion multiplication.

The near-one threshold selects the distinct unweighted helper. Neither path
updates the bank-ready flag. The original supplemental tail receives mode four
and returns without changes, so this adapter leaves supplemental records intact.
It does not substitute regular supplemental interpolation for additive mode.

[180 original-instruction cases](../../native/snow_host/additive_bank_blend_validation.json)
execute the additive router, range traversal, typed leaves, quaternion arithmetic
and no-op supplemental tail without replaced calls. They cover both source
orders, zero/full/partial masks, weights 0.3/0.5/1, exclusions and three nonidentity
quaternions. Complete destination bytes, flags, preserved supplemental records,
group visits and observed normalization inputs/seeds match. Storage is separate
in this fixture. Masked additive weighting, outer mode-one orchestration,
allocation and live selection remain separate boundaries.

## Masked additive byte banks

`blend_additive_pose_bank` now accepts `weight_mode`: two retains uniform routing,
zero reads keyed weight bytes from the original first bank, and one reads them
from the original second bank. Arithmetic source swapping does not change the
weight-byte source. The existing keyed iterator preserves defaults, paired-byte
consumption and cached weights within each selected range.

Masked additive channels use the unweighted helper exactly when the low 32 bits
of the truncated integer weight equal 255. This differs from the uniform
near-one tolerance test. Other integer weights use the weighted helper. Kind
exclusions still apply after weight discovery; supplemental records and bank
flags remain untouched. There is no regular masked router's per-group uniform
override parameter on this additive entry.

[432 original-instruction cases](../../native/snow_host/masked_additive_bank_validation.json)
execute the original masked additive router and all channel callees without
replacement. The matrix covers both weight sources, both arithmetic source
orders, bytes 0/127/255, full and partial masks, weights 0.3/1, exclusions, and
three quaternion inputs. Full output buffers, flags, unchanged supplemental
records, group visits and normalization-input/seed consumption match. This is
separate storage with synthetic profiles; arbitrary overlap, outer mode-one
preprocessing and live animation selection remain unproved.

## Non-mutating pre-consumption markers

Probe ABI v2 extends the paired actor snapshots with the signed counter and two
raw timers from the local pre-consumption branch above. In the analyzed layout,
they are runtime offsets `0xa80`, `0x1580` and `0x1584`. The saved instruction
sequence decrements the counter immediately before loading and threshold-testing
the pending vector. These are ordinal storage fields, not named gameplay states.

The [reader/fixture validation](../../native/snow_host/preconsume_snapshot_validation.json)
covers signed representation, raw timer values, failed-read invalidation and a
synthetic wrapped-call decrement. No original-game capture of these fields has
run yet. Comparing unsigned 32-bit before/after bit patterns modulo 2^32 avoids
misclassifying signed wrap. A net decrement of one supports this path, but other
writes or helper effects can obscure it; it is not equivalent to an entry probe
at the consumer. Whole-wrapper velocity differences still include other forces.

The pending queue remains an unsafe arbitrary-thread mod entry: its four-lane
add is not atomic, and the consumer clears after releasing its lock. A future
write API must establish an ordered owner and define one-shot completion before
using the queue. This observation change provides evidence for that decision
without publishing such a write API prematurely.

### Live pre-consumption marker observation

The [expanded moving-rider capture](../../native/snow_host/preconsume_live_observation.json)
recorded 228 valid paired calls. Every pair decremented the counter by exactly
one modulo 2^32. Slot installation/restoration/drain passed, the host remained
ordinary and advancing for 20 seconds, and cleanup passed. The associated 211
request groups all matched the reconstructed float32 elapsed/consumed relation,
including one five-call group.

This strengthens the link from the observed actor wrapper to the local
pre-consumption region. It remains indirect evidence rather than an exact
consumer entry/return probe. Both pending snapshots were zero in every pair, so
this run supplies no nonzero pending-consumption result. It does not authorize
arbitrary-thread queue access or establish protection of the post-unlock clear.

## Countdown clock and adjacent impulse magnitude

The earlier ordinal label "two timers" is corrected here. Runtime `+0x1584`
is decremented by the float at runtime `+0x1520`. The local sequence is:

```text
countdown = f32(countdown - elapsed_dt)
```

There is no zero clamp in that sequence. Later branches can clear both fields
or reset this countdown to the float32 constant `0.3330000042915344` after
paired direct impulse calls. `reference.central_impulse.advance_preconsume_countdown`
implements only the subtraction, not those later branch decisions.

Runtime `+0x1580` is instead assigned a curve-scaled value and used as an impulse
magnitude with the main/rider mass split in the neighboring branch. Treating it
as a second elapsed timer would be wrong. Its full branch model remains separate
from the small countdown helper. The trace's `preconsume_timers` array retains
its legacy name for compatibility: element 0 is this scalar magnitude, element 1
is the countdown. Do not infer gameplay state names from these fields alone.

[Validation](../../native/snow_host/preconsume_countdown_validation.json) matched
the portable helper in 48 isolated original-instruction cases. In the existing
live run, all 228 before/after countdown pairs matched elapsed-time subtraction
exactly at float32 precision. The 31 calls with different elapsed and consumed
arguments all matched elapsed, and none matched consumed. This discriminates
the clocks rather than relying on the 197 single-call cases where they agree.
The adjacent magnitude was zero throughout this run. The countdown remained
negative and continued decreasing; no reset or jump impulse was observed.

## Stateful jump consumer

[reference.snow_jump_step](../../reference/snow_jump_step.py) now supplies the
stateful local branch described by the existing snow integration guide. Its
inputs are cached factor, countdown, elapsed interval, air clock, enabled base
factor, release signal, positive gravity magnitude, combined body mass, configured
rider mass and rider presence. Compiled-curve gains are explicit inputs evaluated
at release signal, contact depth and projected speed by the caller.

Operation order follows the inspected instructions:

```text
countdown = f32(countdown - elapsed_dt)
if air_time > 0 or base_factor <= 0:
    cached_factor = 0; countdown = 0; return
if countdown > 0:
    retain cached_factor; return
if release_signal <= 0:
    cached_factor = 0; return
factor = f32(f32(coil_gain * base_factor) / gravity)
factor = f32(depth_gain * factor)
factor = f32(speed_gain * factor)
cached_factor = factor
if rider_present:
    request rider central impulse (0, 0, f32(factor * configured_rider_mass))
request main central impulse (0, 0, f32(f32(combined_mass - configured_rider_mass) * factor))
countdown = f32(0.333)
```

All operands are rounded to float32 on entry to their modeled arithmetic. The
coil gain is multiplied by the base factor *before* division by gravity; the
older mathematical shorthand `base / gravity * coil` can round differently.
Requests are rider first, then main, each with force=true. Zero gain still
produces requests and resets the countdown. There is no clamp on the main mass
difference, and missing rider representation does not remove that subtraction.

The function returns requests; it performs no locking, physics integration or
backend dispatch. Finite-input validation is our portable policy. Seven synthetic
boundary tests validate the implementation's contract. The prior 48-case
original-instruction comparison covers only the countdown subtraction, not this
whole newly composed branch. Full branch comparison with intercepted curves and
body calls is the next validation gate. No live jump reset was captured yet.

### Jump branch instruction comparison

The subsequent [288-case original-instruction comparison](../../native/snow_host/jump_branch_validation.json)
matched the composed jump reference exactly for cached factor, countdown,
body request vectors, force flag and ordering. Branch coverage comprised 216
disabled cases, 24 countdown-held cases, 24 no-release cases and 24 submitting
cases. Cases include exact cooldown expiry, absent rider, negative main mass
difference, zero curve gain and multiple nonzero gains.

Synthetic constant compiled curves ran through the original clamped-low segment
evaluation instructions. Body impulse calls and lock enter/leave were intercepted.
The submitting cases entered one lock, requested rider then main when present,
and left the same lock; no actual body writes or lock synchronization were
performed. General curve domains, invalid configuration transfers, upstream input
release production and outer actor gates are outside this comparison.

A rounding regression test preserves a concrete distinction: coil gain 1.3,
base 80 and gravity 9.81 yield factor 10.60142707824707 before depth/speed gains.
Dividing base by gravity first yields 10.601426124572754. Both are plausible
mathematical rewrites, but only the former matches the inspected instruction order.

## Charge-release state composition

[reference.snow_charge_release](../../reference/snow_charge_release.py) implements
the existing [integration guide's](../systems/snow/integration/CLIENT_GUIDE.txt)
release-state transitions with explicit float32 arithmetic. It consumes previous
cooked/saved charge, elapsed clock, rate and both release copies, plus a new cooked
sample, raw remapped input, separate timing arguments, threshold and update mode.
It returns new state without mutating the caller's dictionary.

The bench can now compose this stage with curves, the jump consumer and central
body arithmetic. The release is generated when cooked coil reaches exactly zero,
not immediately when raw input becomes zero. The strict elapsed threshold and
rate comparison against -1 remain intact. Other update modes retain prior release
signals and rate while updating cooked coil and elapsed time. This retention must
not be replaced with a universally cleared one-shot event.

Seven synthetic release tests and one added bench composition case cover the
state boundaries and one charge/release sequence. The newly implemented release
stage has not received the isolated original-instruction comparison performed
for the jump consumer. Device-to-cooker mapping, exponential lookup data, profile
selection and mode ownership remain explicit integration dependencies.

### Charge-release original-instruction validation

The [new 1,536-case comparison](../../native/snow_host/charge_release_validation.json)
executes the original selected release-state block against the public module.
All six stored fields matched by float32 bytes: cooked value, saved charge,
elapsed clock, rate and both signal copies. In 1,369 cases the elapsed and
derivative intervals differed. Mode coverage was 765 cases for mode 1, 400 for
mode 0 and 371 for mode 2. Forty-six active-mode cases emitted a release.

The harness intercepted the threshold getter, checked its selector and supplied
a scalar threshold. It did not execute profile blending or the cooker. The
original block starts after the new cooked value has already been stored, so
this verifies release-state consumption of that sample rather than its producer.
It extends the earlier private harness, which had used equal timing arguments,
and supersedes the synthetic-only qualification for this local release module.

`releaseJumpThreshold` in this branch is compared with elapsed release time.
It is not a minimum cooked-charge strength. A port that tests charge >= 0.25
at raw trigger release implements a different policy. The saved-charge signal
can be smaller than that threshold and still pass the timing test; the jump
consumer's curves and gates then decide the requested impulse.

## Input cooker arithmetic

[reference.input_cooker](../../reference/input_cooker.py) implements the finite
float32 cooker leaf with a required external decay lookup. It does not substitute
`math.exp` or ship a decoded table. Input values and coefficients are rounded to
float32; operation order is preserved:

```text
use_zero = abs(target) <= abs(current) or f32(current * target) <= 0
base, proportional = coefficients[ToZero if use_zero else ToOne]
x = -f32(elapsed_dt * proportional)
decay = supplied_lookup(x)
step = f32(f32(f32(1 - decay) * abs(f32(target - current)))
           + f32(elapsed_dt * base))
if target > current:
    candidate = f32(current + step)
    if candidate > target: candidate = target
else:
    candidate = f32(current - step)
    if candidate < target: candidate = target
if abs(f32(target - candidate)) < epsilon:
    candidate = target
```

The original code rounds the candidate before overshoot handling; a rewrite
that first takes `min(step, error)` need not preserve every rounding result.
Starting from zero takes ToZero. The snap comparison is strict; equality at
epsilon does not snap. No extra clamp is applied to the supplied lookup value.

[384 original-instruction cases](../../native/snow_host/input_cooker_validation.json)
matched the public helper's output bytes and lookup argument exactly. Of those,
288 selected ToZero and 96 selected ToOne. The lookup was intercepted with supplied
values, including 1.1 to test arithmetic outside the usual exponential range.
Five portable tests cover branch choice, clamp, snap and required lookup behavior.

This closes the tested local arithmetic, not the original lookup table, profile
blend, hardware mapping or live input timing. The historical `reference.snow.cooker`
remains a mathematical reference with its generated exponential approximation;
use the explicit-lookup helper when preserving those distinctions matters.


## Decay lookup construction

`reference.decay_table` reconstructs the 256-segment builder from 257 supplied
samples. Every operation below rounds to float32. The original initializer uses
low = -10, high = 0 and padding = 0.0001.

```text
width = high - low
step = width * (1 / 256)
start = low - width * padding
x[i] = (float32(i) * step) + low
slope[i] = (sample[i+1] - sample[i]) / step
intercept[i] = sample[i] - x[i] * slope[i]
denominator = ((padding + 1) * width) + (low - start)
index_scale = 256 / denominator
```

Preserve the parentheses and intermediate rounding. Padding scales with width;
the generic curve compiler's padding cap does not apply. The resulting table
uses `reference.runtime_curve.evaluate` for clamped segment selection and linear
evaluation.

The original builder and evaluator were emulated with supplied synthetic sample
values. Four sample sets matched all 514 output floats per builder case, and
1,056 evaluator cases matched exactly. All 257 sampling arguments were checked.
See `native/snow_host/decay_table_validation.json` for the bounded receipt.

The scalar and vector exponential routines were intercepted. Host exponential
samples are authored fixtures, not recovered original samples. Their native
implementations remain unresolved. The floor helper was also intercepted for
finite nonnegative indices. This was offline instruction emulation, not a live
game test; no initialized original table is included.


## Decay exponential lanes

`reference.decay_exp.exp_lane` reconstructs both packed-vector paths over the
cooker's finite [-10, 0] domain. The caller selects `sse2` or `sse41`; automatic
CPU dispatch and exceptional/outside-domain paths are excluded. The reference
uses round-to-nearest-even and float32 rounding after each arithmetic operation.

Both paths scale the input by float32(64 / ln(2)). SSE2 obtains the rounded integer
through a 12582912 bias and uses its bit representation. SSE4.1 uses integer
conversion and explicit nearest rounding. They subtract the integer multiplied
by two parts of ln(2)/64, 0.01082611083984375 and
4.313856607041089e-06, rounding each multiplication and subtraction separately.
For the remainder r, the polynomial order is `((r + r) + 2) + (r * r)`.

The integer's low six bits select a mantissa; the remaining bits construct an
exponent for the polynomial's scale. The 64 mantissas can be independently
computed as the low 23 bits of float32(2 ** (j / 64)). All 64 generated entries
matched each original path's table. No table payload is copied into the module.
The explicit bit construction and rounding order are in the reference code.

The [instruction receipt](../../native/snow_host/decay_exp_validation.json)
compares 4,356 lane cases per path, including the 257-point decay grid and a
4,097-point domain sweep, plus padding lanes. All outputs match exactly under
MXCSR 0x1f80. No calls were intercepted in these leaf comparisons. Host exp
rounded to float32 differs in 1,893 tested lanes per path; at -5 the reconstructed
value is 0.006737947463989258 rather than 0.0067379469983279705.

This closes the packed-lane arithmetic boundary over the tested domain. The
builder's final sample uses a separate scalar routine, which is not covered by
this receipt. Live CPU dispatch remains unobserved. Using this lane routine for
all 257 samples is therefore a composed substitute for that last scalar call,
not yet proof of the complete original initialized table.


### Joined default decay table

The later [joined builder comparison](../../native/snow_host/decay_table_joined_validation.json)
executes the original builder, vector dispatch and scalar SSE endpoint with no
exponential call interception. For each vector path, all 514 table floats match
`reference.decay_exp.cooker_table`, followed by 4,104 exact lookup comparisons.
The scalar SSE call at zero produces exactly 1. The floor helper remains
intercepted for finite nonnegative indices. This supersedes the missing scalar
endpoint boundary above for the SSE scalar path only.

The same test attempted both vector paths with scalar FMA enabled. Unicorn
rejected `vfnmadd231sd`; these attempts are recorded as unsupported, not passes.
CPU selectors and nearest-even MXCSR are set in the emulator, not observed live.
The public factory therefore requires `scalar_path='sse2'` and an explicit
`vector_path`. It supplies the fixed [-10, 0] domain and original padding.
General scalar exponential behavior and live floating-point mode are unresolved.

The jump bench can now use this complete reconstructed default table without
caller-supplied exponential samples. Its example still uses authored damping,
raw inputs and clocks. In that example the constant-one lookup fixture reached
cooked zero on frame four; the reconstructed table reaches it on frame five.
That difference demonstrates the effect of decay arithmetic in the composed
model. It does not establish the original game's jump latency.


### Stateful cooker with reconstructed lookup

The [joined cooker comparison](../../native/snow_host/input_cooker_joined_validation.json)
executes the original cooker and lookup without intercepting the lookup call.
It loads the independently reconstructed default table, previously checked
against the complete original builder for the SSE scalar path. Only the floor
helper remains intercepted.

Twenty-four synthetic sequences cover six coefficient profiles and four interval
patterns, including 30, 60 and 120 Hz and a varying interval sequence. Across
6,144 consecutive frames, output float32 bytes and lookup arguments match exactly.
There are 4,995 ToZero and 1,149 ToOne visits, with 960 lookup arguments below the
padded domain. Each sequence retains the prior native result; it does not reset
filter state at every comparison. The receipt records zero transitions and
target-hit counts per scenario. Raw-device mapping, release/jump execution,
native cadence and live floating-point mode are not tested here.

`engine.physics.step` now uses this float32 cooker and reconstructed default
decay for steering. Its coefficients 0/12 and 0/9, clock choice, target mapping
and subsequent turning policy remain authored. Diagnostics expose the cooker
branch, lookup argument/result and step. The historical `reference.snow.cooker`
remains available as the earlier approximation; the engine no longer calls it.


## Input speed profile selection

`reference.input_profile` preserves the preset selection branch order and scalar
blend arithmetic. Each operation below rounds to float32:

```text
converted = runtimeSpeed * float32(3.6)
if converted <= normalThreshold: weight = 0
else if converted >= fastThreshold: weight = 1
else: weight = (converted - normalThreshold) / (fastThreshold - normalThreshold)
value = ((1 - weight) * normalValue) + (weight * fastValue)
```

The selector is gradual between ascending thresholds, not a switch. The normal
comparison takes priority. Equal or reversed finite thresholds consequently
select an endpoint without dividing by zero. The separate scalar blend does not
clamp its supplied weight.

For thresholds 7 and 12, the interval in runtime-speed units is 7/3.6 through
12/3.6, approximately 1.94 through 3.33. If runtime speed is metres per second,
the threshold numbers are kilometres per hour. This corrects the initial task's
7–12 m/s assumption and agrees with the existing snow guide's conversion.
It does not assign that conversion to every speed curve in the game.

The [instruction receipt](../../native/snow_host/input_profile_validation.json)
covers 690 selector cases and 120 scalar blend cases. It executes the conversion
instruction, initialized finite selector branches and scalar blend tail. Getter
validation, nonfinite settings, resource selection and the upstream speed producer
are outside this check. Earlier research identifies that native producer as
projected speed; `engine.physics` still supplies relative speed magnitude as an
authored approximation. The engine now uses the exact selector arithmetic for
its diagnostic and synthetic turn-policy blend, without claiming native steering
profile routing. Profile coefficients remain caller-supplied or synthetic.

Float32 boundary detail: supplying the mathematical value 12/3.6 rounds the
converted speed just below 12, producing weight 0.9999998211860657. A slightly
larger input such as 3.3333335 reaches the fast endpoint. Tests retain this result
rather than forcing ideal-real-number boundary equality.


## Projected input speed

`reference.projected_speed` reconstructs the cached-state speed writer. Given
cached linear velocity v and the supplied normal n, each operation rounds to
float32, with reduction order x + (y + z):

```text
p[i] = v[i] * n[i]
d = p.x + (p.y + p.z)
t[i] = v[i] - d * n[i]
s[i] = t[i] * t[i]
speed = sqrt(s.x + (s.y + s.z))
```

This block does not normalize n or subtract a moving surface's velocity. A unit
normal removes the normal component; a nonunit normal retains the literal
arithmetic rather than silently correcting it. The fourth SIMD lane does not
contribute to the stored scalar. The inspected producer loads cached velocity
before this block and stores the resulting magnitude for subsequent consumers.

The [instruction comparison](../../native/snow_host/projected_speed_validation.json)
matched 1,028 stored-speed outputs exactly, including pure-normal motion, zero
normals and nonunit normals. Normal sourcing, cached-body acquisition and update
cadence were supplied, not executed. The diagnostic tangent and dot values
follow inspected intermediates; the receipt compares the final stored speed.

The independent runtime now computes the input profile speed from body velocity
projected against its sampled terrain normal. This replaces its previous total
relative-speed magnitude. The terrain normal and sampling time are authored
substitutes for the original cached normal and update order. While airborne the
runtime still samples terrain below the body; it does not claim native airborne
normal behavior. `input_speed` diagnostics expose speed, projection and dot.
Pure vertical flight above a horizontal plane consequently stays at the normal
profile rather than selecting the fast profile just from vertical speed.


### Cached projection normal lifetime

Follow-up inspection identifies the projection normal as the third basis vector
of a cached frame. The frame writer copies all four candidate lanes directly to
that slot before constructing the other basis vectors. The upstream rebuilding
block is entered only when the immersion accumulator is strictly greater than
zero. Nonpositive values skip the rebuild and preserve the previous normal.
This is distinct from the separate air-clock threshold of 0.001.

Inside the positive-immersion branch, the inspected code aggregates eligible
contact normals weighted by contact values, normalizes, considers a fallback fit,
and can smooth a rotation from the prior normal. The final candidate is passed
to the frame writer. Those branches and their complete data producers remain
unreconstructed here. A raw current terrain normal is not equivalent to this
stateful procedure.

The [bounded instruction receipt](../../native/snow_host/projection_normal_gate_validation.json)
checks five finite immersion values, including positive 0.00001 below the air
clock threshold, and three exact four-lane candidate copies. It does not execute
the intervening candidate generation or complete frame construction.

The runtime now retains `projection_normal` while unsupported and updates it
from terrain when supported. Support is an authored proxy for positive immersion;
terrain is an authored candidate without native aggregation or smoothing. Old
checkpoints and airborne spawns without that state use synthetic world-up. The
new state is checkpointed with the body. Diagnostics identify the actual normal
and whether it was retained or replaced by a supported candidate. This supersedes
the previous runtime behavior of resampling the input projection normal every
airborne frame. The native initialization and exact airborne transitions remain
open until their producers are reconstructed or measured.


## Contact normal aggregation

`reference.contact_normal` reconstructs the eligible-record accumulation loop and
normalization arithmetic. In record order, each eligible contact contributes
`float32(weight * normalLane)` to each of four float32 accumulator lanes.
Ineligible records contribute nothing. The sum is not divided by total weight
before normalizing; inserting such a division could change rounding.

For accumulated vector v, compute squared length with x + (y + z) reduction,
excluding W. With a supplied reciprocal-square-root instruction seed r, the
normalization scale is `(3 - ((r * squaredLength) * r)) * (0.5 * r)`, rounding
each operation to float32. Multiply the XYZ sum by that scale and explicitly
clear W. The instruction seed is a dependency because RSQRTPS is approximate.
The reference does not silently substitute exact square root. It rejects zero
length as an authored boundary rather than inventing a native fallback.

The [instruction comparison](../../native/snow_host/contact_normal_validation.json)
matched all four accumulated lanes in 128 cases and all normalized lanes in 98
nondegenerate cases. Normalization used the seed captured after the emulated
original RSQRTPS instruction. This verifies the downstream arithmetic given that
seed, not bit identity with a physical CPU's approximation.

The result is an intermediate candidate. Existing code still applies fallback
fitting, hemisphere/candidate selection and optional angular smoothing before
publishing the frame normal. Those stages and full contact-record producers
remain unresolved. This module is therefore not yet substituted for the runtime's
terrain candidate; doing so would omit known intervening behavior.


### Contact normal candidate selection

`reference.contact_normal.select_candidate` now reconstructs the comparison of
the normalized weighted candidate with a supplied fitted candidate. If the
previous-contact gate is false, retain the weighted candidate. Otherwise compute
both dot products against the prior cached normal with float32 x + (y + z)
reduction. Choose the fitted candidate when its dot is greater than or equal to
the weighted candidate's dot; equality explicitly favors the fit.

Before comparison, when fitted Z < float32(0.1) AND fitted-dot-prior <
float32(0.9), negate its lanes, overwrite Z with float32(0.01), then normalize
using the explicit reciprocal-square-root seed and the recovered refinement.
Recompute its dot against the prior normal before choosing. Both comparisons
are strict. The producer supplies zero W; correction negates it to negative
zero, which the returned four-lane candidate preserves. This sign does not
contribute to XYZ dot products but matters for exact stored bytes.

The [instruction comparison](../../native/snow_host/normal_selection_validation.json)
matched 324 four-lane selections, including 81 fit corrections and 120 fitted
selections. Candidate generation, the previous-contact flag producer, and later
angular smoothing remain outside this receipt. The correction uses a seed
captured from emulated RSQRTPS, not an asserted physical-hardware result. Tests
also cover no-history behavior, ties, strict low-Z boundaries and signed zero.
The runtime's terrain candidate remains labeled approximate until fitting and
smoothing are connected; this closes the intermediate selection boundary only.


### Normal angular smoothing gain

`reference.contact_normal.smoothing_gain` reconstructs the temporary gain used
for angular interpolation. Every call initializes current gain to float32(0.0001)
and cooks toward float32(0.75) with the supplied elapsed interval. ToZero base
and proportional terms are zero. ToOne proportional is also zero. ToOne base
is 60, except when prior normal Z < float32(0.15) and selected candidate Z >
float32(0.3), when base is 1. Both tests are strict. Snap epsilon is 0.0001.
The 60/1 selection is an additive base rate, not exponential damping. The actual
cooker/lookup path remains explicit to preserve arithmetic and any lookup-at-zero
rounding. The gain is freshly initialized; it is not a persistent filter state.

At dt=1/60 the ordinary branch reaches the 0.75 target, while the special branch
returns about 0.01677. This is a gain on an angular step, not directly a component
blend of the two normals. The [joined comparison](../../native/snow_host/normal_smoothing_gain_validation.json)
executes coefficient selection, original cooker and original lookup for 120 cases
with the reconstructed default table. All gain outputs match, including 24 slow
coefficient cases and strict Z boundaries. Only the floor helper is intercepted.

Inspection of the surrounding block shows additional gates: the runtime control
at +0xa6c must exceed float32(0.2), the cross-product lanes must not all be within
float32(0.00001), and the angle-table result must be nonzero. The cross product
of old normal and candidate supplies the rotation axis. The code multiplies gain
by the angle-table result and 0.5, constructs a quaternion using sine/cosine,
rotates the old normal, then normalizes it before writing the frame. The exact
angle-table initialization, trigonometric routines, runtime gate producer and
joined rotation remain unverified here. No complete smoother or runtime adoption
is claimed by this gain receipt.


### Normal quaternion application

`reference.contact_normal.rotate_normal` reconstructs the four-lane application
of a supplied XYZW quaternion to the old XYZ normal, followed by normalization.
With quaternion vector q, scalar w and old normal v, the XYZ expression is:

```text
p = q * v
d = p.x + (p.y + p.z)
c = cross(q, v)
r = ((c * w + d * q) + (w * w - 0.5) * v) * 2
```

Every product, subtraction and addition rounds separately to float32. The native
SIMD final multiplier is (2, 2, 2, 0), so W becomes zero by multiplication and
retains its arithmetic sign. The code then measures XYZ squared length using
x + (y + z), refines a supplied RSQRTPS seed, and scales all four lanes. The
reference preserves this order instead of using a generic quaternion helper.
Degenerate rotated normals are rejected as an authored boundary.

The [instruction receipt](../../native/snow_host/normal_rotation_validation.json)
compares all four output lanes in 514 cases, including identity and a quarter
turn. Other cases use synthetic unit normals and unit quaternions; not every
combination is necessarily reachable from the native smoothing axis. The
reciprocal-square-root seed comes from the emulated instruction. The receipt
does not cover quaternion generation, angle lookup or scalar trigonometry.
Those numerical services remain the missing connection between the recovered
smoothing gain and this recovered rotation block.


### Composed normal smoother

`reference.contact_normal.smooth_normal` joins the inspected gates, cross-product
axis, supplied angle lookup, temporary gain, quaternion construction and final
rotation. It accepts explicit angle, decay, sine, cosine and reciprocal-square-root
services. There are no implicit trigonometric or lookup substitutes.

The control <= float32(0.2) branch passes through the selected candidate. So does
the branch where every axis component is within float32(0.00001), or where the
angle lookup returns zero. This means exactly antiparallel old/candidate normals
pass through the candidate rather than rotating smoothly through an invented
axis. Otherwise compute halfAngle = float32(float32(gain * angle) * 0.5), then
quaternion XYZ = axis * float32(sine(halfAngle) / axisLength), with W from cosine.
The separate length guard uses an identity quaternion for length <= 0.00001.
The recovered rotation block produces the final four-lane normal.

The [joined instruction receipt](../../native/snow_host/normal_smoother_joined_validation.json)
compares the entire original block in 128 cases: 64 control bypasses, 24 axis
bypasses, 20 angle bypasses and 20 rotations. All final lanes match exactly.
The original cooker and decay lookup execute against the previously validated
reconstructed SSE table. The angle table is synthetic, sine/cosine calls use
intercepted host-math results rounded to float32, floor is intercepted, and the
RSQRTPS seed is captured from the emulator. Thus the result validates composition
under explicit service inputs, not original angle/trigonometric implementations.
Native gate-state production and fitted candidates remain supplied boundaries.
The runnable runtime still uses its documented normal approximation.


## Contact clock before normal rebuilding

`reference.contact_clocks.advance` reconstructs the three-field clock update.
All inputs and additions round to float32. If supplied immersion > float32(.001),
retain immersion, clear air time, and add elapsed time to contact time. Otherwise
clear immersion and contact time, and add elapsed time to air time. Equality at
.001 takes the air branch.

The inspected caller executes this block immediately before invoking normal
reconstruction. Consequently its small positive immersion values <= .001 have
already become zero when the normal builder applies its separate > 0 guard.
The isolated guard receipt above remains correct, but does not establish that
.00001 reaches rebuilding on this joined call route. This ordering narrows that
earlier boundary explicitly.

The normal smoother's previously unnamed +0xa6c control is this contact-time
accumulator. Its strict > float32(.2) test therefore activates angular smoothing
after accumulated contact time exceeds .2. Before then, candidate selection can
still occur, but the smoother passes that candidate through. This is not a
universal landing or grounded-state rule. The underlying immersion is supplied
by volume/contact geometry and is not interchangeable with a renderer's ground
flag. Float32 accumulation controls the exact frame crossing the threshold.

The [instruction receipt](../../native/snow_host/contact_clocks_validation.json)
compares all three outputs in 162 finite cases. The volume producer and elapsed
clock source remain inputs. The jump bench optionally accepts `contact_state`
with air_time/contact_time and per-frame `immersion`, then derives air time before
jump evaluation. It rejects simultaneous explicit air_time. This joins recovered
clock and jump arithmetic under authored scenario scheduling; it does not execute
the original collision query or prove the full simulation cadence.


## Player update intervals and worker migration

Reanalysis of two existing live captures checks the timestamp intervals around
selected player-wrapper calls. The [aggregate receipt](../../native/snow_host/update_interval_observation.json)
contains counts and source hashes, without actor pointers or body payloads. No
new game run or memory modification was performed for this analysis.

The first capture has 235 complete intervals, no observed same-actor overlap,
and 193 thread changes across 234 adjacent intervals. The second has 228 complete
intervals, no observed overlap, and 194 thread changes across 227 adjacent
intervals. Both exports report zero dropped records and successful installation,
restoration and drain. Neither has a reservation-order entry reversal or a
zero-duration interval.

This directly distinguishes observed serial execution from fixed thread affinity.
A future update experiment must follow the selected actor's execution context;
remembering the first worker thread would miss later updates. These recordings
do not prove that the scheduler excludes overlap in every mode, that the actor
remains alive outside each invocation, or that another subsystem cannot write
its state concurrently. The wrapper intervals include before/after snapshot
work. Timestamps with equal ticks cannot resolve finer ordering.

`scripts/analyze_update_capture.py` now reports interval overlaps per actor,
including enclosing intervals and calls whose body binding changes. Different
actors are kept separate. It also reports worker changes between nonoverlapping
neighbors and entry-order inversions relative to record reservation. Missing,
invalid and zero-duration intervals are counted explicitly. Synthetic tests
cover nested overlap, reservation reordering, rebinding, distinct actors, clock
ties, malformed intervals and migration without overlap.

The next scheduler question is which dependency or ownership mechanism orders
these migrating invocations. Join the selected actor callback to the dispatch
job and its request completion before inferring an execution gate. Input
publication needs its own timestamp and generation at that boundary; neither
capture establishes input ingestion order. No command queue or mutation API is
installed by this analysis.

### Engine-phase stationary body observation

The [resident engine-phase physics baseline](SCHEDULER_DELEGATES.md#live-stationary-actor-baseline)
now links 16 engine requests to 32 valid before/after snow-body observations. In
that session the main inverse mass is approximately 0.17580873 and the rider
inverse mass approximately 0.05, corresponding to rider mass 20 in the existing
body-unit convention. Main velocity and pending impulse remain zero. This is a
stationary live baseline, not an impulse-response experiment, universal tuning
value, or proof of physical units. It makes the two bodies and their mass fields
available for later request-correlated tests without invoking a setter.

## Animation-interface markup query

The branch-zero query helper at RVA `0xdda430` loads its receiver's `+0xb0`
interface and tail-calls slot `0xb8`. The inspected Kino factory installs table
RVA `0x2909790` on its returned interface; that table's slot resolves to
`0x12f2d20`. This is a static factory/type join. The live dispatcher's query
owner and that provider identity have not yet been joined in one guarded capture.

The query follows `interface+0x20 -> +0x80 -> +0x1a10` to a collection header.
Its count is the low 29 bits of the header's second word; records are 0x68 bytes.
The first word is header-relative only when bit 62 is set and bit 61 is clear;
otherwise it is absolute. These are build-specific layouts, not public API fields.

For each record, the key at +0x50 must match. Its float at +0x58 must not be
strictly greater than FLT_MAX, and its float at +0x5c must not be strictly less
than zero. Unordered comparisons do not reject under masked SIMD exceptions.
These are coarse interval checks, not an evaluation of the current clip clock.
The query packet requests flag bit 1, so the record's byte at +0x60 must contain
that bit. The helper at `0x12fbdf0` then collects paired values through
`0x12e9d40`; their producer and meaning remain external to this reconstruction.

```python
for record in graph_records:
    if record.key != query_key:
        continue
    if record.start > FLT_MAX or 0.0 > record.end:
        continue
    if not record.flags & 2:
        continue
    values = collect_second_words(record)  # still runs for selector ALL_ONES
    if selector == 0xffffffff:
        accepted = True
    elif selector == 0:
        accepted = all(value == 0 for value in values)
    else:
        accepted = any(value == selector for value in values)
    destroy_temporary_collection()
    if accepted:
        return True
return False
```

Empty collections accept selectors zero and all-ones, but reject other selectors.
The native function returns a boolean; the independent
[`markup_query.py`](../../engine/markup_query.py) additionally returns the first
accepted record index for inspection. Its 4096-record limit and argument checks
are authored safeguards. It acquires no live objects and provides no scheduler,
clock, locking or native allocation policy.

[Original-instruction validation](../../native/snow_host/markup_query_instruction_validation.json)
compared 1,440 synthetic cases with the portable model, including all four
relative-address flag combinations, key mismatch, record flags, empty/mixed
selector collections, float limits, infinity and quiet NaN. Original query and
selector instructions ran in an emulator; collection initialization, population
and cleanup were intercepted. Collector ordering and cleanup counts were checked.
This proves neither the collector implementation nor live player behavior.

Previously observed markup IDs 84 and 92 used keys `0x00c00002` and `0x00c0000b`
with selector `0xffffffff`. If their live provider is the inspected interface,
the selector does not further reject an eligible record after collection.
The next check is a fresh guarded join from dispatcher query owner to interface
and table, followed by graph-record observation at the actual markup update.
No generic queued-event callback is required by this static query route.

### Null-context collector resolved

Further inspection narrows the collector boundary above. The query packet's
first pointer is zero on this route. At `0x12e9d40`, that skips the optional
context comparison and leaves the source index at zero. The record starts with
another packed collection header, using the same bit-62/bit-61 address rule and
low-29-bit count. Its elements are two uint32 words, eight bytes per pair.

```python
# This query always passes context=None and starts with empty temporary storage.
source_index = 0
pairs_to_copy = record.pairs[source_index:]
if pairs_to_copy:
    old_count = len(temporary)
    grow_destination(old_count, len(pairs_to_copy))
    copy_bytes(temporary, old_count * 8, pairs_to_copy, len(pairs_to_copy) * 8)
# Selector logic inspects each copied pair's second word.
```

This path does not generate selector values or call gameplay handlers. It copies
existing record data. Destination growth and memory management remain external;
this observation is not a claim about their side effects or failure behavior.
The optional non-null-context branch is outside this query's contract.

[`query_markup_records`](../../engine/markup_query.py) now accepts complete
caller-supplied records with paired values, without an unknown collector callback.
It preserves the original first-match selection while returning the index for
inspection. Input validation and limits are authored, and it does not mutate
input records or acquire live memory.

The [extended instruction receipt](../../native/snow_host/markup_query_collector_validation.json)
repeats all 1,440 cases with the original collector instructions included. Only
initialization, destination growth, byte copy and cleanup services are intercepted.
The fixture checks collector order, growth/copy counts, query packet fields and
final boolean results. Both source and destination address flag modes are tested
in matching combinations; independent cross-combinations were not exhaustively
covered. Record production, live provider identity and concurrent mutation remain
unresolved. This supersedes the unknown-collector boundary for the null-context
route only, not for every caller of the collector.

### Graph-record copy and partition writers

Static inspection now identifies writers of the same `+0x1a10` collection
layout. These are candidate upstream routes, not a proved live-player call chain.
The [static range receipt](../../native/snow_host/markup_record_writers_static.json)
identifies the inspected instruction ranges. No execution coverage is claimed
for this receipt.

At `0x12fca20`, the first argument supplies a source collection and the second a
destination. The function reserves combined capacity, then appends each source
record in order using `0x128fd70`. Each append sets destination byte `+0x1a28`
to one. If the third argument's low byte is nonzero, it clears bit 0 of the newly
appended record's `+0x60` flag byte. It does not clear bit 1.

```python
reserve(destination, destination.count + source.count)
for record in source:
    append_record(destination, record)  # nested copy/allocation services external
    destination.marker = 1
    if clear_bit_zero:
        destination.last.flags &= 0xfe
```

The copy helper explicitly copies the key at +0x50 and the three 32-bit fields at
+0x54, +0x58 and +0x5c. It transfers flag bits 0 through 3 individually, preserving
the destination's upper nibble. Its nested copy service at `0x125bd60` remains an
unresolved ownership/allocation boundary. Do not model this as a raw shallow copy
of all 0x68 bytes or assume that upper flag bits come from the source.

At `0x1317050`, source is the third argument; the first and second arguments are
two destinations. Each source record is copied into temporary storage, its scalar
fields and low flag nibble are transferred, and bit 0 is optionally cleared.
The record key goes to `0x12fbc20`, which chooses the destination:

```python
for record in source:
    temporary = copy_record_with_external_nested_storage(record)
    if clear_bit_zero:
        temporary.flags &= 0xfe
    if recognized_key(record.key, optional_key_table):
        append_record(second_destination, temporary)
        second_destination.marker = 1
    else:
        append_record(first_destination, temporary)
        first_destination.marker = 1
    release_temporary_storage()
```

`recognized_key` first calls `0x12fbd00` on a global registry. That helper performs
an unsigned lower-bound search in a uint32 key collection, then tests equality.
If not found and the optional table is non-null, it scans 24-byte entries and
compares each uint32 at +0x10 with the key. The registry's semantic category,
ordering producer and optional table's owner are not yet established; assigning
names such as active, disabled or locomotion to the two destinations would be
premature.

A caller inside `0x12ca440` copies a collection to temporary storage, clears the
original through `0x126fbf0`, and calls the partition routine twice with different
sources and opposite clear-bit-zero conditions. The clear helper calls an
external cleanup routine for a nonempty collection and resets its low-29-bit
count. This establishes an actual copy/clear/partition sequence in static code;
it does not establish how often it executes or which scheduler phase owns it.

The immediate implication for the known markup query is narrow but useful:
clearing record bit 0 does not reject its mode-2 query, which tests bit 1. Whether
a record remains visible also depends on which destination becomes the queried
collection, its key and interval gates, and its lifetime. Next trace the caller's
source/destination owners and verify the live query provider before attributing
this partition to a particular rider action.

### Guarded provider observation

[`capture_markup_provider`](../../engine/markup_provider_observation.py) provides
an authored read-only adapter for the static provider join. The caller must first
verify the process/image and acquire a fresh dispatcher with external identity
guards. The adapter follows dispatcher+0x38, owner+0xb0, interface+0x20,
attachment+0x80 and graph+0x1a10. It requires interface table RVA 0x2909790 and
slot 0xb8 target RVA 0x12f2d20; a mismatch rejects the observation.

A null attachment yields an explicit absent result, corresponding to the query's
early false return. Otherwise the adapter accepts at most 64 records and reads
only the key, scalar +0x54 bits, interval bits and flag byte. All acquired pointers,
headers, scalar records and external guards are compared again before returning.
No nested pair arrays, live pointers, game calls, callbacks or writes are exposed.
Failure produces no partial result. Transport timeouts and process identity are
the caller's responsibility; the adapter is bounded but does not stop workers or
pin objects. Equal sequential reads are not an atomic snapshot and cannot detect
an intervening change that returns to the same bytes.

Synthetic tests cover the four packed-address modes, null attachment, empty and
oversized collections, wrong provider/target, changed record contents and short
reads. These tests validate the observer's rejection behavior, not live graph
membership. A live receipt remains required before claiming the rider's query
uses this provider. Nested values and actual notification execution require
separate observations even after that join succeeds.

### Live provider join

A [bounded live check](../../native/snow_host/markup_provider_live_validation.json)
now connects the acquired snow actor's motion component and markup dispatcher to
the expected provider table and query target. The registry actor and independently
acquired boxed ownership route agreed. External guards included component table,
component/controller backlinks, both markup-object links, actor table and actor
self-pointer. Independent selected-local-player identity remains unproved.

The accepted observation used 11 provider reader calls. The interface attachment
was present and its graph collection used header-relative addressing, with zero
records. All retained endpoint bytes matched on recheck. This proves the observed
provider membership and an empty collection at sampling endpoints; it does not
prove an atomic snapshot, an executed query, a notification, clip selection or a
motion release. No movement input was sent.

An earlier session rejected ownership acquisition because a root guard changed;
it never reached the provider observer. The next session used up to three fresh
ownership acquisitions without weakening the guards. Both sessions stopped the
research bottle and verified saves/settings restoration and the original DLL.
The private controller and raw addresses remain outside the repository.

The next useful observation belongs inside the markup update boundary, where
record production and consumption can be ordered. Repeated idle heap polling may
miss temporary records. The copy/clear/partition writers are static leads for
that possibility, not proof that this empty sample caught a specific phase.

### Typed markup-update recorder core

[`snow_markup_update_trace.h`](../../native/snow_host/snow_markup_update_trace.h)
and [implementation](../../native/snow_host/snow_markup_update_trace.c) add an
independent recorder for a receiver-plus-float call. The target candidate is the
motion component's slot 0x4b0, which preserves XMM1 into the markup update. This
core does not install a hook, resolve a component or sample live graph memory.
Its reader is supplied externally; snapshot fields are authored diagnostics,
not a recovered object layout. A native guarded reader remains to be connected.

The recorder forwards the float argument and records its raw 32-bit encoding,
component, caller, thread and entry/exit timestamps. The original callback is
void-typed because the inspected caller ignores its result; preserving arbitrary
return registers is not part of this contract. It never interprets the float as
a duration or animation weight. The producer's units remain a separate question.

A fixed reservation buffer avoids allocation on the call path. Overflow and
calls arriving after close still invoke the original without sampling. Closing
blocks new reservations; drain waits for admitted calls to finish. Only then can
records be read. Close/drain does not permit unloading: cached callers may still
invoke the wrapper, so its code, callbacks and context must remain valid. Readers
must return exactly one to accept a sample; other results zero it. Original or
reader nonlocal exits are not contained and can leave the recorder undrained.
Reservation order does not establish execution order across worker threads.

The [native fixture](../../tests/fixtures/snow_markup_update_trace_fixture.c)
checks 800 calls on eight threads with 17 reservations and 783 overflow forwards,
recursive calls, invalid samples, close during an active call, late forwarding,
zero capacity and argument-bit preservation for zero, negative zero, infinity and
quiet NaN. Native execution passed with address/undefined-behavior sanitizers;
the core also compiled with MinGW for Windows x64. These are fixture and compile
results, not Windows execution or live game ABI validation. Installation, guarded
sampling and live callback execution remain the next integration work.

### Native provider sampler

[`snow_markup_provider.h`](../../native/snow_host/snow_markup_provider.h) and
[implementation](../../native/snow_host/snow_markup_provider.c) provide the
bounded native reader needed by the typed recorder. Its snapshot replaces the
recorder core's initial placeholder diagnostics. It follows component/controller
backlinks, both markup links and the proved provider chain, requiring the known
component, controller and provider tables and query target. The caller still owns
fresh actor/component provenance and verified image/process identity.

It samples notification-array pointer/count, attachment state, packed graph header
and up to eight scalar records. It does not dereference the notification array or
nested pair data. Two full snapshots must agree; rejected reads zero the output.
This requires at most 46 read callbacks for eight records, each at most 17 bytes;
the declared public bound is 56. No allocation, writes or game calls occur.
Snapshots include private addresses and must be sanitized before publication.
Equal snapshots do not provide lifetime pinning, atomicity or ABA protection.

The [fixture](../../tests/fixtures/snow_markup_provider_fixture.c) checks all four
packed address modes, including a negative relative displacement, eight-record
sampling, every one of the 46 read-failure positions, mutation between passes,
broken backlinks, wrong provider table, oversize rejection and null attachment.
Native tests and ASan/UBSan pass; the source compiles for Windows x64. Recorder
lifecycle tests also pass with the expanded snapshot. No Windows execution,
slot installation or live update capture is claimed for this sampler yet.

### Windows markup-update slot wrapper

[`snow_markup_update_probe.h`](../../native/snow_host/snow_markup_update_probe.h)
and [implementation](../../native/snow_host/snow_markup_update_probe.c) expose an
experimental ABI-1 wrapper for the typed update recorder. Configuration specifies
the image data slot, original receiver-plus-float function, one component filter
and supplied reader/context; it does not install. Other components forward
without sampling. The original return value is intentionally outside the ABI.

Installation accepts an aligned committed non-executable image slot in the
original function's module, checks its expected pointer, then swaps only that
pointer with compare/exchange. It restores page protection and pins the wrapper
and target modules. Restore replaces only its own pointer, preserves competitors,
and can be retried. Call restore after any installation attempt, then close and
drain. The callbacks and reader context must remain valid for cached callers;
module pinning alone does not preserve caller-owned context. The capture limit
is 256 records. No code instructions are patched by this wrapper.

[Five authored Windows fixture runs under Wine](../../native/snow_host/markup_update_probe_wine_validation.json)
passed in separate processes: normal installation, competing replacement,
heap-slot rejection, closed-before-install and changed-original rejection.
The fixture checks negative-zero float argument bits through the installed slot,
receiver filtering, before/after sampling, exact record size, original pointer and
page-protection restoration, and quiet-NaN forwarding through a cached wrapper
pointer after close and FreeLibrary. The wrapper remains pinned. This exercises
the Windows x64 receiver-plus-float ABI in an authored fixture, not the game's
callsite. No game was launched; the research bottle was stopped afterward.

The [fixture source](../../tests/fixtures/snow_markup_update_probe_fixture.c)
and compile-only unittest are included. An example standalone build from the
repository root, using a Windows x64 MinGW compiler, is:

```sh
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -shared \
  native/snow_host/snow_markup_update_probe.c \
  native/snow_host/snow_markup_update_trace.c -o probe.dll
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror \
  -I native/snow_host tests/fixtures/snow_markup_update_probe_fixture.c -o fixture.exe
```

Run `fixture.exe` with the absolute DLL path and one mode name: `normal`,
`conflict`, `heap`, `closed` or `changed`. It touches only its own authored test
slot. Game integration still requires a bounded controller/plugin, fresh
component guards, the native provider reader, original-callsite verification,
and restoration evidence. This DLL alone is not a completed game capture tool.

### Triggered markup-update capture plugin

The opt-in [`markup_update_capture.c`](../../native/snow_host/examples/markup_update_capture.c)
plugin joins the native sampler and typed slot wrapper. Build it using
`scripts/build_snow_host.py --adapter steep --markup-update-capture-plugin --out`
with a build directory outside the repository. Its INI requires `[capture]`,
`enabled=1`, and `milliseconds` between 100 and 1000. A private controller supplies
fresh hexadecimal size/component/owner/actor/world fields, then creates the
INI path plus `.trigger`. Saved addresses must never be reused across sessions.

The worker waits at most 180 seconds. It checks original function/caller byte
signatures, actor/self/entity/world relationships and the native provider chain,
then temporarily replaces component table slot 0x4b0. It records float argument
bits and before/after scalar metadata, restores the slot, and closes/drains the
recorder. The plugin issues no movement input or original game calls of its own;
the wrapper forwards calls made by the game. Module/context lifetime remains
pinned for possible cached callers.

The `.armed` marker follows successful installation; `.done` means trace output
was written, not success. Inspect every summary flag and independently verify the
restored slot. `.trace.jsonl` includes caller addresses and belongs in private
session storage. Requested milliseconds are not an exact frame window; marker
I/O, restoration and sample overhead affect the interval. Stale trigger/armed/done
markers reject initialization. The controller must retain a session watchdog and
cleanup path, including on timeout or failed guards.

### First live markup-update boundary capture

The [live receipt](../../native/snow_host/markup_update_live_validation.json)
records 58 calls of the acquired motion component's slot 0x4b0 in a requested
500 ms capture. Every caller was RVA 0x34df47, the return site immediately after
that slot call in the inspected three-phase update routine. Nine distinct thread
IDs appeared. This establishes execution of the component update route, not
merely membership in a batch or the existence of a table entry.

All 116 before/after native samples passed their guards. Each snapshot reported
148 dispatcher notification records and zero graph query records. These counts
refer to different collections: registered notification records are not the
provider's currently available candidate records. No nested pairs or individual
notification callbacks were captured. Empty boundaries cannot rule out records
created and removed within the original call, nor do they show that any specific
notification record was evaluated.

The float argument varied across calls; its min/max/median are retained in the
receipt without assigning units. The static caller loads this value from its
helper result at +0x18 and forwards it through the phase calls. Neither its
numerical scale nor correlation with wall time alone establishes a physics
substep duration.

The plugin restored the original slot and the controller independently verified
it. No records were dropped. The host remained ready and unfaulted. The bottle
stopped, saves/settings were restored and the original DLL hash matched. No
movement input was sent. The next discriminating capture should include a
controlled action and selected notification cached/query states at this boundary;
a separate callback observation is still required to prove motion release.

### Selected notification-state sampling

The native sampler now includes IDs 84 and 92 when their indices exist in the
dispatcher's notification array. For each it reads query key, selector, pending
index bits, branch byte, force byte, cached byte and signed-link-count bits.
Raw integer bits are preserved rather than interpreting negative sentinel values
as positive counts. Missing indices are explicit absent records; counts above
4096 reject. No listener descriptors are copied or modified.

This extends the native sampler's previous count-only notification observation.
Both sequential samples include the selected fields, so changes between those
passes reject the whole sample. The eight-provider-record case now uses 50 read
callbacks, each at most 20 bytes, within the declared 56-call bound. Tests cover
all 50 read-failure positions, absent notification indices, the oversized-count
gate and the decoded selected fields; ASan/UBSan passed.

The expanded record changes the experimental Windows probe ABI from 1 to 2.
Consumers must check both ABIVersion and RecordSize and rebuild against the new
header. The older five-mode Wine receipt documents ABI 1. It is not retroactively
claimed as execution validation of ABI 2. A cached-value transition across the
original component update would still not prove which listener executed; reader
snapshots are distinct from direct callback tracing.

### Controlled-input cached-state transitions

A [live ABI-2 capture](../../native/snow_host/markup_update_input_live_validation.json)
recorded 98 original update calls across nine threads, all from RVA 0x34df47.
All before/after samples passed, no records were dropped, and both reports from
the gated W-input helper fell inside the captured call envelope. The helper held
scan 17 for a requested 500 ms; API acceptance and report timestamps do not prove
the game's ingestion time or causality by themselves.

Provider candidates appeared: the before-sample count was zero for 64 calls,
one for two, three for eleven, four for nineteen and six for two. ID 84 changed
cached value 0 -> 1 across call 51, then 1 -> 0 across call 72. Its key was
0x00c00002, selector all-ones, branch zero, force zero and link count one. ID 92
remained cached zero with key 0x00c0000b. Pending indices stayed all-ones.

For each selected ID in each call, the reconstructed key/interval/bit-1 predicate
was evaluated on the before-sample graph records. All 196 predicted booleans
matched the after-sample cached values. This is a live cross-check of the decoded
predicate against original state updates, beyond the earlier emulator fixtures.
Because both selectors are all-ones, nested pair contents cannot reject an
otherwise eligible candidate on the decoded query path; they were not sampled.
The comparison does not validate other selector modes against live records.

On the rising transition, the matching candidate had flag byte 3. On the falling
transition, the observed candidates had keys 0x80000001, 0x80000002 and 0x80000003,
with no matching ID-84 key. Those keys are identifiers, not decoded animation
names. The predicate correctly distinguishes absence of the matching record from
a universal empty collection.

This connects graph eligibility with the notification's cached-state changes
across actual component updates. It still does not directly bracket query entry,
listener execution or the downstream motion-release handler. Static notifier
logic predicts notification on these changes with the observed positive link
count, but no individual callback invocation or physical effect is claimed.

Original slot restoration was independently verified; the host stayed ready and
unfaulted. The bottle stopped, saves/settings were restored and the original DLL
was verified. Next capture the specific callback or its guarded actor-state
outputs alongside these transitions, preserving the distinction between a
predicted notification and an observed listener execution.

### ID-84 callback edge independence

The callback at RVA 0x5c7040 does not read the incoming markup ID, value byte or
sentinel. Both cached-state edges observed above therefore enter the same local
callback logic if notification invokes it. This differs from ID 92's callback,
which explicitly branches on the value byte. Neither edge of ID 84 should be
named activation or release based only on its boolean direction.

```python
def notification_84(controller, ignored_id, ignored_value, ignored_sentinel):
    if (controller.interface.available() & 0xff) == 0:
        return
    entity = controller.interface.entity()
    actor = lookup(entity, actor_type_token())
    if actor is None:
        return
    dispatch_motion_action_a(actor)  # return ignored; nested state decides action
    vector = [0.0, 0.0, 0.0, 0.0]
    vector_service(actor, vector)
    accumulate_scaled_pending(actor, vector)
```

The services occur in that order. The vector service at 0x516ad0 enters the
actor's motion dispatcher at +0x1010; it is not justified to replace it with a
no-op. The final accumulator at 0x1373c10 consumes the vector after that service.
Zero initialization does not prove the final vector is zero. The accumulator's
arithmetic and guards are documented earlier in this guide.

Adapter A at 0x536460 also enters the +0x1010 motion state machine. One branch
reaches 0x536620 only when the inspected nested state selectors permit it. That
helper tests the actor virtual-slot 0x4b0 predicate before clearing fdc and calling
the release service. It does not unconditionally clear fc9. Existing dispatcher
and release models remain the authority for those deeper state gates.

[`markup_motion_callback.notification_84`](../../engine/markup_motion_callback.py)
implements the observed orchestration with explicit supplied services. It returns
an authored completion diagnostic, not the native ABI result. No live lookup,
state-machine substitute, exception containment or rollback is provided.
[Original-instruction validation](../../native/snow_host/markup_callback84_instruction_validation.json)
compares 24 synthetic cases with the model: low-byte predicate behavior, null
actor and values 0, 1 and 255. All external services are intercepted. The fixture
also verifies the vector starts at positive zero and that modifications by the
vector service reach the accumulator. These results explain what to observe in a
live callback; they do not establish that the callback ran in the prior capture.

### Snow-state vector output

The vector dispatcher at RVA 0x516ae0 selects by the current motion-state tree
while holding its recursive lock. With dispatcher field +8 equal to zero, outer
selector 3 calls 0x516cb0, selector 1 calls 0x516f60, and selector 0 with child
selector 5 calls 0x516e70. Other selectors zero the output. When dispatcher +8 is
nonzero it leaves the supplied vector untouched. Deferred-transition processing
and unlocking follow. Thus the post-dispatch state, not just the markup value,
determines which vector feeds the accumulator.

The nested-selector-5 helper at 0x516e70 has now been decoded. Let `u` be the
owner's four-lane vector at +0x720, `n` the actor vector at +0x210 and `g` the
float at +0xe0 of the active handle payload reached through owner+0x50. Semantic
names and units of these fields remain unproved. For finite XYZ inputs with
fourth lane zero, the local calculation is:

```python
c = cross(n, u)
if all(abs(lane) <= float32(1e-5) for lane in c):
    output = g * u
else:
    length2 = dot(c, c)
    seed = hardware_rsqrt_estimate(length2)
    reciprocal_length = (3 - (seed * length2) * seed) * (0.5 * seed)
    output = g * cross(reciprocal_length * c, n)
```

Every multiply/add/subtract rounds as float32 in the inspected SIMD order.
For unit `n`, the nondegenerate mathematical expression is the normalized
projection of `u` onto the plane perpendicular to `n`, scaled by `g`. That
interpretation assumes a unit normal; the binary does not normalize `n` here.
A nonunit `n` changes output magnitude. Near-parallel inputs use the original
scaled direction instead of a zero projection. Do not replace that fallback.

[`markup_snow_vector.snow_vector`](../../engine/markup_snow_vector.py) implements
this finite-XYZ branch with explicit reciprocal-square-root seed injection.
[104 synthetic original-instruction cases](../../native/snow_host/markup_snow_vector_instruction_validation.json)
matched XYZ output bits exactly using the emulator's captured RSQRT estimate,
including nonunit normals, near-parallel fallback and randomized finite vectors.
This does not establish the physical CPU's approximation, arbitrary fourth-lane
behavior, NaN/overflow handling or live branch selection. Finite-input validation
is an authored restriction. The active handle and its payload are supplied by
the fixture; inactive handle behavior is not modeled as a safe null result.

The other two state branches and their vector producers remain separate leads.
Most importantly, the live ID-84 transitions do not yet prove selector 0/5 was
active. A next actor-state capture should include the dispatcher selector tree,
these direction/scale inputs and pending-vector output before attributing the
newly decoded projection to the observed rider movement.

### Shared selector-1 projection and selector-3 gain

Outer selector 1's helper at 0x516f60 reads the same active-handle payload gain
(+0xe0), invokes 0x519580 to construct the vector, and scales the returned vector.
The latter helper repeats the nested-selector-5 cross-product normalization and
near-parallel fallback, without applying gain itself. The
[selector-1 instruction receipt](../../native/snow_host/markup_selector1_instruction_validation.json)
compares 104 finite XYZ cases with `snow_vector`; all XYZ bits match using the
captured emulator RSQRT seed. This establishes shared local arithmetic despite
the different call structure, not shared authored state names or live activation.

Outer selector 3 uses a different gain helper at 0x519640. It reads the actor's
uint32 field +0xfcc and selects a float from the active payload reached through
a global manager's +0x20 handle:

| Actor state value | Payload float offset |
| --- | --- |
| 0 | +0x60 |
| 2 or 5 | +0x5c |
| 9 | +0x1a8 |
| Any other uint32 | Return positive zero; no payload-field read |

[`branch3_gain_bits`](../../engine/markup_snow_vector.py) exposes this mapping
with a supplied payload-field reader and raw float bits. It does not assign sport
names to the state values. [56 original-instruction cases](../../native/snow_host/markup_gain_instruction_validation.json)
matched the mapping, including negative-zero and NaN bit patterns, absent matches
and high-bit state values. The global pointer is still loaded by native code on
the default path, although its payload is not dereferenced there; the portable
helper models field selection, not that global memory access.

The selector-3 vector helper at 0x516cb0 first tests actor virtual slot 0x458.
If true it scales an entity transform direction. Otherwise it examines the length
of actor vector +0x250, chooses an entity-direction fallback at low magnitude,
and at greater magnitude computes a normal-relative projection using actor+0x210.
The entity-direction fallback can be sign-flipped by actor byte +0x1b4. Both
branches use the new gain selector. That full branch, its threshold and degenerate
cross-product behavior are not yet implemented or validated here. In particular,
its higher-magnitude branch does not visibly share the explicit cross-near-zero
gate of 0x519580, so blindly reusing `snow_vector` would change its behavior.

### Selector-3 vector calculation resolved

The finite-XYZ arithmetic of 0x516cb0 is now implemented by
[`branch3_vector`](../../engine/markup_snow_vector.py). This supersedes the earlier
unimplemented-vector boundary, while leaving live state selection, transform
ownership, arbitrary fourth-lane behavior and hardware RSQRT fidelity open.
The supplied direct-direction gate is the low-byte result of actor slot 0x458;
the reverse flag comes from actor+0x1b4. `v` is actor+0x250, `n` actor+0x210 and
`d` the resolved entity transform's +0x10 vector.

```python
if direct_direction:
    output = gain * d                 # reverse flag ignored
elif float32(sqrt(dot(v, v))) <= float32(0.01):
    output = gain * (-d if reverse_fallback else d)
else:
    c = cross(n, v)
    seed = hardware_rsqrt_estimate(dot(c, c))
    reciprocal_length = (3 - (seed * dot(c, c)) * seed) * (0.5 * seed)
    output = gain * cross(reciprocal_length * c, n)
```

Operations retain the native float32 order in the implementation. The magnitude
threshold is 0.01 in the stored vector's unproved units. The nonzero predicate
branch bypasses both magnitude and reverse-flag handling. In the projection
branch there is no small-cross guard. For parallel vectors with magnitude above
the threshold, RSQRT(0) and subsequent arithmetic produce NaNs under the emulator's
masked-exception configuration. This is an observed local degenerate result, not
proof that such inputs arise during gameplay. Replacing it with an invented
fallback would alter the recovered behavior.

[416 original-instruction fixture cases](../../native/snow_host/markup_branch3_instruction_validation.json)
cover direct/fallback/projection branches, both reverse states, the magnitude
boundary, parallel inputs and randomized finite XYZ vectors. Finite output lanes
match bitwise using captured emulator RSQRT seeds; NaN lanes match classification
without asserting a portable NaN payload. The virtual predicate and gain lookup
are intercepted, and the fixture uses the embedded entity-transform path. External
transform resolution, inactive handles and live callback selection remain outside
this validation.

### Motion vector dispatcher contract

[`markup_vector_dispatch`](../../engine/markup_vector_dispatch.py) now connects
the decoded local formulas to their state routes. Current mode is the motion
machine field +8, not an incoming event number. The owner at +0x10 supplies outer
state at +0x18 and child at +0x20; an inner state is read only on outer state zero.
Receiver depth counts child links below that owner.

| Current mode | Outer state | Inner state | Local operation | Receiver depth | Native return |
| --- | --- | --- | --- | --- | --- |
| Nonzero | Not read | Not read | Preserve existing output | None | 1 |
| 0 | 1 | Not read | Projection helper 0x516f60 | 1 | 0 |
| 0 | 3 | Not read | Direction helper 0x516cb0 | 1 | 0 |
| 0 | 0 | 5 | Projection helper 0x516e70 | 2 | 0 |
| 0 | Other combinations | As needed | Write four positive-zero lanes | None | 0 |

The callback's return is ignored by the dispatcher. The dispatcher's own return
distinguishes nonzero current mode from the mode-zero branch, not success of
vector generation. A helper producing NaNs or a zero vector still receives the
mode-zero return value. ID 84 ignores that result in turn.

`select_vector_route` returns descriptive labels and `dispatch_vector` performs
preserve/zero/external-callback behavior on caller-owned vector storage. These
functions do not implement the native lock or deferred-transition epilogue.
The caller must resolve fresh state and receiver ownership; no native execution
permission follows from obtaining a route label.

[90 original-instruction cases](../../native/snow_host/markup_vector_dispatch_instruction_validation.json)
matched route, receiver depth, vector contents and return value. The actual
uncontended lock acquire/release and active-dispatch depth instructions ran in the
emulator; thread identity and vector callbacks were intercepted, and deferred
flags were zero. Final lock ownership/depth and dispatch depth were checked.
This is not validation of contention, reentrant state mutation, pending-transition
processing or a guarantee that pre-update selectors survive ID-84's earlier
motion action unchanged. The latter is why live selectors should be sampled at
the relevant service boundary before attributing a vector to a branch.

### World-interval-scaled callback accumulation

The ID-84 callback's final service, RVA 0x1373c10, is a distinct producer from
the unscaled queue leaf documented earlier. It first requires actor+0x10 entity,
actor+0x168 runtime and entity+0x60 world pointers to be non-null. Failure at any
of those gates returns without reading the input vector. Otherwise:

```python
scale = float32(world.interval * 30.0)
for lane in range(4):
    runtime.pending[lane] = float32(
        float32(scale * input_vector[lane]) + runtime.pending[lane])
```

The world interval is the float at world+0x1060. The
[world-clock producer and accessor](INPUT_TO_ACTION_ROUTE.md)
identify it as processed milliseconds divided by 1000, supporting seconds. It
is not established as the physics substep interval. The constant is exactly
30.0. Thus an interval of 1/60 supplies a scale of 0.5 in this producer; the
subsequent pending consumer separately applies body inverse mass. Do not apply
this factor to the plain queue leaf or infer the vector's physical units from
the factor alone.

All four lanes participate, including W. The instruction order multiplies interval
by 30 before multiplying the vector, then adds the existing pending value. It
performs no locking or direct velocity mutation. The native MOVAPS operands require
aligned vectors. A source aliasing the pending buffer is loaded before the final
store, so the operation is accumulation of its prior value, not sequential lane
updates reading partially changed data.

[`queue_world_scaled_pending`](../../engine/markup_pending.py) implements the
finite-float32 arithmetic after pointer gates. [Original-instruction validation](../../native/snow_host/markup_pending_instruction_validation.json)
matched 200 arithmetic cases including five intervals, all four lanes and source
aliasing, plus three early-null cases with an unmapped input pointer. Those cases
verify the guards avoid input reads. The portable kernel takes values directly
and does not resolve pointers or provide synchronization.

This closes the arithmetic link from the callback's state-dependent vector to the
pending buffer. Live callback execution, which vector-state branch was selected,
its interval/input values and the pending consumer's relative timing still need
observation before claiming an end-to-end measured physical effect.

### Runnable vector-to-pending inspection

Run the authored synthetic example without any game files:

```sh
python3 -m engine.markup_vector_bench engine/examples/markup_vector_projection.json
```

The [inspection API](../../engine/markup_vector_bench.py) composes state-route
selection, the decoded XYZ vector formula and world-interval-scaled accumulation.
The [example](../../engine/examples/markup_vector_projection.json) uses post-dispatch
state 0/0/5, direction [1,0,1], normal [0,0,1], gain 2 and an explicitly synthetic
RSQRT seed of 1. It produces vector [2,0,0,0] and pending [1,0,0,0] at world
interval 1/60. This is a worked formula example, not measured game behavior.

JSON input requires schema `markup-vector-bench-v1`, explicit provenance
`authored_synthetic` or `caller_supplied_observation`, `post_dispatch_state`,
`pending_before` and `world_interval`. Formula routes also require `vector_inputs`.
Projection routes use direction/normal/gain; outer-three uses current/normal,
entity_direction/gain and boolean direct_direction/reverse_fallback. The gain is
already resolved by the caller. A normalization route requires `rsqrt_seed`;
`positive_infinity` represents the zero-length seed in a degenerate test. Missing
seeds fail rather than silently using another approximation.

`inspect(document)` returns route, receiver depth, dispatcher return, computed
vector, seed-request squared lengths, pending result and explicit boundaries.
The command supports `--output PATH`. It never modifies input documents. XYZ
formulas are composed with an authored zero W lane; no native W-bit equivalence
is asserted. Nonfinite vector results are represented as strings in valid JSON
and report `nonfinite_vector_pending_not_evaluated`, since the pending arithmetic
kernel intentionally accepts only finite inputs.

Crucially, the supplied state is the state at vector-service entry, after ID-84's
earlier motion action. The bench does not predict that transition, acquire live
objects, simulate the pending consumer or update body velocity. It assumes the
native entity/runtime/world presence gates already passed. This makes the decoded
formula chain usable while keeping the unresolved scheduler and callback links
visible. Tests cover the CLI example, preservation of caller input, skip/zero
routes, missing seeds and explicit nonfinite results.

### Actor state and pending-vector sampler

[`snow_markup_actor.h`](../../native/snow_host/snow_markup_actor.h) and
[implementation](../../native/snow_host/snow_markup_actor.c) provide a separate
native read-only snapshot for the next update-boundary capture. It verifies the
known actor table and self-link, resolves entity/world, and reads world interval
bits. It follows motion current mode and only the selector-tree links needed by
the decoded routing rules: outer state is absent for nonzero mode, and inner
state is absent unless outer state is zero. Absent is explicit, not state zero.

When actor.runtime is present, the sampler checks its table and actor backlink
before reading four pending-vector lanes. It also records actor normal/current
vector bits, gain-selector state, reverse-fallback byte and fc9/fdc bytes. It does
not interpret those bytes as universal grounded or immobility predicates.
A null runtime is represented explicitly and does not authorize pending-buffer
access. Fresh acquisition and selected-local-player provenance belong to the
caller. The current API requires entity/world to exist.

Two equal sequential samples are required; failures zero the output. The deepest
implemented route takes 40 reads, at most 16 bytes each, below the declared limit
of 48. These snapshots contain private addresses and need sanitization before
publication. They are not atomic, cannot detect all intermediate changes or ABA,
and do not pin any object. The sampler issues no game call, lock or write.

The [fixture](../../tests/fixtures/snow_markup_actor_fixture.c) exercises all 40
read-failure positions, pending mutation between passes, actor/runtime backlink
failure, mode-dependent skipped pointer reads and a null runtime. Native execution
and ASan/UBSan passed; Windows x64 compilation passed after fixing a compiler
warning. No live capture or Windows execution of this sampler is claimed yet.

This sampler is intentionally separate from notification observation. Even when
both are sampled around one original update call, a boundary state does not prove
the state used inside ID-84's vector service: its preceding action may perform
transitions. Such a combined capture can identify candidate correlations and
narrow where a direct service/callback observation is needed.

### Combined provider and actor capture

The capture plugin now samples actor state after each accepted provider sample,
with an independent `actor_valid` flag. An actor rejection does not erase a valid
provider sample. A failed outer actor/entity/world identity recheck still rejects
the entire observation. This keeps partial acceptance explicit instead of treating
unsampled actor fields as zeros. The experimental probe ABI is now 3 because its
record embeds the actor snapshot; rebuild consumers and check version/size.

Provider and actor observations are sequential, not one simultaneous snapshot.
Each performs its own repeated-read checks. Combined acceptance therefore cannot
prove the actor state was unchanged at the instant the provider fields were read,
and neither establishes internal callback ordering. The additional read overhead
also means capture timing should not be compared directly with uninstrumented
performance. All raw float fields are serialized as uint32 bits for later analysis.

### Live actor correlation at markup edges

The [combined live receipt](../../native/snow_host/markup_actor_live_validation.json)
contains 104 update calls from RVA 0x34df47 during a controlled W-input trial.
All 208 provider samples and all 208 actor samples were accepted. The input
helper's key-down/up reports both fell inside the callback envelope. No records
were dropped; restoration was independently checked, the host remained ready and
unfaulted, and bottle/save/settings/DLL cleanup passed.

Two calls bracketed ID-84 cached transitions:

| Record | Cached transition | State before and after | fdc before -> after | Pending buffer |
| --- | --- | --- | --- | --- |
| 56 | 0 -> 1 | current 0, outer 0, inner 5 | 1 -> 0 | Zero -> nonzero XYZ |
| 79 | 1 -> 0 | current 0, outer 0, inner 5 | 0 -> 0 | Zero -> nonzero XYZ |

The fc9 byte stayed one. These were the only nonzero pending snapshots among
208 samples; other samples contained zero. That does not identify the operation
that subsequently cleared or consumed the buffer. A later call changed the outer
state from 0 to 3 across the update without an ID-84 cached transition.

Both transition boundaries match the nested-selector-5 vector route and the
mode/state gate leading toward the unconditioned-by-fc9 release helper. The
observed rising-edge fdc change and two pending accumulations are consistent with
the decoded ID-84 service order. They do not directly prove listener invocation,
that the internal state stayed unchanged throughout the call, or that no other
writer contributed. The vector-owner direction and active gain were not sampled,
so the projection formula has not yet been compared with these live deltas.

The update's float argument matched the sampled world+0x1060 interval bit-for-bit
in all 208 before/after comparisons. Together with the existing clock producer,
this supports identifying this observed argument as the ordinary world interval
in seconds. It does not make it a physics-substep interval or prove the equality
for every callback path or game state.

The next focused observation is the vector source/gain at this state and the
specific callback/service boundary. That can distinguish a numerically explained
pending delta from the current temporal and structural correlation.
