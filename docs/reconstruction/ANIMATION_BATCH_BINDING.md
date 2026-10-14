# Animation-time batch binding

The constructor now closes the worker-selection gap in [component dispatch](ANIMATION_COMPONENT_DISPATCH.md). The configured animation-time job uses the concrete reverse visitor implemented by `engine.animation_batch`, with no receiver-pointer adjustment.

## Established static chain

```text
scheduler owner constructor
    -> embedded job with concrete virtual table
    -> range worker
    -> concrete batch visitor
    -> configured receiver dispatcher
    -> receiver virtual slot 0x270
    -> KinoComponent time-update thunk, when the receiver is KinoComponent
    -> component's stored interface update slot
    -> recovered outer animation update
```

The owner constructor initializes the embedded job and installs its final table. Setup later installs the slot-0x270 receiver dispatcher in that job's callback field and assigns the animation-time labels. The final table's worker invokes its visitor slot after claiming a receiver range. That slot selects the inspected visitor, rather than the earlier generic adjusted-receiver candidate.

This is a static dispatch chain conditional on receiver identity. It does not prove that a current player is in a live job batch, or establish dependency ordering relative to physics/input jobs.

## Selected visitor

```text
visit_batch(job, pointer_span, count):
    base = pointer_span.base
    callback = job.callback
    for index from count - 1 down to 0:
        receiver = base[index]
        callback(receiver)
```

The callback is captured once before the loop. Changing the stored job callback during an invocation does not change later calls in that same batch. The pointer-array base is also captured once, but each receiver entry is read when its iteration executes. Replacing an unvisited entry can therefore affect a later call. This describes the instructions; it does not authorize concurrent mutation of native storage.

No adjustment is added to the receiver pointer, and this visitor does not supply the separate context argument read by the previously considered generic visitor. That earlier candidate must not be used as this job's ABI. Thread context is established separately through the surrounding job callbacks.

Reverse visitation is local to one claimed range. It does not establish a global order across worker threads or show that count reaching zero means all callbacks have returned. The [existing range-claim evidence](SCHEDULER_BATCH_EPOCH.md) keeps that distinction explicit.

## Portable API

`visit_animation_batch(job, receivers, count=None)` accepts a job dictionary containing a callback and a caller-owned sequence of receivers. It captures the callback, reads entries during iteration and returns visited indices as diagnostics. Pointer arithmetic, ownership and native thread state are replaced by explicit Python references. Counts outside the supplied sequence or nonnegative signed-int32 range are rejected rather than emulating invalid native accesses.

```python
from engine.animation_batch import visit_animation_batch

seen = []
job = {'callback': seen.append}
indices = visit_animation_batch(job, ['first', 'second', 'third'])
assert indices == [2, 1, 0]
assert seen == ['third', 'second', 'first']
```

The API does not choose job membership or invoke the full component update automatically. Callback exceptions propagate and stop the portable loop; native exception unwinding is not reconstructed.

## Validation

The original selected visitor and original slot-0x270 dispatcher passed 36 isolated cases using synthetic receivers with returning method stubs. Counts zero through eight were combined with callback replacement and unvisited receiver-entry replacement. Results matched the portable loop, including callback capture. See the [receipt](animation_batch_validation.json). Four repository tests cover local order, empty spans, callback retention, late receiver reads and invalid inputs.

The constructor/setup/table chain and range-worker visitor call were statically inspected. Original range claiming, thread context, real component execution and concurrent mutation were not emulated in this check.

## Remaining boundary

The next useful joins are the gather/membership writer for this exact job, its dependency edges, and the producers of the world-clock fields consumed by KinoComponent. These would connect the static route to who runs, when, and with which interval. The selected visitor and receiver adjustment are no longer open questions for this constructor/setup pair.

Evidence anchors: owner constructor `1408aff20`, embedded job offset `0x3af0`, final table `141ec7f38`, worker slot `0x40` -> `1408c7800`, visitor slot `0x80` -> `1408f2b60`, setup `140905dd0`, receiver callback `1409d44c0`, callback field job+`0x1c0`. The earlier adjusted-receiver candidate was `1408f2b00`; it is not selected by this table. Original code and receiver payloads remain private.
