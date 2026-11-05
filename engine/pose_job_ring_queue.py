"""Job dispatcher ring queue (0x18b7710 push, pop inside 0x18b7f80) and its users.

Evidence (static + native sequential validation, see
native/snow_host/pose_job_ring_queue_validation.json):
  * 0x18b7710 is the queue push; the same body is inlined in the shutdown chunk
    0x18b797e (record built on the stack, tag 0x1de3f0c9) and the pop body is inlined
    in the ordinary worker loop 0x18b7f80. The dispatcher chunk 0x18b7d03 calls
    0x18b7710 with the 24-byte record (tag 0x1de3f0c7, slot, callback, argument) that
    engine.pose_dispatch passes to its enqueue service.
  * The queue lives at dispatcher+0x218: 0x400 ring bytes followed by four u32
    counters (offsets relative to the queue): +0x400 read claim, +0x404 read
    published, +0x408 write claim, +0x40c write published. Counters are free running
    and compared with wrapping 32-bit arithmetic; a record at counter value c occupies
    ring bytes (c & 0x3ff) onward and splits across the end of the ring.
  * The ring is memcpy (0x141c6afb0) based; here it is plain byte copying.

Recovered, natively validated: the sequential result of push, pop, the record
consumer in the worker loop and the exit-record publication loop. The step
machines below expose every atomic operation as a separately named step so a
caller can interleave them. THE INTERLEAVING of those steps is authored
exploration; it is not native evidence (see engine.pose_job_ring_model_check).

Authored guards (not native): push on a full ring or behind an unpublished writer spins
forever natively; push_record raises RingStalled after spin_limit iterations. The
worker loop rejects slot >= 32 instead of reading outside the dispatcher.
Offsets are evidence anchors, not portable API fields.
"""
import struct

RING_SIZE = 0x400
RECORD_SIZE = 0x18
QUEUE_OFFSET = 0x218            # inside the dispatcher object
READ_CLAIM, READ_PUBLISHED, WRITE_CLAIM, WRITE_PUBLISHED = 0x400, 0x404, 0x408, 0x40c
QUEUE_BYTES = 0x410
UNCLAIMED = 0x628               # dispatcher u32[32]: callbacks not yet claimed
UNFINISHED = 0x6a8              # dispatcher u32[32]: callbacks not yet finished
HANDLES = 0x118                 # dispatcher u64[]: worker wait handles
TAG_CALL = 0x1de3f0c7
TAG_EXIT = 0x1de3f0c9
M32 = 0xffffffff


class RingStalled(RuntimeError):
    """Authored guard: the native routine would spin here."""


class WorkerHalt(Exception):
    """Raised by supplied services to stop a worker loop under test."""


def pack_record(tag, slot, callback, token):
    return struct.pack('<IIQQ', tag, slot, callback, token)


def unpack_record(raw):
    return struct.unpack('<IIQQ', bytes(raw))


class _Atomics:
    """Shared-memory view; each method is one atomic instruction."""

    def __init__(self, buf, base, ring):
        self.buf, self.base, self.ring = buf, base, ring

    def addr(self, which):
        return self.base + self.ring + which - RING_SIZE

    def read(self, which):          # lock xadd [x], 0
        return struct.unpack_from('<I', self.buf, self.addr(which))[0]

    def cas(self, which, expected, desired):   # lock cmpxchg; returns prior value
        a = self.addr(which)
        old = struct.unpack_from('<I', self.buf, a)[0]
        if old == expected & M32:
            struct.pack_into('<I', self.buf, a, desired & M32)
        return old


class _Op:
    pc = None
    done = False
    result = None

    def key(self):
        return (self.pc, self.a, self.b, self.chunks)

    def clone(self):
        c = object.__new__(type(self))
        c.__dict__.update(self.__dict__)
        return c

    def _split(self, index):
        off = index & (self.ring - 1)
        n1 = min(self.ring - off, RECORD_SIZE)
        self.chunks = (off, n1)

    def _copy_in(self, buf, head):
        off, n1 = self.chunks
        o = self.base
        if head:
            buf[o + off:o + off + n1] = self.record[:n1]
        else:
            buf[o:o + RECORD_SIZE - n1] = self.record[n1:]

    def _copy_out(self, buf, head):
        off, n1 = self.chunks
        o = self.base
        if head:
            self.out = bytes(buf[o + off:o + off + n1])
        else:
            self.out += bytes(buf[o:o + RECORD_SIZE - n1])


