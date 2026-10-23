"""Recovered primary command-queue quota and drain policy.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, primary command queue budget.
Queue ownership, record copies/reference counts and dispatch bodies are supplied
adapters. No native locks, game mutation or concurrent implementation is provided.
"""


def _word(value, bits):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(f'uint{bits} required')
    return value


def _signed32(value):
    value &= 0xffffffff
    return value if value < 0x80000000 else value - 0x100000000


def command_quota(count, capacity, *, snapshot_override=False):
    """Return the original uint32 quota, including signed wrapping arithmetic.

    For ordinary nonnegative small queue sizes: default 1; when more than 3/4
    full, count - floor(capacity/2). Override returns the sampled count instead.
    Sampling is under a queue lock natively; inputs here are caller snapshots.
    """
    _word(count, 32)
    _word(capacity, 32)
    if type(snapshot_override) is not bool:
        raise ValueError('boolean override required')
    quota = 1
    if _signed32(count * 4) > _signed32(capacity * 3):
        signed_capacity = _signed32(capacity)
        half = _signed32(capacity - (-1 if signed_capacity < 0 else 0)) >> 1
        quota = (count - half) & 0xffffffff
    return count if snapshot_override else quota


def drain_primary(*, quota, bypass_budget, take, process, ticks, frequency,
                  max_attempts=4096):
    """Run the recovered loop with caller-owned queue/clock adapters.

    take() returns (available: bool, record). It must copy/retain a record while
    holding its queue lock, then release that lock before returning. process()
    receives the retained record after that release. These adapter obligations
    are not enforced by this serial model. ticks() yields uint64 clock ticks.
    frequency is the supplied positive uint64 clock divisor.

    Budget is checked after processing; an individual command can exceed it.
    max_attempts is an authored protection against endless supplied producers.
    """
    _word(quota, 32)
    _word(frequency, 64)
    if not frequency or type(bypass_budget) is not bool:
        raise ValueError('positive frequency and boolean budget bypass required')
    if type(max_attempts) is not int or max_attempts < 1:
        raise ValueError('positive attempt budget required')
    started = _word(ticks(), 64)
    processed = attempts = 0
    elapsed_us = None
    while True:
        if attempts == max_attempts:
            raise RuntimeError('authored command attempt budget exhausted')
        available, record = take()
        if type(available) is not bool:
            raise ValueError('take must return boolean availability')
        attempts += 1
        keep_going = available
        if available:
            process(record)
            processed += 1
            if not bypass_budget:
                delta = (_word(ticks(), 64) - started) & 0xffffffffffffffff
                elapsed_us = ((delta * 1000000) & 0xffffffffffffffff) // frequency
                if elapsed_us > 10000:
                    keep_going = False
        quota = (quota - 1) & 0xffffffff
        if not keep_going or (not bypass_budget and quota == 0):
            break
    return dict(did_work=processed != 0, processed=processed, attempts=attempts,
                remaining_quota=quota, elapsed_us=elapsed_us,
                native_locking_proved=False)
