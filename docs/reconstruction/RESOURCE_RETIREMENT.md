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

## Allocation metadata selection

[`lookup_allocation_metadata`](../../engine/allocation_metadata_lookup.py)
reconstructs the complete leaf `0x1229bc0..0x1229c0d`. Its receiver supplies a
first-level region-pointer table at +0x370. For an unsigned 64-bit payload address:

```text
region_pointer = region_table[address >> 32]
if region_pointer != null:
    tag = region_pointer[(address >> 16) & 65535]
    if tag != 255:
        return entries[tag & 127]
return entries[default_byte]
```

Entries begin at receiver +0x378; the default byte is at +0x774. The default
index is not masked. Address bits 0..15 are ignored, so this is a 64-KiB-region
classification lookup, not a per-object header read. The returned pointer-sized
value is captured before virtual destruction and passed to the allocator's
release operation afterward. Its internal type and owner remain unresolved.
The routine performs no payload dereference, null-payload rejection, bounds check
or locking. Null or unregistered addresses are not automatically rejected.

The layout requires care at raw edge values: entry index 127 begins at +0x770,
so the default byte overlaps its pointer-sized storage. Do not construct two
independent native fields and assume arbitrary values can coexist. The model
uses supplied readers so actual storage aliases can be represented. Whether
index 127 or defaults above the ordinary entry range occur in valid native
allocations is not established by reading this function.

[The complete-leaf comparison](../../native/snow_host/allocation_metadata_lookup_validation.json)
checks 16,448 synthetic cases, covering every tag byte, absent regions, selected
unmasked default indices, high-address partitions and low-address boundaries.
It executes the original instructions without intercepted services and preserves
the default/entry storage alias. This does not prove live table validity,
registration, synchronization or object lifetime.

The connected loading probe now uses this model, and its
[24-case instruction comparison](../../native/snow_host/joined_retirement_loading_validation.json)
executes the original lookup rather than returning supplied metadata. Earlier
paragraphs describing supplied allocation services remain applicable to the
allocator's final release operation; lookup itself is now reconstructed. The
synthetic selected entry is stable during these joined runs. Real payload
methods, region registration and allocator release remain external dependencies.

## Metadata registration and default selection

[`register_metadata`](../../engine/allocation_metadata_registry.py) reconstructs
`0x122eb90..0x122ec93`; `select_default_metadata` adds the wrapper at
`0x122eca0..0x122ecc9`. A metadata record carries its byte index at +0x19.

```text
register(registry, record):
    if record.index != 255:
        return true
    lock(registry.registration_lock)
    inserted = false
    for index in 0..126:
        if registry.entries[index] == null:
            record.index = index
            registry.entries[index] = record
            inserted = true
            break
    unlock(registry.registration_lock)
    if inserted:
        notify observers in order with event 0 and record
        # observer count is read again after every callback
    return inserted

select_default(registry, record):
    result = register(registry, record)
    registry.default = record.index
    return result
```

The table has **127 usable registration slots**, not 128. The initializer at
`0x1227380` clears 0x3f8 bytes beginning at +0x378, exactly 127 pointers, sets a
separate count at +0x770 to zero and sets default +0x774 to 255. This explains the
raw lookup's entry-127 overlap noted above: a malformed tag can index into other
fields, but normal registration never assigns 127. The region initializer at
`0x1224f30` requests 65536 bytes, fills them with 255, then publishes the region
pointer and increments the separate count. These initialization statements are
static inspection; the registration comparison below does not execute them.

Registration trusts every preexisting index other than 255 without checking the
selected registry. It checks that byte before locking and does not check it again
after locking. A successful return therefore does not establish membership,
current region association or exclusive ownership. After a new insertion,
notifications run outside the lock. Object-style observers receive event zero
and the record through virtual slot +8; function-style observers receive event
zero, the record and their stored context. The count is re-read, so callbacks can
extend the traversal. Retaining observer storage/modules remains an external
requirement; arbitrary removal during traversal is not made safe by this model.

The default wrapper ignores registration failure when assigning the default.
A full table plus an unassigned record therefore returns false and writes 255
as the default. It also reads the record index after notifications, so callback
changes affect that assignment. This wrapper cannot be treated as a validated
fallback installation API without an additional caller contract.

[Original-instruction comparison](../../native/snow_host/allocation_metadata_registry_validation.json)
passes 192 cases covering existing indices, first/middle/last free slots, full
tables, both observer styles, callback extension/index changes and the default
wrapper. Locks and observer effects are supplied. The full original routines
execute and return/state/event order matches the model. Actual region tag
publication, concurrent registration, registry lifetime and allocator release
remain open. This finding narrows metadata ownership rules; it does not identify
the live allocator's release vtable or prove safe memory reclamation.

## Metadata removal and notifications

[`unregister_metadata`](../../engine/allocation_metadata_removal.py) reconstructs
`0x12313f0..0x123146b`, joined to the complete notification dispatcher at
`0x1225b50..0x1225bf3`:

```text
index = record.index                 # captured before locking
lock(registry.registration_lock)
registry.entries[index] = null      # no entry-identity or bounds check
if registry.default == index:
    registry.default = 255
unlock(registry.registration_lock)
result = dispatch_observers(registry, event=0, record)
record.index = 255                  # after callbacks, even if they changed it
return result
```

The local model requires index0..126 and retained table/record storage. Native
code does not enforce those requirements. In particular it can clear a slot that
currently contains another record, and it does not reject an already unassigned
index. Do not expose this as a validated mod-facing removal API.

The dispatcher selects an observer collection at `registry + signed(event)*0x190`.
Its count at collection +0x188 is re-read after each callback. Object-style records
call virtual slot +8 with `(object,event,record)`; function-style records call
`(event,record,context)`. Low32 callback results are bitwise-ORed, with zero for an
empty collection. No meaning is assigned to those result bits. The public model
accepts the already selected collection; the connected removal uses event zero.

Observers see a cleared entry and, if it matched, default255, while the record
still carries its old index. Changes to that record index during notification
are overwritten by the final255 store. Registration and this removal both use
event zero in the inspected paths; do not invent distinct add/remove event
numbers. Notifications do not imply asynchronous callbacks have drained.

**Region tags are not cleared by this routine.** The descriptor destructor at
`0x1223ac0` calls the separate region scanner `0x1229690` before performing a
similar entry-removal sequence. That is a static caller relationship, not proof
that every removal caller retires regions first. The scanner's full behavior and
its callback to the underlying region owner remain a next investigation. A tag
still naming a cleared entry makes the lookup return null; the lookup does not
fall back merely because the selected entry is null.

[Joined original-instruction comparison](../../native/snow_host/allocation_metadata_removal_validation.json)
passes 108 cases over first/middle/last valid indices, matching/nonmatching
defaults, null/matching/mismatched slots, both observer styles and controlled
callback extension/index mutation. Only locks and callback bodies are supplied;
the removal and dispatcher execute together. Region retirement, concurrent table
mutation, module lifetime and safe storage reclamation are not established.
