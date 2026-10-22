# The selected player's actor is in the `BeforeSimulation` motion batch

This closes the static/live **membership** part of release gate 3 ([scheduler roadmap](../../engine/SCHEDULER_ROADMAP.md)) for one gameplay state. The selected player's snowboard actor is a receiver of `Physic::BeforeSimulation`, whose callback dispatches receiver table slot `0x270`. For this actor that slot is the already-traced player update that reaches action ingestion. The candidate batch named in the [input audit](SCHEDULER_INPUT_AUDIT.md#focused-follow-up-one-motion-batch-is-upstream-of-world-simulation), `Physic::PreBeforeSimulation`, was empty and had never been allocated.

Per-request execution and order against `PhysicsWorldStep` were later measured (sections below). Actor gates, riding state and input freshness remain open. Addresses below are image RVAs (preferred base `0x140000000`) for the analyzed image SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. Runtime pointers stay private.

## Static joins

All four facts below are checked as exact instruction bytes by the private capture before any live read.

| Fact | Evidence |
| --- | --- |
| Generic motion thunk | `0x8b9750`: `mov rax,[rcx]; jmp [rax+0x270]`. Each receiver's own table slot `0x270` is called. |
| `Physic::PreBeforeSimulation` | Job at action graph `+0x4ad8`; setup `0x907d4e` stores the thunk at `+0x4c98` (job `+0x1c0`). Gather `0x8be137` copies world registry entry 24 (`world+0x730`) into `graph+0x4c70` (job `+0x198`), append off. |
| `Physic::BeforeSimulation` | Job at `+0x4ca0`; the same setup stores the thunk (callee-saved `rbx`) at `+0x4e60` at `0x907e37`. Gather `0x8be150` copies entry 25 (`world+0x770`) into `graph+0x4e38`. |
| `Ai::UpdateAIPreUpdate` | Setup `0x905834` stores the thunk at `graph+0x1ca0` (job `+0x1ae0`). Builder `0x9119c0`, an inlined lock-and-copy, fills `graph+0x1c78` from entry 5 (`world+0x270`, count `+0x278`, lock `+0x280`) and another job from entry 4. |

Registry entries begin at `world+0x130` with stride `0x40` (pointer, signed count, tagged capacity), as in the [membership follow-up](SCHEDULER_MEMBERSHIP_FOLLOWUP.md). All three jobs carry the shared range-job table `0x1ec7f38` live. A constructor at `0x8b0d5c` that installs `0x1e92e70` at offset `0x4ad8` builds a different object; the live value settled this.

The input audit's setup already registers `PreBeforeSimulation -> BeforeSimulation -> PhysicsWorldStep`. Run5/run37 private evidence binds the player's slot `0x270` to `0x564ee0`, which passes the actor's motion object (`actor+0x1010`) to `0x5654c0` and on to action ingestion `0x541da0`.

## Live result

A bounded Highball/D3DMetal session reached gameplay through startup navigation, acquired the player freshly, then made two guarded passes. There were no gameplay inputs, memory writes or debugger. The [sanitized receipt](live_motion_membership_validation.json) records the outputs and hashes of the private result and acquisition.

| Batch (registry entry) | Source count | Storage capacity | Remaining | Player receivers |
| --- | --- | --- | --- | --- |
| `Physic::PreBeforeSimulation` (24) | 0 | 0 | 0 | none |
| `Ai::UpdateAIPreUpdate` (5) | 1 | 1 | 0 | index 0: owned component, table `0x1e789b8`, slot `0x270` -> `0x67ceb0` |
| `Physic::BeforeSimulation` (25) | 5 | 5 | 0 | index 2: **the acquired actor pointer**, table `0x1e7a350`, slot `0x270` -> `0x564ee0`, storage index 2; index 1: owned component, table `0x1ee5a40` |

Both passes matched. The actor match is pointer equality with the acquisition's actor, whose table and `actor+0x10 == entity` link the acquisition already guards. The animation Kino membership reproduced at source and storage index 3 of 4.

A registry scan of entries 0–31 found the entity pointer itself in none of them. Components owned by the entity (qword at receiver `+0x10`) appear in entries 4, 5, 8, 12, 13, 15, 16, 17, 19, 23, 25 and 30. The registries hold components, not entities. The owner offset is proven for `KinoComponent` and confirmed for the actor; for other receiver layouts it is an assumption, so the scan names it as such.

Earlier sessions in the same series show the guards working: one stopped at a wrong job-table expectation before reporting anything, and one found PreBeforeSimulation unallocated.

## Per-request submission (passive burst)

Burst sampling of both jobs' headers (287 accepted samples over ten roughly 24 ms bursts, read-only) showed `BeforeSimulation` and `Ai::UpdateAIPreUpdate` requested and started together. That happened about every 12 ms, with identical counters in 283 samples. The request-to-start window was visible with one dependency hold (21 samples). One sample caught the AI batch started with one unclaimed receiver while `BeforeSimulation` was still held. Execution counters and the `BeforeSimulation` claim count were always zero: claiming finished faster than the sampling could catch.

## Execution: entry probe

With explicit approval, a private Snow-host plugin replaced **one heap pointer** by compare-and-swap. That pointer is `BeforeSimulation`'s installed callback field, which held the motion thunk. The plugin pointed it at a recording thunk that saves the argument registers, records the entry, restores the registers and tail-jumps into the original thunk unchanged. No game code or tables were modified. The field held the expected thunk and the job held the range table before install, and the plugin compare-and-swapped the field back after a 10 s window. Exit is not recorded, because the callee's full signature is not known. A synthetic Wine test (four threads, forwarded arguments checked) passed before the live run.

| Measure (10 s live window) | Result |
| --- | --- |
| Install / restore | installed, restored, 0 records dropped; game continued, session closed normally |
| Selected actor entries | 1,009, exactly one per `BeforeSimulation` request (1,009 distinct request counts) |
| Job state at actor entry | started equal to requested in 1,009 of 1,009 |
| Relation to world `Step` | request count minus Step last-run count constant across all entries: one request per Step |
| Relation to `EndFrame` | Step last-run exactly one ahead of EndFrame at every entry: within the Step frame |
| Threads, cadence | 10 distinct worker threads; median 9.87 ms between actor entries (p10 9.02, p90 10.81) |
| Other receivers | 4,036 entries: the batch's other four receivers, once per request |

Two further 10 s windows replicated this. One was standing: 948 of 948 actor entries, exactly once per request. In the other, forward was held through chained 1.5 s holds for part of the window: 1,002 of 1,002. Game acceptance of that input is unverified. The batch's other receivers rose from exactly 4 to about 4.84 per request during the hold, so membership changed, yet the actor still entered exactly once per request. Over all three windows: 2,959 of 2,959.

This joins membership to execution: in this gameplay state, the selected actor's slot-`0x270` route into action ingestion is entered once in every world request, on worker threads, inside that request's Step frame. The probe is a research tool with build-specific addresses and is not published.

## Order against `PhysicsWorldStep`

