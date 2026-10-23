"""Compose recovered allocation policy and manager startup using a synthetic heap."""
import json
import struct
from engine.allocation_policy import allocate_bytes, select_allocation_context
from engine.command_initialization import allocate_construct_publish, initialize_manager


def run():
    buffers, events, published = {}, [], []
    active = [1]
    attempts = [0]

    def backend(allocator, size, context):
        attempts[0] += 1
        events.append(dict(event='synthetic_allocate', allocator=allocator, bytes=size, context=context))
        if attempts[0] == 1:
            return 0
        token = 0x100000 + attempts[0]*0x100000
        buffers[token] = bytearray([0xa5]*size)
        return token

    def recover(*args):
        events.append(dict(event='synthetic_recovery', request=list(args)))
        active[0] = 2
        return 1

    def context(size, mode, source):
        return select_allocation_context(size, mode, source, special_a=11, special_b=22,
                   coarse_source=33, override_source=44, resolve=lambda *args: 0)

    def allocate(size, alignment, selected):
        return allocate_bytes(size, alignment, selected, current_allocator=lambda: active[0],
                   allocate_default=backend,
                   allocate_aligned=lambda allocator, size, alignment, selected: backend(allocator, size, selected),
                   recover=recover)

    def lock(storage, offset, receiver):
        struct.pack_into('<Q', storage, offset, receiver+offset+8)

    def container(storage, offset, zero):
        storage[offset:offset+12] = bytes(12)

    services = dict(read_allocator_source=lambda: 11, allocation_context=context, allocate=allocate,
                    lock=lock, container=container, release_buffer=lambda *args: None, clear_buffer=lambda *args: None)
    result = allocate_construct_publish(services=services, fallback=0,
                construct=lambda receiver: initialize_manager(buffers[receiver], receiver, services=services),
                publish=published.append)
    return dict(evidence='recovered dispatch and context policy; synthetic heap, globals and recovery',
                events=events, allocated_buffers=len(buffers), published_constructed_receiver=published == [result] and result in buffers,
                native_heap_or_lifetime_proved=False)


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
