# Resource retirement reconstruction

This guide maps the executable retirement models and their evidence. It describes
an independent reconstruction of local resource-management behavior, not original
engine source or a safe native plugin-unload API. Resource holders occur across
subsystems; the shared manager must not be labeled animation-specific solely
because animation research first reached it.

## Run the connected paths

From the repository root, with Python and no game files:

```sh
python3 -m engine.examples.command_retirement_probe
python3 -m engine.examples.holder_consumption_probe
python3 -m engine.examples.retirement_service_probe
```

The first shows command-record release into a deferred queue, including wrapped
queue growth. The second distinguishes consumption, refused cleanup and holder
recycling. The third composes preparation, consumption, recycling, worker handoff
and post-unlock destruction calls. Their storage, payload operations and external
services are explicitly synthetic. JSON outcomes are inspection diagnostics, not
native return values or guarantees of live completion.

## Data flow and implementation map

| Stage | Independent implementation | Behavior established | External dependency |
| --- | --- | --- | --- |
| Record release | [command_record_cleanup](../../engine/command_record_cleanup.py) | Detach associated object, clear invoker, ordered holder decrements | Associated destructor; holder release callback |
| Release routing | [holder_release_queue](../../engine/holder_release_queue.py) | Gates, queued flag, insertion, optional post-unlock service | Locks, growth, cleanup |
| Queue resize | [holder_ring_resize](../../engine/holder_ring_resize.py) | Logical pointer preservation, ownership, failure boundaries | Allocation, copying, free |
| Preparation | [resource_preparation_queue](../../engine/resource_preparation_queue.py) | Capture published budget, pop triples, key check, current-payload dispatch | Locks and resource dispatcher |
| Consumer scope | [holder_consumer_scope](../../engine/holder_consumer_scope.py) | Processing gate, dynamic loop, worker counter transfer and signal condition | Locks, per-item callback, signal |
| Consumer item | [holder_consumer_step](../../engine/holder_consumer_step.py) | Pop, cache payload, callback-sensitive mode/status ordering | Payload operations, output append, cleanup |
| Holder cleanup | [holder_cleanup](../../engine/holder_cleanup.py) | Two-count gates, detachment, status changes and pool-link update | Token services and pool lookup |
| Pool lookup | [holder_pool_lookup](../../engine/holder_pool_lookup.py) | First matching descriptor using signed /24 and low32 comparison | Descriptor population and lifetime |
| Service wrapper | [holder_retirement_service](../../engine/holder_retirement_service.py) | Guard ordering, mode-one destruction after unlock, array ownership | Preparation, consumption, destructors, allocator |

The names and dictionary representations are our design. The documentation in
each module defines required fields and normal-return assumptions. Existing
stable-input decision helpers remain useful, but the mutable consumer model is
needed when callbacks change mode, references or payload linkage.

## Distinctions an engine implementation must preserve

- **Published budget and queue occupancy differ.** Preparation exchanges one
  budget and processes exactly that many triples. Later callback publications
  wait for another invocation. Retirement consumption instead re-reads occupancy.
- **Queued flag and insertion differ.** The flag is set before growth. An empty
  ring's null allocation can leave a flagged holder without a queue entry.
  Occupied preserving resize has no null guard before copying.
- **Consumption and recycling differ.** References restored by a callback or a
  retained separate count can prevent cleanup after the queue entry is removed.
- **Holder recycling and payload destruction differ.** Cleanup can detach a
  payload and publish a free-list index. The wrapper's destruction traversal is
  separate, occurs after unlocking, and runs only for mode exactly one.
- **Captured payload and current state differ.** Consumption keeps its original
  payload pointer across callbacks but re-reads mode and status afterwards.
- **Pool selection and pointer validity differ.** The recovered locator accepts
  arithmetic matches without alignment or full-width range checking. It is not
  a suitable mod-facing pointer validator.
- **Signal and completion differ.** Worker counter transfer and signaling do not
  prove that the receiving worker ran or completed disposal.

The models preserve these distinctions. Python errors at invalid-state boundaries
are authored diagnostics; they do not invent native rollback or exception-safe
unlock behavior.

## Evidence ladder

