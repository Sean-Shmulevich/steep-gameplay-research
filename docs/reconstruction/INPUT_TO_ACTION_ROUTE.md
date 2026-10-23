# Input polling to world action: registered route

The normal rebuilt graph has a concrete outer dependency route from the input
holder poll to the previously studied world action wrapper. This is a static
registration result with bounded instruction emulation, not a live proof of
which substep consumes which player sample.

```text
StepPreWorlds: vector histories and ownership transitions
  -> Step: rebuild/register world-stage chains when its gate permits
  -> earlier world/engine stages
  -> world PreAI: includes the registered manager refresh route
  -> intervening world/engine stages
  -> AI global-update graph and its terminal
  -> UpdatePadManager: holder cycle and device/service polling
  -> world AI stage: eligible worlds in handle order
  -> AI after-update graph: CoordinatorManagerUpdate and its terminal
  -> world AfterUpdate stage: eligible worlds in handle order
  -> world UpdateAction stage: eligible worlds in handle order
```

Each world stage has a seed and tail. A stage with no eligible worlds has its
seed as its tail. Each included world contributes a conditional wrapper entry
and terminal. The arrows across such a wrapper abbreviate its interior; they
do not prove that the primary body executes. Different stages enumerate the
world handles separately, so mutations between enumerations could change their
membership. The validation below uses stable lists.

## Concrete joins

The engine Step callback registers the following outer edges using ordinary
successor registration, which returns the successor for chained calls:

| Predecessor | Successor |
| --- | --- |
| AI first terminal | UpdatePadManager |
| UpdatePadManager | World AI seed |
| World AI tail | AI second entry |
| AI second terminal | World AfterUpdate seed |
| World AfterUpdate tail | World UpdateAction seed |

The provider is the one already decoded in [AI provider chains](ENGINE_PROVIDER_CHAINS.md).
Its first pair contains global AI work; its second contains CoordinatorManagerUpdate.
This is a receiver-identity join, not a label-based ordering guess.

The three consecutive world-stage builders select these wrappers from each
resolved world.graph:

| Stage | Stage seed/tail offsets | Adapter | Wrapper offset | Setup labels |
| --- | --- | --- | --- | --- |
| World AI | 0x638 / 0x7d0 | 0x8eb580 | 0xc840 | UpdateAIWorldIsPausedBranch / UpdateAIEndNode |
| World AfterUpdate | 0x7d8 / 0x970 | 0x8eb500 | 0xcd38 | AfterUpdateWorldIsPausedBranch / AfterUpdateEndNode |
| World UpdateAction | 0x978 / 0xb10 | 0x8eb5a0 | 0x91d0 | UpdateActionWorldIsPausedBranch / UpdateActionEndNode |

These offsets are evidence anchors for this build. The name AfterUpdate does
not imply end-of-frame completion: its actual registered successor here is the
action stage. The UpdateAction wrapper is the same adapter/graph relation
documented in [action graph integration](ACTION_REARM_CALLER.md).

## What the tests establish

[Three-stage builder validation](../../native/snow_host/input_poll_to_action_chains_validation.json)
executes the original consecutive AI, AfterUpdate and Action builders in 121
cases. Zero through four handles cover resolved, unresolved and resolved-null
worlds. The original adapters, wrapper-link helpers and ordinary registration
wrappers execute; every observed registration, clear receiver and all three
final tails match the expected stage-local chains.

[Outer graph validation](../../native/snow_host/input_poll_to_action_graph_validation.json)
executes 16 relocated original Step registration slices through the Action seed.
The original provider getters and ordinary registration wrappers execute. It
checks six edges including the predecessor-to-AI-entry edge, both terminal
clear receivers and stored first-terminal identity.

Both tests substitute locks and outgoing-list mutation with observations. They
do not execute the original graph, wait for workers, prove callback termination,
or validate concurrent container mutation. The two tests establish the outer
edge identities and per-stage list construction separately; their synthetic
fixtures are not a captured game frame.

## Joining the player route already observed

