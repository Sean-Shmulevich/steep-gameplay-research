# Animation context holder retirement

The [effect model](../../reference/animation_context_retirement.py) describes the
local retirement routine called after a holder release. It does not implement
native locking, reclamation or a public lifetime lease.

## Recovered behavior

The outer routine acquires a manager lock, invokes retirement, and releases the
same lock. Inside that lock, retirement proceeds only when all these hold:

- Reference count is zero.
- Low 24 status bits are zero.
- Status bits 24 and 26 are clear.

For an attached target, the routine clears the low 19 bits of the target's
packed word. If that word has bit 28 set, it calls a target service before
clearing the holder's target pointer and visibility bit 31. That service's
complete effects remain external. If there is no attached target, this path
does not clear bit 31. The routine then sets holder status bit 26.

When backing storage exists, a backing-unregistration service is called unless
the backing lies in the native reserved range or holder status bit 28 is set.
A supplied slot descriptor identifies the free-list head and holder slot index.
The native insertion is equivalent to:

```python
holder.references_or_next = descriptor.free_head
descriptor.free_head = holder_slot_index
```

This field has changed meaning. A nonzero value after retirement may be a
free-list link, not an ownership count. An inspection tool must interpret it
with lifecycle state; it must not treat that number alone as proof of liveness.
The model retains the output key `references` to expose the exact overwritten
field, but its meaning after `recycle_slot` is the free-list link.

## Model contract

`plan_context_retirement` takes uint32 references and status, an optional target
word, explicit backing/range predicates, and caller-supplied slot index and free
head. It returns local state changes and ordered effect names. It does not infer
pointer ranges, resolve a descriptor, call services or mutate input storage.
These are adapter boundaries, not extra native guards. No pose, units or timestep
is involved. Concurrent changes and compare/exchange retries are not modeled.

## Validation and limits

The [108-case receipt](../../native/snow_host/context_retirement_validation.json)
executes the original wrapper and inner routine with synthetic holders. It varies
reference counts, blocking status bits, target presence/flags, backing presence
and reserved-range membership. Target clearing, packed-word changes, retired
status, and free-list insertion execute as original instructions. The comparison
also checks lock/service/unlock ordering.

