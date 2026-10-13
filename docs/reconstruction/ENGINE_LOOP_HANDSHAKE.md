# EndFrame supplies the ordinary loop rearm boundary

The routine that prepares engine dependencies and submits the next root request is bound to the engine's `EndFrame` job. It is not merely an unidentified external entry point. The action graph feeds a downstream engine completion chain that becomes a predecessor of that EndFrame job.

This closes a concrete ordinary path from action completion to the following preparation and root submission. It refines the unresolved caller in [Action graph caller and engine-step integration](ACTION_REARM_CALLER.md). The result is conditional on the inspected dependency route and ordinary completion semantics; alternate branch release, startup and exceptional callers remain separate cases.

## The preparation routine is the EndFrame callback

Engine setup stores the previously inspected preparation/submission routine in a callback job and binds its receiver to the engine owner. The job receives the labels `EndFrame` and `Engine::EndFrame`.

Its callback performs other engine service calls, prepares the engine dependency links, then chooses between ordinary root submission and an event-related branch. Thus repeated submission can happen from within the completed frame's downstream job rather than from an external loop that explicitly calls a wait before every frame.

```text
end_frame_callback(engine):
    run_preparation_services()
    prepare_engine_dependency_links(engine)
    if engine.selects_ordinary_root_submission:
        submit(engine.root_job)
    else:
        invoke_event_branch(engine)
```

The [event-branch audit](ENGINE_EVENT_SUBMISSION.md) separately connects its owner-held handle and restart path while retaining protected-operation and waiter limits. This document follows the ordinary submission branch and the dependency gate that gets execution into the callback.

## The action terminal feeds the EndFrame predecessors

The Step callback's graph wiring connects the action-world chain to later world and engine stages. In the inspected enabled rebuild path, the action tail feeds an engine-following job, which feeds subsequent world-stage chains. Those stages eventually reach a later world-stage tail that feeds two engine jobs. Both of those engine jobs feed an engine join node.

Preparation registers that join node as a predecessor of a second completion join. Engine setup connects the second join to a fanout parent. That parent feeds five jobs, and each of the five registers EndFrame as its successor. A separate earlier engine branch also registers EndFrame as a successor.

```text
last_action_world_terminal
    -> engine_following_job
    -> later_world_stage_chains
    -> later_world_stage_tail
    -> { engine_finish_A, engine_finish_B }
    -> engine_join
    -> completion_join
    -> fanout_parent
    -> { finish_job[0], ..., finish_job[4] }
    -> EndFrame
```

The braces indicate dependencies, not an inferred fixed execution order. Other incoming edges are omitted. Omitting them does not remove the demonstrated action-to-EndFrame dependency path, but this diagram is not a complete frame graph.

The five-job fanout is a concrete setup loop with five iterations. Each iteration registers the fanout parent as predecessor of one job and that job as predecessor of EndFrame. This is stronger evidence than the label `EndFrame` alone.

## Callback jobs become done on reservation

The engine constructor binds both its root callback job and EndFrame to the inspected ordinary callback-job table. Its worker invokes the stored callable, with optional context-entry and context-exit callbacks.

This job type differs from the receiver range job. Its local empty predicate returns false. Its reservation method locks the job, marks it done through the scheduler's removal helper, unlocks it, then invokes an optional reservation callback. Therefore the ordinary queue removes this one-shot callback job from scheduling at reservation, before executing its callback body.

The queue has already incremented the execution and outstanding-dispatch counts before calling the reservation method, as established in [the scheduler rearm audit](SCHEDULER_REARM.md). A done lifecycle state consequently does not mean the callable has returned.

```text
queue_reserve_callback_job(job):
    atomic_increment(job.outstanding_dispatches)
    atomic_increment(job.executions)
    lock(job)
    mark_done_and_remove_from_scheduler(job)
    unlock(job)
    run_optional_reservation_callback(job)

execute_callback_job(job):
    run_optional_context_entry(job)
    job.bound_callable(job.bound_receiver)
    run_optional_context_exit(job)
    finish_dispatch(job)
```

This is an explanatory combination of separate routines, not a recovered single function. The existing finalizer gate still requires zero executions before releasing outgoing dependencies. The ordinary successor-release protocol starts pending work only after its dependency holds fall to zero.

## Why this protects the ordinary receiver batch

On the inspected ordinary receiver path, an early worker exit with receivers still unclaimed leaves the empty predicate false. That alone cannot normally finalize the receiver job and release its successors. Once all ranges are claimed, count zero can permit the done transition, but finalization still waits for the execution count to reach zero.

Combining that local rule with the newly joined dependency path yields:

```text
receiver job empty AND all its dispatched worker bodies returned
    -> receiver job ordinary finalizer releases successors
    -> action graph reaches its terminal
    -> downstream frame dependencies complete
    -> EndFrame callable executes
    -> dependency preparation
    -> submit next root request
```

Under those conditions, the next gather reached through the next ordinary request follows the previous receiver callbacks. The exclusion comes from dependency completion and the position of the EndFrame callable in that graph. The preparation helper itself still contains no wait for receiver execution.

The next root can be submitted while the EndFrame callable is still executing and before EndFrame's own dispatch bookkeeping finishes. That is compatible with this narrower result: prior action receiver bodies have already completed. It does not establish that every engine subsystem is idle, that frame requests never overlap at any point, or that all engine storage can be replaced then.

## What remains conditional

This pass closes the previously missing ordinary rearm caller. Several stronger claims remain unproved:

- Alternate dependency-release paths may propagate without executing the ordinary action path. Their skip/reset semantics must be audited separately before extending this proof to all branch outcomes.
- Startup submits the engine root through another routine. The ordinary repeating EndFrame chain is not a universal caller inventory.
- The event branch may stop or change repeated submission; its handshake has separate receiver and state requirements.
- The selected player's world must still be joined to the eligible-world list for a player-specific live claim.
- Faults, direct helper invocations, cancellation and unusual scheduler state transitions require their own reachability checks.

The companion [root-to-Step route audit](ENGINE_ROOT_STEP_ROUTE.md) identifies the mode gates selecting Step versus a bypass. The storage-ordering argument here applies to the selected ordinary Step topology; root submission alone is not evidence that the action gather will run.

This is also not a deterministic stepping interface. It identifies an ordinary storage-lifetime ordering for the action receiver batch, not a guarantee of fixed substep count or input timing.

## Verification

The callback binding, names, constructor table, reservation method, worker method and dependency setup were decoded from the analyzed image. The preparation/submission callback's complete 99-byte function has SHA-256 `4d62e63b416df9897fe7c8d65cfba90829b40dcc92be154c8ad1118589764e90`. The 162-byte binding span has SHA-256 `8af5d968af0ef5328db14bb7fcb263ef07add7aba711e73b2aa9ae9bb7f14bfe`. The 126-byte completion-join/fanout setup span has SHA-256 `2f953a70fb9b1f36541163e9180bc13104915cf56e61c4ca5a1d8107a32e1a0a`.

The image SHA-256 is `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. Hashes identify the reviewed evidence without distributing executable bytes. No game was launched, attached to or modified. Static dependency registration supports the stated ordinary path; it is not a live trace of every mode.
