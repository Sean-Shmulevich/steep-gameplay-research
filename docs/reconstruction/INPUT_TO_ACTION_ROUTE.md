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

## Remaining input-to-physics questions

- Which UpdateAction receivers evaluate the active player's source chain, and
  which producer publishes its motion input?
- Where that publication lies relative to each physics substep, including
  multi-substep frames and paused/bypass routes.
- Whether another polling call updates the cache between the named task and a
  consumer. The conditional direct polling route still exists.
- Whether the player's selected world/actor is present in the constructed list.
- The world AfterUpdate interior and any additional side effects between polling
  and Action. Its name and wrapper offset do not answer this.

This route supports targeting the named pad task and downstream action boundary
for a future shared-sequence capture. It does not yet support a claim of exact
frame-by-frame replay, a universal one-poll-per-substep rule, or safe arbitrary
scheduler mutation. Detailed instruction findings remain in
[input update order](INPUT_UPDATE_ORDER.md).
