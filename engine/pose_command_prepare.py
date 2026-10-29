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


def construct_pose_command_constraint(constraint, *, constraint_token, owner_token,
                                       first_body, second_body, callback_token,
                                       userdata, request_byte, table, secondary_table,
                                       bodies, metadata, construct_base, invoke):
    """Recovered specialized constructor with supplied base construction.

    construct_base(constraint_token, first_body, second_body, owner_token, byte)
    initializes the same constraint buffer and may reorder endpoints. invoke uses
    the preparation callback interface, but scalar/mode are0 and count is cleared.
    Unlike per-step preparation, construction has no six-count post-call reset.
    Table identities are caller supplied build-specific evidence.
    """
    construct_base(constraint_token,first_body,second_body,owner_token,request_byte&255)
    struct.pack_into('<Q',constraint,0,table)
    struct.pack_into('<Q',constraint,0x40,secondary_table)
    view=memoryview(constraint)
    initialize_pose_command_storage(view[0x78:0x1f8])
    actual_first=struct.unpack_from('<Q',constraint,8)[0]
    struct.pack_into('<Q',constraint,0x1f8,callback_token)
    struct.pack_into('<Q',constraint,0x50,userdata)
    constraint[0x59]=int(first_body!=actual_first)
    actual_second=struct.unpack_from('<Q',constraint,0x10)[0]
    single=True
    if actual_second:
        body=bodies[actual_second]
        meta=metadata[struct.unpack_from('<Q',body,0x30)[0]]
        single=not bool(struct.unpack_from('<H',meta,0x50)[0]&0x8000)
    constraint[0x70]=int(single)
    a,b=(actual_second,actual_first) if constraint[0x59] else (actual_first,actual_second)
    struct.pack_into('<I',constraint,0x74,0)
    invoke(callback_token,a,b,view[0x78:0x1f8],view[0x74:0x78],0.,0,userdata)
