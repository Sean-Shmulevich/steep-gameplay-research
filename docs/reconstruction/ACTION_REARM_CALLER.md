# Action graph caller and engine-step integration

This pass moves the unresolved rearm boundary outside the individual world's action graph. A concrete world adapter connects its conditional entry and terminal to an outer chain of eligible worlds. That chain is rebuilt by a callback labelled `Engine::EngineLoop::Step`. The engine's preparation routine also clears cached terminal dependencies before a root submission path. None of the inspected clearing helpers waits for prior receiver callbacks to finish.

The subsequent [EndFrame audit](ENGINE_LOOP_HANDSHAKE.md) identifies the repeating caller and closes the ordinary dependency path before preparation and repeated submission. Alternate modes and stronger global-exclusion claims remain separate. The [previous rearm audit](SCHEDULER_REARM.md) established ordinary worker completion accounting; this document does not turn that local result into a universal engine-loop barrier.

## A world adapter joins the exact conditional wrapper

A short leaf adapter loads the action graph from its world receiver, selects the already identified action conditional wrapper and tail-calls a generic wrapper-link helper. This closes the previously missing runtime receiver relation: the adapter receives the world whose graph contains the candidate receiver batch.

The wrapper-link helper obtains the separately allocated conditional entry and the inline terminal. Under the terminal's job lock, it clears that terminal's outgoing dependency list. It then invokes the supplied predecessor's successor-registration method with the conditional entry and returns the terminal.

```text
append_world_action(predecessor, world):
    wrapper = world.action_graph.action_conditional_wrapper
    entry = wrapper.allocated_conditional_job
    terminal = wrapper.inline_terminal_job

    lock(terminal)
    clear_dependency_list(terminal.outgoing)
    unlock(terminal)

    predecessor.register_successor(entry)
    return terminal
```

The predecessor call is virtual. The ordinary successor-registration interpretation is supported by the scheduler methods already documented, but a complete outer-chain lifetime proof must retain each actual job binding rather than assuming all virtual implementations behave identically.

## Eligible worlds form a chain

The adapter has a verified direct callsite in an outer world-stage builder. The builder initializes an action-stage seed and stores it as the current tail. It walks an array of world handles in increasing array index. The handle supplies its pointer only when a signed metadata word is negative; a null resulting pointer skips the entry.

For each eligible world, the builder calls the adapter with the current tail and replaces the tail with the returned action terminal. A similar pattern builds several other world stages in the same routine.

```text
rebuild_action_world_chain(world_stages):
    tail = world_stages.action_seed
    clear_job_outgoing_dependencies(tail)

    for handle in world_stages.handles_in_array_order:
        world = handle.pointer if handle.signed_metadata < 0 else null
        if world is not null:
            tail = append_world_action(tail, world)

    world_stages.action_tail = tail
```

With two eligible worlds, the registered dependency chain is:

```text
action seed
    -> world A conditional entry
    -> world A action terminal
    -> world B conditional entry
    -> world B action terminal
```

Each conditional entry retains its internal primary and alternate routes. This diagram abbreviates those internal branches. It describes registered dependencies and their order; it does not identify world A as the selected player's world without the handle/actor join.

An empty eligible-world list leaves the seed as the tail. No fabricated world or action job is inserted for that case.

## The outer caller is an engine-step job callback

The world-stage builder is called by an engine-owner callback bound during setup to a job labelled `Engine::EngineLoop::Step`, with short label `Step`. The callback's receiver is the same engine owner used when its callable is installed. The callback returns immediately when its owner gate byte is zero.

On the enabled path it rebuilds the world stages, then connects them to the surrounding engine graph. The prior stage's tail becomes the predecessor of the action seed. The action tail is cached on the engine owner and receives two outgoing connections: a further world-stage seed and another engine job. Later connections continue through other stages. The callback finally activates its own outgoing dependencies through its virtual activation method.

```text
engine_step_callback(engine):
    if not engine.rebuild_gate:
        return

    rebuild_world_stage_chains(global_world_stages)
    register_surrounding_engine_dependencies()
    prior_world_stage_tail.register_successor(action_seed)
    engine.cached_action_tail = action_tail
    action_tail.register_successor(next_world_stage_seed)
    action_tail.register_successor(engine_following_job)
    register_remaining_engine_dependencies()
    activate_step_outgoing_dependencies(force=true)
```

Names such as `engine_following_job` preserve unresolved semantics. The inspected edges establish where the action terminal goes without inventing the job's gameplay purpose.

## Preparation clears graph links, not worker execution

A separate preparation routine copies a byte from the world-stage owner into the engine's rebuild gate. If enabled, it clears outgoing dependency lists for several engine jobs and cached stage terminals, including the cached action tail. It then nulls the cached terminal pointers and reconstructs starter dependencies. It performs additional dependency preparation outside that gate as well.

The clearing helper takes a job lock and delegates to a dependency-list helper.
The [later clear audit](ALTERNATE_DEPENDENCY_RELEASE.md#destructive-list-clear-has-a-diagnostic-boundary)
identifies an INT3 diagnostic before active-list processing; the active effects
below require continuation past that boundary. That helper may process an active list through the alternate release route, then clears its active flag and entry count. It does not poll execution count, outstanding dispatches or the receiver batch's remaining count. The alternate release route's recursive semantics are a separate audit.

A reviewed submission routine calls this preparation and then either submits the engine owner's root job through ordinary scheduler submission or takes another branch through an event-related helper. Therefore the ordering directly visible here is:

```text
prepare_engine_dependency_links(engine)
if engine.selects_ordinary_root_submission:
    submit(engine.root_job)
else:
    invoke_alternate_event_helper(engine)
```

The event helper's complete behavior is not assigned here. More importantly, no wait should be inserted before preparation in this pseudocode unless its caller is recovered. A lock used to mutate dependency links is not by itself proof that receiver ranges are no longer active.

## What remains to close

At this audit's original boundary, the caller or dispatcher invoking preparation again remained unidentified. The [follow-up](ENGINE_LOOP_HANDSHAKE.md) now resolves its ordinary EndFrame binding and dependency chain. The limits below describe what this audit alone did not prove:

- that the inspected root submission reaches the bound Step job under every mode;
- that completion of the current engine terminal is observed before preparation mutates cached action-terminal dependencies;
- that every world in the list is stable throughout rebuilding;
- how an early-exited receiver batch with remaining claims is resumed or discarded.

The useful next target is that outer engine-loop invocation and its completion/event handshake. Searching only for references to the world's action terminal would miss this level of indirection. The terminal is returned through the wrapper adapter, folded into a stage tail, then cached by the engine owner.

## Static verification and search limits

The adapter, generic wrapper-link helper, world-stage fold, Step callable binding, Step callback, preparation helper and ordinary submission branch were decoded from the same analyzed image. Its SHA-256 is `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. Retained setup exports corroborate the action wrapper's identity.

The world adapter is a leaf without an exception-directory function entry. Searching instruction bytes for its graph-member displacement exposed it; following only functions with unwind entries had missed it. The resulting branch target and caller were then decoded as instructions. Raw byte candidates alone were not treated as callsites.

Direct-call and pointer searches are bounded static searches. A missing direct reference does not exclude a callable assembled with a relative instruction, virtual dispatch or alias. No game was launched, attached to or modified for this pass.
