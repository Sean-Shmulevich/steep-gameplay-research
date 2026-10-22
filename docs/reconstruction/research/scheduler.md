# Scheduler and input publication contract for reconstruction

This pass reviewed the local scheduler, input, backend, and recorder evidence. It did not launch a game, attach a debugger, deliver input, mutate game memory, or change another agent's files. This is an implementation contract and focused verification pass, not newly captured execution evidence.

## What reconstruction would buy us

A reconstructed engine gives us owned interfaces: explicit tick boundaries, input packets, reproducible scenarios, state checkpoints, material overrides, and animation/physics inspection. Those interfaces can support mods to **our implementation** without searching heap objects or injecting into a live scheduler. They do not make the original executable moddable automatically, and agreement inside the reconstructed engine does not establish agreement with the original.

The smallest useful next milestone is an owned headless snow simulation with explicit publication boundaries and trace records. Reconstructing the entire renderer, asset streamer, and original task scheduler is unnecessary for that milestone. Keep the original-game passive sampler as the external oracle and treat observations as asynchronous until execution-event attribution is established.

## Established producer/consumer flow

The following combines several already-supported relationships rather than upgrading one isolated report:

1. ActionGatherComponents invokes the physics service to build the post-physics component work array from two registration lists.
2. The registered graph connects gather through animation/ragdoll preparation, BeforeSimulation, then PhysicsWorldStep. A second normal-skeleton branch joins high-priority physics wrapup before final world completion.
3. Each world substep runs the selected snow-actor batch and waits, then backend integration, subsequent world work, and a second actor batch and wait.
4. The snow producer captures body velocity into its write cache **before that invocation's snow impulses**. Immediate impulses change linear/angular velocity; later backend integration changes pose about the center of mass.
5. A named AfterPhysicSimulationUpdate job is downstream of the outer world-step job. Its selected component route requests the player's pose, exchanges the read/write caches, copies the published velocity to the actor, and subsequently copies it to the motion state. Gates and exceptional zeroing paths remain material.
6. Live membership in that post-physics job was observed for the selected player before and after movement. Membership does not prove that a particular callback or swap ran during a particular observed update.

Sources: `runtime/testbench/run18/FINDINGS.md`, `run19/FINDINGS.md`, `run20/FINDINGS.md`, `run21/FINDINGS.md`, `run23/LIVE_RESULT.md`, and `run5/backend/findings.md` beneath `runtime/testbench`.

```text
# Conditional original-game flow; semantic names are explanatory.
gather_components():
    build_post_physics_work_from_registered_components()

# The graph imposes this predecessor chain; it is not a full global ordering.
after_ragdoll_and_animation_preparation():
    before_simulation()
    world_step():
        for substep in selected_substeps:
            snow_actor_batch_and_wait():
                apply_optional_body_corrections()
                write_cache.velocity = body.velocity
                advance_histories()
                apply_snow_forces_and_impulses()
                postprocess_body_velocity()
            integrate_world(substep.elapsed)
            following_world_work()
            second_actor_batch_and_wait()

after_high_priority_physics_wrapup():
    post_physics_component_job():
        if component_and_actor_gates_pass:
            dispatch_selected_player_motion_state():
                if selected_branch_uses_physics_pose:
                    exchange_cache_roles()
                    read_body_pose_under_lock()
                    actor.velocity = read_cache.velocity_or_zero_by_gate()
            apply_exceptional_velocity_guard()
            if snapshot_refresh_allowed:
                motion.cached_velocity = actor.velocity

# Separately, inside one selected player motion-update invocation:
motion_update():
    ingest_action_samples()
    prepare_shared_control_carrier()  # includes separate action sampling
    dispatch_motion_state()
# Its position relative to world substeps remains unresolved.
```

This ordering explains a body velocity differing from the three agreeing cache copies without inventing a fixed one-frame lag. A pose query must not become an unconditional publication operation in a new implementation.

## Preserve three different clocks

The derivative interval passed to snow can be the entire consumed outer interval, while the elapsed interval is the per-substep interval. Some charge/input work additionally uses an approximately 0.033 accumulator threshold, subtracts it at most once, and adds elapsed after snow work. That is not timestep subdivision and not an input packet generation.

