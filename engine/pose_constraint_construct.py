"""Recovered base constraint initialization and endpoint ordering.

Evidence: LINK_SOLVER.md, Base construction and endpoint canonicalization.
"""
import struct


def construct_pose_constraint_base(record,*,constraint_token,first_body,second_body,
        owner_token,request_byte,tables,bodies,metadata,visit_body):
    """Initialize base state, returning the original object identity.

    owner_token is retained for caller ABI compatibility but is unused here.
    visit_body(body_token) supplies each admitted original endpoint's virtual28.
    It is not labeled as wake/activation because those concrete effects are unknown.
    Nullable second endpoints are supported by construction, not necessarily by
    later two-endpoint ring registration.
    """
    def meta(body):
        ptr=struct.unpack_from('<Q',bodies[body],0x30)[0]
        return metadata[ptr]
    def prioritized(body):return bool(struct.unpack_from('<H',meta(body),0x50)[0]&0x8000)
    def key(body):return struct.unpack_from('<I',meta(body),0x54)[0]
    record[8:0x20]=bytes(24)
    first_priority=prioritized(first_body);first_key=key(first_body)
    second_key=0
    swap=False
    if second_body:
        second_priority=prioritized(second_body);second_key=key(second_body)
        swap=(not first_priority and second_priority) or (
            first_priority==second_priority and second_key<first_key)
    a,b,ka,kb=(second_body,first_body,second_key,first_key) if swap else (
        first_body,second_body,first_key,second_key)
    struct.pack_into('<QQII',record,8,a,b,ka,kb)
    record[0x20:0x40]=bytes(32)
    struct.pack_into('<I',record,0x48,0xffffffff)
    struct.pack_into('<Q',record,0x50,0)
    struct.pack_into('<Q',record,0,tables[0]);struct.pack_into('<Q',record,0x40,tables[1])
    struct.pack_into('<H',record,0x59,0x100)
    struct.pack_into('<Q',record,0x60,0);struct.pack_into('<I',record,0x68,0xffffffff)
    if request_byte&255 and prioritized(first_body) and second_body and prioritized(second_body):
        visit_body(first_body);visit_body(second_body)
    return constraint_token
