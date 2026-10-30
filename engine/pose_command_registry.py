"""Recovered provider registration for command preparation collections.

Evidence: LINK_SOLVER.md, Command registry population.
"""
import struct


def _u32(raw,offset):
    return struct.unpack_from('<I',raw,offset)[0]


def _pointer(raw,offset):
    return struct.unpack_from('<Q',raw,offset)[0]


def _append(provider,offset,token,arrays,grow):
    capacity=_u32(provider,offset+12)
    if _u32(provider,offset+8)==capacity:
        grow(provider,offset,(capacity*2)&0xffffffff if capacity else 8)
    count=_u32(provider,offset+8)
    arrays[_pointer(provider,offset)][count]=token
    struct.pack_into('<I',provider,offset+8,(count+1)&0xffffffff)


def register_pose_constraint(provider,token,*,arrays,grow,notify,get_kind):
    """Register one constraint, attach endpoint rings, then classify it.

    grow(provider,descriptor_offset,capacity) updates storage/pointer/capacity and
    preserves active entries. notify(token,2) supplies endpoint-ring insertion;
    the service name is retained for API compatibility.
    get_kind(token) supplies the virtual method's uint32 result. The first command
    list is70; the general constraint list is60. No inferred duplicate rejection.
    """
    _append(provider,0x60,token,arrays,grow)
    notify(token,2)
    if get_kind(token)==4:
        _append(provider,0x70,token,arrays,grow)


def register_pose_constraint_container(provider,token,*,containers,arrays,grow,get_kind):
    """Register an object and append kind4 children to the second command list.

    Child count60 is captured after the object append. Child pointer58 is reloaded
    on every iteration. The returned index is captured before storage growth.
    The registered object's semantic class remains unresolved.
    """
    original_count=_u32(provider,0x58)
    _append(provider,0x50,token,arrays,grow)
    container=containers[token]
    count=_u32(container,0x60)
    for index in range(count):
        child=arrays[_pointer(container,0x58)][index]
        if get_kind(child)==4:
            _append(provider,0x80,child,arrays,grow)
    return original_count