For ordinary finite inputs, after the existing smoothing/frequency-selection stage, the recovered policy is:

```text
acc = f32(retained + frame_dt)
# Smoothing may cap acc at f32(0.06666667014360428),
# update a history ring, and select frequency from a table.
# Without smoothing frequency=120; policy==1 overrides it to 90.
if acc < f32(9.999999747378752e-6):
    clear retained, derivative_dt, inverse_dt, step_count, elapsed_dt
else if acc < f32(1 / frequency):
    n = 1; consumed = acc
else:
    q = f32(frequency * acc)
    n = floor(q)
    frac = f32(q - floor(q))
    threshold = f32(0.8) if policy != 0 else f32(0.5)
    if frac >= threshold:
        n += 1
        consumed = acc
    else if policy != 0 and frac >= f32(0.15):
        consumed = min(acc, f32(f32(f32(n) * f32(1.1)) / frequency))
    else:
        consumed = acc
    elapsed_dt = f32(consumed / f32(n))
# Single-step branch supplies elapsed_dt=acc directly.
derivative_dt = consumed
retained = f32(acc - consumed)
inverse_dt = f32(1 / consumed)
```

All arithmetic above is float32 at the documented operations. The full smoothing table and ring-order contract are in `runtime/testbench/run5/subdivision/findings.md`; this abbreviated description must not replace them in a compatibility implementation.

The live scheduler study observed smoothing enabled, a ten-entry ring, policy zero at capture endpoints, selected frequency 120, and both one- and two-step samples. Thus 120 is not proof of a fixed 1/120-second simulation. Source: `runtime/testbench/run6/README.md`.

## A drain predicate is not a safe pause button

The job distinguishes exhausted claims from completed callbacks. Its visitor caches its callback once per claimed range and invokes it in reverse component order. Updating the slot does not change callbacks already cached by workers. A zero active-adapter count cannot exclude a worker that fetched the adapter and has not entered it yet.

The known drain loop waits for state zero and signed outstanding execution/completion accounting nonpositive. Diagnostic strings establish states 0=Unscheduled, 1=Scheduled, 2=Done. “Done” is therefore not the same condition as fully drained in this path. Explicit wait can execute work using game thread-local state; it is unsuitable for arbitrary injected calls.

```text
drain_observation(job):
    state = load(job.state)
    memory_barrier()
    outstanding = signed_load(job.outstanding)
    return state == Unscheduled and outstanding <= 0
# This is a two-load observation; it neither blocks new submissions
# nor pins the owning scheduler's allocation.
```

The derived cleanup releases its owned work array before the conditional base wait. Upstream submission exclusion and ownership guarantees remain unresolved. This is a missing analysis precondition, not evidence of an original-game race.

Sources: `runtime/testbench/run24/FINDINGS.md` through `run29/FINDINGS.md`, especially run26's delayed cached-pointer fixture and run29's diagnostic state mapping.

## Minimal instrumentation plan

### Original-game observation

1. Reacquire process creation identity, active world, scheduler, selected player, component, and supported callback identities. Multiple schedulers can coexist, so a valid root alone is insufficient.
2. Start with a bounded passive recording of selected policy/timing fields and ownership guards. Record each field group's read interval and reject changing links. Do not call this atomic or infer callback execution from membership.
3. Before any event hook, close owner lifetime and exclusion of new submissions. Preserve a process-lifetime recorder allocation for an initial bounded experiment; this reduces reclamation risk but does not solve slot lifetime or installation safety.
4. If that prerequisite is established, record separate events for input ingestion, world-step entry, actor producer entry/exit, substep completion, post-physics component entry/return, cache exchange, and outer completion. Each record needs a capture epoch, thread identity, invocation identity, actor/world identity, event kind, local sequence, raw clock, and relevant step values. Keep nesting per thread.
5. Use committed records, nonwrapping capacity and explicit drop counts. Ticket reservation order is not cross-thread causal order. Use dependency edges and matched invocation/return pairs to infer causality. Any lost context event invalidates its affected interval.
6. Join the action-store source and version before making exact input-age claims. An OS key-delivery timestamp is not ingestion time. Existing consecutive-nonzero counters and history cursors are not commit generations.

