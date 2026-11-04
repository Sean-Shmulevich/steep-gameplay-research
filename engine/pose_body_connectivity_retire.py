"""Connectivity-refresh retire stage: unlink, reset and round-robin queue links.

Evidence: docs/reconstruction/LINK_SOLVER.md, Body connectivity retire (RVA
0x18de440) and the pointer-vector reserve it calls (RVA 0x18def10).

Recovered local behavior only. "Retire" is an authored service label: the native
routine does not destroy or free the selected links. It removes each one from its
selector1 endpoint rings, resets its endpoint/contact/held state and appends the
pointer to a pending vector at +0x28 of a queue owner chosen round-robin from the
provider's slot table at +0x70. What later consumes those vectors is not
reconstructed here.
"""
import struct

RESERVE_ALIGNMENT = 0x10
RESERVE_TAG = 0x28


def reserve_pose_pointer_vector(descriptor, capacity, *, allocator):
    """Set a pointer vector's capacity through the global allocator (0x18def10).

    descriptor is a writable 16-byte view: pointer q@0, count u32@8, capacity
    u32@0xC. Equal capacity is a no-op. A null pointer is allocated, a nonnull
    pointer is reallocated for nonzero capacity, or released and nulled for zero.
    Byte size is the 32-bit truncation of capacity*8. Capacity is then stored and
    a larger count is clamped to it. Old element bytes are the allocator's concern.
    allocator.allocate(size, alignment, tag), reallocate(pointer, size, alignment,
    tag) and release(pointer) are supplied services (allocator vtable+8/+0x10/+0x18).
    """
    capacity &= 0xFFFFFFFF
    if capacity == struct.unpack_from('<I', descriptor, 0xC)[0]:
        return
    pointer = struct.unpack_from('<Q', descriptor, 0)[0]
    size = (capacity * 8) & 0xFFFFFFFF
    if pointer:
        if capacity:
            pointer = allocator.reallocate(pointer, size, RESERVE_ALIGNMENT, RESERVE_TAG)
        else:
            allocator.release(pointer)
            pointer = 0
    else:
        pointer = allocator.allocate(size, RESERVE_ALIGNMENT, RESERVE_TAG)
    struct.pack_into('<Q', descriptor, 0, pointer)
    struct.pack_into('<I', descriptor, 0xC, capacity)
    if struct.unpack_from('<I', descriptor, 8)[0] > capacity:
        struct.pack_into('<I', descriptor, 8, capacity)


def retire_pose_body_connectivity(provider, output, divisor, *, queue_owners,
        queue_arrays, detach, reset, reserve):
    """Process selected link pointers in order; native order per element:

    1. detach(link, 1)  -- 0x195c270; bind to pose_endpoint_rings.detach_pose_endpoint_rings
    2. owner = provider qword at 0x70 + 8*slot  (captured before reset)
    3. reset(link)      -- 0x1958ba0; bind to pose_link_state_reset.reset_pose_link_state
    4. owner+0x28 vector: if count == capacity, reserve(view, 2*capacity or 8)
       (32-bit doubling), then reread pointer/count, store link, count += 1
    5. slot = (slot + 1) % divisor, 32-bit unsigned; slot starts at 0

    output is the shared selection list. Its length is captured once; elements are
    reread each iteration. queue_owners maps owner token -> raw owner bytes;
    queue_arrays maps vector pointer -> element bytes. A zero divisor raises
    ZeroDivisionError after the first link has been fully queued, where native
    takes a divide fault; an empty output never divides. Count above capacity
    is not grown or checked natively; an undersized array raises here.
    """
    count = len(output) & 0xFFFFFFFF
    divisor &= 0xFFFFFFFF
    slot = 0
    for i in range(count):
        link = output[i]
        detach(link, 1)
        owner_token = struct.unpack_from('<Q', provider, 0x70 + slot * 8)[0]
        reset(link)
        owner = queue_owners[owner_token]
        vector = memoryview(owner)[0x28:0x38]
        used, capacity = struct.unpack_from('<II', vector, 8)
        if used == capacity:
            reserve(vector, (capacity * 2) & 0xFFFFFFFF if capacity else 8)
        pointer, used = struct.unpack_from('<QI', vector, 0)
        elements = queue_arrays[pointer]
        if len(elements) < used * 8 + 8:
            raise IndexError('queue vector storage is smaller than its count')
        struct.pack_into('<Q', elements, used * 8, link)
        struct.pack_into('<I', vector, 8, (used + 1) & 0xFFFFFFFF)
        slot = ((slot + 1) & 0xFFFFFFFF) % divisor