The inner player route is not an unplaced callback. The earlier
[membership and execution study](MOTION_MEMBERSHIP_OBSERVATION.md#order-against-physicsworldstep)
identified the selected actor in world registry entry 25, gathered into
`Physic::BeforeSimulation`. Its installed thunk calls receiver slot `0x270`,
which selects the player update for that actor. Registry entry 24,
`PreBeforeSimulation`, was empty in that observation.

The registered inner route and its gated consumer are:

```text
world UpdateAction conditional wrapper
  -> active primary physics prerequisites
  -> Physic::PreBeforeSimulation
  -> Physic::BeforeSimulation
       selected actor virtual motion update
         -> activity/controller/motion-enabled gates
         -> motion preparation and post-preparation skip gate
         -> action ingestion, if those gates pass
  -> PhysicsWorldStep
       -> eligible substeps
            -> snow action sampling or the selected override/source branch
```

This expands the relevant part of the wrapper, not all its branches or jobs.
The outer chain above is static registration/emulation evidence. The earlier
live entry/exit study separately recorded 701 requests in a standing state:
all 3,505 receiver calls returned before the matching PhysicsWorldStep callback
entered. The actor entered and returned once per request. These were not live
captures of the newly reconstructed polling chain, nor proof that the actor's
inner ingestion call ran.

The [192-case gate validation](MOTION_MEMBERSHIP_OBSERVATION.md#motion-ingestion-gates-original-instruction-validation)
explains that remaining distinction. Preparation happens before the skip test;
a gate snapshot at outer callback entry cannot establish ingestion execution.
Source callbacks and their sample writes are also already decoded, including
[directional publication](MOTION_MEMBERSHIP_OBSERVATION.md#directional-source-through-action-publication).
The missing result is their invocation and publication timing for the selected
action in the same request, not the existence of a local vector writer.

## Action refresh has a registered callback

A focused offline follow-up connects the reset enumerator to a registered
manager callback. It does not yet identify the registration service's scheduler
job. All addresses here are RVAs in the same analyzed build as the preceding
receipts.

```text
initialization helper, receiver owner
  manager = global_input_manager
  service = owner + 0x10
  register_manager_callbacks(manager, service)
    service.virtual_slot_20(index=0,
        callback=refresh_manager_callback, context=manager)

refresh_manager_callback(manager):
  enter_exclusive_accounting(manager)
  refresh_contexts(manager)
  leave_exclusive_accounting(manager)

refresh_contexts(manager):
  enter_exclusive_accounting(manager)
  for context in manager.context_array:
    copy_three_current_service_flags(context)
    if context.active:
      refresh_context_preamble(context.source)
      for group in context.three_groups:
        for binding in reverse(group.bindings):
          reset_and_evaluate_actions(binding.map)
          if binding.blocker and binding.blocker.enabled:
            break   # next group, not end of all contexts
  leave_exclusive_accounting(manager)
```

The initialization call at `0x458e78` passes the manager loaded from global
`0x312bb00`, the same global used by motion ingestion. Registration routine
`0x4ba730` builds a callable for `0x4b4ba0` and passes it to the supplied
service's virtual slot `0x20`, with index zero. The callable retains the manager
receiver and uses invoker `0x43f5b0`. Two other callbacks are registered by that
routine through different slots; their presence does not establish invocation
order.

The registered callback calls `0x4d0290`, which enumerates manager contexts
using the count at `+0x2a` and array at `+0x20`. Active contexts visit the three
groups at `+0x90`, stride `0xc`. Each selected binding supplies its map at
`+0x28` to `0x4b69b0`. That enumerator clears sample fields and dispatches the
stored action's virtual slot `0x10`, matching the earlier
[reset and repopulation study](ACTION_RESET_CALLBACK.md). This closes a callback
registration-to-writer route independently of binding insertion/removal.

[Registration validation](../../native/snow_host/action_refresh_registration_validation.json)
executes the complete original registration routine in 12 cases, varying three
manager identities and all four initial context tag combinations. All three
outgoing callable arguments, indices, manager contexts and invokers match. The
service's three virtual registration methods are substituted with argument
observers. Thus the test validates construction and handoff, not storage,
invocation, locking under contention or sample freshness.

### Concrete service storage

The owner constructor at `0x444f20` installs primary table `0x1e67338`
and a secondary service table `0x1e67420` at `owner+0x10`. The primary table
contains initialization method `0x47bdc0`, whose tail calls the initialization
helper described above. This joins the service receiver to a constructed type;
its semantic class name has not been established here.

Secondary slot `0x20` selects leaf `0x4ba3d0`. It copies all 32 callable bytes
into `service+0x2b0+32*sign_extend(index)`. Because service is `owner+0x10`
and this registration supplies index zero, the refresh callable resides at
`owner+0x2c0`. This is a fixed indexed slot, not an appended callback list.
The copy preserves the source callable and does not check bounds or lock.
Do not expose arbitrary indices as a safe native mod API.

```text
register_fixed_refresh(service, index, callable):
    destination = service + 0x2b0 + 32 * sign_extend_32(index)
    copy_16_bytes(destination, callable)
    copy_16_bytes(destination + 16, callable + 16)
```

The record contains callback, auxiliary qword, tagged manager context and
invoker. Registration clears context tag bit zero and preserves bit one.
The stored invoker `0x43f5b0` forwards the supplied receiver to the callback
and moves the supplied float argument into its expected argument register.
That invoker alone does not identify where or how often the slot is invoked.

[Original storage validation](../../native/snow_host/action_refresh_storage_validation.json)
repeats the 12 complete registration cases with the original slot-zero and
slot-`0x20` storage methods executing. It checks both stored records, including
the refresh callable at owner-relative `+0x2c0`. Only the third registration,
through slot `0x48`, remains an observer substitution. Constructor table
binding is static evidence; full owner construction and callback execution were
not emulated.

The next target is the consumer of this exact fixed slot, followed by that
consumer's scheduler binding. Its placement in UpdatePadManager, UpdateAction,
or another stage remains open. Index zero and the surrounding lifecycle
callbacks do not establish a frame cadence.

## Fixed refresh slot transfers to the attached world service

The fixed slot has a concrete transfer consumer. Helper `0x4c5910` reads
`owner+0x18`, then obtains the attached world's service from `world+0xff8`.
It passes six callable records beginning at `owner+0x2c0` to service category
4 through `0x695af0`. Thus the refresh callback registered at fixed index zero
is one of the records considered for that world's callback storage. This is a
storage join, not yet its execution site.

The helper is called by `0x4c8070`. That caller requires a nonnull attached
world and a zero owner byte at `+0x20`; it sets that byte to one before transfer.
The inspected route therefore performs setup on that transition. It does not
copy the callbacks afresh on every physics substep. Other callers and lifecycle
transitions must be considered before inferring when registration can change.

```text
transfer_fixed_callbacks(service, category, source, count):
    descriptor = service + 0x30 + 12 * category
    descriptor.count = 0
    for i in descending(count - 1, 0):
        record = source[i]                 # 32 bytes
        if (record.tagged_context & ~3) != 0 or record.callback != null:
            reserve_if_needed(descriptor)
            append_copy_of_32_bytes(descriptor, record)
```

The clearing wrapper is `0x695af0`, which tail-calls `0x655e40`. For category
4 the destination descriptor is `service+0x60` and its uint16 count is at
`+0x6a`. It retains existing capacity while resetting the count. The source
callables remain unchanged. A record with only tag bits set and a null callback
is skipped even if its invoker field is nonnull. A null callback with a nonnull
masked context is retained; that is the observed eligibility test, not a claim
that every such synthetic record would be safe to invoke.

[Transfer validation](../../native/snow_host/action_refresh_world_transfer_validation.json)
executes both original routines with capacity for six records. All 64 presence
patterns pass for callback-only, context-only and combined populated records,
for 192 cases without call substitutions. The checks cover reverse order,
count reset, exact 32-byte copies, unchanged source records and untouched
unused destination bytes. Capacity growth and concurrent mutation are outside
this validation.

The remaining static target is the consumer of category 4 in this particular
world service. A global AI provider also has callback lists, but that similarity
does not establish receiver identity or scheduler placement. Follow the
`world+0xff8` service and category-4 descriptor before joining it to a named job.

## Category 4 reaches a concrete callback worker

World construction stores the result of factory `0x6595f0` at `world+0xff8`.
Its constructor `0x644a20` installs table `0x1e89d98`. Service initialization
`0x658f30` constructs a separate job owner through `0x644ee0`, stores it at
`service+0xf8`, and assigns `job_owner+0x18f8 = service+0x30`. That last
assignment is the exact descriptor-base join to the category-4 storage above.

Setup routine `0x69da40` installs callback `0x698cd0` in the job at
`job_owner+0x2a60`, with the job owner as context. Its labels are
`SetupUpdateAIManagersBeforeAI` and `Ai::UpdateAIManagersBeforeAI`.
The callback gathers category 4 and then category 5 through `0x643ba0`.
This identifies a concrete setup callback, rather than assuming that all
similarly named AI jobs use the same provider.

```text
setup_before_ai(job_owner):
    gather(category=4, descriptors=job_owner.callback_descriptors)
    gather(category=5, descriptors=job_owner.callback_descriptors)

gather(category, descriptors):
    source = descriptors[category]
    if source.count == 0: return
    job = job_owner + 8 + category * 0x1c8
    ensure_capacity_if_needed(job, source.count)
    append_copies(job.records, source.records, source.count)
    job.record_count += source.count
    activate_or_notify_job(job, source.count)
```

The copy helper appends to the existing job count. It does not reset that count
in this routine. Empty source leaves the job untouched and does not invoke the
activation helper. Repeated setup therefore needs the separate job-reset and
completion protocol; this local pseudocode must not be used as a free-standing
frame loop. Capacity growth and concurrent append safety require their own
validation.

The constructor installs range-job table `0x1e92b40` for the fourteen category
jobs. Its worker slot `0x80` resolves to `0x67d690`. Within a supplied range it
obtains a float from job slot `0x88`, visits records in descending index order,
clears the context's low two tag bits and calls each record's invoker. The
refresh record's invoker `0x43f5b0` then dispatches `0x4b4ba0` with the manager
as receiver. This connects the stored action-refresh record to an executable
worker route. It does not prove that the selected player's action refresh ran
in any particular live request.

[Composed validation](../../native/snow_host/action_refresh_job_validation.json)
executes the original category-4/5 setup callback, gather copy, range worker
and callable invoker for all 49 count pairs from zero through six. It checks
record copies, counts, activation arguments, reverse worker order, untagged
receivers and exact float32 argument forwarding. Job activation is observed
rather than scheduled, the clock returns a supplied value and the final action
callback records arguments. Job counts begin at zero and capacity is supplied.
No actual engine threads or action evaluators run in this test.

The earlier transfer reverses source slots and the worker reverses its supplied
range. These reversals do not prove globally ascending registration order when
real scheduling divides the work into multiple ranges. Likewise, the setup
label does not establish its complete predecessor chain. The next target is
this job owner's graph registration and category-job completion/reset path,
joined through the concrete service table to the outer world AI stage.

## Callback count is unclaimed work, not completion

The category-job table's slot `0x40` selects `0x65b050`. That method atomically
claims records by reducing `job+0x1a0` before invoking worker slot `0x80`.
This supplies the missing local explanation for why the gather routine's
append count can return to zero without clearing the retained backing array.
It is a remaining-work counter, not an immutable list length or completion
counter.

For the inspected nonnegative counts, positive chunk size and nonoverflowing
threshold arithmetic, the claim rule is:

```text
remaining = job.remaining
repeat:
    if remaining > job.tail_threshold:
        next = max(job.tail_threshold, remaining - job.chunk_size)
    elif remaining > 0:
        next = remaining - 1
    else:
        return no_claim
    observed = compare_exchange(job.remaining, remaining, next)
    if observed == remaining:
        return records[next:remaining]
    remaining = observed
```

The original instructions use signed 32-bit comparisons and arithmetic. The
pseudocode's domain avoids overflow; it is not a replacement for those rules
on malformed configuration. Each successful claim names a suffix of the
remaining prefix. The worker visits that supplied range in descending order.

The method calls an optional pre-hook once before its first range. It attempts
further claims while the inspected global generation value remains unchanged
and its optional yield gate does not request an exit. It calls its optional
post-hook after this processing. The configured category hooks set and clear
a thread-local world context; they are not the record-count reset mechanism.
An early exit can leave unclaimed work. A successful last claim can make the
count zero while its callback body is still running. Scheduler execution and
completion accounting remain necessary before reusing the job's storage.

[Drain validation](../../native/snow_host/action_refresh_drain_validation.json)
extends the earlier gather/worker test through the original complete claim
method. All 294 combinations pass: two categories for each of 49 count pairs,
with chunk sizes 1, 2 and 6 and tail threshold 1. Each drain checks callback
order and remaining count, then invokes the drained method again and confirms
that retained records are not executed. Activation, clock and final callback
substitutions remain explicit. This test is single-threaded, uses empty
pre/post hooks and a stable generation, and does not exercise CAS contention,
early yield or completion barriers.

The pair setup helper `0x699140`, called with category 4 and setup job
`job_owner+0x2a60`, registers setup -> category 4. Its call into `0x643f90`
registers category 4 -> category 5. The supplied terminal is null on this
setup call. Separately, service slot `0x50`, method `0x675660`, links an
external predecessor to that setup job and returns category 5 at
`job_owner+0x8f0`. These are inspected registration relations. The caller of
that service method must still be joined before claiming a complete outer
poll-to-refresh dependency chain.

## Refresh belongs to the upstream world PreAI route

The service slot-`0x50` caller is world-graph setup `0x908ae0`, at callsite
`0x908e10`. This routine obtains the service from the same world's `+0xff8`.
It connects world graph job `+0x390` to the service's before-AI setup job and
connects the returned category-5 terminal to world graph job `+0x558`.
The latter job already precedes the wrapper terminal at `graph+0xc6a8`.
The graph's wrapper is at `+0xc698`; its setup labels include
`UpdatePreAIGather`, `Ai::UpdatePreAI`, and `Ai::UpdatePreAISingleThreaded`.

```text
world PreAI wrapper entry
  -> gather and prerequisite jobs
  -> world graph +0x390
  -> service before-AI setup
  -> service category 4: includes manager refresh
  -> service category 5
  -> world graph +0x558
  -> world PreAI terminal
```

This diagram shows the relevant registered dependencies, not every incoming
hold or conditional branch. The primary work must be selected and all other
prerequisites released for its callbacks to execute.

Adapter `0x8eb640` links `world.graph+0xc698` into the outer world chain.
Builder slice `0x68a6d8..0x68a738` uses stage seed `+0x2f8`, tail `+0x490`
and the same signed-handle eligibility and list-order fold as the later world
stages. The Step registration then connects that tail to stage seed `+0x14d8`.
That stage's tail at `+0x1670` precedes engine job `+0x1f18`, which precedes
the global AI provider entry. The previously validated global AI terminal
precedes UpdatePadManager.

[Extended outer graph validation](../../native/snow_host/input_pre_ai_to_poll_graph_validation.json)
executes the original Step slice `0x69c786..0x69c8ac` in 16 relocated fixtures.
It verifies eight outer registration edges through the Action seed, with
locks and list mutations substituted as in the preceding graph tests. The
PreAI interior and intervening world's stage interior are static joins, not
executed by this test. Actual job dispatch is not exercised.

The consequence is narrower than a latency measurement: this registered
manager-refresh route is upstream of the named pad poll on the ordinary stage
chain. The earlier post-pad world-AI-to-Action route remains valid, but it must
not be used to place this particular action writer after polling. Additional
polling calls, binding-triggered refresh and other writers remain possible.
There is no established universal one-frame delay or one-poll-per-refresh rule.

The next live capture should explicitly distinguish the PreAI refresh from
UpdatePadManager and downstream ingestion. It must record the selected action's
actual evaluation and sampled values; stage order alone does not establish
which cached device sample was used.

## Composed PreAI registration validation

[Complete PreAI setup validation](../../native/snow_host/action_refresh_preai_graph_validation.json)
now executes original setup `0x908ae0` in sixteen relocated fixtures, including
original service bridges `0x6757a0` and `0x675660`. It observes all eight
registered edges and both terminal-clear receivers. Sixteen additional fixtures
execute complete category-pair setup `0x699140` and its helper `0x643f90`,
confirming setup -> category 4 -> category 5. The original name/configuration
setters execute. Only lock and outgoing-list operations are substituted by
observers. These 32 cases strengthen the earlier static interior join; they do
not execute the assembled graph.

Category-4 metadata selects the special range configuration. Original setup
calls the chunk setter with `0x7fffffff`, leaves the tail threshold at zero,
and assigns the clock pointer `world+0x1048`. Under the decoded claim rule,
a positive valid signed count fits in one maximal claim. This is more specific
than the generic small-chunk drain tests. Combined with descending source
transfer and descending worker traversal, a stable initial category-4 list is
visited in ascending source-slot order within that claim. This conclusion
requires no concurrent population change, no additional appended records and
successful callback return. It is not a global ordering guarantee for other
categories or registration paths.

The supplied fixtures use the constructor-supported service/range tables and
ordinary successor nodes. Full construction, conditional execution, concurrent
claims, original clock evaluation and live callback bodies remain outside this
test. A count of zero is still only evidence that no records remain unclaimed;
the maximal claim reduces it before running any action callbacks.

## The callback interval and ramp clock are separate reads

The category-job table's slot `0x88` selects accessor `0x66e4c0`:

```text
callback_interval(job):
    clock = job.clock_pointer
    return clock.interval if clock != null else +0.0
```

It loads the pointer at job `+0x1c0`, then copies the float32 at clock `+0x18`
without arithmetic or filtering. Category-4 setup supplies `world+0x1048`,
so this is the ordinary world interval at `world+0x1060`. The
[existing world-clock producer](WORLD_CLOCK.md) derives it as
`f32(processed_input_ms / 1000)`. Seconds are supported by that producer's
arithmetic; this accessor does not compute a physics-substep interval.

The worker reads the interval once before traversing its supplied record range.
The callable invoker moves it into the callee's second argument register.
The registered manager callback `0x4b4ba0` does not read that register: its
inspected body performs exclusive accounting and calls the context-refresh
routine using the manager receiver. Therefore this argument's presence alone
does not establish how source processors measure time.

In particular, the [directional ramp clock producer](MOTION_MEMBERSHIP_OBSERVATION.md#ramp-clock-producer-joins-the-existing-clock-tree)
uses a separately selected object's divided ticks at clock `+8`, converted to
seconds and differenced against a saved value. It does not use this callback's
float interval. The two paths have distinct read sites and rounding behavior;
their live selected-world identities must be observed before assuming equality.

[Clock forwarding validation](../../native/snow_host/action_refresh_clock_validation.json)
removes the clock-method substitution from the earlier 49-case composed
setup/worker test. Original accessor, worker and invoker preserve positive and
negative zero, ordinary finite values, negative values, infinity and a NaN
payload at the final recording callback. Null clock returns positive zero.
These are controlled bit-pattern fixtures, not observed gameplay intervals.
Activation and the final callback remain substituted; original clock updates
and action-source timing do not run in this test.

For a future capture, record the callback clock identity and interval separately
from the ramp's selected clock identity, divided ticks and saved ramp value.
Neither quantity is an action-publication generation or proof of sample age.

## Next capture contract

Once live access is available, extend the existing request/substep recorder
rather than repeating the membership experiment. This is a proposed experiment,
not a recovered engine interface or a completed capture.

| Event | Correlation and value to record | Question answered |
| --- | --- | --- |
| Named pad task return | holder/cache identity, request context if available, monotonic event sequence | Which completed poll precedes the consumer? |
| Selected action evaluation return | action identity and processed sample, caller identity, thread and sequence | Did this action callback publish, and from which caller? |
| Actual ingestion entry/return | actor/motion/action identity, request, consumed values | Did the inner call run despite its gates? |
| Snow sampling within a substep | same world/request, substep ordinal, source branch and sampled value | Does snow read that action again or use an override? |

Callback return is an observation point, not an atomic publication guarantee.
Instrument the proven sample-writing sites if nested callbacks or concurrent
writes make a return observation ambiguous. A recorder sequence is our event
ordering aid; it must not be presented as an original sample-generation field.
Matching values alone cannot distinguish a fresh equal sample from an old one.
Retain dropped-record counts and reject completeness claims for incomplete
windows. Preserve receiver identity checks and callback restoration safeguards.

## Remaining input-to-physics questions

- Which UpdateAction receivers evaluate the active player's source chain, and
  which producer publishes its motion input?
- Where that publication lies relative to each physics substep, including
  multi-substep frames and paused/bypass routes.
- Whether another polling call updates the cache between the named task and a
  consumer. The conditional direct polling route still exists.
- Whether the selected world and actor match the outer stage and inner batch
  in a new correlated capture. Earlier membership proves one observed state,
  not every rebuilt list.
- The world AfterUpdate interior and any additional side effects between polling
  and Action. Its name and wrapper offset do not answer this.

This route supports targeting the named pad task and downstream action boundary
for a future shared-sequence capture. It does not yet support a claim of exact
frame-by-frame replay, a universal one-poll-per-substep rule, or safe arbitrary
scheduler mutation. Detailed instruction findings remain in
[input update order](INPUT_UPDATE_ORDER.md).


## Runnable local refresh reconstruction

[`engine.action_refresh`](../../engine/action_refresh.py) now exposes two independent
adapters for the decoded local behavior. `reset_action` accepts an immutable byte
snapshot, a caller-resolved owner suppression gate, and an explicit source evaluator.
It clears offsets 0x60 through 0x83 before evaluation, preserving status, raw input,
and all other bytes. A suppressed owner still permits the clearing but prevents
evaluation. The evaluator can immediately repopulate samples. Returning a copy is
our API design; the native routine mutates its action in place.

`refresh_groups` visits exactly three stable groups in forward order, visiting
bindings within each group in reverse order. It resets a binding before reading
its blocker; a blocker stops only that group's walk. Callers supply binding-map
enumeration, concrete source evaluation, active-context selection, preamble and
manager synchronization. Structural list mutation during traversal is not modeled.
These rules come from [the reset and group walk](ACTION_PUBLICATION_FOLLOWUP.md#the-reset-reaches-the-sampled-vector)
and [concrete callback research](ACTION_RESET_CALLBACK.md).

```python
from engine.action_refresh import reset_action, refresh_groups

# Synthetic example: the caller supplies the source evaluator and binding order.
actions = {"steer": bytes(160)}
def reset_binding(name):
    actions[name] = reset_action(
        actions[name], owner_suppressed=False, evaluate=lambda cleared: cleared)

refresh_groups([["steer"], [], []], reset_binding=reset_binding,
               blocker_enabled=lambda name: False)
```

The identity evaluator above is solely an example. It does not reproduce the
native source evaluators or device caches.

The [differential receipt](../../native/snow_host/action_reset_adapter_validation.json)
records 72 comparisons against the complete original reset routine. Each compares
all 160 synthetic action bytes and the callback-entry snapshot. Fixtures vary
initial byte patterns, status, absent/present owner, suppression byte and callback
repopulation. Tagged-map enumeration and the virtual evaluator were substituted;
original reset stores and owner gating executed in instruction emulation.
Three-group ordering, callback-dependent blocking, duplicate binding identity and
error propagation have separate unit tests. This is not native differential proof
of group traversal, live scheduler execution or input freshness.

Run the portable tests without game files:

```sh
python3 -m unittest discover -s tests -p test_engine_action_refresh.py
```


## Category activation joins the common range lifecycle

The category-4 table `0x1e92b40` binds the same ordinary begin (`0x11d1540`),
empty predicate (`0x8eb040`) and finalizer (`0x11d1670`) described in
[range begin behavior](SCHEDULER_BEGIN_PATHS.md) and
[ordinary completion](SCHEDULER_REARM.md). This is a concrete table join;
it does not depend on naming this object an animation job.

The previously substituted activation helper `0x8c12d0` locks the job and reads
its dependency-hold field before selecting a path:

```text
activate_category(job):
    enter_scope()
    lock(job)
    if job.dependency_holds == 0:
        if job.state == 0 or job.state == 2:
            job.ordinary_begin()
        elif job.state == 1:
            wake_scheduler_workers()
    unlock(job)
    leave_scope()
```

`ordinary_begin` acknowledges the requested generation and activates outgoing
dependencies before testing signed remaining count. Positive remaining count
queues the job. Nonpositive count takes the immediate ordinary-finalizer route.
The existing scheduled-state path only wakes workers through the inspected
helper; it does not call the range worker directly or repopulate its array.
The wake helper enumerates scheduler workers, updates each wake-state counter
atomically and signals workers whose prior counter was negative.

The [activation receipt](../../native/snow_host/action_refresh_activation_validation.json)
records 48 composed instruction-emulation cases executing the original activation,
begin, empty predicate and finalizer using the category table. Synthetic holds,
states and remaining counts select each local branch. Locking, scope helpers,
queue insertion, dependency effects and worker wake are substituted. Thus this
extends the earlier gather tests' activation boundary, but does not execute a
real dependency graph or dispatch a worker. Negative remaining count and state 3
are branch probes, not claims that these represent valid workloads.

This narrows the remaining completion question. The category job shares the
ordinary lifecycle, whose established dispatch accounting separates exhausted
claims from returned worker bodies. We still need a composed category-specific
worker/completion check and the next-request graph barrier before claiming its
callback storage is safe to reuse. A direct call to its finalizer is not a safe
mod API: the finalizer itself does not check for active worker bodies.


## Category worker return and dependency release

The generic execution wrapper `0x11e9990` calls the job's slot 0x40, restores
its execution context, then calls completion `0x11e2d70`. With the concrete
category table, that slot reaches the decoded claim worker `0x65b050` and
callback visitor `0x67d690`. Completion reaches the same table's empty predicate
and finalizer. This joins the category route to the previously documented
[ordinary completion protocol](SCHEDULER_REARM.md#completion-separates-empty-work-from-finished-callbacks).

```text
execute_reserved_category_dispatch(job):
    install_execution_context()
    job.claim_and_execute_callback_ranges()
    restore_execution_context()
    atomic_decrement(job.executions)
    if job.state == SCHEDULED and job.remaining <= 0:
        lock(job)
        if job.state == SCHEDULED and job.remaining <= 0:
            remove_from_scheduler_and_mark_done(job)
        unlock(job)
    if job.state == DONE:
        lock(job)
        if job.state == DONE and job.executions == 0:
            job.ordinary_finalize()  # releases active outgoing dependencies
        unlock(job)
    atomic_decrement(job.outstanding_dispatches)
```

Execution and outstanding counters are at job+0x4c and +0x50, respectively.
They must already account for reserved dispatches before this wrapper runs.
The pseudocode abbreviates native nested locking and profiling. It is not a
standalone lock implementation or permission to call the finalizer directly.

The [composed receipt](../../native/snow_host/action_refresh_completion_validation.json)
records 21 cases: zero through six callbacks, with one through three pre-reserved
dispatches. Original wrapper, range claiming, callback visitor, invoker, clock
getter, completion, done transition and finalizer execute together. Locks,
queue removal, successor release and final action callbacks are substituted.
The test serially returns each reserved dispatch; it does not emulate concurrent
worker interleavings.

All callbacks observe remaining count zero while execution and outstanding counts
still include every reserved dispatch. Earlier returns can mark the job done,
but release occurs only on the final return. At the release hook, executions is
zero and outstanding dispatches is one. The final outstanding decrement follows
release, leaving both counters zero when the wrapper returns.

These results close the composed local worker/completion check. They do not prove
that the next gather waits on this category's completion in every mode, that no
other code accesses its storage, or that a live snapshot is atomic. The next
storage-lifetime question is the graph path from this request's completion to
permission to gather the next request.


## Ordinary rearm argument and runnable refresh probe

The remaining lifetime question can reuse the existing
[EndFrame dependency research](ENGINE_LOOP_HANDSHAKE.md). The category-4/5
terminal feeds the world PreAI terminal, whose outer chain precedes the named
pad poll and the later Action stage. The established Action-to-EndFrame chain
then precedes dependency preparation and ordinary root resubmission:

```text
category 4 worker bodies return
  -> category 4 releases category 5
  -> world PreAI terminal
  -> outer PreAI tail and intervening stages
  -> pad poll and later Action stage
  -> Action terminal and downstream frame joins
  -> EndFrame callback prepares links and submits next ordinary root
  -> next eligible Step path can gather again
```

This is an inference joining the documented ordinary graph edges and completion
rules. It is stronger than treating the next gather as an unidentified external
call, but remains conditional on those routes being selected. It is not a newly
executed whole-frame graph or a universal exclusion proof. Alternate release,
startup/event submission, direct service calls, dynamic world membership and
concurrent external mutation remain outside this argument. EndFrame can submit
the next root before its own wrapper returns; global engine idleness is not
required by this narrower callback-storage ordering.

A portable composition now runs the recovered partial chain
`BeforeAISetup -> Category4 -> Category5 -> PreAISingleThreaded -> PreAITerminal`
with the independent scheduler and action-reset adapter:

```sh
python3 -m engine.examples.action_refresh_probe
python3 -m unittest discover -s tests -p test_action_refresh_probe.py
```

The [probe](../../engine/examples/action_refresh_probe.py) supplies synthetic
populations and a constant source evaluator. It reserves two dispatches before
claiming the single manager callback. Remaining count becomes zero immediately,
but category 5 stays blocked after the first return and starts only after the
second reservation returns. The next request suppresses evaluation and clears
the first request's sample. Tests assert these transitions and callback ordering.

The harness resubmits after the partial terminal; it does not implement or test
the native EndFrame graph. Two reservations, the serial execution order and the
bounded maximal chunk size are fixture choices. Omitted incoming dependencies
and source evaluators must not be inferred from this example. The useful next
live evidence remains correlated request identity, category completion and the
next gather on the actual selected world, once game access is available.