| Evidence | What it exercises | What it does not establish |
| --- | --- | --- |
| Public unit/integration tests | Model branches, aliases, callback changes and composition | Original runtime equivalence by themselves |
| [Record-to-queue comparison](../../native/snow_host/command_retirement_composition_validation.json) | Original record cleanup, release and resize together | Native allocator/destructor/lock internals |
| [Consumption-to-pool comparison](../../native/snow_host/holder_consumption_composition_validation.json) | Original consumer, cleanup and pool lookup together | Outer synchronization or completed disposal |
| [Joined service comparison](../../native/snow_host/joined_retirement_service_validation.json) | Original wrapper and middle routines through post-unlock calls | Supplied leaf-service effects and concurrency |
| [Original recursive-lock comparison](../../native/snow_host/retirement_recursive_lock_validation.json) | Game adapters plus previously observed Wine lock instructions | Live object identity, contention or lifetime |
| [Controlled handoff](../../native/snow_host/recursive_lock_handoff_validation.json) | Original lock arithmetic across virtual-thread interleavings | OS wait/wake implementations or fairness |
| [Real-thread fixture](../../native/snow_host/recursive_contention_fixture_validation.json) | Windows API critical sections with actual threads under Wine | Game adapters, game objects or engine-wide lock ordering |

Original-instruction comparisons use a private analysis image. Public receipts
contain hashes, scope and outcomes; they contain no game executable or memory
payload. Public probes and tests run independently of that private image. Test
counts describe sampled cases, not a percentage of engine coverage.

## Integration boundaries and next investigations

The retirement path belongs to the existing
[frame-path research](ANIMATION_CONTEXT_RETIREMENT.md#retirement-service-joins-the-frame-path).
That relationship does not prove all command callbacks have completed before
retirement. Command preparation is not automatically a callback-drain barrier.

The strongest next ownership questions are:

1. What initializes, retains and destroys the command manager and shared resource
   registry during transitions? Do not infer permanent lifetime from a singleton.
2. Which references protect each callback context, payload and module while jobs
   execute? Existing local counters must not be named universal callback counts.
3. What are the actual resource dispatcher, token-service and payload-destructor
   effects for a selected subsystem? Current composition supplies those leaves.
4. What live phase and lock-order contract permits submission and observation
   without racing teardown? Platform recursion alone cannot answer this.

A persistent native API needs verified object identity, lifetime, permitted phase,
lock ordering, admission and completion accounting. These models provide parts of
that contract; they do not authorize arbitrary calls or plugin unloading.

For detailed pseudocode, source anchors and limitations, follow the matching
sections in [resource/animation retirement](ANIMATION_CONTEXT_RETIREMENT.md) and
[request-command lifecycle](REQUEST_COMMAND_LIFECYCLE.md). For the wider project,
use the [scheduler roadmap](../../engine/SCHEDULER_ROADMAP.md).

## Mode-zero loading producer

The formerly supplied mode-zero dispatch has a local executable implementation:
[`enqueue_loading_destruction`](../../engine/loading_destruction_enqueue.py).
It inserts into the loading-owner ring and increments the staged word that the
retirement consumer later transfers to the worker's published counter. See the
[producer contract](LOADING_THREAD_LIFECYCLE.md#executable-loading-destruction-insertion)
for field naming and signed/raw counter distinctions. This does not change the
older joined-probe receipt scopes; those runs still supplied the dispatcher.

## Connected loading disposal probe

```sh
python3 -m engine.examples.retirement_loading_service_probe
```

This newer probe connects the retirement service, actual reconstructed loading
insertion, staged-to-pending transfer and loading destruction batch. The older
`retirement_loading_probe` is a decision/counter demonstration; it does not
exercise this complete chain. The new probe supplies synthetic payload methods,
allocation services and locks. Its driver chooses to invoke the loading batch
after the retirement service returns; that serial schedule is authored, not a
claim about native scheduling or exclusion.

`before_batch` exposes the boundary: in mode zero the holder is already detached
and recycled while one payload waits in the loading queue and no destruction
has happened. The insertion lock nests to depth three under the enclosing
service and consumer locks. Mode one instead destroys through the wrapper,
without publishing loading work. Retained references or the processing guard
can prevent entry to the loading path.

A supplied growth refusal on an empty loading ring shows why completion must not
be inferred from counters. The holder is detached, insertion fails, staged work
is still published, and the empty batch clears that pending count without a
destruction call. The result has zero staged, pending, busy and queue count, yet
the payload has not been destroyed. This is a controlled service outcome, not a
claim that the native allocator returns this way during gameplay.

[The connected original-instruction comparison](../../native/snow_host/joined_retirement_loading_validation.json)
passes 24 scenarios over modes zero/one/two, retained references, processing guard
and sufficient/zero loading capacity. Original wrapper, preparation, consumer,
cleanup, pool lookup, insertion and batch routines execute; leaf services and
zero-capacity growth refusal are supplied. It checks service-event order and
state both before and after the batch. Payload lifetime, real destructor effects,
concurrent producer exclusion and safe plugin unloading remain unproved.
