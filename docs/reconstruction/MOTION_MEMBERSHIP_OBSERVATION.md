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
