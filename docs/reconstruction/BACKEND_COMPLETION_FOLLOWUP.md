# Queued backend callbacks and completion accounting

A bounded static follow-up identifies the queued-record consumer's normal callback branch and its matching completion decrement. This narrows an open item in the earlier backend research. It does not establish a global scheduler barrier, submission exclusion, thread lifetime or callback exception behavior.

## Concrete record and counter join

The existing backend scheduler builds a 24-byte record containing a kind, a recycled group slot, a callback and a callback argument. The newly inspected consumer reads from the same queue layout, decodes the same callback-record kind and indexes the same two counter arrays using the record's group slot.

For that normal record branch, the operation order is:

```text
consume_callback_record(manager, record):
    atomic_add(manager.not_started[record.group_slot], -1)
    record.callback(record.argument, false)
    atomic_add(manager.outstanding[record.group_slot], -1)
```

The submitting thread's previously inspected help path passes true as the second callback argument and uses the same before/after counter order. These boolean values are established at the call boundaries. Their meaning for every possible callback is not inferred here.

The producer initializes both counters for the queued workers. It executes its own callback inline and can help consume queue records while waiting. The final selected-group wait observes the outstanding counter, not just the not-started counter. Normal callback return therefore precedes the consumer's matching decrement.

This closes the arithmetic join for this consumer branch. A source scan found no aligned direct call to the consumer in the bounded search, so its concrete thread-entry registration was not established by this follow-up. The shared record kind, queue and counter accesses support identifying its local consumer role; they do not prove execution by a particular live thread.

## Queue claims are another separate boundary

The consumer first reads queue claim and published-write cursors. It accepts a 24-byte record only when the unsigned available-byte distance is at least 24 and no greater than the 1,024-byte ring capacity. A compare/exchange reserves the read span; the copy may split across the ring end. It then advances the ordered read-release cursor before decoding the record kind.

```text
claim_record(queue):
    repeat:
        start = atomic_read(queue.claim_cursor)
        available = u32(atomic_read(queue.published_write_cursor) - start)
        if available < record_size or available > ring_capacity:
            return no_record
    until compare_exchange(queue.claim_cursor, start, start + record_size)

    record = copy_record_with_ring_wrap(start)
    wait_until_compare_exchange(queue.release_cursor, start,
                                start + record_size)
    return record
```

The released queue storage can be reused before the callback completes because the callback record has already been copied to local storage. Queue consumption, callback start and callback completion are distinct events.

A second recognized record kind decrements both group counters and returns from this consumer routine without calling the normal callback. Its producer and higher-level meaning were not traced. It must not be renamed cancellation or shutdown solely from this local branch. A completion counter can therefore include more than normal callback returns, depending on which records were submitted.

## Remaining conditions

- The consumer waits through a protected helper before reading records. Notification/wakeup semantics remain unresolved.
- Another protected helper appears in its empty-queue handling path. Its behavior is not supplied by this decoding.
- The normal callback-return branch was inspected, not an exception-unwind protocol. No completion guarantee after a thrown or nonreturning callback is established.
- Group slots and counters recycle. They are not monotonically increasing input or world generations.
- The queue producer's reservation/publication protocol, concrete consumer registration, and object teardown must still be joined before claiming full concurrent lifetime safety.
- This is the backend's selected callback group. It is not proof that all engine jobs, animation work, rendering or new submissions have stopped.

## Evidence

The consumer was decoded within its 453-byte exception-table range. Linear decoding encounters protected/opaque bytes on an empty-queue path; the normal callback branch was decoded separately from a direct branch target established earlier in that same function. That restart is explicit, not a claim that every byte in the range is ordinary code.

Consumer range SHA-256: `c215aa01f85a5336f411c3ead3474c316cc7dc93f2ecade44cb7997e0c136e0e`.

Studied image SHA-256: `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.

The counter displacements, record construction and normal callback call sites were checked directly against the local image. No image bytes, raw instructions or process data are distributed in this document. No game was launched or attached to. See the [scheduler contract](research/scheduler.md) for the broader conditional world-step and publication relationships.
