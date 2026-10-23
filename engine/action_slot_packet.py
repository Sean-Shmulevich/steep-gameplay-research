"""Recovered initial-slot packet conversion before later cache processing.

Evidence: INPUT_UPDATE_ORDER.md, Initial-slot packet conversion.
Packet and binding records must be supplied; no device API or key map inferred.
"""
import struct
from engine.action_cache_exchange import CACHE_SPAN


def _inputs(snapshot, packet):
    if not isinstance(snapshot,bytes) or len(snapshot)!=CACHE_SPAN:
        raise ValueError('exact 0x818-byte snapshot required')
    if not isinstance(packet,bytes) or len(packet)!=16:
        raise ValueError('exact 16-byte slot packet required')


def decode_slot_axes(snapshot, packet):
    """Copy four signed int16 / 32767 axes into two XY pairs, retaining Z/W."""
    _inputs(snapshot, packet)
    result=bytearray(snapshot)
    for offset,value in zip((0x1f0,0x1f4,0x200,0x204),struct.unpack_from('<4h',packet,8)):
        struct.pack_into('<f',result,offset,value/32767.0)
    return bytes(result)


def map_slot_buttons(snapshot, packet, bindings):
    """Map 32 explicit (kind, code) uint32 pairs to bytes and float32 scalars.

    Only kind 1 and nonzero code are active. Native shift counts wrap modulo32.
    Masks 0x400/0x800 use packet trigger bytes6/7: digital >30, analog /255.
    Other masks test the packet uint16 at +4 and yield digital/analog 0 or1.
    Unmapped entries are cleared, not retained. No axis conversion occurs here.
    """
    _inputs(snapshot,packet)
    records=tuple(tuple(pair) for pair in bindings)
    if len(records)!=32 or any(len(pair)!=2 for pair in records):
        raise ValueError('32 kind/code pairs required')
    if any(type(v) is not int or not 0<=v<1<<32 for pair in records for v in pair):
        raise ValueError('uint32 binding fields required')
    result=bytearray(snapshot)
    buttons=struct.unpack_from('<H',packet,4)[0]
    for i,(kind,code) in enumerate(records):
        pressed=False;scalar=0.0
        if kind==1 and code:
            mask=1<<((code-1)&31)
            if mask in (0x400,0x800):
                raw=packet[6 if mask==0x400 else 7]
                pressed=raw>30;scalar=raw/255.0
            else:
                pressed=(buttons&mask)==mask;scalar=float(pressed)
        result[0x30+i]=int(pressed)
        struct.pack_into('<f',result,0x168+i*4,scalar)
    return bytes(result)
