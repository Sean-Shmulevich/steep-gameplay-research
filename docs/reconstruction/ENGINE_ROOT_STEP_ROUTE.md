# Engine root to Step and world-action route

The setup code registers a concrete route from the engine root to the job bound to `Engine::EngineLoop::Step`. Two levels of conditional jobs can bypass that route. Their predicates are byte reads, not inferred meanings from job names. This closes the static dependency route for the enabled ordinary mode. It does not prove that an arbitrary live request takes it or that every job completes.

This extends [the action caller audit](ACTION_REARM_CALLER.md). The outer request/completion handshake is treated separately in [the engine loop handshake](ENGINE_LOOP_HANDSHAKE.md).

## Registered route and exact gates

The names below are local explanatory aliases. `register(a,b)` records b as an outgoing successor of a. It is a dependency operation, not an immediate call to b. The inspected ordinary registration method returns b, which explains the chained receiver calls in setup and the Step callback.

```text
register(Root, RootSide)
register(Root, ModePredecessor)
register(ModePredecessor, GlobalModeBranch)

GlobalModeBranch.predicate = () => global_mode_owner.mode_byte
GlobalModeBranch.true_successor = Bypass
GlobalModeBranch.false_successor = Sequence1

register(Sequence1, Sequence2)
register(Sequence2, Sequence3)
register(Sequence3, Sequence4)
register(Sequence4, Fork)

register(Fork, OwnerBranchA)
register(Fork, OtherWorkWrapper.entry)
register(Fork, OwnerPredecessorB)
register(OwnerPredecessorB, OwnerBranchB)

OwnerBranchA.predicate = () => engine.owner_mode_byte
OwnerBranchA.true_successor = Bypass
OwnerBranchA.false_successor = BeforeStep1
register(BeforeStep1, BeforeStep2)
register(BeforeStep2, Step)

OwnerBranchB.predicate = () => engine.owner_mode_byte
OwnerBranchB.true_successor = Bypass
OwnerBranchB.false_successor = Step

register(Bypass, Join)
register(BeforeStep2, Join)
register(Step, Join)
```

The global predicate returns its owner's byte verbatim. The two owner predicates return the same engine byte verbatim. The conditional registration helper selects its primary list for a nonzero selector and secondary list for zero. The [conditional begin and alternate-release findings](ALTERNATE_DEPENDENCY_RELEASE.md) distinguish executing the selected route from bypassing the unselected route.

Thus a sufficient stable mode selection for the shown normal route is:

```text
global_mode_owner.mode_byte == 0
engine.owner_mode_byte == 0 at BOTH owner-branch evaluations
```

The two owner predicates are separate evaluations, not one cached snapshot. Assigning one sampled value to the whole request would add an unproved stability assumption. A nonzero global mode selects Bypass. A nonzero owner mode selects Bypass at that owner branch. No pause, loading, editor or shutdown meaning is assigned to these bytes by this pass.

Step has more than one incoming dependency. The two false routes above do not mean that Step should execute twice. Scheduler holds and request counts determine eligibility. The other fork's concrete completion behavior and all external holds still matter to a complete execution proof.

## Preparation preserves the Step route

Preparation copies the world-stage owner's rebuild byte into an engine byte. When enabled, it clears outgoing links on selected engine jobs and previously cached world-stage terminals, clears the cached pointers, then restores these starter edges:

```text
register(BeforeStep2, Join)
register(BeforeStep2, Step)
register(Step, Join)
register(WorldBridgeA, Join)
register(WorldBridgeB, Join)
```

It also clears and rebuilds the RootSide successor relation outside that gate. This routine does not remove the root-to-global-branch connection or replace the two owner predicates. Clearing outgoing links remains a graph mutation, not a callback-completion barrier.

## Step constructs the route into world stages

Setup installs the Step callable with the same engine owner as its receiver. The callback checks the copied rebuild byte before doing anything. When enabled it rebuilds the per-world stage chains and connects Step to their first engine predecessor.

