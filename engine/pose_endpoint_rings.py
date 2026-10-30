"""Recovered endpoint-specific circular registration and removal.

Evidence: LINK_SOLVER.md, Endpoint ring registration and removal.
"""
import struct


def _pointer(raw,offset):
    return struct.unpack_from('<Q',raw,offset)[0]


def _write(raw,offset,value):
    struct.pack_into('<Q',raw,offset,value)


def _head(body_token,selector,bodies):
    offset={0:0x88,1:0x80,2:0x90}.get(selector)
    return _pointer(bodies[body_token],offset) if offset is not None else 0


def _set_head(body_token,selector,value,bodies):
    offset={0:0x88,1:0x80,2:0x90}.get(selector)
    if offset is not None:_write(bodies[body_token],offset,value)


def _port(record,body_token):
    return 0x20 if _pointer(record,8)==body_token else 0x30


def attach_pose_endpoint_rings(token,selector,*,records,bodies):
    """Insert after each existing head, or publish a singleton ring.

    Both endpoints are processed, first then second. The native helpers do not
    treat null endpoints specially. Selector values other than0/1/2 do not publish
    body heads; records still receive singleton pointers. Normal use requires
    valid endpoints and an unlinked record.
    """
    record=records[token]
    for endpoint,port in ((8,0x20),(0x10,0x30)):
        body_token=_pointer(record,endpoint)
        head=_head(body_token,selector,bodies)
        if head:
            anchor=records[head]
            following=_pointer(anchor,_port(anchor,body_token))
            _write(record,port,following)
            _write(record,port+8,head)
            _write(anchor,_port(anchor,body_token),token)
            next_record=records[following]
            _write(next_record,_port(next_record,_pointer(record,endpoint))+8,token)
        else:
            _write(record,port,token);_write(record,port+8,token)
            _set_head(_pointer(record,endpoint),selector,token,bodies)


def detach_pose_endpoint_rings(token,selector,*,records,bodies):
    """Splice both rings, replace a removed head with its predecessor, clear ports.

    Assumes valid attached membership. Repeated removal is not idempotent and is
    not made so here. Neither record endpoints nor unrelated body heads are reset.
    """
    record=records[token]
    for endpoint,port in ((8,0x20),(0x10,0x30)):
        following=_pointer(record,port)
        if following==token:
            _set_head(_pointer(record,endpoint),selector,0,bodies)
        else:
            previous=_pointer(record,port+8)
            predecessor=records[previous]
            _write(predecessor,_port(predecessor,_pointer(record,endpoint)),following)
            # Reload both links after the first neighbor write, matching native.
            following=_pointer(record,port);previous=_pointer(record,port+8)
            successor=records[following]
            _write(successor,_port(successor,_pointer(record,endpoint))+8,previous)
            body_token=_pointer(record,endpoint)
            if _head(body_token,selector,bodies)==token:
                _set_head(body_token,selector,_pointer(record,port+8),bodies)
    record[0x20:0x40]=bytes(32)
