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
