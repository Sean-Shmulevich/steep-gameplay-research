"""Compose recovered startup and construction with synthetic storage/services."""
import json
import struct
from engine.command_initialization import allocate_construct_publish, initialize_manager


def run_case(fail_manager_allocation=False, fallback=0):
    buffers, requests, published = {}, [], []

    def allocate(size, alignment, context):
        requests.append(dict(bytes=size, alignment_argument=alignment))
        if fail_manager_allocation and len(requests) == 1:
            return 0
        token = 0x100000 + len(requests) * 0x100000
        buffers[token] = bytearray([0xa5] * size)
        return token

    def lock(storage, offset, receiver):
        struct.pack_into('<Q', storage, offset, receiver + offset + 8)

    def container(storage, offset, zero):
        storage[offset:offset+12] = bytes(12)

    services = dict(read_allocator_source=lambda: 1,
                    allocation_context=lambda size, mode, source: 42,
                    allocate=allocate, lock=lock, container=container,
                    release_buffer=lambda storage, offset: None,
                    clear_buffer=lambda storage, offset: None)
    result = allocate_construct_publish(services=services, fallback=fallback,
                construct=lambda receiver: initialize_manager(buffers[receiver], receiver, services=services),
                publish=published.append)
    return dict(manager_allocation_succeeds=not fail_manager_allocation,
                requests=requests, constructor_ran=len(requests) > 1,
                published_fallback=fail_manager_allocation and published == [fallback],
                constructed_manager_published=not fail_manager_allocation and result in buffers,
                native_allocator_or_lifetime_proved=False)


def run():
    return dict(evidence='composition of recovered control and writes with synthetic services',
                cases=[run_case(), run_case(True), run_case(True, 123)])


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
