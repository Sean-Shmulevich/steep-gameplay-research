# Executable ordinary queue policy

`engine.queue_policy` implements the selection rules in
[Ordinary queue eligibility and selection](SCHEDULER_QUEUE_ELIGIBILITY.md),
including its eligibility gates, score arithmetic and category traversal sections.
The implementation is serial. It does not reproduce queue locks, worker events,
atomic notification counters or unknown optional eligibility callbacks.

## Standalone API

`select_queue(jobs, order, shared_default=..., worker_mask=..., local=False)`
returns `selected`, `score`, `rejected_by_affinity` and evaluated IDs in `visited`.
The first two fields are null when no candidate beats the initial `INT_MAX` score.
Only each visited job's `limit` can mutate.

Each job record supplies `kind` as `range` or `callback`, signed int32 `limit`
and `executions`, optional uint32 `required_mask` and `excluded_mask`, and
`optional_eligible` as a supplied boolean or null. Null means no extra eligibility
gate. These values are inputs, not inferred job identities or native callables.
Mask width follows the inspected DWORD affinity operations.

`select_categories(jobs, local, shared, shared_default=..., worker_mask=...)`
accepts three arrays each for local and shared queues. It checks local then shared
within categories zero, one and two, returning on the first successful queue.
The result adds `category`, `source` and per-queue `scans`. Array order is explicit.
These standalone selectors do not derive category assignments or queue insertion targets.

Both APIs validate the whole fixture before traversal. Duplicate entries, a job
in multiple queues and aliased mutable job records are rejected as adapter policy.
Validation does not resolve limit sentinels or invoke eligibility code.

## Operation order and arithmetic

The supplied optional gate precedes all virtual eligibility and affinity work.
Range eligibility resolves `INT_MAX` in place before its signed execution-limit
comparison. Shared affinity rejection therefore leaves that resolved range limit
in place. Callback eligibility always passes. Its limit sentinel resolves only
when it reaches scoring after affinity. Local selection bypasses affinity only.

`occupancy_score(executions, limit, shared_default)` wraps multiplication to signed
int32 and truncates signed division toward zero. A nonpositive limit returns the
shared default. Python's floor division is not used directly for negative values.
For example, `INT_MAX * 2` wraps to minus two, whose division by three truncates to
zero. Positive divisors exclude the signed minimum divided by minus one exception.

Selection replaces the best candidate only for a strictly lower score. Equal
scores preserve the earlier entry. Zero exits immediately, leaving later job
sentinels untouched. A score equal to `INT_MAX` never replaces the initial best.
No undocumented positive-default constraint is imposed on the supplied int32.

## Mixed scheduler integration

The optional constructor argument has this shape:

```python
policy = {
    'shared_default': 8,
    'worker_mask': 1,
    'jobs': {
        'motion': {'category': 0, 'queue': 'shared', 'limit': 2},
        'callback': {'category': 1, 'queue': 'local', 'limit': 0},
    },
}
scheduler = MixedScheduler(definitions, handlers, queue_policy=policy)
```

Every executable range or callback job needs an explicit mapping. Mapping fields
also accept `required_mask`, `excluded_mask` and `optional_eligible`. Terminal and
conditional jobs execute synchronously and do not receive queue mappings. The
policy limit supplies the denominator and range eligibility cap; the older
`max_concurrency` adapter field is used only when this policy is absent.

When a policy-enabled job is enqueued, its `INT_MAX` limit resolves immediately
to the supplied default. This follows the enqueue producer in
[Queue producers](SCHEDULER_QUEUE_PRODUCERS.md). The standalone APIs accept already
assembled queues and retain the selector-local mutation rules above.

`reserve()` selects first, then performs existing outstanding-dispatch and
execution accounting and the kind-specific reservation effect. Callback jobs
leave the queue and become done before the body runs. Range jobs stay eligible
only under their recovered execution cap. A supplied `reserve(name)` must name
the current policy winner; it cannot bypass selection. An invalid explicit choice
is rejected without committing sentinel mutations or trace events.

`ready()` previews candidates by repeatedly selecting and removing each selected
candidate from copied policy state. It changes no counters, limits or trace. Only
its first result predicts the immediate next reservation. Reserving a job changes
execution counts, so the remainder is not a future dispatch schedule.

