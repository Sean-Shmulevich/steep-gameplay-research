"""AUTHORED bounded model checker for the job ring queue. Not native evidence.

engine.pose_job_ring_queue recovers (and the Unicorn harness validates) only the
sequential behavior of each routine. This module takes its atomic-step machines
and explores EVERY interleaving of their atomic steps, assuming sequentially
consistent memory, a scaled-down ring (default 0x40 bytes, which still wraps and
splits records) and a fixed set of operations per thread. Distinct states are
memoized, so spin loops become cycles of the state graph. Properties are about
the reconstructed algorithm; no claim is made that the original engine, its memory
ordering on hardware, or its OS scheduling behave this way.

Thread programs:  ('push', [records])  pushes in order, each to completion
                  ('pop', n)            n consecutive pop attempts (empty returns None)
"""
from . import pose_job_ring_queue as Q

M32 = 0xffffffff


def make_record(tag):
    """Distinct, recognizable 24-byte record."""
    return bytes((tag * 37 + i * 11) & 0xff for i in range(24))


def initial_buffer(ring, start, preload):
    buf = bytearray(ring + 0x10)
    for i in range(4):
        buf[ring + 4 * i:ring + 4 * i + 4] = (start & M32).to_bytes(4, 'little')
    pre = []
    for n in range(preload):
        rec = make_record(0x80 + n)
        Q.push_record(buf, rec, ring=ring)
        pre.append(rec)
    return buf, pre


def _counters(buf, ring):
    return tuple(int.from_bytes(buf[ring + 4 * i:ring + 4 * i + 4], 'little') for i in range(4))


class _Thread:
    __slots__ = ('kind', 'items', 'idx', 'op', 'results', 'claims')

    def __init__(self, kind, items):
        self.kind, self.items, self.idx, self.op, self.results, self.claims = kind, items, 0, None, (), ()

    def clone(self):
        t = _Thread(self.kind, self.items)
        t.idx, t.results, t.claims = self.idx, self.results, self.claims
        t.op = self.op.clone() if self.op else None
        return t

    @property
    def done(self):
        n = len(self.items) if self.kind == 'push' else self.items
        return self.idx >= n and self.op is None

    def key(self):
        return (self.idx, self.op.key() if self.op else None, self.results, self.claims)

    def step(self, buf, ring):
        if self.op is None:
            self.op = (Q.PushOp(self.items[self.idx], ring=ring) if self.kind == 'push'
                       else Q.PopOp(ring=ring))
        name = self.op.step(buf)
        if self.op.done:
            if self.kind == 'push':
                self.claims += (self.op.claim_index(),)
            else:
                self.results += ((self.op.claim_index() if self.op.result else None, self.op.result),)
            self.op, self.idx = None, self.idx + 1
        return name


def _invariant(buf, ring):
    rc, rp, wc, wp = _counters(buf, ring)
    d = lambda x: (x - rp) & M32
    if not (d(rc) <= d(wp) <= d(wc) <= ring):
        return 'counter order broken rc=%x rp=%x wp=%x wc=%x' % (rc, rp, wp, wc)
    return None


