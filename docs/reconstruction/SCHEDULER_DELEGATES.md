# Scheduler delegate dispatch contracts

The constructor-bound graphics delegate and a branch-job delegate share an
invocation adapter. Their enclosing dispatch contracts must remain distinct.

## Common invocation adapter

RVA `0x8ab390` receives function storage in RCX and receiver in RDX. It moves the
receiver to RCX and tail-jumps through the first qword of function storage.
The [invoker check](../../native/snow_host/graphics_delegate_invoker_validation.json)
verifies exact forwarding and preservation of the caller's return address.
It does not strip tags or determine a callback's return type.

The graphics binding is documented under
[graphics delegate invocation](ANIMATION_CONTEXT_RETIREMENT.md#graphics-delegate-invocation-adapter).
Its owner-relative delegate is not interchangeable with the existing probe's
image-backed virtual slot. Native installation remains unimplemented here.

## Branch dispatcher

Dispatcher RVA `0x11d14c0` has the following locally inspected behavior:

```text
branch_dispatch(job):
    lock(job + 8)
    receiver = job.delegate.context_word & ~3
    result = job.delegate.invoker(&job.delegate.function_storage, receiver)
    if low_byte(result) != 0:
        helper_A(job + 0x1b8)
        helper_B(job + 0x70)
    else:
        helper_A(job + 0x70)
        helper_B(job + 0x1b8)
    unlock(job + 8)
```

The delegate begins at job +0x198; context is +0x1a8 and invoker +0x1b0.
The two list services are `0x11d29e0` and `0x11e7ba0`, respectively. Their
semantics are deliberately not inferred from this caller alone. The dispatcher
appears as a stored function pointer at image RVA `0x28f53d0`; that reference
alone does not identify every receiver or establish the graphics-job route.

A [16-case connected instruction check](../../native/snow_host/branch_delegate_validation.json)
executes both this dispatcher and the common invoker. It tests all four context
tag combinations and predicate results 0, 1, 255 and 256. The last case follows
the false branch because only AL is tested. The check verifies decoded receiver,
lock/predicate/list-service/unlock order and the two selected list addresses.
The predicate, lock and list services are intercepted. Callbacks return normally;
no exception cleanup or concurrency guarantee is established.

## Remaining graphics binding gap

This branch dispatcher supplies concrete evidence of upstream tag stripping for
one scheduler job type. It cannot close the graphics route by analogy: it consumes
a predicate return byte, while the inspected graphics binding alone establishes
no such predicate contract. To install a graphics-phase observer, first identify
the concrete job table and its dispatch slot, follow that body into the delegate,
and qualify owner lifetime and slot ownership. Keep an observation wrapper's
calling convention tied to that confirmed route.


## Concrete graphics dispatcher now identified

The [live binding capture](../../native/snow_host/graphics_job_live_binding.json)
qualifies the graphics job at engine owner +0x218. Three startup samples agree:
table RVA `0x1e89618`, slot +0x40 target `0x65b1e0`, main delegate callback
`0x656c20`, invoker `0x8ab390`, and masked context equal to the engine owner.
Selector +0x5a was zero in those samples. This closes the concrete-table and
upstream-decoding gaps above for this observed binding. It does not sample the
callback's execution or establish selector stability across frame gates.

```text
graphics_job_dispatch(job):
    if (job.before.context & ~3) != 0 or job.before.function != null:
        job.before.invoker(&job.before.function, job.before.context & ~3)
    job.main.invoker(&job.main.function, job.main.context & ~3)
    if (job.after.context & ~3) != 0 or job.after.function != null:
        tail_call job.after.invoker(&job.after.function, job.after.context & ~3)
```

The before, main and after delegates begin at job +0xf0, +0x198 and +0x110.
Each record is 32 bytes. The main call is unconditional; its return is not used
for branch selection. Optional eligibility checks function/context, not whether
the invoker field is nonzero. A tag-only context with null function is skipped.
Do not assume a context-only record is safe with every invoker implementation.

A [32-case connected instruction check](../../native/snow_host/graphics_dispatch_validation.json)
executes this concrete dispatcher and the common invoker. It varies all context
tags, optional callback presence and callback return bytes. It verifies exact
before/main/after ordering, decoded receivers and normal return stack balance.
Synthetic callbacks supply no evidence about native mutation or exception safety.

The before/after records are candidates for bounded phase observation. No native
installation was attempted. An installer must preserve existing callbacks,
qualify the full descriptor and owner, prevent concurrent inconsistent updates,
and account for callers that already loaded an invoker. Image-vtable swapping
rules do not automatically establish those owner-relative delegate guarantees.
The read-only session stopped cleanly with saves/settings restored and original
DLL verified. No private heap addresses are included in the public receipt.

## Job teardown contract

Static inspection connects the live graphics table's deleting destructor at RVA
`0x652c70` to base teardown `0x11cb650`. The relevant normal path is:

```text
graphics_job_destroy(job, flags):
    job.main.invoker = null
    job.table = base_job_table
    if job.byte_194 != 0:
        repeat:
            state = read_u32(job + 0x54)
            stack_locked_or_zero()  // ordering instruction, not the job lock
            count = read_i32(job + 0x50)
            if state == 0 and count <= 0: break
            processor_pause()
    job.completion.invoker = null  // +0x168
    job.after.invoker = null       // +0x128
    job.before.invoker = null      // +0x108
    teardown_list(job + 0x70)
    destroy_lock(job + 8)
    if flags & 1: free_storage(job, 0x1b8)
    return job
```

The base constructor at RVA `0x11c8c40` initializes +0x50/+0x54 to zero
and the word at +0x194 to zero. It also clears the function, context and invoker
fields of the before/after/completion delegates. It does not initialize every
byte of those 32-byte records. This is a constructor default, not an observation
of the live job's current wait policy. Subsequent writers remain to be qualified.

The [36-case instruction check](../../native/snow_host/graphics_teardown_validation.json)
executes both destructors with synthetic job storage. It varies the wait flag,
state 0/1/2, count 0/1/-1 and deletion flag. Fourteen cases enter the busy loop
and receive a synthetic releasing update on the second poll. List teardown,
lock destruction and free are intercepted. It verifies main-invoker clearing
before the wait, optional-invoker clearing afterward, helper arguments and
return-stack balance. Negative count alone does not keep this local loop busy.

The runnable [bounded trace model](../../engine/scheduler_job_teardown.py)
accepts supplied state/count read pairs. Exhausting observations while busy
reports an incomplete trace. It never invents a completed drain or runs native
cleanup. For example:

```python
from engine.scheduler_job_teardown import teardown_trace
trace = teardown_trace(True, [(1, 0), (0, 1), (0, 0)])
assert trace['completed']
```

For modding, this rules out treating destructor entry as a general callback
quiescence point. The main invoker is already cleared when the optional wait
starts; the local dispatch reads that invoker unconditionally. The inspected
paths therefore require an external lifecycle/order guarantee to prevent a
concurrent dispatch from consuming the cleared descriptor. The wait itself uses
two separate reads and a flag that starts disabled. Neither that loop nor a zero
counter proves that all mod callbacks, cached pointers or queued work are gone.
We have not established the protecting scheduler phase or enabled-flag writer.

## Separate post-service delegate

The same live graphics table's slot +0x58 targets RVA `0x67adf0`. It acquires
job +8, calls `0x11d16f0`, releases job +8, then conditionally invokes the delegate
at job +0x150 using the same function/context eligibility and tag masking rules.
The inner routine itself acquires and releases job +8. If state +0x54 equals 1,
it calls `0x11e7940` with the global service and job; otherwise it writes state 2.
The locks' implementation and the helper's full effects are outside this local
inspection. Do not call the +0x150 delegate an all-work-finished or unload-safe
callback based on its position after this service. Its scheduling caller and
relationship to active callbacks still need qualification.

## Submission enables the teardown wait

The writer at RVA `0x11e2d06` belongs to the submission routine `0x11e2ca0`,
whose request/begin behavior is already reconstructed in
[MixedScheduler](../../engine/mixed_scheduler.py) and the
[request reducers](REQUEST_STATE_MODEL.md). This closes the previous unknown
writer relationship for this submission path:

```text
submit(job):
    capture_notification_generation()
    lock(job + 8)
    if job.state == UNSCHEDULED:
        job.requested += 1
        if job.holds == 0: job.virtual_begin()
    scheduled = job.state == SCHEDULED  // reread after possible begin
    job.byte_194 = 1
    unlock(job + 8)
    service_notification_generation()
    return scheduled
```

Profiling calls surround this body under a separate global switch. The wait flag
is set even when no request is incremented, and even when a synchronous empty
begin returns the job to UNSCHEDULED. It is set after the virtual begin returns.
The native comparison precedes the flag store; the saved boolean is returned
after unlocking and notification service. The [18-case instruction check](../../native/snow_host/submit_lifetime_validation.json)
varies initial states, holds and begin-result states. It checks the write order,
request count and returned boolean with profiling disabled and external services
intercepted. This identifies one writer, not every submission path or flag reset.

`MixedScheduler` already represented this flag as `usage`; no new native flag is
invented. Its new `teardown_wait_status(name)` connects that existing field to
the destructor predicate and reports state and outstanding dispatches separately
from executions. It is read-only and does not destroy a job. Integration tests
cover queued state with no dispatch yet, callback return before final dispatch
accounting, final drain, immediate empty-range completion and later resubmission.
A false `would_wait` result is an instantaneous serial observation, not a permit
to unload, mutate native descriptors or prevent future requests.

## Queue removal behind the post-service path

The previously opaque helper `0x11e7940` chooses a category queue from job +0x40.
When the low 32-bit affinity mask at +0x38 is nonzero, its least significant set
bit selects an entry in service +0x6c0. A nonnull entry selects that worker's
queue at `worker +0xd0 + category*0x240`. Otherwise the route falls back to
`service + category*0x240`. The category is sign-extended; valid category bounds
are a caller invariant, not checked here.

Under the selected queue lock, helper `0xe30420` searches the pointer array at
queue +0x30 for this job. If found, `0x115b920` shifts the following entries down
and decrements the count, preserving their order. A miss leaves the array alone.
The caller ignores that helper's success byte. If job byte +0x170 is nonzero,
it decrements service +0x8dc regardless of whether removal succeeded. It then
sets job state to DONE and unlocks the queue. Queue membership and accounting
consistency are therefore required invariants, not repaired by this routine.

This is static inspection, not a connected emulation of the removal chain.
The ordinary begin path already called this operation `remove_from_queue`;
see [begin paths](SCHEDULER_BEGIN_PATHS.md). The new connection is to graphics
slot +0x58 through `0x11d16f0`. That route can transition to DONE without waiting
for every outstanding dispatch. Its optional +0x150 delegate must not be exposed
as an all-dispatches-drained notification. The reservation caller is resolved in the section below. Outer lifecycle
exclusion remains open.

## Dispatch phases versus finalization

The worker wrapper at RVA `0x11e9990` invokes job slot +0x40 at `0x11e9a3c`,
restores its execution context, then calls `0x11e2d70` at `0x11e9a7d`. The
[category worker analysis](INPUT_TO_ACTION_ROUTE.md#category-worker-return-and-dependency-release)
already established that wrapper's ordinary completion path. The concrete
graphics binding now connects its before/main/after calls to the same boundary.

The [64-case connected check](../../native/snow_host/graphics_completion_validation.json)
executes the graphics dispatcher, common invoker, completion routine and ordinary
finalizer in that serial order. An authored caller omits the wrapper's TLS,
profiling and notification operations. Synthetic callbacks, lock services and
dependency release replace external effects. The check varies context tags,
optional handlers, states SCHEDULED/DONE and one/two active dispatches. These
supplied states exercise local branches, not asserted live graphics workloads.

All optional after calls run with execution and outstanding counts unchanged.
Completion first decrements executions. With DONE and zero executions, it calls
the ordinary finalizer. That finalizer releases active dependencies before
writing UNSCHEDULED. The outstanding count remains positive during that release
and drops only afterward. With SCHEDULED and the callback job's false empty
predicate, this local completion path does not finalize it. This connects the
callbacks to existing completion semantics without treating an after callback,
DONE state or dependency release as a universal drain.

## Reconstructed before and after handlers

`MixedScheduler` callback definitions accept optional `before_handler` and
`after_handler` names alongside `handler`. Names resolve through the existing
versioned registry. Each receives `(context, None)` and runs synchronously in
before/main/after order, inside the reserved dispatch. Return values do not
select a branch. Missing optional handlers are skipped; an absent main handler
remains the reconstruction's authored no-op fixture policy. This is not a model
of a null native main invoker, which the inspected dispatcher calls unconditionally.

Run the example with:

```sh
python3 -m engine.examples.callback_phase_probe
```

The example reports positive outstanding accounting during all three handlers
and after their return, then zero after `finish_dispatch`. A dependent terminal
job begins during finalization. The registry is immutable after construction;
this API does not replace live native descriptors. Existing fail-stop behavior
on Python handler exceptions is adapter policy, not recovered native unwinding.
Three tests cover ordering and dependency timing, ignored return values, failure
without invented completion, and rejected bindings/job kinds.

A scoped search of indirect slot +0x58 calls in scheduler-region functions found
several profiling and unrelated object calls, but no newly qualified graphics-job
caller. Do not identify those solely from their slot offset. The reservation caller is resolved below. Outer destruction exclusion remains
open.

## Reservation callback and category lock ownership

The selected-job tail at RVA `0x11d8238` increments outstanding dispatches at
+0x50 and executions at +0x4c, then invokes slot +0x58 at `0x11d8246`.
Only afterward does it release the category queue lock. With the observed
ordinary graphics table, that slot is `0x67adf0`, the previously described
post-service delegate path. Thus its +0x150 delegate is the optional reservation
callback, not a completion notification. This connects the concrete binding to
[the already documented callback reservation route](ENGINE_LOOP_HANDSHAKE.md#callback-jobs-become-done-on-reservation).
The earlier unresolved-caller statements are superseded for this queue route.

```text
selected_job_tail(job, category_queue):  // category lock already held
    atomic_increment(job.outstanding_dispatches)
    atomic_increment(job.executions)
    job.on_reservation():
        lock(job)
        lock(job)  // nested state-service call
        if job.state == SCHEDULED:
            remove_from_queue_and_mark_done(job)
        else:
            job.state = DONE
        unlock(job)
        unlock(job)
        invoke_optional_reservation_delegate(job)
    unlock(category_queue)
    return job
```

The removal helper has its own queue locking, described above. The pseudocode
abbreviates that helper and does not claim the queue selected by removal always
aliases the outer category container. Valid routing and lock implementation are
separate native invariants. The reservation delegate runs after the two local
job-lock acquisitions have been released, but before the outer queue unlock.
Earlier wording that merely said "after lock release" was insufficient for
choosing a mod execution phase.

An [eight-case connected instruction check](../../native/snow_host/graphics_reservation_validation.json)
executes the selected tail, concrete reservation method, nested state service,
graphics body dispatcher, common invoker, completion and ordinary finalizer.
All four context tags and optional reservation presence are tested. The category
lock is supplied as held on entry; lock services, removal/state change and
dependency release are intercepted. The fixture observes:

```text
account dispatch -> mark DONE -> optional reservation -> outer queue unlock
-> before -> main -> after -> dependency release -> final accounting return
```

Counts are one during reservation and all body phases. Dependency release sees
zero executions and one outstanding dispatch. The final state has both counts
zero and is UNSCHEDULED. This is serial instruction evidence, not live concurrent
lock validation. A scoped search initially missed the connection because the
selected tail has a separate function-table range and no local state +0x54
access; searches requiring both properties in one range exclude this caller.

The reconstruction now accepts `reservation_handler` for callback jobs, resolved
through the same versioned registry. `reserve(..., context=...)` supplies the
context; `dispatch_next(context)` forwards it. The handler runs after the
reconstructed job becomes DONE and leaves the queue, before reserve returns.
Its trace labels the native lock context. The Python scheduler does not implement
those native locks, and this field is not authorization to install an arbitrary
mod callback under a game queue lock. Keep reservation separate from body-phase
hooks. Failure uses the existing authored fail-stop policy without pretending
the reserved dispatch completed. Three tests cover phase order and counters,
context forwarding, failed reservation and incompatible job kinds. The runnable
`callback_phase_probe` now includes reservation as its first observation.

## Engine construction and initial frame-service selector

Constructor RVA `0x647d60` initializes an event holder at owner +0x48 and
constructs ordinary callback jobs at +0x60 and +0x218. Both receive table RVA
`0x1e89618`, matching the root/graphics layout and the earlier live graphics-table
observation. This is a layout-and-binding join; constructor entry was not observed
live. The constructor prefix stores word 1 at owner +0x59, which writes byte
+0x59 as 1 and the adjacent frame-service selector +0x5a as 0. Selected tail
stores clear owner +0x58. These are distinct bytes, not one boolean field.

```text
engine_constructor_prefix(owner):
    initialize_event_holder(owner + 0x48, 0, 0)
    owner.byte59 = 1
    owner.frame_service_selector = 0  // same native 16-bit store
    initialize_callback_job(owner + 0x60, category=1, byte_limit=1)
    initialize_callback_job(owner + 0x218, category=1, byte_limit=1)
    # Further embedded jobs and initialization follow.

selected_constructor_tail(owner):
    owner.byte58 = 0
    # Other stores omitted.
```

Each of these two job initializations clears the main function, context and
invoker. Their limit is set explicitly to 1 after the base constructor. The
base constructor supplies initially empty optional delegates and a zero usage
flag. A constructed job with a null main invoker is not ready for dispatch;
the later setup routine `0x6968e0` supplies callable bindings and graph edges.
This separates construction, binding and submission instead of treating a
matching table as evidence that a callable is installed.

The [six-case instruction check](../../native/snow_host/engine_job_initialization_validation.json)
executes the constructor prefix and base job constructor, followed by selected
tail stores. It varies initially zero/nonzero synthetic storage and three shared
worker defaults. It verifies event/job receiver offsets, table identities,
selector bytes, limits, null callable fields and zero usage flags. Event, lock
and dependency-list construction are intercepted, and the middle of the engine
constructor is omitted. This does not validate full construction, its caller,
shutdown, or the absence of later writes through aliases.

For the [two-read placement model](../../engine/frame_service_placement.py),
two observations retaining this initialized zero select site A, not the
BeginGraphicFrame site. The live zero samples agree with the initialized value,
but neither those samples nor this constructor store proves selector stability
between gates. Later selector writers and the outer lifetime exclusion still
need qualification. This supersedes the earlier missing-initialization lead
without changing the model's two-independent-read contract.

## Bounded inspection API

[engine_job_observation](../../engine/engine_job_observation.py) exposes the root
and graphics job bindings together with their dispatch accounting and usage
flags. It accepts an exact-read transport and a caller-verified image identity:

```python
from engine.engine_job_observation import observe_engine_jobs
report = observe_engine_jobs(
    readv, image_base=relocated_base, image_size=verified_image_size,
    verified_image_sha256=verified_hash)
```

The adapter does not verify the supplied hash itself. The transport must enforce
process identity and read timeouts. It performs two sequential sweeps, totaling
at most 16 ranges and 2086 bytes. Each checks the owner global, shared table
methods, both embedded job tables, then rereads owner/table identities after the
job blocks. A failed guard or short read raises instead of returning a qualified
sample. No writes or engine calls occur.

Each report includes selector/start-region bytes, execution/outstanding counters,
request/hold fields, the usage flag, the local teardown wait predicate and the
four delegate records' function/invoker classifications. Image addresses become
RVAs; raw heap addresses and auxiliary delegate payloads are omitted. Receiver
relationships distinguish owner, job, null and other. Optional eligibility uses
the inspected masked-context-or-function rule. A nonempty descriptor is not
proof that its callback is callable or safe to invoke.

`observations_equal` compares all raw bytes read, including redacted fields,
while exporting only normalized observations. Thus equal-looking public samples
can still be marked unequal if a hidden context or auxiliary field changed.
Equality is not an atomic snapshot, lifetime pin, proof of execution, or native
mutation permission. The two job samples can also describe different instants.
The root layout is constructor-qualified; the graphics binding additionally has
the earlier live capture. This expanded API has synthetic tests but has not yet
been used for a live capture.

Six tests cover read bounds, tag handling, pointer redaction, changed counters,
redacted pointer changes, guard failure, short reads, bad method/build identity
and external callbacks. It is intended to replace isolated unqualified field
reads when testing lifecycle relationships. Native callback installation and
outer ownership/destruction remain unresolved.

## Live lifecycle inspection

The [expanded live receipt](../../native/snow_host/engine_jobs_live_observation.json)
records three successful uses of the bounded API after native startup reached
gameplay. Three relevant instruction spans matched the analyzed image. All
owner/table guards passed; each report used 16 ranges and 2086 bytes. The capture
sent no movement input, installed no scheduler callback and attached no debugger.
The startup director still performed its established native navigation actions.

Both root and graphics request/started counters advanced. Across the six sweeps,
the paired counts were 2047, 2047, 2055, 2056, 2065 and 2065. Both job states,
execution counts and outstanding counts were zero at each sampled point. The
root usage flag was true; the graphics usage flag was false in every sample.
Selector +0x5a remained zero; the neighboring observed bytes +0x58/+0x59 were
1/0, differing from their construction defaults. This does not identify their
intervening writer or promise selector stability between observations.

Root main was RVA `0x6569e0`, graphics main `0x656c20`, both with the common
invoker and an owner-related receiver. Root before was nonempty and bound to
`0x75e600`, whose inspected body is an immediate return. Root after/reservation
and all three graphics optional delegates were empty by the dispatcher predicate.
An occupied descriptor can therefore bind a no-op; emptiness alone does not
explain what work a phase performs. None of these callbacks was observed at entry.

The differing usage flags fit the established distinction between explicit
submission and dependency-driven request propagation. A new two-cycle synthetic
integration test demonstrates that distinction in MixedScheduler. It is a
consistent explanation, not live proof of the graphics request producer.
Neither false usage nor the false local teardown predicate proves a job never
executes. Likewise zero sampled execution counters cannot establish that no body
ran between samples. One paired capture detected changing raw observations;
two were equal, with neither result establishing atomicity or lifetime pinning.

The game stopped deliberately after capture. Bottle shutdown, save restoration,
settings restoration and original-DLL verification all passed. Raw process
identity and transport data remain private. The next useful execution capture
should join these bindings to callback entry and exit, rather than infer active
work or mutation permission from idle-looking polls.

## Native delegate recorder core

The authored [C recorder](../../native/snow_host/snow_delegate_trace.c) and
[header](../../native/snow_host/snow_delegate_trace.h) support the inspected
invoker's two-argument shape: function-storage address and decoded receiver.
The caller supplies the original invoker. The recorder forwards both arguments
without dereferencing either, records entry/exit ticks and thread identity, and
returns the original integer result unchanged. No float/vector return contract
is asserted. Graphics dispatch ignores that result; this is not a replacement
for an arbitrary unknown callback ABI.

Capture uses an atomic closed-bit/active-count gate and bounded, nonwrapping
record reservations. A call admitted before close completes its record. Calls
after close still forward but do not write records. Full capacity drops capture,
not the underlying call. Records are available only after close plus capture
drain. Callback code, recorder state, records and function providers must remain
alive for all possible callers, including cached callers after close. There is
no reset/reopen operation, exception containment or native unload permission.
Addresses in the internal record are private session provenance, not public data.

The native pthread fixture holds one original call active, closes capture, makes
a late forwarding call, then releases and joins the first caller. It verifies
argument identity, a full-width integer result, entry/exit timing, unchanged
output on refused reads, close/drain behavior and zero-capacity forwarding. The
core also compiles as a Windows x64 object with MinGW. This checks portable
recording mechanics and compilation; it does not prove the Windows live ABI or
install anything in the game.

The existing actor-vtable installer cannot be reused unchanged. It requires a
nonexecutable image-backed slot whose module can be pinned. The graphics main
invoker lives at owner +0x3c8 inside a heap-owned delegate. Replacing only that
aligned qword is a candidate publication strategy that avoids rewriting all
32 descriptor bytes, but compare/exchange alone does not pin the owner or prove
the function/context binding remained compatible. A native adapter still needs
qualified binding checks, a stated owner-lifetime window, retained forwarding
code/configuration, conflict-aware restoration and a bounded capture controller.
No DLL wrapper, installer or live capture using this new core is claimed yet.

## Experimental Windows adapter

The [Windows adapter](../../native/snow_host/snow_delegate_probe.c) now builds as
`snow_delegate_probe.dll` in the standalone host build. Its
[ABI v1 header](../../native/snow_host/snow_delegate_probe.h) describes a one-shot
configuration and installation attempt, retryable restore, close/drain and sized
record reads. It targets the graphics main delegate at owner +0x3b0 and its
aligned invoker field at +0x3c8. This is not a general hook-placement API.

Configure checks owner-global identity, the graphics job table and dispatch
method, the function/auxiliary/context fields and original invoker. Function,
invoker, dispatch method, table and owner global must belong to the same image;
code targets must occupy executable image pages. The slot must occupy committed,
writable private memory. The adapter pins its own module and the original image,
then initializes the recorder before any supported pointer publication.

Install rechecks the binding and uses compare/exchange to replace only the
invoker qword. It does not alter page protection or rewrite the other delegate
fields. Restore rechecks identity and descriptor fields, replaces only its own
pointer, accepts an already-restored original, and refuses a competing pointer.
Closing capture prevents future installs but preserves late forwarding through
cached wrapper addresses. Keep the DLL/configuration/storage alive through
process exit; capture drain does not permit native unload.

The caller must still guarantee allocated, unreused owner storage while install
and restore access the slot, and compatible function/context ABI for cached
callers. Guard reads and CAS do not establish those prerequisites or prevent a
concurrent teardown between checks. No live-game installation was performed.
Build identity and exact native instruction compatibility remain caller duties.

The [Windows fixture receipt](../../native/snow_host/delegate_probe_fixture_validation.json)
records five synthetic-process scenarios under Wine: ordinary install/restore,
competing invoker, owner/context changes, read-only owner memory, and close before
install. They check refusal without overwriting a competitor, retry after restored
identity, unchanged full-width return, record copying and cached forwarding after
restore/close. The fixture uses allocated storage that remains alive throughout;
it does not prove the game's ownership window or protection-layer acceptance.

The [fixture source](../../tests/fixtures/snow_delegate_probe_fixture.c) can be
compiled with the same MinGW compiler and include path as the DLL, then invoked
as `snow_delegate_probe_fixture.exe <DLL-path> <scenario>`. Scenario names are
`normal`, `conflict`, `identity`, `readonly` and `closed`. The standard host build
compiles the DLL but neither loads it nor launches this fixture or the game.
This supersedes the prior missing-DLL/installer status; live ABI and owner-lifetime
qualification remain open.

## One-shot capture controller

The opt-in [capture plugin](../../native/snow_host/examples/delegate_capture.c)
is built by `build_snow_host.py --adapter steep --delegate-capture-plugin`.
It is disabled unless its plugin INI has `[capture] enabled=1`. Its configured
`milliseconds` must be between 100 and 2000, with a default of 500. Initialization
refuses an existing `<config-path>.trigger`; the controller must create that
file later inside its explicitly bounded owner-lifetime experiment.

The pinned worker waits at most 180 seconds for the trigger. On receipt, it
checks fingerprints of the common invoker, graphics dispatcher and main callback
prefix, then resolves the engine owner and expected main descriptor. It configures
and installs the probe, captures for the configured interval, restores once and
polls close/drain for at most two seconds. An unload notification requests early
cancellation; it does not unload the pinned forwarding code. It never sends
movement input, pauses the scheduler or calls a gameplay setter.

The output is local JSONL at `<config-path>.trace.jsonl`, including installation,
restoration and drain outcomes plus private pointer/timestamp records. A consumer
must read and validate the complete file, including the expected record count;
file existence alone does not mean the writer has finished. Missing output,
failed restore, incomplete drain or a truncated file is a failed capture, not
permission to discard the forwarding module. No automatic retry/reinstall occurs.

The [controller fixture](../../native/snow_host/delegate_capture_fixture_validation.json)
tests disabled configuration, stale-trigger refusal and rejection of an
incompatible synthetic executable under Wine. The underlying adapter's successful
synthetic installation is documented separately. No live-game installation has
been performed with this controller. A trigger is not a native lifetime lock;
the experiment must still state and check its owner-lifetime assumptions.

## First live graphics delegate capture

The [live receipt](../../native/snow_host/delegate_probe_live_validation.json)
records a successful 500 ms one-shot experiment after native startup reached
gameplay. The controller first qualified the owner and job bindings, checked the
game was advancing and not held, then created the plugin trigger. The plugin's
instruction fingerprints, configuration and installation all passed.

The recorder captured 42 calls, with no dropped records, over a measured
0.4990537-second entry-to-final-exit span. Every record used the selected main
function-storage address and decoded engine receiver. One thread appeared in
these records. Observed call durations ranged from 60.3 to 258.8 microseconds,
with a median of 70.3 microseconds. These are instrumented durations, not an
original-engine performance benchmark or a physics-step rate.

Restore and capture drain succeeded. The controller reread the original common
invoker and same owner identity, then observed the engine step count advance from
2058 to 2075 after restoration. Before capture it was 2014. Those counters are
separate observations, not per-record substep attribution. The experiment sent
no movement input, requested no scheduler pause and attached no debugger.

This provides actual invocation evidence that the earlier idle-looking polls
could not supply. The bounded ABI forwarding, pointer replacement, complete
record output and restoration worked for this binding in this session. It does
not establish safe arbitrary mod execution at this phase, all-thread affinity,
input/physics alignment, or behavior during owner destruction. The experiment
assumed stable engine storage during normal gameplay; same-owner guards before
and after do not prove lifetime exclusion or rule out address reuse.

The capture plugin and forwarding code stayed pinned until the game process
exited. The launcher deliberately stopped the bottle after validation and verified
save/settings restoration and the original DLL. No raw pointers or trace payloads
are included in the public receipt. This supersedes prior no-live-installation
status for this one tested binding and controller; general native unload remains
unsupported.

The next instrumentation join should associate these callback entries with job
state, frame-service selector and caller provenance. Forty-two graphics callbacks
alone do not establish which physics or input work belongs to each one.

## Caller provenance instrumentation (record ABI 2)

The authored native recorder now accepts an explicit caller return address. The
Windows wrapper captures its own return address before forwarding, with inlining
prevented, and exports record ABI 2. JSONL summaries identify `record_abi: 2`;
each record adds private hexadecimal `caller`. Clients must check both ABI and
record size before reading native records. The existing portable call API records
zero for unavailable provenance; it does not guess a caller from its own stack.

This adds no stack walk or game-state reads. A caller address identifies a return
site, not a complete invocation chain: tail calls can remove intermediate frames.
Interpret it only after checking the current module range and build identity;
normalize to an image RVA for public findings. Raw addresses remain private.
The prior 42-call live receipt used ABI 1 and does not validate this new field.
Job counters, selector reads, and input/physics association remain pending.

All five synthetic Windows/Wine adapter scenarios passed with ABI 2. In the
three scenarios that capture a call, the recorded return address belongs to the
fixture executable image, not the probe DLL. The portable threaded fixture also
checks full-width caller preservation while closing during an active call.
These are synthetic checks; no new game session was launched for this change.
The controller refusal receipt retains its earlier source hashes and is historical.

## Live caller attribution

The [ABI 2 live receipt](../../native/snow_host/delegate_caller_live_validation.json)
records 43 captured calls with zero drops during a configured 500 ms window.
Every caller resolves to RVA `0x65b223`, immediately following the indirect call
at `0x65b221` in the decoded graphics dispatcher. That call loads the main
invoker from job +0x1b0, passes function storage at job +0x198, and masks the
receiver context's low two bits. Recorded storage and receiver matched the
selected graphics binding throughout this capture.

This closes the immediate live caller-to-dispatcher join. It does not establish
which worker wrapper invoked the dispatcher, an entire call stack, or a physics
substep/input relationship. The original invoker was restored and engine steps
advanced from 2014 to 2031 after restoration (1967 before capture). No movement,
scheduler pause, or debugger attachment was used. The launcher stopped the game
and verified saves, settings, and original DLL restoration. The next observation
is job state before and after this now-attributed main call; completion accounting
must still be distinguished from returning out of the main callback.

## Entry/return job observations (record ABI 3)

The authored recorder's optional observation provider runs immediately before and
after forwarding the original main delegate, inside the reserved capture record.
Closed or full captures forward without invoking the provider. Configuration is
immutable after publication. Native record ABI 3 adds `before` and `after` fields;
JSONL declares `record_abi: 3`. Clients must check ABI and record size.

For the selected graphics binding, each observation checks the owner global,
job table, dispatcher method, descriptor and acceptable invoker both before and
after reading six consecutive counters at job +0x4c, usage at +0x194 and the
owner frame-service selector at +0x5a. Expected invokers are the recorder and the
original (restoration may occur during a call). A competing invoker is rejected.
Counter meanings follow the dispatch/completion evidence above: executions,
signed outstanding dispatches, state, started requests, requested requests, holds.
The bytes are retained as raw unsigned usage/selector values, not inferred flags.

`valid: 1` means these sequential reads and identity guards passed. It is not an
atomic snapshot, a lock, or an owner-lifetime guarantee. On any guard/read failure,
the observation stays zero with `valid: 0`; forwarding still occurs. Returning
from the original main callback is not dispatcher completion: after-delegate,
worker context restoration and completion accounting may still follow.

Entry/exit timing now includes both observation providers, so it is not directly
comparable to earlier instrumented callback durations. The provider uses bounded
self-process reads without retries, game setters or scheduler locks. Operating
system read latency remains outside a hard real-time guarantee. Raw caller and
object pointers remain private.

### Live entry/return accounting

The [ABI 3 live receipt](../../native/snow_host/delegate_state_live_validation.json)
contains 48 captured calls with zero drops and 96 successful guarded observations.
Every caller was the previously verified graphics main-dispatch return site.
Every before/after pair agreed: executions 1, outstanding dispatches 1, state 2
(`DONE`), holds 0, usage byte 0 and frame-service selector 0. Started and requested
counts matched and advanced consecutively from 2053 through 2100 across records.

This directly demonstrates an active, non-drained job with state `DONE` and zero
usage, including immediately after its main callback returned. It supports the
reconstructed distinction between main-body return and worker-side completion.
It does not capture the later decrements or prove the request producer. Selector
zero is consistent with the earlier site's frame-service route; the graphics
callback's entry alone does not prove that other site executed in that frame.

The synthetic test `test_live_graphics_signature_is_not_a_drain_predicate` in
[test_mixed_teardown_status.py](../../tests/test_mixed_teardown_status.py) reproduces
this accounting signature with a dependency-requested callback. Its local
teardown predicate is false while the execution and outstanding counters remain
positive; only explicit dispatch completion drains them. This is a reconstruction
comparison, not proof that the chosen synthetic producer is the live producer.

Restore/drain succeeded, simulation steps advanced afterward from 2103 to 2124,
and saves/settings/original DLL cleanup passed. No movement, pause, or debugger
was used. Instrumented durations include both observation providers. The next
missing live boundary is worker completion/finalization and its dependency
release, rather than another idle poll or treating the main return as a drain.

## Connected finalization and dependency release

The [128-case instruction check](../../native/snow_host/completion_release_validation.json)
connects original completion, ordinary finalizer, and the full normal dependency
release routine. Earlier connected tests stubbed the release service. This check
substitutes recording lock services and successor begin only. It varies active
list, last hold/zero holds, pending request, credit gate, zero/positive credit,
and deferred flag for both normal successors and credit recipients. Ten cases
invoke the successor begin stub. The credit-recipient path here is the second
loop inside normal release, not the separate alternate-release operation.

For the supplied one-dispatch DONE predecessor, the checked boundaries are:

| Boundary | Predecessor lock depth | Executions | Outstanding | State |
| --- | --- | --- | --- | --- |
| Virtual finalizer entry | 1 | 0 | 1 | DONE |
| Dependency release entry | 2 | 0 | 1 | DONE |
| Successor begin, when eligible | 2 (plus successor lock depth 1) | 0 | 1 | DONE |
| Finalizer return | 1 | 0 | 1 | UNSCHEDULED |
| Just before outstanding decrement | 0 | 0 | 1 | UNSCHEDULED |

Depth means nested calls to the inspected lock/unlock services in this serial
fixture. It does not establish the OS implementation, contention behavior, or
reentrancy guarantees of those services. Successor begin is a stub: whether it
queues work or runs another inline chain depends on its actual job type.

Normal release clears the active list before visiting targets. Its normal-target
loop decrements holds; only a last hold with a pending request reaches the credit
gate. An enabled gate with no positive credit sets deferred; otherwise begin runs
and consumes one credit only when that gate is enabled. The credit-recipient loop
adds a credit and begins only with positive credit, zero holds, a pending request,
and deferred set. It consumes that credit and clears deferred before begin.

The reconstructed scheduler now emits `mixed_dependency_begin_enter` and
`mixed_dependency_begin_return`, including owner state, executions, outstanding
count, target state, and cause (`normal_hold` or `credit`). These are serial model
observations, not native lock events. Tests cover both routes and immediate empty
range finalization, which has zero outstanding dispatches. A finalizer name alone
therefore does not imply that a worker dispatch is completing.

### Next native observation boundary

A one-argument wrapper around callback-job table slot +0x70 can observe finalizer
entry/return. The completion caller returns to RVA `0x11e2dff`; ordinary begin's
empty-work caller returns to `0x11d15e2`. Caller provenance must distinguish these
paths. The inspected callback predicate is false, but a shared-table probe still
must not presume every invocation represents the selected graphics job.

The existing image-slot installer demonstrates guarded compare/exchange and
protection restoration, but its action-vector record format is not a job-state
record. A dedicated adapter should filter the current selected job, forward all
other objects, preserve the original ABI, pin forwarding code, bound records,
and avoid arbitrary plugin calls, logging, or scheduler mutation inside the hook.
Configuration must verify current build, table slot, method, owner and job identity;
restoration must preserve competing slot values. No such finalizer hook has been
installed by this pass.

Crucially, this slot executes under the outer job lock, and its return is still
before the final outstanding decrement. It is useful instrumentation, not an
unlocked mod callback or complete worker-exit notification. A later boundary is
still needed to observe the decrement directly. The two inspected call sites do
not constitute an exhaustive inventory of possible finalizer callers.

## Filtered native finalizer adapter

The authored [finalizer probe](../../native/snow_host/snow_finalizer_probe.c) and
[ABI 1 header](../../native/snow_host/snow_finalizer_probe.h) implement the next
observation adapter. The build produces `snow_finalizer_probe.dll`; it is not an
automatically loaded plugin. A bounded controller and live build fingerprints
remain required before using it in the game.

Configuration qualifies a current owner/global/table relationship, an aligned
nonexecutable image slot at table +0x70, and an executable original target in the
same module as the table and owner global. It pins its module and the original
image. Install rechecks owner/table/slot, changes only the table pointer using
compare/exchange, and restores page protection immediately. Restore changes only
its own pointer (or accepts an already-restored original); a competitor is kept.
No instruction bytes are patched.

The adapter filters the selected `owner +0x218` job. Other objects using the shared
table forward without reserving records or running observation readers. Selected
calls record the return address, entry/exit time, thread, integer result, and
before/after guarded job fields using the existing delegate recorder. In this
adapter `function_storage` is zero and `receiver` is the job, not the engine owner.
The one-pointer integer-result ABI is explicit; it is not a generic virtual-call
wrapper and makes no floating/vector return claim. Clients must check this
adapter's ABI and record size, not infer compatibility from a different probe.

Recording validates the current owner, job table and original/wrapper slot before
and after reading counters. Invalid observations remain zero/invalid while the
original call still forwards. No user callback, output, mutation or control lock
runs inside the dispatch wrapper. The original may hold scheduler locks, and the
read operations add overhead. Guard success is not atomicity or lifetime pinning.

Unlike a heap descriptor, the restored slot lives in a pinned image. Cleanup can
therefore restore the original pointer even if owner identity is lost during the
capture. This does not permit further qualified recording against that owner.
Capture close/drain authorizes copying records only; cached calls still forward,
and the module and recorder must remain resident until process exit. Installation
is one-shot, restoration retryable; restore must be attempted after any install
attempt, including a reported page-protection failure. Concurrent third-party
page-protection changes and OS protection failures are not excluded by the CAS.

The [synthetic fixture](../../tests/fixtures/snow_finalizer_probe_fixture.c) tests
shared-table filtering, full-width forwarding, return-site attribution, state
observation, protection preservation, competing-pointer refusal/retry, owner-loss
cleanup, close-before-install refusal, and heap-table rejection. The selected
synthetic original changes DONE to UNSCHEDULED but intentionally leaves the
outstanding count positive. This models the finalizer boundary; it is not a live
native completion result or an arbitrary mod execution API.

The [Windows/Wine validation receipt](../../native/snow_host/finalizer_probe_fixture_validation.json)
records seven passing synthetic scenarios. No game was launched. The initial
fixture incorrectly assumed the default image-page protection; the corrected
fixture measures and checks preservation of the original value. Fault-injected
OS protection failures and concurrent third-party page changes remain untested.

### Bounded finalizer capture controller

The opt-in [finalizer controller](../../native/snow_host/examples/finalizer_capture.c)
adds a fresh-trigger workflow, three instruction fingerprints (ordinary finalizer,
completion prefix, graphics dispatcher), selected graphics binding checks, a
100..2000 ms capture window, restoration after any install attempt, and a bounded
two-second recorder drain. Installation must return exactly 1; a protection-error
return does not start the capture interval. The module remains pinned.

Output identifies `probe: finalizer` and `record_abi: 1`. Its receiver is the job,
not the engine owner. A controller must validate the complete file, record count,
caller sites, owner continuity, original slot restoration, and continued simulation.
A fresh trigger is not a lock or an owner-lifetime guarantee. This supersedes the
previous missing-controller status; live validation is a separate evidence step.

### First live graphics finalizer capture

The [live finalizer receipt](../../native/snow_host/finalizer_capture_live_validation.json)
records eight selected calls with zero drops and 16 valid before/after observations.
Every return address resolves to RVA `0x11e2dff`, immediately after completion's
virtual finalizer call. Entry had executions 0, outstanding 1, and state 2 (DONE).
Return had executions 0, outstanding 1, and state 0 (UNSCHEDULED). Holds, usage,
and selector were zero throughout. Started/requested matched and advanced
consecutively from 599 through 606.

This closes the live worker-completion-to-finalizer caller join and confirms the
state transition while outstanding accounting remains positive. It does not
observe the later outstanding decrement. Static/serial instruction evidence says
the outer job lock remains held at this return; this session did not instrument
OS lock ownership or dependency-release internals.

The selected job was correctly filtered and the shared slot restored. Subsequent
engine steps advanced from 608 to 611 (596 before capture). The launcher verified
bottle stop, saves/settings restoration, and original DLL. No movement, pause or
debugger was used. The configured 500 ms capture had an observed 700.0507 ms
entry-to-final-exit span; control-thread scheduling can overshoot its deadline.
These bounded loops are not hard real-time capture guarantees. No performance
comparison with prior main-callback captures is warranted.

Together with the separate main-callback capture, the evidence now distinguishes
body entry/return (executions 1, outstanding 1), finalizer entry (0, 1, DONE), and
finalizer return (0, 1, UNSCHEDULED). These were separate sessions, not correlated
records from the same request. Both zero executions and UNSCHEDULED can therefore
coexist with unfinished outstanding-dispatch accounting on the observed path.

## Same-request phase correlation

The authored [correlation API](../../engine/scheduler_capture_correlation.py)
accepts two private envelopes with `session`, `image_base`, and `rows` (the full
JSONL summary followed by records). The session token must be supplied by a
controller that verified the same process and creation identity; the file analyzer
cannot establish that identity itself. The selected owner and QPC frequency must
also match. It supports main recorder ABI 3 and finalizer recorder ABI 1 only.

```sh
python3 -m engine.scheduler_capture_correlation main-envelope.json finalizer-envelope.json
```

Both capture lifecycles must report successful restoration/drain, complete bounded
record counts and zero drops. Every record's storage, receiver and caller must
match the selected binding and decoded return site. Before/after job observations
must be valid and retain one equal started/requested value to supply a correlation
key. Duplicate keys are ambiguous and never paired; invalid or changing keys are
rejected observations. Unmatched window-edge records remain explicit.

For each unique matched request the report exposes observed timestamp order,
thread equality, the gap in common clock ticks, and agreement with the previously
observed accounting progression. Mismatches remain false flags, not silently
removed records. Output omits process identity and raw pointers. Request-sorted
output is not an inferred chronological ordering across counter wrap. Timestamp
order alone does not prove causality, OS-lock ownership, the final outstanding
count decrement, or permission to mutate game state. Owner/request reuse without
an observable duplicate remains a lifetime limitation of the capture guards.

### First joint attempt: disjoint record spans

The [joint attempt receipt](../../native/snow_host/joint_phase_capture_inconclusive.json)
preserves an inconclusive result. Independent trigger files produced 17 main
records (requests 1868..1884) and 56 finalizer records (1885..1940). The analyzer
reported no rejected/ambiguous observations, but zero paired requests and disjoint
observed record spans. No same-request relationship was established. The
`observed_capture_windows_overlap` field compares record timestamp extents; it
is not a measurement of actual installation windows.

Both plugin summaries reported successful restoration and drain, and launcher
cleanup passed. However, the controller asserted a minimum pair count before its
post-capture readback/progress checks, so those checks did not run. The public
receipt distinguishes plugin-reported restoration from live external verification.
A revised controller must perform cleanup/readback before analytical assertions.

The next capture should use a single worker that configures both probes, installs
both, then starts one shared interval and restores both. Independent trigger
files are insufficient synchronization. The correlator must continue preserving
unmatched edges and refusing guessed pairings; increasing the nominal durations
alone would not establish synchronized start.

### Coordinated capture implementation

The [paired controller](../../native/snow_host/examples/scheduler_phase_capture.c)
uses one worker and one trigger. It verifies five code spans and both bindings,
configures both adapters, installs main then finalizer, and starts its interval
only after both report success. It marks the interval with a common QPC start/end,
restores finalizer then main, and closes/drains both within a bounded polling loop.
Every configured adapter receives a restoration attempt even if installation
partially fails. Record windows can include installation/restoration edges, so
records are still correlated rather than assumed to align by row index.

The correlation tool requires matching nonzero shared markers when supplied and
reports `inside_shared_interval` for each pair. Legacy independent captures retain
null for that field. Marker agreement is controller evidence, not a new native
scheduler barrier. Installing/restoring the two hooks is sequential, and control
thread scheduling can still overshoot the configured interval.

The [refusal receipt](../../native/snow_host/paired_capture_fixture_validation.json)
covers disabled configuration, stale trigger, stale output and incompatible
executable. Both refusal outputs report zero interval markers. It does not test
injected partial-install/protection failures. Adapter-level rollback/conflict
checks remain separate evidence. This supersedes the missing coordinated-controller
status; the earlier disjoint-record attempt remains an inconclusive observation.

### Coordinated attempt stopped before activation

The [startup failure receipt](../../native/snow_host/paired_capture_startup_failure.json)
records a distinct failure before probe installation. The navigator observed the
gameplay HUD 37 times; its native world step advanced from 998 to 6898. However,
`player.get` returned `no_player` and `player.bind` returned `player_rejected`
(runtime link invalid), so the player-required readiness gate never completed.
The experiment controller timed out without writing a trigger. Both probes
remained uninstalled. Watchdog/bottle, saves/settings and original DLL cleanup
passed; the navigation outcome itself was failure.

This does not test the coordinated hook implementation. Scheduler-only captures
should have a separately named readiness contract using gameplay HUD, advancing
engine state and current engine/job identity checks. They should not silently
claim player readiness or relax the existing gate for player-dependent work.
The player runtime-link failure remains an independent unresolved observation.

### Scheduler-only readiness contract

The startup navigator now has an explicit `--readiness scheduler` mode. It requires
two consecutive recognized gameplay HUD samples with host readiness, advancing
world steps, and no reported host fault. It never invokes `player.get` or
`player.bind`. Its distinct outcome is `scheduler_ready`, with
`scheduler_native_verified: true` and `gameplay_native_verified: false`; it does
not publish a spawn position. Spawn validation is rejected in this mode.

Default/player readiness remains unchanged. This scheduler gate establishes only
HUD plus host progression; it is not a substitute for current engine-owner/job
identity guards, code fingerprints, hook cleanup or continued-progress checks in
the capture controller. The earlier failed player binding remains unresolved.

### Successful same-request paired capture

The [paired live receipt](../../native/snow_host/paired_capture_live_validation.json)
records 14 main callbacks and 10 finalizers. Ten unique request keys (951..960)
matched; eight complete pairs (952..959) lay within the common marked interval.
Four unmatched main records and two paired boundary records remain explicit.
No observations were rejected or ambiguous, and neither recorder dropped records.
The QPC-marked shared interval was 0.4994697 seconds.

Every matched request had ordered main return then finalizer entry, the same
observed thread, and the expected accounting progression: main entry/return
executions 1, outstanding 1, DONE; finalizer entry executions 0, outstanding 1,
DONE; finalizer return executions 0, outstanding 1, UNSCHEDULED. This is now a
same-request relationship within one verified process/session, rather than a
comparison of separate runs. It still stops before the final outstanding decrement
and does not instrument OS lock ownership or establish a general mutation phase.

The controller independently reread both original bindings and observed engine
steps advance from 963 to 965 after capture (948 before). Launcher cleanup passed
for bottle stop, saves, settings and original DLL. No movement, pause or debugger
was used. Readiness was explicitly `scheduler_ready`; player readiness was not
claimed. The previous player-link rejection is not repaired or explained by this
result, even though the host happened to report a bound player in this session.

This supersedes the missing same-request correlation result. The previous disjoint
record spans and pre-trigger player-readiness failure remain preserved as distinct
failed attempts. Next instrumenting the final decrement requires another boundary;
matching finalizer return to main execution does not make it a drain notification.

## Post-completion observation-site audit

The fully decoded execution wrapper calls completion at RVA `0x11e9a7d`; its
return site is `0x11e9a82`, after the original outstanding decrement. There is no
unconditional virtual callback between that return and the wrapper epilogue.
The worker-array notification path is conditional on a queue-counter change,
and its notification adapter at `0x1c3b570` is further conditional on a negative
old per-worker counter. It cannot be used as a universal dispatch-finished hook.

The wrapper's context-after slot +0x30 and optional diagnostic-end slot +0x60 run
before completion. Hooking them would not observe the missing decrement either.
The new [connected wrapper validation](WORKER_THREAD_CONTEXT.md#executable-normal-return-wrapper-reconstruction)
executes that order and records notification only after local accounting reaches
zero in the supplied serial cases. It does not establish live notification
coverage or a new arbitrary-mod phase.

For a direct observation of every completion, a future probe must cover the actual
completion return boundary (or its caller), with an explicitly validated ABI,
stack/unwind behavior and installation method. Current slot-based probes do not
supply that hook. Conditional notification is a useful separate scheduler signal,
not a substitute that closes the outstanding-decrement observation gap.


## Engine-main observation site

The adapter now exports `SnowDelegateProbe_ConfigureSite(binding, site)` with
fixed `SNOW_DELEGATE_GRAPHICS_MAIN` and `SNOW_DELEGATE_ENGINE_MAIN` choices.
The existing `SnowDelegateProbe_Configure(binding)` still selects graphics.
Record ABI version 3 and record layout are unchanged. An unknown site is refused
without consuming configuration; successful configuration remains one-shot.

| Site | Embedded job | Main descriptor | Invoker slot |
| --- | --- | --- | --- |
| Graphics main | owner +0x218 | owner +0x3b0 | owner +0x3c8 |
| Engine main | owner +0x740 | owner +0x8d8 | owner +0x8f0 |

The engine choice follows the inspected
[BeginEngineFrame command binding](ANIMATION_CONTEXT_RETIREMENT.md#beginengineframe-command-binding).
This callback calls the command executor. Selecting its descriptor is therefore
a way to observe the relevant enclosing phase, not evidence that a submitted
command ran or that the whole physics frame completed. The caller supplies and
validates the selected site's function, table and dispatch identities. The
adapter still requires the masked receiver to equal the descriptor's owner;
a binding with a different receiver is refused rather than guessed.

Both choices apply the same identity checks, invoker-only compare/exchange,
conflict-aware restoration and retained forwarding after recorder close.
Counters are read from the selected job, not always from the graphics job.
The caller must continue to guarantee owner storage lifetime; image pinning does
not retain heap objects. Records are sequential observations, not atomic snapshots.

The [site-extension fixture receipt](../../native/snow_host/delegate_site_fixture_validation.json)
covers six synthetic Windows scenarios for each site under Wine, including
post-call identity invalidation. Run the fixture as
`snow_delegate_probe_fixture.exe <DLL-path> <scenario> engine` for engine-main,
or omit `engine` for the legacy graphics path. The adapter extension itself does not redirect existing controllers or publish
commands to the game. The subsequent opt-in controller and live evidence are
described below.


## Engine-main controller and live observation

The standalone `delegate_capture` plugin now accepts `[capture] site=engine`;
the default remains `graphics`. Invalid names refuse initialization. The summary
identifies the selected site. Each site checks its callback fingerprint as well
as the common invoker and dispatch method before configuration. See
[configuration instructions](../../native/snow_host/BUILD_AND_RUN.md) and the
[five-case controller fixture receipt](../../native/snow_host/delegate_capture_site_fixture_validation.json).
The paired main/finalizer controller still selects graphics.

One [bounded live capture](../../native/snow_host/engine_main_capture_live_validation.json)
installed the engine-main observer and recorded 39 calls with no drops over a
0.4905468-second entry span. Requests 1594 through 1632 were consecutive in entry
order. All before/after observations were valid and equal within each call:
executions=1, outstanding=1, state=2, holds=0, usage=0, selector=0. Call intervals
did not overlap in this capture. This does not establish universal serialization.

The calls were distributed across **two threads**, with 36 on one and 3 on the
other. A callback API should identify the validated engine phase, not promise a
single fixed main thread. Return from the observed body still precedes execution
completion accounting; it is not a drain or unload boundary.

The observer reported successful configuration, installation, restoration and
recorder drain. The bounded launcher stopped normally and verified restored
saves/settings and the original DLL. Readiness was `scheduler_ready`; no movement
input or mod command was sent. This proves the selected callback can be observed
in that session. It does not establish rider gameplay, transition safety, command
manager lifetime or actual command invocation. Heap-owner lifetime remains a
caller prerequisite; no general lifetime exclusion mechanism was added.

The next command experiment must distinguish the enclosing phase from a command's
own invocation and correlate request identity through admission and completion.
The live thread distribution is a constraint on that design, not a reason to
assume the command can run on any arbitrary thread.

## Resident request observation in engine-main

The experimental delegate adapter now accepts one opt-in observation request
through `SnowDelegateProbe_ArmObservation`, after configuration and before any
install attempt. This is our resident wrapper's one-slot request, not a submission
to the game's command manager. The first intercepted engine-main invocation
atomically claims it, samples the command-manager global read-only, forwards the
original invoker, samples again and publishes a returned receipt. Later concurrent
or cached calls continue forwarding without repeating the request.

The receipt identifies request, thread, caller, receiver, descriptor storage and
entry/return ticks. It can be matched to the enclosed normal delegate record.
Read failure is explicit, and pointer equality between two samples is not an
atomic snapshot or lifetime pin. A missing returned receipt is inconclusive: the
request may be pending, executing, or unable to return. No cancellation, exception
recovery, native-queue admission, gameplay write or safe-unload promise is added.
The existing owner-storage prerequisites for installing/restoring the descriptor
remain. Modules and observation storage stay resident through the experiment.

The Windows fixture receipt is
[delegate_request_fixture_validation.json](../../native/snow_host/delegate_request_fixture_validation.json).
It exercises the real compiled adapter under Wine with authored owner/callback
storage: engine request execution/return, graphics refusal, no rearm, and a cached
post-close invocation that does not repeat the request. It does not establish
native phase or manager ownership. The optional plugin setting and private output
format are documented in [build and run](../../native/snow_host/BUILD_AND_RUN.md#one-resident-engine-delegate-observation-request).

### Live one-request result

[Two live session receipts](../../native/snow_host/delegate_request_live_validation.json)
record the request running inside the inspected BeginEngineFrame main-delegate
wrapper, with caller RVA `0x65b223`. Each request bracket encloses exactly one
ordinary delegate entry/return record on the same thread, with valid before/after
job observations. The two manager-pointer reads succeed and agree in each run.
This is a live authored read-only request delivered by interception, not proof of
native command-queue submission.

The first capture contains 50 callback records without loss, but its controller
then used an incorrect job-map key and stopped validation. Its adapter reports
restoration and drain, and process cleanup passed; do not count it as a complete
success. The corrected second controller reads the selected invoker slot directly.
It captures 48 callbacks without loss across three thread IDs, independently
verifies restoration, and observes continued engine progress. Request brackets
last approximately 100.1 and 96.9 microseconds, including instrumentation and the
forwarded original call; these are not uninstrumented engine timing estimates.

The three observed callback threads reinforce that the contract should identify
an engine phase and request, not assume one fixed operating-system thread.
Both sessions close the research bottle and verify saves, settings and the
original DLL. Neither tests map transitions or owner destruction. The manager
pointer remaining equal is an observation, not a lifetime or safe-mutation proof.
