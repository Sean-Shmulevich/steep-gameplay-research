# Mixed scheduler: executable contract and remaining boundaries

[The mixed scheduler](../../engine/mixed_scheduler.py) now combines ordinary range jobs, one-shot callback jobs, synchronous terminal nodes and conditional nodes in one executable serial model. Normal release resolves each successor's begin immediately, before advancing to the next successor. Alternate release resolves bypass callbacks recursively and preserves its different active-flag ordering. These are connected operations, rather than independently evaluated counter examples.

The model is grounded in [rearm and completion](SCHEDULER_REARM.md), [range claiming](SCHEDULER_BATCH_EPOCH.md), [alternate propagation](ALTERNATE_DEPENDENCY_RELEASE.md), [callback reservation and EndFrame](ENGINE_LOOP_HANDSHAKE.md), and [explicit helping](WAIT_HELPER_DISPATCH.md). It is not a concurrent replacement for the original engine scheduler. Deterministic queue selection, handler registry, topology restrictions, error handling and resource bounds are explicit adapter decisions.

## Four job kinds are necessary

| Kind | Begin behavior | Dispatch/completion behavior |
| --- | --- | --- |
| `range` | Snapshot requested into started, activate successors; queue nonempty work or finalize the empty branch | Claims reduce remaining before callbacks; done on empty, finalization waits for zero executions |
| `callback` | Same ordinary begin prefix, but empty predicate is always false | Queue reservation marks done and removes it from the queue before executing the stored callable; finalization still waits for return accounting |
| `terminal` | Snapshot requested, activate and normally release outgoing dependencies, return to unscheduled | Synchronous dependency operation; no range-worker reservation or body |
| `conditional` | Evaluate its supplied predicate; alternate-release unselected route before normally releasing selected route | No ordinary begin's request snapshot, queue insertion or worker body is added |

Conditional activation processes primary completely, including descendant activation, before processing secondary. For either list, inactive activation adds its direct holds, sets active, then propagates. An active list is revisited only when the parent's incoming force flag requests it. Child activation still receives false; that incoming flag is not forwarded unchanged. This ordering follows the inspected conditional activation method and successor walker.

Alternate callbacks for ordinary/range/callback/terminal fixtures recheck holds and propagate through their one outgoing list. Conditional alternate callbacks recheck holds and bypass both lists without evaluating a predicate. These kinds represent the inspected bindings; they are not a promise that all native subclasses behave the same way.

## State ownership and public API

Construct `MixedScheduler(definitions, handlers=None, trace_capacity=4096, max_transitions=10000)`. Each definition requires `id` and `kind`. Common fields are `successors`, `credit_recipients`, `credit_gate` and `credits`. Conditional nodes additionally accept `secondary`, `secondary_credits`, and either a versioned `predicate` handler or an explicit Boolean `condition`. Range nodes accept a JSON `receivers` array, `chunk_size`, `tail_threshold` and `max_concurrency`. Range/callback nodes can name a `handler`; without one, their invocation is symbolic and still traced.

The registry maps a handler name to `{version: "caller_revision", callback: callable}`. Body callbacks receive `(context, receiver)`; callback-job receivers are `None`. Predicates receive `context` and must return a Boolean. Finite JSON results are accepted. Version labels are caller-supplied identity metadata, not a proof of equivalent code or closure state.

| API | Contract |
| --- | --- |
| `activate(job, recurse=False)` | Activate the selected job's lists using its kind; does not submit or execute work |
| `submit(job, context=None)` | Apply the inspected UNSCHEDULED request gate and dispatch the selected begin immediately when holds are zero |
| `ready()` | Inspect the adapter's queue-order eligible jobs; no advancement |
| `reserve(job=None)` | Increment executions and outstanding dispatches before reservation effects; return an immutable dispatch token |
| `claim_range(token)` | Apply the recovered tail-claim arithmetic; return an immutable range token or no range |
| `execute_range(token, range_token, context=None)` | Visit retained receiver indices in reverse order within that range; leave dispatch accounting active |
| `execute_callback(token, context=None)` | Execute exactly one reserved callback body; leave dispatch accounting active |
| `finish_dispatch(token, early_exit=False, context=None)` | Apply execution decrement, done/finalizer checks, successor effects, then outstanding decrement |
| `dispatch_next(context=None)` | Reserve and execute one eligible dispatch, ordinarily exhausting that range worker's claims |
| `run_ready(context=None, max_dispatches=1000)` | Repeat bounded dispatches; reaching the bound is not a claim that the graph finished |
| `prepare_range(job, receivers)` | Replace caller-owned receiver storage only while that target is UNSCHEDULED with no executions/outstanding dispatches |
| `snapshot()` | Copy counters, lists, queue, live dispatch descriptions, registry versions, faults and bounded trace |

Conditional roots require explicit activation before direct submission. Ordinary begin activates its own outgoing list. Topology is fixed for the instance, while range storage can be replenished at the declared gate. Held jobs may be prepared: dependency holds and active outgoing lists do not themselves represent in-flight worker access. The target's execution accounting, rather than all engine jobs being idle, guards this adapter operation.

Live Python callback frames and external context are not serialized. Snapshots are inspectable JSON, not a resumable mid-callback checkpoint or a source of reusable live tokens. Dispatch/range tokens belong to one instance, require exact integer fields, and become invalid when the dispatch returns. Boolean or floating-point aliases of integer fields are rejected before mutation.

## Return order is explicit

The model implements this selected ordinary completion sequence:

```text
finish_dispatch(job):
    executions -= 1
    if state == SCHEDULED and range_empty:
        remove_from_queue()
        state = DONE
    if state == DONE and executions == 0:
        release_normal_successors_immediately()
        state = UNSCHEDULED
    outstanding_dispatches -= 1
```