def explore(programs, *, ring=0x40, start=0, preload=0, max_states=1000000):
    """Explore all interleavings. Returns a report dict; report['failures'] lists
    property violations (each with an example schedule)."""
    buf0, pre = initial_buffer(ring, start, preload)
    threads0 = [_Thread(k, v) for k, v in programs]
    pushed = {}
    for ti, (k, v) in enumerate(programs):
        if k == 'push':
            for n, r in enumerate(v):
                pushed[r] = (ti, n)
    for n, r in enumerate(pre):
        pushed[r] = (-1, n)
    seen = {}
    edges = []          # per state: list of successor ids
    terminal = []
    failures = {}
    order = []
    def key(buf, threads):
        return (buf, tuple(t.key() for t in threads))

    def fail(kind, detail, path):
        failures.setdefault(kind, dict(detail=detail, schedule=list(path)))

    k0 = key(bytes(buf0), threads0)
    seen[k0] = 0
    edges.append([])
    order.append(None)
    stack = [(0, bytes(buf0), threads0, ())]
    transitions = 0
    truncated = False
    while stack:
        sid, buf, threads, path = stack.pop()
        problem = _invariant(buf, ring)
        if problem:
            fail('counter_invariant', problem, path)
        live = [i for i, t in enumerate(threads) if not t.done]
        if not live:
            terminal.append(sid)
            _check_terminal(buf, threads, programs, pushed, pre, ring, start, path, fail)
            continue
        for i in live:
            nb = bytearray(buf)
            nt = [t.clone() for t in threads]
            name = nt[i].step(nb, ring)
            transitions += 1
            nb = bytes(nb)
            k = key(nb, nt)
            nid = seen.get(k)
            if nid is None:
                if len(seen) >= max_states:
                    truncated = True
                    continue
                nid = len(seen)
                seen[k] = nid
                edges.append([])
                stack.append((nid, nb, nt, path + ((i, name),)))
            edges[sid].append(nid)
    # blocked states: cannot reach any terminal state (spin forever)
    rev = [[] for _ in edges]
    for s, outs in enumerate(edges):
        for o in outs:
            rev[o].append(s)
    good = set(terminal)
    work = list(terminal)
    while work:
        s = work.pop()
        for p in rev[s]:
            if p not in good:
                good.add(p)
                work.append(p)
    return dict(states=len(seen), transitions=transitions, terminal_states=len(terminal),
                states_that_cannot_finish=len(seen) - len(good),
                initial_can_finish=0 in good, truncated=truncated, failures=failures)


def _check_terminal(buf, threads, programs, pushed, pre, ring, start, path, fail):
    rc, rp, wc, wp = _counters(buf, ring)
    popped = [(ti, c, rec) for ti, t in enumerate(threads) if t.kind == 'pop' for c, rec in t.results if rec is not None]
    recs = [r for _, _, r in popped]
    if len(set(recs)) != len(recs):
        fail('duplicate_delivery', 'a record was popped twice', path)
    for r in recs:
        if r not in pushed:
            fail('corrupt_record', 'popped bytes match no pushed record (torn or stale read)', path)
    popped = [p for p in popped if p[2] in pushed]
    recs = [p[2] for p in popped]
    if rc != rp or wc != wp:
        fail('counters_not_quiescent', (rc, rp, wc, wp), path)
    # records still in the ring at quiescence
    left = []
    n = min(((wp - rp) & M32) // Q.RECORD_SIZE, ring // Q.RECORD_SIZE + 1)   # corrupt counters must not loop
    for j in range(n):
        idx = (rp + j * Q.RECORD_SIZE) & M32
        off = idx & (ring - 1)
        raw = bytes(buf[(off + k) % ring] for k in range(Q.RECORD_SIZE))
        left.append(raw)
    expected = sorted(pushed)
    got = sorted(recs + left)
    if got != expected:
        missing = [pushed[r] for r in expected if r not in got]
        extra = len(got) - len(set(got))
        fail('lost_or_phantom_record', dict(missing=missing, extra=extra), path)
    # claim order: popping in claim-index order must give per-producer FIFO, and
    # (pop claims are exclusive) the popped claim indices are distinct
    by_claim = sorted(((c - start) & M32, r) for _, c, r in popped)   # modular order from the start counter
    last = {}
    for _, r in by_claim:
        prod, seq = pushed[r]
        if prod >= 0 and last.get(prod, -1) > seq:
            fail('producer_fifo', 'records of producer %d dequeued out of push order' % prod, path)
        last[prod] = max(last.get(prod, -1), seq)
    for ti, t in enumerate(threads):
        if t.kind == 'pop':
            seqs = {}
            for c, r in t.results:
                if r is None or r not in pushed:
                    continue
                prod, seq = pushed[r]
                if prod >= 0 and seqs.get(prod, -1) > seq:
                    fail('per_consumer_fifo', 'consumer %d saw producer %d out of order' % (ti, prod), path)
                seqs[prod] = max(seqs.get(prod, -1), seq)
    # global FIFO: claim index order equals push claim order
    claims = {}
    for ti, t in enumerate(threads):
        if t.kind == 'push':
            for n, c in enumerate(t.claims):
                claims[(ti, n)] = c
    for _, c, r in popped:
        pc = claims.get(pushed[r])
        if pc is not None and pc != c:
            fail('slot_mismatch', 'record popped from a different counter value than it was pushed at', path)
