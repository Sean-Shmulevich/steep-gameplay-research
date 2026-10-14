# Engine owner and event destruction boundary

The engine's inline event holder is joined to construction, start, end-of-frame notification and consumption. This pass does **not** recover the matching engine-owner destructor or prove that the event remains alive through every stop/restart path. It narrows that gap and excludes a nearby teardown routine that belongs to another object.

This follows [the event consumer audit](ENGINE_EVENT_CONSUMER.md). No original-game execution, attachment or protected-code emulation was performed.

## Construction and retained state

The concrete engine-owner constructor passes the address of its inline event holder to the platform constructor wrapper. That wrapper stores the returned handle in the holder. The constructor then constructs the engine's embedded scheduler jobs and initializes its start and alternate-mode bytes to zero.

```text
construct_engine_owner(engine):
    engine.event.handle = protected_create_handle(arguments)
    construct_embedded_engine_jobs(engine)
    engine.start_flag = false
    engine.alternate_mode = false
    initialize_other_engine_fields()
```

The protected creation operation was later resolved to `kernel32.dll!CreateEventA`, with its result stored unchecked ([live capture](ENGINE_EVENT_ADAPTER.md#creation-close-candidate-and-live-owner-state)). The recovered storage is one handle field in an inline holder; no reference count or ownership token is added by the inspected wrapper.

Start, end-of-frame and consume operate on that same holder. Start sets the start flag and clears alternate mode before its reset-candidate operation and root submission. Consume loads the global engine owner, performs the protected handle operation, then clears start. Neither inspected path clears the stored handle or nulls the global owner pointer.

```text
consume_engine_event():
    engine = global_engine_owner
    protected_consume(engine.event.handle, infinite_timeout_value)
    engine.start_flag = false
    # No recovered owner release, handle clear or global-pointer clear here.
```

The start flag therefore cannot be substituted for a reference count or handle-validity test. Its clearing records ordering after the consume helper returns, subject to that helper's unresolved status semantics.

## Candidate holder destruction is not yet bound to this owner

A small holder helper loads the handle through its receiver and calls a protected target. Ordinary object teardown routines invoke this helper on their inline event holders, making it a close/destruction candidate. The protected operation was later resolved to `kernel32.dll!CloseHandle` ([live capture](ENGINE_EVENT_ADAPTER.md#creation-close-candidate-and-live-owner-state)); the identity join to the engine holder below is still missing.

```text
candidate_destroy_holder(holder):
    protected_handle_operation(holder.handle)
```

A bounded direct-call scan located 31 call/jump candidates to this helper in the ordinary code section. The reviewed candidates did not establish a call with the concrete engine's holder as receiver. One nearby destructor-like routine writes its own object table and tears down a holder followed by many embedded members. Its holder belongs to a different object layout and is not the engine's holder. Reusing that destructor because it is nearby would create a false identity join.

Likewise, no engine-owner destructor table binding or complete deallocation path was recovered in this pass. The engine constructor's embedded job tables identify the jobs' implementations, not a deleting destructor for the containing owner.

## Consume precedes cleanup, but cleanup is not yet owner destruction

The inspected outer routine calls the exact event consumer, then enters several service cleanup operations. Its first direct post-consume helper conditionally calls a service method, calls another service helper and tail-calls an output/reporting-related routine. That local sequence has no direct engine-holder destruction or global-owner clear.

Later cleanup includes virtual service calls and protected targets. Their presence prevents a negative whole-program conclusion. The visible ordering can be stated as:

```text
outer_interface_callback_returns()
consume_engine_event()
post_consume_service_work()
additional_cleanup_with_unresolved_callees()
```

It cannot yet be rewritten as `wait_until_every_job_finishes(); destroy_engine(); close_event()`. In particular, EndFrame performs its event operation from inside its callback, before that callback's own completion bookkeeping returns through the scheduler. A consumer return alone is not proof that every possible owner reference or dispatch has disappeared.

## Exact remaining lifetime obligations

The next necessary identity join is a destroy/release call whose receiver is the same engine owner, or a demonstrated process-lifetime allocation policy for that owner. Neither is established here. A complete contract must then show:

- which call stops future root submissions and prevents another restart during destruction;
- which completion condition covers pending and executing uses of the owner;
- when the event holder is closed relative to the consumer and EndFrame callback;
- when the global owner pointer is invalidated, if it is invalidated at all;
- how failed creation, consumption or close operations affect those transitions.

These are unresolved proof conditions, not assertions that the original engine mishandles them. The lack of a destructor in this bounded search does not imply an immortal owner or a leak.

## Verification scope

The concrete owner constructor, holder constructor wrapper, candidate holder teardown wrapper, exact consumer and immediate outer post-consume path were decoded from the analyzed image. Its SHA-256 is `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.

The direct-call scan and established global-owner reference searches do not cover every indirect dispatch, protected caller, alias or inlined teardown. No raw executable material, machine-local path or unsupported destructor binding is included in this document.

## Later static and live narrowing

The engine constructor has no direct call or pointer reference in the ordinary code section, and the global owner slot has no plain store there. Both its invocation and owner publication are therefore reached from protected code. A full direct-call scan of the `CloseHandle` wrapper still finds no engine-holder receiver. A live sample during gameplay showed a stable owner and handle. A process-lifetime owner remains consistent with every observation but is not proved.
