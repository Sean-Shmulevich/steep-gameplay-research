# Unselected branches release holds without starting their jobs

The alternate release left open in [scheduler rearm](SCHEDULER_REARM.md) is now resolved for the concrete receiver, gather, skeleton, terminal and conditional job tables inspected here. It propagates through an unselected route by removing dependency holds. It does **not** execute the ordinary job body, call ordinary begin, consume credits, or acknowledge a request as started.

This is a bounded static finding, not a live cancellation API or a proof of the action graph's complete request lifecycle. No game execution, attachment or mutation occurred.

## Alternate list release

The helper accepts a dependency-list object. Its local behavior is:

```text
release_alternate(list):
    if list.active != 1:
        return
    for successor in list.successors_in_stored_order:
        previous = atomic_fetch_add(successor.holds, -1)
        if previous == 1:
            lock(successor)
            successor.on_alternate_last_hold()
            unlock(successor)
    list.active = 0
```

The last-hold test uses the old atomic value. A transition from two holds to one performs no recursive callback. A transition from one to zero reaches the virtual callback under the successor lock. The callback checks the current hold count again, which matters if another owner has acquired a hold in the intervening interval.

The active byte is cleared **after** visiting successors. In contrast, the normal release path clears its list before visiting successors. Preserve that order in a compatibility model. It does not establish that reentrant topology mutation is supported; the helper snapshots its iteration bounds and the surrounding graph/lifetime policy remains relevant.

## Concrete successor behaviors

The inspected pointer-receiver job, gather job, skeleton job and inline terminal job all bind the alternate callback to the same small implementation:

```text
ordinary_on_alternate_last_hold(job):
    if job.holds == 0 and job.outgoing.active != 0:
        release_alternate(job.outgoing)
```

The conditional job binds a different implementation:

```text
conditional_on_alternate_last_hold(branch):
    lock(branch)
    if branch.holds == 0:
        if branch.primary.active != 0:
            release_alternate(branch.primary)
        if branch.secondary.active != 0:
            release_alternate(branch.secondary)
    unlock(branch)
```

A nested conditional reached this way bypasses **both** outgoing routes. It does not evaluate its predicate or select one route for normal execution. The extra lock is present even when the caller already holds the successor lock; this pseudocode describes observed nesting, not a prescription to use a non-reentrant host mutex.

These table bindings were checked in the analyzed image. They must not be extrapolated to every possible job subclass without inspecting that subclass's alternate callback.

## Requested and started counts remain distinct

Neither of these alternate callbacks reads or writes the requested/started counters. They do not set lifecycle state, decrement execution/outstanding-dispatch counters, inspect an empty predicate or call the finalizer. The list helper also does not perform the normal credit/defer checks.

For example, consider a nonexecuting job with one remaining hold, `requested = 7` and `started = 6`. Alternate release can remove that last hold and recursively release the job's outgoing holds while leaving both counters unchanged. Their mismatch survives; it is not a count of work currently queued, nor evidence that the job body has run.

That mismatch alone does not make the alternate path enqueue work. A later **normal** last-hold release or another supported request/start operation would have its own eligibility checks. This pass does not prove what the next action-graph request caller does with every such job.

The inline terminal job deserves particular care. Its normal begin snapshots its requested count and synchronously releases outgoing dependencies. Its alternate callback does neither of those normal-begin operations; it propagates alternate release through its outgoing list. Reaching a terminal by alternate recursion is therefore not the same event as observing normal terminal begin or waiting for all dispatched work to finish.

## Why branch release order matters

The conditional begin implementation first releases the unselected route through the alternate helper, then releases the selected route normally:

```text
conditional_begin(branch):
    lock(branch)
    selected = evaluate_predicate(branch)
    if selected:
        release_alternate(branch.secondary)
        release_normal(branch.primary)
    else:
        release_alternate(branch.primary)
        release_normal(branch.secondary)
    unlock(branch)
```

Suppose two pre-held paths reconverge at a job J, leaving J with two holds:

1. The unselected route releases one hold alternately. J now has one hold, so its alternate callback does not run.
2. The selected route later completes and normally releases the remaining hold.
3. Normal last-hold release evaluates J's requested/started mismatch and credit/defer gate and may begin J.

A node exclusive to the unselected route can instead reach zero on alternate release and pass that bypass through its descendants without running them. This explains how a shared join can remain available for the selected route while an unused branch is removed from dependency waiting.

This is a structural example under the stated pre-held topology. Arbitrary concurrent releases can have other orderings. If alternate release is the operation removing the final hold, the inspected callback does not consult earlier normal releases or a pending-request flag before propagating bypass. Do not replace these operations with an order-independent rule such as “run whenever any predecessor executed.” The full graph's ordering and activation policy must justify the intended behavior.

