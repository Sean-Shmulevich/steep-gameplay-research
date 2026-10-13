# Executable request, hold and credit rules

[The request-state module](../../engine/request_state.py) expresses the local counter rules from [scheduler rearm](SCHEDULER_REARM.md) as serial JSON-state reducers. It makes request behavior testable without running the game or treating a remaining-work counter as completion.

This is a narrow reference, not a replacement native scheduler. It executes no callbacks, uses no locks or atomics, and supplies no submission exclusion. Its returned effects stop at virtual-call boundaries whose selected receiver and surrounding order must be established separately. The owned [job executor](../../engine/jobs.py) and [controller](../../engine/control.py) remain independent implementations; this module does not modify them.

## State and operations

Each job contains `state`, `requested`, `started`, `holds`, `credit_gate`, `credits`, and `deferred`. The lifecycle labels use the diagnostic names UNSCHEDULED, SCHEDULED and DONE. This model does not infer lifecycle transitions from counters, nor convert requested/started values into global frame IDs.

| Operation | Implemented local rule | Explicit boundary |
| --- | --- | --- |
| `submit(job)` | Increment requested only while UNSCHEDULED; emit begin when holds are zero | Usage flag, profiling, begin receiver, and submit's eventual boolean return are omitted |
| `begin_ordinary(job)` | SCHEDULED is a no-op; otherwise snapshot requested into started | Emit activation and empty-work/queue/finalizer decisions; do not execute them |
| `add_hold(job)` | Increment holds; increment requested only on zero-to-one transition | No graph recursion |
| `activate(list, jobs, recurse=False)` | Add holds only when inactive; mark active before returning successor activation effects | Caller resolves successor virtual methods |
| `release_one_dependency(job)` | Decrement a positive hold; only the last hold checks requested versus started and the credit gate | Emit begin or defer; no callback execution |
| `release_one_credit(job)` | Increment signed credit; if positive, no holds, unstarted request and deferred, consume a credit, clear deferred and emit begin | This is the normal release's separate credit-recipient loop |
| `release_normal(list, jobs)` | Inactive list is a no-op; process normal successors then credit recipients | Nonrecursive batch helper; see ordering limitation below |

`new_job(...)` and `new_dependency_list(successors, credit_recipients)` construct caller-controlled fixtures. Lists retain order and repeated entries. Recipient IDs must uniquely identify objects: two different IDs pointing to the same Python dictionary are rejected, preventing a detached transaction from losing alias identity.

Direct submit does **not** apply the inspected last-hold credit gate. Ordinary begin itself checks SCHEDULED, not a general `holds == 0` or `requested != started` condition. Adding either check everywhere would change the observed local behavior.

## Effects must be consumed explicitly

`invoke_begin` means the inspected branch reaches a virtual begin call. It does not mean a callback ran or a job completed. If that receiver is proven to use ordinary begin, the caller can apply `begin_ordinary`. That prefix then stops before its own virtual activation and work-predicate calls. Conditional and terminal job methods must not be silently routed through the ordinary prefix.

For example, two predecessors hold a common successor:

```python
from engine import request_state as r

jobs = {"join": r.new_job(credit_gate=True)}
left = r.new_dependency_list(["join"])
right = r.new_dependency_list(["join"])

r.activate(left, jobs)   # holds=1, requested=1; activation effect is opaque
r.activate(right, jobs)  # holds=2, requested still 1
assert r.release_normal(left, jobs) == []
assert r.release_normal(right, jobs)[0]["kind"] == "begin_deferred"

effects = r.release_one_credit(jobs["join"])
assert effects[0]["kind"] == "invoke_begin"
# Only because this fixture chooses an ordinary begin receiver:
r.begin_ordinary(jobs["join"])
assert jobs["join"]["started"] == jobs["join"]["requested"] == 1
# No queue insertion, callback execution or completion was performed.
```

Applications must preserve the native call boundary when expanding effects. Calling `submit` repeatedly while leaving an emitted begin unprocessed is not a faithful replay of synchronous submission: the real begin might already have queued the job and changed its lifecycle state before the next submit.

## Ordering details that matter

Normal activation adds all successor holds, marks the outgoing list active, then propagates successor activation. Repeating activation on an active list with `recurse=False` does nothing. With `recurse=True`, the selected parent repeats the walk without adding holds. Its child activation calls still receive `recurse=False`: the inspected parent clears the argument before invoking its list walker. The incoming override is not recursively propagated unchanged.

Native normal release marks its list inactive **before** successor callbacks. The batch reducer commits detached arithmetic at the end and returns opaque calls with the list already inactive. It therefore preserves final local arithmetic only when those omitted callbacks do not modify later recipients. To preserve a graph with such interactions, explicitly clear the list, call the one-recipient reducer, resolve its effect immediately using the correct receiver, and then advance to the next recipient. Do not describe the batch reducer as a recursive native graph interpreter.

The last-hold branch with a positive gated credit consumes one credit and invokes begin. It does not clear a previously set deferred flag in the inspected instructions. The separate credit-recipient path does clear deferred when it wakes a job. Their field writes intentionally differ.

The credit-recipient path tests the **post-increment** signed credit count. Moving from -1 to 0 does not wake the job. Moving from 0 to 1 can wake it only when holds are zero, requested differs from started, and deferred is set. A recipient appearing in both lists retains the effects of the first loop when the second loop examines it.

The [alternative dependency release](ALTERNATE_DEPENDENCY_RELEASE.md) has different receiver dispatch and activation-clearing order. It is deliberately absent here; normal credit release must not be substituted for it.

## Operational limits and validation

Counters are restricted to an ordinary signed 32-bit operational domain; requested, started and holds are nonnegative. Native integer wraparound is not reproduced. Underflow, overflow, malformed state and ambiguous aliases are adapter errors. Batch helpers validate on detached copies, so a validation error leaves the supplied fixtures unchanged. This transactional protection is our adapter policy, not a claim about native exception behavior.

The model omits worker reservation/execution accounting, queue insertion, empty-work finalization, scheduler TLS, native recursive locks, alternative receiver dispatch, dynamic topology mutation, request ownership, and the caller that rearms the action wrapper. Successful reducer tests do not prove any of those boundaries or establish a native storage-lifetime barrier.

All state is JSON-compatible. Checkpoint/restore is an ordinary JSON roundtrip, provided the caller separately retains topology identity and resolves pending effects in the same order. The reference stores no pending effect queue and does not supply a universal frame generation.

## Verification

The focused implementation pass checked 294 instruction spans from five existing local exports against the frozen image SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. The inspected exports cover submit, ordinary begin, ordinary activation, its successor walker and normal release including the credit-recipient loop. This verifies retained static evidence consistency, not native runtime execution.

[Fourteen tests](../../tests/test_engine_request_state.py) cover duplicate activation, two-predecessor joins, local begin gates, credit deferral/wakeup, signed-credit boundaries, distinct deferred-flag writes, overlapping recipient roles, inactive release, underflow rollback, alias rejection, repeated entries and checkpoint-equivalent continuation.

Run `python3 -m unittest discover -s tests -p 'test_engine_request_state.py'` from the repository root.
