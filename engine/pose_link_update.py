"""Recovered paired-frame payload update and cached-word matching.

Evidence: CENTRAL_IMPULSE.md, Paired-frame payload update.
"""
import math
import struct
from reference.central_impulse import f32


def update_pose_link_payload(previous, records, *, first_frame, second_frame,
                             first_index, second_index):
    """Update zero to four 48-byte records in supplied 288-byte payload storage.

    Frames supply three XYZ basis rows and XYZ translation. No orthonormality is
    imposed. Row ID and cached values are raw32 words; no impulse meaning assumed.
    Returned immutable copy and finite-input validation are authored API choices.
    """
    if len(previous)!=288 or not 0<=len(records)<=4 or any(len(r)!=48 for r in records):
        raise ValueError('288-byte payload and at most four 48-byte records required')
    frames=[]
    for frame in (first_frame,second_frame):
        if len(frame['basis'])!=3 or any(len(v)!=3 for v in frame['basis']) or len(frame['translation'])!=3:
            raise ValueError('Three XYZ basis rows and XYZ translation required')
        basis=[[f32(x) for x in row] for row in frame['basis']]
        translation=[f32(x) for x in frame['translation']]
        if not all(math.isfinite(x) for row in basis+[translation] for x in row):
            raise ValueError('Finite frame components required')
        frames.append((basis,translation))
    oldcount=struct.unpack_from('<I',previous,0x110)[0]
    ids=[struct.unpack_from('<I',previous,0x2c+64*i)[0] for i in range(4)]
    cached=[struct.unpack_from('<I',previous,0x40+64*i)[0] if oldcount>i else 0 for i in range(4)]
    out=bytearray(previous)
    for i,record in enumerate(records):
        start=0x10+i*64;out[start:start+48]=record
        for src_offset,dst_offset,(basis,translation) in zip((16,32),(16,32),frames):
            point=struct.unpack_from('<3f',record,src_offset)
            if not all(math.isfinite(x) for x in point):raise ValueError('Finite point components required')
            delta=[f32(x-y) for x,y in zip(point,translation)]
            transformed=[]
            for row in basis:
                p=[f32(x*y) for x,y in zip(row,delta)]
                transformed.append(f32(f32(p[0]+p[1])+f32(p[2]+0.0)))
            struct.pack_into('<3f',out,start+dst_offset,*transformed)
        feature=struct.unpack_from('<I',record,28)[0]
        value=0
        for j in (3,2,1,0):
            if feature==ids[j]:value=cached[j]
        struct.pack_into('<IIHH',out,start+48,value,0,first_index&0xffff,second_index&0xffff)
    struct.pack_into('<I',out,0x110,len(records))
    return bytes(out)