## Reconstruction implications

A useful semantic model needs two release operations:

| Operation | Last-hold behavior for the inspected ordinary job |
| --- | --- |
| Normal release | Check requested versus started, apply credit/defer policy, potentially begin |
| Alternate release | Recheck current holds and recursively release active outgoing holds alternately |

Neither is a general-purpose thread cancellation operation. Alternate release does not wait for execution counts to reach zero or retire callbacks that already started. Treating it as a safe native pause, stop or unload mechanism would be unsupported.

Tests for an independent model should distinguish an exclusive unselected path, a reconvergent selected/unselected join, a nested unselected conditional, a pending-but-bypassed request and a newly added hold before callback entry. The event trace should separately label normal begin, ordinary finalization and alternate propagation rather than reporting all three as completed execution.

This closes the local alternate-recursion question in the rearm audit. It does not close the runtime caller that submits the next action-graph request or the barrier excluding replacement of a still-used receiver array.

## Evidence scope

The complete alternate dependency-list helper, the complete ordinary leaf callback, the complete conditional callback and the conditional begin routine were inspected directly. Five concrete table bindings connected receiver/gather/skeleton/terminal jobs to the ordinary callback and the conditional job to its two-list override. The normal release/request behavior was cross-referenced with the previously inspected scheduler sources.

The analyzed image SHA-256 is `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. No raw exports or machine-specific paths are included. The pseudocode preserves the observed hold tests, recursion choice and active-byte ordering while abbreviating the platform lock implementation.


## Destructive list clear has a diagnostic boundary

The world-chain rebuild's list-clear helper differs from ordinary alternate
release. At entry it checks whether the source list is active. If so it calls a
short helper containing `NOP; INT3; RET` in the inspected image. The breakpoint
precedes any successor hold decrement. The live exception handler, debugger
interaction and whether this path is expected to resume are not established.
It must not be silently treated as a harmless callback or normal supported clear.

If execution continues past that helper, the clear routine walks successor
entries, rechecks the source active byte for each entry, decrements holds and
invokes the target's alternate callback when the prior hold was one. It then
sets the source active byte and successor count to zero. It retains the backing
storage. Inactive clear skips hold decrements and removes successor entries.
Descendant alternate release deactivates lists but does not remove their entries.

```python
def clear_dependency_list_native_outline(source):
    if source.active:
        breakpoint_diagnostic()  # INT3 in the inspected image
        # The following requires a handler to resume execution.
    for target in source.successor_entries:
        if source.active:
            old = atomic_decrement(target.holds)
            if old == 1:
                with target.lock:
                    target.alternate_callback()
    source.active = False
    source.successor_count = 0
```

This is a serial outline. The source-byte recheck and current-hold recheck inside
callbacks are retained in the native path; concurrency and reentrant list mutation
are not reproduced by the inspection API. No request acknowledgement, normal body
execution, execution-count drain or thread cancellation follows from this clear.

`engine.alternate_dependencies.clear_dependency_list` now models the operation.
It accepts the same explicit graph/binding schema as `release_alternate`. An active
list raises `ActiveDependencyClear` without mutation by default. Passing
`continue_after_diagnostic=True` explicitly selects inspection of the continuation;
it does not configure or bypass a live game handler. The operation commits only
after validation and event-budget checks, preserving existing graph object
identities. Transactions, cycle rejection and diagnostic policy are adapter choices.
Only the selected source loses successor entries. Credit-recipient lists, request,
started, deferred and lifecycle fields remain unchanged.

[Validation receipt](../../native/snow_host/dependency_clear_validation.json):
128 original-instruction completed cases cover inactive clear and explicit active
continuation, varied hold counts, duplicate entries and active/inactive descendant
lists. The original clear routine, diagnostic helper and ordinary recursive
alternate callbacks execute; locks are stubbed. A Unicorn interrupt hook observes
interrupt 3. An additional 64 cases stop at that interrupt and confirm the source
and target memory blocks are unchanged. Continued cases explicitly resume after
the interrupt; that is a test policy, not evidence of live exception handling.
Five API tests cover receipt replay, stop-without-mutation, descendant preservation,
no request acknowledgement and event-budget rollback.

This qualifies earlier descriptions that an active clear may alternate-release
its descendants: those describe the continuation instructions and must retain the
diagnostic boundary. The inactive-only world-stage topology API remains restricted;
this new operation is an explicit graph inspection tool, not authorization to
rewire an active native scheduler.
