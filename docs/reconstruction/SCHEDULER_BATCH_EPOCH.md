# Motion-batch count: consumed on claim, not cleared after the callback

The [membership follow-up](SCHEDULER_MEMBERSHIP_FOLLOWUP.md) established that an empty registration source leaves the gathered destination untouched. This pass identifies an ordinary path that makes this safe: the candidate batch's range worker atomically reduces that same destination count as it claims ranges. A fully claimed prior batch therefore leaves a zero count even though old receiver pointers remain in allocated storage.

This is a conditional explanation, not a proof that every new request starts empty. The worker has early-exit gates, and count zero precedes completion of the last claimed callback. The graph's cross-request exclusion and exceptional reset/resume policy remain separate obligations.

No game was launched or attached to. This document summarizes static code and retained exports, without publishing executable addresses or raw code payloads.

## Identity join

The action-graph constructor initializes the `PreBeforeSimulation` job's pointer array and active count/capacity pair to zero. It installs the same concrete range-job table identified by the scheduler audit. That table selects the inspected range worker and reverse-order receiver visitor.

The gather destination is the job's array header. Its active count is also the range worker's atomic claim counter. These are the same storage location under the established job-base/graph-base relation, not two counters that merely happen to agree. The capacity field is separate. The constructor's zero store is initialization, not evidence of a per-request reset.

The following operations are therefore joined:

```text
construct_job():
    storage = null
    remaining = 0
    capacity = 0
    chunk_size = 1
    tail_threshold = 0
    early_exit_gate = false
    install_range_worker_and_receiver_visitor()

nonempty_gather(source):
    prepare_storage_and_clear_active_count()
    copy_receiver_pointers(source)
    remaining = source.count

worker_claim():
    atomically_reduce(remaining)
    invoke_claimed_receiver_range()
```

The named callback is installed by the separate graph setup documented in the [scheduler input audit](SCHEDULER_INPUT_AUDIT.md). Constructor and setup are not collapsed into one original routine here.

## Actual range-claim arithmetic

For ordinary valid settings (`chunk_size > 0`, `tail_threshold >= 0`, nonnegative count), each claim uses this compare/exchange loop:

```text
claim(job):
    old = job.remaining
    repeat:
        if old > job.tail_threshold:
            if old >= job.tail_threshold + job.chunk_size:
                proposed = old - job.chunk_size
            else:
                proposed = job.tail_threshold
        else:
            if old <= 0:
                return NO_RANGE
            proposed = old - 1

        success, observed = compare_exchange(job.remaining, old, proposed)
        if success:
            start = job.storage + proposed * pointer_size
            count = old - proposed
            return start, count
        old = observed
```

The successful atomic store happens **before** the context-entry callback and receiver visitor. The visitor reads each receiver pointer in reverse order within its claimed range. Concurrent claimers may interleave; the local reverse loop is not a global receiver execution order.

This algorithm consumes the tail of the active array. With count five, chunk two and tail threshold four, the first claim changes five to four and owns one receiver; the remaining four are claimed individually. With count ten under the same settings, successive claims can reduce ten to eight, six and four, then switch to single entries. The worker does not compact, erase or zero the claimed pointer slots.

The job's chunk-setting method clamps a requested chunk below one up to one, then sets the tail threshold to twice the selected chunk for the finite ordinary branch. The constructor's initial chunk-one/tail-zero setting is distinct. Signed overflow and sentinel settings are outside the ordinary examples above.

## Where a worker stops

After its first successful claim, the worker captures a shared comparison value, optionally invokes a context-entry callback, then visits the range. After each visited range it can stop taking additional work if:

- that shared comparison value has changed; or
- the job's early-exit flag is set and another shared value is nonzero.

The meanings of those shared values are not assigned as frame number, cancellation generation or pause state by this pass. Their tested comparisons are sufficient to show an exit path before the next claim.

If neither exit condition applies, the worker reloads chunk settings/count and tries another claim. Once there is no positive range, it reaches the context-exit path. The job's local empty predicate is simply `remaining <= 0`; it does not inspect in-flight ranges or callbacks.

```text
worker(job):
    range = claim(job)
    if no_valid_positive_range(range):
        return

    comparison_value = shared_comparison_value
    run_optional_context_entry()
    repeat:
        visit_range(range)
        if shared_comparison_value != comparison_value:
            break
        if job.early_exit_gate and shared_exit_value != 0:
            break
        range = claim(job)
        if no_valid_positive_range(range):
            break
    run_optional_context_exit()
```

This describes the inspected worker, not the complete scheduler's decision to resubmit, help, finalize or stop the job. Other workers may already have claimed the rest of the array when one worker exits.

## Consequences for an empty gather

Four states that previously looked similar now have distinct meanings:

| State before a new empty gather | What the local helper preserves | Consequence supported by these routines |
| --- | --- | --- |
| Freshly constructed job | Null array, zero count | No range is available |
| Prior batch fully claimed and all callbacks returned | Allocated old pointers, zero count | Old pointer bytes are inactive; no range is available |
| Prior batch fully claimed, final callback still running | Allocated old pointers, zero count | No *new* range is available; prior execution is still possible |
| A worker exited early while some receivers remain unclaimed | Positive remaining count and old pointers | Empty gather alone does not invalidate those remaining receivers |

The last case is not evidence that stale receivers actually execute in normal gameplay. The outer scheduler may prevent that gather, resume the previous work, or reset the job elsewhere. It is the exact case for which a cross-request protocol is still needed.

Count zero is therefore neither a destructor safety signal nor a request-generation marker. Capturing old pointers after count reaches zero does not establish current membership. Conversely, a positive count does not identify which request supplied it without a separate epoch association.

## What this closes and what remains

This closes an ordinary **consumption-based clearing path** for the candidate batch. It corrects the stronger suggestion that a dedicated unconditional count reset must necessarily exist before every gather: after complete claiming, no such reset is required to make an empty source yield no new ranges.

It does not locate an unconditional next-request reset of this array. It also does not establish that root invocation waits for all prior range callbacks before the builder can reallocate or replace the array. That exclusion is essential: a worker's range points directly into the gathered array, and rebuilding that array could otherwise invalidate its captured storage. This is an unresolved lifecycle gate, not a claim that the original game lacks protection.

Next closure should join the named graph request's completion/rearm path to the following gather, covering both fully consumed and early-exit cases. Evidence should identify which pending/running ownership guarantees prevent rebuilding while any claimed range still uses the old buffer. A global integer with no proven writer/consumer meaning cannot substitute for that join.

For the independent engine, explicit per-request immutable arrays, a remaining-to-claim count and a separate in-flight/completion count make these distinctions inspectable. Such an API is our design. The recovered arithmetic alone does not promise those fields or guarantees in the original engine.

## Verification

All 107 exported instruction spans in the selected range-worker export matched the analyzed image byte-for-byte. The contiguous worker span's SHA-256 is `cf6f33ee90c3ebc49a4bcde7d3580eba7456db718b9eaeab84c91c06760e2230`. The constructor's job-base calculation, zero initialization and concrete table store were inspected, as were the table's worker/visitor bindings, its empty predicate and the chunk setter.

The analyzed image SHA-256 is `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. This verifies local static branches and owner-relative fields. It is not a live epoch trace or proof of exclusive caller coverage.