Snapshots include configuration under `queue_policy` and mutable selection data
under `selection_jobs`. Execution counts in that snapshot copy reflect current job counts; inspection
does not mutate the underlying selector records. `jobs` remains the authoritative
reservation and completion accounting. Selection
trace events include evaluated queues, scores and affinity rejection evidence.
The existing default remains the simpler insertion-order adapter. Owned gameplay
does not silently acquire invented categories or worker masks.

## Tests and boundaries

`tests/test_engine_queue_policy.py` covers signed wrap and truncation, strict ties,
early zero, sentinel mutation ordering, supplied gate rejection, any-bit required
masks, excluded-mask precedence, local bypass, ordered categories and callback
versus range reservation accounting. It also verifies that readiness inspection
and invalid explicit reservation leave state unchanged.

Run `python3 -m engine.examples.queue_policy_probe` for a synthetic mixed-scheduler
example. Its blocked job remains scheduled after the other jobs finish; no ready
candidate does not imply all queued work completed.

Concrete per-job assignment writers, unknown eligibility code, other native job kinds and
multi-worker race behavior remain outside this model. Explicit worker/default
values make the executable policy testable without inventing those inputs.

## Worker and enqueue producers

`engine.queue_producers.worker_configuration(requested, upper_bound)` exposes
worker-count initialization without allocating threads or arrays. Both inputs
are uint32. Its result contains the unsigned selected count, signed int32
interpretation of the same bits for the selector's `shared_default`, and the
signed auxiliary-count calculation. The signed interpretation connects producer
storage to the recovered signed scoring consumer; it is not a claim that large
worker counts are operationally valid.

`worker_mask(index)` returns the rotating single-bit uint32 mask.
`enqueue_destination(category, required_mask, worker_slots)` returns a category,
local/shared queue designation and optional worker index. Slots are explicit
booleans for pointer presence. A missing slot raises an adapter error; a present
null slot selects shared storage. The function does not consider excluded masks,
matching the inspected routing path. Ordinary category validation is adapter
policy, not a recovered constructor guard.

These pure functions can supply configuration to a caller-owned scheduler setup.
They do not allocate native worker threads. The optional topology integration
below uses their routing and mask rules. Queue locks, aggregate-limit updates and
notification counters remain outside their scope. `base_job_limit(byte_argument, shared_default)` now implements the base-constructor
signed minimum followed by uint8 conversion. Later concrete overrides remain
separate from that initial value.

Six producer tests cover unsigned clamp boundaries, signed storage, rotating
masks, lowest-bit routing, null versus absent slots and the interaction between
local routing and exclusion bypass. See [producer evidence](SCHEDULER_QUEUE_PRODUCERS.md).

## Explicit worker topology and controlled interleaving

The optional policy can now replace `worker_mask` with `worker_slots`, a list of
booleans identifying present and null worker slots. Job mappings omit `queue` in
this mode. The recovered lowest-required-bit rule computes destinations, and
worker masks follow the rotating producer. Categories and limits remain explicit.

```python
policy = dict(shared_default=2, worker_slots=[True, True], jobs={
    'motion': dict(category=1, limit=2, required_mask=0),
})
scheduler = MixedScheduler(definitions, handlers, queue_policy=policy)
a = scheduler.reserve(worker_index=0)
b = scheduler.reserve(worker_index=1)
```

Submit the relevant root before reserving. `ready`, `reserve`, `dispatch_next`
and `run_ready` accept the worker index. Topology mode requires an explicit
present worker. A worker sees its own local queues and the common shared queues;
other workers' local jobs are excluded before selection. Required-mask references
to missing array slots fail validation rather than inventing native behavior.
The setup is immutable, so computing destinations at configuration time is
equivalent to recomputing this routing when enqueuing under those fixed inputs.

Dispatch records and reservation trace events retain worker identity. One worker
may hold one outstanding ordinary dispatch. Until it returns, readiness is empty
and anonymous reservation returns no token; forcing a named reservation fails.
This is the testbench's ordinary-worker contract. Nested helping, thread-local
state, atomic races, dynamic worker replacement and real OS threads are not modeled.
Callbacks and claims run only when explicitly invoked by the caller, allowing
controlled interleavings without wall-clock timing.

`python3 -m engine.examples.worker_topology_probe` runs 100 synthetic receivers
using recovered chunk/threshold 32/64. Worker zero holds the first 32 while worker
one claims and completes the remainder. The terminal cannot begin until the held
range returns. Five topology tests also cover local ownership, shared affinity,
callback single reservation, invalid worker identities and inspection immutability.
The 128-slot model bound is an adapter resource limit, not a native supported count.
