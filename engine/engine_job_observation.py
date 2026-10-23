"""Bounded read-only engine callback-job observation for one qualified image.

Evidence: SCHEDULER_DELEGATES.md. Caller verifies build and process identity and
provides a timed exact-read transport. No writes, callback invocation or lifetime
pinning. Output normalizes image pointers and omits raw heap addresses.
"""
import struct

IMAGE_SHA256 = '32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2'
OWNER_GLOBAL_RVA = 0x312cfe8
TABLE_RVA = 0x1e89618
METHODS = {0: 0x652c70, 0x40: 0x65b1e0, 0x58: 0x67adf0,
           0x60: 0x2aa0c0, 0x68: 0x11d1540, 0x70: 0x11d1670}
JOBS = {'root': 0x60, 'graphics': 0x218}
DELEGATES = {'before': 0xf0, 'after': 0x110, 'reservation': 0x150, 'main': 0x198}


def observe_engine_jobs(readv, *, image_base, image_size, verified_image_sha256):
    """Two guarded sequential sweeps: at most 16 ranges / 2086 bytes.

    `verified_image_sha256` is the caller's identity assertion, not a hash that
    this reader computes. The transport must enforce process identity/timeouts.
    Stable equal output does not prove atomicity, callback execution or unload
    safety. Unknown non-image callbacks are classified without exporting pointers.
    """
    if verified_image_sha256 != IMAGE_SHA256:
        raise ValueError('unsupported verified image')
    if (type(image_base) is not int or type(image_size) is not int or
            image_base < 0x10000 or image_size < OWNER_GLOBAL_RVA + 8 or
            image_base + image_size > 0x800000000000):
        raise ValueError('invalid image range')
    reads = total = 0
    def get(plan):
        nonlocal reads, total
        for address, size in plan:
            if not 0x10000 <= address <= 0x800000000000 - size:
                raise ValueError('invalid read address')
        reads += len(plan); total += sum(n for _, n in plan)
        blocks = list(readv(plan))
        if len(blocks) != len(plan) or any(type(b) is not bytes or len(b) != n
                                         for b, (_, n) in zip(blocks, plan)):
            raise ValueError('incomplete read')
        return blocks
    def q(block, offset=0):
        return struct.unpack_from('<Q', block, offset)[0]
    def pointer(value):
        if not value:
            return {'kind': 'null'}
        if image_base <= value < image_base + image_size:
            return {'kind': 'image', 'rva': value-image_base}
        return {'kind': 'outside_image'}
    def decode(block, owner, offset):
        if q(block) != image_base + TABLE_RVA:
            raise ValueError('job table mismatch')
        executions, outstanding, state, started, requested, holds = struct.unpack_from('<6I', block, 0x4c)
        signed_outstanding = outstanding if outstanding < 0x80000000 else outstanding - 0x100000000
        delegates = {}
        for name, at in DELEGATES.items():
            function, auxiliary, context, invoker = struct.unpack_from('<4Q', block, at)
            receiver = context & ~3
            delegates[name] = dict(function=pointer(function), invoker=pointer(invoker),
                context_tags=context & 3,
                receiver_relation=('null' if not receiver else 'owner' if receiver == owner
                                   else 'job' if receiver == owner+offset else 'other'),
                dispatch_policy='unconditional' if name == 'main' else 'optional',
                optional_eligible=None if name == 'main' else bool(function or receiver))
        usage = block[0x194] != 0
        return dict(table_rva=TABLE_RVA, executions=executions,
            outstanding_dispatches=signed_outstanding, state=state,
            started=started, requested=requested, holds=holds, usage=usage,
            local_teardown_would_wait=usage and (state != 0 or signed_outstanding > 0),
            delegates=delegates)
    samples = []; raw_snapshots = []; first_owner = None
    for _ in range(2):
        raw_owner, table = get([(image_base+OWNER_GLOBAL_RVA, 8), (image_base+TABLE_RVA, 128)])
        owner = q(raw_owner)
        if not 0x10000 <= owner <= 0x800000000000 - 0x3d0:
            raise ValueError('owner unavailable')
        if first_owner is not None and owner != first_owner:
            raise ValueError('owner changed between sweeps')
        first_owner = owner
        if any(q(table, slot) != image_base+rva for slot, rva in METHODS.items()):
            raise ValueError('job methods mismatch')
        blocks = get([(owner+0x58, 3)] + [(owner+offset, 0x1b8) for offset in JOBS.values()])
        result = dict(byte58=blocks[0][0], byte59=blocks[0][1], frame_service_selector=blocks[0][2],
                      jobs={name:decode(block, owner, offset)
                            for (name, offset), block in zip(JOBS.items(), blocks[1:])})
        end = get([(image_base+OWNER_GLOBAL_RVA, 8)] + [(owner+offset, 8) for offset in JOBS.values()])
        if q(end[0]) != owner or any(q(b) != image_base+TABLE_RVA for b in end[1:]):
            raise ValueError('owner or job identity changed during sweep')
        samples.append(result)
        raw_snapshots.append(tuple([raw_owner, table] + blocks + end))
    return dict(schema='engine-job-observation-v1', samples=samples,
                observations_equal=raw_snapshots[0] == raw_snapshots[1], reads=reads, bytes=total,
                atomic_snapshot=False, lifetime_pinned=False, callback_execution_proved=False,
                native_mutation_authorized=False)