No new hook, native execution or live capture was attempted here. The current recorder sink and callback adapter were tested in isolated fixtures, not installed as a live game tracing API.

### Owned reconstruction

Make publication explicit: `step(inputs, elapsed_dt, derivative_dt) -> committed_state`. Define a simulation tick/generation owned by the reconstruction and expose `load_scenario`, `set_inputs`, `step`, `snapshot`, and `trace`. Record RNG state, timers, control filters, contact histories, animation phase, and pending transitions in checkpoints. A transform-only reset is not a complete replay state.

Provide two timing modes: a deliberately fixed-step development mode and an evidence-based original scheduler policy mode. Label the fixed-step mode as our design. Keep rendering interpolation outside simulation advancement. Ordered single-thread execution is a practical reference oracle before introducing parallel jobs; replay inside it does not prove original multi-thread determinism.

Useful first acceptance cases: changing a pose query does not advance simulation; two publication reads do not exchange buffers; one- versus two-substep schedules preserve the elapsed/derivative distinction; pending callbacks prevent reclamation; capture overflow produces explicit invalidity; a world switch requires a new epoch; repeated identical input does not acquire a fabricated new original-game generation.

## Focused verification performed this pass

Read-only comparison against the frozen RVA-aligned image with SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2` verified 291 exported instruction spans from six selected files and four post-physics job table bindings. Files checked were the run28 base destructor, explicit wait, finish-execution and finalizer exports, plus run19 range visitor and range worker exports. No verification artifacts outside this report were modified.

This confirms retained static evidence consistency, not new function execution or complete scheduler coverage. The most productive unresolved join is still exact input-source freshness and ingestion placement; the most important prerequisite for modifying the original scheduler is owner lifetime plus exclusion of new submissions. Full engine reconstruction is not required to investigate either one.


## Outer world-loop instruction check

A [12-case instruction receipt](../../../native/snow_host/world_loop_validation.json)
executes the outer world-loop instructions with every called function intercepted.
It checks zero, one, two and five substeps, counter wrap, and synthetic changes to
the selected count at the second-batch return. Optional profiler branches are
disabled. The batch workers, waits and backend solver are not executed by this
check. Their contracts still come from the separate static research above.

The checked loop is more precisely expressed as:

```text
prepare_world_service()
i = 0
while unsigned(i) < load(selected_count):
    snow_batch_and_wait(world, load(elapsed), load(consumed))
    intervening_services()
    backend_prepare(world.backend)
    backend_integrate(world.backend, load(elapsed))
    backend_followup(world.backend)
    intervening_services()
    second_actor_batch_and_wait(world, load(elapsed))
    i = uint32(i + 1)
world.request_counter = uint64(world.request_counter + 1)
```

The selected count is reread at each loop condition. It is not a local immutable
snapshot in this function. Synthetic mutation from five to one ended after one
iteration; mutation from one to three continued through three iterations. This
is a check of load placement, not evidence that native code changes the count
mid-loop or permission to do so. Each relevant call reloads its scalar arguments;
intercepted callees deliberately clobbered the volatile scalar registers.

The world counter increments once on return even when the selected count is zero.
It also wraps modulo 2^64. Consequently a counter advance alone does not prove a
physics substep executed. Conversely, several actor invocations can share a
counter value while the loop executes multiple substeps. Capture group size is
still not a directly observed native substep index.

### What explains the observed worker migration

The [player-wrapper interval analysis](../CENTRAL_IMPULSE.md#player-update-intervals-and-worker-migration)
found no overlap across two captures, while neighboring invocations often ran on
different workers. The established batch-and-wait route explains how substeps
can be sequential without fixed worker affinity: the next iteration is reached
after the first batch, integration and second batch return.

That explanation is conditional on each batch's wait contract and the same outer
world invocation. It does not exclude duplicate actor records within one batch,
another caller invoking the same actor, or another subsystem writing its state.
A complete exclusion claim needs registration uniqueness, all relevant dispatch
routes, and matching live world/job identity. The outer loop has no per-actor
mutex in this checked body. Do not infer one from the absence of overlap.

The next discriminating trace should correlate the outer-loop invocation and
batch identity with the existing actor entry/exit records. It should retain
separate identities for the motion-ingestion invocation and input publication.
The conditional order above does not place device ingestion between substeps.
