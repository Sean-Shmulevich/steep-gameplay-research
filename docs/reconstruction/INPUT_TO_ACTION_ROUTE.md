# Input polling to world action: registered route

The normal rebuilt graph has a concrete outer dependency route from the input
holder poll to the previously studied world action wrapper. This is a static
registration result with bounded instruction emulation, not a live proof of
which substep consumes which player sample.

```text
StepPreWorlds: vector histories and ownership transitions
  -> Step: rebuild/register world-stage chains when its gate permits
  -> earlier world/engine stages
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
