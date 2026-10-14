# Engine frame graph: what precedes the EndFrame signal

The stop handshake signals its event from inside the `EndFrame` callback ([event adapter](ENGINE_EVENT_ADAPTER.md#live-handshake-resolution)). This pass recovers the engine-owned frame graph that setup registers, and asks which of its jobs are guaranteed to be upstream of `EndFrame`. It narrows the "drain coverage" gate in the [scheduler roadmap](../../engine/SCHEDULER_ROADMAP.md); it does not close it.

Job names below are the setup labels attached to each embedded job. Offsets and addresses remain private. No game was launched for this static pass.

## Edge kinds

Setup uses four registration forms, all decoded from the setup routine:

- an ordinary successor registration on the predecessor job;
- a conditional registration that adds a successor to a branch job's primary (selector 1) or secondary (selector 0) list;
- a group add, which registers `group.begin -> job` and `job -> group.end` for a group whose begin job is allocated and whose end job is inline;
- a final binding between `EndFrame` and a separate engine member, whose meaning is not resolved here.

## Static topology

```text
BeginFrame
  -> BeginGraphicFrame -> GraphicFrame -> EndGraphicFrame -> EndFrame
  -> BeginEngineFrame -> CheckEngineStop
        [1] -> UpdateWhileEngineIsPaused -> EndEngineFrame
        [0] -> UniverseLinkStart -> UpdateSingleThreadedUniverseComponents
             -> UpdateMultiThreadedUniverseComponents -> PreActionStep -> PreStep
PreStep
  -> EngineStoppedPreStepActionBranch
        [1] -> UpdateWhileEngineIsPaused
        [0] -> PreActionWorldStep -> StepPreWorlds -> { Step, EndEngineFrame }
  -> MenusAndSounds group { SoundManagerUpdate, SoundManagerUpdateOcclusion,
                            SoundDynEchoManager::ResolveAsyncRequest, NetEngine_PreUpdate }
        -> MenusAndSoundsEnd -> EngineStoppedPreStepBranch
  -> LoadingAdvisorUpdate -> EngineStoppedPreStepBranch
EngineStoppedPreStepBranch
  [1] -> UpdateWhileEngineIsPaused
  [0] -> Step
Step -> EndEngineFrame
SoundManagerUpdate -> SoundManagerSoundEmittersUpdate -> EndEngineFrame
SoundManagerUpdateOcclusion -> SoundManagerComputeOcclusion -> EndEngineFrame
StepDispatchEvents, AfterAIAndSkel, NetEngine_PostUpdate, second group end -> EndEngineFrame
EndEngineFrame -> finish fanout -> finish[0..4] -> EndFrame
```

The three branch jobs read the engine's mode routing documented in [the root-to-Step route](ENGINE_ROOT_STEP_ROUTE.md) and [mode writers](ENGINE_MODE_WRITERS.md). Their labels name the bypass that earlier audits called anonymous: when the selector is nonzero, world `Step` is replaced by `Engine::EngineLoop::UpdateWhileEngineIsPaused`, which still feeds `EndEngineFrame`. The first branch is labelled `CheckEngineStop`. The other two are labelled `EngineStoppedPreStepActionBranch` and `EngineStoppedPreStepBranch`.

The engine's dependency preparation, which runs inside `EndFrame` before its branch, clears and rewires the per-frame side: `StepPreWorlds -> Step -> Graphic::EndEngineFrame`, `StepDispatchEvents` and `AfterAIAndSkel -> EndEngineFrame`, and `BeginGraphicFrame -> GraphicFrame`. The Step callback then wires `Step -> WorldLinkStart` and the world-stage chains. Those chains attach the remaining embedded jobs (domino, cinematic, pad, camera, action manager, accomplishment manager), and they reconverge on `StepDispatchEvents`, `AfterAIAndSkel` and `NetEngine_PostUpdate`.

## Coverage result

Treating every recovered setup edge as a dependency, and both branch alternatives as possible:

- 30 embedded jobs are reachable from `BeginFrame` through static edges. **Every one has a path to `EndFrame`.** No statically reachable job bypasses it.
- The four statically wired jobs that are not reachable from the root without per-frame wiring all feed `EndEngineFrame`.
- Seven embedded jobs have only per-frame edges. A later full extraction (46 constructed objects: 40 jobs, 3 branches, 2 groups and a list; 50 setup edges, 6 preparation edges and 29 Step-callback edges) found that domino, cinematic, pad and camera have outgoing edges only to world-stage jobs or to jobs returned by a singleton getter. Their path to `EndEngineFrame` therefore depends on world-stage internals and is **not proved**. One embedded job is constructed but never labelled or wired, and one group has no members.

Under ordinary dependency semantics, therefore, the `EndFrame` callback that performs `SetEvent` runs after every job in the engine's own frame graph for that request has released its dependencies. Combined with the [ordinary finalizer rule](ENGINE_LOOP_HANDSHAKE.md#why-this-protects-the-ordinary-receiver-batch), the receiver bodies of those jobs have returned.

## What this does not cover

- `EndFrame` itself: the signal fires inside its callback, before its own dispatch bookkeeping finishes.
- Work outside this graph: the [idle task worker pool](IDLE_TASK_WORKERS.md), the [loading thread](LOADING_THREAD_LIFECYCLE.md), asynchronous requests that jobs such as `ResolveAsyncRequest` merely service, and any graphics submission that continues after `EndGraphicFrame`.
- Alternate dependency-release paths, which may complete a branch without executing its body ([alternate release](ALTERNATE_DEPENDENCY_RELEASE.md)).
- The final `EndFrame` binding to another engine member, whose effect is unresolved.

The waiter's return therefore supports "the signalling frame's engine graph has completed up to `EndFrame`", not "the process is idle".

## Evidence

Edges were extracted from the setup routine, the dependency-preparation routine and the Step callback in the analyzed image (SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`), with group semantics taken from the decoded group helpers. The reachability computation is a private script over that edge list. Static registration is not a live trace of every frame.

## Live check: the in-game menu is not the stop mode

The global setter writes the request argument, mode, neighbor flag and companion bytes of the same global engine owner that holds the event. [One bounded session](live_engine_mode_menu_validation.json) sampled those bytes during gameplay, then pressed Escape, which opened the Progress menu (verified from screen text), and sampled again. A second Escape left the menu open; it was sampled a third time.

All 24 samples showed mode 0 and companion 0. The menu therefore does not select `UpdateWhileEngineIsPaused`; world stepping continues behind it. The request-argument byte was 1 throughout. Only the setter writes it, so the stop mode was entered and cleared at least once earlier in the session, plausibly during startup or loading. That timing was not observed. The routing name "engine is paused" must not be equated with the user-facing menu.
