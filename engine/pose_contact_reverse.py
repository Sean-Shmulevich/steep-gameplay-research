"""Contact role reversal; LINK_SOLVER.md, Reversed contact pair adapter."""
import struct


def reverse_contact_records(records, start, count):
    """Swap point roles and flip normal sign bits, preserving identifiers/scalars."""
    if start<0 or count<0 or (start+count)*48>len(records):
        raise ValueError('Complete retained record range required')
    for i in range(start,start+count):
        offset=i*48
        first=bytes(records[offset+16:offset+28])
        records[offset+16:offset+28]=records[offset+32:offset+44]
        records[offset+32:offset+44]=first
        for j in range(3):
            word=struct.unpack_from('<I',records,offset+j*4)[0]
            struct.pack_into('<I',records,offset+j*4,word^0x80000000)