class PushOp(_Op):
    """Push of one 24-byte record. Atomic steps in native order:
    load_read_published, load_write_claim, claim_cas, copy_head, [copy_tail],
    publish_cas (repeated until it succeeds). Retries restart at
    load_read_published."""

    def __init__(self, record, *, base=0, ring=RING_SIZE):
        if len(record) != RECORD_SIZE:
            raise ValueError('records are 24 bytes')
        if ring & (ring - 1) or ring < RECORD_SIZE:
            raise ValueError('ring size must be a power of two >= 24')
        self.record, self.base, self.ring = bytes(record), base, ring
        self.pc, self.a, self.b, self.chunks = 'load_read_published', 0, 0, (0, 0)

    def step(self, buf):
        at = _Atomics(buf, self.base, self.ring)
        name = self.pc
        if name == 'load_read_published':
            self.a = at.read(READ_PUBLISHED)
            self.pc = 'load_write_claim'
        elif name == 'load_write_claim':
            self.b = at.read(WRITE_CLAIM)
            used = (self.b - self.a) & M32
            free = (self.a - self.b + self.ring) & M32
            # native: ja (used > ring) retry; jb (free < 24) retry
            self.pc = 'load_read_published' if used > self.ring or free < RECORD_SIZE else 'claim_cas'
        elif name == 'claim_cas':
            if at.cas(WRITE_CLAIM, self.b, self.b + RECORD_SIZE) != self.b:
                self.pc = 'load_read_published'
            else:
                self._split(self.b)
                self.pc = 'copy_head'
        elif name == 'copy_head':
            self._copy_in(buf, True)
            self.pc = 'copy_tail' if self.chunks[1] < RECORD_SIZE else 'publish_cas'
        elif name == 'copy_tail':
            self._copy_in(buf, False)
            self.pc = 'publish_cas'
        elif name == 'publish_cas':
            # publication is strictly in claim order: wait for the previous writer
            if at.cas(WRITE_PUBLISHED, self.b, self.b + RECORD_SIZE) == self.b:
                self.pc, self.done = 'done', True
        else:
            raise RuntimeError('push already complete')
        return name

    def claim_index(self):
        return self.b


class PopOp(_Op):
    """Pop of one record. Steps: load_read_claim, load_write_published,
    claim_cas, copy_head, [copy_tail], publish_cas (spins). An empty or
    inconsistent snapshot completes with result None (no retry, unlike push)."""

    def __init__(self, *, base=0, ring=RING_SIZE):
        self.base, self.ring = base, ring
        self.pc, self.a, self.b, self.chunks, self.out = 'load_read_claim', 0, 0, (0, 0), b''

    def step(self, buf):
        at = _Atomics(buf, self.base, self.ring)
        name = self.pc
        if name == 'load_read_claim':
            self.a = at.read(READ_CLAIM)
            self.pc = 'load_write_published'
        elif name == 'load_write_published':
            self.b = at.read(WRITE_PUBLISHED)
            avail = (self.b - self.a) & M32
            if avail > self.ring or avail < RECORD_SIZE:
                self.pc, self.done, self.result = 'done', True, None
            else:
                self.pc = 'claim_cas'
        elif name == 'claim_cas':
            if at.cas(READ_CLAIM, self.a, self.a + RECORD_SIZE) != self.a:
                self.pc = 'load_read_claim'
            else:
                self._split(self.a)
                self.pc = 'copy_head'
        elif name == 'copy_head':
            self._copy_out(buf, True)
            self.pc = 'copy_tail' if self.chunks[1] < RECORD_SIZE else 'publish_cas'
        elif name == 'copy_tail':
            self._copy_out(buf, False)
            self.pc = 'publish_cas'
        elif name == 'publish_cas':
            if at.cas(READ_PUBLISHED, self.a, self.a + RECORD_SIZE) == self.a:
                self.pc, self.done, self.result = 'done', True, self.out
        else:
            raise RuntimeError('pop already complete')
        return name

    def key(self):
        return (self.pc, self.a, self.b, self.chunks, self.out)

    def claim_index(self):
        return self.a


def _run(op, buf, spin_limit):
    for _ in range(spin_limit):
        if op.done:
            return op.result
        op.step(buf)
    if op.done:
        return op.result
    raise RingStalled(op.pc)


