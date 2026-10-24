"""Recovered packed link keys and serialized payload-row layout.

Evidence: CENTRAL_IMPULSE.md, Link keys and payload row serialization.
Field names remain structural; no contact/manifold semantics are assumed.
"""
import struct


def pack_link_key(first, second, detail):
    """Two low-16 fields followed by one low-32 field, in a uint64 key."""
    return (first&0xffff)|((second&0xffff)<<16)|((detail&0xffffffff)<<32)


def decode_payload_row(serialized, previous_row):
    """Map one admitted 60-byte serialized field into a retained 64-byte row.

    The caller supplies prior bytes so the final four bytes remain untouched.
    This does not parse the enclosing tagged stream or select active row count.
    """
    if len(serialized)!=60 or len(previous_row)!=64:
        raise ValueError('Exact 60-byte field and 64-byte destination row required')
    out=bytearray(previous_row);cursor=0
    for offset in (0x10,0x14,0x18,0x20,0x24,0x28,0,4,8,0xc,0x30,0x34):
        out[offset:offset+4]=serialized[cursor:cursor+4];cursor+=4
    for offset in (0x38,0x3a,0x2c,0x2e):
        out[offset:offset+2]=serialized[cursor:cursor+2];cursor+=2
    out[0x1c:0x20]=serialized[cursor:cursor+4]
    return bytes(out)


def remove_link_key(collection, first, second, detail):
    """Remove the last matching packed key by swap-last; keep inactive tail.

    Collection slots contain 16-byte immutable records. Return is an authored
    diagnostic; native function's return register is not a boolean contract.
    """
    key=pack_link_key(first,second,detail)
    for index in range(collection['count']-1,-1,-1):
        if struct.unpack_from('<Q',collection['slots'][index])[0]!=key:continue
        collection['count']-=1
        collection['slots'][index]=collection['slots'][collection['count']]
        return True
    return False
