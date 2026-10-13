# Engine event consumer and stop request

This pass connects the engine-owned handle in [Engine end-of-frame event branch](ENGINE_EVENT_SUBMISSION.md) to a concrete consumer. It also identifies a writer that selects the alternate end-of-frame route. The resulting structure supports a stop-request / end-of-frame notification / wait interpretation. Protected platform adapters and one outer virtual callback still prevent a complete synchronization contract.

## The request writer is the same engine owner

A request routine performs several service operations, writes a separate global request flag, loads the established global engine-owner pointer, and, if that pointer is non-null, sets its alternate-mode byte. This is the exact byte tested by the end-of-frame callback; the relationship does not depend on matching an unrelated structure offset.

```text
request_engine_stop_candidate():
    perform_request_side_service_operations()
    global_request_flag = true
    engine = global_engine_owner
    if engine is not null:
        engine.alternate_mode = true
```

The write is an ordinary byte store. The inspected routine contains no event wait after this write and does not directly submit another root job. Its service operations precede the write, so their duration or side effects cannot be collapsed into the store itself.

Two direct callers were verified: a branch of an outer command dispatcher, and a routine that performs service calls and invokes the request only when a predicate returns nonzero. The command's external meaning and the predicate's semantics remain unassigned. These callers prove the request routine is reachable without establishing which user action selects it.

## Exact handle consumer

The consumer loads the same global engine owner, passes the address of its inline event holder to a helper, and clears the owner's start flag after that helper returns. Unlike the request writer, this consumer has no visible null-owner guard.

The helper loads the stored handle, supplies `0xffffffff` as its second argument, and enters another protected platform adapter. The argument pattern is consistent with an infinite event wait. The exact platform API, returned status and error behavior are not decoded.

```text
consume_engine_event():
    engine = global_engine_owner
    protected_handle_operation(engine.event.handle, 0xffffffff)
    engine.start_flag = false
```

The start flag is the same byte set by the earlier start/restart routine. It is distinct from alternate mode. Clearing it after the protected call is recovered ordering; treating it as an independently sufficient idle or completion predicate is not established.

## Outer start / callback / consume sequence

A larger outer routine preserves an interface object supplied by its caller. On the inspected path it invokes that interface, starts the engine cycle, invokes another method on the same interface, then calls the exact event consumer before proceeding to cleanup.

```text
outer_run(interface):
    # Initialization and other operations omitted.
    interface.before_run()
    start_engine_cycle()       # Clears alternate mode, reset-candidate, root submit.
    interface.run_callback()   # Concrete implementation not yet identified.
    consume_engine_event()    # Exact owner-held handle, then clear start flag.
    continue_outer_cleanup()
```

`before_run` and `run_callback` are descriptive placeholders, not recovered original method names. Their virtual slots and receiver identity are established. The latter callback's implementation remains unresolved, so this pass cannot claim that it runs a message loop or issues the stop request itself.

Combining this with the previous evidence gives the following conditional interpretation:

1. Start clears alternate mode, performs the reset-candidate operation, and submits the root job.
2. Ordinary end-of-frame callbacks prepare dependencies and resubmit the root while alternate mode is clear.
3. The request writer sets alternate mode on that same engine owner.
4. An end-of-frame callback that observes the set byte still performs preparation, then selects the event operation instead of root resubmission.
5. After its outer callback returns, the outer routine consumes that same event and clears the start flag.

Steps 1–5 describe verified caller/state relationships. Calling the platform operations *reset*, *signal* and *wait* remains an interpretation until the protected adapters are resolved. The request-to-observation delay is not quantified. A request arriving after one end-of-frame test could leave another ordinary submission already selected.

## What this closes and what it does not

The event is no longer an ownerless notification lead: its consumer, restart-side operation, end-of-frame operation and request byte all join through the exact engine owner. The visible outer path consumes it after the interface callback and before subsequent cleanup.

This is not a safe single-step API yet. Remaining release gates are concrete:

- Resolve the protected handle operations, including status/error behavior, before relying on event signaling or waiting guarantees.
- Identify the outer interface's concrete `run_callback` implementation and its relation to the request writer.
- Establish visibility and ownership rules for the plain alternate-mode store. No cross-thread synchronization guarantee follows from the byte access alone.
- Prove which outstanding scheduler work is covered when the end-of-frame event operation occurs. An event consumer is not automatically a drain of all unrelated jobs.
- Recover handle destruction and owner lifetime across cleanup/restart. The consumer assumes a valid global owner.

In particular, preparation still precedes the end-of-frame branch test. This new consumer does not insert an earlier wait into that callback or establish that arbitrary external graph edits are safe while the game is running.

## Static evidence

The request writer, its two direct callers, the handle consumer, its helper, and the outer caller's start/callback/consume sequence were decoded from the analyzed image with SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. Receiver links were checked through the common global pointer and explicit member-address computation. No original-game execution, attachment or emulation was performed for this pass. No raw executable material is included here.