```text
Step.callback(engine):
    if engine.rebuild_byte == 0:
        return

    rebuild_world_stage_chains(world_stages)
    register(WorldStart, Stage1.seed)
    register(Stage1.tail, WorldBridgeA)
    register(WorldBridgeA, WorldBridgeC)
    register(WorldBridgeC, Stage2.seed)
    register(Stage2.tail, StageAux.seed)
    register(StageAux.tail, ProviderPredecessor)
    register(ProviderPredecessor, ProviderPair1.entry)
    register(ProviderPair1.terminal, ProviderSuccessor)
    register(ProviderSuccessor, Stage3.seed)
    register(Stage3.tail, ProviderPair2.entry)
    register(ProviderPair2.terminal, Stage4.seed)
    register(Stage4.tail, ActionStage.seed)

    register(ActionStage.tail, FollowingStage.seed)
    register(ActionStage.tail, FollowingEngineJob)
    # Additional stage links continue beyond this point.

    register(Step, WorldStart)
    Step.activate_outgoing(force=true)
```

`ProviderPair1` and `ProviderPair2` are obtained through four virtual getters on a separate global provider. The inspected callback connects their entry and terminal endpoints; this pass has not decoded their interior jobs. The route above is therefore an exact endpoint graph with two unresolved internal provider paths, not a proof that those paths always release their terminals.

Each world-stage builder initially sets its tail to its seed, clears the seed's outgoing links, then folds the eligible world handles in array order. For the action stage, the adapter selects the previously identified action wrapper from each world's graph. Its wrapper terminal becomes the next predecessor. An empty world list has seed equal to tail.

The action terminal has two successors. It is not the whole engine request's final completion point. The additional world-action predicate can also bypass receiver execution; reaching the action entry alone does not prove that physics or animation ran.

## What this permits and what remains

The recovered graph supports an explicit model with separate global-mode selection, two owner-mode evaluations, a Step rebuild gate and per-world conditional routing. A reconstruction can represent those decisions without inventing a direct root-to-physics call.

For original-game stepping, the remaining checks are concrete:

- Resolve both provider entry-to-terminal interiors before treating the displayed world route as a complete release chain.
- Identify writers and lifetime rules for the global mode byte and engine mode byte; do not assume they remain stable during a request.
- Retain the outer completion handshake and all incoming holds. A route to Step does not authorize editing links while another request is active.
- Join an eligible world handle to the player world before treating that world's action batch as the player simulation.

## Evidence boundary

This was a read-only static pass against the analyzed image with SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. No game execution, process attachment or payload publication occurred. The following hashes cover concatenated exception-directory fragments in address order, including chained fragments:

| Routine | Bytes | SHA-256 |
| --- | ---: | --- |
| Engine graph setup and callable bindings | 6704 | `72e33bdd895f585210b61f861c6db7a7defe0947ba4e8d9b08d73be8616676b3` |
| Engine Step callback | 959 | `3f6af92b1e3b0df070c7f26dcdf78641c9dc1f3c30f7bd9050374b5d6c9d2bb1` |
| Engine dependency preparation | 732 | `b3cf04e418a29f45c58e88af59de5b172e736bcee94674ea6472b7cae7bbc884` |
| World-stage chain builder | 1496 | `094c6fdab389d5991de69ba8bc8b5b5e42272b2e875a52363eba79ca9c5d5729` |
| Conditional successor registration | 107 | `7d75b5330dd5f429295d740ec472090cc5d630aa664dc8987a70e0b927fc467a` |

The two predicate leaves lack exception-directory entries and were decoded from their actual callable targets. Their complete bodies are a global-pointer load plus byte read plus return, and a receiver-relative byte read plus return, respectively. Job labels corroborate the Step binding; the dependency calls, predicate targets and receiver bindings establish the relationships reported here.
