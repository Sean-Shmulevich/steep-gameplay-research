"""Recovered post-solve link payload feedback.

Evidence: CENTRAL_IMPULSE.md, Link solver-result feedback.
"""
import struct


def write_pose_link_feedback(context, link_tokens, *, links, payloads):
    """Copy result lane0 bits or zero into eligible retained payload rows.

    links[token]: flags84, payload_count, payload_slots. Payloads are writable
    bytearrays. context: flags38, result_rows of complete16-byte records.
    Valid retained storage is required. No synchronization or solver is supplied.
    """
    for token in link_tokens:
        link=links[token]
        if not link['flags84']&1:continue
        count=link['payload_count']
        for i in range(count):
            payload=payloads[link['payload_slots'][i]]
            if not payload[0x114]&1:continue
            row_count=struct.unpack_from('<I',payload,0x110)[0]
            if row_count>4:raise ValueError('Retained payload supports at most four rows')
            for row in range(row_count):
                offset=0x40+64*row
                if context['flags38']&0x20000000:
                    index=struct.unpack_from('<I',payload,offset+4)[0]
                    result=context['result_rows'][index]
                    if len(result)!=16:raise ValueError('Complete 16-byte solver result required')
                    payload[offset:offset+4]=result[:4]
                else:
                    payload[offset:offset+4]=bytes(4)
