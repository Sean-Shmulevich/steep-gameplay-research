# Input polling to world action: registered route

The normal rebuilt graph has a concrete outer dependency route from the input
holder poll to the previously studied world action wrapper. This is a static
registration result with bounded instruction emulation, not a live proof of
which substep consumes which player sample.

## Current reconstruction boundary

The sections below retain the evidence trail, including earlier questions that
later sections resolve. Current conclusions are:

| Part | Established scope | Remaining boundary |
| --- | --- | --- |
| Registration and placement | Manager refresh stored in category 4; concrete worker and world PreAI edges identified | Live selected-world/request identity and additional refresh paths |
| Claim and callback execution | Original worker, visitor, clock and invoker execute in bounded composed tests | Actual source evaluator/device-cache freshness |
| Completion and successors | Original completion/release gates tested; independent successor model matches semantic fixtures | Native locks, real simultaneous threads, exceptional paths |
| Claim contention | Saved CPU contexts exercise actual failed CAS and retry with shared job memory | Hardware memory ordering and dynamic reservation races |
| Next request | Conditional ordinary graph argument joins PreAI through Action to EndFrame | Full graph execution, alternate modes, external mutators |
| Runnable reconstruction | Reset/traversal adapters and two-request scheduler probe | Native map enumeration, complete context/evaluator integration |

Thus local category execution is no longer an unidentified scheduler connection.
The highest-value live check is a correlated request trace from actual manager
evaluation through player ingestion, with completion and next-gather identity.
Local tests cannot establish the age of the device sample being consumed.

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


## Original release into the next category

The [successor-release receipt](../../native/snow_host/action_refresh_successor_validation.json)
extends the composed category completion test by executing original ordinary
release `0x11e7ba0`, rather than replacing it with a recorder. The synthetic
outgoing list contains a second job with the same concrete category table.
Its ordinary begin, empty predicate, outgoing activation and empty finalization
also execute. Queue insertion/removal, locks and final action callbacks remain
substituted. Registration itself is tested separately; this fixture directly
constructs the successor list.

The ordinary successor loop follows these decisions:

```text
if outgoing.active != 1:
    return
outgoing.active = 0
for successor in outgoing.normal_successors:
    prior_holds = atomic_decrement_return_old(successor.holds)
    if prior_holds == 1:
        lock(successor)
        if successor.started != successor.requested:
            if successor.credit_gate and successor.credits <= 0:
                successor.deferred = 1
            else:
                if successor.credit_gate:
                    atomic_decrement(successor.credits)
                successor.begin()
        unlock(successor)
# A separate credit-recipient loop follows; excluded from this fixture.
```

There are 144 cases combining zero/one/six predecessor callbacks, one/two
pre-reserved dispatches, one/two initial successor holds, matching/pending
request counters, three credit configurations and empty/nonempty successor
ranges. Before the final dispatch return, the successor's holds and started
counter remain unchanged. Final release decrements one hold. Begin occurs only
when that decrement removes the final hold, a request is pending and credit
permits it. A permitted empty successor finalizes immediately; a nonempty one
is queued. An enabled gate without credit sets the deferred flag.

These gate fixtures test local branch behavior, not a claim that category 5
uses credit gating in the observed configuration. Credit-recipient lists are
empty, alternate release is excluded, and no native concurrency is exercised.
This removes the ordinary successor-release substitution from the tested
worker/completion chain. It still does not execute the complete PreAI graph,
the next gather, or actual source evaluation.


## Portable differential successor fixtures

The 144 native successor cases contain 24 distinct successor input/output
combinations. Their decoded synthetic state is retained in
[portable fixtures](../../tests/fixtures/action_refresh_successor.json), with no
original object bytes, addresses or game payloads. Outcomes are collected from
the emulated original instructions; duplicates across predecessor callback and
reservation counts must agree before export.

[The regression test](../../tests/test_action_refresh_successor_native.py) seeds
the independent mixed scheduler at the ordinary-release boundary, then executes
its release and concrete range begin. It compares hold/request/started counts,
credit/deferred state, lifecycle state, queue membership and source-list clearing.
All 24 outcomes match without a runtime change.

```sh
python3 -m unittest discover -s tests -p test_action_refresh_successor_native.py
```

Private model-state seeding in this test is deliberate and limited to fixture
construction. It is not a public mod API. The portable test validates the
release/begin portion, not the original worker/completion path, native locking,
reservation accounting or a complete frame. Those have separately stated
validation scopes above.


## Controlled overlap of dispatch lifetimes

The [interleaving receipt](../../native/snow_host/action_refresh_interleaving_validation.json)
records 18 controlled instruction-emulation cases. A first original execution
wrapper is stopped at one of three boundaries: final action callback entry,
visitor return, or immediately before dispatch completion. Its CPU context and
stack are retained while one or two other pre-reserved dispatches run against
the same job memory on separate stacks. The first context is then restored.

The first dispatch has claimed the whole range before each pause. Other
dispatches find no remaining work and can transition the job to done, but the
retained first execution keeps the execution count at one. No dependency release
occurs during those other returns. Resuming the first dispatch completes each
callback exactly once and then releases dependencies with executions zero and
outstanding dispatches one. The wrapper finally leaves both counters zero.

This exercises overlapping dispatch lifetimes, including another worker returning
while the first has not yet evaluated its action callback. It goes beyond the
previous serial-return fixtures, but does not execute simultaneous native
threads. Lock calls are no-ops, switches occur outside lock regions, queue removal
and dependency release are substituted, and synthetic TLS has no active context
instrumentation. CAS contention, memory ordering and dynamic queue reservation
are not validated.

