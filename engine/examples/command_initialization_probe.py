"""Synthetic services exercise recovered constructor writes and publication order."""
import json
import struct
from engine.command_initialization import initialize_and_publish


def run():
    events = []
    storage = bytearray([0xa5] * 512)
    allocations = []

    def lock(buf, offset, receiver):
        events.append(dict(service='synthetic_lock', offset=offset))
        struct.pack_into('<Q', buf, offset, receiver+offset+8)

    def container(buf, offset, zero):
        events.append(dict(service='synthetic_container', offset=offset))
        buf[offset:offset+12] = bytes(12)

    def allocate(size, alignment, context):
        allocations.append(size)
        return 0x200000 + len(allocations) * 0x100000

    services = dict(lock=lock, container=container, allocate=allocate,
                    read_allocator_source=lambda: 0,
                    allocation_context=lambda size, mode, source: 0,
                    release_buffer=lambda buf, offset: events.append(dict(service='synthetic_empty_cleanup', offset=offset)),
                    clear_buffer=lambda buf, offset: events.append(dict(service='synthetic_clear', offset=offset)))
    published = []
    result = initialize_and_publish(storage, 0x100000, services=services, publish=published.append)
    return dict(evidence='recovered writes and normal-return publication with supplied synthetic services',
                allocation_bytes=allocations,
                capacities=[struct.unpack_from('<I', storage, o+20)[0] for o in (0x30, 0x88, 0x100, 0x160)],
                publication_matches_receiver=published == [result], services=events,
                native_allocator_or_lifetime_proved=False)


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
