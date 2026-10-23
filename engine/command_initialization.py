"""Detached reconstruction of command-manager initialization and publication.

Evidence: REQUEST_COMMAND_LIFECYCLE.md, Command-manager initialization contract,
Exact command-manager constructor entry, and Constructor return publication.
Caller supplies storage and external services; this does not allocate the manager,
initialize native locks, access live memory, or establish object lifetime.
Names and the Python service interface are authored reconstruction choices.
"""
import struct


def initialize_manager(storage, receiver, *, services):
    """Apply known writes in native order and return the supplied receiver token.

    storage is a mutable bytearray covering at least 0x179 bytes. Services are
    lock(storage, offset, receiver), container(storage, offset, zero),
    release_buffer(storage, offset), clear_buffer(storage, offset),
    read_allocator_source(), allocation_context(size, mode, source), and
    allocate(size, alignment, context). Returned allocation tokens are uint64;
    zero selects the observed null-result branch. Native failure policy is unknown.
    Service exceptions propagate without rollback; no native unwind claim follows.
    Unwritten bytes remain caller-owned and unchanged by this function.
    """
    if not isinstance(storage, bytearray) or len(storage) < 0x179:
        raise ValueError('mutable storage covering 0x179 bytes required')
    if type(receiver) is not int or not 0 <= receiver < 2**64:
        raise ValueError('uint64 receiver token required')
    required = ('lock', 'container', 'release_buffer', 'clear_buffer',
                'read_allocator_source', 'allocation_context', 'allocate')
    if any(not callable(services.get(name)) for name in required):
        raise ValueError('all explicit external services required')

    def put(offset, fmt, value):
        struct.pack_into(fmt, storage, offset, value)

    def empty_header(offset, owned=False):
        storage[offset:offset+24] = bytes(24)
        if owned:
            storage[offset+24] = 1

    def allocate(offset, capacity, stride):
        size = capacity * stride
        source = services['read_allocator_source']()
        context = services['allocation_context'](size, 0xffffffff, source)
        pointer = services['allocate'](size, 1, context)
        if type(pointer) is not int or not 0 <= pointer < 2**64:
            raise ValueError('allocator service must return a uint64 token')
        put(offset, '<Q', pointer)
        if pointer:
            storage[offset+24] = 1
        put(offset+20, '<I', capacity if pointer else 0)

    services['lock'](storage, 0, receiver)
    empty_header(0x30)
    allocate(0x30, 3072, 104)
    put(0x50, '<I', 0)
    put(0x54, '<I', 0)
    services['lock'](storage, 0x58, receiver)
    empty_header(0x88)
    allocate(0x88, 4, 16)
    put(0xa8, '<I', 0)
    put(0xac, '<I', 0)
    services['container'](storage, 0xb0, 0)
    storage[0xbc] = 0
    services['lock'](storage, 0xc0, receiver)
    services['container'](storage, 0xf0, 0)
    empty_header(0x100, owned=True)
    services['lock'](storage, 0x120, receiver)
    services['container'](storage, 0x150, 0)
    empty_header(0x160, owned=True)
    for offset in (0x100, 0x160):
        if struct.unpack_from('<I', storage, offset+20)[0] == 128:
            services['clear_buffer'](storage, offset)
        else:
            services['release_buffer'](storage, offset)
            allocate(offset, 128, 104)
    return receiver


def initialize_and_publish(storage, receiver, *, services, publish):
    """Compose the recovered normal-return boundaries with a supplied publisher.

    publish receives the constructor result only after initialization returns.
    It models the singleton store as an external service, not native synchronization.
    """
    if not callable(publish):
        raise ValueError('publisher required')
    result = initialize_manager(storage, receiver, services=services)
    publish(result)
    return result


def allocate_construct_publish(*, services, construct, publish, fallback):
    """Recovered startup control with allocator/constructor/publisher supplied.

    See REQUEST_COMMAND_LIFECYCLE.md, Manager storage request and conditional
    construction. Context receives (384, 8, allocator_source); allocate receives
    (384, 8, context). A zero allocation skips construct and publishes fallback,
    corresponding to incoming RSI. No universal zero-RSI invariant is assumed.
    Native allocator implementation, failure policy and lifetime remain unknown.
    Validation and Python exception propagation are authored interface behavior.
    """
    if type(fallback) is not int or not 0 <= fallback < 2**64:
        raise ValueError('explicit uint64 fallback token required')
    if not callable(construct) or not callable(publish):
        raise ValueError('constructor and publisher required')
    if any(not callable(services.get(name)) for name in
           ('read_allocator_source', 'allocation_context', 'allocate')):
        raise ValueError('explicit allocator services required')
    source = services['read_allocator_source']()
    context = services['allocation_context'](384, 8, source)
    receiver = services['allocate'](384, 8, context)
    if type(receiver) is not int or not 0 <= receiver < 2**64:
        raise ValueError('allocator service must return a uint64 token')
    result = construct(receiver) if receiver else fallback
    if type(result) is not int or not 0 <= result < 2**64:
        raise ValueError('constructor service must return a uint64 token')
    publish(result)
    return result