Normal release clears the source list before processing successors. Each last-hold request/credit decision invokes that successor's selected begin synchronously. Credit-recipient processing follows the normal successor loop. Alternate release keeps the source list active through descendant traversal and clears it afterward. No generic “all predecessors completed” rule substitutes for these different operations.

The [multiple-claim test](../../tests/test_engine_mixed_scheduler.py) reserves two range dispatches, claims the entire receiver array, then delays both callbacks. Remaining becomes zero while executions and outstanding dispatches remain two. Returning the first dispatch marks the range job done but does not release its successor. Only returning the last dispatched worker reaches finalization. The successor can begin while the predecessor's final outstanding decrement is still pending.

An explicitly modeled early worker exit can leave remaining positive. Its return does not finalize the range job or release successors. A later dispatch can claim the rest. The adapter accepts `early_exit=True` as a caller-supplied observation; it does not name or synthesize the native shared values that trigger that exit.

## EndFrame may submit the next root before returning

There is deliberately no global “all jobs drained” precondition on `submit`. A versioned EndFrame callback can submit an UNSCHEDULED root while EndFrame is DONE with executions and outstanding dispatches still one. The root can become SCHEDULED before EndFrame's own callback return and final bookkeeping.

This is a material part of the [recovered ordinary loop](ENGINE_LOOP_HANDSHAKE.md). Requiring the entire previous request to drain before allowing any new submission would erase it. The prior action receivers can have returned even though EndFrame is still executing. Graph-wide idle, receiver-storage eligibility and the UNSCHEDULED submission gate are different conditions.

[The runnable three-cycle probe](../../engine/examples/mixed_scheduler_probe.py) combines a root callback, conditional motion path, range job, bypass terminal, join terminal and EndFrame callback. The middle cycle bypasses motion. EndFrame submits cycles two and three while its own accounting remains positive. The probe completes three cycles with four receiver visits, none in the skipped cycle. Its topology and handlers are synthetic; the local rules they exercise are the recovered part.

Run it with `python3 -m engine.examples.mixed_scheduler_probe` from the repository root.

## What is implemented by choice

The adapter runs serially and uses deterministic queue insertion order. `max_concurrency` caps simultaneous retained reservations by the modeled execution count. It is an adapter bound, not a complete implementation of native category selection, priority or the separate working/reservation bookkeeping. Delayed tokens permit explicit interleavings without creating native worker threads.

Definitions are limited to 128 jobs and receiver arrays to 100,000 elements. Static dependency cycles are rejected, including credit edges. Callback-driven repeated root submission remains possible and is bounded by `run_ready`'s dispatch count. Recursive synchronous transitions have a separate budget. The trace has explicit drop accounting; a full trace buffer does not silently claim completeness.

Handler exceptions and transition-budget exhaustion cause a visible fail-stop fault. They do not fabricate native catch/finally behavior or falsely finalize an interrupted callback. Already performed external context effects are not rolled back. Inspect the fault and construct a fresh instance; no forced decrement or unsafe reset is exposed as a native operation.

## Exact limits on native compatibility

These missing or intentionally excluded pieces prevent a claim that the model is the complete native scheduler:

1. **Category/priority selection and worker reservation accounting.** The ordinary route's ordering is known, but its complete eligibility, routing, optional reservation callbacks and separate working fields are not implemented here.
2. **Thread-local execution/profiling context and platform locks.** Recursion is immediate Python execution. No atomic memory-order, recursive-lock, thread-affinity or concurrent publication equivalence is claimed.
3. **Helping versus queue dispatch.** The inspected helper increments counts but bypasses reservation and concurrency-limit checks. This model only exposes the ordinary queue route. Applying that helper to an always-nonempty callback job would require a separately proven protocol.
4. **Dynamic topology rebuilding and every native job subclass.** Static definitions avoid active registration/removal and world-list mutation. Receiver methods must be inspected before assigning a supported kind.
5. **Exceptional unwinding, shutdown and event/startup modes.** The ordinary EndFrame chain is joined; it is not an exhaustive caller or cancellation inventory. The event branch, startup and destroyed-owner handling need their own contracts.
6. **Frame/substep/input identity.** Job request counters are not global frame IDs. The model does not connect input ingestion to a particular native substep or turn a Boolean predicate into a fully understood pause state.
7. **Native storage lifetime.** The owned `prepare_range` gate is useful for fixtures, but it does not pin a native allocation or prove live registration ownership. The selected player/world membership remains a separate runtime join.

These limits do not prevent using the connected model to test graph logic, dependency order, pending requests, branch bypass, delayed reservations and callback resubmission. They define the evidence required before mapping those tests back to a particular original-game mode.

## Validation

[Fourteen focused tests](../../tests/test_engine_mixed_scheduler.py) cover delayed multiple claims, done-on-reservation callbacks, mixed reconvergence, immediate normal recursion, conditional activation order, credit wakeup, positive-count early exit, tail-claim arithmetic, stale/forged tokens, fail-stop errors, bounded traces, repeated requests and EndFrame overlap. The three-cycle probe is also exercised by the suite.

Run `python3 -m unittest discover -s tests -p 'test_engine_mixed_scheduler.py'`. These are synthetic execution tests against inspected local contracts, not native gameplay traces or whole-engine determinism proof.

The [explicit helper API](WAIT_HELPER_DISPATCH.md) adds bounded range helping separately from ordinary queue reservation. It preserves empty-versus-drained predicates and explicitly leaves native TLS and owner protection unresolved.
