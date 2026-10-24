"""Recovered link-builder dispatch, with builder bodies supplied as services.

Evidence: LINK_SOLVER.md, Link builder dispatch.
"""
import struct


def dispatch_pose_link_builders(context, link_tokens, *, links, bodies, payloads, builders):
    """Visit a retained link range and dispatch enabled payloads.

    Service names describe raw metadata-bit state and multi-row selection, not
    physical body classes. Each service receives (context, first, second, payload).
    Callbacks may mutate retained storage; captured gates/counts stay captured.
    Resizing/freeing the native range during traversal is outside this contract.
    """
    extent = len(link_tokens)
    for index in range(extent):
        link = links[link_tokens[index]]
        if not link['flags84'] & 1:
            continue
        first, second = link['first_body'], link['second_body']
        mode = context['flags38'] & 3
        count = link['payload_count']
        metadata_set = bool(bodies[second]['metadata_flags50'] & 0x8000)
        prefix = 'metadata_set' if metadata_set else 'metadata_clear'
        for slot in range(count):
            payload = payloads[link['payload_slots'][slot]]
            if not payload[0x114] & 1:
                continue
            multiple = mode == 0 and struct.unpack_from('<I', payload, 0x110)[0] > 1
            name = prefix + ('_multi' if multiple else '_single')
            builders[name](context, first, second, payload)