[The portable model test](../../tests/test_action_refresh_interleaving.py) reproduces
the corresponding observable schedules in the independent scheduler. Its
before-body boundary represents native callback entry; the two post-body native
boundaries share one model representation because the model does not reproduce
wrapper instructions. It compares remaining counts, done-versus-returned state,
retained execution count, callback identity/order and successor readiness.

```sh
python3 -m unittest discover -s tests -p test_action_refresh_interleaving.py
```


## Stale claim retry under controlled contention

The [claim-contention receipt](../../native/snow_host/action_refresh_claim_contention_validation.json)
records eight original-instruction interleavings. A dispatch stops immediately
before either its initial or subsequent `lock cmpxchg`, retaining a positive
expected remaining count in its CPU context. Another pre-reserved dispatch runs
against shared memory, claims the remaining callbacks and returns. Restoring the
first context makes its stale compare-and-swap fail naturally; the fixture does
not force the flags or patch the instruction result.

Both retry branches load the observed count returned by CAS. With that count now
zero, the stale dispatch performs no duplicate callbacks and returns through
normal completion. Every callback executes exactly once, in the expected order
for these fixtures, and successors release only after both dispatches return.
The test covers one/three/six callbacks with maximal chunk or chunk one, plus
subsequent-claim failures with three/six callbacks at chunk one. Chunk one is a
synthetic configuration probe; the decoded category setup uses maximal chunk.

This is evidence for the original claim retry instructions under controlled
interleaving. It is not a hardware memory-model test, lock-contention test,
concurrent registration test or exhaustive schedule exploration. The independent
serial scheduler has no instruction-level CAS failure representation; no claim
is made that its ordinary unit tests reproduce that instruction mechanism.


## Vector-source refresh adapter

[`refresh_vector_action`](../../engine/vector_action_refresh.py) composes the
existing reset, source-selection and publication kernels for the vector-source
subtype. It accepts explicit source configuration, ownership predicates,
vector/scalar providers and a processor callback. It does not silently choose a
processor, map a physical device or query the live game.

The adapter preserves the decoded order: reset, optional-owner suppression,
configuration presence, selected-source ownership/read, lane selection, optional
processing, then raw/sample/direction/magnitude/status publication. Source blocking
supplies zero but does not bypass processing. Missing configuration returns after
reset, retaining previous raw input and status while sample/direction/magnitude
remain cleared. The published sample retains analog amplitude; normalization
applies to the separate direction field.

The vector callback was re-inspected at RVA 0x4b21d0 for this composition. Its
configuration-null branch returns before source reads; its lane branch precedes
processing and its final stores match the existing publication kernel. Individual
kernels have earlier validation. The composed reset/vector callback comparison
is now recorded in the differential section below; source/cache internals and
processor execution remain supplied boundaries.

The output includes an immutable byte snapshot and diagnostics stating whether
evaluation, source selection and processing occurred. Snapshot layout is a
build-specific inspection adapter, not a portable native object schema. Only
finite float32 publication is supported. A caller-supplied RSQRT seed retains the
existing numerical boundary; omission uses a labeled scalar approximation.
External processor side effects, native locking, map traversal and input sample
freshness remain outside the interface.

```sh
python3 -m unittest discover -s tests -p test_vector_action_refresh.py
```


## Differential reset and vector callback validation

The [composed vector receipt](../../native/snow_host/vector_action_refresh_validation.json)
records 1,440 cases executing the original reset enumerator and vector-source
callback together. Every case compares all 192 bytes of the synthetic action
against `refresh_vector_action`, plus the source-helper and processor call
sequence. No adapter correction was required.

Coverage combines source kinds 0/1/2/3/unknown, three lane modes, zero/analog/small/
3-4 vector inputs, owner suppression, missing source configuration, source
blocking, and absent/enabled/bypassed processor configuration. Native handle
selection and processor-call gating execute as original instructions. The
substituted processor halves each lane, making processing distinguishable from
bypass and exposing whether lane selection happened first.

The native source helper is supplied a synthetic vector/scalar/blocked-zero
result; its underlying ownership and cache reads do not execute. The map
enumerator supplies one synthetic action. For direction byte parity, the test
observes the native RSQRTPS seed and supplies it to the independent publication
kernel. This tests the refinement/publication operations without claiming to
reproduce seed generation on every CPU. Sample, magnitude and status do not
rely on that supplied seed.

This closes the previously pending composed local comparison. It does not
establish an active player binding, source-cache freshness, real processor-chain
selection, asynchronous publication safety or scheduler-integrated evaluation.


## Source ownership and cache getters in the composed refresh

The [expanded cache receipt](../../native/snow_host/vector_refresh_cache_validation.json)
executes the original source helper, ownership predicates and scalar/vector cache
getters inside the same reset/vector callback test. All 2,880 cases match the
independent composition's complete synthetic action bytes and source/processor
call sequence. This removes the previous source-helper-result substitution.

Synthetic source owners point to actual-layout cache and priority tables. The
fixtures exercise all-null priority slots, a first other owner ahead of self,
and self ahead of another owner. Mask stacks cover empty, a nonnull last entry,
and an earlier nonnull entry followed by null. Thus the native path applies both
ownership precedence and last-entry mask semantics before lane selection,
processing and publication. An earlier nonnull mask does not suppress a read
when the last entry is null.

Map enumeration, cache locks and the processor callback remain substituted.
Source ownership/cache objects are synthetic; the fixture does not execute their
constructors or producers. Exact direction comparison still supplies the native
RSQRT estimate. The new result establishes read-side composition, not device
identity, timestamps, atomic cache publication or which polling cycle produced
the selected sample. The next source-side gap is upstream cache production and
its relation to the refresh/request timeline, rather than these cache getters.


## Publication clocks are not analog sample generations

