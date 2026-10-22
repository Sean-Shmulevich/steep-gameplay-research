"""Bounded read-only compact action-map observer, not the full radix decoder.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Tagged action-map observation.
Unsupported roots are never reported as missing keys. No game calls or writes.
"""
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class MapObservation:
    status: str
    value_slot: int = 0
    action: int = 0
    count: int = 0


def observe_compact_map(read, root: int, key: int) -> MapObservation:
    """At most six reads, 528 bytes, two matching observations.

    Supports null root and inspected tag-1 leaves with 1..31 sorted keys.
    Tag-3 radix trees require another decoder. Matching copies do not pin memory
    or establish atomicity, lifetime, writer generation or ownership.
    """
    if any(type(x) is not int or not 0 <= x < 1 << 64 for x in (root, key)):
        raise ValueError('root and key must be uint64')
    if root == 0:
        return MapObservation('missing')
    if root & 7 != 1:
        return MapObservation('unsupported')
    base = root & ~7
    def get(offset, n):
        address=base+offset
        if address >= 1 << 64 or address+n > 1 << 64 or not base:
            raise ValueError('address overflow/null base')
        value=read(address,n)
        if not isinstance(value, bytes) or len(value)!=n:
            raise ValueError('incomplete read')
        return value
    def sample():
        last=struct.unpack('<Q',get(0,8))[0]
        if last >= 31:
            return MapObservation('unsupported'),last,()
        count=last+1
        keys=struct.unpack('<'+'Q'*count,get(8,count*8))
        if any(a>=b for a,b in zip(keys,keys[1:])):
            raise ValueError('unordered or duplicate keys')
        if key not in keys:
            return MapObservation('missing',count=count),last,keys
        index=keys.index(key)
        # Inspected value-area alignment tiers for last-index 0..30.
        offset=next(n for n in (2,3,4,6,8,12,16,24,32) if n>=count+1)
        slot=base+(offset+index)*8
        action=struct.unpack('<Q',get((offset+index)*8,8))[0]
        return MapObservation('found',slot,action,count),last,keys
    try:
        first,second=sample(),sample()
        return first[0] if first==second else MapObservation('unstable')
    except (OSError,ValueError,struct.error):
        return MapObservation('invalid')


def observe_action_map(read, root: int, key: int) -> MapObservation:
    """Compact roots or inspected radix branches and single-entry leaves.

    Radix work is capped at 16 nodes per pass, 128 reads and 8192 bytes total.
    Other leaf forms remain unsupported. Two complete traversal receipts must
    match, including bytes read along the selected path. Not an atomic snapshot.
    """
    if any(type(x) is not int or not 0 <= x < 1 << 64 for x in (root,key)):
        raise ValueError('root and key must be uint64')
    if root == 0 or root & 7 == 1:
        return observe_compact_map(read,root,key)
    if root & 7 != 3:
        return MapObservation('unsupported')
    reads=total=0
    class Limit(Exception):pass
    def sample():
        nonlocal reads,total
        receipt=[];seen=set()
        def get(a,n):
            nonlocal reads,total
            if not 0<a<1<<64 or a+n>1<<64:raise ValueError('address')
            reads+=1;total+=n
            if reads>128 or total>8192:raise Limit()
            b=read(a,n)
            if not isinstance(b,bytes) or len(b)!=n:raise ValueError('short read')
            receipt.append((a,b));return b
        def done(status,slot=0,action=0):
            return MapObservation(status,slot,action),tuple(receipt)
        node=(root&~7)+8
        for depth in range(16):
            if node in seen:raise ValueError('cycle')
            seen.add(node)
            raw=get(node,16);pointer,prefix=struct.unpack('<QQ',raw);tag=raw[15]
            if 8<=tag<=14:return done('missing')
            if 0x2c<=tag<=0x32:
                if (prefix^key)&0x00ffffffffffffff:return done('missing')
                return done('found',node,pointer)
            if tag==0x23 and depth==0:
                shift=56;family='dense'
            elif 0x0f<=tag<=0x15:
                shift=8*(tag-0x0e);family='linear'
            elif 0x16<=tag<=0x1c:
                shift=8*(tag-0x15);family='bitmap'
            elif 0x1d<=tag<=0x22:
                shift=8*(tag-0x1c);family='dense'
            else:return done('unsupported')
            mask=0x00ffffffffffffff & ~((1<<(shift+8))-1)
            if (prefix^key)&mask:return done('missing')
            digit=(key>>shift)&255;base=pointer&~7
            if family=='dense':
                if not base:raise ValueError('null children')
                node=base+digit*16
            elif family=='linear':
                header=get(base,8);count=header[0]
                if not 1<=count<=7:raise ValueError('linear count')
                digits=header[1:1+count]
                if len(set(digits))!=count:raise ValueError('duplicate digit')
                if digit not in digits:return done('missing')
                node=base+8+digits.index(digit)*16
            else:
                if not base:raise ValueError('null bitmap')
                header=get(base+(digit>>5)*16,16)
                bitmap=struct.unpack_from('<I',header)[0]
                bit=1<<(digit&31)
                if not bitmap&bit:return done('missing')
                children=struct.unpack_from('<Q',header,8)[0]&~7
                if not children:raise ValueError('null packed children')
                node=children+(bitmap&(bit-1)).bit_count()*16
        raise Limit()
    try:
        first,second=sample(),sample()
        return first[0] if first==second else MapObservation('unstable')
    except Limit:return MapObservation('limit')
    except (OSError,ValueError,struct.error):return MapObservation('invalid')
