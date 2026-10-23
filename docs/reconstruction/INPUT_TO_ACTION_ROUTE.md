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
