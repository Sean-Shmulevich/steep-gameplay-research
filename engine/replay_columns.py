"""Bounded reconstruction of the live-replay byte-column decoder, version >=70.

Evidence: docs/reconstruction/LIVE_REPLAY_LEADS.md, Byte-column compression.
Input begins at the second-stage compressed block, not a complete ghost file.
Record meanings and outer framing remain unresolved. Limits are authored guards.
"""
import struct


def decode_columns(payload, record_count, *, max_output=16*1024*1024):
    if not isinstance(payload, (bytes, bytearray)):
        raise ValueError('Byte payload required')
    if type(record_count) is not int or record_count < 1:
        raise ValueError('Positive record count required')
    if type(max_output) is not int or max_output < 0:
        raise ValueError('Nonnegative output bound required')
    if len(payload)<4:
        raise ValueError('Truncated record width')
    width=struct.unpack_from('<I',payload)[0]
    total=width*record_count
    if total>max_output or total>0xffffffff:
        raise ValueError('Decoded records exceed output bound')
    output=bytearray(total);cursor=4
    def take():
        nonlocal cursor
        if cursor>=len(payload):raise ValueError('Truncated column stream')
        value=payload[cursor];cursor+=1
        return value
    for column in range(width):
        literal=take()
        remaining=0;value=0
        for row in range(record_count):
            if literal:
                value=take()
            else:
                if remaining==0:
                    value=take();remaining=take()
                # Native counter is uint8. A stored zero yields 256 repetitions.
                remaining=(remaining-1)&255
            output[row*width+column]=value
    return {'record_width':width,'record_count':record_count,
            'data':bytes(output),'consumed':cursor}
