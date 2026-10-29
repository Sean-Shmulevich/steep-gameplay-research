"""Recovered kind4 command preparation and six-command defaults.

Evidence: LINK_SOLVER.md, Command preparation producer boundary.
"""
import struct


def initialize_pose_command_storage(storage):
    """Initialize six64-byte records, preserving bytes outside the384-byte span."""
    for index in range(6):
        offset=64*index
        storage[offset:offset+48]=bytes(48)
        struct.pack_into('<4I',storage,offset+48,0,0xff7fffff,0x7f7fffff,0)


def prepare_pose_command_constraint(constraint, *, reciprocal, bodies, metadata, invoke):
    """Invoke stored callback with writable inline output views when admitted.

    invoke(function, first, second, commands, count, reciprocal, mode, userdata).
    commands is384 bytes; count is4 bytes. This binding requires a well-behaved
    callback that respects supplied storage. Return value is an authored admitted
    flag, not a recovered native return value.
    """
    first=struct.unpack_from('<Q',constraint,8)[0]
    body=bodies[first]
    meta=metadata[struct.unpack_from('<Q',body,0x30)[0]]
    if meta[0x52]&1:return False
    second=struct.unpack_from('<Q',constraint,0x10)[0]
    if second:
        meta=metadata[struct.unpack_from('<Q',bodies[second],0x30)[0]]
        if meta[0x52]&1:return False
    if constraint[0x59]:first,second=second,first
    userdata=struct.unpack_from('<Q',constraint,0x50)[0]
    function=struct.unpack_from('<Q',constraint,0x1f8)[0]
    view=memoryview(constraint)
    invoke(function,first,second,view[0x78:0x1f8],view[0x74:0x78],reciprocal,1,userdata)
    if struct.unpack_from('<I',constraint,0x74)[0]>6:
        struct.pack_into('<I',constraint,0x74,0)
    return True
