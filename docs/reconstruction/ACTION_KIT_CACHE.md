# ActionKit pointer cache

`ActionKit` is the resource type behind the previously labeled
`animation_resource_a` finalization route. It is not the player skeleton type.
The type metadata names it and joins its constructor, finalizer, object size,
vtable resource reader and type getter. Those links identify the receiver without
assigning semantic names from proximity in the executable.

## Inspected layout

This layout is specific to the studied 64-bit build. Offsets are evidence fields,
not a portable live-process API. No serialized ActionKit payload is included.

| Offset | Inspected role |
| --- | --- |
| `0x00` | Virtual table installed by the constructor |
| `0x10` | Source array of control-record pointers |
| `0x1a` | Source count, uint16 |
| `0x4c` | Cache array of resolved raw object pointers |
| `0x56` | Cache count, uint16 |
| `0x78` | Cache lock |

The type metadata and deleting destructor agree on an object size of `0xa8`.
The constructor zeroes the source/cache array descriptors and requests lock
initialization. The [32-case identity/constructor receipt](../../native/snow_host/action_kit_identity_validation.json)
checks metadata joins and executes the original constructor and array initializers
from varied synthetic storage. Lock initialization is intercepted.

## What the cache does

The [portable implementation](../../reference/object_pointer_cache.py) resolves
source records through status bit 31 and the current thread visibility mask. It
builds only while cache count is zero. Once a nonempty cache exists, later calls
leave it unchanged, including null entries. It takes no additional object or
record references. The [96-case two-call receipt](../../native/snow_host/pointer_cache_validation.json)
checks this behavior against the original instructions.

Registration places the finalizer in the before-readiness callback category.
See [registration evidence](CENTRAL_IMPULSE.md#concrete-animation-side-registration-routes)
and [cache pseudocode](CENTRAL_IMPULSE.md#animation-resource-raw-pointer-cache).
There are also direct calls from action-related runtime setup paths; registration
is not the only way the builder is reached. Those direct callers have not yet
been validated as complete runtime paths.

## Lifetime and reset limits

Static destructor inspection shows that it destroys the cache lock, frees owned
cache storage according to its array-storage flags, and releases the source
handle array through a separate helper. The full destructor has not been emulated here. The source-array helper is now
validated separately below. Do not infer the lifetime of every cached object from the
cache builder, which itself retains nothing.

Constructor initialization is established. A bounded scan of the nearby animation
routines found the cache builder's direct count write but did not establish an
in-place invalidation/reset path. Indirect array operations and code outside that
scan remain possible. Reconstructing an ActionKit by calling its constructor over
a live instance is not a supported cache-reset operation.

Before exposing this through a mod API, trace the source-handle array's ownership,
consumer access to the raw-pointer cache, and any mutation/invalidation protocol.
This resource can help explain action binding and finalization timing. It does
not by itself provide a skeleton pose snapshot or an animation-frame callback.

## Source handles own references

The destructor's source-array helper is now decoded and validated. Its element
cleanup decrements each record's ownership word at `+12`, not the record-only
count at `+8`. When the resulting low 24 bits are zero, it requests retirement.
This happens once per array slot, so repeated slots referencing the same record
release multiple ownership references.

Two independent bits in the array descriptor control cleanup:

| Storage flag | When clear | When set |
| --- | --- | --- |
| Bit 14 | Release each element's ownership | Skip element releases |
| Bit 15 | Free nonnull array storage | Skip storage deallocation |

```python
if not (array.storage_flags & 0x4000):
    for record in array.slots:
        after = atomic_decrement_u32(record.status)
        if (after & 0xffffff) == 0:
            request_retirement(record)
if array.storage_pointer is not None and not (array.storage_flags & 0x8000):
    free_array_storage(array.storage_pointer)
# This helper does not clear the array pointer, count or storage flags.
```

The [cleanup planner](../../reference/handle_array_cleanup.py) preserves repeated
aliases and effect order. Its [96-case original-instruction receipt](../../native/snow_host/handle_array_cleanup_validation.json)
executes the full array helper and per-record release loop. Cases cover all four
flag combinations, null/empty storage, repeated references and final/nonfinal
releases. Retirement, allocator lookup and storage deallocation are intercepted.
The descriptor remains unchanged and record-only counts remain untouched. Full
ActionKit destruction and source-array acquisition are not executed by this check.

This refines the lifetime interpretation. The cache builder acquires no references,
but source-array slots with element cleanup enabled carry ownership obligations
that can support the cached objects' lifetime. Runtime flags and external mutation
still need validation; borrowed arrays do not establish the same ownership.
Calling this destructor helper twice would repeat releases or deallocation because
it does not invalidate its descriptor. It is not an in-place cache reset API.

## Source-handle acquisition and tagged input

The ActionKit reader iterates its source slots and passes each to a generic
reference reader. The non-inline branches of that reader now have original-
instruction validation. Successful assignment acquires ownership rather than
merely copying a record address:

```python
record = lookup_identifier_or_sentinel(identifier)
atomic_increment_u32(record.status)       # lookup temporary, under pool lock
atomic_increment_u32(record.status)       # destination slot ownership
old = atomic_exchange(destination_slot, record)
release_ownership(old)
release_ownership(record)                 # drop lookup temporary
```

For the null identifier, the sentinel path supplies the temporary reference without
registry lookup. Distinct old/new records lose/gain one net ownership reference.
When they alias, counts return to their initial values. The
[assignment model](../../reference/record_retirement.py) preserves the operation
order and retirement requests instead of assuming distinct records.

The inspected serialized reference reader has these branches:

| Leading byte | Prefix consumed | Observed behavior |
| --- | --- | --- |
| `1` | tag, auxiliary byte, uint64 identifier: 10 bytes | Optional reader policy checks the identifier; accepted references assign ownership. A follow-up service receives identifier, field key and auxiliary byte even after rejection. |
| Other nonzero values | tag, skipped byte, uint64 identifier: 10 bytes | Assign ownership directly; the skipped byte does not drive this branch's assignment. |
| `0` | Separate longer path | Acquires a record, reads further fields and invokes object creation/reading services; not validated in this pass. |

The byte roles are local decoding observations, not a complete asset-format
specification. The auxiliary byte's wider meaning and the follow-up service's
contract remain open. The concrete ActionKit call site supplies field key
`0xef82fce4`; a symbolic meaning for that key is not established here.

If the tag-1 policy rejects an identifier, the reader decrements the old slot's
ownership and stores the sentinel. This reset path does not perform a balancing
sentinel increment. The inspected sentinel handling must not be generalized into
ordinary reference transfer. A follow-up request still occurs after reset.

The [96-case reader receipt](../../native/snow_host/reference_reader_validation.json)
executes the complete original reader for tags 1, 2 and 255, with contiguous input,
existing records and the object resolver disabled. Original record lookup,
assignment and rejection-reset code execute. Locks, map search, policy, retirement
and follow-up request services are intercepted. Cases cover null/nonzero identifiers,
aliasing, rejection, auxiliary bytes and status flags. It consumes exactly 10 bytes
on these paths. Inline objects, refill, record allocation and the full enclosing
ActionKit reader are outside this receipt.

Together with finalization and cleanup, this establishes the local lifecycle for
ordinary source slots: acquire owned record, resolve into a raw-pointer cache,
release ownership during array destruction. It does not establish safe concurrent
mutation, automatic cache invalidation after slot replacement, or a live mod API.
