"""Collect a body's circular link records and dispatch connectivity refresh.

Evidence: docs/reconstruction/LINK_SOLVER.md, Body connectivity refresh.
"""
import struct


def refresh_pose_body_connectivity(body, *, body_token, metadata, owners,
        controllers, links, collect, rebuild, retire):
    """Recover logical traversal and service ordering, abstracting scratch storage.

    collect(provider, rows)->mutable output list; rebuild(context, output) and
    retire(provider, output, 1) share that list. Rows are immutable 24-byte copies.
    Native scratch allocation/free is deliberately outside this logical API.
    Malformed nonclosing rings raise ValueError, an authored guard.
    """
    meta = metadata[struct.unpack_from('<Q', body, 0x30)[0]]
    owner = owners[struct.unpack_from('<Q', meta, 0x20)[0]]
    controller = controllers[struct.unpack_from('<Q', owner, 0x20)[0]]
    seed = struct.unpack_from('<Q', body, 0x80)[0]
    if not seed:
        return
    rows = []
    seen = set()
    current = seed
    while True:
        if not current or current in seen:
            raise ValueError('link ring does not close at its seed')
        seen.add(current)
        link = links[current]
        rows.append(bytes(link[8:0x20]))
        offset = 0x20 if struct.unpack_from('<Q', link, 8)[0] == body_token else 0x30
        current = struct.unpack_from('<Q', link, offset)[0]
        if current == seed:
            break
    output = collect(struct.unpack_from('<Q', controller, 0x38)[0], rows)
    rebuild(struct.unpack_from('<Q', controller, 0x30)[0], output)
    retire(struct.unpack_from('<Q', controller, 0x38)[0], output, 1)
