"""Recovered kind-3 callback publication and counted-ring consumption.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, callback command producer and ABI.
This serial model uses owned descriptor bytes and supplied dispatch callbacks.
It does not retain native context objects, model native reference holders, lock
queues, register code, or authorize original-game submission.
"""
import struct


def callback_arguments(record, *, record_identity=0):
    """Describe kind 3/4 Win64 arguments without executing an address.

    record is a supplied 104-byte image. identity is an abstract base token;
    returned storage_offset locates the copied callable wrapper within it.
    Kind 3 establishes two arguments; kind 4 additionally establishes payload.
    """
    if not isinstance(record, bytes) or len(record) != 104:
        raise ValueError('104-byte supplied record required')
    kind = struct.unpack_from('<I', record)[0]
    if kind not in (3, 4):
        raise ValueError('only callback kinds 3 and 4 are decoded here')
    offset = 24 if kind == 3 else 56
    context, target = struct.unpack_from('<QQ', record, offset + 16)
    result = dict(kind=kind, record_identity=record_identity, storage_offset=offset,
                  context=context & ~3, target=target)
    if kind == 4:
        result['payload'] = struct.unpack_from('<Q', record, 88)[0]
    return result


def submit_callback(queue, descriptor, *, capacity, deferred):
    """Model the producer's ordinary ring branch, excluding alternate staging.

    queue is a caller-owned list of 32-byte descriptors. Returns an observation,
    not a recovered native success code. Full admission still increments deferred.
    The context/invoker words are copied without retaining their pointees.
    """
    if not isinstance(descriptor, bytes) or len(descriptor) != 32:
        raise ValueError('32-byte descriptor required')
    if type(capacity) is not int or not 1 <= capacity <= 0x7fffffff or len(queue) > capacity:
        raise ValueError('valid ring capacity required')
    if type(deferred) is not int or not 0 <= deferred <= 0xffffffff:
        raise ValueError('uint32 deferred counter required')
    inserted = len(queue) < capacity
    if inserted:
        queue.append(descriptor)
    return dict(inserted=inserted, deferred=(deferred + 1) & 0xffffffff)


def drain_counted_callbacks(queue, *, active, dispatch, max_dispatches=4096):
    """Replay service A's budget and retained-record behavior for kind 3 only.

    Caller supplies active after the native-style preparation transfer and owns
    serialization. A popped descriptor remains cached for exhausted-ring attempts.
    Native active is exchanged to zero before processing; returned active mirrors
    normal completion. An initially empty positive-budget path has no valid kind-3
    descriptor and is refused here, not invented as a valid native no-op.
    """
    if type(active) is not int or not 0 <= active <= 0xffffffff:
        raise ValueError('uint32 active counter required')
    if type(max_dispatches) is not int or max_dispatches < 0:
        raise ValueError('nonnegative authored dispatch limit required')
    budget = active if active < 0x80000000 else 0
    if budget > max_dispatches:
        raise ValueError('authored dispatch limit exceeded')
    cached = None
    popped = 0
    for _ in range(budget):
        if queue:
            cached = queue.pop(0)
            if not isinstance(cached, bytes) or len(cached) != 32:
                raise ValueError('32-byte descriptor required')
            popped += 1
        if cached is None:
            raise ValueError('no decoded callback for initially empty positive budget')
        dispatch(cached)
    return dict(active=0, dispatched=budget, popped=popped,
                repeated_cached=budget-popped, native_lifetime_proved=False)
