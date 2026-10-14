"""Bounded clip-body framing from Studio format research, not native execution.

Evidence and limitations: docs/reconstruction/ANIMATION_CONTAINER.md.
Returned metadata is caller-owned; public diagnostics must omit private IDs.
"""
import math
import struct
from .animation_channel_framing import frame_serialized_channel


def parse_clip_body(data):
    data=memoryview(data);position=0
    def take(size):
        nonlocal position
        if size<0 or size>len(data)-position:raise ValueError('truncated clip body')
        start=position;position+=size
        return data[start:position]
    def read(fmt):return struct.unpack('<'+fmt,take(struct.calcsize('<'+fmt)))[0]
    def expect(fmt,value):
        if read(fmt)!=value:raise ValueError('unexpected clip field')
    def zeros(size):
        if any(take(size)):raise ValueError('nonzero reserved clip field')
    def object_header(kind):
        expect('B',0);expect('Q',0);expect('I',kind)
    record_id=read('Q');expect('I',0x0fa3067f);expect('B',1)
    duration=read('f')
    if not math.isfinite(duration) or duration<0:raise ValueError('invalid clip duration')
    hash_a=read('I');probe=read('I');version=2 if probe else 1
    hash_b=probe if version==2 else None
    if version==2:zeros(8)
    zeros(3);streamed=read('B')
    if streamed not in (0,1):raise ValueError('invalid streamed flag')
    event_count=read('I');events=[]
    if event_count>(len(data)-position)//23:raise ValueError('invalid event-track count')
    for _ in range(event_count):
        object_header(0x41682213);expect('H',65535);count=read('I');items=[]
        if count>(len(data)-position)//109:raise ValueError('invalid event count')
        for _ in range(count):
            start=position;expect('B',0);uid=read('Q');kind=read('I')
            if uid==0:raise ValueError('missing event identifier')
            if kind==0x561e06fc:size=117 if version==1 else 119;marker=size-2
            elif kind==0x2350a2e0:size=109;marker=94
            else:raise ValueError('unsupported event class')
            take(size-13)
            if bytes(data[start+marker:start+marker+2])!=b'\x01\x03':raise ValueError('invalid event marker')
            items.append({'class':kind,'serialized_start':start,'serialized_end':position})
        expect('I',0);expect('H',count)
        times=[read('H') for _ in range(count)]
        if times!=sorted(times):raise ValueError('unsorted event times')
        events.append({'events':items,'ticks':times})
    object_header(0x0181efe8);hash_c=read('I');count=read('I')
    if count>(len(data)-position)//16:raise ValueError('invalid binding count')
    bindings=[]
    for _ in range(count):
        expect('Q',0);expect('I',0x653caa76);bindings.append(read('I'))
    if bindings!=sorted(bindings):raise ValueError('unsorted bindings')
    expect('H',0);blob_size=read('I') if version==2 else 0
    blob_start=position;take(blob_size)
    channel_mask=read('I');expect('I',count);tracks=[]
    for index,binding in enumerate(bindings):
        start=position
        if position>=len(data):raise ValueError('missing channel')
        if data[position]==254:
            take(1);reference=read('I')
            tracks.append({'track_number':index,'binding_hash':binding,
                           'shared_track_reference':reference,'serialized_start':start,'serialized_end':position})
        else:
            parsed=frame_serialized_channel(data,position);take(parsed['consumed'])
            tracks.append({'track_number':index,'binding_hash':binding,'codec':parsed['encoding'],
                           'serialized_start':start,'serialized_end':position})
    if position!=len(data):raise ValueError('trailing clip bytes')
    return {'version':version,'record_id':record_id,'duration':duration,'hash_a':hash_a,
            'hash_b':hash_b,'hash_c':hash_c,'streamed':streamed,'event_tracks':events,
            'blob_start':blob_start,'blob_size':blob_size,'channel_mask':channel_mask,
            'tracks':tracks,'consumed':position}