Locks, target service, backing unregistration and descriptor lookup are
intercepted. The experiment therefore does not prove actual lock exclusion,
allocator recycling, target destruction, races or a safe modding lifetime API.
This extends the earlier static retirement lead in
[the context retention findings](CENTRAL_IMPULSE.md#evaluator-context-retention-boundary).
Holder ownership and target validity must remain distinct.

## Target service records paired associations

The previously intercepted target service has now been followed into its local
body. It takes a separate global lock and rechecks target packed-word bit 28.
If that bit is clear, it unlocks without recording either association. If set,
its observed sequence is:

```python
set_thread_local_context(global_context)
target_to_backing[target] = backing
set_thread_local_context(0)
set_thread_local_context(global_context)
backing_to_target[backing] = target
set_thread_local_context(0)
```

Each assignment obtains a writable map value slot first. The two maps are
distinct fields. The TLS setter writes its argument into a thread-local slot;
it clears to zero rather than restoring a captured previous value. No direct
virtual target-destructor call occurs in this service body. The complete map
implementation and later consumers remain external, so the paired writes alone
do not prove when or whether target destruction occurs.

The [association model](../../reference/animation_target_retirement.py) uses
caller-supplied symbolic keys and copies of maps. It preserves unrelated entries
and overwrites the selected slots. It does not invent removal of stale reverse
entries, uniqueness guarantees, rollback, native map allocation or actual TLS.
Its `locked_target_word` input is explicitly the post-lock observation, not the
flag read by the earlier retirement caller.

The [16-case receipt](../../native/snow_host/target_retirement_validation.json)
executes the original service with map-slot lookup, locks and TLS setter
intercepted. Original map-value writes execute. It varies the flag before and
after lock acquisition, other flag bits, and null/non-null backing. This proves
the second flag check can suppress or enable these local writes independently
of the earlier value in this synthetic test. It does not emulate a concurrent
writer or establish lock semantics. The next ownership lead is the consumer of
these paired maps, not a presumed immediate target destructor.

## Paired-map resolution fallback

A statically inspected transform-accessor path calls a target-resolution wrapper
that reads the same backing-to-target map as its last fallback. The maps are
therefore not established as a cleanup queue. The term “backing” above names the
opaque holder field, not a proven allocation type; some values are reserved-range
identities, and this lookup treats the field as an identity key.

The [resolution model](../../reference/animation_target_resolution.py) expresses
the wrapper's exact local precedence:

```python
if key_is_null or not globally_enabled:
    return null
lock()
entry = primary_lookup(key)
if entry is not null:
    result = entry.payload  # even a null payload ends the search
else:
    result = secondary_lookup(key)
    if result is null:
        result = backing_to_target.get(key)
unlock()
return result
```

The [64-case receipt](../../native/snow_host/target_resolution_validation.json)
executes this original wrapper while intercepting the lock and three lookup
services. It checks gates, precedence, returned values and lock-call order,
including a present primary entry with a null payload. The wrapper does not
perform an additional reference increment or target-validity check after the
fallback returns. Lookup service internals may have their own effects; these
remain outside the check. A successful result is not a lifetime lease.

The accessor caller connection is a static finding, not a live observation of
this fallback being used. Actual map searches, primary/secondary service
semantics, association removal/rebinding and their synchronization remain open.

### Original primary and secondary searches connected

The primary lookup scans an ordered array of 16-byte pairs. In this caller its
second search argument is null. Its exact match condition becomes:

```python
for row in pairs:
    if row.payload is null or row.key == requested_key:
        return row
return null
```

Consequently, an unrelated row with a null payload can precede and suppress a
later matching row. This is recovered behavior, not an adapter filtering rule.
The producers and intended meaning of those null rows remain unknown; do not
silently skip them or describe them as tombstones without further evidence.

The secondary service looks up an identity-to-holder map. For a present, nonnull
holder it returns the holder's target field directly. It does not inspect the
holder's visibility/status word or increment its count in this local routine.
Missing map entries or null holders return null and permit the final fallback.

`resolve_registered_target` composes these operations. The
[192-case receipt](../../native/snow_host/registered_target_validation.json)
executes the original wrapper, pair search and secondary service together, with
only map lookup and locks intercepted. Tests cover absent tables by empty pair
arrays, duplicate keys, null rows, holder absence, target absence and fallback
availability. The original nested lock calls all receive the same global lock
address in this tested configuration. `outer`, `pair` and `holder` event labels
name call sites, not different locks. Their recursive/exclusion behavior is not
established by interception. No concurrent mutations, ownership acquisition or
live target validity is proven.

## Association removal gate

The paired-map removal routine has now been identified. When globally disabled
it returns null without changing the target. Otherwise, if the target word's low
19 bits are zero, it looks up and saves the target-to-backing value, erases that
entry, and erases the reverse entry only when the saved value is nonnull. Each
erasure is bracketed by TLS context set/clear calls. It then clears target bit 28
and returns the saved backing identity. The bit clear also occurs when nonzero
low bits prevented all map operations.

```python
backing = null
if enabled:
    if (target.word & 0x7ffff) == 0:
        backing = target_to_backing.get(target)
        erase(target_to_backing, target)
        if backing is not null:
            erase(backing_to_target, backing)
    target.word &= ~(1 << 28)
return backing
```

There is no lock acquisition in this local routine. A statically inspected caller
can wrap it in the global lock; no universal caller synchronization is inferred.
The low-bit meaning is not assigned an ownership-count name here.

`remove_target_association` is an independent symbolic-map model. Its
[48-case receipt](../../native/snow_host/target_removal_validation.json) executes
the original routine with map and TLS services intercepted. Gates, erase call
arguments/order, target-word changes and returned identity are checked. Python
map deletion supplies the model's container effects; native map deletion itself
is not validated. Tests include absent/null/non-null mappings and enabled/disabled
paths. A cleared target bit does not prove these maps no longer contain an entry.

This closes a paired-map removal lead, not the ordered primary-pair array's
insertion/removal rules. Those remain separate structures and an open question.

## Construction pair finalization

A static construction path supplies a producer for the ordered array. With a
nonnull identity it locks, initializes an available target's header, appends
`(identity, target)`, and unlocks before invoking a supplied constructor callback.
After that callback it invokes the pair finalizer. Allocation and callback
behavior have not been validated in this pass. A null target can be written by
the append path, but successful recovery from allocation failure is not proven.
This is evidence of a construction-time registry, not proof that every row comes
from this path or that null rows are intentionally usable placeholders.

The finalizer searches for the first row whose payload equals its target OR whose
key equals its identity. Unlike the resolution caller, it supplies a nonnull
target as the second match value. On a hit it replaces the row with the last row
and decrements count. It does not preserve ordering or clear inactive storage.

If a matching row was removed and the target word's low 19 bits are zero, it
calls the identity-registration service. Otherwise it sets target bit 28 itself.
A missing row also takes that bit-setting path. The registration service can
have additional effects; the finalizer model returns the target word at that
service boundary when `registration_requested` is true, not a claimed complete
post-registration word.

The [effect model](../../reference/animation_registry_pairs.py) and
[28-case receipt](../../native/snow_host/registry_pairs_validation.json) cover the
original finalizer, original pair search and original swap-removal helper. Lock
calls, the fixed-size copy service and identity registration are intercepted.
Tests vary key/payload matches, duplicate matches, first/middle/last positions,
empty/missing matches and low-bit gates. They also demonstrate why swap-removal
can change which duplicate key wins the next lookup. No constructor callback,
allocation behavior, registration effects or concurrent access is established.

### Registration connected after pair finalization

The registration routine first invokes the same ordered resolver using the
identity. A nonnull result suppresses registration, even when it names a target
other than the proposed one. Otherwise, if the global registry flag is enabled,
it locks, sets target bit 28, writes identity-to-target, then target-to-identity,
with TLS context set/clear around each map write, and unlocks. The resolver and
registration branch read the same global enable byte. The routine returns the
supplied identity whether registration occurred or was suppressed.

`finalize_and_register` composes pair removal with this decision and the two map
writes. Resolution observes the post-removal pair order. Its `events` field is
the local finalizer trace; `resolution` reports lookup details and `registered`
reports whether registration wrote the maps. It does not flatten these into a
claimed full native scheduling trace. The earlier boundary-only finalizer remains
available for callers supplying their own registration service.

The [56-case connected receipt](../../native/snow_host/registry_registration_validation.json)
executes the original finalizer, pair search, removal helper, registration,
resolver and secondary holder service. Locks, fixed-size copy, map-container
services and TLS remain intercepted; the original map-value writes and target
flag update execute. Cases include enabled/disabled registration, an existing
fallback mapping, duplicate pairs and nonzero low target bits. The secondary
holder map is absent in these cases. No constructor, allocation, concurrent
registry mutation or target lifetime is validated. This replaces the registration
stub for this bounded connected path, not for every previous receipt.

### Supplied-storage construction chain

The [56-case construction receipt](../../native/snow_host/registry_construction_validation.json)
executes the complete wrapper with supplied nonnull storage and identity. The
original append and capacity-check routines run with sufficient existing space,
followed by the original finalizer and registration/resolution chain. The supplied
constructor callback is a synthetic service that sets the target word; it is not
a recovered game constructor. The experiment checks that the temporary pair is
already appended, the wrapper's initial header and zero target word are present,
and the registry lock has been released before the callback. It also checks the
returned target and final pair/map/target-word state.

[The construction adapter](../../engine/animation_registry_construction.py)
provides `construct_supplied_target`. It gives a caller callback a copied snapshot
of the temporary pairs and initial target word. The callback returns the uint32
word used by finalization. This is a deliberately bounded callback contract:
registry mutation, exceptions in native constructors, reentrant constructors,
allocation/failure, null identities and actual object initialization are not
reconstructed. Snapshot immutability is our inspection policy, not native
behavior. No native memory, vtable value or game payload is exposed by the API.

The original wrapper publishes before callback and finalizes afterward, so the
lookup window is established locally. Its use by real constructors or competing
threads remains unobserved. Locks, copy/map/TLS services retain the prior
interception boundaries; no actual allocator or native constructor executes.

## Recursive lock adapter integration

The registry call sites use the same protected entry/exit adapters whose API
targets were previously resolved to `RtlEnterCriticalSection` and
`RtlLeaveCriticalSection` in a Wine process. See the existing
[live adapter evidence](CENTRAL_IMPULSE.md#skeleton-lock-adapters-resolved-in-a-live-process).
This is reuse of that observation, not a new live probe of the registry lock.

The [56-case lock-chain receipt](../../native/snow_host/registry_lock_chain_validation.json)
now executes those protected adapters within the complete supplied-storage
construction chain. Encoded target slots are replaced only in the emulator so
that transfers reach synthetic enter/leave services. Each transfer receives the
pointer stored in the registry lock wrapper. The services maintain a serial
recursion counter; every case balances to zero, with maximum depth two or three.
The constructor callback is still reached with depth zero. Final registry and
target-word results match the same reconstruction.

This removes entry-wrapper interception from this receipt, not external lock
implementation. Real critical-section ownership, blocking, wakeup, memory order,
destruction and contention are untested. The synthetic service accepts one
thread only; a balanced call history does not pin a target or its buffers.

The authored [completed-event checker](../../engine/recursive_lock_trace.py)
accepts ordered successful acquisitions/releases for one logical lock, with
thread identities and optional reported post-event depths. It reports current
owner/depth, maximum recursion, and balance. It rejects foreign-owner completed
acquisitions, unmatched releases and inconsistent reported depths. Attempted or
blocked acquisitions are not completed events and must not be fed into this
checker. Trace completeness remains explicitly unproven, even when balanced.

## Passive construction-pair inspector

`engine.animation_registry_observation.capture_construction_pairs` takes an
identity-checked `readv` transport, a freshly resolved registry address and 1–30
external identity/build guards. The layout is specific to the inspected build.
The transport must enforce process identity, read permissions and timeouts.

The inspector reads the packed pair-array header, rejects a count beyond capacity
or the caller's budget, and reads at most 512 pairs in chunks no larger than 256
bytes. It rechecks the guards and header, rereads all pair bytes, then rechecks
the guards/header again. It fails on incomplete reads or changed observations;
it does not retry into a mixed result. Empty storage is not dereferenced.

The result uses capture-local symbolic labels to preserve equality relationships
without publishing raw pointers or identity values. Optional `query_identity`
applies only the recovered pair-array predicate, reporting the selected index,
whether it matched the key, and whether the target is null. This is not the full
resolver: it does not apply global enable/null-query gates, inspect secondary
holders, traverse maps, or follow target pointers. Labels cannot be used across
captures to assert object identity.

Matching reads cannot rule out ABA changes or concurrent writes between reads.
The output therefore keeps `atomic_snapshot`, `lifetime_retained`, and
`safe_native_call_established` false. It neither acquires a native lock nor calls
game code. Synthetic tests cover changed rows/headers, short reads, capacity and
budget rejection, empty storage and address-free alias reporting. The subsequent live checks below validate empty-array observation; a nonempty
live pair capture remains untested.

### Run the synthetic observation demo

From the repository root:

```sh
python3 -m engine.examples.animation_registry_observation_demo
```

This uses a synthetic byte buffer as the read transport. Its three pairs contain
an unrelated null-payload row before the requested identity, so the query reports
index 1 with `matched_key: false` and `target_null: true`. It demonstrates the
inspection API and recovered pair precedence without game files or process access.

A private capture command has also been prepared using the existing bounded
process reader. It requires an explicit process identity file, verifies the local
analyzed-image hash, checks three instruction spans in the target process, and
uses PID/creation-time guards on every read request. It permits 1–8 captures with
at most 512 pairs each, under the reader's existing time/request limits. Raw reads
stay in the private output directory. At preflight, syntax and argument parsing were checked;
no live capture ran then because no game process was available. Code-span checks are
bounded build checks, not a hash of the whole running image.


### Bounded live empty-array observations

The [live receipt](../../native/snow_host/registry_pairs_live_observation.json)
records two bounded sessions and six successful passive captures. All PID,
creation-time, code-span and repeated-header checks passed. The early session
observed count 0/capacity 0 three times. The delayed session observed count
0/capacity 4 three times. Both sessions used the configured D3DMetal launch path
with no navigation, gameplay input, debugger, injected module or memory writes.
Gameplay state was not verified.

Capacity four is consistent with an array allocated during startup and later
emptied. This is an inference, not a captured append, callback or removal. The
reader followed no live target pointer and read no active pair payload because
all counts were zero. This establishes process transport and empty-header
observation, not live pair interpretation or lifetime safety.

The sessions completed in approximately 21 and 48 seconds under a 90-second
watchdog. After cleanup, bottle and game configuration bytes matched both saved
pre-session copies, and the bottle process listing was empty. The first identity
attempt in each session failed or timed out; subsequent identity acquisition
succeeded before any capture. Failures did not trigger a restart of an active
game session. Raw reads and process addresses remain private.

The next live question is observing an active construction interval. Repeated
empty captures cannot establish that the array is unused or that callbacks do
not consult it. A targeted in-process observation at the established append or
callback boundary would provide stronger evidence than a longer passive poll,
but requires separate hook and lifecycle validation.

## Accessor construction bypasses pairs

The direct attachment and hierarchy-reparenting paths use metadata named
`Hierarchy` for the entity's transform accessor. The inspected metadata reports
224 bytes and a constructor callback that transfers to the accessor initializer.
These attachment callers pass a null identity to the common construction wrapper.
They therefore bypass temporary-pair append and identity finalization. Observing
the construction pair array cannot be assumed to observe these accessor creations.
The allocation path remains external, and this metadata connection is static.

The [initializer](../../reference/transform_accessor_initialization.py) now
models all writes to the 224-byte storage. It copies a supplied 64-byte transform
from shared globals, clears entity/child/sibling links, installs the common
fallback holders in both descriptor slots, initializes descriptor fields and
synchronization fields, and clears the extra pointer/byte fields it explicitly
writes. Two neighboring flag bytes are set to one. Unwritten bytes remain intact,
including the 64-byte getter scratch area beginning at offset `0xa0`.

The transform globals in the analyzed static image are zero. The constructor
API requires supplied transform bytes rather than assuming live zeros. The
subsequent shared-initializer finding below establishes identity after that
initializer runs; its execution in a particular live construction remains unobserved.
Likewise, constructor completion does not make the untouched scratch area a valid
pose; consumers must follow the existing getter/copy-out production rules.

The [128-case receipt](../../native/snow_host/accessor_initialization_validation.json)
executes 64 original initializer calls and 64 complete construction-wrapper calls
with null identity and supplied nonnull storage. The wrapper follows the actual
metadata constructor callback. No service interception is reached. Inputs vary
all backing bytes and supplied transform-global bytes. All 224 output bytes,
including unchanged regions, match. Native fallback-holder identity is checked
privately and replaced with a synthetic token in the public receipt. No game
matrix payload, process pointer or executable byte is published.

This closes the constructor's local defaults and explains why the registry
capture was the wrong observation point for these null-identity accessor paths.
Allocator behavior, metadata replacement, live transform-global initialization,
owner attachment, cleanup exclusion and thread context remain separate gates.


### Shared transform default initializer

A direct SIMD-store search found a small initializer that writes the four
constant rows `(1,0,0,0)`, `(0,1,0,0)`, `(0,0,1,0)`, `(0,0,0,1)` into the shared
transform globals. A function pointer to it exists in the inspected read-only
data. This establishes its local output, not when that pointer is invoked during
startup. The direct-store scan found these four stores but does not exclude
indirect or dynamically generated writes elsewhere.

`bootstrapped_transform_default()` returns those identity bytes explicitly. The
[64-case bootstrap receipt](../../native/snow_host/accessor_bootstrap_validation.json)
executes the original shared initializer over arbitrary prior global bytes,
then the original accessor initializer directly or through the actual metadata
callback and null-identity construction wrapper. No service stub is reached.
The shared global output and all 224 accessor bytes match, including unchanged
backing regions and synthetic representation of fallback-holder identity.

This supports an identity initial transform when the shared initializer has
executed and no later writer has changed it. It does not make scratch storage
initialized, establish live initialization order, or justify omitting the explicit
transform argument when observing an unknown process state.

## Direct accessor attachment

The direct-descriptor attachment branch is now connected to the actual accessor
constructor. After resolving a visible parent entity, it performs:

```python
if parent.accessor is null:
    a = construct_accessor(identity=null, storage=null, metadata=Hierarchy)
    # Constructor and allocator notification have returned here.
    parent.accessor = a
    a.owner = parent
child.accessor.next = parent.accessor.child_head
parent.accessor.child_head = child
```

The owner slot is published before the backlink. Existing accessors keep their
prior backlink and all other fields except the child-list head. The routine does
not deduplicate the inserted child in this branch. The child's accessor must
already exist. Invalid/cyclic topology prevention may belong to callers; this
routine does not establish it. Its local attachment path does not acquire the
registry lock when construction uses null identity.

The [storage model](../../reference/transform_accessor_attachment.py) composes
initialization and attachment over caller-supplied bytes and symbolic uint64
identities. It models only this visible direct-descriptor branch. Allocation,
visibility service, indirect descriptor mode, invalid pointers and concurrency
are outside the API. It returns the new child-next value separately so callers
can keep child and parent storage distinct.

The [64-case receipt](../../native/snow_host/accessor_attachment_validation.json)
executes the complete direct attachment, real construction wrapper and real
metadata constructor. Visibility and allocation services plus allocator
notification are intercepted. The experiment checks the entire accessor buffer,
parent publication, backlink, child head and child-next values. The notification
still sees no parent accessor; the backlink-store boundary sees the parent slot
already installed and the newly initialized backlink still null. Existing and
new accessor cases are included. Null-allocation behavior, type alternatives,
concurrent publication and lifetime safety are not tested.

This supersedes the earlier static-only classification for this local direct
attachment branch. It does not prove an arbitrary observer can safely use the
owner pointer between publication and backlink installation, or that an existing
accessor survives cleanup while being inspected.

## Child unlink and cleanup

The direct unlink helper now executes inside the cleanup experiment. On a head
match, the parent head becomes the removed child's next link. Otherwise the
helper walks children until it finds a predecessor whose next link is the target,
and replaces that predecessor link with the target's next link. In every normal
return path it clears the requested child's next link, including when the child
was not found in the parent list. The supplied child and its accessor must exist.

The [unlink model](../../reference/transform_accessor_unlink.py) preserves this
nonmember side effect. It reports whether a parent-list removal occurred
separately from clearing the target link. `unlink_and_plan_cleanup` feeds the
resulting head state into the existing descriptor/children/sibling cleanup gates.
Missing or cyclic traversed nodes are rejected by the inspection adapter; native
termination on invalid/cyclic input is not established. The model does not free
storage or release real holders.

The [288-case receipt](../../native/snow_host/accessor_unlink_cleanup_validation.json)
executes the original cleanup and unlink bodies. Descriptor validity, allocation
metadata and deallocation are still supplied services. Head, interior, last,
missing and empty-list cases are covered, with absent/present accessor, descriptor
and sibling gates, and three reader-word values. It checks every supplied child's
next link, parent head, release call order, descriptor counts and owner-slot clear.
Holder counts start at two so retirement is not reached. The deallocator still
observes the owner slot pointing to the accessor, as in the prior cleanup test.

This closes the supplied-post-unlink-state boundary for these cases. The cleanup
result remains independent of the tested reader-word values. Actual deallocation,
caller serialization and lifetime protection remain separate questions. Descriptor
validity is connected in the follow-up below; a successful unlink does not by itself prove safe
concurrent cleanup.


## Descriptor visibility connected to cleanup

`descriptor_is_valid` in the [unlink model](../../reference/transform_accessor_unlink.py)
now expresses the original descriptor predicate. Mode 1 selects the first holder.
Mode 2 selects the second holder only when the 16-bit index is not 65535. Other
modes return false. For the selected holder the rule is:

```python
status_mask = UINT64_MAX if holder.status & 0x80000000 else 0
visible = bool(holder.target & (status_mask | thread_visibility_mask))
```

The TLS value is a 64-bit mask, not a boolean override. For example, target
`0x100` with clear status bit 31 and TLS mask `0x80` is invisible; mask `0x100`
makes it visible. A zero target stays invisible even with all visibility bits
set. These numeric targets are synthetic bit patterns, not process pointers.
Mode 1 ignores the index sentinel; mode 2 rejects it before accessing its holder.
The model accepts supplied holder values and never dereferences a process address.

The native predicate at build-relative RVA `0x124a850` calls the TLS getter at
RVA `0x119f8d0`. The getter reads the TLS index global, follows `GS:[0x58]` to the
TLS slot array, selects that index, then reads the slot block's 64-bit value at
`+0x48`. The experiment supplies synthetic GS/TLS storage and executes these
instructions, rather than replacing the getter with a return-value stub.

The [320-case receipt](../../native/snow_host/accessor_descriptor_cleanup_validation.json)
connects original unlink, descriptor selection, TLS lookup and cleanup. Cases
vary modes 0 through 3, the index sentinel, target presence, status bit 31, five
TLS masks, last-child versus remaining-child unlink, and three reader words.
Checks include resulting child links, parent head, holder decrements, release
order, unchanged reader word and owner-slot clearing. Allocation metadata and
the deallocator are intercepted; holders start at count two to avoid retirement.
The deallocator still sees the owner slot before it is cleared.

This replaces the descriptor-predicate stub for these cases. It does not establish
actual allocation/free behavior, native TLS setup, the meaning of arbitrary TLS
mask values in gameplay, holder lifetime, or caller synchronization. In particular,
a true descriptor predicate does not acquire a reference or grant a safe pose-read
window. No live game ran for this validation.


## Descriptor detach dispatch

The direct cleanup routine has two statically found relative-call sites. One is
inside the descriptor dispatcher at RVA `0x124b290`; the other is an inline
mode-1 path in the child traversal at RVA `0x124b340`. This search covers relative
calls in the analyzed text, not all possible indirect callers.

The [dispatch model](../../reference/transform_accessor_unlink.py)
`plan_descriptor_detach` preserves the dispatcher's argument arithmetic:

```python
if mode == 1:
    target = first.target & (status_mask(first) | tls_mask)
    direct_cleanup(target, child)
elif mode == 2:
    target = second.target & (status_mask(second) | tls_mask)
    indexed_service.detach(target, descriptor.index_record, child)
```

Here `status_mask` expands status bit 31 to all 64 bits or zero. Unlike the
validity predicate, the dispatcher does not check the index sentinel and does not
reject zero or partial targets. Mode 2 forwards a pointer to the index record at
`descriptor+0x14`; the 16-bit index is within it at `+0x18`. The model reports the
index value rather than exposing that native address. Other modes do nothing.
This is an effect plan, not a callable native mod API.

The [128-case receipt](../../native/snow_host/descriptor_detach_validation.json)
executes the original dispatcher and TLS getter. Both downstream services are
intercepted at entry. Checks cover exact target masking, the child argument,
index-record address, modes, sentinel, and unchanged descriptor/holder counts.
A partial mask can produce a nonzero value different from the supplied target;
these synthetic bit-pattern cases deliberately stop before any dereference.
They do not establish that such masks occur during normal gameplay.

### Outer ownership lead

The parent-detach caller at RVA `0x124b780` first copies the descriptor through
RVA `0x1244420`. That copy increments each selected holder's reference count,
installs the holder in the temporary descriptor, releases the displaced fallback,
and copies mode/index metadata. It retains both holder fields, regardless of mode.
The parent-detach caller then checks descriptor validity before its virtual
notification and the dispatch call. The child traversal contains analogous inline
holder retention and validity logic before its cleanup call. These are static
findings, not a validated concurrent ownership protocol.

The local dispatcher adds no holder references or reader admission of its own.
The outer caller's validity check also precedes a virtual callback, so it should
not be treated as a guarantee that all relevant state stays unchanged until
cleanup. The exact callback effects and caller serialization remain open.
Holder retention is a useful lead for target lifetime; it does not establish an
accessor lease, stable hierarchy topology, or a safe pose-buffer read window.
Next connect the outer detach, descriptor copy, and cleanup under original
instructions, observing holder counts across callbacks and accessor release.


## Parent detach ownership experiment

The [parent-detach model](../../reference/transform_parent_detach.py) and
[288-case original-instruction receipt](../../native/snow_host/parent_detach_validation.json)
connect the outer mode-0/mode-1 detach routine, real descriptor copy, TLS getters,
descriptor reset, direct unlink and both accessor cleanup paths. Virtual
notifications, allocation metadata and free services are intercepted. They do
not mutate state in these cases. The optional auxiliary notification is disabled.
The parent accessor starts with an invalid descriptor, no next link, and the
selected child at its head; an optional sibling follows the child.

Both distinct descriptor holders start at count `N`, where `N` is 2, 4 or 17.
Their count progression is:

1. Descriptor copy retains both holders: `N + 1`.
2. If the mode-1 parent is visible, the child notification runs and parent unlink
   occurs. With no remaining sibling, parent accessor cleanup reaches free while
   both holders still have count `N + 1`. The manager notification follows.
3. Replacing the child's descriptor with fallback holders releases its original
   references: both counts return to `N`. Mode becomes zero and index metadata
   resets to its sentinel values.
4. If requested, the now-invalid child accessor is freed when it has neither
   children nor a next sibling. The original holders still have count `N` here.
5. Releasing the temporary descriptor leaves both original counts at `N - 1`.

The free callbacks observe each owner's accessor slot still populated. Original
instructions clear that slot after the callback returns. Holder counts never
reach zero in this experiment, so retirement services are not exercised. Actual
freeing is intercepted; this establishes the decision and ordering, not native
allocator behavior.

The child cleanup flag controls cleanup of the child's accessor only. Disabling
it does not suppress unlink or prevent the parent accessor's cleanup. Modes 0
and invisible mode 1 skip parent notification/unlink but still reset the child
descriptor and can clean up the child accessor. The model preserves these local
branches without asserting that every synthetic combination occurs in gameplay.
The tested reader words are 0, 3 and `0x100001`; they remain unchanged and do not
change the free decisions.

### Consequence for a pose snapshot API

Retaining the descriptor holders is not an accessor lease. Both parent and child
accessor free decisions can occur while the temporary descriptor still owns
references. Combined with the unchanged reader word, this rules out using either
of those local mechanisms alone as proof of safe accessor inspection.

A snapshot API still needs an execution window that excludes hierarchy teardown
and relevant pose writes, then an owned copy of the pose before that window ends.
The original callback effects, caller thread/phase constraints, indexed mode 2,
aliased holders, last-reference retirement and concurrent traversal remain open.
The present model is an inspectable effect plan and does not call native services.


## Entity lifecycle ordering

The transform teardown wrapper has a direct caller at RVA `0x8925b0`. The
[previous entity-constructor evidence](../systems/tricks/target-publication/evidence.md)
identifies primary table RVA `0x1ebbf78`; its slot `0x48` contains this caller.
Another path at RVA `0x892720` clears a referenced collection before tail-calling
it. The separate reattachment wrapper at RVA `0x124ccd0` also reaches parent
detachment, so teardown is not yet confined to destruction or one scheduler job.

The [lifecycle order model](../../reference/entity_deactivation.py) expresses the
following original order under stable component-array and nonmutating callback
assumptions:

1. Call component slot `0x110` in reverse array order.
2. Call component slot `0x48` in forward order, skipping null entries in this
   second pass. Call the separate optional component's slot `0x48` if present.
3. Run transform teardown, which can release transform accessors.
4. If the entity's registry link equals the selected global registry, acquire
   that registry's lock, search its pair array, remove a matching entry if found,
   release the lock, and clear the entity's registry link even if no entry matched.
5. Run an optional task service, then a tail service at entity `+0x208`.
6. Store `(entity.state_byte - 1) & 255` in the following byte.

The first component pass dereferences every component without a null test.
The forward pass reloads array/count after reverse callbacks. The model assumes
callbacks leave those inputs unchanged; dynamic replacement is not modeled.
`component_before`, `component_release`, `task_release` and `tail_service` are
reconstruction labels for observed call sites, not recovered semantic names or
proof that each callback destroys its receiver.

The [192-case receipt](../../native/snow_host/entity_deactivation_validation.json)
executes the full original lifecycle method, intercepting the component callbacks,
transform teardown, lock adapters, removal, task and tail services. It checks
order, registry-search arguments, registry-link clearing and byte wrap across
zero through three components, optional component/task presence, matching versus
other registry, found versus absent registry entry, and state bytes 0, 1 and 255.
The adapter accepts the native 16-bit count range, but original-instruction cases
cover only those small collections. No callback effects or concurrent access are
validated by this experiment.

The lock acquisition inside this method occurs **after** transform teardown.
Therefore this acquisition cannot establish exclusion for the earlier accessor
cleanup. A caller could already hold a broader or recursive lock; that remains
unresolved. The registry backlink is likewise still populated during teardown,
so it cannot by itself certify accessor lifetime.

The concrete next caller-search target is this identified primary-table slot,
including the collection-clearing tail caller and derived-table variants.
A generic slot-`0x48` call is not sufficient to identify an entity lifecycle call:
receiver provenance must match. Trace that provenance to its world mutation or
scheduler phase before comparing exclusion with SkeletonPostUpdate. No new
live pose-copy API is enabled by these local ordering results.


## Collection drain provides a broader lock scope

A collection-drain routine at RVA `0x823410` copies nonnull source entries to a
local temporary array, clears the source count, and calls each temporary entry's
primary-table slot `0x48`. The calls are bracketed by manager lock helpers
at RVAs `0x11a8390` and `0x11bacf0`. Those helpers add `0x60` to their incoming
manager and tail-call the previously resolved critical-section enter/leave
adapters. The call site supplies the shared control manager at RVA `0x3301d80`,
so this scope uses its `+0x60` lock. Holder retirement uses the same manager's
`+0xb8` lock instead; these lock identities must not be conflated.

This is a broader scope than the registry lock acquired inside the lifecycle
method after transform teardown. For receivers whose primary slot is the base
entity lifecycle method, the collection lock brackets that method and its
transform teardown. Receiver type is a precondition: a generic slot-`0x48`
dispatch alone does not prove that an arbitrary entry is an entity.

The [30-case receipt](../../native/snow_host/entity_drain_validation.json)
executes the original drain, both lock-address helpers, the base entity lifecycle
method selected through its original table, and transform teardown with absent
accessors. Synthetic entities vary their state byte; collections include empty,
null-slot, reordered and duplicate entries. Platform lock operations, temporary
allocation/release, optional collection service and the entity tail service are
intercepted. The recorder verifies that the source count is already zero at lock
entry, that each lifecycle/teardown call occurs at bracket depth one, and that
temporary release occurs after lock exit. Original entity state-byte writes are
checked. There are no original allocator calls or concurrency in this experiment.

The [collection-drain model](../../reference/entity_deactivation.py)
`plan_entity_collection_drain` preserves these call-order rules for supplied
base-entity receivers without accessors. Null entries are skipped; duplicates
are dispatched repeatedly. Empty collections still enter and leave the lock.
Its capacity/input rejection is authored inspection policy. The native routine
also has an optional collection service before gathering entries; that service's
effects remain external, and callbacks are nonmutating in the validation.

Direct caller inspection finds three routes: a collection destructor at RVA
`0x7ff4d0`, a reset/rebuild path at `0x80ff60`, and an owner lifecycle method at
`0x892300` using its embedded collection at `+0x90`. Higher callers also reach the
reset/rebuild path. These roles describe inspected local operations; their
selected-world identity and scheduler phase are not established.

### Snapshot implications and next join

This establishes a real candidate for broader serialization, not a modding lock
contract. The original-instruction fixture proves bracket order for the supplied
receiver types; it does not show that the selected player belongs to a production
collection drained here. It also does not prove that every reattachment, child
traversal or pose writer acquires this lock. Calling it from an arbitrary mod
thread could introduce an untested lock-order dependency.

Next identify the embedded collection's concrete owner and its mutation callers,
and determine whether direct reattachment uses the same scope. Compare those
paths with the known SkeletonPostUpdate component lock and worker phase. A live
snapshot API still requires both accessor lifetime exclusion and coherent pose
publication; collection-lock bracketing alone does not establish either globally.


## Hierarchy command execution boundary

Reattachment has a concrete deferred-command route. The queue flush entry at
RVA `0x1247a20` transfers a deferred counter into the active counter, then invokes
the consumer at `0x12477e0`. The consumer snapshots and clears its active counter,
then performs that many iterations if the snapshot is positive as a signed
32-bit value. The counter addition wraps at 32 bits.

On each iteration it acquires the queue lock, conditionally pops a 128-byte record
from its ring, retains the record's three holders into local storage, copies its
metadata/transform/flags, releases the popped record's references, and releases
the queue lock. Only **after unlocking** does it process the local record through
RVA `0x1247740`. The queue lock is not the shared manager's collection-drain lock.

The record processor resolves its first holder through status bit 31 alone,
without a TLS visibility override. For a visible nonzero target it updates an
entity byte while preserving its high bit:

```python
entity_byte = (entity_byte & 0x80) | ((entity_byte - 1) & 0x7f)
if entity_byte & 0x7f == 0:
    copy_parent_descriptor()
    detach_and_reattach(entity, descriptor, optional_transform, options)
```

The low seven bits wrap: zero becomes 127 rather than triggering reattachment.
Values 1 and 129 become 0 and 128 respectively, and both trigger the call.
The processor supplies its recorded optional transform, flags and other arguments
to the previously identified reattachment wrapper at RVA `0x124ccd0`.

The consumer calls the processor even on an iteration where no ring record was
available. Its local record initially uses invisible fallback holders, but after
a successful pop an empty iteration processes the cached record again. This is
observable with deliberately mismatched budget/occupancy inputs. Whether the
producer permits that mismatch during normal operation is unknown; it is not a
claim that the game routinely repeats reattachments.

The [360-case receipt](../../native/snow_host/hierarchy_queue_validation.json)
executes the original deferred-counter transfer, queue consumer, slot-reference
release, descriptor-copy instructions and completion gate. Platform queue locks
and the final detach/reattach wrapper are intercepted. Cases cover empty and
nonempty rings, wrap at the end of a four-slot ring, pending/deferred combinations,
signed-negative and wrapping counters, visibility, high-bit preservation,
underflow and cached-record processing. Every processor and reattachment entry
has queue lock depth zero. The same synthetic entity is used in all occupied
records; holder counts stay nonfinal. This does not validate concurrent producers,
actual reattachment effects or a native ownership lease.

The [command model](../../reference/hierarchy_commands.py) accepts logical dequeue
order and supplied resolved target tokens. It preserves byte arithmetic, count
transfer, cached-record behavior and event ordering, returning copied state and
reattachment targets. Independent tests also exercise distinct targets and
invisible records; those combinations are not additional original-instruction
coverage. Input/capacity/iteration guards are authored inspection policy.

### Connection to engine command processing

The flush entry is called near the start of RVA `0x664260`. Its wrapper at
`0x664200` carries the inspected profiler string `::Engine::ExecuteCommands`.
Another caller of the same command executor carries
`::Engine::ExecuteEngineCommands`. These names are direct string evidence,
not inferred from queue arithmetic. The executor has multiple call paths,
including callers at RVAs `0x656900`, `0x67e030`, and the wrapper's callers at
`0x662c80` and `0x69a190`. The `0x662c80` path includes fragmented unwind ranges;
its call at `0x662ea6` is inside the larger routine, not a standalone job entry.

This moves the lifetime investigation to a concrete engine-command boundary.
The inspected queue consumer itself does not acquire the shared collection-drain
manager lock, and its queue lock ends before reattachment. A broader lock held
by the executor's callers remains possible. We have not proved that engine
commands cannot overlap SkeletonPostUpdate or that every direct reattachment
passes through this queue. The separate refresh/reattach caller remains relevant.

Next recover the queue producer's budget/occupancy invariant and identify where
`ExecuteCommands` runs relative to world job completion and loading transitions.
Those joins are prerequisites for treating a command callback or animation
callback as a safe native snapshot scope.


## BeginEngineFrame command binding

The engine setup binds RVA `0x656900` to the job labelled `BeginEngineFrame`,
with profiler label `Engine::BeginEngineFrame`. This is the callback whose body
calls the executor carrying `::Engine::ExecuteEngineCommands`, which in turn
flushes hierarchy commands. The callback is stored in the job embedded at engine
`+0x740`; its receiver comes from the engine-owner global, not necessarily the
setup routine's incoming owner. The binding preserves tag bit 1 and clears tag
bit 0 in the packed receiver field.

The [binding receipt](../../native/snow_host/begin_commands_binding_validation.json)
executes the original binding span for four input tags and two supplied receiver
identities, plus the original adjacent edge-registration span. Label/registration
services are intercepted. It verifies the callable, packed receiver, both labels,
and registrations `BeginFrame -> BeginEngineFrame -> CheckEngineStop`. Hashed
instruction spans also identify the inspected direct calls from that bound
callback to the command executor and from the executor to the hierarchy flush.
The receipt is setup/instruction evidence, not a live frame trace.

Together with the [existing engine graph](ENGINE_FRAME_GRAPH_COVERAGE.md), the
normal dependency route is:

```text
BeginFrame
  -> BeginEngineFrame [executes hierarchy commands]
  -> CheckEngineStop
       paused route -> UpdateWhileEngineIsPaused
       normal route -> UniverseLinkStart -> universe work -> PreStep -> world Step
```

Therefore the later paused-engine selection does not by itself skip hierarchy
command processing. This statement concerns the inspected engine-mode branch,
not the in-game menu and not every possible external hold/stop mechanism.
The current frame's ordinary downstream world jobs wait for the BeginEngineFrame
dispatch to finish; they cannot run merely because its callback was reserved or
marked done. Previous-frame exclusion additionally depends on the ordinary
EndFrame rearm path and its documented graph-coverage limits.

### Runnable partial scheduler probe

Run:

```sh
python3 -m engine.examples.begin_commands_probe
```

The [probe](../../engine/examples/begin_commands_probe.py) uses the existing
independent mixed scheduler with the recovered entry/branch topology, a synthetic
hierarchy command, and an authored terminal `ProbeEnd`. It executes commands in
both normal and paused cases. After the BeginEngineFrame body returns but before
dispatch finalization, the branch already has a request, yet still has one hold;
only finishing the dispatch permits the selected route. The synthetic command
changes byte 129 to 128 and emits one reattachment request in both cases.
This demonstrates model composition, not original-game replay or native mutation.

### Remaining exclusion requirements

This binding gives a concrete phase candidate: inside the ordinary
BeginEngineFrame callback after hierarchy command flushing, before downstream
world work. It is not yet a safe mod callback contract. The executor can also run
through direct paths during other engine operations, graphic work branches
separately from BeginFrame, and loading/idle workers are outside this narrow
chain. Direct reattachment and transform writes have not all been confined to
this phase. The callback's opaque services and failure paths also remain external.

Next check the command producer's publication/count invariant and correlate this
bound job with selected-player animation and topology-change observations. A
mod API must explicitly distinguish holding world simulation from stopping
engine command execution; neither should silently imply process-wide quiescence.


## Full-ring publication can exceed occupancy

Both hierarchy producers check signed occupancy against capacity under the queue
lock. If capacity is no greater than occupancy, they skip record construction,
occupancy increment and write-index advance. They nevertheless increment the
deferred processing counter at queue `+0x54` before unlocking. This is shared by
the explicit-transform producer at RVA `0x124c7a0` and default-transform producer
at `0x124c970`.

```python
if count < capacity:
    publish_record()
    count += 1
    write_index = (write_index + 1) % capacity
deferred = (deferred + 1) & UINT32_MAX
```

The [36-case receipt](../../native/snow_host/hierarchy_full_queue_validation.json)
executes the original full/overfull branch slices of both producers. Capacities
1, 4 and 128, count equal to or one above capacity, and deferred values 0, 1 and
UINT32_MAX verify no count/index change and an unconditional wrapping increment.
These slices do not execute lock acquisition, temporary descriptor construction,
record publication, outer entity-byte updates or concurrent production.
The [full-ring effect model](../../reference/hierarchy_commands.py)
`full_ring_submission` implements only this verified branch.

Static inspection of the outer submission wrappers shows that they increment
the entity's low-seven-bit pending field after the producer returns, then replace
its high bit with the inverse descriptor-validity result. The entity-byte update
therefore follows the producer's queue unlock. These outer operations still need
connected instruction validation and caller-thread analysis before drawing a
concurrency conclusion.

The full-ring branch provides a concrete local mechanism for the previously
synthetic budget/occupancy mismatch: an attempted submission can add a processing
unit without adding a record. A composed model test fills a one-slot ring,
attempts one more submission, then shows two processing iterations for the one
stored record. The second iteration uses the cached record. This composition
uses nonmutating callbacks and is not a live trace or proof of production overflow.
Actual queue capacity, producer backpressure, permitted caller concurrency and
whether full capacity is reachable during gameplay remain unresolved.

For a future mod command API, do not equate a deferred-counter increment with
successful record publication. An independently designed adapter should report
capacity rejection explicitly; that policy must remain distinct from recovered
native behavior. Next validate successful publication through outer byte update
and identify the constructor's ring capacity and producer serialization.


## Hierarchy queue startup capacity

The startup initializer at RVA `0x1249f60` allocates an 88-byte queue object,
initializes its lock, zeros count/write/read fields, and requests a ring capacity
of **2048 records**. The allocation helper at RVA `0x1245e30` multiplies that count
by the 128-byte record stride, requesting 262144 bytes. It sets capacity to 2048
only on successful ring allocation. Both processing counters start at zero.

The [eight-case receipt](../../native/snow_host/hierarchy_init_validation.json)
executes both original routines with intercepted allocation and lock initialization.
It varies object/ring allocation outcomes and initial backing bytes. Object
allocation failure publishes null. Ring allocation failure still publishes the
queue object with null storage and capacity zero; the counters remain zero.
This establishes constructor behavior, not actual out-of-memory handling by all
later callers. The [initializer model](../../reference/hierarchy_commands.py)
`initial_hierarchy_queue` exposes these outcomes without native allocation.

The earlier drain adapter requires positive capacity and therefore intentionally
rejects this zero-capacity failure state. That is an authored inspection guard,
not evidence the native initializer rejects it. The full-ring branch analysis
and cached-record experiment likewise do not establish what a live failed
allocation does across later engine operations.

A full ring under this successful initialization means 2048 occupied records,
not the one-slot synthetic example used to expose the branch arithmetic. The
constructor was identified by scanning RIP-relative stores to the queue global;
the earlier read/LEA-only helper omitted those stores. Actual startup invocation,
later capacity changes, live peak occupancy and producer backpressure remain
unverified. The recovered capacity narrows the overflow question without proving
that overflow is common or impossible.


## Successful hierarchy record publication

The [96-case receipt](../../native/snow_host/hierarchy_publication_validation.json)
executes both producers' successful locked publication slices, including the
original descriptor copy. A supplied synthetic local record is copied into its
selected ring slot: target holder, two descriptor holders, mode/index metadata,
64 transform bytes, four option bytes, a 32-bit argument and a 64-bit argument.
Each of the three distinct holders gains one reference. Descriptor-copy fallback
releases also execute. Twelve padding bytes between descriptor metadata and the
transform are left unchanged, rather than initialized as record content.

After the copy, occupancy increments, write index advances modulo capacity, and
the deferred counter increments with uint32 wrap. Cases exercise modes 0, 1 and 2,
capacities two and four, nonempty occupancy, end-of-ring wrap and deferred wrap.
Both producers execute unchanged without intercepted services in these slices.
Outer locking, local record construction, later entity-byte publication and
concurrent producers/consumers remain outside the experiment.

The [bookkeeping model](../../reference/hierarchy_commands.py)
`hierarchy_publication_state` now handles successful and full branches together
for valid allocated ring storage. It reports whether a record was published,
separately from the deferred count. It does not copy native records or retain
holders. Tests replay the 96 successful cases and the 36 full-ring cases through
this common model. Zero-capacity allocation failure remains an explicitly rejected
adapter input, not silently treated as successful initialization.

This establishes successful record publication before the budget increment
inside the inspected producer lock scope. It does not establish that the outer
entity counter, updated after unlocking, is serialized against command processing.
That outer publication boundary remains the next connected test.


## Entity-byte publication and ordering sensitivity

The [512-case receipt](../../native/snow_host/hierarchy_submit_byte_validation.json)
executes the default-transform submission wrapper's original post-producer byte
update, including the actual descriptor-validity predicate and TLS getter. Every
initial byte value is tested against both validity outcomes. The exact update is:

```python
entity_byte = ((entity_byte + 1) & 0x7f) | (0 if descriptor_valid else 0x80)
```

The high bit is replaced by inverse validity, not preserved. The low seven bits
wrap, including 127 to zero. The [submission model](../../reference/hierarchy_commands.py)
`hierarchy_submission_byte` expresses that operation. The instruction slice starts
after the producer returns; queue publication and unlock were established in
separate producer inspections. This is not a single connected concurrent test.

### A counterexample to final-byte-only verification

With one published record, a visible target, initial byte zero and a valid
parent descriptor, compare two sequential compositions of the recovered rules:

| Order | Byte changes | Reattachment call |
| --- | --- | --- |
| Producer byte update, then consumer | 0 -> 1 -> 0 | One |
| Consumer, then producer byte update | 0 -> 127 -> 0 | None |

Both end at zero. A final-state sampler could therefore miss the difference in
completion events. The [composition test](../../tests/test_hierarchy_commands.py)
checks this result through the actual reconstructed producer-byte and consumer
models. It is an authored ordering experiment, not proof that the second ordering
is reachable in the original engine. Atomicity of either whole modeled operation
is also not claimed; native byte operations comprise several instructions.

This makes the next runtime question precise: does caller or phase serialization
ensure the entity-byte update completes before its queued record is consumed?
Queue unlock alone cannot establish that order because the wrapper updates the
entity byte after its producer returns. BeginEngineFrame phase ordering may
provide it for some callers; direct command-executor invocations and all producer
callers still need to be classified.

A future observation should record producer publication/return, wrapper byte
update and matching record processing, with thread and entity identity. Counting
only final bytes or queued records is insufficient. Such observations can test
specific interleavings but cannot by themselves prove universal race freedom.
No live game mutation or additional native API was enabled by this pass.

## Caller can bypass hierarchy queue

The caller at RVA `0x9239b0` chooses between queued hierarchy submission and
immediate virtual transform dispatch. The exact branch is:

```text
if not descriptor_valid or (owner.flags & 4):
    dispatch_transform(entity, owner.transform)
elif owner.flags & 1:
    submit_hierarchy(entity, descriptor, owner.transform,
                     argument=0, auxiliary=0,
                     flags=[0, (owner.flags >> 3) & 1, 1])
else:
    transform = copy(descriptor_transform(descriptor))
    compose_in_place(transform, owner.transform)
    dispatch_transform(entity, transform)
```

`compose_in_place` names the call at RVA `0x2ec780`, not a newly established
matrix convention. The immediate wrapper at RVA `0x124d0f0` constructs a packet
containing the transform pointer twice and a 32-bit value `0x1f`, then calls
entity virtual slot `0x90` synchronously. The concrete virtual implementation
may perform additional deferred work; immediate dispatch does not prove an
immediate final pose write.

The [512-case receipt](../../native/snow_host/hierarchy_route_validation.json)
executes the original caller branches for every flag byte and both supplied
validity results. The predicate is intercepted; execution stops at the selected
service call. Queued stack flags are checked. Composition, submission, virtual
side effects and scheduler context are not executed by this check. The portable
`hierarchy_transform_route` model exposes only this route decision.

A higher caller starts at RVA `0x923af0`; the earlier unwind-derived
`0x923b30` label was an interior fragment. It resolves an entity through a
status-bit-masked holder, calls the default submission wrapper via `0x925450`,
then calls this route selector. Its function pointer appears at RVA `0x1ed2040`.
Another default-submission caller at RVA `0x9406e0` has a function-pointer entry
at RVA `0x1ed1ff0`. Table ownership and invocation phase remain unresolved.
These static references do not establish either caller as a scheduler job.

**Probe consequence:** a hierarchy-queue trace alone cannot establish exclusion
of transform updates. Correlate selected-entity route decisions and virtual
transform dispatch with BeginEngineFrame entry/exit, alongside queue publication
and consumption. The branch-local code supplies no enclosing lock proof; caller
serialization must still be established. This narrows the required observation
without claiming a live race or a safe callback.

## Submission caller ownership is FXSpawnedEntity

The two previously unowned pointer entries belong to the same primary table,
RVA `0x1ed1f98`. Its type getter at slot `0x30` loads the metadata pointer from
RVA `0x2dfcb48`. In the analysis image that metadata names `FXSpawnedEntity`,
reports size `0x90`, and links its constructor thunk to RVA `0x91b990`.
The constructor installs this table, closing the metadata-to-instance-layout
join. This is a mapped-image type identity, not an observed live instance.

| Table slot | Method RVA | Inspected route |
| --- | --- | --- |
| `0x58` | `0x9406e0` | Nonnull fourth argument reaches default submission |
| `0x88` | `0x93e400` | Holder-resolved entity reaches the transform route selector |
| `0xa8` | `0x923af0` | Holder-resolved entity reaches default submission, then the route selector |

The [ownership receipt](../../native/snow_host/hierarchy_owner_validation.json)
checks metadata/table links and executes the original constructor thunk/body
with four initial memory fills. Base construction and two container initializers
are intercepted. The constructor establishes flags `1`, field `+0x68` as
`0xffffffff`, and field `+0x6c` as zero. Consequently its initial flags select the
queued route for a valid descriptor and direct dispatch for an invalid one.
Later flag changes are possible and not excluded by this constructor check.

This identifies a spawned-effects caller family, not a player motion or skeleton
job. A spawned effect might attach to a player, but that relationship requires
separate evidence. Function names for the three slots, caller thread, phase and
outer serialization remain unknown. The immediate-dispatch exclusion requirement
still stands, but this family should not be used as evidence that player pose
writes occur on the same path. Next prioritize the other queue callers and the
selected player's concrete transform virtual implementation; only broaden the
live trace to FX instances when an attachment relationship is established.

## Entity transform notification lists are captured separately

The existing [target-publication evidence](../systems/tricks/target-publication/evidence.md)
identifies constructor-backed entity table RVA `0x1ebbf78`, whose transform
virtual slot `0x90` is RVA `0x8841f0`. This method holds the entity's recursive
lock across pre-notifications, transform copy/accessor propagation, and
cache/post-notifications. This join reuses prior static findings; it does not
newly identify a live player's table.

The [18-case original-instruction receipt](../../native/snow_host/entity_transform_validation.json)
now executes that wrapper, both actual component loops, and the actual 64-byte
transform copy with no optional accessor. Thread identity, the cache service and
component virtual calls are intercepted. It covers empty, one- and three-element
initial collections, replacement collections of zero to two elements, and both
fresh and already-owned recursive lock states.

A synthetic pre callback replaces the entity's component-array pointer and count.
The original backing array stays allocated throughout this experiment. Observed
execution is:

```text
enter_recursive_entity_lock()
pre_list = capture(owner.components_pointer, owner.components_count)
for component in pre_list:
    component.pre_transform(packet)      # sees old entity transform
copy_64_bytes(owner.transform, packet.first_transform)
# optional accessor propagation omitted in this experiment
publish_cache(owner.transform)           # sees new entity transform
post_list = capture(owner.components_pointer, owner.components_count)
for component in post_list:
    component.post_transform(packet)     # sees new entity transform
leave_recursive_entity_lock()
```

Here `capture` means the pointer and extent, not a copy or retained snapshot of
component objects. The original pre loop completes its initial extent after the
replacement. The post loop uses the replacement collection. Recursive depth is
one higher during all intercepted services and returns to its incoming value;
an initially unowned lock clears its owner and lock word on exit.

This proves a local ordering and collection-reload behavior, not safety under
arbitrary callback mutation. Freeing the original backing, removing live objects,
throwing, or reentering with further transforms is outside the check. Nor does
this lock establish accessor lifetime or exclusion from unrelated hierarchy
operations. A reconstructed observer must not assume each pre callback has a
matching post callback on the same component. A native mod API still needs live
entity-table identification and evidence that its chosen execution phase excludes
other writers.

### Executable notification adapter

`reference.entity_transform_update` now implements this recovered no-accessor
ordering with exact 64-byte transform payloads and supplied notification/cache
services. The two traversals retain their backing Python list and initial extent,
but read each list element when invoked. Python lifetime retention is an authored
implementation property, not native lifetime proof. The adapter rejects optional
accessors rather than silently omitting their propagation. Its logical lock rejects
contention rather than spinning; authored exception cleanup releases that lock
without rolling back already performed side effects. It is not thread synchronization.

Run `python3 -m engine.examples.entity_transform_probe` to inspect a synthetic
old-list pre pass followed by a replacement-list post pass. The adapter matches
all 18 native-instruction receipt cases. Separate tests cover unsupported paths
and authored failure cleanup. This exposes a reconstruction API, not an API
that invokes the original game or a renderer/physics transform setter.

### Optional accessor propagation gate

The [1,036-case instruction receipt](../../native/snow_host/transform_propagation_gate_validation.json)
executes the original transform-copy routine through its optional-accessor gate.
It covers all low flag bytes plus high-bit representatives, accessor absence or
presence, and both supplied descriptor-validity results. The actual copy precedes
all predicate/propagation calls. Those two services are intercepted; accessor
internal locking, matrix composition and child traversal are not executed.

```text
copy(entity.transform, packet.first_transform, 64)
if entity.accessor != null and packet.flags & 1:
    if packet.flags & 4:
        propagate(entity.accessor, packet)   # no preliminary validity query
    elif not descriptor_valid(entity.accessor.descriptor):
        propagate(entity.accessor, packet)
```

Counterintuitively, a valid descriptor suppresses this outer propagation call
when bit 2 is clear. This does not mean valid parents never update: the forced
path bypasses that query, and the propagation routine has its own conditions.
Flags 31 from the wrapper always select the forced path when an accessor exists.

The executable adapter now accepts packet flags and explicit validity/propagation
services. It reevaluates accessor presence after pre callbacks and copy, invokes
propagation before cache/post notifications, and never silently drops an eligible
accessor call. This supersedes the initial blanket accessor rejection described
above. Missing required services still fail explicitly. The adapter's argument
preflight, Python service signatures and exception cleanup are authored API
choices, not recovered native calling conventions. The accessor implementation
itself remains unresolved at this boundary.

### Accessor writer release precedes child traversal

The propagation routine at RVA `0x124a980` has two distinct phases. Its writer
protocol protects a conditional local transform recomputation. After decrementing
writer depth, it clears owner/releases its writer claim when depth reaches zero.
Only then does it load the first child and walk the hierarchy:

```text
acquire_accessor_writer()
if descriptor_valid(accessor.descriptor) and packet.flags & 2:
    recompute_local_transform(...)        # composition convention still external
leave_accessor_writer()
child_entity = accessor.first_child
while child_entity != null:
    child_accessor = child_entity.accessor
    propagate_child(child_accessor, packet)
    child_accessor = child_entity.accessor   # loaded again after the call
    child_entity = child_accessor.next_child
```

The child phase is not gated by descriptor validity or bit 1. Those gates control
local recomputation only. Nested entry restores the incoming writer depth before
the child phase; an outer writer claim can therefore remain held. At initial
depth zero, this accessor's writer claim is fully released before child dispatch.
The calling entity's separate recursive lock can still be held in the previously
validated entity route. Neither fact alone establishes global topology exclusion.

The [84-case receipt](../../native/snow_host/accessor_child_walk_validation.json)
executes the original accessor routine with zero, one or three synthetic children,
initial writer depths zero/two, and flag/validity combinations that skip local
recomputation. Thread identity, descriptor validity and the child service are
intercepted. It verifies restored writer state at every child dispatch. A synthetic
child callback optionally clears its next link; the original walk then stops,
confirming next-link acquisition occurs after the callback, not before it.

The receipt does not execute the matrix-composition branch or child-service
internals. It does not free nodes, replace accessors, introduce concurrent writers,
or prove those operations safe. Static instructions show the accessor reload;
only next-link mutation was exercised. Capturing all children into an immutable
list before callbacks would change this routine's observed traversal behavior.
This phase split should guide the native trace: record accessor writer release
and each child-service entry separately, rather than treating propagation as one
uniform locked region.

### Transform multiplication convention

Two complete original helpers now have portable numerical implementations in
`reference.transform_composition`, validated by a [240-case receipt](../../native/snow_host/transform_composition_validation.json).
No helper calls are intercepted. Synthetic matrices include nonorthonormal linear
parts and same-pointer composition. Every output byte matches, with float32
rounding after each multiply and each left-associated addition. The validated
domain is finite normal-range inputs without overflow, under default rounding;
NaN payloads, denormal handling and other floating-point modes are not claimed.

Interpret four consecutive 16-byte memory groups as rows. For destination `A`
and source `B`, RVA `0x2ec780` overwrites `A` with:

```text
C[i,j] = (((f32(B[i,0]*A[0,j]) +f32 f32(B[i,1]*A[1,j]))
                         +f32 f32(B[i,2]*A[2,j]))
                         +f32 f32(B[i,3]*A[3,j]))
# Thus C = B * A in this row-storage interpretation.
```

`+f32` denotes one rounded float32 addition. This memory convention does not
establish gameplay axes or require the renderer to use the same notation.
All input rows load before output stores, permitting exact source/destination
aliasing. The independent adapter is pure and snapshots both inputs.

RVA `0x23fe10` replaces the top-left 3x3 with its transpose, clears the first
three homogeneous lanes, and sets the last row to:

```text
[-dot3(original_row0.xyz, original_translation.xyz),
 -dot3(original_row1.xyz, original_translation.xyz),
 -dot3(original_row2.xyz, original_translation.xyz), 1]
```

It performs no determinant calculation or scale division. This is a rigid affine
inverse when the linear part is orthonormal; scaled/sheared input still receives
the same arithmetic and must not be silently changed to a general inverse.

In the accessor recomputation branch, the parent-descriptor transform is copied,
passed through this transpose helper, then used as the destination of composition
with the incoming transform as source. Therefore the candidate local matrix is
`incoming * transpose_affine(parent)` in the stated row convention. The routine
then applies a translation tolerance/preservation rule before storing its final
result; that rule remains outside this helper validation. The prior unnamed
composition boundary is now resolved for these exact two helpers, not for every
matrix utility or every caller's semantic coordinate frame.

### Local translation preservation threshold

The local recomputation's remaining arithmetic is now implemented by
`recompute_accessor_local(parent, incoming, previous)`. After composition it
compares old and candidate translation with an inclusive componentwise float32
threshold whose bits are `0x3a83126f`, approximately `0.0010000000474974513`:

```text
candidate = incoming * transpose_affine(parent)
within = all(abs(f32(candidate.translation[i] - previous.translation[i]))
             <= f32(0.001) for i in [0,1,2])
if within:
    candidate.translation.xyz = previous.translation.xyz
    candidate.translation.w = 1
# Otherwise retain the entire computed translation row, including w.
# Candidate basis rows replace old basis rows on both branches.
```

This is a whole-vector preservation decision, not independent per-axis snapping
and not an angular/basis tolerance. The original SIMD masks both comparison
homogeneous lanes to zero. Its fourth comparison therefore passes for the finite
cases studied. No world-unit interpretation is assigned to this threshold.

The [76-case combined receipt](../../native/snow_host/accessor_local_math_validation.json)
executes the complete accessor propagation routine, including the original
transpose, multiplication, SIMD comparison, output copy and writer release.
Only thread identity, successful descriptor validity and parent-transform getter
are supplied services; child lists are empty. Exact output bytes match for
adjacent float32 values below/at/above the threshold on each axis with both
signs, differing homogeneous lanes, and forty synthetic parent/incoming pairs.
Writer state returns to unowned/zero depth in every case. This supersedes the
previous open translation-rule boundary. Child propagation internals, live
parent identity, lifetime and nondefault floating-point modes remain unresolved.

### Child transform candidate modes

The child service RVA `0x124bcd0` selects arithmetic by accessor field `+0x58`.
Using the row-storage convention above, let `L` be its local matrix, `P` the
incoming packet matrix, and `C` the supplied cached-transform getter result:

| Numeric mode | Candidate behavior |
| --- | --- |
| 0 | Compose `L * P`, then run basis-normalization helper `0x3728f0`; helper not yet modeled |
| 1 | Keep first three rows of `C`; translation row comes from `L * P` |
| 2 | Compose and normalize as mode 0; replace translation xyz with cached xyz and w with 1 |
| 3 | Keep cached basis; translation xyz = incoming xyz + local offset expressed in cached basis; w = 1 |
| 5 | Full `L * P` composition |
| Other values, including 4 | No candidate from the switch; optional modifier path may still supply one |

Modes 0/2 are static branch interpretations, not validated numerical models.
Modes 1/3/5 are implemented by `child_transform_candidate` and matched against
[72 original-instruction cases](../../native/snow_host/child_transform_math_validation.json).
The real composition helper runs; only cached-transform acquisition is supplied.
Execution stops before the modifier and virtual-dispatch phases. Mode 3 evaluates
each offset lane in the observed order `(local.z*C.row2 + local.y*C.row1) +
local.x*C.row0`, rounding each operation to float32 before adding incoming xyz.
These numeric IDs are not assigned guessed animation/attachment names.

Static continuation shows an optional modifier at accessor `+0x80` runs before
writer acquisition. If no candidate exists but a modifier is present, the routine
first fetches the cached matrix. If neither candidate nor modifier exists, it
returns. The eventual entity virtual `+0x90` receives the same candidate pointer
in both packet transform slots and packet flags with bit 1 cleared. Modifier
semantics, actual virtual receiver identity and normalization details remain
unverified here. The independent numerical adapter refuses modes 0/2 explicitly
and returns `None` for a switch that generates no candidate; it does not silently
skip a modifier or claim to execute the whole child service.

### Child modifier and entity dispatch validated

The [160-case complete-route receipt](../../native/snow_host/child_transform_dispatch_validation.json)
executes the child routine through normal return for modes 1/3/5 and noncandidate
modes 4/255. It varies modifier presence, incoming writer depth zero/two, four
packet flag words and two modifier-context tags. Composition and writer protocol
are original instructions; cache getter, thread identity, modifier and final
entity virtual callback are supplied services.

The modifier runs at incoming writer depth, before this invocation acquires its
writer claim. Its context pointer has the low two bits cleared. A synthetic
modifier edits translation x; the edited value reaches entity virtual `+0x90`.
For a noncandidate mode, a present modifier gets the cached matrix and still
causes entity dispatch. With no candidate and no modifier, no entity call occurs.
At entity dispatch writer depth is incoming depth plus one; normal return restores
incoming state. Both transform slots in the outgoing packet point to the same
candidate buffer, and outgoing flags equal incoming flags with bit 1 cleared.

`prepare_child_transform_packet` exposes the candidate/modifier/packet portion
for reconstruction clients. It preserves the two-slot alias and requires an
explicit modifier callable. Native context-pointer decoding, writer acquisition,
entity dispatch and lifetime are outside this pure preparation API. Modifier
signature, finite-result validation and Python memory ownership are authored.
This extends the earlier arithmetic model without treating the supplied native
callback stubs as reconstructed component implementations.

### Basis rebuild for normalized child modes

Helper RVA `0x3728f0` is now implemented as `normalize_transform_basis`:

```text
y = normalize(original.row1.xyz)
x = normalize(cross(y, original.row2.xyz))
z = normalize(cross(x, y))
result = [ [x,0], [y,0], [z,0], [original.translation.xyz,1] ]
```

The original first basis row is discarded. Each normalization computes
`n = f32(x*x + f32(y*y + z*z))`, with each product separately rounded.
It obtains a hardware `rsqrtps` seed `s`, then computes the scale factor as
`f32(f32(3 - f32(f32(s*n)*s)) * f32(0.5*s))`. Each vector multiplication is
also float32. Cross-product subtraction order is preserved by the adapter.

The [64-case receipt](../../native/snow_host/transform_normalize_validation.json)
executes the entire original helper without replacing instructions. It records
its three emulator-produced reciprocal-square-root seeds and supplies those to
the portable model. Output comparisons are byte-exact conditional on those seeds.
This does not prove cross-CPU `rsqrtps` equivalence or original-game live output.
Finite nondegenerate bases are covered; the adapter explicitly rejects zero or
nonfinite squared lengths rather than inventing a recovered fallback.

Child modes 0/2 now accept an explicit `reciprocal_sqrt` service and use this
helper after composition. Mode 2 then replaces translation with cached xyz and
w=1. This supersedes their earlier unconditional rejection; omission of the seed
service still refuses explicitly. Tests using `1/sqrt(n)` are authored numerical
examples, separate from original-instruction comparisons. The full child routine
for these two modes has not yet been compared end-to-end with captured seeds.

### Normalized child routes and runnable hierarchy example

The [64-case normalized-route receipt](../../native/snow_host/child_normalized_dispatch_validation.json)
now executes modes 0/2 from child-routine entry through normal return, including
original composition, basis rebuild, modifier path, writer protocol and final
packet construction. Getter/thread identity/modifier/entity implementation are
supplied services. Four flag words, modifier absence/presence, initial depths
zero/two and tagged modifier contexts are exercised. The complete output packet
matches the portable implementation byte-for-byte using the observed emulator
reciprocal-square-root seeds. This closes the previous end-to-end normalized-mode
validation gap within that scope, not cross-CPU or live component equivalence.

Run `python3 -m engine.examples.hierarchy_transform_probe` for a synthetic parent
and two children wired through the reconstructed entity/packet APIs. Mode 0 follows
the composed translation; mode 2 retains cached translation. Parent pre notification
precedes both child updates, and parent post notification follows them. Outgoing
flags are 29 from input 31. All logical entity-lock depths return to zero.

The example uses an explicitly authored exact reciprocal-square-root seed policy,
synthetic transforms, fixed child ordering, no modifier and supplied no-op cache
services. It does not recreate native accessor locks, dynamic linked-list traversal,
asset animation, or a live hierarchy snapshot. It is an executable integration
example of the recovered arithmetic and notification contracts, with those scene
and service choices kept explicit.

### Queue argument supplies the child transform mode

The hierarchy record field at `+0x74`, previously called `argument`, is forwarded
as the attachment mode. Completion routine RVA `0x1247740` loads it into the
fourth argument of reattachment wrapper `0x124ccd0`. That wrapper preserves it
through descriptor handling and forwards it to attachment routine `0x124cdd0`,
which writes it to the selected accessor's `+0x58`. This is the field read by
the child transform switch. The same mode is used whether a queued transform
pointer is supplied or null.

The [28-case joined receipt](../../native/snow_host/hierarchy_mode_transfer_validation.json)
executes the original completion, wrapper and attachment prefix through the mode
write. It covers modes 0..5 and `0xffffffff`, explicit/default transform selection,
and both high-bit states of the entity completion byte. Existing accessor storage
is supplied. Validity, attachment permission, parent resolution, detach and
descriptor assignment are intercepted. The low-seven-bit count begins at one,
so it reaches the reattachment branch. The test stops before subsequent modifier,
flag and transform setup and does not prove those opaque services or a live bind.

No mode-range validation occurs along this exercised accepting path: even
`0xffffffff` reaches accessor storage. Its later child behavior is the switch's
noncandidate path, where a modifier can still cause publication. Public queue
receipt keys retain `argument` for compatibility; interpret that field as
`attachment_mode` for this proven producer-to-consumer chain, not as a universal
meaning for similarly named fields elsewhere.

The constructor writes mode 0. The inspected FXSpawnedEntity explicit submission
at RVA `0x923a18`, helper call at `0xa95390`, and indexed-descriptor attachment
call at `0xd2ddc5` all supply zero in the mode argument. The latter two are static
call-site observations with unresolved owner/phase, not new live player evidence.
An indexed descriptor and child mode 0 are distinct concepts: descriptor mode
selects how a parent target is resolved; attachment mode selects transform math.
Do not substitute one for the other in decoded assets or reconstructed APIs.

### Attachment transform setup uses a distinct inverse

The accepting attachment path at RVA `0x124ceed` distinguishes null from explicit
transform input. Its null branch calls helper `0x2396b0`, not the rigid transpose
helper `0x23fe10` used by later accessor recomputation. The new helper contains a
cofactor-style SIMD calculation and `rcpps` followed by two reciprocal refinement
steps. A complete portable, byte-exact transcription remains open.

```text
if explicit_offset is not null:
    target = explicit_offset * parent_transform
    entity.publish_transform(target, target, flags=31)
else:
    local = current_entity_transform * inverse_helper(parent_transform)
    if descriptor_valid(accessor.descriptor):
        accessor.local = local
        parent_again = get_parent_transform(accessor.descriptor)
        propagate_child(accessor, [parent_again, parent_again, flags=31])
```

The null branch obtains the parent again before child propagation; the two getter
results need not be assumed identical under mutation. A validity failure skips
its local assignment and child call. Those failure/mutation variants have not
yet been exercised by this receipt. The explicit branch does not directly write
the accessor local matrix in this slice; it dispatches through the entity interface.

The [16-case setup receipt](../../native/snow_host/attachment_transform_setup_validation.json)
executes both setup branches with the actual inverse and composition helpers.
Parent getter, successful validity and terminal entity/child callbacks are supplied.
Fixtures vary parent scale and shear. Explicit-offset outputs match composition
byte-for-byte. Null-offset stored local matrices recompose to the original entity
transform with maximum per-element error below `1e-4`. This supports a general
inverse interpretation over the tested nonsingular fixtures; singular and
ill-conditioned matrices, arbitrary projective matrices and hardware reciprocal
seed variation remain untested.

The null branch thus derives a placement-preserving local candidate, but its
subsequent child mode may normalize the basis or preserve selected cached rows.
Do not claim final world placement is always unchanged, or substitute the rigid
transpose helper for this attachment-time inverse. Final lifecycle notifications,
actual child publication and concurrent parent identity remain outside this slice.

### Attachment inverse arithmetic

`reference.transform_inverse.inverse_transform(matrix, reciprocal_seed)` now
transcribes the lane arithmetic of helper RVA `0x2396b0`. It rearranges the input
rows, constructs cofactor vectors with the observed float32 multiply/add/subtract
order, reduces determinant lanes, refines reciprocal estimates twice, and scales
the cofactor vectors into output rows. ABI save/restore operations are omitted;
intermediate `v` names retain arithmetic dependencies rather than native pointers.
For each determinant lane `d` and supplied reciprocal seed `s`, refinement is:

```text
r = f32(f32(s+s) - f32(f32(d*s)*s))
r = f32(f32(r+r) - f32(f32(r*r)*d))
```

The separate ordering of the two refinements matters. The source preserves the
cofactor operation sequence rather than replacing it with a generic double-
precision matrix inverse. Native reciprocal seeds are supplied per lane; using
`1/d` is an explicitly authored numerical policy.

The [80-case receipt](../../native/snow_host/transform_inverse_validation.json)
executes the complete original helper with no instruction substitution and records
the emulator's reciprocal inputs/seeds. Portable output matches all 64 bytes for
forty affine and forty general well-conditioned synthetic matrices when given
those same seeds. This supersedes the untranscribed inverse boundary in the setup
section. It does not prove cross-CPU seed equivalence, singular/ill-conditioned
behavior, overflow or denormal behavior. The adapter rejects zero/nonfinite
determinant lanes by authored policy; no native failure fallback is claimed.

### Attachment setup read/validity order

`reference.attachment_transform_setup.initialize_attachment_transform` connects
the recovered inverse/composition helpers to explicit parent, validity, storage
and publication services. It implements the transform-setup phase after the
outer attachment has been accepted. Allocation, parent linking and final lifecycle
notifications remain external; this API does not perform a native attachment.

The [64-case joined receipt](../../native/snow_host/attachment_setup_order_validation.json)
executes original setup with real inverse/composition and observed reciprocal
seeds. Parent getter, descriptor validity and terminal publication are supplied.
It varies explicit/null input, validity success/failure, parent scale/shear, and
a synthetic change to the second parent read. Portable stored-local and published
matrices match original output bytes conditional on the captured seeds.

For null input, inversion and local computation happen before descriptor validity
is queried. Failure leaves accessor local storage unchanged and skips child
publication. Success stores the first-read-derived local matrix, reads the parent
again and publishes that second matrix to child propagation. A parent change is
not detected or reconciled by this slice. It must not be represented as a single
atomic parent snapshot in an inspection/modding API. The explicit-offset branch
uses one parent read and publishes directly without this validity query.

The portable service signatures and return labels are authored API choices.
Its published packet aliases both matrix slots and supplies flags 31. Runtime
pointer lifetimes, caller exclusion and what final child publication does to a
live entity are still outside the proof.

### Inner attachment acceptance is not a transactional reparent

The inner attachment prefix at RVA `0x124cdd0` resolves a parent, queries that
parent's descriptor first-holder link through `0x1248bd0`, and applies these checks
in order before allocating or assigning its attachment fields:

```text
reject if resolved_parent_link == child
reject if resolved_parent == child
reject if parent.owner != null and child.owner != null
          and parent.owner != child.owner
reject if not child.virtual_permission(resolved_parent)
otherwise continue attachment
```

`owner` names the compared `+0x60` field without asserting a universal world or
scene type. The parent-link query resolves the first holder of the parent's
accessor descriptor; its inspected body does not recursively walk ancestors.
These checks must not be advertised as complete cycle prevention. A null resolved
parent is not handled by this prefix before its parent-link query; the portable
planner rejects a missing supplied parent rather than simulating invalid memory.

The [48-case acceptance receipt](../../native/snow_host/attachment_acceptance_validation.json)
executes the original prefix with supplied resolution/link/permission services.
It verifies acceptance and whether the permission callback is reached across self,
parent-link, matching/conflicting/null owner and permission cases. Same-identity
fixtures keep their owner fields consistent. Child bytes remain unchanged in this
prefix, and execution stops before accepted mutation or rejection cleanup.
`plan_attachment_acceptance` exposes these local rules with authored reason labels.

The outer reattachment wrapper `0x124ccd0` calls detach with cleanup disabled
before invoking this inner routine on its accepted-descriptor path. Therefore
inner rejection does not establish that the previous relationship survives the
complete reparent operation. A future public mod API needs either a proved
preflight/rollback contract or explicit nontransactional semantics. No successful
rollback or live rejected-reparent experiment is claimed here.

### Concrete entity permission checks groups and requests flag propagation

Both constructor-backed entity tables `0x1ebbf78` and `0x1ebcbd8` bind permission
slot `0x98` to RVA `0x886980`. The metadata pointer it tests identifies
`EntityGroup` in the analysis image. Its interval predicate classifies a receiver
inside the group's type range. The callback then behaves as follows:

```text
if child is EntityGroup:
    reject if resolved group collection(child) contains parent
elif parent is EntityGroup:
    reject if resolved group collection(parent) contains child
if child.bit35 != parent.bit35:
    request_child_flag_setter(parent.bit35)
return allowed
```

The `elif` is material: when both are groups, this callback inspects the child
collection only. The collected-holder comparisons apply the status/TLS mask;
collection membership is not a bare saved-pointer comparison. Collector RVA
`0x8912d0` statically traverses managed records at `+0x210`, recurses for group
receivers and appends retained holders. Its recursion/lifetime behavior is not
validated by the callback receipt and must not be conflated with a complete,
concurrency-safe cycle detector.

The [32-case receipt](../../native/snow_host/attachment_permission_validation.json)
executes the complete permission callback, including its actual interval predicate,
member comparison, holder-release paths and accept/reject decision. Type getters,
group collection, TLS mask and the flag setter are supplied services. Fixtures
cover both group predicates, selected membership, and both values of each flag.
The flag setter is invoked only on an allowed path with mismatched bits and
receives the parent's bit. The meaning of bit 35 remains unnamed; its setter's
actual effects are not included in this proof.

`plan_entity_attachment_permission` exposes this selection/decision/effect order
using supplied membership results. This refines the earlier opaque permission
boundary. The earlier assertion that child bytes remain unchanged applies only
to the acceptance prefix with a stub permission service. Real permission is not
necessarily read-only: it can request flag propagation before attachment fields
are installed. The concrete live player's table and complete group reachability
still need separate evidence.

### Attachment flag propagation reaches skeleton-linked entities

Setter RVA `0x89a0c0` updates entity word `+0x98` bit 35 when different and calls
cache-refresh helper `0x86f990` on that change. Regardless of whether the bit changed,
it then visits linked hierarchy children through the actual first/next accessors.
After those children return, it resolves a component using metadata getter
`0xd4ba80`. The analysis-image metadata names `SkeletonComponent`. If found, its
16-byte records at `+0x280`, with count `+0x28a`, supply holder-resolved entities
that receive the same recursive setter. This is an entity-link collection, not
proof that these records are bone transforms or animation tracks.

The [32-case receipt](../../native/snow_host/attachment_flag_propagation_validation.json)
executes the original setter recursively, including its hierarchy getters and
actual flag writes. Cache refresh, component lookup and TLS mask are supplied.
A synthetic root has one hierarchy child; its optional skeleton list references
another entity and that same child again. All initial flag combinations and both
target bits verify hierarchy-first ordering, skeleton lookup afterward, unchanged-
bit traversal, and duplicate visits. The second visit to an already-updated child
does not refresh its cache but still performs its component lookup.

`plan_attachment_flag_propagation` reconstructs this order for supplied stable
resolved graphs. It preserves duplicates and does not use a global visited set.
Its visit bound is authored protection against unbounded inspection, not evidence
of native cycle detection. Concurrent link mutation, actual lookup lifetime, cache
side effects and cyclic native behavior remain untested. The flag's gameplay name
remains unknown; a cache connection alone does not justify calling it visibility,
collision, freezing or animation activation.

### Skeleton-linked propagation has a distinct mode switch

The existing [linked-object evaluation trace](CENTRAL_IMPULSE.md#the-optional-evaluation-call-propagates-linked-object-transforms)
already connects component `+0x280` records to transform propagation at RVA
`0xd64150`. Following that consumer now resolves its per-entry mode switch.
The routine composes and normalizes a base matrix before reaching the switch;
the switch must not be replaced wholesale with the ordinary hierarchy-child API.

| Mode | Skeleton-linked switch behavior |
| --- | --- |
| 0 | Publish precomputed normalized matrix |
| 1 | Cached basis plus precomputed translation xyz, w=1; publish |
| 2 | Precomputed basis plus cached translation xyz, w=1; publish |
| 3 | Cached basis plus provider translation and local offset expressed in cached basis; publish |
| Other, including 4 and 5 | Retain precomputed matrix but do not enable publication |

The existing optional modifier tail can still modify the retained matrix and
enable publication for any mode. In contrast, ordinary hierarchy mode 5 itself
publishes full composition, and an unknown hierarchy mode with a modifier fetches
a cached candidate. Those distinctions are observable and must remain separate.

The [84-case mode-switch receipt](../../native/snow_host/skeleton_link_modes_validation.json)
executes the original slice from mode load through candidate/publication selection,
with current-transform getter and successful descriptor validity supplied. Modes
0..5 and uint32 max are compared using synthetic matrices. Output bytes and the
publication-enable flag match `select_skeleton_link_transform`. The inputs model
already-computed provider/normalized transforms; this slice does not validate
the provider arithmetic, normalization, record selector loop, callback effects or
live synchronization. Mode 3's arithmetic shares the verified offset formula,
but that does not make the surrounding pathways equivalent.

This fills the earlier open per-entry mode semantics for the tested successful-
descriptor branch. The list's insertion/removal producers, selector/resource
mapping and actual player-linked membership remain further work. These records
must still not be presented as decoded bone tracks.


### Skeleton selector traversal ordering

`reference.skeleton_link_traversal.plan_skeleton_link_traversal` exposes the
recovered traversal as an event plan over supplied selectors and holder-resolution
results. The parameter `visible` means a non-null resolved target in this API;
it does not mean camera visibility, rendering visibility or a gameplay flag.
Inputs and output event names are our API design. Strict type/range validation
is authored. Provider computation and the target update body remain external.

The routine caches only the last selected selector, initially uint16 max.
A requested selector other than uint16 max filters records before that cache is
consulted. A changed selected selector requests the provider transform before
resolving the target. Thus an unavailable target can still cause provider work,
and a sequence 7,9,7 requests it three times. Filtering that sequence for 7
requests it once: the skipped 9 never changes the cache.

An all-selectors request clears pending bit zero on return, even for an empty
list. A specific-selector request preserves the pending byte. A first record
whose selector is uint16 max matches the initial cache sentinel and skips provider
initialization. The planner exposes this as `provider_initialized=False`; it must
not supply an identity matrix or reuse a fabricated pose to hide the boundary.
Whether such a record is valid or reachable in a live list is unknown. This
synthetic observation does not establish a live uninitialized-transform defect.

The [108-case receipt](../../native/snow_host/skeleton_link_traversal_validation.json)
executes original entry, filter, selector-cache comparison, holder resolution,
loop and return instructions. Provider work is replaced by cache completion;
the target body is skipped and the TLS mask is supplied. Cases cover empty,
repeated, interleaved and sentinel selectors, requested filters, null targets and
pending bytes. The tests compare full ordered event plans and pending results.
This extends the mode-switch evidence without proving provider arithmetic,
selector-to-bone mapping, live membership, concurrent list mutation or complete
skeleton evaluation. The next useful boundary is provider pose acquisition and
its coordinate conversion before the already-decoded target mode switch.


### Skeleton provider pose conversion

The linked-object provider getter is a direct uint16 index into a pose array,
with 32 bytes per record: four position lanes followed by four quaternion lanes.
It performs no bounds check in the inspected getter. The count and allocation
layout were already recovered in the [provider metadata research](CENTRAL_IMPULSE.md#provider-metadata-supplies-a-transform-bound-and-allocation-size).
The complete producer chain, resource mapping and selector-to-bone interpretation
remain unresolved. The portable API accepts supplied records rather than reading
native memory.

The conversion tests provider flag bit 26. When set, it passes the record's
position and quaternion through. Otherwise it applies the provider's base
position and quaternion. `already_transformed` is our descriptive gate name;
its producer and the absolute coordinate frame are not proved by this consumer.
With base quaternion `q=(u,w)`, record position `p`, record quaternion `c`, and
base translation `b`, the recovered arithmetic is:

```text
position = b + 2 * (u * dot(u,p) + w * cross(u,p) + (w*w - 0.5) * p)
rotation = HamiltonProduct(q, c)
```

For unit `q`, the first expression is quaternion rotation plus translation.
The routine does not normalize `q` or `c`; silently normalizing would change
non-unit behavior. `convert_skeleton_provider_pose` preserves the inspected
float32 multiplication/addition ordering rather than just evaluating those
real-number formulas. It returns position xyz and quaternion xyzw. The following
matrix-conversion call and translation-w replacement are outside this API.
Input finite-vector/type guards are authored, not recovered native checks.

The [120-case receipt](../../native/snow_host/skeleton_provider_pose_validation.json)
executes the original selector getter and conversion block with synthetic arrays,
without replacing calls. Both flag branches, multiple record indices, identity
base rotations and general non-unit quaternions are covered. Position xyz and
quaternion output bytes match the portable implementation. This proves the
local conversion for those inputs, not the upstream pose generation, native
array lifetime, live player bone mapping or complete animation evaluation.


### Provider evidence reconciliation and inspection path

The linked-object conversion is a second consumer-side validation of arithmetic
already exposed by `reference.ground_response_pose.provider_pose_transform`.
It is not a newly discovered pose format or a newly completed animation producer.
The earlier [pose-channel observer](CENTRAL_IMPULSE.md#pose-channel-observation-from-supplied-component-identity)
already joins a sorted uint32 key lookup to a low-16-bit record index, provider
storage and pose conversion. The lookup's key names and relationship to authored
bone names still require evidence; a numeric selector is not by itself a bone name.

The metadata supplies a transform-record count independently of allocation byte
size. `pose_bank_layout` and `capture_pose_channels(record_count=None)` already
validate that relationship. Typed channel copying and bank-combination copy modes
also have recovered implementations. Those are partial storage producers, not a
complete explanation of clip evaluation or every writer to the bank.

Cross-consumer regression now checks the earlier 240 conversion cases through the
linked-object API and the new 120 linked-object cases through the existing passive
reader with synthetic memory. Position xyz and quaternion bytes agree in those
fixtures. The reader retains four position lanes; the linked-object API returns
three, so this comparison deliberately makes no equivalence claim for position w.
It also does not establish equivalence for all floating-point edge cases or
native object identity. These tests reuse recorded native receipts and do not
represent additional native executions or a live capture.

The practical inspection entry remains `engine.pose_channel_observation.capture_pose_channels`.
It needs a caller-supplied read transport, fresh component identity and guards;
sequential rechecks do not pin lifetime or make a snapshot atomic. Remaining work
should follow the producer/caller chain and resource-key mapping, rather than
reimplementing the already available metadata decoder and channel reader.


## Graphics sibling exclusion probe

The runnable `engine.examples.begin_commands_probe` now also composes the
registered graphics sibling chain with the entry/stop branch. It reserves and
executes a synthetic GraphicFrame callback but deliberately delays its dispatch
finalization. Commands and either selected world/paused route can execute while
that graphics dispatch remains outstanding. The authored terminal waits until
the graphics chain is finalized. Tests cover both branch selections.

This demonstrates the ordering limits of the reconstructed graph, not native
parallel execution or a complete frame graph. In particular, being inside
BeginEngineFrame after command flushing is not enough to authorize changes to
objects still accessible by graphics. A mod command needs an operation-specific
ownership/exclusion contract in addition to a named phase. Loading and idle
workers are not modeled by this probe and remain separate concerns.


## Command executor entry paths and callback tail

A focused direct-call audit finds ten validated call instructions targeting the
executor: one in BeginEngineFrame, one in the small profiled wrapper, and eight
in the transition helper previously associated with the BeginFrame stop-mode
path. The wrapper itself has two validated direct callers; the transition helper
also has two. These counts are a bounded image search, not a complete call graph.
Indirect calls, tail jumps and protected/unlisted bodies remain outside it.
See [entry audit](../../native/snow_host/command_executor_entry_validation.json).

Consequently, observing the executor address or its execution flag alone cannot
identify a once-per-frame mod callback. The eight sites are distinct instructions
in one helper, not evidence of eight executions in a recorded session. A native
observer must retain caller/request provenance and distinguish regular frame
entry from transition-driven flushing.

The inspected executor body has this local ordering (descriptive names; opaque
callees remain unresolved):

```text
execute_engine_commands(manager):
    manager.executing_byte = 1
    flush_hierarchy_commands(manager)
    service_A(manager)
    ready = service_B(manager)
    if not ready or global_state.flag52 != 0:
        service_C(manager)
    service_D(manager.embedded58)
    global_service.virtual60()
    cursor = manager.callback_array
    end = manager.callback_array + manager.callback_count_u16
    while cursor != end:
        callback = *cursor
        callback.virtual0()
        cursor += 1
        end = manager.callback_array + manager.callback_count_u16
    manager.executing_byte = 0
```

The flag at manager +0xbc is set and cleared with ordinary byte stores in this
body. No test-and-set, recursion rejection, or locking is visible in those stores;
outer callers or callees may still serialize execution. The callback array at
+0xb0 and 16-bit count at +0xba are reread after every virtual call. The cursor
continues from its previous address rather than being rebuilt from the reread
base. This is not an immutable callback snapshot. It does not establish that
callbacks are permitted to resize or mutate the list; doing so could invalidate
the cursor. No unconditional exception-cleanup guarantee follows from the normal
return's byte clear.

The next productive binary search is for writers of this concrete callback list,
its registration/removal and destruction paths, and checks of the execution byte.
That can establish whether this is a usable existing registration mechanism,
what callback ownership it expects, and how removal waits for execution. Until
then, do not install arbitrary mod objects into this list or interpret the byte
as a lock. This work is separate from player timing and deterministic stepping.


## Command participants have a preparation dispatch

The same manager and callback array also appear in the preparation routine at
RVA `0x67ced0`. Its prefix performs two atomic counter transfers before invoking
slot +8 on each entry. The executor later invokes slot 0. This supports describing
the entries as two-phase command participants; it does not identify their concrete
classes or turn either slot into a public mod API.

```text
prepare_command_participants(manager):
    deferred_A = atomic_exchange(manager.deferred_A, 0)
    atomic_add_wrapping_u32(manager.active_A, deferred_A)
    deferred_B = atomic_exchange(manager.deferred_B, 0)
    atomic_add_wrapping_u32(manager.active_B, deferred_B)
    cursor = manager.callback_array
    end = manager.callback_array + manager.callback_count_u16
    while cursor != end:
        (*cursor).virtual8()
        cursor += 1
        end = manager.callback_array + manager.callback_count_u16
    # Additional locking and processing follow; not modeled by this prefix.
```

The counter pairs are manager +0x50/+0x54 and +0xa8/+0xac. Each deferred field
is exchanged separately, then added into its active field with `lock xadd`.
The two transfers are not one atomic transaction. Counter meaning beyond the
observed active/deferred roles remains tied to the surrounding consumers.

The [16-case original-instruction check](../../native/snow_host/command_participant_prepare_validation.json)
uses empty, single, reordered and duplicate participant lists, plus zero,
ordinary and wrapping counter combinations. Both transfers complete before
all intercepted participant calls. Duplicate entries receive repeated calls.
Original prefix instructions execute; participant bodies are synthetic returns,
and execution stops before the later manager lock. This validates local ordering
and arithmetic, not mutation safety or native concurrent execution.

The transition helper calls this preparation repeatedly before its corresponding
executor calls. Other observed direct paths also call preparation, so neither
method is inherently once-per-frame. A candidate participant must be researched
as a pair of behaviors with explicit lifetime and reentrancy constraints.

Registration/removal is still open. The local offset scan did not establish a
writer of this specific list; same-offset fields on unrelated objects were not
accepted as evidence. Next follow construction/destruction of this exact manager
and identify concrete participant tables implementing both slots. Avoid reusing
unrelated array append helpers until their receiver identity is established.


### Executable counter-transfer interleavings

`engine.command_counter_transfer.replay_counter_transfers` exposes each deferred
exchange and active add as a separate event. Its sequential transfer results
match all 16 original-prefix cases above. The harness also accepts explicitly
synthetic submission increments to test ordering: an increment before exchange
is included in that transfer, while one after exchange remains deferred even
when the captured old value is subsequently added to active. Pair A can finish
while pair B is not yet transferred. Arithmetic wraps at 32 bits.

The harness is not a concurrent implementation or a recovered submission API.
It accepts caller-selected event order, does not invoke callbacks, and exposes
pending transfers and every intermediate state. The native producer, exact
manager construction, participant registration/removal and lifetime guarantees
remain unresolved. The singleton in the inspected image is null; matching raw
field offsets in other types did not establish its constructor. A fresh live
manager/participant-table observation is the next useful qualification step.


## Live command participant identity

`engine.command_participant_observation.observe_command_participants` now reads
the build-qualified manager singleton, list header, at most 32 participant
pointers, tables and the two method slots. Two complete structural samples must
agree. Reads are bounded to 134 operations/2100 bytes, and tables/method targets
must lie in caller-qualified image/code ranges. This is structural observation,
not invocation or lifetime proof. Heap addresses remain private provenance.
Synthetic tests cover empty/max lists, shared tables, every short-read position,
null manager, count limits, invalid targets and changing method pointers.

The first live use returned one stable participant across three observations at
roughly 15.6–17.1 seconds of host uptime. Host readiness was established, but the
samples did not require or prove gameplay readiness. No movement, hold or release
commands were issued. Cleanup passed. See [live receipt](../../native/snow_host/command_participant_live_observation.json).

The observed table has RVA `0x1efbe38`, execution method `0xa95450`, and preparation
method `0x75e600`. Static inspection of preparation shows a no-op return. Execution
iterates a handle container at participant +8, retains each returned holder,
resolves its payload through signed status, calls `0x89f730(payload, 0, 1)` for
visible nonzero targets, releases the holder, advances the iterator, and finishes
through the container helper. Iterator and target-operation semantics remain
unresolved; this is not a claim that it implements arbitrary commands.

Two validated table-installation sites now give concrete owner leads. The
constructor at RVA `0xa708a0` embeds the participant at owner +0x4b8, zeros its
container pointer, and publishes it to a singleton slot only if that slot is null.
The teardown candidate at `0xa77a50` reinstalls the same table, clears that singleton
only if it equals this embedded participant, and calls the container helper.
These paths do not yet prove removal from the command manager's participant list.
The next join is between this participant singleton, manager-list registration,
and owner teardown, followed by decoding the participant's target operation.


## Participant execution bypasses re-deferral

Following the observed participant singleton identifies a producer at RVA
`0xa7d870`. If the participant singleton is absent it returns immediately.
Otherwise it obtains the supplied object's holder at +0x180 (or a default holder
for null input), retains it, and passes it to insertion helper `0xacacf0` on the
participant's embedded container. The helper releases that temporary holder
reference on either insertion-result branch. The internal container publication
and synchronization helpers remain unclassified; this is not a generic mod queue.

The participant's execution target `0x89f730` has a concrete reentrancy rule.
After its eligibility and ancestor/target-selection work, it calls a getter
that reads the command manager's execution byte at +0xbc. The selected branch is:

```text
if manager.executing_byte != 0 and bypass_defer == 0:
    enqueue_selected_target(selected_target)
else:
    apply_operation(selected_target, selected_ancestor, local_zero_word)
```

The observed participant invokes this target with argument bytes `(0, 1)`;
the third argument supplies `bypass_defer`. Thus execution of deferred work takes
the immediate branch even while the manager's executing byte is set. The byte
is a deferral predicate for this route, not a mutual-exclusion primitive or a
universal rule for every engine mutation. The complete recursive operation and
its exact high-level purpose remain unresolved.

`engine.command_mutation_route.select_command_mutation_route` implements this
local branch for uint8 inputs. The [16-case receipt](../../native/snow_host/command_mutation_route_validation.json)
executes the original branch and actual byte getter with values 0, 1, 2 and 255
for each flag. Enqueue/apply bodies are intercepted; all choices match the
independent function. This does not validate prior target selection, mutation,
container lifetime, or registration/removal from the command manager.

This gives an end-to-end structural join from executor -> concrete participant
-> guarded operation -> deferred producer -> participant container. It is not
an observed execution trace. Next decode container publication/clearing and the
selected operation, while separately locating manager-list membership writers.


## Compact participant container is a deduplicating key set

The insertion helper at RVA `0x108d060` branches on the low three bits of the
container word. Tag 6 uses a compact sorted array of unsigned 64-bit keys. Its
allocation begins with `count - 1`, followed by keys. A matching key returns 0
without insertion. A missing key is inserted at its unsigned-order position and
returns 1; storage may be shifted in place or reallocated using size-class data.
An empty zero container allocates the first compact entry. Inserting a new key
into a 31-key compact container takes a tag-7 promotion path, whose internals
remain outside this implementation. Duplicate lookup at 31 keys stays compact.

```text
compact_insert(sorted_unique_keys, key):
    index = unsigned_lower_bound(sorted_unique_keys, key)
    if index points to key:
        return unchanged, 0
    if count == 31:
        return promote_and_insert(...)  # separate unresolved representation
    insert key at index, preserving unsigned order
    return updated, 1
```

`engine.command_compact_set.compact_command_insert` implements logical compact
membership and duplicate behavior. It rejects unsupported promotion rather than
inventing the tag-7 representation. Its [27-case instruction comparison](../../native/snow_host/command_compact_set_validation.json)
executes the original insertion routine with allocation/free services intercepted.
Cases include empty, existing and 30/31-key sets, duplicate insertion, unsigned
high-bit and maximum keys. All returned membership/result pairs match. Synthetic
allocation succeeds; native allocation failure and concurrency are untested.

For this participant, producer keys are holder addresses, so repeated submission
of the same holder is coalesced in the compact representation. This is not FIFO
command storage. Logical key ordering is established; full iterator behavior and
publication during iteration still need separate validation.

The compact clear branch frees the compact allocation and zeros the container
word; it does not visibly walk keys to release holder references. The insertion
routine likewise stores raw keys. Temporary retain/release around submission and
around each execution callback does not prove a queued holder remains owned for
the entire deferred interval. That lifetime must come from another owner or
contract; it is unresolved. Do not infer persistent retain semantics merely from
the fact that the key denotes a holder.


## Compact key iteration and mutation boundary

The participant begins with cursor zero and invokes the first/seek helper.
For compact tag 6, first returns the cursor unchanged if that exact key exists;
otherwise it delegates to next. Next increments the uint64 cursor, then seeks
the first key greater than or equal to that incremented value. Thus normal next
visits keys strictly above the previous key, in unsigned address order.

```text
first(keys, cursor):
    if cursor in keys: return found, cursor
    return next(keys, cursor)
next(keys, cursor):
    if container is empty: return exhausted, cursor
    previous = cursor
    cursor = uint64(cursor + 1)
    if previous == UINT64_MAX: return exhausted, cursor
    key = unsigned_lower_bound(keys, cursor)
    if key exists: return found, key
    return exhausted, cursor
```

`engine.command_compact_set.compact_command_seek` preserves the output-cursor
write even on nonempty exhaustion; a maximum cursor wraps to zero and ends.
The [100-case instruction comparison](../../native/snow_host/command_compact_iteration_validation.json)
executes original first/next, membership and compact lookup code without helper
substitution on covered paths. Empty and compact sets, zero and high-bit keys,
31 entries, absent cursors and uint64 exhaustion all match. The larger tag-7
traversal and native concurrent mutation are not validated.

Because each call searches the currently supplied set by value, this is not an
immutable snapshot traversal. In serial synthetic changes between calls, a newly
inserted key below the cursor is skipped, while a higher key can be visited.
Removing the current key does not prevent seeking the next greater key. Those
logical effects do not grant permission to mutate native storage concurrently;
allocation and iterator exclusion remain unresolved. The observed participant
clears its container after traversal, so publication during traversal must be
understood before treating it as a reliable general mod-command mechanism.


## Participant execution, reference bracket and TLS context

The submission wrapper's helper at RVA `0x11751c0` resolves the module TLS block
through the Windows TLS array and writes its argument at block +0x40. Submission
sets this field before insertion and clears it with zero afterward. The helper
contains no lock acquisition or atomic ownership operation. Its semantic purpose
remains unnamed; it is a context setter, not evidence of container serialization.
This local observation does not exclude locks in outer callers or other helpers.

An [18-case connected instruction check](../../native/snow_host/command_participant_execution_validation.json)
now executes the participant body together with original compact first/next and
clear paths. Apply, holder-retirement and storage-free services are intercepted.
Synthetic sets contain zero, one or three holders; reference counts and status
bits vary. The check establishes these local rules:

- Each encountered holder is incremented before payload resolution.
- Signed status selects visibility; invisible holders skip the apply call.
- Visible nonzero payloads receive arguments `(0, 1)` while the temporary
  reference is held. Calls follow compact unsigned key order.
- The holder is decremented afterward. A resulting zero with low 24 status bits
  clear selects the retirement helper; other cases skip retirement.
- Normal traversal completion clears the compact container after holder handling.
  Storage free is last, and the container word becomes zero.

The zero-reference test cases establish instruction branching on synthetic
readable storage, not permission to use a native dead holder. A temporary retain
inside execution cannot protect a holder that was already invalid before that
instruction. No whole-deferred-interval ownership guarantee follows.

The connected test does not run the apply operation, real allocator/retirement,
callback fault paths, tag-7 representation or concurrent publication. The core
mod-loader gap is still manager-list registration and lifecycle exclusion, not
more confidence in compact arithmetic. Next prioritize the exact manager's list
writer/removal path and participant ownership rather than extending unrelated
container branches.


## Participant registration and removal resolved locally

Following the concrete owner's embedded address reveals both manager-list
operations. Owner method RVA `0xaaf760` passes `owner +0x4b8` to registration
wrapper `0x653de0` near entry. Owner cleanup method `0xab68d0` passes the same
embedded address to removal wrapper `0x68b410` at its tail. Both wrappers load
the exact command-manager singleton and target its array at +0xb0.

These wrappers are leaf functions without exception-table records. Earlier
searches requiring exception-table membership missed them. Absence from that
search was not evidence of protected code or absent registration. Their complete
short instruction sequences and tail targets are now inspected and hashed.

```text
register(manager, participant):
    if participant already occurs in manager.participants:
        return false
    ensure_capacity_for_one_more()  # allocator/failure contract still external
    append participant
    return true

remove(manager, participant):
    index = first matching entry
    if absent: return false
    if index is not last:
        entries[index] = entries[last]
    count -= 1
    return true
```

Registration helper `0x999d70` uses a membership search and appends unique raw
pointers. Removal helper `0x766ab0` calls the index eraser `0x115b8d0`, which
copies the last eight-byte element into the removed slot and decrements the
16-bit count. It does not shift the intervening entries. Consequently removal
can change subsequent callback order. If a synthetic list contains duplicates,
only its first match is removed. Neither local path invokes participant methods
or visibly retains/releases participant ownership.

`engine.command_participant_registry` reconstructs membership changes on supplied
storage with sufficient capacity. The [40-case instruction comparison](../../native/snow_host/command_participant_registry_validation.json)
executes original singleton wrappers, search, append and removal instructions;
only the eight-byte copy primitive is intercepted. Empty, first/middle/last,
absent, duplicate-registration and duplicate-initial-list cases all match.
Capacity growth and allocation failure remain outside this model.

No execution-byte check, mutex or wait-for-callback appears in these local
registration/removal paths. This closes the local list-operation gap, not the
native concurrency or unloading contract. Removing a pointer does not prove a
callback already holding it has returned. The owner methods' calling phases,
serialization with executor traversal, and their ordering before destruction
must be established before installing third-party participants. Those are now
specific caller/lifetime targets rather than unknown registration functions.


## Owner lifecycle dispatch and destruction boundary

A [static lifecycle audit](../../native/snow_host/command_owner_lifecycle_audit.json)
checks 11 instruction anchors and six dispatch entries. Constructor writes
establish the tables directly; no RTTI or original class name is assumed.
The derived constructor calls the base constructor before replacing its table.

| Owner dispatch offset | Base target RVA | Derived target RVA | Observed role |
| --- | --- | --- | --- |
| `+0x00` | `0xa7c700` | `0x1c86f0` | Deleting destructor wrapper |
| `+0x90` | `0xaaf760` | `0x20d2c0` | Registration-containing lifecycle method |
| `+0xc8` | `0xab68d0` | `0x21d380` | Removal-containing lifecycle method |

The base table is at RVA `0x1efbe68`; the derived table is at `0x1e0f650`.
Their constructor anchors are `0xa708c4` and `0x1b314e`. These addresses identify
this build only and are not plugin API constants.

```text
derived_registration(owner, argument):
    base_registration(owner, argument)  # includes participant registration
    perform_derived_setup(...)

derived_removal(owner):
    perform_derived_cleanup(...)
    tail_call base_removal(owner)      # includes participant removal

deleting_wrapper(owner, flags):
    destroy_owner(owner)
    if flags & 1:
        deallocate(owner, owner_size)
    return owner
```

The base deleting wrapper supplies size `0x4d8`; the derived wrapper supplies
`0x550`. The derived destructor tails into the base destructor. Within base
destruction, the embedded participant table is reset, its global pointer is
cleared if it still points at this participant, and its pending container is
cleared. Clearing that global pointer is distinct from removing the participant
from the command manager's array.

Registration/removal therefore have distinct dispatch entries from destruction.
This does not prove that a destructor's transitive callees cannot perform
additional unregistration. Nor does the derived cleanup order establish that
callbacks have drained before cleanup starts. The next required link is the
receiver-qualified caller of these lifecycle slots and its synchronization with
the command executor. Generic calls through `+0xc8` occur across unrelated
classes, so slot equality alone cannot identify a removal caller.

This audit is static evidence. No live lifecycle observation, concurrency test,
or safe third-party participant installation is claimed.


## Named owner correction: UIManager and UIManagerGame

The [named-type audit](../../native/snow_host/command_owner_type_audit.json)
resolves the previously unnamed owner through constructor metadata, independent
of RTTI. This supersedes the earlier unknown-name boundary, while preserving
its unresolved scheduling and lifetime boundaries.

| Metadata name | Name field RVA | Recorded size | Constructor thunk | Constructor |
| --- | --- | --- | --- | --- |
| `UIManager` | `0x2e62838` | `0x4d8` | `0xa6a8e0` | `0xa708a0` |
| `UIManagerGame` | `0x2c7b7e8` | `0x550` | `0x19b8b0` | `0x1b3140` |

Each record points to the exact null-terminated name. At name-field +0x10 it
records the size matching the deleting wrapper; at +0x38 it points to a short
constructor thunk. Both thunks directly jump to the constructor whose table
installation was audited above. `UIManagerGame` calls the `UIManager` constructor
before installing its derived table. The thunks have no exception-table entry,
so a direct-call-only constructor search did not find the registration metadata.

The participant at owner +0x4b8 is therefore a UI-manager-owned participant.
Its live table and execute/prepare identities remain valid observations. The
prior live sample did not read the enclosing owner's primary table, so it does
not establish which derived owner type was instantiated in that session.

This matters for reconstruction: the engine command manager can host subsystem
participants, and the one observed so far is associated with UI. Its compact
pending set and deferral bypass must not be presented as a proven universal
physics-command queue. The applied target operation is still unnamed; ownership
alone does not determine every operation that a UI manager can request.

Next separate the engine-wide dispatch contract from this participant's local
UI lifecycle. A bounded live observation can qualify the enclosing owner table
using the embedded offset and same-build table identities. A caller trace must
still prove the phase and any drain before removal. Other subsystem interfaces
need their own receiver and lifetime evidence rather than inheriting this
participant's semantics.
