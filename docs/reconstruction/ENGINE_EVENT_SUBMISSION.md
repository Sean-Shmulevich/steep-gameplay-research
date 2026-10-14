# Engine end-of-frame event branch

The alternate branch in the [engine rearm caller](ACTION_REARM_CALLER.md) uses a handle stored in the engine owner. It does not submit the ordinary root job. The protected adapter was subsequently decoded and its live target resolved to `kernel32.dll!SetEvent`; see [the later capture](ENGINE_EVENT_ADAPTER.md#live-target-resolution). The restart-side `reset_candidate` and consumer adapters were later resolved to `ResetEvent` and `WaitForSingleObject` ([handshake capture](ENGINE_EVENT_ADAPTER.md#live-handshake-resolution)). Returned status, lifetime and scheduler-drain guarantees remain separate questions.

## Recovered receiver and operation order

The engine constructor initializes an inline, pointer-sized handle holder before constructing the root scheduler job. Its constructor receives two false boolean arguments. The helper transforms these into the four platform-call arguments `(null, 1, 0, null)` and stores the returned value in the holder. The holder is a member of the engine owner, not a per-world action object or a temporary allocated by each submission.

The end-of-frame callback retains the same owner receiver across preparation and branch selection. Before preparation it also invokes several service callbacks; their effects are outside this local account.

```text
construct_engine_event(engine):
    # Exact argument transformation; platform_create remains unresolved.
    engine.event.handle = platform_create(null, 1, 0, null)

end_frame_tail(engine):
    prepare_engine_dependency_links(engine)
    if engine.alternate_mode == false:
        ordinary_scheduler_submit(engine.root_job)
    else:
        event_operation(engine.event.handle)
```

The alternate helper loads the handle from the holder and transfers control to a protected adapter. No ordinary scheduler submission, requested-count increment or dependency traversal is visible in that helper's exposed instructions. This establishes the branch separation; it does not establish the complete behavior of the protected adapter.

## Restart-side operation

A separate start/restart routine obtains the engine owner from its global slot. It sets an owner flag, clears the alternate-mode byte, performs another platform operation on **the same handle**, optionally performs engine setup, and then submits the root job.

```text
start_engine_cycle():
    invoke_outer_service()
    engine = global_engine_owner
    engine.start_flag = true
    engine.alternate_mode = false
    reset_candidate(engine.event.handle)
    if engine.setup_gate == false:
        setup_engine(engine)
    ordinary_scheduler_submit(engine.root_job)
```

`reset_candidate` is deliberately a provisional name. It is a distinct one-handle operation reached through a protected adapter. The visible caller ignores its result. Neither this routine nor the alternate end-of-frame tail allocates a replacement event holder.

The constructor arguments match the shape of an unnamed, manual-reset, initially unsignaled Windows event. Other callers use the alternate helper at worker-notification sites and at both the entry and exit of a thread routine. Together these support **signal on end-of-frame / reset on restart** as a strong interpretation. Exact platform targets, failure behavior and any implicit blocking still require resolution. No API name is treated as recovered here.

## Lifetime and wait boundary

The confirmed lifetime is ownership by the engine object: construction stores the handle; the end-of-frame branch and restart path reuse that member. This pass has not established its destruction/close path, duplicate-handle ownership, or behavior after platform creation failure.

An adjacent two-argument handle helper appears to test readiness and then use a caller-supplied parameter before testing a returned status against zero. Its protected transitions prevent a complete straight-line decoding. Bounded direct-call searches did not connect it to this engine event. It therefore cannot supply the missing engine wait boundary.

In particular, none of the findings proves:

- that a wait on this handle occurs before dependency preparation;
- that the alternate branch waits for receiver callbacks or outstanding range executions;
- that observing this event means every job in every world is idle;
- that clearing alternate mode is itself a safe graph-rebuild barrier.

The subsequent [consumer audit](ENGINE_EVENT_CONSUMER.md) identifies the alternate-mode setter, exact handle consumer and outer start/callback/consume sequence. Resolving the protected signal/reset targets is a separate, concrete prerequisite for importing operating-system event semantics into the reconstruction. A matching function signature is insufficient to establish synchronization guarantees.

## Evidence and reconstruction boundary

The engine constructor, end-of-frame branch, restart path, handle constructors and exposed platform adapters were inspected in the same analyzed image, SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. Cross-callers corroborate the notification interpretation, not the exact operating-system target. Protected adapters contain transformed control flow; linear disassembly after such a call is not assumed to represent the actual continuation.

A reconstruction may expose explicit `signal`, `reset` and `wait` interfaces as its own synchronization design. Those interfaces must remain labeled a design choice until the original handle consumers and adapter targets are closed. No original game was launched, attached to or modified for this pass.

## Later adapter decoding

The [bounded adapter experiment](ENGINE_EVENT_ADAPTER.md) reduced the EndFrame handle operation to a single encoded target-slot read plus a fixed addition, with a verified synthetic tail-transfer convention. The analyzed slot itself decodes to an invalid address; the running process's target must still be read and identified. This narrows the protected-call blocker without promoting the signal interpretation to a confirmed API.

The subsequent [live target capture](ENGINE_EVENT_ADAPTER.md#live-target-resolution) closes the EndFrame operation's API identity as `SetEvent` for the observed Wine session. Earlier provisional signal wording records the prior evidence boundary. It does not apply to the now-resolved target identity, but failure behavior and the reset/wait operations remain unproved.