def push_record(buf, record, *, base=0, ring=RING_SIZE, spin_limit=10000):
    """Sequential 0x18b7710(queue, record)."""
    _run(PushOp(record, base=base, ring=ring), buf, spin_limit)


def pop_record(buf, *, base=0, ring=RING_SIZE, spin_limit=10000):
    """Sequential pop: 24 record bytes, or None when fewer than 24 are published."""
    return _run(PopOp(base=base, ring=ring), buf, spin_limit)


# --- users of the queue -----------------------------------------------------

def _add(dispatcher, offset, delta):
    old = struct.unpack_from('<I', dispatcher, offset)[0]
    struct.pack_into('<I', dispatcher, offset, (old + delta) & M32)
    return old


def _slot(slot):
    if slot >= 32:
        raise ValueError('slot outside dispatcher counter arrays (native reads out of range)')
    return slot * 4


def handle_job_record(dispatcher, raw, invoke):
    """Record consumer of the worker loop (0x18b7f80 after the pop).

    TAG_CALL: unclaimed[slot] -= 1; invoke(callback, token, False); unfinished[slot] -= 1.
    TAG_EXIT: unclaimed[slot] -= 1 and unfinished[slot] -= 1, then the loop returns.
    Any other tag only reaches the re-read. Returns (outcome, skip_wait) where skip_wait
    is true when unclaimed[slot] is nonzero afterwards (loop pops again without waiting).
    """
    tag, slot, callback, token = unpack_record(raw)
    off = _slot(slot)
    if tag == TAG_CALL:
        _add(dispatcher, UNCLAIMED + off, -1)
        invoke(callback, token, False)
        _add(dispatcher, UNFINISHED + off, -1)
        outcome = 'call'
    elif tag == TAG_EXIT:
        _add(dispatcher, UNCLAIMED + off, -1)
        _add(dispatcher, UNFINISHED + off, -1)
        return 'exit', False
    else:
        outcome = 'ignored'
    return outcome, struct.unpack_from('<I', dispatcher, UNCLAIMED + off)[0] != 0


def run_job_worker(dispatcher, worker_index, *, wait, invoke, fault):
    """Ordinary worker loop 0x18b7f80(dispatcher, worker_index).

    wait(handle): the opaque event wait on the worker's handle (dispatcher+0x118+8*i);
    the native call also passes the queue address. invoke(callback, token, caller_flag).
    On an empty pop the loop scans unclaimed[0..31]; the first nonzero entry calls an
    opaque non-returning routine (0x143e20621), modeled as fault(index, value); if
    every entry is zero it waits again. Returns when an exit record is consumed.
    """
    handle = struct.unpack_from('<Q', dispatcher, HANDLES + 8 * worker_index)[0]
    skip_wait = False
    while True:
        if not skip_wait:
            wait(handle)
        skip_wait = False
        raw = pop_record(dispatcher, base=QUEUE_OFFSET)
        if raw is None:
            for i in range(32):
                value = struct.unpack_from('<I', dispatcher, UNCLAIMED + 4 * i)[0]
                if value:
                    fault(i, value)
                    raise WorkerHalt('opaque routine returned')
            continue
        outcome, skip_wait = handle_job_record(dispatcher, raw, invoke)
        if outcome == 'exit':
            return


def publish_exit_records(dispatcher, notify):
    """Shutdown 0x18b7940 (loop chunk 0x18b797e) up to its first opaque wait.

    Sets unclaimed[0] = unfinished[0] = workers - 1 (workers = u32 at +0xc), then for
    index 1..workers-1 pushes (TAG_EXIT, 0, 0, 0) and calls notify(handle[index]).
    Exit records name slot 0, so consuming one decrements slot 0 counters. Later
    operations of the routine (waits, handle teardown) are not modeled.
    """
    workers = struct.unpack_from('<I', dispatcher, 0xc)[0]
    struct.pack_into('<I', dispatcher, UNCLAIMED, (workers - 1) & M32)
    struct.pack_into('<I', dispatcher, UNFINISHED, (workers - 1) & M32)
    for index in range(1, workers):
        push_record(dispatcher, pack_record(TAG_EXIT, 0, 0, 0), base=QUEUE_OFFSET)
        notify(struct.unpack_from('<Q', dispatcher, HANDLES + 8 * index)[0])
