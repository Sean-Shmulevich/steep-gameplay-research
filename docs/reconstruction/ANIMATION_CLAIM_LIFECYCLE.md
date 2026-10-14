# Animation count consumption and callback completion

The animation-time job's active count is its remaining-to-claim counter. Its selected range worker atomically reduces that same field before entering context or invoking the receiver visitor. This supplies an ordinary consumption path to zero without requiring a separate unconditional reset after every batch.

This joins the animation [registry copy](ANIMATION_MEMBERSHIP_COPY.md) to the already recovered [range arithmetic](SCHEDULER_BATCH_EPOCH.md) and [queue-change yield rule](RANGE_WORKER_YIELD.md). The identity follows from the animation constructor's selected table and the worker's field accesses, not from the similarity of two counters.

## Order inside one invocation

```text
range = claim_and_reduce_remaining()
if no range:
    return
captured_change = queue.change_counter
enter_optional_context()
repeat:
    visit_animation_range(range)
    if queue.change_counter != captured_change:
        break
    if early_exit_enabled and queue.front_counter != 0:
        break
    range = claim_and_reduce_remaining()
    if no range:
        break
leave_optional_context()
```

The selected visitor captures its receiver callback separately for each range and visits entries in reverse within that range. A yield signal observed during a receiver call takes effect after the entire claimed range returns. It does not cancel the remaining entries of that range.

With two receivers and a chunk size of two at tail threshold zero, claiming writes remaining count zero. Context entry and both receiver calls then execute while that field is already zero. This is direct evidence that the field cannot prove callback completion.

## Empty gather revisited

| Prior state | Effect of the next empty source copy |
| --- | --- |
| All ranges claimed and callbacks returned | Retains zero; no new work available |
| All ranges claimed but a callback is still active | Retains zero; execution may still be in progress |
| Worker yielded with unclaimed entries | Retains positive remaining count and existing pointers |

This resolves the ordinary clearing question raised by the membership-copy pass. It does not prove which cross-request protocol excludes copying or reallocating storage while an earlier claimed range still refers to it. A positive remainder after yielding may be resumed by another invocation; the outer scheduler decides that lifecycle.

## Explicit claim API

`AnimationMembership.claim(chunk_size=1, tail_threshold=0)` now applies the recovered claim arithmetic and reduces `count` before returning an `AnimationSpan`. The span retains the storage reference and reads its entries when accessed. It is compatible with `visit_animation_batch`.

```python
from engine.animation_membership import AnimationMembership
from engine.animation_batch import visit_animation_batch

state = AnimationMembership(['first', 'second'], 2)
span = state.claim(2, 0)
assert state.count == 0
assert state.claim() is None

# The receivers have not run yet, despite count being zero.
seen = []
visit_animation_batch({'callback': seen.append}, span)
assert seen == ['second', 'first']
state.copy_registry([])
assert state.count == 0
```

The claim API requires exclusive serial ownership. It models a successful compare/exchange, not contention or a native atomic snapshot. The returned span is not a completion token. Callers must keep storage stable until all claimed spans finish; Python retaining an old list after replacement does not establish native lifetime safety. The independent mixed scheduler has separate dispatch/range tokens and completion accounting for its own execution model.

## Validation

The original worker, selected table, visitor and receiver dispatcher passed 576 isolated cases against portable composition. Cases combine counts zero through eight, chunks one through four, tail thresholds zero/one/three/five, and four queue modes: unchanged, changed during the first receiver call, nonzero front counter with early exit enabled, and the same counter with early exit disabled.

Synthetic receiver/context callbacks return normally. Checks compare every context-entry, receiver and context-exit event, including remaining count at each event, final count and queue counters. The native compare/exchange instructions execute without competing threads. The check confirms that yield waits for the current range and can leave a positive remainder. See the [receipt](animation_worker_validation.json).

Four additional repository tests cover zero-before-callback behavior, late reads through a captured span, full/partial claim followed by an empty gather, and invalid settings leaving state unchanged. No live game state or native scheduler completion protocol was exercised.

Evidence anchors: animation table `141ec7f38`, worker `1408c7800`, visitor `1408f2b60`, dispatcher `1409d44c0`; pointer array job+`0x198`, remaining job+`0x1a0`, chunk/tail job+`0x1b0`/`0x1b4`, early-exit byte job+`0x1b8`. Claim updates at `1408c7854` and `1408c7922` target the same field written by the animation gather at owner+`0x3c90`, where job=owner+`0x3af0`.

The [stage-dependency follow-up](ANIMATION_STAGE_DEPENDENCIES.md) now joins this animation job to the downstream action gather and the previously inspected ordinary completion/rearm route. Remaining count zero alone must not be used as a safe pause, buffer-reuse or next-request signal. Live identity and exceptional-mode coverage remain separate requirements.
