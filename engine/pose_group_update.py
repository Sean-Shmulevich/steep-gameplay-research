"""Recovered body group-update orchestration with explicit native services.

Evidence: CENTRAL_IMPULSE.md, Body group update ordering.
Context fields group408/group410 and body metadata names remain structural.
"""


def update_pose_body_group(context, body, *, eligible, detach, virtual8,
                           acquire_group, virtual40, append, finalize):
    """Normal-return service ordering over retained mutable dictionaries.

    body: group, metadata {flags16, flags8, kind8}; context: group408, group410.
    All service effects are external, including assignment of body.group.
    """
    group=body['group']
    if body['metadata']['flags8']&8:
        was_special=(group==context['group410'])
        if (eligible(context,body)&255)!=int(was_special):
            detach(context,body)
            if virtual8(body,1)&255:
                metadata=body['metadata']
                if not metadata['flags16']&0x8000:
                    selected=context['group408']
                elif metadata['flags8']&8 and eligible(context,body)&255:
                    selected=context['group410']
                else:
                    selected=acquire_group(context)
                    if body['metadata']['kind8']&15==2:
                        virtual40(body)
                append(selected,body)
            group=body['group']
    return finalize(context,group)
