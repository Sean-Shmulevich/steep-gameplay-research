"""Byte-bank adapter for recovered parent-relative hierarchy conversion.

Evidence: CENTRAL_IMPULSE.md, Relative conversion byte adapter.
This representation keeps primary transforms in data, separate from the
supplemental records list. Header bytes are opaque and never interpreted.
"""
import struct
from reference.animation_hierarchy import decompose_bank_hierarchy


def convert_relative_byte_bank(source, destination, selector, reciprocal_sqrt):
    if destination is None:
        destination=source
    count=source['profile']['primary_count']
    if type(count) is not int or not 0<=count<=65535:
        raise ValueError('uint16 primary count required')
    if not count:
        return dict(visited=[],skipped=[],in_place=destination is source)
    a,b=source['data'],destination['data']
    # Distinct memoryview slices can overlap invisibly. Do not snapshot them and
    # silently claim native overlap behavior; this bridge accepts whole buffers.
    if not isinstance(a,(bytes,bytearray)) or not isinstance(b,bytearray):
        raise ValueError('whole byte buffers required for relative conversion')
    if min(len(a),len(b))<count*32:
        raise ValueError('primary records outside supplied storage')
    header=source['parent_header']
    if not isinstance(header,bytes) or len(header)!=32:
        raise ValueError('opaque 32-byte parent header required')
    def unpack(data):
        rows=[struct.unpack_from('<8f',data,i*32) for i in range(count)]
        return [(r[:4],r[4:]) for r in rows]
    result=decompose_bank_hierarchy(unpack(a),None if a is b else unpack(b),
        source['profile']['metadata'],selector,reciprocal_sqrt)
    # Write only visited records, preserving skipped byte patterns exactly.
    for i in result['visited']:
        position,rotation=result['records'][i]
        struct.pack_into('<8f',b,i*32,*position,*rotation)
    destination['parent_header']=header
    destination['flags']=(destination['flags'] & ~(1<<27)) | (1<<26)
    return {k:result[k] for k in ('visited','skipped','in_place')}
