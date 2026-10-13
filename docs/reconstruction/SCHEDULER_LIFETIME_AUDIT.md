# Scheduler construction and lifetime boundary

A focused static pass closed the timing-state constructor edge. The ten-entry smoothing history and enabled default are now supported by a concrete constructor path, not only the earlier live observation. This is a construction result for the inspected world scheduler; it does not establish every scheduler variant, later configuration change or safe submission-exclusion mechanism.

## Newly closed constructor relationship

The already identified world-scheduler constructor stores its supplied owner pointer, constructs its embedded jobs, then passes the embedded timing block to a separate initializer. That initializer creates the history storage and writes the following exact defaults:

| Field | Constructed value |
| --- | --- |
| Retained accumulated duration | 0 |
| Consumed/derivative duration | float32(1 / 90) |
| Reciprocal consumed duration | 90 |
| Selected frequency | 90 |
| History count | 0 |
| History next-write index | 0 |
| History oldest index | 0 |
| History allocation size | 40 bytes |
| Allocation alignment argument | 4 |
| History capacity | 10 when allocation result is nonnull; otherwise 0 |
| Substep count | 0 |
| Elapsed/per-substep duration | float32(1 / 90) |
| Smoothing enabled | true |

Allocation is delegated through two helpers. This pass establishes their arguments and the final result used by the timing object, not their complete allocator/failure semantics. No history sample initialization loop appears in the timing initializer. The logical count is zero, so a reconstruction can use a zero-filled storage array without claiming the original array was zero-filled.

```text
construct_world_scheduler(storage, owner):
    storage.owner = owner
    construct_embedded_jobs(storage)
    initialize_timing(storage.timing)
    register_job_dependencies(storage)
    install_callbacks(storage)
    return storage

initialize_timing(timing):
    timing.retained = f32(0)
    timing.consumed = f32(f32(1) / f32(90))
    timing.inverse_consumed = f32(90)
    timing.frequency = f32(90)
    timing.history_pointer = null
    timing.history_count = 0
    timing.history_next_write = 0
    timing.history_oldest = 0
    timing.history_capacity = 0

    allocation_context = allocation_helper(size=40, alignment=4,
                                           global_allocator_context)
    timing.history_pointer = allocation_finish(size=40, alignment=4,
                                               allocation_context)
    timing.history_capacity = 10 if timing.history_pointer != null else 0
    timing.step_count = 0
    timing.elapsed = f32(f32(1) / f32(90))
    timing.smoothing_enabled = true
```

Helper names above are descriptive placeholders. The owner is stored directly in this local constructor. No reference acquisition, release policy or lifetime guarantee should be inferred from that store.

## Important corrections for a stepping API

A freshly constructed scheduler has **zero substeps but nonzero duration fields**. A probe that treats nonzero elapsed duration as proof of pending or running work will misclassify this state. Use the generation, dispatch state and job completion relationships instead.

The startup frequency of 90 does not prove external policy one. The first timing update can overwrite it using the smoothing table, or force 120 when smoothing is disabled, followed by the external policy-one override. Constructor defaults and steady-state timing selection are separate stages.

The initialized ten-entry ring qualifies the [smoothing audit](SCHEDULER_SMOOTHING_AUDIT.md): capacity ten is statically supported for this constructor. It remains caller-owned storage in the timing producer, and later resize/reset/toggle writers remain untraced. A compatibility checkpoint must carry count, both cursors, capacity and chronological sample contents; reconstructing only a frequency loses history.

A null allocation result records zero capacity while leaving smoothing enabled. The timing producer assumes usable storage and a valid capacity. This pass does not establish whether an outer allocator throws, aborts or makes that state unreachable. An independent implementation should reject unavailable history storage before timing evaluation; that is explicit safety behavior, not a claimed recovered recovery branch.

## What this does and does not close about lifetime

Construction now connects the world scheduler's supplied owner, embedded jobs and timing storage. The existing scheduling research separately establishes the substep callback and local completion paths. Together they identify useful state to expose in a future owned stepping interface.

They still do not supply a safe original-engine pause operation. The missing boundary is exclusion of **new submissions and owner destruction**, followed by generation-correct drain and stable publication. Reading an idle/drained predicate cannot acquire that exclusion. Likewise, retaining a raw owner pointer cannot pin its allocation or detect a destroy-and-reuse cycle.

A designed reconstruction may implement the following protocol, clearly as its own lifecycle contract:

```text
request_pause(world_generation)
    stop accepting new submissions for that generation
    retain owner until outstanding work and readers finish
    drain accepted jobs and verify completion generation
    publish immutable completed-state snapshot
    acknowledge_paused(world_generation, completed_tick)

step_once(paused_token, input_packet)
    validate owner generation and paused ownership
    admit one bounded update under the same submission gate
    complete jobs and publish state
    return to paused state before acknowledging completion
```

The constructor research does not establish the original game implements this protocol. For original-engine instrumentation, the next useful static work is identifying the owner teardown path and every submission entry that must share the exclusion gate. A live sample of a zero counter cannot replace those proofs.

## Verification and bounds

The saved world-scheduler constructor export was independently checked against the studied image: all 746 listed instructions matched. The timing initializer was newly disassembled within its exception-table function bounds, 170 bytes. Constants one and ninety were read from the referenced scalar locations. No game or debugger was started, no process state changed, and no executable bytes are distributed here.

Studied image SHA-256: `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.

World-scheduler constructor window SHA-256: `085d70e33f6a451c713db559d4dfc2af4c6b4a2417daa999f244e14d4d2b7869`.

Timing initializer SHA-256: `a9e519bfecf5cbe9e26969dd2d8a6e091e82729d340129047355286da2828979`.

The [scheduler research](research/scheduler.md) retains the surrounding task and ownership context. This pass did not establish policy writers, teardown synchronization, exclusion or a whole-engine barrier.
