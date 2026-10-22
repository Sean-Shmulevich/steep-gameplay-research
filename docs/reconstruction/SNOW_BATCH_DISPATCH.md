# Snow actor batch preparation and identity

`engine.snow_batch` models selector-zero record gathering and the requested claim
size. The caller supplies stable registration snapshots. Python tokens, frozen
records and tuple ownership are authored representations; no native allocation,
locking, scheduling or object lifetime is provided.

## Recovered preparation

The first actor batch in each world substep creates a local job and a record
array. Under the first registration lock, gathering copies the first registration
list to tag-zero records, then the alternate list to tag-two records. Each native
record occupies 16 bytes, with tag at the beginning and actor pointer at byte 8.
The copies preserve source order and duplicates. Gathering does not apply player
wrapper gates, sleep tests or sport filtering.

```text
records = []
under registration_lock:
    for actor in first_registration_list:
        records.append({tag: 0, actor: actor})
    for actor in alternate_registration_list:
        records.append({tag: 2, actor: actor})
requested_claim_size = max(unsigned_record_count // 20, 1)
if records are not empty:
    configure_local_job(records, requested_claim_size)
    bind_elapsed_and_consumed_pair()
    submit_local_job()
    wait_for_claim_exhaustion_and_dispatch_completion()
```

The division partitions records, not time. Alternate records participate in the
count even though the selected tag-two visitor is a no-op. The job's chunk setter
and range claim behavior are separate operations described in the
[claim audit](SCHEDULER_BATCH_EPOCH.md). This module returns the requested size;
it does not silently equate that with a full worker execution policy.

The [instruction receipt](../../native/snow_host/snow_gather_validation.json)
compares six selector-zero gather cases against the portable model, including
empty lists, alternate-only data, duplicates and mixed lists. Lock and capacity
helpers are intercepted with sufficient storage supplied. It also compares the
isolated original division/clamp instructions against every unsigned 16-bit count,
65,536 cases. This does not test allocator growth, malformed headers or concurrent
registration. The portable gather rejects combined counts beyond the packed
14-bit capacity as an authored validation boundary.

## Conditional uniqueness and completion

The retained registration research identifies an insertion helper that searches
for the exact pointer and returns without inserting when it is already present.
The matching removal helper swaps the final entry into the removed slot. Both
are called under the list lock on the inspected registration path. These findings
come from retained private membership research, whose hash is recorded in the
receipt. Its build-specific anchors are insertion `140999d70`, pointer search
`1406cd390`, removal `140766ab0`, and swap-last helper `14115b8d0`. This pass
reviewed that finding; it did not rerun those registration helpers. See also
[the input audit](SCHEDULER_INPUT_AUDIT.md).

Thus an initially valid unique list maintained exclusively by the inspected
insertion/removal helpers remains unique. Gathering copies that invariant; it
does not enforce it. Duplicate fixture inputs correctly yield duplicate records.
Do not strengthen this conditional invariant into proof that every writer uses
those helpers or that every live batch has unique membership.

The nonempty first-batch path forces the explicit wait. Its first phase waits for
claim exhaustion; its second waits for job lifecycle zero and nonpositive signed
outstanding dispatch accounting. These are distinct from the claim count alone.
The [outer-loop check](research/scheduler.md#outer-world-loop-instruction-check)
places backend integration after the batch returns. This supports serial
substeps while allowing different workers to run their actor callbacks.

## Identity needed in the next capture

The job and callable are constructed in the batch caller's stack frame. Their
addresses may be reused in later invocations. A pointer alone is therefore not a
batch generation, and the outer request counter alone cannot distinguish its
substeps. The existing actor capture has neither a batch invocation token nor a
direct native substep index.

A future recorder needs an authored invocation token at batch entry, associated
with the local job and copied callable before submission. Carry that association
to record dispatch; retire it only after the explicit wait returns. Record the
outer world invocation separately. This is a proposed observation protocol, not
an identified native generation field or an installed hook. Account for recursive
helper dispatch and reused stack addresses. A thread ID cannot replace this
association because actor work migrates among workers.

The next unresolved join is the execution-context job pointer available at the
actor visitor and its relation to that batch-local job. Once established, the
existing player callback can be attributed to a batch without inventing a
substep index from elapsed time or record ordering.