**Static chain.** The physics-state constructor (`0x136a550`, bounds from the image's exception table) builds a chain of jobs in a 0x13a0-byte state object. It names the job at `state+0x1b0` `PhysicsWorldStep`, stores its callback `0x8ab390` in that job's delegate (field `state+0x360`), and keeps the job's address at `state+0x10`. Its creator stores the state at `physics+0x18` and passes `physics` as the state's first field. The action-graph setup (`0x90835b`) hands `BeforeSimulation` to a physics-service method (`0x13a75e0`, vtable `0x2911780`, slot `0x70`) with `world+0xff0` as the physics object. That method registers three successors of `BeforeSimulation`: `[state+0x10]` (the step job) and two further jobs at `state+0x368` and `state+0x520`. The live chain matched: `world+0xff0 -> physics`, `physics+0x18 -> state`, `[state] == physics`, `[state+0x10] == state+0x1b0`, the callback field held `0x8ab390`, and the step job carried the vtable its constructor installs (`0x1e89618`).

**Counters at actor entry.** With the entry probe also reading the step job's counters (still one pointer swap), a 10 s standing window gave 1,002 of 1,002 actor entries once per request. At every entry the step job's request count equalled `BeforeSimulation`'s and its started count was one behind: the world step of that request had been requested but had not started.

**Entry/exit probe.** With further explicit approval, a second private plugin swapped **two** heap callback pointers by compare-and-swap and restored both:

- `BeforeSimulation`'s field became a call wrapper recording entry and exit. This is safe for this job because its only caller, the range-job chunk loop (`0x8f2b60`, range table slot `0x80`), passes just the receiver and ignores the result. The wrapper carries unwind information.
- `PhysicsWorldStep`'s field became an entry-only pass-through.

A synthetic Wine test checked balanced entry/exit, preserved return and callee-saved registers, a stack walk through the wrapper, intact step arguments, restore, and refusal on a wrong step callback.

| Measure (10 s standing window) | Result |
| --- | --- |
| Install / restore | both installed and restored, 0 records dropped; session closed normally |
| Requests | 701; actor entry and exit once per request (701/701); step entry once per request (701/701) |
| Request association | step request count equal to `BeforeSimulation`'s at every step entry; started equal to requested; inside the Step frame |
| Order | in 701 of 701 requests every receiver call (3,505, including the actor's) returned before `PhysicsWorldStep`'s callback was entered; none returned after |
| Gap, last return to step entry | median 11 µs (min 2, p90 17, max 83) |
| Actor call duration | median 22 µs (p90 31, max 81) |
| Threads | 10 for the actor, 10 for the step |

In this state the selected actor's update completes before the world step of the same request begins. The cadence was about 14 ms per request in this window against about 10 ms in the entry-only windows; whether that is probe overhead or variance is not established. The short actor call while standing is consistent with the actor's internal gates returning early, which is not yet examined.

## What this establishes and what it does not

Established for this state:

- the selected player's actor, by exact pointer, is in entry 25 and in `BeforeSimulation`'s gathered storage at the same index;
- that batch's installed callback dispatches slot `0x270`, which is the traced player update that reaches action ingestion;
- the earlier candidate `PreBeforeSimulation` carried no receivers this session.

Not established:

- (now shown by the entry probe) per-request invocation of the actor's callback;
- (now measured) the order of that invocation against `PhysicsWorldStep`: completed before the step's entry in 701 of 701 requests;
- that the actor's gates (activity, controller, actor `+0x1fd` skip) passed inside the call;
- riding or other gameplay states: the player had just spawned and no input was sent;
- input freshness: who writes the action payload and when it is published.

`callback_execution_established`, `input_freshness_established` and `safe_to_step_established` remain false in every output.

## Reader and validation

[`engine/motion_membership_observation.py`](../../engine/motion_membership_observation.py) provides:

- `capture_motion_membership(readv, entity, world, image_base, guards, job=..., entry=..., actor=None)` for the three named batches. It checks the job table and the installed thunk, then reports per receiver whether it is the entity or the supplied actor, whether it is owned by the entity, its table and slot-`0x270` RVAs, and its storage and unclaimed indices.
- `scan_registry(readv, entity, world, guards, entries=32, image_base=None)`, which reports where the entity and its owned components appear. Implausible headers are marked invalid rather than followed.

Both bound counts (256 source receivers, 1024 storage slots), recheck every followed header and identity field, and never dereference destination storage values. Thirteen synthetic tests cover the three batches, actor and owned matches, unclaimed prefixes, empty sources with stale storage, tables outside the image, identity-check failures, malformed headers, replaced sources and short transports.

## Next

1. Examine the actor's internal gates (activity, controller, `+0x1fd` skip) inside the call.
2. Repeat the membership and order measurements during verified riding.
3. Continue the separate freshness work on the action payload writer.

## Motion ingestion gates, original-instruction validation

A subsequent isolated emulation executed the original actor entry and nested
motion-update branches in 192 synthetic cases. All cases passed. The
[validation receipt](../../native/snow_host/motion_gate_validation.json) records
code hashes, inputs and outcomes. This establishes local branch behavior with
substituted callees, not live input consumption.

The gate order is:

```text
actor_before_simulation(actor):
    decrement_nonzero_countdown(actor)
    prepare_motion(actor.motion)          # body unresolved here
    prepare_actor(actor)                  # body unresolved here
    update_speed_state(actor)             # happens before activity gates
    if actor.activity_byte == 0: return
    controller = resolve_signed_handle(actor.controller_handle)
    if controller.block_byte != 0: return
    if actor.motion_enabled_byte != 0:
        update_motion(actor.motion)
    continue_actor_bookkeeping()

update_motion(motion):
    actor = motion.actor
    if actor.predicate_a():
        prepare_a(motion)
    elif actor.predicate_b():
        prepare_b(motion)
    if actor.skip_byte != 0: return        # read AFTER preparation
    ingest_actions(motion)
    update_optional_auxiliary_flag(motion)
    prepare_carrier(motion)
    dispatch_motion_state(motion)
```

These names describe roles for this explanation; they are not recovered type or
field names. Build-specific anchors are actor entry `0x140564ee0`, nested update
`0x1405654c0`, ingestion `0x140541da0`, activity byte `+0x1fa`, controller handle
`+0xff0`, controller block byte `+0xfc`, motion enable byte `+0xfc9`, skip byte
`+0x1fd`, motion object `actor+0x1010`, and its actor pointer `motion+0x40`.
Predicates use actor slots `0x458` and `0x460`. Preparation A takes precedence;
false from both predicates still permits ingestion when skip is zero.

The actor's later `+0xfc8` eligibility calculation is downstream of this optional
motion call. Its additional gates must not be imported into the earlier
input-ingestion condition.

Validation covered all 64 combinations of the four gate bytes and two predicate
results, each with preparation leaving skip untouched, clearing it or setting
it. The latter two mutations were supplied by the test. They demonstrate why a
skip snapshot at callback entry cannot alone establish whether ingestion ran;
they do not prove either preparation helper writes that field. The test checked
preparation precedence and ingestion/carrier/dispatch order. It substituted all
helper bodies, used a valid stable controller handle and null auxiliary object,
and stopped before later actor bookkeeping.

### Consequence for the next recorder

Record the ingestion call itself, or its return site, to establish consumption.
An outer callback entry and its gate-byte snapshot are supporting context only.
Associate that event with the existing request and direct native substep records
without assuming a fixed counter offset. Record action payloads at ingestion and
at the snow consumer separately. Equal payloads would establish observed reuse
only; a writer/publication event is needed to establish freshness. None of these
new correlated observations has yet been captured live.

## Preparation B pose history

Inspection of both preparation exports found no direct store to the actor skip
byte. This does not establish that the callees leave it unchanged: preparation A
can emit events and preparation B can call a further motion consumer. Those
transitive effects remain unresolved. All 350 exported instruction spans across
both functions matched the analyzed image.

Preparation B (`0x1405659d0`) resolves a provider through the actor's entity,
looks up key `0xa5661995`, and retrieves a two-vector pose from a provider-owned
object. The meaning of that key and the active actor predicate remain open.
Its local history logic is now executable in
[`engine/motion_pose_history.py`](../../engine/motion_pose_history.py):

```text
provider = lookup_provider(actor.entity)
if provider is not null:
    key_index = lookup_key(provider, 0xa5661995)
    if key_index == 0xffff:
        sample_count = 0
    else:
        previous_pose = current_pose
        if sample_count < 2:
            sample_count += 1
        current_pose = retrieve_pose(provider, key_index)
        if provider_pose_flags.bit26 == 0:
            current_pose = convert_using_provider_transform(current_pose)
if sample_count >= 2:
    blocked = false
    evaluate_downstream_guard(actor.motion, &blocked)
    if not blocked:
        call_further_motion_consumer()
```

Current and previous poses occupy motion `+0x3d0..+0x40f`, each 32 bytes;
the count byte is `+0x410`. The provider's pose object is at `+0x258` and its
flags at `+0x8c`. The conversion branch contains rotation/translation arithmetic,
but its exact convention is outside this validation. The independent API accepts
an already resolved final pose and preserves its bits as opaque bytes.

Twelve original-instruction emulation cases tested missing provider, missing key,
and valid direct-pose lookup with initial counts 0, 1, 2 and 255. See the
[receipt](../../native/snow_host/motion_history_validation.json). A missing
provider preserves both poses and the count, and can still reach the downstream
guard using old history. A missing key resets only the count, retaining the pose
bytes. Valid lookup shifts history and increments only counts below two; values
above two remain unchanged. Therefore this is not a guarantee of two consecutive
fresh samples, nor a counter measured in physics substeps.

Resource helper results were synthetic. Provider bit26 was set to select direct
pose storage. The downstream guard was forced to reject, so the further consumer
was not executed. This does not prove animation playback, physical actuation,
input freshness, skip mutation, or live selection of this branch.

The independent model's tests compare all 12 receipt outcomes, exercise a missing
provider gap followed by key invalidation, and reject malformed API inputs. The
model is an inspection kernel; it is not wired into every snow substep because
that would invent an update cadence. A future capture should correlate this
branch's invocation and count with motion requests before assigning it a clock.

## Pose history feeds query endpoints

The further consumer is `0x14055ace0`. Its inspected body checks actor `+0xfe4`,
a required motion `+0x48` object, and a time threshold before iterating a
configuration array with 28-byte records. It invokes `0x1404ece90` for each
record and stops at the first true return. The result becomes motion `+0x565`
in preparation B. This alone does not identify the gameplay meaning of that byte.

The query helper calls `0x1404f5700`, which consumes the history directly:

```text
start = previous_position + rotate(previous_rotation, record.local_point)
end   = current_position  + rotate(current_rotation, record.local_point)
displacement = end - query_shape_origin
length = norm(displacement)
# after a minimum-length test:
direction = displacement / length
hit = execute_query(shape, direction, length, world)
if hit:
    copy_hit_to_caller_output()
return hit
```

The endpoint helper builds a transform whose translation uses `start`; the
subsequent shape initializer and backend are not independently validated here.
Thus the endpoint pair is established, while identifying the whole operation as
a swept collision query is an interpretation of its construction and call flow.
It is not a velocity calculation: the endpoint prefix has no division by time.
The exact shape type, hit filtering and physical response remain unresolved.

`query_endpoints` in the independent pose-history module implements the endpoint
prefix. For quaternion `(q,w)` and point `v`, its rotation helper evaluates:

```text
rotated = 2 * (dot(q,v)*q + w*cross(q,v) + (w*w - 0.5)*v)
endpoint = position + rotated
```

The implementation preserves the inspected float32 operation order. It does not
normalize the quaternion. The helper's fourth output lane is zero; the API
returns XYZ. Previous/current positions are the first vector of each history
pose, and XYZW quaternions the second vector. This convention is now established
for this consumer; it does not identify the resource key or actor sport.

The [endpoint receipt](../../native/snow_host/motion_endpoint_validation.json)
contains 32 synthetic cases executed through the original endpoint prefix and
original rotation helper without substituting those calculations. Both XYZ
endpoints matched the independent implementation bit for bit, including an
identity rotation case and arbitrary nonunit quaternions. Execution stopped
before query orientation construction. No collision backend, hit publication,
live motion path or input freshness was validated.

The next useful targets are the record-array owner and the downstream hit/flag
consumers. They can establish what the query tests and how it affects motion.
The lock-protected guard `0x14052c4a0` is also a state-machine query with possible
deferred processing, so treating it as a side-effect-free boolean getter would
be premature.

## State guard and deferred work

The guard called before the pose-history query, `0x14052c4a0`, is now validated
through its ordinary pending-service path in 400 original-instruction emulation
cases. See the [receipt](../../native/snow_host/motion_guard_validation.json)
and independent [decision API](../../engine/motion_query_guard.py).

Its decision portion is:

```text
result = true
if motion.bypass_count == 0:
    if parent.state == 3 and child.state == 2:
        output_byte = 1
        result = false
    elif parent.state == 0 and child.state in {0, 3, 4}:
        output_byte = 1
        result = false
# all other branches preserve output_byte
return result
```

The states are numeric labels, not identified gameplay names. The second test's
last value is 4: the instructions subtract 3 before comparing the remainder to
1. An initial transcription interpreted that comparison as original state 1;
the original-instruction matrix rejected it and the model was corrected before
commit. Output preservation also means the return value is not generally the
logical inverse of the caller's byte. Preparation B initializes that byte to
zero and tests it after return; it does not use the function return value.

The surrounding ordering is part of the finding:

1. Acquire the recursive lock at motion `+0x20`, or reuse same-thread ownership;
   increment lock depth at `+0x28`.
2. Increment query nesting at `+0x30`, evaluate the predicate, then decrement it.
3. Inspect flags `+0x34` and `+0x35`. With repeat processing disabled and pending
   work set, call `0x1404eb310` once while the lock remains held. With repeat
   processing enabled, the code additionally checks query nesting and may loop;
   that branch is not covered by this validation.
4. Decrement lock depth. At zero, clear the thread owner to `0xffffffff`, execute
   the ordering instruction, and release the lock word. Return the saved result.

The bypass count is `+8`; parent pointer is `+0x10`; each inspected state's
numeric field is `+0x18`, with child pointer at parent `+0x20`. These are build
anchors, not portable object layouts. The independent API implements only the
predicate. It does not invent synchronization or deferred transition behavior.

Validation crossed bypass 0/1, parent and child states 0..4, initial output 0/1,
unowned versus same-thread nested lock, and absent versus present pending work.
The real instructions restored query depth and lock depth; the nested case kept
the existing lock owner. The service stub verified that query depth was already
zero and the lock was still held, then cleared the pending flag. Thread identity
was supplied; contention, repeat processing and actual deferred effects remain
unverified.

For input/scheduler observation, the important consequence is that this guard
can process work after evaluating its predicate but before returning to the
pose-query caller, all before the later action-ingestion call. Entry-time state
snapshots therefore cannot stand in for observations at the actual consumption
point. The next static target is the pending-work service and the writers of its
flags; live correlation should retain this ordering rather than flattening the
guard into a read-only boolean getter.

## Guard can return a decision from the previous state

The pending service is now connected to a concrete motion-state commit.
Sixteen isolated cases executed the original guard `0x14052c4a0`, service
`0x1404eb310` and commit routine `0x140555700` together. See the
[integrated receipt](../../native/snow_host/motion_transition_validation.json).
Only thread identity and leaf callbacks were substituted; the three routines'
branches, pointer assignments, pending flags and recursive-lock operations ran
as original instructions.

The service performs:

```text
acquire_recursive_motion_lock()
if query_depth == 0 and service_enabled_byte != 0:
    query_depth = 1
    pending_service_byte = 0
    commit_or_service_current_state()
    query_depth -= 1
else:
    pending_service_byte = 1
release_recursive_motion_lock()
```

`service_enabled_byte` is motion `+0x2c`; its actual lifecycle meaning is not
identified. Clearing the pending flag occurs before entering the commit routine.
A request made during callbacks could set it again; this experiment used inert
callbacks and does not establish the actual reentrant writers.

The commit routine reacquires the same recursive lock and performs:

```text
if pending_object != null and pending_mode != 2:
    if current_object != null:
        current_object.callback_slot_0x10()
        # Current is reread after that callback.
        if current_object != null:
            current_object.callback_slot_0x00(argument=1)
    current_object = pending_object
    current_mode = pending_mode
    pending_object = null
    pending_mode = 2
    current_object.callback_slot_0x08()
else:
    if current_object != null and current_mode == 0:
        service_current(current_object)
if secondary_object != null:
    service_secondary(secondary_object)
```

Build anchors are current mode `+8`, pending mode `+0xc`, current object `+0x10`,
pending object `+0x18`, secondary object `+0x38`. Mode 2 suppresses commit even
when a pending pointer exists. Names such as exit/dispose/enter in the receipt
are role interpretations of callback ordering; their actual bodies were not
executed. In particular, argument 1 to slot zero does not itself establish
allocation ownership or complete destruction behavior.

The guard saves its predicate result before calling this service. In tested
commit cases it returned the old-state decision after publishing the new state.
The caller's output byte likewise retained the result of the earlier predicate.
The new state's slot-8 callback observed current=new, pending=null, pending
mode=2. All three lifecycle callbacks ran at recursive lock depth 3 and query
depth 1. The chain restored both depths to zero and released the lock afterward.

The matrix crossed blocking/nonblocking old-state predicates, service enabled
or disabled, pending object present or absent, and pending mode 0 or 2. Disabled
service retained the pending-service byte. Enabled service cleared it in these
inert-callback cases, including cases where no transition was eligible. Current
mode was zero, the secondary pointer was null, and repeat processing was off.
No contention, callback reentrancy, exceptions, concrete sport-state identities,
or live original-game transition was tested.

This narrows the recording requirement: a guard's return value cannot identify
the state that will consume the subsequent actions. Capture current-state
identity at ingestion itself and, when tracing transitions, capture publication
before the new-state entry callback. Do not place an arbitrary mod callback in
that publication window: lock ownership is known locally, but lifecycle and
reentrancy contracts remain unresolved. The next useful join is the writer that
requests a pending state and sets these mode/enable/pending fields.

## Disable parks the current state in the pending slot

Tracing pending-slot writers identified a disable/enable lifecycle, rather than
a general request enqueue API. The original disable `0x1404fdc20`, pending
cancellation `0x1405557f0`, enable `0x1404e8550`, service and commit routines
passed eight integrated synthetic cycles. See the
[receipt](../../native/snow_host/motion_suspend_validation.json).

```text
disable_motion():
    acquire_recursive_lock()
    if enabled:
        enabled = false
        cancel_pending()
        if current != null:
            current.slot16()
            pending = current             # reread after callback
            pending_mode = current_mode
            current_mode = 2
            current = null
        if secondary != null:
            secondary.slot16()
            if secondary != null: secondary.slot0(1)
            secondary = null
    release_recursive_lock()

cancel_pending():
    acquire_recursive_lock()
    if pending_mode != 2:
        if pending != null: pending.slot0(1)
        pending = null
        pending_mode = 2
    release_recursive_lock()

enable_motion():
    acquire_recursive_lock()
    if not enabled:
        enabled = true
        service_pending()                 # depth and enabled gates still apply
    release_recursive_lock()
```

The byte at `+0x2c` now has an observed enable/disable role in these routines.
The current object is not passed to slot zero by the disable path: it is retained
in the pending slot. An already pending eligible object is passed to slot zero
before replacement. The secondary object follows slot16, slot0(1), clear-pointer
ordering and is not automatically recreated by the tested enable path.

Each tested cycle began enabled with current mode zero when current existed,
and eligible pending mode zero when pending existed. All eight combinations of
current, pending and secondary presence passed. Repeated disable did no further
callback work. Enable restored the parked current object through the real commit
routine, invoking its slot8 callback; repeated enable also did no further work.
Locks and query nesting returned to zero after every operation. Leaf callbacks
were inert, so no actual allocation was freed and callback-induced mutations,
exceptions or resource effects were not tested.

This means a pending pointer is not evidence of a newly requested sport or
motion state: it may be the previous current object parked while disabled.
Record enabled/current/pending/mode together when interpreting a snapshot.
The cycle does not restore physics, input, animation time, world state or random
state. It is neither whole-game pause nor backward stepping.

Other direct references to the cancellation routine include construction and
cleanup of objects with different surrounding layouts. Shared helpers do not
establish that every caller is the player's motion object. Candidate child-state
request routines near `0x1404fc720` write their own `+0x28`/`+0x1c` pair and then
service an owner at `+0x10`; that is a separate ownership join to trace before
calling them top-level transition requests. Generic request coalescing remains
unresolved.

## Nested requests and replacement

The mode-zero request at `0x1404fc720` is now joined to the owner service through
two nested state containers. Eight original-instruction chains validated this
join with successful synthetic allocation and inert lifecycle callbacks. See
[receipt](../../native/snow_host/motion_child_request_validation.json) and
[independent symbolic request model](../../engine/motion_child_requests.py).

The request cancels an eligible pending child through `0x1405363c0`, writes
pending mode zero, allocates and initializes a 32-byte child, then stores it at
container `+0x28`. The container's owner pointer at `+0x10` leads to the top-level
motion object. If owner `+0x34` is nonzero, the request tail-calls its service;
otherwise publication ends with a pending child. This identifies an immediate
service-request role for that flag, in addition to its repeat-processing role
in guarded callers.

The chain is:

```text
request_mode_zero(child_container):
    cancel_eligible_pending_child()        # sentinel for this family is 9
    pending_mode = 0
    pending = allocate_and_initialize_child()
    if owner.immediate_service_flag:
        service_owner(owner)

service_owner(owner):
    # enabled and query-depth gates described above
    # no eligible top-level replacement in the tested chain
    if owner.current_mode == 0:
        service_state(owner.current)

service_state(state):
    # no eligible replacement at this level in the tested chain
    if state.current_mode in {3, 4}:
        service_leaf_container(state.current)

service_leaf_container(container):
    if pending != null and pending_mode != 9:
        if current != null:
            current.slot16()
            if current != null: current.slot0(1)
            current = null
        current = pending
        current_mode = pending_mode
        pending = null
        pending_mode = 9
        current.slot8()
```

The intermediate state service is `0x1405159c0`; the leaf service is
`0x140526a80`. The intermediate container uses sentinel 5, the leaf sentinel 9,
and the top-level owner sentinel 2. These repeated layouts are distinct types
of state container. Applying one sentinel to all levels would change which
pending pointers get committed or canceled. The state labels 3 and 4 have not
been mapped to sports or named gameplay states.

The test crossed intermediate state 3/4, immediate flag 0/1, and owner query
depth 0/1. Two successive requests produced different lifecycle traces:

- Immediate and idle: old exit/dispose, first child enter, first child
  exit/dispose, second child enter.
- Deferred or busy: first pending child dispose, old exit/dispose, second child
  enter when service was invoked later. The first child never entered.

Thus repeated requests replace an uncommitted pending object on this path; they
do not form a queue of actions to replay later. Immediate requests can commit
before the requesting routine returns. In all cases the top-level current
pointer and intermediate current-container pointer were unchanged. Only the
leaf current pointer was replaced.

The deferred test explicitly cleared query depth before invoking service; it did
not prove which original scheduler boundary does that. No allocation failure,
concurrent requests, callback mutation or live input was tested. The symbolic
model reproduces successful request/callback ordering and is checked against
all eight receipts. It does not implement native synchronization or invent the
missing callbacks. Next targets are the caller of this concrete request and
its resource/state labels, followed by an observation at actual ingestion.

## Child entry consumes ingestion history

The mode-zero child's installed entry callback is `0x140573900`. Its table
`0x141e7a1d0` was read directly from the request's constructor sequence. The
callback now executes as original instructions inside the request/cancel/owner
service/nested commit experiment, rather than being an inert substitute.
Thirty-two cases passed; see the
[receipt](../../native/snow_host/motion_child_input_entry_validation.json).

```text
entry(child):
    # child -> container -> intermediate state -> motion owner
    ancestor_motion.cached_value_bits = ancestor_profile.value_bits
    child.motion.actor.flag = 1
    child.within_threshold = unsigned(child.motion.active_xy_count) <=
                             unsigned(child.motion.profile.threshold)
```

The copied profile word is `profile+0x30`, destination motion `+0x6bc`.
The actor flag is `actor+0x1b74`. The comparison reads motion `+0x384` and profile
`+0xe8`, writing the child's byte `+0x18`. Both profile accesses resolve the
signed handle at motion `+0x50`. The ancestor chain for the copy is
`child+8 -> container+8 -> intermediate+0x10`; the comparison instead uses the
child's direct owner pointer `+0x10`. The test makes those resolve to the same
motion object, but the routine itself does not check their equality.

The counter at motion `+0x384` has an inspected writer in ingestion
`0x140541da0`: it resets when both first-action X and Y compare equal to zero,
and increments otherwise, including unordered comparisons. Consequently the
entry flag samples a history of ingestion calls, not elapsed seconds or
necessarily physics substeps. This joins a concrete state-entry consumer to the
known ingestion writer. It does not establish the action payload's freshness,
the ordering of a particular live entry relative to that writer, or what later
behavior the child flag controls.

The integrated matrix retained intermediate states 3/4, immediate/deferred
service and busy/idle owner depth, and added counts 0, 3, 4 and `0xffffffff`
against threshold 3. All entry flags matched unsigned less-than-or-equal, the
profile word copied exactly, and the actor flag became one. Allocation,
disposal and exit effects remained substituted; entry was real. The independent
`sample_child_entry` API reproduces these local effects as an immutable result.
Profile units and actor-flag meaning remain unnamed.

The concrete caller `0x14055ddb0` constructs the intermediate mode-4 container,
then conditionally requests its mode-zero child when owner flag `+0x34` is set.
Its guarded caller `0x14055dc20` selects that path only under top-level mode 0,
intermediate state 3, and next child state 3. A caller at `0x140532dbe` then
reads actions `0x74` and `0x75`; those observations are static leads, not a
license to name this transition jump, landing or recovery. The next useful
consumer to trace is the child's `+0x18` flag, while preserving the ingestion
counter as a candidate observation channel.

## Input-history flag reaches a later transition request

The normal motion dispatcher `0x140565100`, already downstream of ingestion in
`0x1405654c0`, selects the mode-4/leaf-0 route through its jump table. That route
reads the concrete child's byte `+0x18` and passes it as the second argument to
`0x1405265f0`. This closes the local consumer join for the entry-time input-history
flag. It does not yet establish the final gameplay effect of the next request.

The consumer follows this ordered logic, with exact float32 comparisons:

```text
predicate = actor.slot_0x428()
value = motion.scalar_0x350
threshold = profile.scalar_0x60
if not predicate and threshold >= value:
    fallback_prepare(motion)
    motion.word_0x5e0 = 0
    fallback_request(intermediate_state)
    motion.byte_0x204 = 1
elif value >= threshold:
    motion.xyz_0x1d0 = (0, 0, 0)
    actor.byte_0x1b77 = 1
    actor.byte_0x1b76 = 1
    motion.byte_0x47e = child.entry_input_flag
    request_transition(motion, true)
```

The first predicate is a concrete virtual call, not a confirmed airborne or
contact flag. Neither scalar's units are established here. Equality selects the
fallback when the predicate is false and the second request when it is true.
Unordered comparison on either scalar reaches neither request under the tested
masked floating-point exception configuration. The input-history flag is copied
only on the second route; it does not select between these immediate branches.

Twenty original-instruction cases ran the real dispatch and consumer with a
supplied actor predicate and substituted external request bodies. They covered
both saved flag values, both predicate results, below/equal/above threshold,
NaN value and NaN threshold. The second route cleared exactly the inspected
three words, set both actor bytes and copied the flag; other routes preserved
those fields. Calls occurred under motion lock/query depth one, and both depths
returned to zero. See the
[receipt](../../native/snow_host/motion_child_dispatch_validation.json) and
`route_child_update` in the symbolic request module.

The next request target is `0x14055d030`. It accepts the boolean in the low byte
of the argument register; its caller does not clear the upper bits. It gates
again on the current hierarchy before dispatching a child handler. The earlier
full-register assertion in the private harness was corrected to inspect the
actual byte argument. No downstream transition body, physical impulse, animation
change or live call ordering was exercised in this pass. The next useful trace
is the consumer of motion `+0x47e` and the child handler selected by this request.

## Input-change latch consumer

A retained instruction export identified the next consumer of motion `+0x47e`
at `0x1404f64e0`. Its full local routine now passed 192 original-instruction
cases with supplied external setting/action gates. See
[receipt](../../native/snow_host/input_latch_validation.json) and
[executable latch math](../../engine/motion_input_latches.py).

Two sticky latches contribute to the returned combined byte:

```text
if first_latch == 0:
    distance_xy_squared = (baseline.x-current.x)^2 +
                          (baseline.y-current.y)^2
    retain_clear = (setting_gate or action_gate) and
                   not_ordered_greater(distance_xy_squared, threshold) and
                   (unsigned(first_nonzero_count) > 3 or action_gate)
    first_latch = not retain_clear

if second_latch == 0 and not secondary_suppressed:
    distance_y_squared = (baseline_secondary.y-current_secondary.y)^2
    second_latch = ordered_greater(distance_y_squared, threshold) or
                   unsigned(second_nonzero_count) <= 3

combined = first_latch or second_latch
return combined
```

The operations use float32 subtraction, multiplication and addition. Equality
does not satisfy greater-than. The inspected `JA` branches are also false for
unordered float comparisons, so replacing the first test with an ordinary
`distance <= threshold` changes NaN behavior. The independent API preserves
that distinction. Counts are ingestion calls, not milliseconds or substeps.

Build anchors: first/current vectors motion `+0x360` and baseline `+0x6e0`;
secondary current Y `+0x374`, baseline Y `+0x704`; counts `+0x384/+0x388`;
threshold profile `+0x68`; latches `+0x47e/+0x47f`; combined `+0x47d`.
Secondary suppression is motion `+0x5d != 0 or +0x65 != 0`. It prevents updating
the second latch here, while an already set latch remains set. The routine
also zeroes its local secondary-vector copy under suppression.

The setting gate comes from an external lookup with identifier `0x1519`. The
action gate combines an actor/controller eligibility byte with an external
query involving action IDs `0x7e` and `0x76`. Their user-facing meanings and
service contracts remain unresolved. The optional call controlled by motion
`+0x694` was disabled in this experiment. The baseline producers and external
latch-reset writers were not tested.

The matrix crossed both initial latch bits, setting/action gates, nonzero counts
3/4, unchanged/changed/NaN input and secondary suppression. It validated both
latch writes and the combined return. In this routine an already set latch never
clears, explaining how the entry-time history flag can affect later processing
even if the input changes afterward. This establishes an input-change gate,
not the final force, trick, animation or collision behavior. The transition
request separately constructs a mode-6 child through `0x14055d1f0`; joining that
child's update to this latch consumer is still required before treating the
static field match as a complete executed chain.

## Baseline publication and partial latch reset

The comparison baselines have a concrete branch-dependent writer in
`0x140532c70`. Its block `0x140532e3a..0x140532ec9` performs:

```text
smoothed = f32(f32((1-alpha) * smoothed) + f32(alpha * current_vector))
cached_word = ingestion_word
primary_baseline = ingested_primary_vector
secondary_baseline = ingested_secondary_vector
```

Here `alpha` is profile `+0x64`, smoothed is motion `+0x6f0`, and current vector
is `+0x360`. The word copies `+0x150 -> +0xb0`, primary `+0x160 -> +0x6e0`,
and secondary `+0x170 -> +0x700`. The primary baseline source is not the same
field as the smoothing input. Upstream ingestion can select an alternative
primary action, so replacing one with the other would erase a real distinction.
The branch follows the actor slot-`0x428` result in the inspected control flow;
it is not an unconditional once-per-frame baseline refresh.

Thirty-two original-instruction slice cases checked all copied bits and exact
float32 smoothing for alpha 0, 0.25, 1 and 1.5. There is no clamp in this block.
The test chose this branch directly and did not execute its preceding actor
predicate or establish how often it runs. See the
[receipt](../../native/snow_host/input_baseline_validation.json) and
`refresh_input_baselines` in the input-latch API.

A second concrete writer, reset prefix `0x140536260..0x1405362f1`, clears motion
XYZ `+0x1d0`, copies both ingestion vectors into the same baselines, sets first
latch to `unsigned(count+0x384) <= unsigned(profile_threshold+0xe8)`, and clears
second latch. It does **not** write the combined byte `+0x47d` in this prefix.
Eight cases spanning counts 0, 3, 4, `0xffffffff` and both prior combined values
passed. Subsequent actor/state operations were excluded from this validation.

The reset inspection API therefore reports the recomputed latch pair and the
preserved combined byte separately. A read-only snapshot must not assume those
values agree until the combined byte's producer has run. This is another reason
to capture at known execution boundaries rather than infer scheduler order from
apparently contradictory field values.

There are additional baseline/reset paths, including a conditional second-channel
reset near `0x14052e43c` and a baseline copy from motion `+0x7b0/+0x7c0` in other
branches. These remain separate leads, not covered by the new API. The latch
routine's callers gate its execution through actor `+0xff8` and the resolved
object's byte `+0x64`; when the combined latch is true they call `0x1404f66f0`.
That downstream arithmetic and its actor/body consumer are the next targets for
connecting the input history to a physical effect.

## Connected rotation proposal

The combined latch's downstream routine `0x1404f66f0` is the already documented
initial spin/flip proposal, acceptance and feedback path. See
[body proposal guide](../systems/body/CLIENT_GUIDE.txt),
[rotation stages](../systems/tricks/rotation/CLIENT_GUIDE.txt) and
[motion lifecycle](../systems/tricks/motion-lifecycle/CLIENT_GUIDE.txt).
The equations were previously explained there. This follow-up supplies the
concrete ingestion/state-entry/latch connections and original-instruction
validation; it should not be counted as discovering those formulas again.

The independent engine now exposes
[`initial_rotation_proposal`](../../engine/motion_rotation_proposal.py), with
float32 operation order checked against 120 original prefix executions.
The scalar square-root service was supplied; SIMD operations and branches ran
as original instructions. The [receipt](../../native/snow_host/rotation_proposal_validation.json)
records exact XYZ output bits for disabled/enabled latches, selected limits
110/360/450, zero, single-axis, mixed-axis, signed and deadzone-boundary inputs.
Those limit values are test inputs, not new evidence of live profile selection.

```text
x, y = primary input if first_latch else (0, 0)
z = secondary Y if second_latch else 0
if abs(y) < float32(0.3): y = 0
if abs(z) < float32(0.4): z = 0
q = (z, float32(1.414)*y, -float32(1.414)*x)
if norm(q) <= float32(0.01): scale = 0
else:
    scale = max(sqrt(x*x+y*y), abs(z)) * limit * float32(pi) / 180 / norm(q)
proposal = q * scale
```

The implementation preserves individual float32 operations rather than simply
using the algebraically equivalent normalized-vector expression. There is no
clamp on input magnitude in this prefix. Equipment remapping, stance inversion,
proposal acceptance, mixed-axis boost and later magnitude feedback are outside
this API and validation; calling it the final spin rate would be incorrect.
Its returned vector is local radians per supplied time unit, not torque or a
verified physical-body write. Nonfinite API inputs are rejected as an explicit
inspection policy; native nonfinite behavior is not claimed by that policy.

A composition test connects the latch API to this proposal. With the gates held
clear, count four and squared-distance threshold .15, primary X .3 does not
activate a proposal, while .4 does. This is a synthetic exercise of the two
reconstructed local blocks, not a live or same-substep game observation.

This connection explains why an apparent "input smoothing" issue can originate
from state-entry history, persistent latches, the proposal's separate deadzones,
or acceptance of the resulting direction. The scheduler investigation should
record those stages separately. The next useful closure is their actual
same-request ordering and the existing target-publication/body-consumer gap,
rather than rederiving the documented proposal equations.

## Bounded native motion-state reader

[`snow_motion_observe`](../../native/snow_host/snow_motion_observation.h) now
provides the observation needed to correlate this research with existing snow
substep records. It is a standalone authored C reader, not an installed hook.
It accepts a caller-verified actor/table identity and an exact bounded memory
reader, checks the embedded motion object's actor backlink, and takes two
matching observations with at most 18 reads total.

Captured fields include current/pending top-level ownership, lock and query
nesting, enable/immediate/pending flags, the ingested input vectors, distinct
current-action vectors, both nonzero-input counters, all three latch bytes, and
the primary/smoothed/secondary baseline vectors. Input words retain their raw
bits, including NaN payloads and signed zero. It does not collapse the combined
latch byte into the OR of the two underlying flags.

For top-level mode zero it observes the current state's header. It follows that
state's current child only on the inspected mode 0/3/4 branches. It never follows
pending pointers or an unbounded state chain. A null current pointer produces
an observation with that deeper level marked unavailable. Wrong actor identity,
wrong backlink, failed reads, address overflow or changed captured values clear
the entire output and return failure.

The native fixture covers each of the 18 read failures, a changed counter across
samples, owner/table rejection, excluded branches with deliberately invalid
pointers, child-address overflow, distinct input counts, raw float-bit retention
and stale combined-latch preservation. The focused five-fixture C suite passed,
and MinGW compiled the reader with warnings treated as errors.

This reader does not claim an atomic snapshot or detect address reuse. Matching
lock/depth samples neither exclude another thread nor grant permission to mutate
the object. Observed modes do not prove allocation type outside the verified
actor route. Identical counters do not prove that ingestion did not run: a
zero-input update can leave a counter at zero. Two matching samples do not
establish action freshness, a producer generation or ingestion execution.

The next implementation step is an optional channel in the native capture
record, keeping motion-observation validity separate from job/substep validity.
Only after integrated fixtures should a bounded live capture correlate these
values against direct substep ordinals. The existing capture ABI and live probe
were not changed in this pass.

## Optional motion channel in the substep recorder

The authored recorder now supports `snow_trace_call_observed`: an optional
bounded motion callback before and after the original actor update, independently
of job attribution, direct frame attribution and body snapshots. Each side has
its own validity flag. A rejected callback clears only that side's motion output;
it cannot suppress the original call or discard valid job/frame evidence.
Closed and full recorders forward without invoking either optional observer.
Callbacks must return normally; this is not exception containment.

The native probe exposes `SnowProbe_ConfigureObserved` and uses the bounded
reader above. Configuration is immutable before publishing dispatch. Existing
configure functions leave motion capture disabled. The record layout is now
experimental ABI v5: rebuild consumers and DLL together; do not mix older
headers or DLLs. The capture plugin enables it with `[capture] observe_motion=1`.
The experiment launcher exposes the same option as `--observe-motion` for the
host `update-capture` plan. It remains off by default.

Local JSONL includes attempted/before-valid/after-valid flags, ownership and
mode observations, counters, all three latch bytes, and input/baseline words as
unsigned raw float32 bits. Invalid motion objects are omitted. These files
contain process pointers and stay private. At most 36 extra exact memory reads
are attempted per captured update, up to 18 on each side. Timing includes this
observer work and must not be interpreted as uninstrumented callback cost.

Validation uses authored native and Windows/Wine fixtures, not game execution.
The trace fixture tests all nine pairs of callback status 0/1/2, preserves valid
job/frame results on motion rejection, preserves valid motion when attribution
fails, and checks disabled/full/closed behavior and before/after order. The
Windows fixture opts into the real reader on synthetic objects and invalidates
the actor backlink during original dispatch to check after-only rejection.

Live correlation remains pending. A matching before/after record cannot identify
an ingestion call, prove atomicity, resolve address reuse, or establish the
producer's generation. The next experiment should compare these observations
within directly attributed request/substep sequences, retaining invalid samples
and measuring observer overhead rather than inferring missing events.

### Aggregate comparison of motion observations

`scripts/analyze_update_capture.py` includes the optional motion channel via
`scripts/analyze_motion_capture.py`. It reports field-change counts without
publishing pointer identities, raw input vectors or baseline payloads. Validation
rejects malformed flags, word widths, vector lengths and pointer encodings.
Rejected or missing observations break adjacent comparisons.

Three comparisons remain distinct: before-to-after within an update;
after-to-before between consecutively numbered substeps in an observed batch;
and after-to-before across a changed outer completion counter. The latter is an
observed boundary, not proof that exactly one frame elapsed. Neighbor comparisons
require one actor and motion address, valid frame/job flags, ordered nonoverlapping
wrapper intervals and valid ordinal/count bounds. Address equality cannot detect
object reuse. Equal raw bits cannot prove that a writer did not run.

Synthetic tests cover raw signed-zero differences, within/gap/boundary separation,
rejected samples, malformed arrays and flags, missing channels, overlap, changed
actors and skipped ordinals. This analyzer does not promote a comparison into
input-ingestion ordering or atomic-state evidence.

### Live motion-to-substep correlation

The [aggregate live receipt](../../native/snow_host/motion_substep_live_observation.json)
records 226 motion-valid, job-valid and direct-frame-valid updates. No records
were dropped. All 207 observed outer groups had complete ordinal sequences:
188 records belonged to one-substep batches and 38 to two-substep batches.
Hook restoration, recorder drain, launch-setting restoration, bottle shutdown
and original DLL hash verification passed.

No sampled motion field changed inside any of the 226 actor-update wrappers.
No sampled motion field changed across the 19 consecutive-substep gaps within
an observed batch. Across all 206 observed outer-counter boundaries, only
baseline word index 5 changed: the Y component of the smoothed four-vector.
Ingested/current input words and both nonzero counters were zero in the sampled
records; the observed mode tuple was top-level 0, state 3, child 1. No steering
input was applied during this capture.

The smoothed vector's decay matched `refresh_input_baselines` bit-for-bit on
all 206 boundary comparisons using candidate float32 alpha 0.1 and the sampled
zero current vector. This is a hypothesis check using the existing recovered
formula. Alpha was not read from the live profile, and matching the decay does
not uniquely identify a coefficient, writer or call count. No raw input or
baseline vectors are published in the receipt.

This gives a concrete cadence lead: in this idle observation, the smoothed
baseline changed between observed batches and stayed stable through the
sampled substeps. It does not establish input-ingestion execution or timing.
Next: capture the live profile coefficient and correlate a controlled nonzero
input, checking whether changes appear before the first substep and whether
the same baseline formula still predicts the observed values.

### Observed profile coefficient channel

Experimental ABI v6 adds an independently valid profile observation. The
inspected smoothing block resolves motion `+0x50` to a handle, uses the sign
bit of its 32-bit status at `+0x0c` to retain or mask its object pointer, and
reads alpha from the resulting profile `+0x64`. The reader follows that exact
sign gate and retains the raw coefficient bits without clamping or fitting.

Two motion samples must still match. Profile reads may fail independently:
a null/unsigned-status handle, inaccessible profile, overflow, changed handle,
changed profile pointer or changed alpha clears only profile fields. Matching
profile observations do not prove lifetime or exclude ABA reuse. The expanded
reader attempts at most 24 exact memory reads per observation, or 48 per captured
update. Rebuild DLL and consumers together for the new record layout.

The analyzer now separately tests the existing `refresh_input_baselines`
four-vector formula with the observed alpha on qualified outer-boundary pairs.
It requires matching profile identities and alpha across the gap. It reports
nonfinite/unrepresentable inputs separately and never exports the pointers or
raw vectors. The next-before current vector is only a sampled input: it is not
proved to equal the input at the writer's execution time. A formula match still
does not establish writer identity or call count.

Validation: 32 focused native/analysis tests, six synthetic Windows/Wine probe
cases, and the capture-plugin build passed. The failure matrix covers each read,
the status sign gate, pointer overflow, coefficient instability, and independent
profile rejection. The Windows motion fixture verifies the actual reader returns
the synthetic coefficient bits. The previous ABI-v5 live trace remains readable
and is correctly treated as lacking a profile coefficient. No ABI-v6 game
capture has run yet; controlled nonzero input remains the next live experiment.

### Controlled input during capture

The configured-workspace launcher accepts `--capture-steering` together with
`--observe-motion` on the host `update-capture` plan. This selects a five-second
capture and invokes the existing guarded OS-input helper after resume, requesting
scan 30 for 700 ms. Scan 30 is the physical A key; semantic steering response
must be established from observations rather than the name of this option.

The helper checks process creation identity and the exact game window, requires
foreground focus, refuses an already-held key, and releases attempted keys in
its cleanup block. Its private JSONL records QPC timestamps for key delivery.
The controller requires successful helper exit, two accepted OS deliveries and
confirmed release. This does not prove game acceptance or exact ingestion time.
No direct game-action injection is introduced. The optional callback is absent
for the original observation-only path; tests verify execution after resume and
that a failed delivery report makes the capture result fail.

### Live nonzero input and observed coefficient

The [steering capture receipt](../../native/snow_host/steering_motion_live_observation.json)
contains 580 valid motion/profile/direct-frame observations across 431 complete
observed batches. The input helper reported accepted scan-30 key-down and key-up
and confirmed release after its requested 700 ms hold. Lifecycle, hook restore,
drain, launch-setting restoration, bottle shutdown and original DLL hash checks
passed. No records were dropped.

Both sampled input-vector transitions appeared at ordinal zero of a new batch.
No sampled motion fields changed inside any wrapper or across the 149 qualified
consecutive-substep gaps. Across 430 outer-counter boundaries, inputs changed
twice; the primary nonzero-input counter advanced by one 56 times, reset by 56
once, and stayed unchanged on the other 373 boundaries. This is consistent with
the recovered counter update/reset rule, but is not an observed ingestion call
count. The second counter remained zero.

The live profile alpha bits were `0x3dcccccd`, float32 0.1, in all 580 records.
Using that observed value, the existing baseline-smoothing function predicted
all 430 four-vector transitions bit-for-bit, including the nonzero interval.
This supersedes the earlier coefficient fit for this session only. Current
input at writer execution time was not observed directly.

The numeric state tuple changed among `(0,3,1)`, `(0,4,6)` and `(0,3,7)`, with
521, 35 and 24 observations respectively. This ties the state hierarchy to a
live input experiment; it does not assign semantic animation/trick names to
those states or prove input alone caused each transition.

QPC frequencies agreed between the helper and recorder. Relative to the helper's
post-delivery reports, the last unchanged update exited about 7.71 ms after
key-down and 15.80 ms after key-up; the first changed update entered about
22.35 ms and 29.52 ms after those reports. These bracket observations, not exact
latency: the helper reports after its OS call, and the motion reads occur inside
wrapper intervals rather than at their endpoint timestamps.

Next: connect the observed mode transitions and counter edges to the previously
inspected BeforeSimulation motion-update route. A function-entry observation or
producer-generation marker would distinguish actual ingestion execution from
matching field changes. Do not infer per-substep ingestion from the counter.

## Ingestion read sequence and both smoothing writers

`engine/motion_input_ingestion.py` implements the inspected ingestion prefix,
validated against original instructions in
[96 emulated cases](../../native/snow_host/motion_ingestion_validation.json).
This reconstructs local behavior, not scheduling or device polling. The prefix
runs from ingestion entry through its second smoothing store, before the helper
and actor-edge tail.

Its ordered operations are:

```python
first_id = 0xd9 if alternate_enabled and actor_predicate() else 0x76
primary = read_action(first_id)        # independent lookup and vector read
primary.x_bits ^= sign_mask_if_flipped
primary_count = increment_u32(primary_count) if nonzero_or_nan(primary.xy) else 0
secondary = read_action(0x77)
secondary.x_bits ^= sign_mask_if_flipped
secondary_count = increment_u32(secondary_count) if nonzero_or_nan(secondary.xy) else 0
current_primary = read_action(0x76)    # read again, not primary's cached value
current_primary.x_bits ^= sign_mask_if_flipped
smoothed_primary = f32(f32((1-alpha)*smoothed_primary) + f32(alpha*current_primary))
current_secondary = read_action(0x77)  # another independent read
current_secondary.x_bits ^= sign_mask_if_flipped
reset_byte = 0
smoothed_secondary = f32(f32((1-alpha)*smoothed_secondary) + f32(alpha*current_secondary))
```

The predicate is called only when the alternate gate is enabled. Both signed
zeros count as zero; unordered NaN comparisons increment the counter. The X
operation toggles its sign bit, retaining NaN payload bits and flipping signed
zero. Counters wrap modulo 2^32. All four lanes participate in smoothing with
float32 multiplication/addition order and no alpha clamp. The reference API
requires four separately supplied payloads so callers cannot accidentally treat
these reads as one atomic input snapshot.

Build anchors: ingestion `0x140541da0` through `0x140541ff7`; global alternate
gate read at `0x140541daa`; actor predicate slot `0x460`; actor sign byte `+0x1b6`;
primary/secondary payloads `motion+0x160/+0x170`; current payloads
`+0x360/+0x370`; counters `+0x384/+0x388`; smoothed vectors `+0x6f0/+0x710`;
reset byte `+0x465`; alpha via the signed profile handle and profile `+0x64`.
The existing recorder includes primary smoothing but not secondary `+0x710`.

The vector-view routine `0x14062ca40` is simply `return object+0x40`; the emulation
executes that original body. The action lookup is substituted with deliberately
distinct payloads, and the actor predicate is synthetic. Cases cover all
alternate/predicate/sign combinations, alpha 0/0.1/1/1.5, zero/nonzero/NaN
counter inputs and wrap. Smoothing test inputs are finite. The tail helper at
`0x1404ed2e0` and actor predicate-edge bookkeeping are excluded.

This supplies a second concrete writer for the live smoothing result. The
previous baseline-refresh slice `0x140532e3a` writes the same primary smoothed
vector with the same formula, while also copying baseline vectors. A match to
that formula does not distinguish its invocation from ingestion. Ingestion's
four lookups, paired counter updates, second smoothing writer and tail give a
more specific event sequence for the next observation.

A further static lead: the action-lookup wrapper `0x14046f140` forwards the
service's selected index at `+0x50` into `0x14046f150`. That function acquires a
reader count, selects a bank from its pointer array, calls lookup `0x1404748a0`,
returns the found record plus `0x20` or a fallback object, and releases the reader
count before the caller obtains its vector view. Full writer/publication and
lifetime semantics remain open. Do not treat the returned address as a retained
lock or proof of immutable contents.

## Action-bank search precedence

`engine/action_bank_lookup.py` now exposes the inspected local selection policy.
The [validation receipt](../../native/snow_host/action_bank_validation.json)
records 98 original-instruction cases with only the map-lookup body substituted.
This is selection, not a new publication/freshness result.

The action bank has three group headers at `+0x90`, `+0x9c`, and `+0xa8`, each
12 bytes. Each header contains an array pointer and uint16 count at `+0x0a`.
The lookup visits groups in that order and records from count minus one down to
zero. For each record it obtains a map through `record+0x28 -> +0x08`, looks up
the zero-extended uint32 action ID, and accepts a nonnull value from the returned
map node. Both an absent node and a node holding null are misses.

```python
for group in groups_in_stored_order:
    for record in reversed(group):
        node = lookup(record.map, uint32(action_id))
        if node is not None and node.value is not None:
            return node.value
        if record.optional_config is not None and record.optional_config.stop_byte != 0:
            return None       # aborts ALL remaining records and groups
return None
```

The optional config is `record+0x20`, with the stop byte at config `+0x2c`.
A hit takes precedence over that byte. The role name `stop_on_miss` is authored;
its runtime UI/context meaning remains unresolved. The containing manager
converts a null result into its fallback action object, so a fallback can mean
that a higher-priority miss suppressed otherwise available lower records. It
must not automatically be interpreted as a physical key-up or a fresh zero.

Validation used three groups with two records each, every hit location or no
hit, every stop location or no stop, and both miss representations. It compared
the returned value AND exact visitation order. Five independent tests also cover
empty groups and the uint16 group-count contract. No live active-bank binding,
map internals, lifetime, writer exclusion or publication generation is claimed.

The manager reader-count guard surrounds selection but is released before
returning the action object. The vector-view body then returns object `+0x40`.
Therefore that guard alone is not a retained vector snapshot guarantee. The
next useful join is the selected live bank/context plus the writer that updates
the action object's vector, or a direct ingestion event that can distinguish the
four action reads in one call. Search precedence should be retained in either
instrumentation plan rather than sampling an arbitrary matching action record.

## Copy getter and ingestion view join

The unresolved getter named in the older
[action-ownership evidence](../systems/input/action-ownership/evidence.md) is
now inspected and emulated. `0x14046f200(manager, output, action_id)` performs:

```python
object = manager_lookup(manager, manager.selected_index, action_id)
output.bits16 = object.vector_bits16
return output
```

It passes the unchanged manager receiver and action ID into `0x14046f150`,
using manager `+0x50` as the selected index. It reads exactly 16 bytes at returned
object `+0x40` and writes them to caller output. The manager lookup returns a
selected action pointer plus `0x20`, or the fallback object. Thus a selected
record supplies bytes at action `+0x60`. Motion's `0x14046f140` followed by view
`0x14062ca40` reaches the identical bytes; the view just returns object `+0x40`.
This is a copy getter versus a borrowed-address accessor, not two vector types.

The motion ingestion global load resolves to `0x14312bb00`, the same global
published by the previously inspected manager constructor. That constructor
passes its manager receiver to the callable binder. This closes the static
initializer/receiver join to motion's manager lookup. It does not establish
current live identity after further setup or possible rebinding.

[48 original-instruction cases](../../native/snow_host/action_getter_join_validation.json)
execute both paths with ordinary and owner-thread reader admission, valid and
out-of-range selected indices, hit and fallback results, two initial reader
counts, and three byte patterns including signed zero and a NaN payload. The
bank lookup and thread-ID service are substituted; actual manager admission,
release, copy getter and vector-view instructions execute. Both paths preserve
the input bits and restore the reader count. A subsequent synthetic source
mutation leaves the completed copy unchanged while changing borrowed storage.
No concurrent writer is simulated.

Crucially, the manager lookup releases its reader count before either vector
access. A copied output is detached after copying, but this does not prove an
atomic source read, lifetime retention or freshness. The action callback writer
family is already connected in [the reset-callback study](ACTION_RESET_CALLBACK.md).
What remains is the live selected action's concrete subtype and the ordering of
its refresh/publication relative to the four ingestion reads and physics batch.
The old getter-target ambiguity is closed; those runtime questions remain open.

## Tagged action-map observation

The map lookup has distinct root encodings. Root zero returns missing. Low tag
bits 1 select a compact sorted-key representation; tag 3 selects a larger
radix-tree decoder. Other nonzero tags take an error path in the inspected
routine. The authored observer reports unsupported encodings explicitly instead
of silently returning missing.

`engine/action_map_observation.py` implements the inspected compact-root case
for populations 1 through 31. The root pointer is masked with `~7`. The first
qword is population minus one, followed by unsigned 64-bit sorted keys. The
value area begins at the first supported qword tier large enough for header and
keys: 2, 3, 4, 6, 8, 12, 16, 24 or 32 for this inspected population range.
The matched key index selects the corresponding qword value slot. The function
returns that slot, not its stored action pointer; a found slot containing zero
is distinct from a missing key until the enclosing bank traversal interprets it.

[589 original-instruction comparisons](../../native/snow_host/compact_action_map_validation.json)
cover every supported population, every present key, keys below/above the range,
and gaps. The original routine's compact-root instructions execute unchanged;
its value-area lookup bytes are used privately to construct the fixtures. The
independent reader's alignment-tier formula produces the exact returned slots.
Four public tests cover the supported sizes, six read-failure positions,
changed values between samples, sorted-key rejection and present-null values.

The reader performs at most six exact reads totaling 528 bytes and requires two
matching observations of the header, keys and selected value. It rejects short
reads, overflow and corrupt ordering. Unsupported large populations and radix
roots remain explicitly unsupported. Matching copies do not establish lifetime,
atomicity, address-reuse detection or freshness. No game calls, locks, mutations
or live attachment are used by this reader.

Build anchors: root dispatch `0x14109a650`, compact branch `0x14109ad93` through
`0x14109ae01`, and private compact value-area table at image RVA `0x28dc9e9`.
Radix dispatch starts at `0x14109a669`; it has several internal node encodings.
Completing those node forms, or observing the actual selected live map encoding,
is necessary before claiming that the complete live action bank is readable.

### Radix branch formats and single-entry leaves

`observe_action_map` extends the compact observer with the inspected tag-3 root
and three branch families. The [252-case original-instruction comparison](../../native/snow_host/action_map_radix_branch_validation.json)
checks 84 cases per family across levels and digit positions including bitmap
word boundaries and high-byte selection. Original lookup and terminal-node code
execute without substituted helpers. The fixtures are single-branch trees;
deep mixed-format trees remain a separate validation target.

A tag-3 root begins its first 16-byte node at masked root plus eight. Node byte
15 identifies its format. Branches select a byte of the unsigned key. At the
lower levels they first compare the stored compressed prefix in bits above the
selected byte through bit 55. The tag occupies the top byte and is excluded.
Pointer tag bits are cleared before following branch storage.

- Tags `0x0f..0x15`: short linear digit list, selecting key bytes 1 through 7.
  Storage begins with count and up to seven digit bytes; 16-byte child nodes
  begin at storage plus eight. The matching digit's index selects the child.
- Tags `0x16..0x1c`: bitmap-ranked children for the same byte levels. Digit
  divided by 32 selects one of eight 16-byte headers. Its 32-bit bitmap tests
  presence. The popcount of bits below the selected bit indexes packed children
  through the header's tagged pointer at plus eight.
- Tags `0x1d..0x22`: dense tables indexed directly by key bytes 1 through 6.
  Root-only tag `0x23` selects byte 7. Each child occupies 16 bytes.
- Tags `0x08..0x0e` are empty terminals. Tags `0x2c..0x32` compare the low 56
  key bits and return the node's first qword as the value slot on a match.

These are functional format descriptions, not recovered class names. Missing
prefix/digit/leaf matches return `missing`; a present null value remains `found`
with action zero. Other leaves report `unsupported`. Corrupt linear counts,
repeated node addresses, null child storage, overflow and failed reads are
rejected. A depth or budget limit reports `limit`, not missing.

Radix traversal is capped at 16 nodes per pass, 128 total exact reads and 8192
bytes. Both traversal receipts, including addresses and bytes read, must match.
This observes only the selected path; it does not detect changes in unvisited
branches, ABA reuse or guarantee atomicity/lifetime. Tests additionally cover
prefix rejection before dereference, unstable values, cycles and depth limits.

Packed-array and bitmap leaves still require decoding. Until those and deep
mixed traversal are validated, the observer is an explicitly partial inspection
API and must not be used to declare an arbitrary live action absent.

### Reuse of existing packed-leaf reconstruction

The broader registry work already decoded the same lookup routine's packed and
bitmap leaves. Its [branch and leaf study](CENTRAL_IMPULSE.md#radix-packed-and-bitmap-leaves)
and `reference/registry_snapshot.py` are now reused by the action observer,
superseding the unsupported-leaf boundary above. The earlier work was missed
during the first action-specific branch pass; these leaf formulas are reused
findings, not new discoveries.

The shared decoder gains optional `resolve_slot(raw_value, slot_address)` identity
mapping. Existing callers retain their original `resolve_value(raw_value)`
behavior. This allows the action observer to carry the selected physical slot
through the existing logical lookup without confusing duplicate stored values
with slot identity. The observer then reads the selected action pointer from
that slot. A null pointer remains a found value, not a missing map entry.

The selected-path reader delegates one encountered leaf to the existing bounded
snapshot decoder. That decoder handles 1..7-byte packed arrays, inline 1/2/3-byte
keys and four 64-bit bitmap groups. Existing duplicate-key scan order and
layout tables remain authoritative. Leaf snapshots include their inspected
keys and value arrays; branch traversal still follows only the selected path.
Both full traversal receipts must match. The existing 16-node, 128-read and
8192-byte limits remain enforced by the outer reader.

The [new adapter receipt](../../native/snow_host/action_map_all_leaves_validation.json)
re-executes all 3,501 existing original-instruction leaf fixtures and compares
exact native slot addresses, as well as values, against this observer. It
includes 253 top-byte branch-to-leaf joins and every inspected multi-value leaf
kind. The original fixture generator is reused unchanged; original receipts
are preserved. Public integration tests exercise dense-to-bitmap-to-inline
paths, seven-byte array layout boundaries, bitmap leaves and slot mapping.
All 49 focused action-map/registry tests passed.

All previously inspected compact and radix lookup encodings are represented.
Unknown encodings, corrupt data and budget exhaustion remain explicit failures;
this is not a claim of arbitrary map compatibility or stable live access. The
next task is bounded live manager/bank ownership and action identity sampling,
using the decoded search precedence. No live action selection or publication
ordering was established by this integration pass.

### Manager-to-action observer

`engine/action_binding_observation.py` connects the selected manager bank, reverse
binding precedence and bounded action-map decoder into one read-only operation.
`observe_action_binding(read, manager, action_id, fallback)` returns the selected
bank, binding, physical value slot, action, virtual table, third virtual callback
and the 16 raw bytes at action+0x60. The callback is an observed identity only;
this reader does not establish a callable signature or invoke it.

The caller supplies verified build-specific manager and fallback identities and
a callback that returns exactly the requested bytes. The reader rejects observed
writer bits in the manager lock word without acquiring a lock. It follows the
selected bank and checks three binding groups in reverse record order. A missing
or null action continues unless that binding's stop-on-miss flag is set. An
out-of-range bank index, exhausted search or stop-on-miss returns the fallback's
16 bytes at +0x40 with a distinct reason. Unsupported maps, failed reads, changing
receipts and exhausted budgets never become ordinary missing-action results.

Two complete traversal receipts must match, including read addresses and bytes.
Limits are 512 reads and 32768 bytes total, 64 records per group and 128 visited
records per pass. Matching receipts do not prove atomicity, object lifetime or
absence of ABA reuse. The reader neither calls the game nor writes memory.

The [integrated validation receipt](../../native/snow_host/action_binding_validation.json)
records 98 comparisons against the original manager, bank and compact-map
instructions. Only the thread-ID provider was substituted. Fixtures cover each
of six binding positions, null and missing values, stop flags and fallback
selection. The original reader-admission path executes and releases its reader
count. Instances are synthetic; radix encodings are validated separately by the
map studies above. Public tests cover selected sample and callback identity,
precedence, writer refusal, unsupported maps, failure at each read and changing
payloads between passes.

Next: use a fresh live manager identity to observe concrete action types and
samples alongside motion ingestion. These offline results do not establish live
ownership, reset ordering or the ingestion job's position among substeps.

### Fresh manager root observation

`engine/action_root_observation.py` adds `observe_rooted_action` for transports
that already verify process and build identity. It accepts the manager global's
address, reads the current manager pointer, runs the bounded binding observer,
then rechecks the global. A changed root discards all candidate addresses and
sample bytes. An unpublished null manager reports `unavailable`; failed root
reads report `invalid`. This adds at most two eight-byte reads to the binding
observer's budget. It does not pin lifetime or detect an ABA replacement.

The private workspace collector now connects this operation to the existing
persistent read-only helper. That helper checks PID, executable basename and
creation time on each request, with 224 requests and a 40-second deadline. The
collector also compares selected manager/bank/map routine signatures against
the analyzed image before and after sampling. These selected checks are not a
whole-image equivalence proof. It reads one requested action, defaults to 0x76,
and sends neither input nor game calls. Raw observations remain private.

Public fixtures cover a fresh root on each invocation, root replacement after a
valid action read, an unpublished manager and a short final root read. The
private command's argument handling was checked without accessing a process.
No live result is claimed for this collector yet. Its first live run should use
a freshly identified gameplay process and record both success and refusal
outcomes before attempting time-series sampling.

### Live selected action is composite

The first bounded `action-observe` run succeeded in gameplay after startup host
loading. Action 0x76 resolved from selected bank index zero to a nonnull action,
with two matching traversal receipts and an unchanged manager global. The
selected sample was sixteen zero bytes. There were 38 persistent-helper
requests taking about 1.30 seconds in total. The game remained in ordinary
simulation for the subsequent 20-second check; cleanup restored settings,
stopped the owned bottle and verified the original input DLL. See the
[public receipt](../../native/snow_host/action_identity_live_observation.json).

The observed virtual table is image RVA 0x1e6b6f0 and its third callback is RVA
0x4b24c0. The analyzed implementation at that callback is a composite action
selector. It is not the directly evaluated two-axis callback at RVA 0x4b2680.
The runtime callback bytes themselves were not compared in this capture; the
classification joins the observed callback address to the analyzed image.
This does not yet identify any live child as a keyboard or controller source.

For a nonnull configuration at action+0xb0, the analyzed callback reads the
child pointer array at +0xb8 and its unsigned 16-bit count at +0xc2. It calls
each visited child's third virtual method before checking child status +0x30.
For non-final children, configuration+0x28 points to records whose +0x10
integer controls selection. The following pseudocode preserves the branches:

```text
result_status = 0
for i in range(child_count):
    child[i].callback_slot_2()
    status = child[i].status_byte
    if i == child_count - 1:
        copy_sample_fields(child[i], parent)
        result_status = status
        continue
    mode = configuration.records[i].mode
    if mode == 1 and status == 0:
        break
    if mode == 0 and status != 0:
        copy_sample_fields(child[i], parent)
        result_status = 1
        break
parent.status_byte = result_status
```

`copy_sample_fields` copies the three 16-byte fields at +0x50, +0x60 and +0x70,
and the four bytes at +0x80. These match the previously inspected raw/sample/
direction/magnitude layout. It also briefly copies the child status before
the final status assignment. Unknown mode values continue to the next child.
A mode-1 failure exits without copying these fields; zero children also leaves
them untouched while clearing status. Thus a false status does not by itself
prove that this callback zeroed its sampled vector. A preceding reset may have
cleared it, but that execution order was not observed here.

The null-configuration path invokes a separate allocation/diagnostic route and
is not represented by this pseudocode. This branch analysis has not yet had
original-instruction fixture validation. Next: validate the composite selector,
then read its live child identities and mode records with the same root and
traversal guards. Timing attribution must follow the selected producer rather
than assuming that action 0x76 itself computes directional input.

### Composite selector validation

`engine/composite_action.py` implements the configured composite callback as
`evaluate_composite(child_count, update_child, mode_at, previous_payload)`.
The child evaluator returns status and 52 uninterpreted bytes covering the
three vector fields and magnitude. It is called lazily, only for children the
original loop visits. Mode lookup occurs after that child's evaluation, and
never for the final child. The result includes the selected child index and
exact visited order, without inferring device labels or input generations.

[Original-instruction comparison](../../native/snow_host/composite_action_validation.json)
now validates 1,393 configured cases. It executes the complete callback and
substitutes only child virtual calls with supplied status/payload outcomes.
Cases exhaust lengths zero through three across status bytes 0, 1, 2 and 255
and modes 0, 1, 2 and 0xffffffff. Another 300 seeded cases exercise lengths four
through sixteen. Comparisons check the entire parent object and the exact
child-call sequence, not only the selected vector.

All cases passed: 186 retained the previous payload, 539 selected an early
child and 668 copied the final child. The fixture includes status/payload
inconsistency deliberately: status zero is not evidence that vector bytes are
zero. Early mode-zero selection normalizes a nonzero child status to one;
final-child selection preserves the complete status byte. Public tests also
check that skipped child evaluations and final-child mode reads do not occur.

This supersedes the unvalidated-branch boundary above for the configured local
selector. Null configuration remains excluded. The child producer behavior,
mutation of parent/configuration during a child call, and ordering relative to
reset or motion ingestion are not reconstructed by these fixtures. The caller
must supply those dependencies explicitly. Next is bounded live enumeration
of the selected composite's child identities and mode records.

### Composite child observation

`engine/composite_action_observation.py` enumerates a verified composite
parent's child pointers, virtual tables, third callbacks, status bytes and
52-byte sample payloads. Non-final children include their configured selection
mode; the final child has no mode read, matching callback control flow. It
checks the supplied parent table and callback identities before following the
composite layout. Null configuration, unsupported type, invalid reads, size
limits and changing receipts have distinct outcomes.

Two complete read receipts must match. Enumeration is capped at sixteen
children, 136 exact reads and 5600 bytes across both passes. These are fixed
structural bounds, tested with the maximum child count. It invokes no callback
and makes no selection claim from sampled status values. Enumeration includes
children the actual callback may skip. Neither equal receipts nor a matching
parent identity pins object lifetime or rules out ABA reuse.

The private `composite-observe` launch plan brackets child enumeration with two
complete rooted action lookups and requires their observations to match. It
also checks the composite callback's analyzed instruction bytes and compares
each observed child's first 32 callback bytes with the analyzed image. These
checks support local identity; they are not full child-code equivalence or
proof that a child executed in the observed frame. Raw records remain private.

Public fixtures cover final-child mode omission, all read failures, changed
mode data, null children, unsupported parent callbacks and count limits.

### Live composite has vector-source and directional children

The first `composite-observe` run passed in gameplay. Action 0x76 had exactly
two children. Both complete child receipts matched and a fresh rooted action
lookup after enumeration equaled the one before it. The composite callback's
configured and null-configuration instruction range matched the analyzed image;
each child's first 32 callback bytes also matched. The capture made 96 read
requests in about 1.37 seconds. Ordinary simulation continued for 20 seconds,
then settings restoration, bottle shutdown and original-DLL verification passed.
See the [live receipt](../../native/snow_host/composite_children_live_observation.json).

| Child | Table RVA | Callback RVA | Selection | Static behavior |
| --- | --- | --- | --- | --- |
| 0 | 0x1e6b650 | 0x4b21d0 | Mode 0: accept immediately when status is nonzero | Obtains a vector through helper 0x4b8ca0, applies configured lane selection, then processing and sample publication |
| 1 | 0x1e6b740 | 0x4b2680 | Final child: copy regardless of status if reached | Previously reconstructed two-axis directional combination and processing |

Both child statuses and all inspected sample bytes were zero. This supports
the inactive configuration's identities, not an observed execution sequence or
proof of which child last published the parent. The first callback's vector
source has not yet been identified as a particular controller, device or axis.
Likewise the directional callback's source queries need live configuration to
map them to physical keys. The selector can skip the directional child entirely
when the vector-source child is active.

Static inspection of the first callback shows that its configuration+0x30
unsigned value gates an axis-selection branch: for values at most one,
configuration+0x34 equal to one clears Y, and equal to two moves Y into X and
clears Y. Other values retain the source vector. It then runs the same style of
optional processor and magnitude/direction publication as the directional
family. This is a new static lead, not yet an original-instruction-validated
reconstruction of the source helper or processor binding.

Next: decode the vector source helper, recover the two children's live source
configuration and processor identities, and then capture their publication
relative to motion ingestion. The relevant callbacks and child ownership are
now concrete; device mapping and scheduler ordering remain open.

### Vector-source ownership and masking

`engine/vector_action_source.py` reconstructs the first child's source selection,
ownership predicate, cache suppression and lane selection with raw bytes. It
does not identify physical devices or implement the writers of these caches.
The child configuration's unsigned kind at +0x30 selects:

| Kind | Ownership family | Cached channel | Output before lane selection |
| --- | --- | --- | --- |
| 0 | vector | 0 | Four cached lanes |
| 1 | vector | 1 | Four cached lanes |
| 2 | scalar | 10 | Cached scalar in X; Y/Z/W zero |
| 3 | scalar | 12 | Cached scalar in X; Y/Z/W zero |
| Other | none | none | All zero |

The caller passes the child+0x10 source owner to the ownership predicate. Its
+8 unsigned index combines with the selected channel to locate seven priority
slots. Starting at the highest slot and walking downward, the first nonnull
owner blocks the read if it differs from the caller. All-null or first-self
permits it; lower-priority entries are then irrelevant. Relative to the shared
table pointer, the highest-slot address is:

```text
vector: table + 0xf050 + 0xe8 * (owner.index + 8 * channel)
scalar: table + 0x0850 + 0xe8 * (owner.index + 8 * channel)
for slot in [highest, highest-8, ..., highest-48]:
    if slot.value != 0:
        blocked = slot.value != owner
        return blocked
return false
```

If permitted, each getter follows the pointer at owner+0 to its cache object.
It enters the lock at cache+0x2e8 and inspects the unsigned 16-bit stack count at
+0x252. A nonempty stack uses the pointer array at +0x248. Only the last entry
matters: nonnull suppresses the result to positive zero; a null last entry
permits the cache read even if earlier entries are nonnull. The getter releases
the lock before copying the vector or scalar:

```text
blocked = stack.count != 0 and stack[stack.count - 1] != null
unlock()
if blocked: return zero
vector_value = cache.bytes[0x1f0 + 16 * channel : +16]
scalar_value = cache.bytes[0x168 + 4 * channel : +4]
```

The getter lock therefore does not itself prove an atomic cache-value read.
Its role in coordinating stack mutations and upstream writers remains open.
When kind is 0 or 1, lane mode +0x34 equal to one clears Y; equal to two moves
Y to X and clears Y. Z/W remain unchanged. Other lane modes retain all lanes.
Scalar kinds ignore lane mode. Unknown kinds skip ownership and cache calls.

The [original-instruction receipt](../../native/snow_host/vector_action_source_validation.json)
records 4,320 passing comparisons of the original callback prefix, source
helper, both ownership predicates and both cache getters. Only the lock/unlock
calls are substituted; the test also verifies gate/getter/lock call order.
Cases cover all supported kinds plus unknown values, every highest-nonnull
priority position with self and foreign owners, empty/null/nonnull mask tops,
lane modes and raw signed-zero/NaN/infinity payloads. Comparison stops before
processor invocation. This supersedes the unvalidated source-prefix boundary
above but leaves processor selection, device-cache production and live gate
state unresolved.

The next useful live read is the child source owner, source configuration and
processor identities, not simply its sampled vector. These distinguish neutral
input, ownership suppression and mask suppression before testing refresh timing.

### Source configuration observation

`engine/action_source_observation.py` reads the source configuration and
processor behind a known vector or directional child. It requires the caller
to supply verified family/table/callback identities. It returns processor table,
processing callback, resolved processor-configuration handle and whether the
configuration enables processing. An inactive signed handle resolves to null
and permits processing; an active nonnull configuration with byte +0x18 zero
bypasses it, matching the inspected caller branch.

Directional children expose their eight source-query IDs in field order. Vector
children expose kind, lane mode, source owner/index, cache identity, seven owner
priority entries, mask count/top and the selected cached bytes. A detached
`derived_source_bits` value applies the reconstructed gates and lane selection
to those observed bytes. It is not a recording of a callback's execution. Cache
bytes are read even when suppressed, to preserve that distinction.

The reader compares two receipts of the relevant fields and is capped at 64 reads/4096 bytes.
It invokes no engine routines or lock operations. Parent and child provenance
must be checked by the surrounding collector; equal receipts do not guarantee
atomicity or lifetime. Unknown vector kinds report unsupported for this
inspection operation even though the reconstructed selector returns zero.

The private `source-observe` plan extends child enumeration, observes the two
known source families, checks processor callback prefixes, re-enumerates the
composite and repeats the rooted parent lookup. Public tests cover ownership
suppression without destroying cached bytes, mask-top behavior, processor
bypass and inactive handles, directional ID ordering, read failures and changed
configuration. Raw observations remain in the private workspace.

### Live source configuration and handle correction

The first `source-observe` run was a partial result, not a passing experiment.
The directional child produced matching observations, but the vector child's
processor handle had changing bytes outside the pointer and sign bit used by
the original resolution branch. The original reader compared all sixteen
handle bytes and refused the observation. The game remained ordinary at final
status; cleanup restored settings, stopped the bottle and verified the original
DLL. The normal twenty-second stability stage did not run after the refusal.
See the [partial receipt](../../native/snow_host/action_sources_live_observation.json).

The reader now compares the handle's object pointer and only the sign bit of
its signed state word. It does not read the unrelated word at +8, and it does
not require the unused lower 31 bits of +0xc to remain constant. A pointer or
active-sign change still rejects the result. Synthetic tests explicitly cover
both tolerated irrelevant-bit changes and rejected active-sign changes. The
unused bits' wider lifecycle meaning is not inferred from this observation.

Offline replay of the two recorded live vector traversals passes this corrected
comparison. That is a reanalysis of captured reads, not a second live capture:

- Vector kind 0, channel 0, lane mode 0: retain all four source lanes.
- All seven priority owners were null; ownership did not suppress the sample.
- Mask count was zero; mask suppression did not apply.
- Cached sample bytes were all zero.
- Processor configuration resolved to null and processing was enabled.
- Its processing callback RVA is 0x490c60, the previously decoded pass-through
  method with the first-use byte. Its code bytes were not checked live here.

The directional child had query IDs `[65, 68, 87, 83, 65535, 65535, 65535, 65535]`
in configuration field order. They correspond to the primary negative-X,
positive-X, positive-Y and negative-Y queries, followed by their alternates.
The primary numbers match the familiar A/D/W/S virtual-key values, but this
capture did not trace physical key delivery; alternate-sentinel interpretation
and the downstream key-state lookup still need verification. Static inspection
of query wrapper RVA 0x9775c0 shows it obtains a global service and forwards
the ID to RVA 0x116b460; it does not use its incoming source-owner receiver.

Directional processing was enabled with a resolved configuration and callback
RVA 0x4906f0. Its prefix matched live. The analyzed body is an ordered processor
chain: it starts with the input vector, visits the pointer array at +0xd0 using
the count at +0xda, applies each child's own configuration bypass gate, then
passes that child's output to the next. Which child processors and parameters
this live chain contains remains open. The directional and vector actions
shared the same source-owner identity and index zero in this capture.

Next: rerun the corrected reader and enumerate the directional processor chain.
That will determine what shaping follows the reconstructed directional
combination before the composite publishes its result. Publication scheduling
and device-cache writers remain separate unresolved joins.

### Ordered processor-chain kernel

`engine/action_processor_chain.py` implements the chain observed behind the
directional child. `process_chain(raw16, configuration_flags, evaluate)` takes
explicit child configuration outcomes and a caller-supplied child evaluator.
False means a resolved configuration disables the child; true enables it;
None means no configuration resolved and the child is invoked. No unknown
child is silently replaced by a pass-through or default processor.

The inspected loop snapshots its unsigned 16-bit count and visits the pointer
array in increasing order. Its vector field updates are:

```text
parent.accumulator = input
for child in ordered_children:
    child.raw = parent.accumulator
    child.working = parent.accumulator
    config = resolve_using_handle_pointer_and_active_sign(child.handle)
    if config is null or config.processing_enabled_byte != 0:
        child.working = copy16(child.process(child.working))
    child.published = child.working
    parent.accumulator = child.working
return address_of(parent.accumulator)
```

The parent accumulator is +0x30; child raw/working/published are +0x50/+0x20/
+0x60. The child method is virtual slot +0x28. A bypassed child still overwrites
all three vector fields with the incoming value, but its processing callback
and callback-specific state updates do not run. An empty chain returns its
input unchanged. This is sequential composition, not averaging or selection.

The [original-instruction receipt](../../native/snow_host/action_processor_chain_validation.json)
records 2,343 passing cases. It executes the original chain loop with supplied
child callback results, covering lengths zero through four, active enabled and
disabled configurations, inactive handles with pointers, active null handles,
non-boolean enable bytes and raw NaN/signed-zero payloads. It compares the
parent output and returned address, exact child call order/arguments, and every
child's three vector fields. The cases contain 7,032 invoked stages and 1,758
bypassed stages. Child formulas and concurrent configuration mutation remain
outside this validation.

`engine/action_processor_chain_observation.py` prepares the corresponding
read-only inspection. It enumerates one level of up to eight stages, retaining
order and repeated child pointers. Each stage records its table, callback,
resolved configuration and enable flag. Two semantic receipts must match;
handle comparison uses only the pointer and active sign bit. Structural limits
are 104 reads and 728 bytes across both passes. A larger chain reports `limit`
instead of silently truncating. Unknown root type, null required links and
failed reads refuse observation. Nested chains are recorded as callback
identities, not traversed automatically.

Public tests cover noncommuting composition, bypass publication, unknown child
result rejection, empty chains, duplicate stage identities, bounds, faults at
each read and changed configuration. No game was launched for this pass. The
chain observer still needs integration with a freshly verified source and a
live capture; the actual directional chain's stage types remain unresolved.

### Live chain and diagonal correction

The `chain-observe` run passed. The corrected source reader accepted both
children live, with matching processor callback prefixes. The directional
source remained unchanged after its chain was read, and the enclosing
composite and rooted action lookups still matched. There were 212 helper
requests, below its 224-request cap. The subsequent twenty-second simulation
check and owned-session cleanup passed. See the
[live chain receipt](../../native/snow_host/action_chain_live_observation.json).

The directional processor contains two stages in this order, both enabled by
their observed configuration flags:

| Stage | Callback RVA | Inspected behavior |
| --- | --- | --- |
| 0 | 0x490220 | Conditional time-based per-axis transition/ramp and curve evaluation |
| 1 | 0x490d70 | Diagonal correction preserving dominant-axis magnitude |

The first stage also has an internal global activation gate. Enabled chain
configuration therefore does not establish that its shaping branch executed.
Its local state transition helper is RVA 0x4cf880; elapsed-clock conversion,
duration, axis selection and curve evaluation are the next reconstruction
targets. The live capture did not read those parameters or record execution.

The second stage is implemented in `engine/action_diagonal.py`. For finite
float32 input it first copies all four lanes, returning unchanged if all four
absolute values are at most float32(1e-5). Otherwise:

```text
x, y = input.xy
if abs(f32(abs(x) - abs(y))) <= float32(1e-5):
    scale = float32(0.7071067690849304)
else:
    large, small = (x, y) if abs(x) > abs(y) else (y, x)
    ratio = f32(f32(1 / large) * small)
    scale = f32(1 / f32(sqrt(f32(1 + f32(ratio * ratio)))))
output = [f32(x * scale), f32(y * scale), input.z, input.w]
```

Ignoring rounding and the near-equal shortcut, the output XY length equals
`max(abs(x), abs(y))`. This is not unconditional unit normalization. Full
diagonal input becomes approximately `[0.7071, 0.7071]`; partial input retains
its dominant-axis magnitude. Z/W are unchanged but participate in the initial
four-lane near-zero gate. Thus nonzero Z/W can cause small XY values to take
the correction branch.

The [diagonal validation receipt](../../native/snow_host/action_diagonal_validation.json)
records 1,412 exact output-byte and return-address matches against the entire
original leaf, with no substituted calls. Cases cover signs, axes, diagonals,
adjacent float32 values around the epsilon, Z/W gate effects and seeded finite
inputs. Nonfinite input is explicitly rejected by this portable adapter;
original SIMD NaN behavior is not claimed. The preceding time-shaped stage
and the live values entering this stage remain separate fidelity boundaries.

### Directional ramp timing and transitions

`engine/action_axis_ramp.py` implements the first observed chain stage in a
finite, positive-duration domain. It accepts explicit start/end clock readings,
configuration gates, per-axis state and a caller-supplied curve evaluator. It
does not manufacture the live duration or curve. The global input-manager
byte +0x91 can bypass this method's shaping after its initial input copy. A
failed configuration-availability gate also bypasses shaping. Both leave the
saved clock unchanged.

On the active path, duration comes from resolved configuration+0x28 and axis
mode from +0x2c. Each axis retains a current state, remembered direction and
timer in arrays at processor+0xec/+0x100/+0x114; count is the unsigned word at
+0xf6. Normal state values are negative=0, neutral=1 and positive=2:

```text
if abs(input) <= float32(1e-5):
    if current != neutral:
        remembered = current
        current = neutral
elif input > 0:
    if current != positive:
        current = positive
        if remembered == negative: timer = +0
        remembered = positive
else:
    if current != negative:
        current = negative
        if remembered == positive: timer = +0
        remembered = negative
```

For neutral state, the timer decreases by elapsed time and output sign uses
the remembered direction. Otherwise the timer increases and sign uses current
state. The result is clamped to `[0, duration]`, divided by duration and passed
to the supplied curve unless the absolute normalized phase is at most
float32(1e-5). That small-phase branch emits signed zero without a curve call.
Output sign is positive only for state 2. Consequently release can retain a
decaying directional output, while reversal starts a new ramp at zero. Input
magnitude beyond its sign/near-zero classification does not directly determine
the ramp output on this path.

Axis entry zero reads/writes X; all later entries read/write Y. Mode 2 skips
entry zero, and mode 1 skips entry one. The generic loop does not limit count
to two, so the reconstruction preserves that behavior without assuming a live
array size. Skipped entries keep their state and input lane unchanged. Z/W are
retained from the initial vector copy.

The clock accessor returns an object whose +0x1050 unsigned 64-bit field is
converted through a signed float32 conversion, with a float32 2^64 correction
for a set high bit, then divided by float32(1000). A missing object yields zero.
Elapsed time subtracts the saved float32 at processor+0xe8. After all axes, a
second accessor call supplies the new saved clock. These can differ within
one invocation. The physical unit and upstream clock producer remain open;
the divisor alone is not proof of seconds. The portable conversion rounds the
integer directly to float32 precision to avoid double-rounding uint64 values.

The [validation receipt](../../native/snow_host/action_axis_ramp_validation.json)
records 1,600 passing original-instruction comparisons of the entire callback
and transition helper. Clock access, external configuration gate helper and
curve evaluation are supplied; the curve fixture is quadratic and is not
claimed as the game's curve. Cases include release, reversal, unusual retained
states, skipped axes, zero through three entries, missing/backward/large clocks
and both bypass gates. Comparisons cover exact output, timer and saved-clock
bits; current/remembered states; curve inputs; and clock query order.

Next: identify the active curve object and duration, decode its evaluator and
verify the clock producer. Those dependencies are required before this kernel
can claim the original player's response timing. A narrow live parameter
collector should reuse fresh chain provenance and respect the existing helper
budget rather than append unbounded reads to the 212-request chain capture.

## Keyed ramp curve evaluation

The ramp dependency at RVA `0x1197fc0` is now independently implemented in
[`action_key_curve.py`](../../engine/action_key_curve.py). Its contract is a
caller-supplied, nondecreasing sequence of finite float32 keys, a query X,
optional input/output bounds, and an explicit cubic-root solver. It has no
persistent state or clock. X/Y units come from its caller; in the ramp caller
X is normalized timer/duration. No live curve keys have been captured.

The curve object holds a key pointer at +0x10, uint16 count at +0x1a, input
bounds at +0x1c/+0x20, output bounds at +0x24/+0x28, and enabling bytes at
+0x2c/+0x2d. Each 32-byte key contains point XY, incoming control XY, outgoing
control XY and a uint32 mode at +0x18. These are build-specific evidence
anchors, not portable object addresses.

Evaluation first clamps X when enabled. Empty curves return positive zero
without output clamping. Before/after the key range, it uses the endpoint Y.
Within the range, it selects the last key whose X is at most the query, so
exact duplicate positions select the last duplicate. The left key selects
interpolation: mode 1 is linear, mode 2 cubic, every other mode holds left Y.
Nonempty results receive the optional output clamp. Equal clamp operands
preserve the second SSE operand, including signed zero.

Linear evaluation returns left Y when abs(right.X-left.X) is strictly below
float32(1e-5); otherwise it computes `(X-left.X)/(right.X-left.X)` then scales
by the Y difference and adds left Y, rounding each operation to float32.

Cubic evaluation uses P0=left point, P1=left outgoing control, P2=right incoming
control, P3=right point. It forms ascending polynomial coefficients for
`BezierX(t)-X` and calls a root solver. If that returns one, two or three roots,
it selects the last returned root and clamps it to [0,1]; no roots gives t=0.
It evaluates BezierY at that t. Root ordering therefore affects output. The
implementation preserves the instruction-level float32 operation order in
both coefficient construction and Y evaluation. It does not silently insert
a generic numerical solver, a smoothstep curve or a sampled-curve evaluator.

The [offline receipt](../../native/snow_host/action_key_curve_validation.json)
records 2,100 passing original-instruction cases, comparing exact float32
results, polynomial coefficient bytes and solver call count. Of those, 1,846
execute without solver substitution; 254 supply synthetic ordered roots at
the polynomial solver boundary. Original key selection, linear arithmetic,
cubic coefficient formation, root selection/clamping and cubic Y arithmetic
execute in the emulator. Fixtures cover repeated positions, endpoint queries,
short linear intervals, unknown modes, clamps and zero through three roots.
No live process was used. The actual root algorithm at RVA `0x11822d0`, its
quadratic fallback, active curve contents and clock units remain unresolved.

## Ordered curve roots

[`action_curve_roots.py`](../../engine/action_curve_roots.py) reconstructs the
solver at RVA `0x11822d0` and quadratic fallback `0x1182500`. The interface
accepts coefficients `(d,c,b,a)` for `d+c*t+b*t²+a*t³`, returning roots in the
original output order. It has no state or clock. All arithmetic rounds after
each float32 operation; the quadratic tolerance comparisons use double
constants. Inputs and intermediate arithmetic must remain finite. Runtime
`sqrt`, `acos`, `cos` and `power` are explicit caller dependencies.

When a is exactly zero, the quadratic path sets `h=c/(2*b)` and
`D=h*h-d/b`. If b is also exactly zero, it returns `-d/c` for nonzero c,
otherwise no roots, including the all-zero polynomial. Quadratic behavior:

```text
D < -0.0001: return []
D < +0.0001: return [-h]
otherwise:  return [sqrt(D)-h, -sqrt(D)-h]
```

The interval is intentional recovered behavior, not a mathematical claim that
a slightly negative discriminant has a real root. The two-root output is
larger first, smaller last. Signed zero from negation is preserved.

For a nonzero cubic coefficient, normalize `B=b/a`, `C=c/a`, `D=d/a`.
The following is algebraic shorthand; use the implementation for exact
float32 ordering:

```text
Q = (B*B - 3*C)/9
R = (2*B*B*B - 9*B*C + 27*D)/54
delta = R*R - Q*Q*Q
if delta <= 0:
    theta = acos(clamp(R/sqrt(Q*Q*Q), -1, 1))
    scale = -2*sqrt(Q)
    return [scale*cos(theta/3)-B/3,
            scale*cos((theta+float32(2*pi))/3)-B/3,
            scale*cos((theta+float32(4*pi))/3)-B/3]
else:
    U = power(abs(R)+sqrt(delta), float32(1/3))
    sign = +1 if R < 0 else -1
    return [sign*(Q/U+U)-B/3]
```

Roots are not sorted or deduplicated. In particular, the cubic curve consumer
chooses the third result on the trigonometric path. The exponent is rounded
float32 one-third; replacing `power` with an exact cube-root operation would
change the implementation. Zero Q/R can cause a zero divisor in the original
trigonometric path. The portable kernel rejects this case explicitly rather
than inventing a triple-root repair. Original non-finite behavior remains an
open boundary.

To compose with the key evaluator, supply `solve_roots` using a partial of
`ordered_curve_roots` with the four runtime-math callbacks. Tests demonstrate
this with Python `math` callbacks, which are labeled portable fixtures. No
claim is made that these callbacks reproduce the original CRT bit-for-bit.

The [solver receipt](../../native/snow_host/action_curve_roots_validation.json)
records 1,441 matching original-instruction cases: 81 lower-degree and 1,360
cubic cases. Ordered root bytes, root count, and the order and exact float32
arguments of runtime-math calls match. Both the emulator and reconstruction
use the same supplied Python math callbacks. Two zero-divisor cases are
explicitly excluded. This resolves solver branch arithmetic and root ordering
within that contract; original runtime-math implementations, non-finite cases,
active curve keys and physical clock units still require work.

### Original runtime-math comparison

The original math routines can execute offline from the private image. A second
validation now executes the complete original solver without substituted calls.
A separate emulator evaluates the original math routines as callbacks for the
independent solver. All 1,441 finite-intermediate cases match exact ordered
root bytes and count when those original callbacks are supplied.

This does **not** make the public Python math fixtures bit-equivalent. Comparing
the same complete original solver with Python math callbacks produced six
root-output mismatches. At the individual callback boundary, nine `acos` calls
and one `cos` call differed. The 1,703 sampled square-root and 1,055 power calls
matched; these counts are observations on this corpus, not proofs over their
full input domains. Small math-result differences can be amplified by the
subtraction used to construct roots. Sorting roots or tolerating an arbitrary
epsilon would hide rather than resolve this difference.

The offline image's runtime dispatch flag is zero. Other CPU-selected math
paths and the live game's initialized dispatch state have not been verified.
The public independent solver still requires explicit math callbacks; original
instruction bytes and emulator images remain private. The next portable-math
work should target `acos` and `cos` arithmetic on their curve-use domains.

Three separate probes also executed the original zero-divisor path for
coefficient sequences `(0,0,0,1)`, `(0,0,0,-1)` and `(-1,3,-3,1)`. Each returned
count three with every root equal to the negative quiet-NaN bit pattern
`0xffc00000`, under the emulator's current floating-point environment. A
mathematically repaired triple-root return would differ from this observed
behavior. The independent API intentionally keeps these cases outside its
finite-intermediate contract. NaN propagation through the complete curve
consumer and other floating-point environments remains unverified.

See [original-math comparison receipt](../../native/snow_host/action_curve_original_math_validation.json).

### Reconstructed curve acos

[`curve_acos`](../../engine/action_curve_math.py) independently implements the
return-value path of RVA `0x1c88a8c` for finite float32 input in [-1,1]. Inputs
outside that domain are rejected. It returns radians and has no persistent
state. CRT error handling and floating-point exception flags are excluded.
No runtime binary, coefficient file or game resource is required.

For |x| below 2^-26 it returns float32(pi/2). The endpoints return +0 and
float32(pi). Otherwise it evaluates a float32 rational approximation:

```text
outer = abs(x) >= 0.5
z = (1-abs(x))/2 if outer else x*x
P = (((-0.013381929136812687 - z*0.003961374517530203)*z
      - 0.05652986839413643)*z + 0.18416160345077515)*z
Q = 1.1049696207046509 - z*0.8364112973213196
r = P/Q
```

Each operation above rounds to float32. The inner branch combines `r*x` with
double-precision pi/2 and a low correction of `6.123233995736766e-17` before
rounding once to float32. Outer branches use `s=float32(sqrt(z))`. Negative
inputs combine `r*s` and s in double precision, then subtract twice that
corrected value from double pi. Positive inputs clear the low 16 bits of s,
reconstruct the lost part using `(z-truncated_s²)/(truncated_s+s)`, and combine
that correction with `2*s*r` and `2*truncated_s` in float32. The source records
the exact operation order; replacing this with an algebraically simpler
expression can alter rounding.

The [acos receipt](../../native/snow_host/action_curve_acos_validation.json)
records 20,334 exact return-bit matches against the complete original routine,
without substituted calls. Samples include signed zero, subnormals, adjacent
float values around each branch threshold, and seeded random values. This is
sampled evidence, not an exhaustive proof over every float32 input or runtime
floating-point mode.

Composing this independent acos with the root solver, while retaining Python
math sqrt/cos/pow fixtures, removes all six previous root-output mismatches
on the 1,441-case corpus. The independently observed single cos callback
mismatch remains a fidelity boundary even though it does not change the final
root bytes in this corpus. Portable cos reconstruction and runtime dispatch
variants therefore remain open; zero-divisor cases are still excluded.

### Reconstructed curve cosine

[`curve_cos`](../../engine/action_curve_math.py) reconstructs the dispatch-zero
path of RVA `0x1c803c0` for finite float32 angles with magnitude at most six
radians. This includes the complete finite angle range generated by the cubic
solver: theta is in [0,pi], and the largest argument is float32-rounded
`(theta+float32(4*pi))/3`, below six. Input is radians, output dimensionless,
and there is no persistent state. Other CPU dispatch paths, large-angle
reduction and floating-point exception side effects are excluded.

The routine converts float32 input to double and uses even symmetry. For
magnitude at most double pi/4, it evaluates the cosine polynomial directly.
Otherwise it computes `n=truncate(abs(x)*(2/pi)+0.5)` and subtracts n times
split pi/2 constants. If reduction loses more than 15 exponent bits, a second
split correction improves the remainder. The branch decision uses the
pre-correction exponent, which the implementation preserves.

For a small remainder, it uses either the remainder itself, `r-r³/6`, one,
or `1-r²/2`, selected by exponent and quadrant. Otherwise, with `z=r*r`,
the odd quadrant evaluates this sine polynomial in double precision:

```text
r + ((((2.7557319223985893e-6*z - 0.0001984126984126984)*z²)
      + (0.008333333333333333*z - 0.16666666666666666)) * (r*z))
```

The even quadrant evaluates the cosine polynomial:

```text
(1 - 0.5*z) +
 (((-2.755731922398589e-7*z + 2.4801587301587298e-5)*z²
   + (-0.0013888888888888887*z + 0.041666666666666664))*z²)
```

Quadrant sign correction precedes the final float32 conversion. The code
preserves each operation's ordering, including the split-reduction correction;
these expressions are a readable guide, not permission to reassociate them.

The [cosine receipt](../../native/snow_host/action_curve_cos_validation.json)
records 20,592 exact return-bit matches against the full original dispatch-zero
routine without substituted calls. Cases include both signs, zero/subnormals,
seeded samples, and neighboring float32 values around pi/4, pi/2, pi, 3*pi/2
and the supported domain endpoint. The earlier isolated cosine mismatch now
matches the original bits in a public regression test.

Using independent curve_acos and curve_cos with the root kernel matches all
1,441 original solver cases. Square root and power remain supplied Python
math fixtures in that composed comparison. Their sampled agreement does not
establish equivalence across all inputs or runtime environments. The next
input-response work can now capture curve data and configuration without
assuming a generic easing curve. Live captures remain subject to session
ownership; none were used for this work.

## Bounded ramp settings reader

[`observe_ramp_settings`](../../engine/action_ramp_observation.py) prepares the
next parameter capture without invoking the game. It takes a byte-reader,
a fresh processor identity, expected vtable/callback and the current build's
manager-global slot. The caller must verify build/process identity and derive
the processor through the current chain. Saved heap addresses are unsuitable.

It reads the manager's global shaping gate, processor configuration handle,
active sign bit, duration, axis mode, axis count, curve pointer, enabled bounds
and up to 64 curve keys. It makes two traversals and accepts only matching
semantic receipts. Budget is at most 32 reads and 4,608 bytes. Reads have no
side effects in this API; the caller owns the actual transport. Returned
addresses are private-session provenance and must not be copied into public
findings. No live run or launcher integration is claimed yet.

Handle comparison excludes unrelated bits. Key comparison excludes padding,
but preserves exact semantic float bits, including signed zero. Disabled
bounds are ignored. Zero-key curves are valid. The reader rejects non-finite
curve values, decreasing key positions, nonpositive duration, unexpected code
identity, null required pointers, truncated reads and budget overruns. It
returns an unstable status when relevant settings change between receipts.
This is a finite reconstruction-domain restriction, not a claim that the
original callback validates its inputs this way.

An inactive or null configuration object reports unresolved availability and
is not dereferenced. A disabled global gate is reported independently from
configuration availability. The initial native availability helper at RVA
`0x119f8d0` reads a TLS slot through GS:[0x58] and an indexed thread-local
pointer at +0x48. Its return combines with the configuration handle sign mask
in the callback's initial test. The observer does not read that thread-local
value and must not label a matching receipt as proof of execution or complete
activation. Chain enablement is also a separate caller-level fact.

Two matching traversals do not guarantee atomicity, lifetime or freedom from
ABA changes. The reader deliberately excludes changing timers and saved clock
from configuration equality. A separate state capture can later relate those
to input at a proven update boundary. Fixture tests cover maximum key count,
all read failure positions, changed configuration/keys, handle metadata,
bounds, signed zero, padding, inactive handles and global gating. Next: wire a
narrow private collector with fresh chain provenance; do not append this to the
212-request capture without re-budgeting the whole experiment.

## Ramp clock object selection

[`select_ramp_clock`](../../engine/action_clock_selection.py) reconstructs the
selection semantics of the ramp clock accessor at RVA `0x66d970`, including
its fallback scan at `0x66d9d0`. This selects an object whose +0x1050 field the
ramp reads; it does not yet identify the field's producer or physical unit.
The API is stateless and accepts current object/handle facts plus an explicit
registry-identity callback. Registry ownership and destruction are excluded.

```text
if manager is absent: return null
if context exists and context.index != -1:
    if override handle is active and its object is nonnull:
        return override object
for candidate handle in manager order:
    if active and object is nonnull:
        if registry_identity(object) not in excluded identities:
            return object
if registry_identity(fallback object) not in excluded identities:
    return fallback object
return null
```

The override bypasses the exclusion scan. Inactive candidate handles are
skipped without registry queries. Exclusion compares registry identities,
not raw object pointers. The scan preserves candidate order and stops at the
first eligible object. The fallback is queried even if its raw pointer is
zero; the callback must define the registry behavior in that case.

Build-specific evidence: context index is +0x200 and override handle pointer
+0x1e8. The manager candidate handle array is +0x72 with uint16 count +0x7c;
excluded identity array is +0x7e with uint16 count +0x88; fallback object is
+0x98. Handle activation is the sign bit of the dword at +0xc. The original
acquires registry identities through RVA `0x11925a0`, then decrements a
reference and can release them through `0x1194350`. Calling the native
accessor is therefore not equivalent to passive memory inspection. A future
read-only observer must reconstruct selection from fresh, bounded reads or
explicitly record an unknown registry dependency.

The [offline receipt](../../native/snow_host/action_clock_selection_validation.json)
records 512 original-accessor cases matching selected pointers and ordered
registry queries. It exercises manager absence, context presence/index,
override activation, candidate activation and exclusions. Registry acquisition
is supplied with synthetic identities and nonterminal reference counts;
reference-destruction paths are not validated. No live game was used.

This narrows where to inspect clock state. It does not prove milliseconds,
seconds, scheduler substeps, pause behavior or clock ownership by the player.
Next: identify writes to the selected object's +0x1050 and verify how selection
relates to the active player context before fitting timing constants.

## Ramp clock producer joins the existing clock tree

The selected object's +0x1048 record matches the ordinary world-clock record
already reconstructed in [WORLD_CLOCK.md](WORLD_CLOCK.md) and
[CLOCK_TREE.md](CLOCK_TREE.md). Its +8 uint64 field is `divided_ticks`, so the
ramp's read at object+0x1050 consumes that field, not the accumulated-tick
field at clock+0 and not the float interval at clock+0x18.

The shared updater at RVA `0x11eca80` writes this field at `0x11ecb8b` when
accumulation is enabled. Joining the previously validated arithmetic gives:

```text
processed = clock input after hold and scale rules
ticks = low_u32(truncate_i64(f32(f32(processed*30) + f32(0.1))))
accumulated_ticks = wrap_u64(accumulated_ticks + ticks)
divided_ticks = accumulated_ticks // 30
ramp_clock = unsigned_to_float32_with_native_signed_correction(divided_ticks)/1000
elapsed = f32(ramp_clock - saved_ramp_clock)
```

The final division rounds to float32. Integer truncation and float rounding
mean this is not interchangeable with summing the float interval. For example,
an unscaled synthetic input of 16 advances total ticks by 480, divided ticks
by 16, and the ramp clock by float32(0.016) from zero. When accumulation is
disabled, divided_ticks is retained even if interval calculation changes.
Positive hold count zeroes processed input, so ordinary non-wrapping totals
remain unchanged. This describes clock arithmetic, not proof that all game
work stops or that the same object is selected across updates.

The existing driver derives its divisor from timer frequency divided by 1000.
Together with this producer, milliseconds for divided_ticks and seconds for
the ramp clock are now supported unit interpretations, rather than an inference
from one isolated divisor. Imported timer API identity and live initialization
remain unresolved. Scale modes, previous-parent-interval child behavior,
selection changes and float32 precision still affect observed timing.

The [composed receipt](../../native/snow_host/action_clock_producer_validation.json)
records 480 exact scalar-bit comparisons across 160 three-node clock trees.
It executes the original complete updater, with lock helpers stubbed, then the
original ramp integer conversion and division on every resulting divided-tick
field. Tests vary holds, scale gates, accumulation, negative inputs and wrapping
states. This connects the two arithmetic kernels offline; it does not prove a
live selected object's root membership or scheduler cadence.

The passive [clock reader](../../engine/clock_observation.py) now exposes
`divided_ticks` from bytes it already reads. No additional remote read or
larger capture is required. Future captures can compare the actual ramp clock
source against interval, total ticks and hold/scale state without conflating
those quantities.

## Composed directional response

[`directional_response`](../../engine/action_response.py) composes the observed
ramp-then-diagonal processor order using the existing processor-chain kernel.
It accepts four input lanes, retained axis states, previous clock, explicit
start/end tick values, duration/mode, a curve callback and separate stage and
internal activation gates. It returns output, detached retained state, saved
clock and raw/working/published stage receipts. There is no implicit device
query, current-world selection or frame clock. Duration and time use the
ramp clock convention described above; input/output lane units remain defined
by their upstream and downstream consumers.

A disabled ramp stage preserves its axis state and saved clock but still
publishes unchanged input for the diagonal stage. An invoked ramp with a
closed internal gate also preserves state, while remaining distinguishable
in the chain receipt from an uninvoked stage. Diagonal enablement is separate.
This matters when testing control changes: a shaping bypass does not imply
that the whole processing chain is bypassed.

The [composed validation](../../native/snow_host/action_response_validation.json)
executes nine original-code sequences of 120 consecutive updates each. The
original chain invokes the original ramp, keyed evaluator, root solver and
runtime math, then original diagonal correction. Only the clock accessor and
TLS availability helper are supplied. Constant, linear and cubic synthetic
curves run with all three ordinary axis modes; sequences include presses,
holds, release, reversal and independently changing bypass gates. Exact final
output, each stage's raw/working/published bytes, axis states, timers and saved
clock match on all 1,080 updates.

The public reconstruction uses independent acos/cos and supplied Python
sqrt/power for the cubic fixture. It requires caller-supplied curves and does
not install these synthetic curves or the fixture duration as player tuning.
This is a composed processor result, not end-to-end gameplay validation.
Device-state ingestion, active action selection, actual curve parameters,
thread-local availability and physics-substep ordering still need evidence.

### Ramp collector integration, offline only

The launcher/probe now routes `ramp-observe` to the private collector's `--ramp`
mode. It inspects only the directional source and requires exactly one known
ramp stage. It brackets settings capture with batched reads of chain shape,
stage pointers, tables, callbacks, configuration handles and enable flags.
It also retains the existing source, composite and rooted action rechecks.
Selected ramp/evaluator instruction signatures are checked before and after.

An initial sequential implementation exceeded the helper's 224-request limit
in the offline fixture and was rejected. Batching the independent identity
reads reduced the maximum-key fixture to 219 requests without raising the
limit. The [fixture receipt](../../native/snow_host/action_ramp_collector_validation.json)
uses earlier private read values combined with synthetic ramp settings and
unused handle metadata. It is not a live capture or evidence that old heap
addresses remain valid. The actual collector always discovers identities
again. Five requests of headroom in this fixture do not guarantee completion
for larger graphs; exhaustion still fails closed. Runtime validation awaits
availability of the game from the other agent.
