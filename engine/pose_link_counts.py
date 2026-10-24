"""Recovered mode-dependent link prepass for planned solver category counts.

Evidence: LINK_SOLVER.md, Link category-count prepasses.
"""
import struct


def count_pose_link_rows(counts,link_tokens,*,links,bodies,payloads,mode):
    """Accumulate into25 retained uint32 counters; mode is the raw settings value.

    Zero mode groups multi-row payloads into category4/5 while nonzero mode uses
    two category6/7 rows per point. Other categories remain untouched. No builder
    implementation or physical meaning is inferred for categories4/5 here.
    """
    if len(counts)!=25 or any(type(v) is not int or not 0<=v<=0xffffffff for v in counts):
        raise ValueError('Exactly25 raw uint32 counts required')
    if type(mode) is not int or not 0<=mode<=0xffffffff:raise ValueError('Raw uint32 mode required')
    for i in range(len(link_tokens)):
        link=links[link_tokens[i]]
        if not link['flags84']&1:continue
        extent=link['payload_count'];total=0;single=0;multiple=0
        for slot in range(extent):
            payload=payloads[link['payload_slots'][slot]]
            if not payload[0x114]&1:continue
            n=struct.unpack_from('<I',payload,0x110)[0]
            total=(total+n)&0xffffffff
            if mode==0:
                if n>1:multiple=(multiple+1)&0xffffffff
                elif n==1:single=(single+1)&0xffffffff
        branch=1 if bodies[link['second_body']]['metadata_flags50']&0x8000 else 0
        counts[branch]=(counts[branch]+total)&0xffffffff
        counts[6+branch]=(counts[6+branch]+2*(single if mode==0 else total))&0xffffffff
        if mode==0:counts[4+branch]=(counts[4+branch]+multiple)&0xffffffff