The existing [selected-cache publication](INPUT_UPDATE_ORDER.md#selected-device-publication-into-the-root)
and [root timestamps](INPUT_UPDATE_ORDER.md#root-cache-edge-timestamps) already
identify a concrete upstream writer for the vector/scalar slots. The unresolved
source-side question is therefore not whether any writer is known. It is which
selected-device update and publication the active refresh actually consumes,
including the holder's exchanges and alternate polling routes.

Selected-cache publication copies vector/scalar bytes without normalization.
Derived-direction production follows, then the root timestamp helper advances
its clock and stamps rising edges. A held derived direction retains its press
stamp even while its analog magnitude changes. Conversely, the current cache
clock can advance while the analog value remains identical. Neither the press
stamp nor equality of vector bytes supplies an analog sample generation.

The [timeline probe](../../engine/examples/input_refresh_timeline.py) connects
`publish_derived_and_stamp` to `refresh_vector_action` using stable synthetic
snapshots and explicit event ordering. Its sequence includes two publications
with identical analog values, then an analog change while the same derived
direction stays pressed. Tests verify the distinct clock/value/edge behavior.

```sh
python3 -m engine.examples.input_refresh_timeline
python3 -m unittest discover -s tests -p test_input_refresh_timeline.py
```

The harness chooses refresh-before-publication, then a final refresh. That
schedule illustrates which cache contents are visible; it does not establish
one-frame input latency, timer units or one publication per engine request.
The processor is explicitly bypassed and native devices are not polled.

A live trace must retain request identity, actual publication and evaluation
entry/return, selected cache identity, raw values and the consuming player
callback/substep. Timestamp equality alone cannot replace those observations.
When reads can straddle a writer, record that uncertainty rather than assigning
a fabricated generation from the clock or vector contents.


## Manager traversal differential validation

The [manager receipt](../../native/snow_host/action_refresh_manager_validation.json)
records 864 executions of complete routine `0x4d0290`, comparing its binding
reset sequence with `refresh_groups`. Cases combine two independently active
contexts, zero/one/three bindings per group, four blocker configurations and
fresh versus same-thread nested exclusive accounting.

The original copies global bytes +0x384/+0x385/+0x388 into context fields
+0xc1/+0xc2/+0xc5 before consulting the context activity byte. Inactive contexts
therefore still receive those flag copies, but do not run the preamble or binding
resets. Active contexts invoke the preamble before visiting the three groups.
Groups are forward, bindings reverse; the blocker check follows each reset.
A reset that changes its blocker to nonzero stops only its own group.

The test supplies thread identity, global flag accessor, preamble and binding
reset effects. The original exclusive-accounting instructions execute without
contention. Both fresh entry and same-thread nested entry restore their expected
owner/depth/accounting fields on return. This does not validate cross-thread
locking or native reentrant callbacks.

This extends the earlier portable group-order tests with original-instruction
comparison. The public adapter still models only the stable group traversal;
manager context selection, flag copies, preamble and synchronization remain
caller responsibilities. Reset/evaluator composition has separate validation;
this traversal test does not execute those bodies or permit structural mutation
of context/group arrays during iteration.


## Context preamble and vector history

The context preamble `0x984160` is not inert: it obtains the cache from the
source object, applies last-entry mask suppression separately to vector channels
0 and 1, and calls history update `0x9842a0` on embedded objects at source+0x10
and source+0x3d0. Cache pointers and mask state are read again for the second
channel; this is not an atomic two-channel snapshot. The manager invokes this
before binding resets. A separate StepPreWorlds history route also uses the
same history helper, as described in [ownership/history research](INPUT_UPDATE_ORDER.md#ownership-table-layout-and-reader-bank).

The outer history helper is now expressed by
[`update_vector_history`](../../engine/action_vector_history.py):

```text
raw_vectors[9..1] = raw_vectors[8..0]
raw_vectors[0] = input_vector
update_features(history, input_vector)  # separate, explicitly supplied helper
magnitudes[9..1] = magnitudes[8..0]
n = f32(f32(x*x + z*z) + f32(y*y + w*w))  # each product also rounds to f32
magnitudes[0] = min(float32_sqrt(n), 1.0)
timestamps[9..1] = timestamps[8..0]
timestamps[0] = global_clock.field_8
```

Raw vectors occupy +0x60..+0xff, magnitudes +0x2e0..+0x307 and timestamps
+0x00..+0x4f, each with ten entries. Magnitude clipping does not normalize or
clip the stored raw vector. Timestamp values are opaque uint64 values; no
monotonicity, unit conversion or generation check occurs in the outer helper.
The independent adapter validates finite arithmetic and uses stable detached
inputs. These are adapter constraints, not claims about all native inputs.

The [history receipt](../../native/snow_host/action_vector_history_validation.json)
compares 72 complete original outer-helper executions against the adapter,
including every byte of a synthetic 0x3c0 object and callback-entry state.
Feature-helper effects are explicitly supplied, including writes that prove
magnitude/time shifting follows the feature call. Clock storage is synthetic.
Two portable tests cover update ordering and eviction after more than ten updates.

Helper `0x9599a0` remains a separate feature-analysis boundary. Initial inspection
shows vector normalization, further history updates and an additional helper
call; those operations are not replaced with a guessed no-op. The API requires
an explicit callback. Preamble cadence, history consumers and their relation to
input selection remain open, so these histories are not sample generations.


## History feature direction remapping

Complete helper `0x9599a0..0x959eef` produces three additional ten-vector
histories at +0x100, +0x1a0 and +0x240. Each shifts nine older entries upward
before storing its newest vector. It normalizes a nonzero input with native
RSQRT/refinement, retains zero, and uses reference axis `(0,1,0,0)`.

A finite-input mathematical description is:

```text
n = normalize_nonzero_four_lanes(input)  # native estimate/refinement boundaries
history_A.push(convert(n))
v = reference_Y if n.y > history.threshold_50 else n
history_B.push(convert(v))
if any(abs(v.lane) > float32(1e-5)):
    unit = normalize_four_lanes(v)
    dot = dot_four_lanes(unit, reference_Y)
    if dot >= 1: angle = 0
    elif dot <= -1: angle = pi
    else:
        angle = acos(dot)
        if dot(cross_xyz(unit, reference_Y), reference_Z) < 0:
            angle = -angle
    response = history.curve(abs(angle) / float32(pi))
    theta = sign(angle) * response
    q = axis_angle(reference_Z, -theta)
    candidate = rotate(q, reference_Y)
else:
    candidate = the already converted value used for history_B
history_C.push(convert(candidate))
```

`convert` denotes the same external helper called three times, not an assumed
identity transform. The first converted result does not replace `n` for threshold
selection, and the second does not replace `v` for angle calculation. In the
near-zero branch, however, the third conversion receives the already converted
second temporary. Aliasing and conversion effects therefore matter.

The curve input is normalized absolute angle, but **its output is not multiplied
by pi before rotation**. The instructions multiply its signed output by -0.5,
then use sine/cosine to construct a Z-axis quaternion. With identity conversion,
this yields approximately `(sin(theta), cos(theta), 0, 0)`. For an identity
curve, backward input maps to theta=1 radian, not pi radians. This distinction
was caught by the original-instruction comparison. The actual configured curve
could supply a different angular scale; its identity is not established here.

The [feature receipt](../../native/snow_host/action_history_features_validation.json)
records 72 complete original-helper runs, including its native trigonometric
routines, against this finite mathematical interpretation. Tests vary zero,
axis, diagonal and Z inputs, threshold -1/0.5/1, and supplied curve gains
0/0.5/1. Three conversion calls are recorded and substituted with identity;
the curve callback is supplied. Newest history vectors agree within 2e-6 per
lane. This is a tolerance comparison, not bit-exact reconstruction of SIMD or
transcendental functions.

The conversion helper has mode-dependent branches and is not proved inert in
live use. Curve configuration, history consumers and scheduler cadence remain
open. These are input-history features, not evidence of player-body rotation or
animation actuation.


### Runnable feature-history adapter

[`update_history_features`](../../engine/action_history_features.py) now implements
the finite mathematical flow above and returns a detached snapshot plus conversion
and curve-call diagnostics. `convert` and `curve` are required callbacks. The
adapter uses the existing labeled scalar reciprocal seed and scalar trigonometry;
it does not claim bit-exact native SIMD/quaternion results.

The 72 original-helper cases now compare this implementation directly: newest
history-vector lanes agree within 2e-6, and all other bytes match exactly for the
synthetic fixtures. Four portable tests verify the curve's angular scale, repeated
conversion on the zero path, separation of conversion output from threshold input,
and composition with the outer history updater.

```python
from engine.action_history_features import update_history_features
from engine.action_vector_history import update_vector_history

def features(snapshot, raw):
    return update_history_features(
        snapshot, raw, convert=explicit_conversion, curve=explicit_curve
    )["snapshot"]

updated = update_vector_history(snapshot, raw_vector, now=opaque_time,
                                update_features=features)
```

The callbacks above must be supplied from known configuration or explicitly
labeled fixtures. They are pure detached-value interfaces: native callbacks that
mutate history storage or input aliases are outside this adapter's contract.
Live curve identity, coordinate service modes and history consumers remain open.


## History conversion modes and planar basis rotation

The shared conversion dispatcher `0x7db490` reads mode at service+0x6c:

| Mode | Inspected route |
| --- | --- |
| 0 or 6 | Global-basis helper 0x7db0a0; a global disable byte returns without changing input |
| 1 | Delegates through another service when available; not decoded here |
| 3 | Uses basis pointer service+0x148, or a global fallback basis when null |
| Other | Returns without modifying the vector |

Mode 3 returns immediately for an exactly zero four-lane vector. It selects the
basis vector at matrix+0x10 unless `abs(abs(primary.z)-1) <= float32(1e-5)`, in
which case it selects matrix+0x20. It clears selected Z/W, normalizes the XY
projection, derives a signed angle relative to +Y, normalizes the input and
rotates it with a Z-axis quaternion.

For finite planar inputs with a nondegenerate selected projection, the derived
mathematical equivalent is:

```text
basis = secondary if abs(abs(primary.z)-1) <= float32(1e-5) else primary
heading = normalize(basis.xy)
yaw = atan2(-heading.x, heading.y)
unit = normalize(input.xy)
output.xy = [cos(yaw)*unit.x - sin(yaw)*unit.y,
             sin(yaw)*unit.x + cos(yaw)*unit.y]
```

The native code obtains the angle through dot/cross/acos branches and uses
RSQRT/refinement and quaternion rotation; atan2 above expresses the planar
geometry, not the original instruction sequence. General nonplanar and fourth-
lane behavior is not established by this equation. Degenerate projected bases
also require separate analysis.

The [conversion receipt](../../native/snow_host/action_history_conversion_validation.json)
records 140 complete original dispatcher runs without substituted calls, using
synthetic service/basis objects. Mode 3 planar results agree within 2e-6;
no-op modes and the explicitly disabled mode-0/6 route retain input. Native
trigonometric routines execute. Mode 1, active global conversion and null-basis
fallback remain outside these tests.

The conversion can therefore change both heading and magnitude in these history
fields. It must not be assumed identity or used to infer that the action sample
itself is normalized. The active service mode, basis owner, live updates and
history consumers remain unknown; a camera-space interpretation is only a lead,
not an established identity.


## Four-lane mode-3 conversion

The expanded [conversion receipt](../../native/snow_host/action_history_conversion_four_lane_validation.json)
adds Z, W and mixed four-lane inputs. The final SIMD multiplier is `(2,2,2,0)`,
so W participates in input normalization but is cleared in the converted result.
For finite nondegenerate inputs, the mathematical extension is:

```text
n = input / sqrt(x*x + y*y + z*z + w*w)
output = [cos(yaw)*n.x - sin(yaw)*n.y,
          sin(yaw)*n.x + cos(yaw)*n.y,
          n.z,
          0]
```

This is not normalization of XYZ alone. With unchanged heading, input
`(0,3,0,4)` produces approximately `(0,0.6,0,0)`. A pure W input can produce
zero output. The earlier planar equation remains valid for its stated domain.
The multiplier was identified after a four-lane comparison disproved the initial
assumption that ordinary rotation would preserve W.

[`convert_history_mode3`](../../engine/action_history_conversion.py) implements
this finite mathematical behavior with explicit primary/secondary basis vectors.
Its scalar normalization and trigonometry remain labeled substitutes. Exactly
zero input returns before consulting basis values; a degenerate projected basis
or normalization underflow is rejected rather than silently repaired. Those
validation failures are adapter policy, not native branch behavior.

All 252 original dispatcher cases pass within 2e-6 per lane across the expanded
inputs and previously tested modes. Mode-3 results compare directly against the
new adapter; no-op and disabled global routes compare against unchanged input.
Three portable tests check fourth-lane participation/discard, vertical fallback
and zero-input early return. The active global route, mode 1, actual basis owner
and runtime mode selection remain unresolved.


## Complete mode-3 history composition

`update_mode3_history` in [the feature module](../../engine/action_history_features.py)
now composes raw/magnitude/time histories, feature remapping and mode-3 conversion.
Callers must supply the selected basis, opaque timestamp and curve. Selecting
this API asserts mode 3; it does not discover the native mode or configuration.
It returns a complete detached snapshot with curve/conversion diagnostics and
explicit numerical policies.

The [complete-history receipt](../../native/snow_host/action_complete_history_validation.json)
executes the original outer updater, feature helper, conversion dispatcher and
native trig together for 288 sequences of three updates each. Inputs cycle
through vector, zero, vector to exercise retained history. All 864 updates match
raw histories, magnitudes, timestamps and unaffected bytes exactly. All 30
feature-history vectors agree within 3e-6 per lane; curve-call count/arguments
and three conversion calls per update are checked.

Only the curve virtual callback is substituted in this composed execution.
Service mode, bases and clock storage are synthetic inputs. There is no context
preamble, cache read, scheduler dispatch or live freshness proof in this test.
The actual curve definition and feature-history consumers remain unresolved.

## Constructor-selected history curves

Static layout and instruction execution now identify concrete defaults for the
curve previously supplied to the history feature adapter. Parent constructor
`0x94d510` initializes histories at receiver `+0x10` and `+0x3d0`, each of size
`0x3c0`. These match the two receivers used by the context preamble. Inner
initializer `0x94d690` installs curve table `0x1edb7d8` at history `+0x308`;
virtual slot `+8` resolves to evaluator `0x971190`. Parent calls append helper
`0x9577c0` with X in XMM1 and Y in XMM2. No live constructor invocation or
absence of later mutation is established.

The first history uses threshold float32 `0.9961947202682495`, approximately
cosine of five degrees. The second uses `1.0`. The threshold acts on normalized
Y before curve evaluation, as described above; it is not a time constant.
The following degree labels explain the constructor constants. The implementation
retains their exact float32 values rather than regenerating them from degrees.

| Input angle represented by X = angle / pi | First-channel output angle | Alternate-center output |
| --- | --- | --- |
| 0 degrees | 0 | 0 |
| 1.5 degrees | No knot | 0 |
| 5 degrees | 1 degree | 0.8 degrees |
| 10 degrees | 5 degrees | Same |
| 20 degrees | 10 degrees | Same |
| 30 degrees | 20 degrees | Same |
| 40 degrees | 40 degrees | Same |
| 180 degrees | 180 degrees | Same |

The alternate branch depends on the byte at build RVA `0x2e22578`. Its semantic
name and live value remain unknown. Channel two always contains just `(0,0)`
and `(1,float32(pi))`. Thus the output really is radians, confirming the earlier
feature-helper interpretation. Do not label these channels movement/camera or
left/right stick without a separate binding proof.

For finite strictly increasing knots, the original evaluator is:

```text
result = 0
for each consecutive pair (x0,y0), (x1,y1), in stored order:
    if x0 <= input <= x1:
        slope = f32(f32(y1-y0) / f32(x1-x0))
        result = f32(f32(f32(input-x0) * slope) + y0)
return result
```

Both segments run at a shared knot, so the later result wins. Values outside
all segments return zero, not a clamped endpoint. Native duplicate-knot handling
exists but is outside the independent adapter's domain; constructor defaults
are strictly increasing.

[Curve implementation](../../engine/action_history_curve.py) exposes
`history_curve_config(channel, alternate_center=...)` and
`evaluate_history_curve(value, points)`. Callers can supply the latter to
`update_mode3_history`; configuration remains explicit. For example:

```python
from engine.action_history_curve import history_curve_config, evaluate_history_curve
config = history_curve_config(0, alternate_center=False)
curve = lambda x: evaluate_history_curve(x, config['points'])
# Set the detached history snapshot's threshold to config['threshold'], then
# pass curve=curve to update_mode3_history with explicit basis and clock.
```

[Validation receipt](../../native/snow_host/action_history_curve_validation.json)
records two original parent-constructor executions and 4,065 original evaluator
comparisons. Knot values, thresholds and output float32 bits match. The private
experiment supplies the inner initializer's storage/vtable setup; original
parent selection, append operations and evaluator execute unchanged. It covers
both channels and flag values, uniform samples, knots and neighboring float32
values. Eleven portable history tests also pass. This closes a constructor
configuration dependency, not device freshness, gameplay binding, scheduler
cadence or live deterministic stepping.

## Complete history with constructor defaults

The curve evaluator now runs inside the original outer-history, feature and
mode-3 conversion chain in [configured history validation](../../native/snow_host/action_configured_history_validation.json).
There are no substituted function calls in this tested path. The experiment
installs constructor-derived knots and thresholds into synthetic storage rather
than executing the constructor, and supplies explicit service, basis and clock
objects. This remains offline instruction execution, not a live scheduler test.

All 768 updates across 256 three-update sequences pass. Both channels, both
constructor flag values, four bases and 16 vectors cover input, release and
repeated input. Vectors include center-adjacent angles, knot angles, signed and
opposite directions, and nonzero Z/W components. Raw, magnitude and timestamp
histories match exactly; all 30 feature vectors agree within 3e-6, with observed
maximum lane error 2.384185791015625e-7. Curve invocation count/argument and three
conversion calls per update are checked. Native curve metadata remains unchanged.

`initial_history_snapshot` creates detached adapter state with zero histories
and the selected threshold. It deliberately omits native pointers and auxiliary
containers. It must never be used as a native object to write into the game.
The separate curve configuration supplies knots to the existing callback API.

Run the [configured history example](../../engine/examples/configured_history_probe.py):

```sh
python3 -m engine.examples.configured_history_probe
```

It applies a synthetic 30-degree direction, release and repeated direction to
both channels with an explicit identity heading basis. The first channel maps
the direction to approximately 20 degrees, the second to 30 degrees. Release
inserts zero features while retaining older entries. Output includes curve
arguments, radians, mapped directions and recent opaque timestamps. This is a
runnable local reconstruction, not proof that these channels control a particular
stick or player action.

The next scheduler question remains the consuming job and sample age. Closing
these local numerical dependencies does not establish ingestion order relative
to physics substeps, live configuration ownership or safe global quiescence.

## History direction reader and action source

A concrete action consumer joins the history layout to the existing source
factory. Evaluation callback `0x4b2a20`, installed by builder `0x457910` at
main table `0x1e6b7e0` slot `+0x10`, calls wrapper `0x48b710`. The wrapper
checks ownership suppression through `0x957e70`; when allowed, it selects
`source + 0x10 + channel * 0x3c0`, passes the auxiliary magnitude threshold
container at history `+0x3a0`, and passes reference vector `source +0x790` to
reader `0x9760a0`. Channel comes from configuration `+0x28`. This is a type-level
consumer join, not proof of the active player's selected binding.

The reader uses newest magnitude at history `+0x2e0` and newest feature **B** at
`+0x1a0`. It does not read the curve-remapped feature C at `+0x240`, older samples
or history timestamps. Its finite, nondegenerate mathematical interpretation is:

```text
if newest_magnitude <= threshold_container.values[0]: return false
reference = normalize4(reference)
direction = normalize4(history_B[0])
dot = dot4(reference, direction)
if dot >= 1: selected = 0
else if dot <= -1: selected = 1
else:
    angle = acos(dot)
    if cross(direction.xyz, reference.xyz).z < 0: angle = -angle
    if -pi/4 < angle < pi/4: selected = 0
    else if -3*pi/4 < angle < -pi/4: selected = 2
    else if pi/4 < angle < 3*pi/4: selected = 3
    else: selected = 1
return selected == requested_sector
```

Strict angle inequalities matter. Exact computed boundary angles fall through
to sector 1. Normalization and acos rounding can decide which side a nominal
45-degree input reaches. The independent adapter retains float32 arithmetic
where decoded and labels scalar normalization/trig as approximations. With +Y
reference, +X selects 3, -X selects 2, +Y selects 0 and -Y selects 1. The initial
static sign interpretation reversed sectors 2/3; original-instruction comparison
caught it, and the implementation now uses direction cross reference.

[Reader implementation](../../engine/action_history_direction.py) exposes
`history_direction_matches(snapshot, reference, magnitude_threshold=..., sector=...)`.
It rejects degenerate directions after the magnitude gate rather than inventing
native NaN behavior. [Reader validation](../../native/snow_host/action_history_direction_validation.json)
executes the full original reader including acos without substituted calls.
All 570 cases agree: below/equal/above magnitude threshold, four sectors plus an
unknown selector, two reference headings and 19 directions including boundary
angles and their nearby angles. This is sampled predicate agreement, not proof
of bit-exact SIMD math across all inputs. Fifteen portable history tests pass.

The calling action evaluator adds temporal behavior. Static inspection shows
configuration `+0x30` selects a rising-edge route for 0, a held route for 1, and
a falling-edge route for 2. Held mode uses timing configuration `+0x34/+0x38`
and action timestamps `+0xc0/+0xc8`. It writes result byte `+0x30`, caches the
current predicate at byte `+0xb8`, and publishes newest magnitude at `+0x60`
after a second ownership check. The timing arithmetic, clock units, missing
configuration path and composed action behavior have not yet been validated.
These are next local dependencies, not a completed player-physics ingestion join.

## History action timing gates

The configured path of evaluator `0x4b2a20` now has a detached timing adapter in
[action history timing](../../engine/action_history_timing.py). This supersedes
the previous section's unvalidated timing boundary for the tested domain only.
The direction predicate and final ownership check remain supplied dependencies
in [timing validation](../../native/snow_host/action_history_timing_validation.json).

Let `current` be the current direction match and `previous` the byte cached at
action `+0xb8`. Modes 0 and 2 publish rising and falling edges respectively.
Mode 1 uses hold delay at configuration `+0x34` and repeat delay at `+0x38`:

```text
active = false
if mode == 0: active = current and not previous
if mode == 2: active = previous and not current
if mode == 1:
    if abs(hold_delay) <= float32(1e-5): active = current
    else if current:
        now = read_clock()
        if current != previous: start_time = now
        else: active = unsigned64(now - start_time) >= ticks(hold_delay)
    if active and abs(repeat_delay) > float32(1e-5):
        now = read_clock()    # separate read, not reused from above
        if unsigned64(now - repeat_time) >= ticks(repeat_delay):
            repeat_time = now
        else: active = false
previous = current
```

For supported finite nonnegative durations below the uint64 range,
`ticks(duration) = truncate(float32(duration * 1000))`. Exact equality passes
both elapsed-time gates. A positive hold delay records its start on the first
matching evaluation without firing. A zero delay can fire immediately, subject
to the repeat gate. Neither timestamp is reset on release. Unsupported mode
values publish false but still update cached `previous`. Unsigned subtraction
also means a supplied clock earlier than the saved timestamp produces a large
elapsed value, not a clamped zero. The adapter preserves that behavior.

Native code has signed/unsigned conversion branches for larger and negative
values; the public adapter explicitly rejects negative, nonfinite and oversized
durations instead of claiming that behavior is reconstructed. The native
near-zero comparison uses absolute values; supported nonnegative inputs permit
the simpler comparison in the implementation.

Clock helper `0x478fe0` first reads a global receiver, then receiver `+0x188`,
then that object's qword `+0x1050`. If either pointer is null, it reads another
global clock object's qword `+8`. This gives a concrete selected-world-versus-
fallback lead; the timing receipt executes the fallback only. Multiplication by
1000 establishes the conversion factor, not independently the live clock units.

The final ownership check can suppress the magnitude published at action `+0x60`
without changing the already computed boolean. The validation supplies the two
predicates independently to confirm this operation order; it does not claim
those predicates are independent in ordinary gameplay.

All 768 original evaluator cases match active flag, cached predicate, both
stored timestamps, number/order of clock reads and magnitude publication.
Original fallback clock instructions execute. Cases cover all prior/current
boolean combinations, modes 0/1/2/3, zero/epsilon/positive delays, repeat gating,
clock thresholds and suppression. Eighteen portable history tests pass. Missing
configuration, the selected-world clock branch, composition with the actual
direction reader, active player binding and physics-substep timing remain open.

## Composed history action evaluation

[Configured action adapter](../../engine/action_history_action.py) composes the
history predicate and timing adapter into detached action-snapshot evaluation.
It preserves unrelated bytes and writes the native result flag, cached predicate,
published magnitude and timestamps. Channel/history selection is explicit at the
API boundary. Missing configuration/resource lookup and manager reset traversal
are not included.

Ownership is observed twice in native order: before the direction test and before
magnitude publication. The adapter uses a callback for each observation. A change
between these observations can therefore suppress magnitude without cancelling
an already computed event, or permit magnitude after a suppressed predicate.
Portable tests cover these combinations as supplied observations; they do not
establish that such changes occur in the game.

[Composed action validation](../../native/snow_host/action_history_action_validation.json)
executes the original configured evaluator, channel wrapper, ownership lookup,
direction reader, native acos and clock accessor together with no substituted
function calls. All 1,800 evaluations across 360 five-evaluation sequences match
the entire 0xe0-byte action snapshot and every clock read. Histories, configuration,
registry and clocks are synthetic. The observation hook changes clock data for
each read, without replacing the clock accessor.

The sequences cover two channels, selectors 0 through 4, timing modes 0 through 3,
and empty/self/other top ownership slots. Hold, direction change, release and
re-entry retain the same action state across evaluations. Clock cases execute:

1. Null global receiver, using fallback clock `+8`.
2. Present receiver but null selected-world pointer, using the same fallback.
3. Present selected-world object, using its clock field `+0x1050`.

Competing clock fields deliberately contain different values, so a wrong branch
would change the observed timestamp/result. This resolves the previously untested
selected-world branch as local behavior. It does not identify the live world's
object or establish its cadence.

Twenty portable history tests pass. This closes the local history-to-configured-
action composition for the tested domain. The original history producer is not
executed in this particular receipt; it has separate composed validation above.
The native registry is stable during each evaluation, classifier inputs here are
finite planar axes, and the missing-configuration route remains excluded. The
remaining scheduler connection is the selected player's consuming job and input
age relative to its physics substeps, not an unidentified local timing predicate.

## Producer and action freshness probe

The [timeline inspection API](../../engine/history_action_bench.py) composes
constructor-configured history production with configured action evaluation.
Callers supply `update` and `evaluate` events independently. Update events carry
four input lanes and an opaque history timestamp; evaluate events carry exactly
the clock reads and two ownership observations consumed by that evaluation.
The API rejects missing or unused observations instead of silently synthesizing
a clock. It reports producer sequence, reuse, history timestamp, action result,
magnitude, timer state and clock reads. Sequence counters are authored inspection
metadata, not discovered native generation fields. No shared clock epoch is assumed.

Run [the freshness example](../../engine/examples/history_action_freshness.py):

```sh
python3 -m engine.examples.history_action_freshness
```

The imposed sequence publishes +Y at history time 9000, evaluates held mode at
action time 100, evaluates again at 200 without publication, publishes release
at history time 9001, then evaluates again. With hold delay 0.1 and no repeat
delay, active states are false, true, false. The second evaluation reuses the
same history but reaches its hold threshold. Release preserves the start time.
The differing timestamp ranges deliberately avoid implying a common clock domain.

[Original-instruction freshness validation](../../native/snow_host/action_history_freshness_validation.json)
executes the history producer and action consumer in that order, with no substituted
calls. Twelve sequences cover both channels, both curve variants and all three
clock-selection cases: 24 producer updates and 36 evaluations. Flags, magnitudes,
timestamps and clock reads match the public probe. Every history byte stays
unchanged during each action evaluation. Mode-3 conversion, native curve evaluator,
sector reader, ownership lookup and clock accessor all execute on synthetic data.

This proves that the local action can change without new history when evaluated
again with an advancing clock. It does not prove that the imposed repeated-
evaluation schedule occurs in the live game. The next correlated scheduler trace
must therefore count producer updates and consumer evaluations separately, retain
both clock observations, and identify the selected objects. An action event alone
is not evidence of fresh input, and an unchanged history timestamp alone cannot
establish whether publication ran with an unchanged clock value.

## Action timer joins the clock record

Accessor `0x472b60` returns selected object `+0x1048`, or the shared global
fallback record if either pointer is null. Action tick accessor `0x478fe0`
returns exactly the qword at `+8` of that selected record. Both accessors use
the same global receiver and fallback globals. This is a direct field-selection
join, not an inference from two coincidentally similar offsets.

[Clock-record validation](../../native/snow_host/action_clock_record_validation.json)
executes both original accessors in 15 cases with no substitutions. It covers
both null fallback conditions and selected object, with values from zero through
uint64 maximum and above the exact integer range of a double. Pointer selection
and integer results match exactly. No float conversion occurs in the tick getter.

The selected-object record matches the already reconstructed ordinary world
clock at `+0x1048`; its `+8` field is `divided_ticks`. See
[the clock producer join](MOTION_MEMBERSHIP_OBSERVATION.md#ramp-clock-producer-joins-the-existing-clock-tree)
and [clock tree arithmetic](CLOCK_TREE.md). Under that established clock layout:

```text
accumulated_ticks = wrap_u64(accumulated_ticks + processed_input_ticks)
divided_ticks = accumulated_ticks // 30
hold_elapsed = wrap_u64(divided_ticks - saved_action_start)
```

The driver/producer evidence supports milliseconds for divided ticks and seconds
for action delay configuration multiplied by 1000. This is stronger than the
isolated multiplier inference, but live initialization and selected-object
membership still need observation. Do not replace the tick accessor with float
interval, accumulated ticks or the ramp's float32 seconds conversion.

[Clock/action integration tests](../../tests/test_history_action_clock.py) combine
the existing independent clock tree and action timer. Positive hold count retains
divided ticks and prevents the tested hold timer from progressing; enabling scale
two advances the tested timer twice as fast. Disabling accumulation retains the
timer's ticks even when the float interval changes. These are composed local
arithmetic consequences, not proof that all game jobs stop during pause or that
the selected clock remains the same across evaluations. The fallback record's
producer and live selected-object changes remain separate observation questions.

## Passive history-action capture contract

The existing native `SnowUpdateRecord` records actor state, job/frame attribution
and optional motion observations around an actor call. It does not record this
history-sector action's configuration, history times, timer state or selected
clock. A motion before/after difference is therefore insufficient to attribute
freshness to this particular source.

[Passive observer](../../engine/action_history_observation.py) supplies a bounded
read-only building block. Callers provide a current action pointer, verified
build-specific table/callback identities, receiver and fallback-clock global
slots, and an exact byte reader. It performs at most 32 reads and 1,024 requested
bytes across two samples. It checks the action type, follows the configuration
and source, bounds the channel to the two decoded histories, and records:

- Source/configuration identities, channel and timing/direction settings.
- Reference vector and first magnitude-threshold value/container identity.
- Three recent history timestamps, newest feature B/C and magnitude bit patterns.
- Published action flag/magnitude, previous predicate and two timer timestamps.
- Receiver, selected object, selected clock-record identity and divided ticks.

Both samples are retained. `observed` means the compared identities/settings
match, even if dynamic values differ; `unstable` means those identities/settings
changed. Equal dynamic values are reported separately. Neither result proves
atomicity, lifetime, absence of ABA changes, action execution or input freshness.
The result explicitly sets those proof flags false. Addresses and raw field
bits in a real receipt are private-session evidence, not public fixture data.
Short reads, unavailable required pointers/thresholds and unsupported types or
channels refuse the observation. No remote code is called or modified.

Tests cover changing clocks, fallback selection, configuration mutation,
unsupported channels and every short-read position. This module is not wired
into the native recorder and was not run against the game. Ownership-slot
sampling and producer/evaluator entry counts still need their own correlated
records. A future collector must supply fresh action provenance from the
selected player's chain and account for the combined read budget before enabling
this optional channel. Repeated passive samples alone cannot close the live
scheduler ordering question.

## Native director startup and passive action-chain repeat

A further live pass reached natively verified gameplay in 45.6 seconds without
keyboard input, at the same spawn as the earlier director test. The simulation
step counter advanced from 3131 to 5244 during observation. Both the action-chain
and ramp collectors passed their identity and selected routine signature checks.
See the [bounded receipt](../../native/snow_host/director_action_observation.json).

Selected action 118 again contained vector and directional children. The
directional branch used query IDs 65, 68, 87 and 83, followed by unused sentinels,
and two enabled processor stages. Its active ramp configuration retained duration
0.20000000298023224, axis mode 0 and two curve keys. The separate global gate was
false; stage enablement alone does not establish that the ramp executed.

This confirms the fast startup path supports the existing passive observers. It
does not locate a history-sector action on the rider, prove input ingestion
cadence, or validate the newest recorder ABI live. The run reused a previously
passing host build. No input was sent and the observations were sequential, not
atomic. Shutdown, save restoration, settings restoration and original DLL
verification all passed.
