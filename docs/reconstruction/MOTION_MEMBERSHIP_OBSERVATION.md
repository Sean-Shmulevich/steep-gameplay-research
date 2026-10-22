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
